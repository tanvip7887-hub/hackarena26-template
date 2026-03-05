import argparse
import threading
import datetime
import time
import cv2
import sys
import os

from flask import Flask, jsonify, request
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from detection.detector import PersonDetector
from detection.tracker import SORTTracker
from detection.zone_manager import ZoneManager
from detection.loitering import LoiterTracker
from detection.threat_engine import compute_threat
from detection.anomaly_detector import PersonBehaviourTracker
from detection.clip_recorder import ClipRecorder

from database.db import init_db, insert_alert, fetch_all_alerts, fetch_latest_alert

app = Flask(__name__)
CORS(app)

_lock = threading.Lock()
_current_status = {
    'mode': 'demo',
    'active_persons': 0,
    'threats': [],
    'latest_alert': None,
    'video_file': 'demo1.mp4'
}

_mode       = 'demo'
_video_file = 'demo1.mp4'
_stop_event = threading.Event()
_detection_thread = None


def _sync_night_mode(mode):
    import detection.threat_engine as te
    te.CURRENT_MODE = mode
    if mode == "demo":
        print("[ThreatEngine] DEMO → Night rule FORCED ON")
    else:
        print("[ThreatEngine] LIVE → Night rule uses REAL CLOCK")


@app.route("/alerts", methods=["GET"])
def get_alerts():
    alerts = fetch_all_alerts()
    return jsonify({"status": "ok", "count": len(alerts), "alerts": alerts})


@app.route("/current_status", methods=["GET"])
def current_status():
    with _lock:
        data = dict(_current_status)
    return jsonify({"status": "ok", "data": data})


@app.route("/videos", methods=["GET"])
def list_videos():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    vdir     = os.path.join(base_dir, "videos")
    videos   = []

    if os.path.isdir(vdir):
        videos = sorted([f for f in os.listdir(vdir) if f.endswith(".mp4")])

    return jsonify({"status": "ok", "videos": videos})


@app.route("/set_mode", methods=["POST"])
def set_mode():

    global _mode, _video_file, _detection_thread, _stop_event

    body      = request.get_json(force=True, silent=True) or {}
    new_mode  = body.get("mode", "").lower()
    new_video = body.get("video", _video_file)

    if new_mode not in ("live", "demo"):
        return jsonify({"status": "error","message": "mode must be live or demo"}), 400

    _stop_event.set()

    if _detection_thread and _detection_thread.is_alive():
        _detection_thread.join(timeout=5)

    _mode       = new_mode
    _video_file = new_video

    _sync_night_mode(new_mode)

    _stop_event       = threading.Event()
    _detection_thread = threading.Thread(
        target=_detection_loop,
        args=(_mode, _video_file, _stop_event),
        daemon=True
    )

    _detection_thread.start()

    with _lock:
        _current_status["mode"]       = new_mode
        _current_status["video_file"] = new_video

    print("[API] Switched → Mode:{} | Video:{}".format(new_mode, new_video))

    return jsonify({"status": "ok", "mode": new_mode, "video": new_video})


def _risk_colour(risk):
    return {
        "Low":    (0,255,0),
        "Medium": (0,165,255),
        "High":   (0,0,255)
    }.get(risk,(255,255,255))


# ───────────────── DETECTION LOOP ─────────────────

def _detection_loop(mode, video_file, stop):

    detector = PersonDetector("yolov8n.pt", confidence=0.4)
    tracker  = SORTTracker(max_age=90, min_hits=1)

    zone   = ZoneManager()
    loiter = LoiterTracker()

    clip_recorder = ClipRecorder(fps=30, seconds=10)

    risk_priority = {"Low":0,"Medium":1,"High":2}

    _last_risk          = {}
    _last_score_bracket = {}
    _seen_pids          = set()
    _peripheral_start   = {}
    _behaviour_trackers = {}

    if mode == "live":

        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            cap = cv2.VideoCapture(1)

        if not cap.isOpened():
            print("No webcam found")
            return

    else:

        base_dir  = os.path.dirname(os.path.abspath(__file__))
        demo_path = os.path.join(base_dir,"videos",video_file)

        if not os.path.exists(demo_path):
            print("Video not found")
            return

        cap = cv2.VideoCapture(demo_path)

    frame_count = 0
    fps_measured = 30
    fps_timer = time.time()

    while not stop.is_set():

        ret, frame = cap.read()

        if not ret:

            if mode=="demo":
                cap.set(cv2.CAP_PROP_POS_FRAMES,0)
                continue

            time.sleep(0.1)
            continue

        frame = cv2.resize(frame,(640,480))

        clip_recorder.add_frame(frame)

        frame_count+=1

        now=time.time()

        if now-fps_timer>=1:

            fps_measured = frame_count/(now-fps_timer)
            frame_count  = 0
            fps_timer    = now

        dets   = detector.detect(frame)
        tracks = tracker.update(dets)

        active_ids=set()

        frame_threats=[]

        now_str=datetime.datetime.now().isoformat(timespec="seconds")

        crowd_count=len(tracks)

        for trk in tracks:

            x1,y1,x2,y2,pid = trk
            pid=int(pid)

            bbox=[x1,y1,x2,y2]

            active_ids.add(pid)

            if pid not in _seen_pids:

                _seen_pids.add(pid)

                _last_risk[pid]="Low"

                _last_score_bracket[pid]=0

                _behaviour_trackers[pid]=PersonBehaviourTracker(pid)

            in_zone   = zone.is_inside(bbox,frame)

            near_zone = zone.is_near(bbox,frame,margin=50)

            if in_zone:
                loiter.person_entered(pid)
            else:
                loiter.person_exited(pid)

            ls = loiter.get_loiter_time(pid) if in_zone else 0.0

            bt=_behaviour_trackers[pid]

            bt.update(
                bbox,
                frame_shape=frame.shape,
                near_zone=near_zone,
                other_persons=None,
                fps=fps_measured
            )

            score,risk,expl = compute_threat(
                True,
                in_zone,
                ls,
                peripheral_seconds=0,
                crowd_count=crowd_count,
                behaviour_anomalies=bt.anomalies
            )

            prev_risk = _last_risk.get(pid,"Low")

            score_bracket=(score//10)*10

            prev_bracket=_last_score_bracket.get(pid,0)

            risk_went_up = risk_priority[risk] > risk_priority[prev_risk]

            score_jumped = score_bracket > prev_bracket and score_bracket>=30

            if risk_went_up or score_jumped:

                clip_path=None

                if risk in ["Medium","High"]:

                    try:

                        clip_path = clip_recorder.save_clip(risk,pid)

                    except Exception as e:

                        print("Clip save error",e)

                insert_alert(
                    now_str,
                    pid,
                    zone.name,
                    ls,
                    score,
                    risk,
                    expl,
                    clip_path
                )

                print("ALERT P{} Risk:{} Score:{} Clip:{}".format(pid,risk,score,clip_path))

            _last_risk[pid]=risk
            _last_score_bracket[pid]=score_bracket

            col=_risk_colour(risk)

            cv2.rectangle(frame,(int(x1),int(y1)),(int(x2),int(y2)),col,2)

        zone.draw(frame)

        hud="Mode:{} People:{} FPS:{:.0f}".format(mode.upper(),crowd_count,fps_measured)

        cv2.putText(frame,hud,(10,25),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,255),2)

        with _lock:

            _current_status["mode"]=mode

            _current_status["active_persons"]=crowd_count

            _current_status["threats"]=frame_threats

            _current_status["latest_alert"]=fetch_latest_alert()

            _current_status["video_file"]=video_file

        cv2.imshow("ThreatSense",frame)

        if cv2.waitKey(1) & 0xFF==ord("q"):
            stop.set()
            break

    cap.release()

    cv2.destroyAllWindows()


def start_detection(mode,video_file):

    global _detection_thread,_stop_event,_mode,_video_file

    _mode=mode

    _video_file=video_file

    _sync_night_mode(mode)

    if _detection_thread and _detection_thread.is_alive():

        _stop_event.set()

        _detection_thread.join(timeout=5)

    _stop_event=threading.Event()

    _detection_thread=threading.Thread(
        target=_detection_loop,
        args=(_mode,_video_file,_stop_event),
        daemon=True
    )

    _detection_thread.start()


if __name__=="__main__":

    parser=argparse.ArgumentParser(description="ThreatSense AI-DVR")

    parser.add_argument("--mode",choices=["live","demo"],default="demo")

    parser.add_argument("--video",default="demo1.mp4")

    parser.add_argument("--host",default="0.0.0.0")

    parser.add_argument("--port",type=int,default=5000)

    args=parser.parse_args()

    init_db()

    start_detection(args.mode,args.video)

    app.run(host=args.host,port=args.port,debug=False,use_reloader=False)