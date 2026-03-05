import type { Threat } from "../types";

const riskStyle = {
  Low:    "text-green  bg-green/10  border-green/30",
  Medium: "text-amber  bg-amber/10  border-amber/30",
  High:   "text-danger bg-danger/10 border-danger/30",
};

export default function ThreatFeed({ threats }: { threats: Threat[] }) {
  // Only show person-level threats (not scene-level id=-1)
  const personThreats = threats.filter(t => t.person_id >= 0);

  if (!personThreats.length) return (
    <div className="text-center text-text-dim font-mono text-xs py-8">
      NO ACTIVE THREATS DETECTED
    </div>
  );

  return (
    <div className="space-y-2">
      {personThreats.map(t => (
        <div key={t.person_id}
          className={`rounded border px-4 py-3 flex items-start gap-4
            ${t.gun_detected
              ? "border-danger bg-danger/10 ring-1 ring-danger/30"
              : t.weapon_detected
              ? "border-orange-500 bg-orange-500/10"
              : t.risk_level === "High"
              ? "border-danger/40 bg-danger/5"
              : t.risk_level === "Medium"
              ? "border-amber/30 bg-amber/5"
              : "border-border bg-bg3"}`}>

          {/* Risk badge */}
          <span className={`text-xs font-head px-2 py-0.5 rounded border font-bold shrink-0
            ${riskStyle[t.risk_level]}`}>
            {t.risk_level.toUpperCase()}
          </span>

          {/* Details */}
          <div className="flex-1 min-w-0">

            {/* Top row */}
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <span className="font-mono text-sm text-cyan">P{t.person_id}</span>

              <span className="text-xs text-text-dim">
                Score: <span className="text-text-bright font-bold">{t.threat_score}</span>
              </span>

              {/* ── Weapon / Gun badges ── */}
              {t.gun_detected && (
                <span className="inline-flex items-center gap-1 text-xs font-mono font-bold
                                 text-white bg-danger px-2 py-0.5 rounded animate-pulse">
                  🔴 GUN
                </span>
              )}
              {t.weapon_detected && !t.gun_detected && (
                <span className="inline-flex items-center gap-1 text-xs font-mono font-bold
                                 text-white bg-orange-600 px-2 py-0.5 rounded">
                  🔪 KNIFE
                </span>
              )}

              {t.in_zone && (
                <span className="text-xs text-danger font-mono">⚠ IN ZONE</span>
              )}
              {t.near_zone && !t.in_zone && (
                <span className="text-xs text-amber font-mono">NEAR ZONE</span>
              )}
              {t.loiter_seconds > 0 && (
                <span className="text-xs text-amber font-mono">
                  Loiter: {t.loiter_seconds.toFixed(0)}s
                </span>
              )}
              {t.peripheral_seconds > 5 && (
                <span className="text-xs text-amber/70 font-mono">
                  Periph: {t.peripheral_seconds.toFixed(0)}s
                </span>
              )}
              {t.crowd_count >= 2 && (
                <span className="text-xs text-orange-400 font-mono">
                  👥 {t.crowd_count}
                </span>
              )}
            </div>

            {/* Behaviour anomaly chips */}
            {t.behaviour_anomalies?.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-1">
                {t.behaviour_anomalies.map(b => (
                  <span key={b}
                    className="text-xs font-mono text-orange-400 bg-orange-400/10
                               border border-orange-400/20 px-1.5 py-0.5 rounded">
                    ! {b}
                  </span>
                ))}
              </div>
            )}

            {/* Explanation */}
            <p className="text-xs text-text-dim leading-relaxed truncate">
              {t.explanation}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}   


threatfeed.tsx