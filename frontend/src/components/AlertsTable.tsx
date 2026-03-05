import type { Alert } from "../types";

const riskBadge = {
  Low:    "text-green  border-green/40  bg-green/5",
  Medium: "text-amber  border-amber/40  bg-amber/5",
  High:   "text-danger border-danger/40 bg-danger/5",
};

// Score bar colour
function scoreColour(score: number) {
  if (score >= 80) return "bg-danger";
  if (score >= 36) return "bg-amber";
  return "bg-green";
}

export default function AlertsTable({ alerts }: { alerts: Alert[] }) {
  if (!alerts.length) return (
    <div className="text-center text-text-dim font-mono text-xs py-8">
      NO ALERTS LOGGED YET
    </div>
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs font-mono text-text-dim border-b border-border">
            <th className="text-left py-3 px-4">TIME</th>
            <th className="text-left py-3 px-4">PERSON</th>
            <th className="text-left py-3 px-4">ZONE</th>
            <th className="text-left py-3 px-4">LOITER</th>
            <th className="text-left py-3 px-4">SCORE</th>
            <th className="text-left py-3 px-4">RISK</th>
            <th className="text-left py-3 px-4">EXPLANATION</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((a, i) => {
            // Detect weapon/gun/unattended from explanation text
            const isGun        = a.explanation?.toLowerCase().includes("gun");
            const isWeapon     = a.explanation?.toLowerCase().includes("weapon") ||
                                 a.explanation?.toLowerCase().includes("knife");
            const isUnattended = a.explanation?.toLowerCase().includes("unattended") ||
                                 a.zone_name === "unattended_object" ||
                                 a.zone_name === "unattended_gun";
            const isScene      = a.person_id === -1;

            return (
              <tr key={a.id ?? i}
                className={`border-b border-border/50 transition-colors
                  ${isGun        ? "bg-danger/5   hover:bg-danger/10"
                  : isWeapon     ? "bg-orange-500/5 hover:bg-orange-500/10"
                  : isUnattended ? "bg-orange-400/5 hover:bg-orange-400/10"
                  : "hover:bg-bg3"}`}>

                <td className="py-3 px-4 font-mono text-xs text-text-dim">
                  {new Date(a.timestamp).toLocaleTimeString()}
                </td>

                {/* Person — show SCENE for id=-1 */}
                <td className="py-3 px-4 font-mono">
                  {isScene
                    ? <span className="text-orange-400 text-xs">SCENE</span>
                    : <span className="text-cyan">P{a.person_id}</span>
                  }
                </td>

                {/* Zone — with weapon/unattended icon */}
                <td className="py-3 px-4 text-text-dim text-xs">
                  <div className="flex items-center gap-1">
                    {isGun        && <span title="Gun detected">🔴</span>}
                    {isWeapon && !isGun && <span title="Weapon detected">🔪</span>}
                    {isUnattended && <span title="Unattended object">🟠</span>}
                    <span>{a.zone_name ?? "—"}</span>
                  </div>
                </td>

                <td className="py-3 px-4 font-mono text-xs">
                  {/* backend sends loiter_time, not loiter_sec */}
                  {a.loiter_time != null ? `${a.loiter_time.toFixed(1)}s` : "—"}
                </td>

                {/* Score with mini bar */}
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-text-bright w-8">
                      {/* backend sends threat_score, not score */}
                      {a.threat_score}
                    </span>
                    <div className="w-16 h-1.5 bg-bg3 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${scoreColour(a.threat_score)}`}
                        style={{ width: `${Math.min(a.threat_score, 100)}%` }}
                      />
                    </div>
                  </div>
                </td>

                <td className="py-3 px-4">
                  {/* backend sends risk_level, not risk */}
                  <span className={`text-xs font-head px-2 py-0.5 rounded border
                    ${riskBadge[a.risk_level] ?? riskBadge["Low"]}`}>
                    {a.risk_level === "Medium" ? "MED" : a.risk_level?.toUpperCase()}
                  </span>
                </td>

                <td className="py-3 px-4 text-xs text-text-dim max-w-xs truncate">
                  {a.explanation}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}