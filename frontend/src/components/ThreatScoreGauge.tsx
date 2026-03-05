interface Props { score: number; risk: "Low" | "Medium" | "High"; }

const riskColor = { Low: "#00ff88", Medium: "#ffaa00", High: "#ff3344" };

export default function ThreatScoreGauge({ score, risk }: Props) {

  const radius = 45;
  const circ = 2 * Math.PI * radius;

  const safeScore = Math.min(Math.max(score, 0), 100);
  const offset = circ - (safeScore / 100) * circ;
  const color = riskColor[risk];

  return (
    <div className="flex flex-col items-center">
      <div className="relative">
        <svg width="120" height="120" viewBox="0 0 120 120">

          <circle cx="60" cy="60" r={radius}
            fill="none" stroke="#1a2a35" strokeWidth="8" />

          <circle cx="60" cy="60" r={radius}
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circ}
            strokeDashoffset={offset}
            transform="rotate(-90 60 60)"
            style={{ transition: "stroke-dashoffset 0.8s ease" }}
          />

          <text x="60" y="55"
            textAnchor="middle"
            fill={color}
            fontSize="22"
            fontFamily="Orbitron"
            fontWeight="700">
            {safeScore}
          </text>

          <text x="60" y="72"
            textAnchor="middle"
            fill="#5a7a8a"
            fontSize="9"
            fontFamily="Share Tech Mono">
            THREAT SCORE
          </text>

        </svg>
      </div>

      <span className="font-head text-xs tracking-widest mt-1"
        style={{ color }}>
        {risk.toUpperCase()} RISK
      </span>
    </div>
  );
}  threatscoregauage.tsx