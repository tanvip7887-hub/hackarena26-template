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


# ─────────────────────────────────────────────────────────────
# NIGHT MODE SYNC
# demo mode → force night ON  (demo videos are night footage)
# live mode → use real clock  (accurate real world behaviour)
# ─────────────────────────────────────────────────────────────
def _sync_night_mode(mode):
    import detection.threat_engine as te
    te.CURRENT_MODE = mode
    if mode == "demo":
        print("[ThreatEngine] DEMO → Night rule FORCED ON (videos are night footage)")
    else:
        print("[ThreatEngine] LIVE → Night rule uses REAL CLOCK")


# ───────────────── API ENDPOINTS ─────────────────

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
    """
    Frontend calls this to get all available demo videos.
    Returns: {"videos": ["demo1.mp4", "demo2.mp4", "demo3.mp4"]}
    Frontend uses this to build video selector buttons automatically.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    vdir     = os.path.join(base_dir, "videos")
    videos   = []
    if os.path.isdir(vdir):
        videos = sorted([f for f in os.listdir(vdir) if f.endswith(".mp4")])
    return jsonify({"status": "ok", "videos": videos})


@app.route("/set_mode", methods=["POST"])
def set_mode():
    """
    Frontend sends this to switch mode or video.

    Switch to live webcam:
      POST /set_mode  {"mode": "live"}

    Switch to demo video 1:
      POST /set_mode  {"mode": "demo", "video": "demo1.mp4"}

    Switch to demo video 2:
      POST /set_mode  {"mode": "demo", "video": "demo2.mp4"}

    Switch to demo video 3:
      POST /set_mode  {"mode": "demo", "video": "demo3.mp4"}
    """
    global _mode, _video_file, _detection_thread, _stop_event

    body      = request.get_json(force=True, silent=True) or {}
    new_mode  = body.get("mode", "").lower()
    new_video = body.get("video", _video_file)

    if new_mode not in ("live", "demo"):
        return jsonify({"status": "error",
                        "message": "mode must be live or demo"}), 400

    # Stop current detection thread
    _stop_event.set()
    if _detection_thread and _detection_thread.is_alive():
        _detection_thread.join(timeout=5)

    _mode       = new_mode
    _video_file = new_video

    # Sync night mode BEFORE starting thread
    _sync_night_mode(new_mode)

    # Start new detection thread
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
        "Low":    (0, 255, 0),
        "Medium": (0, 165, 255),
        "High":   (0, 0, 255)
    }.get(risk, (255, 255, 255))


# ───────────────── DETECTION LOOP ─────────────────

def _detection_loop(mode, video_file, stop):

    detector = PersonDetector("yolov8n.pt", confidence=0.4)
    tracker  = SORTTracker(max_age=90, min_hits=1)

    zone   = ZoneManager()
    loiter = LoiterTracker()

    risk_priority         = {"Low": 0, "Medium": 1, "High": 2}
    _last_risk            = {}
    _last_score_bracket   = {}   # for continuous score bracket alerting
    _seen_pids            = set()
    _peripheral_start     = {}   # {pid: time entered peripheral zone}
    _behaviour_trackers   = {}

    # Object detection — YOLO classes we watch for
    SUSPICIOUS_OBJECTS = {
        24: "backpack", 26: "handbag", 28: "suitcase",
        67: "cell phone", 76: "scissors", 77: "teddy bear"
    }
    
    if mode == "live":
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            print("[Detection] ERROR: No webcam found.")
            return
        print("[Detection] LIVE MODE: Webcam opened.")
    else:
        base_dir  = os.path.dirname(os.path.abspath(__file__))
        demo_path = os.path.join(base_dir, "videos", video_file)
        if not os.path.exists(demo_path):
            print("[Detection] ERROR: Video not found:", demo_path)
            return
        cap = cv2.VideoCapture(demo_path)
        print("[Detection] DEMO MODE: Playing ->", video_file)

    print("-" * 70)
    print("  PID | ZONE | PERIPHERAL | LOITER | CROWD | BEHAVIOUR | SCORE | RISK")
    print("-" * 70)

    frame_count = 0
    fps_measured  = 30.0
    fps_timer     = time.time()

    while not stop.is_set():
        ret, frame = cap.read()
        if not ret:
            if mode == "demo":
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            time.sleep(0.1)
            continue

        frame = cv2.resize(frame, (640, 480))
        frame_count += 1

        # ── FPS Calculation (Safe & Stable) ──────────────────
        now = time.time()
        diff = now - fps_timer

        if diff >= 1.0:  # update once per second
            fps_measured = frame_count / diff
            frame_count = 0
            fps_timer = now

        # ── Detect persons ─────────────────────────────────────
        dets = detector.detect(frame)
        tracks = tracker.update(dets)
        # ── Detect objects every 5 frames (performance) ────────
        object_detections = {}   # {person_pid: (label, confidence)}
        if frame_count % 5 == 0:
            try:
                results = detector.model(frame, verbose=False)[0]
                for box in results.boxes:
                    cls_id = int(box.cls[0])
                    if cls_id in SUSPICIOUS_OBJECTS:
                        bx1,by1,bx2,by2 = map(int, box.xyxy[0])
                        obj_cx = (bx1+bx2)//2
                        obj_cy = (by1+by2)//2
                        # Match object to nearest person
                        for trk in tracks:
                            tx1,ty1,tx2,ty2,tpid = trk
                            if tx1<obj_cx<tx2 and ty1<obj_cy<ty2:
                                object_detections[int(tpid)] = (
                                    SUSPICIOUS_OBJECTS[cls_id],
                                    float(box.conf[0])
                                )
            except Exception:
                pass

        active_ids    = set()
        frame_threats = []
        now_str       = datetime.datetime.now().isoformat(timespec="seconds")
        crowd_count   = len(tracks)
        all_bboxes    = [[int(t[0]),int(t[1]),int(t[2]),int(t[3])] for t in tracks]

        for trk in tracks:
            x1, y1, x2, y2, pid = trk
            pid  = int(pid)
            bbox = [x1, y1, x2, y2]
            active_ids.add(pid)

            if pid not in _seen_pids:
                _seen_pids.add(pid)
                _last_risk[pid]          = "Low"
                _last_score_bracket[pid] = 0
                _behaviour_trackers[pid] = PersonBehaviourTracker(pid)
                print("\n[NEW PERSON] P{} entered scene".format(pid))

            # ── Location ───────────────────────────────────────
            in_zone   = zone.is_inside(bbox, frame)
            near_zone = zone.is_near(bbox, frame, margin=50)

            if in_zone:
                loiter.person_entered(pid)
                _peripheral_start.pop(pid, None)
            else:
                loiter.person_exited(pid)
                if near_zone:
                    if pid not in _peripheral_start:
                        _peripheral_start[pid] = time.time()
                else:
                    _peripheral_start.pop(pid, None)

            ls                 = loiter.get_loiter_time(pid) if in_zone else 0.0
            peripheral_seconds = (time.time() - _peripheral_start[pid]
                                  if pid in _peripheral_start else 0.0)

            # ── Object carrying ────────────────────────────────
            bt = _behaviour_trackers[pid]
            if pid in object_detections:
                label, conf = object_detections[pid]
                bt.carrying_object = True
                bt.carrying_label  = "{} ({:.0f}%)".format(label, conf*100)
            else:
                bt.carrying_object = False
                bt.carrying_label  = ""

            # ── Behaviour tracking ─────────────────────────────
            other_bboxes = [b for b in all_bboxes
                            if b != [int(x1),int(y1),int(x2),int(y2)]]
            #        other_persons=other_bboxes or None)


            bt.update(bbox, frame_shape=frame.shape,
            near_zone=near_zone,
          other_persons=other_bboxes or None,
             fps=fps_measured)        # ← add this

            # ── Threat score ───────────────────────────────────
            score, risk, expl = compute_threat(
                True, in_zone, ls,
                peripheral_seconds=peripheral_seconds,
                crowd_count=crowd_count,
                behaviour_anomalies=bt.anomalies
            )

            import detection.threat_engine as te
            night_str = "YES x1.5" if te.is_night_time() else "NO"

            frame_threats.append({
                "person_id":           pid,
                "bbox":                [int(x1),int(y1),int(x2),int(y2)],
                "in_zone":             in_zone,
                "near_zone":           near_zone,
                "loiter_seconds":      round(ls, 1),
                "peripheral_seconds":  round(peripheral_seconds, 1),
                "crowd_count":         crowd_count,
                "behaviour_summary":   bt.get_summary(),
                "behaviour_anomalies": bt.get_names(),
                "threat_score":        score,
                "risk_level":          risk,
                "explanation":         expl
            })

            # ── Smart alert — escalation OR score crosses bracket ──
            prev_risk     = _last_risk.get(pid, "Low")
            score_bracket = (score // 10) * 10   # 0,10,20,30...
            prev_bracket  = _last_score_bracket.get(pid, 0)

            risk_went_up      = risk_priority[risk] > risk_priority[prev_risk]
            score_jumped       = score_bracket > prev_bracket and score_bracket >= 30

            if risk_went_up or score_jumped:
                insert_alert(now_str, pid, zone.name, ls, score, risk, expl)
                print("\n[ALERT] P{}".format(pid))
                print("  Zone        : {} | Near: {}".format(in_zone, near_zone))
                print("  Loiter      : {:.1f}s | Peripheral: {:.1f}s".format(
                    ls, peripheral_seconds))
                print("  Crowd       : {}".format(crowd_count))
                print("  Behaviours  : {}".format(bt.get_summary()))
                print("  Score       : {}  Risk: {}".format(score, risk))
                print("  Night       : {}".format(night_str))
                print("  Explanation : {}".format(expl))
                print("-" * 70)

            _last_risk[pid]          = risk
            _last_score_bracket[pid] = score_bracket

            # ── Draw ───────────────────────────────────────────
            col = _risk_colour(risk)
            cv2.rectangle(frame,(int(x1),int(y1)),(int(x2),int(y2)),col,2)

            # Score bar — visual continuous score indicator
            bar_w = int((min(score, 100) / 100) * (int(x2)-int(x1)))
            cv2.rectangle(frame,
                          (int(x1), int(y2)+2),
                          (int(x1)+bar_w, int(y2)+8), col, -1)

            cv2.putText(frame,"P{} {} ({})".format(pid,risk,score),
                        (int(x1),int(y1)-8),
                        cv2.FONT_HERSHEY_SIMPLEX,0.55,col,2)

            # Top anomaly tag
            names = bt.get_names()
            if names:
                cv2.putText(frame,"! "+names[0],
                            (int(x1),int(y1)-24),
                            cv2.FONT_HERSHEY_SIMPLEX,0.42,(0,0,255),1)
                if len(names) > 1:
                    cv2.putText(frame,"! "+names[1],
                                (int(x1),int(y1)-40),
                                cv2.FONT_HERSHEY_SIMPLEX,0.38,(0,0,200),1)

            # Loiter / peripheral timer
            if in_zone and ls > 0:
                cv2.putText(frame,"Zone:{:.0f}s".format(ls),
                            (int(x1),int(y2)+20),
                            cv2.FONT_HERSHEY_SIMPLEX,0.4,col,1)
            elif near_zone and peripheral_seconds > 5:
                cv2.putText(frame,"Periph:{:.0f}s".format(peripheral_seconds),
                            (int(x1),int(y2)+20),
                            cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,165,255),1)

            # Object label
            if bt.carrying_object:
                cv2.putText(frame,"[{}]".format(bt.carrying_label),
                            (int(x1),int(y2)+35),
                            cv2.FONT_HERSHEY_SIMPLEX,0.38,(0,100,255),1)

        if crowd_count >= 2:
            cv2.putText(frame,"! CROWD: {} persons".format(crowd_count),
                        (10,75),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,0,255),2)

        loiter.cleanup_absent(active_ids)
        for pid in list(_peripheral_start.keys()):
            if pid not in active_ids:
                _peripheral_start.pop(pid, None)

        zone.draw(frame)

       # import detection.threat_engine as te
        #night_label = "NIGHT x1.5" if te.is_night_time() else "DAY"
        #hud = "Mode:{}  People:{}  {}  [{}]".format(
         #   mode.upper(), crowd_count,
          #  datetime.datetime.now().strftime("%H:%M:%S"), night_label)
        import detection.threat_engine as te
        night_label = "NIGHT x1.5" if te.is_night_time() else "DAY"
        hud = "Mode:{}  People:{}  {}  [{}]  FPS:{:.0f}".format(
              mode.upper(), crowd_count,
               datetime.datetime.now().strftime("%H:%M:%S"), night_label, fps_measured)


        cv2.putText(frame,hud,(10,28),
                    cv2.FONT_HERSHEY_SIMPLEX,0.65,(0,255,255),2)
        lbl = "FILE:"+video_file if mode=="demo" else "WEBCAM LIVE"
        clr = (100,200,255) if mode=="demo" else (0,220,100)
        cv2.putText(frame,lbl,(10,52),cv2.FONT_HERSHEY_SIMPLEX,0.45,clr,1)

        with _lock:
            _current_status["mode"]           = mode
            _current_status["active_persons"] = crowd_count
            _current_status["threats"]        = frame_threats
            _current_status["latest_alert"]   = fetch_latest_alert()
            _current_status["video_file"]     = video_file

        cv2.imshow("ThreatSense [{}]".format(mode.upper()), frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            stop.set()
            break
        time.sleep(0.01)

    cap.release()
    cv2.destroyAllWindows()
    print("[Detection] Stopped. Persons seen:", len(_seen_pids))


def start_detection(mode, video_file):
    global _detection_thread, _stop_event, _mode, _video_file

    _mode = mode
    _video_file = video_file

    # Sync night rule
    _sync_night_mode(mode)

    # Stop previous thread if running
    if _detection_thread and _detection_thread.is_alive():
        _stop_event.set()
        _detection_thread.join(timeout=5)

    _stop_event = threading.Event()

    _detection_thread = threading.Thread(
        target=_detection_loop,
        args=(_mode, _video_file, _stop_event),
        daemon=True
    )

    _detection_thread.start()

    print("[Startup] Detection thread started → Mode:{} | Video:{}".format(mode, video_file))




if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="ThreatSense AI-DVR")
    parser.add_argument("--mode",  choices=["live", "demo"], default=None)
    parser.add_argument("--video", default=None)
    parser.add_argument("--host",  default="0.0.0.0")
    parser.add_argument("--port",  type=int, default=5000)
    args = parser.parse_args()

    print("=" * 60)
    print("  ThreatSense AI-DVR — Startup")
    print("=" * 60)

    # ── Interactive mode selection ─────────────────────
    if args.mode is None:
        print("\n  Select Mode:")
        print("  [1] LIVE  — Webcam")
        print("  [2] DEMO  — Video file")
        choice = input("\n  Enter 1 or 2: ").strip()
        args.mode = "live" if choice == "1" else "demo"

    # ── Interactive video selection ────────────────────
    if args.mode == "demo" and args.video is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vdir     = os.path.join(base_dir, "videos")

        if not os.path.isdir(vdir):
            print("ERROR: videos/ folder not found.")
            sys.exit(1)

        videos = sorted([f for f in os.listdir(vdir) if f.endswith(".mp4")])

        if not videos:
            print("ERROR: No .mp4 files found in videos/ folder.")
            sys.exit(1)

        print("\n  Available Demo Videos:")
        for i, v in enumerate(videos, 1):
            print("  [{}] {}".format(i, v))

        while True:
            choice = input("\n  Enter video number (1-{}): ".format(len(videos))).strip()
            if choice.isdigit() and 1 <= int(choice) <= len(videos):
                args.video = videos[int(choice) - 1]
                break
            print("Invalid choice. Try again.")

    if args.video is None:
        args.video = "demo1.mp4"

    print("\n" + "=" * 60)
    print("  ThreatSense AI-DVR")
    print("  Mode  :", args.mode.upper())

    if args.mode == "demo":
        print("  Video :", args.video)
        print("  Night : AUTO FORCED ON (demo videos are night footage)")
    else:
        print("  Video : WEBCAM (index 0)")
        print("  Night : REAL CLOCK")

    print("  API   : http://127.0.0.1:{}".format(args.port))
    print("=" * 60)

    init_db()

   
    start_detection(args.mode, args.video)

    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)