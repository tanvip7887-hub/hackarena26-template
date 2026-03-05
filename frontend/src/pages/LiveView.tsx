import { usePolling }       from "../hooks/usePolling";
import { getCurrentStatus } from "../api/client";
import ThreatFeed           from "../components/ThreatFeed";
import VideoSelector        from "../components/VideoSelector";

export default function LiveView() {
  const { data: status } = usePolling(getCurrentStatus, 800);
  const threats = status?.threats ?? [];

  // ── Derived counts ────────────────────────────────────────────
  const highRisk        = threats.filter(t => t.risk_level === "High").length;
  const inZone          = threats.filter(t => t.in_zone).length;
  const loitering       = threats.filter(t => t.loiter_seconds > 0).length;
  const gunsDetected    = threats.filter(t => t.gun_detected).length;
  const weaponsDetected = threats.filter(t => t.weapon_detected && !t.gun_detected).length;
  const unattended      = threats.filter(
    t => t.person_id === -1 || t.explanation?.toLowerCase().includes("unattended")
  ).length;

  // Flash red border when gun is active
  const gunActive = gunsDetected > 0;

  return (
    <div className="p-6 space-y-4">

      {/* ── Page header ── */}
      <div className="flex items-center justify-between">
        <h2 className="font-head text-2xl font-black text-text-bright tracking-wide">
          Live View
        </h2>
        <div className="flex items-center gap-2 text-xs font-mono text-green">
          <span className="pulse w-2 h-2 rounded-full bg-green inline-block" />
          REAL-TIME — {status?.active_persons ?? 0} PERSONS
        </div>
      </div>

      {/* ── Gun alert banner (full width, only when active) ── */}
      {gunActive && (
        <div className="flex items-center gap-3 rounded border border-danger bg-danger/10
                        px-5 py-3 animate-pulse">
          <span className="text-2xl">🔴</span>
          <div>
            <p className="font-head font-black text-danger tracking-widest text-sm">
              GUN DETECTED — ALERT SECURITY IMMEDIATELY
            </p>
            <p className="text-xs font-mono text-danger/70 mt-0.5">
              {gunsDetected} armed person{gunsDetected > 1 ? "s" : ""} detected in scene
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-4">

        {/* ── Main panel ── */}
        <div className="col-span-2 space-y-4">

          {/* Camera feed placeholder */}
          <div className={`bg-bg2 border rounded-lg overflow-hidden
            ${gunActive ? "border-danger" : "border-border"}`}>
            <div className="flex items-center justify-between px-4 py-2 border-b border-border">
              <div className="flex items-center gap-2">
                <span className="pulse w-2 h-2 rounded-full bg-danger inline-block" />
                <span className="font-mono text-sm text-text-bright">
                  {status?.mode === "live" ? "WEBCAM — LIVE" : `FILE: ${status?.video_file}`}
                </span>
              </div>
              <span className="text-xs font-mono text-text-dim">
                MODE: {status?.mode?.toUpperCase()}
              </span>
            </div>

            <div className="relative bg-bg h-72 flex flex-col items-center justify-center gap-3">
              <div className="w-16 h-16 border-2 border-green/30 rounded-full flex items-center justify-center">
                <div className="w-6 h-6 border-2 border-green rounded-full pulse" />
              </div>
              <p className="font-mono text-xs text-text-dim text-center px-8">
                OpenCV detection window is running separately.<br />
                This dashboard shows real-time threat data from the backend.
              </p>
              <p className="font-mono text-xs text-cyan">
                http://127.0.0.1:5000 ● CONNECTED
              </p>
            </div>
          </div>

          {/* Threat cards */}
          <div className="bg-bg2 border border-border rounded-lg p-4">
            <div className="text-xs font-mono text-text-dim mb-3 tracking-widest">
              DETECTION RESULTS — FRAME ANALYSIS
            </div>
            <ThreatFeed threats={threats} />
          </div>
        </div>

        {/* ── Right panel ── */}
        <div className="space-y-4">

          {/* Live analytics */}
          <div className="bg-bg2 border border-border rounded-lg p-4 space-y-3">
            <div className="text-xs font-mono text-text-dim tracking-widest">
              LIVE ANALYTICS
            </div>

            {[
              { label: "Active Persons",  value: status?.active_persons ?? 0, color: "cyan"   },
              { label: "High Risk",       value: highRisk,                     color: "danger" },
              { label: "In Zone",         value: inZone,                       color: "amber"  },
              { label: "Loitering",       value: loitering,                    color: "green"  },
            ].map(({ label, value, color }) => (
              <div key={label}
                className="flex justify-between items-center border-b border-border pb-2">
                <span className="text-xs font-mono text-text-dim">{label}</span>
                <span className={`font-head text-xl font-bold text-${color}`}>{value}</span>
              </div>
            ))}

            {/* ── NEW: Weapon / Gun / Unattended counters ── */}
            <div className="pt-1 border-t border-border space-y-2">
              <div className="text-xs font-mono text-text-dim tracking-widest pt-1">
                THREAT OBJECTS
              </div>

              <div className="flex justify-between items-center">
                <span className="text-xs font-mono text-text-dim flex items-center gap-1">
                  🔴 Guns Detected
                </span>
                <span className={`font-head text-xl font-bold
                  ${gunsDetected > 0 ? "text-danger animate-pulse" : "text-text-dim"}`}>
                  {gunsDetected}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-xs font-mono text-text-dim flex items-center gap-1">
                  🔪 Weapons (Knife)
                </span>
                <span className={`font-head text-xl font-bold
                  ${weaponsDetected > 0 ? "text-orange-400" : "text-text-dim"}`}>
                  {weaponsDetected}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-xs font-mono text-text-dim flex items-center gap-1">
                  🟠 Unattended Obj
                </span>
                <span className={`font-head text-xl font-bold
                  ${unattended > 0 ? "text-orange-400" : "text-text-dim"}`}>
                  {unattended}
                </span>
              </div>
            </div>
          </div>

          {/* Video switcher */}
          <VideoSelector />

          {/* Latest alert */}
          {status?.latest_alert && (
            <div className="bg-danger/5 border border-danger/30 rounded-lg p-4">
              <div className="text-xs font-mono text-danger mb-2 tracking-widest">
                LATEST ALERT
              </div>

              {/* Person ID + risk */}
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-mono text-cyan">
                  {status.latest_alert.person_id === -1
                    ? "SCENE"
                    : `P${status.latest_alert.person_id}`}
                </span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded border
                  ${status.latest_alert.risk_level === "High"
                    ? "text-danger border-danger/40 bg-danger/10"
                    : status.latest_alert.risk_level === "Medium"
                    ? "text-amber border-amber/40 bg-amber/10"
                    : "text-green border-green/40 bg-green/10"}`}>
                  {status.latest_alert.risk_level?.toUpperCase()}
                </span>
              </div>

              <p className="text-xs font-mono text-text-dim leading-relaxed">
                {status.latest_alert.explanation}
              </p>

              <div className="mt-2 font-head text-2xl font-black text-danger">
                {status.latest_alert.threat_score}
                <span className="text-xs text-text-dim ml-1 font-mono">/ 100</span>
              </div>

              <div className="text-xs font-mono text-text-dim mt-1">
                {status.latest_alert.timestamp}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}  liveview.tsx