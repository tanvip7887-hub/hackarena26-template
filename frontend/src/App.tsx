import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import { useState, useEffect, useRef } from "react";
import axios from "axios";
import {
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  PieChart, Pie, Cell, AreaChart, Area, BarChart, Bar
} from "recharts";

// ─── TYPES ───────────────────────────────────────────────────────
interface Threat {
  person_id:           number;
  in_zone:             boolean;
  near_zone:           boolean;
  loiter_seconds:      number;
  peripheral_seconds:  number;
  crowd_count:         number;
  behaviour_anomalies: string[];
  threat_score:        number;
  risk_level:          "Low"|"Medium"|"High";
  explanation:         string;
}
interface Alert {
  id:           number;
  timestamp:    string;
  person_id:    number;
  zone_name:    string;
  loiter_time:  number;
  threat_score: number;
  risk_level:   "Low"|"Medium"|"High";
  explanation:  string;
}
interface CurrentStatus {
  mode:           "live"|"demo";
  active_persons: number;
  threats:        Threat[];
  latest_alert:   Alert|null;
  video_file:     string;
}

// ─── API ─────────────────────────────────────────────────────────
const BASE = "http://127.0.0.1:5000";
const api = {
  getStatus: () => axios.get<{status:string;data:CurrentStatus}>(`${BASE}/current_status`).then(r=>r.data.data),
  getAlerts: () => axios.get<{status:string;count:number;alerts:Alert[]}>(`${BASE}/alerts`).then(r=>r.data),
  getVideos: () => axios.get<{status:string;videos:string[]}>(`${BASE}/videos`).then(r=>r.data.videos),
  setMode:   (mode:"live"|"demo", video?:string) => axios.post(`${BASE}/set_mode`,{mode,video}).then(r=>r.data),
};

// ─── POLLING ─────────────────────────────────────────────────────
function usePolling<T>(fetcher:()=>Promise<T>, interval=1000) {
  const [data,    setData]    = useState<T|null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(false);
  const timer = useRef<ReturnType<typeof setInterval>|null>(null);
  const run = async () => {
    try { setData(await fetcher()); setError(false); }
    catch { setError(true); }
    finally { setLoading(false); }
  };
  useEffect(() => {
    run();
    timer.current = setInterval(run, interval);
    return () => { if (timer.current) clearInterval(timer.current); };
  }, [interval]);
  return { data, loading, error };
}

// ─── DESIGN SYSTEM ───────────────────────────────────────────────
// Palantir-inspired: slate dark, no glow, sharp lines, clear type
const C = {
  // Backgrounds - layered slate
  bg:       "#0b0e13",
  surface:  "#111520",
  card:     "#161b26",
  cardHov:  "#1c2333",
  border:   "#242d3d",
  border2:  "#2d3a50",

  // Text
  textPrim: "#e8edf5",
  textSec:  "#8a96aa",
  textDim:  "#4a5568",
  textMute: "#2d3748",

  // Accents — restrained, purposeful
  blue:     "#3b82f6",
  blueL:    "#60a5fa",
  green:    "#10b981",
  greenL:   "#34d399",
  amber:    "#f59e0b",
  amberL:   "#fbbf24",
  red:      "#ef4444",
  redL:     "#f87171",

  // Status
  online:   "#10b981",
} as const;

const risk = {
  color:  { Low: C.green,  Medium: C.amber,  High: C.red   },
  light:  { Low: C.greenL, Medium: C.amberL, High: C.redL  },
  bg:     { Low: "rgba(16,185,129,0.08)",  Medium: "rgba(245,158,11,0.08)",  High: "rgba(239,68,68,0.08)"  },
  border: { Low: "rgba(16,185,129,0.2)",   Medium: "rgba(245,158,11,0.2)",   High: "rgba(239,68,68,0.25)"  },
  label:  { Low: "LOW",    Medium: "MED",    High: "HIGH"  },
};

// ─── SHARED COMPONENTS ───────────────────────────────────────────

function Tag({ level }: { level: "Low"|"Medium"|"High" }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center",
      padding: "2px 8px", borderRadius: 4,
      fontFamily: "'DM Mono',monospace", fontSize: 10, fontWeight: 500,
      letterSpacing: "0.08em",
      color: risk.color[level],
      background: risk.bg[level],
      border: `1px solid ${risk.border[level]}`,
    }}>{risk.label[level]}</span>
  );
}

function Divider() {
  return <div style={{ height: 1, background: C.border, margin: "0" }} />;
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontFamily: "'DM Mono',monospace", fontSize: 10,
      color: C.textDim, letterSpacing: "0.12em",
      textTransform: "uppercase", marginBottom: 14,
    }}>{children}</div>
  );
}

function Card({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      background: C.card, border: `1px solid ${C.border}`,
      borderRadius: 8, overflow: "hidden", ...style,
    }}>{children}</div>
  );
}

function CardHeader({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      padding: "12px 18px", borderBottom: `1px solid ${C.border}`,
      display: "flex", justifyContent: "space-between", alignItems: "center",
    }}>{children}</div>
  );
}

function CardBody({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <div style={{ padding: "16px 18px", ...style }}>{children}</div>;
}

// ─── STAT CARD ───────────────────────────────────────────────────
function StatCard({ label, value, color, delta }: {
  label: string; value: number|string; color: string; delta?: string;
}) {
  return (
    <Card>
      <CardBody>
        <div style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
          color: C.textDim, letterSpacing: "0.1em", marginBottom: 10 }}>{label}</div>
        <div style={{ fontFamily: "'DM Sans',sans-serif", fontSize: 32,
          fontWeight: 700, color, lineHeight: 1, marginBottom: delta?6:0 }}>{value}</div>
        {delta && (
          <div style={{ fontFamily: "'DM Mono',monospace", fontSize: 10, color: C.textDim }}>{delta}</div>
        )}
      </CardBody>
    </Card>
  );
}

// ─── THREAT GAUGE ────────────────────────────────────────────────
function ThreatGauge({ score, riskLevel }: { score: number; riskLevel: "Low"|"Medium"|"High" }) {
  const pct  = Math.min(score / 100, 1);
  const col  = risk.color[riskLevel];
  const half = 163.4; // half circumference of r=52 arc

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
      <svg width="160" height="96" viewBox="0 0 160 100">
        {/* Track */}
        <path d="M 24 78 A 56 56 0 0 1 136 78"
          fill="none" stroke={C.border2} strokeWidth="8" strokeLinecap="round"/>
        {/* Fill */}
        <path d="M 24 78 A 56 56 0 0 1 136 78"
          fill="none" stroke={col} strokeWidth="8" strokeLinecap="round"
          strokeDasharray={half} strokeDashoffset={half*(1-pct)}
          style={{ transition: "stroke-dashoffset 1s ease, stroke 0.3s" }}/>
        {/* Score */}
        <text x="80" y="68" textAnchor="middle" fill={C.textPrim}
          fontSize="26" fontFamily="'DM Sans',sans-serif" fontWeight="700">{score}</text>
        <text x="80" y="82" textAnchor="middle" fill={C.textDim}
          fontSize="9" fontFamily="'DM Mono',monospace" letterSpacing="1">/ 100</text>
      </svg>
      <div style={{
        fontFamily: "'DM Mono',monospace", fontSize: 11, fontWeight: 500,
        color: col, letterSpacing: "0.1em",
        padding: "4px 16px", borderRadius: 4,
        background: risk.bg[riskLevel], border: `1px solid ${risk.border[riskLevel]}`,
      }}>{riskLevel.toUpperCase()} RISK</div>
    </div>
  );
}

// ─── ML PROBABILITY CARD ─────────────────────────────────────────
function ThreatCard({ threat }: { threat: Threat }) {
  const col = risk.color[threat.risk_level];
  const pct = Math.min(threat.threat_score, 100);

  const factors = [
    { label: "Zone Entry",  val: threat.in_zone ? 40 : (threat.near_zone ? 15 : 0),
      max: 40, color: C.red,   info: threat.in_zone ? "Inside restricted zone" : threat.near_zone ? "Near zone boundary" : "Outside zone" },
    { label: "Loitering",   val: Math.min(((threat.loiter_seconds??0)/60)*35, 35),
      max: 35, color: C.amber, info: `${(threat.loiter_seconds??0).toFixed(0)}s in zone` },
    { label: "Behaviour",   val: Math.min((threat.behaviour_anomalies?.length??0)*12, 30),
      max: 30, color: C.blue,  info: `${threat.behaviour_anomalies?.length??0} anomaly flags` },
    { label: "Crowd",       val: threat.crowd_count > 1 ? Math.min(threat.crowd_count*5,20):0,
      max: 20, color: C.green, info: `${threat.crowd_count} persons detected` },
  ];

  return (
    <div style={{
      background: C.card, border: `1px solid ${C.border}`,
      borderLeft: `3px solid ${col}`,
      borderRadius: 6, padding: "14px 16px", marginBottom: 8,
      transition: "background 0.15s",
    }}
      onMouseEnter={e=>(e.currentTarget.style.background=C.cardHov)}
      onMouseLeave={e=>(e.currentTarget.style.background=C.card)}>

      {/* Header row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 13,
            color: C.blueL, fontWeight: 600 }}>P{threat.person_id}</span>
          <Tag level={threat.risk_level}/>
          {threat.in_zone && (
            <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
              color: C.redL, background: "rgba(239,68,68,0.1)",
              border: "1px solid rgba(239,68,68,0.2)", borderRadius: 3,
              padding: "1px 6px" }}>IN ZONE</span>
          )}
          {(threat.behaviour_anomalies?.length??0) > 0 && (
            <span style={{ fontSize: 11, color: C.amberL,
              fontFamily: "'DM Mono',monospace" }}>
              {threat.behaviour_anomalies[0]}
            </span>
          )}
        </div>
        <span style={{ fontFamily: "'DM Sans',sans-serif", fontSize: 22,
          fontWeight: 700, color: col }}>{threat.threat_score}</span>
      </div>

      {/* Overall bar */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
          <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 9,
            color: C.textDim, letterSpacing: "0.08em" }}>THREAT PROBABILITY</span>
          <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 9, color: col }}>{pct}%</span>
        </div>
        <div style={{ height: 5, background: C.border2, borderRadius: 3, overflow: "hidden" }}>
          <div style={{ height: "100%", width: `${pct}%`,
            background: col, borderRadius: 3,
            transition: "width 0.8s ease" }}/>
        </div>
      </div>
      
      {/* Factor breakdown */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 20px" }}>
        {factors.map(f => (
          <div key={f.label}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
              <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 9, color: C.textDim }}>{f.label}</span>
              <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 9, color: C.textSec }}>
                {f.val.toFixed(0)}<span style={{ color: C.textDim }}>/{f.max} · {f.info}</span>
              </span>
            </div>
            <div style={{ height: 3, background: C.border2, borderRadius: 2, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${(f.val/f.max)*100}%`,
                background: f.color, borderRadius: 2, transition: "width 0.5s ease" }}/>
            </div>
          </div>
        ))}
      </div>
      
      {/* Footer tags */}
      {(threat.loiter_seconds > 0 || (threat.peripheral_seconds??0) > 0) && (
        <div style={{ display: "flex", gap: 12, marginTop: 10,
          fontFamily: "'DM Mono',monospace", fontSize: 10, color: C.textDim }}>
          {threat.loiter_seconds > 0 &&
            <span>Loiter <span style={{ color: C.amberL }}>{threat.loiter_seconds.toFixed(0)}s</span></span>}
          {(threat.peripheral_seconds??0) > 0 &&
            <span>Perimeter <span style={{ color: C.blueL }}>{(threat.peripheral_seconds??0).toFixed(0)}s</span></span>}
          <span>Crowd <span style={{ color: C.textSec }}>{threat.crowd_count}</span></span>
        </div>
      )}
    </div>
  );
}

// ─── BEHAVIOUR RADAR ─────────────────────────────────────────────
function BehaviourRadar({ threat }: { threat: Threat }) {
  const col = risk.color[threat.risk_level];
  const data = [
    { axis: "Zone",      val: threat.in_zone ? 100 : (threat.near_zone ? 45 : 0) },
    { axis: "Loiter",    val: Math.min(((threat.loiter_seconds??0)/60)*100, 100) },
    { axis: "Speed",     val: threat.behaviour_anomalies?.some(b=>b.includes("SPRINT"))?90:threat.behaviour_anomalies?.some(b=>b.includes("RUN"))?55:8 },
    { axis: "Crowd",     val: Math.min(((threat.crowd_count??1)/5)*100, 100) },
    { axis: "Behaviour", val: Math.min((threat.behaviour_anomalies?.length??0)*20, 100) },
    { axis: "Perimeter", val: Math.min(((threat.peripheral_seconds??0)/30)*100, 100) },
  ];
  return (
    <div>
      <ResponsiveContainer width="100%" height={170}>
        <RadarChart data={data} margin={{ top:10, right:28, bottom:10, left:28 }}>
          <PolarGrid stroke={C.border2}/>
          <PolarAngleAxis dataKey="axis"
            tick={{ fill: C.textSec, fontSize: 9, fontFamily: "'DM Mono',monospace" }}/>
          <PolarRadiusAxis domain={[0,100]} tick={false} axisLine={false}/>
          <Radar dataKey="val" stroke={col} fill={col} fillOpacity={0.12} strokeWidth={1.5}/>
        </RadarChart>
      </ResponsiveContainer>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "3px 6px", marginTop: 4 }}>
        {data.map(d => (
          <div key={d.axis} style={{ display: "flex", justifyContent: "space-between",
            padding: "3px 8px", background: C.surface, borderRadius: 3,
            border: `1px solid ${C.border}` }}>
            <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 8, color: C.textDim }}>{d.axis}</span>
            <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 8, color: col, fontWeight: 600 }}>{d.val.toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── RISK PIE ─────────────────────────────────────────────────────
function RiskPie({ high, med, low }: { high:number; med:number; low:number }) {
  const total = high + med + low;
  if (total === 0) return (
    <div style={{ height: 110, display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: "'DM Mono',monospace", fontSize: 11, color: C.textDim }}>NO DATA</div>
  );
  const slices = [
    { name: "High",   value: high, color: C.red   },
    { name: "Medium", value: med,  color: C.amber  },
    { name: "Low",    value: low,  color: C.green  },
  ].filter(d => d.value > 0);

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
      <PieChart width={110} height={110}>
        <Pie data={slices} cx={50} cy={50} innerRadius={28} outerRadius={48}
          dataKey="value" paddingAngle={2} strokeWidth={0}>
          {slices.map((d,i) => <Cell key={i} fill={d.color}/>)}
        </Pie>
        <text x={55} y={47} textAnchor="middle" fill={C.textPrim}
          fontSize="14" fontFamily="'DM Sans',sans-serif" fontWeight="700">{total}</text>
        <text x={55} y={59} textAnchor="middle" fill={C.textDim}
          fontSize="8" fontFamily="'DM Mono',monospace">total</text>
      </PieChart>
      <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
        {slices.map(d => (
          <div key={d.name} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 6, height: 6, borderRadius: 1, background: d.color, flexShrink: 0 }}/>
            <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
              color: C.textSec, minWidth: 46 }}>{d.name}</span>
            <span style={{ fontFamily: "'DM Sans',sans-serif", fontSize: 14,
              fontWeight: 700, color: d.color }}>{d.value}</span>
            <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 9,
              color: C.textDim }}>({Math.round((d.value/total)*100)}%)</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── VIDEO SELECTOR ──────────────────────────────────────────────
function VideoSelector() {
  const [videos,  setVideos]  = useState<string[]>([]);
  const [current, setCurrent] = useState("demo1.mp4");
  const [busy,    setBusy]    = useState(false);
  useEffect(() => { api.getVideos().then(setVideos); }, []);
  const switchTo = async (mode:"live"|"demo", video?:string) => {
    setBusy(true);
    try { await api.setMode(mode,video); setCurrent(video??"LIVE"); }
    finally { setBusy(false); }
  };
  return (
    <Card>
      <CardHeader>
        <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
          color: C.textDim, letterSpacing: "0.1em" }}>VIDEO SOURCE</span>
        {busy && <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
          color: C.amberL }}>switching…</span>}
      </CardHeader>
      <CardBody>
        <button onClick={() => switchTo("live")} disabled={busy} style={{
          width: "100%", marginBottom: 8, padding: "9px 14px",
          borderRadius: 5, cursor: "pointer",
          fontFamily: "'DM Mono',monospace", fontSize: 11, letterSpacing: "0.05em",
          background: current === "LIVE" ? C.green : "transparent",
          color:      current === "LIVE" ? "#fff"  : C.textSec,
          border:     current === "LIVE" ? "none"  : `1px solid ${C.border2}`,
          textAlign: "left", transition: "all 0.15s",
        }}>
          <span style={{ marginRight: 8, opacity: 0.7 }}>●</span>
          Webcam Live
        </button>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {videos.map(v => (
            <button key={v} onClick={() => switchTo("demo",v)} disabled={busy} style={{
              padding: "8px 14px", borderRadius: 5, cursor: "pointer",
              fontFamily: "'DM Mono',monospace", fontSize: 11,
              background: current === v ? "rgba(59,130,246,0.1)" : "transparent",
              color:      current === v ? C.blueL : C.textDim,
              border:     current === v ? `1px solid rgba(59,130,246,0.3)` : `1px solid ${C.border}`,
              textAlign: "left", transition: "all 0.15s",
            }}>{v.replace(".mp4","")}</button>
          ))}
        </div>
      </CardBody>
    </Card>
  );
}

// ─── NAVBAR ──────────────────────────────────────────────────────
function Navbar() {
  const { pathname } = useLocation();
  const links = [
    { to: "/",        label: "Dashboard"  },
    { to: "/live",    label: "Live View"  },
    { to: "/alerts",  label: "Alerts"     },
    { to: "/history", label: "History"    },
  ];
  return (
    <nav style={{
      height: 52, display: "flex", alignItems: "center",
      justifyContent: "space-between", padding: "0 24px",
      background: C.surface, borderBottom: `1px solid ${C.border}`,
      position: "sticky", top: 0, zIndex: 100,
    }}>
      {/* Logo */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ width: 28, height: 28, background: C.blue,
          borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L3 7v5c0 5.5 3.8 10.2 9 11.4C17.2 22.2 21 17.5 21 12V7L12 2z"
              fill="white" opacity=".95"/>
            <path d="M9 12l2 2 4-4" stroke={C.blue} strokeWidth="2.5"
              strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <div>
          <div style={{ fontFamily: "'DM Sans',sans-serif", fontSize: 14,
            fontWeight: 700, color: C.textPrim, letterSpacing: "0.02em" }}>
            ThreatSense <span style={{ color: C.blue }}>AI</span>
          </div>
          <div style={{ fontFamily: "'DM Mono',monospace", fontSize: 8,
            color: C.textDim, letterSpacing: "0.1em" }}>SURVEILLANCE PLATFORM</div>
        </div>
      </div>

      {/* Nav links */}
      <div style={{ display: "flex", gap: 2 }}>
        {links.map(({ to, label }) => {
          const active = pathname === to;
          return (
            <Link key={to} to={to} style={{
              padding: "5px 14px", borderRadius: 5, textDecoration: "none",
              fontFamily: "'DM Sans',sans-serif", fontSize: 13, fontWeight: active ? 600 : 400,
              color:      active ? C.textPrim : C.textSec,
              background: active ? C.card    : "transparent",
              border:     active ? `1px solid ${C.border}` : "1px solid transparent",
              transition: "all 0.15s",
            }}>{label}</Link>
          );
        })}
      </div>

      {/* Status */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6,
          padding: "4px 10px", borderRadius: 4,
          background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.2)" }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%",
            background: C.online, animation: "blink 2s infinite" }}/>
          <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
            color: C.online, letterSpacing: "0.08em" }}>ONLINE</span>
        </div>
      </div>
    </nav>
  );
}

// ─── TOOLTIP STYLE ───────────────────────────────────────────────
const ttStyle = {
  contentStyle: { background: C.surface, border: `1px solid ${C.border}`,
    borderRadius: 6, fontFamily: "'DM Mono',monospace", fontSize: 10, padding: "8px 12px" },
  labelStyle:   { color: C.textSec, marginBottom: 4 },
  itemStyle:    { color: C.textPrim },
};

// ─── DASHBOARD ───────────────────────────────────────────────────
function Dashboard() {
  const { data: status, error } = usePolling(api.getStatus, 1000);
  const { data: alertsData }    = usePolling(api.getAlerts,  3000);
  const threats = status?.threats    ?? [];
  const alerts  = alertsData?.alerts ?? [];

  const topThreat = threats.reduce<{ score:number; risk:"Low"|"Medium"|"High" }>(
    (m,t) => t.threat_score > m.score ? { score: t.threat_score, risk: t.risk_level } : m,
    { score: 0, risk: "Low" }
  );
  const highCount = threats.filter(t => t.risk_level === "High").length;
  const medCount  = threats.filter(t => t.risk_level === "Medium").length;

  const trendData = alerts.slice(-20).map((a,i) => ({
    i, score: a.threat_score,
    time: new Date(a.timestamp).toLocaleTimeString([],{ hour:"2-digit", minute:"2-digit" }),
  }));

  const behaviourCounts: Record<string,number> = {};
  threats.forEach(t => t.behaviour_anomalies?.forEach(b => {
    const k = b.split(" ")[0];
    behaviourCounts[k] = (behaviourCounts[k]??0)+1;
  }));
  const behaviourData = Object.entries(behaviourCounts)
    .map(([name,count]) => ({ name, count }))
    .sort((a,b) => b.count - a.count).slice(0,6);

  return (
    <div style={{ padding: "20px 24px", maxWidth: 1440, margin: "0 auto" }}>

      {/* Page header */}
      <div style={{ display: "flex", justifyContent: "space-between",
        alignItems: "center", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontFamily: "'DM Sans',sans-serif", fontSize: 22,
            fontWeight: 700, color: C.textPrim, margin: 0 }}>Security Overview</h1>
          <div style={{ fontFamily: "'DM Mono',monospace", fontSize: 11,
            color: C.textDim, marginTop: 3 }}>
            Mode: <span style={{ color: C.textSec }}>{status?.mode?.toUpperCase()??"—"}</span>
            {status?.mode === "demo" &&
              <span style={{ color: C.textDim }}> · {status.video_file}</span>}
          </div>
        </div>
        {error && (
          <div style={{ padding: "8px 14px", borderRadius: 5,
            background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)",
            fontFamily: "'DM Mono',monospace", fontSize: 11, color: C.redL }}>
            ⚠ Backend unreachable
          </div>
        )}
      </div>

      {/* KPI row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginBottom: 16 }}>
        <StatCard label="ACTIVE PERSONS" value={status?.active_persons??0} color={C.blueL}/>
        <StatCard label="HIGH RISK"      value={highCount}                 color={C.redL}/>
        <StatCard label="MEDIUM RISK"    value={medCount}                  color={C.amberL}/>
        <StatCard label="TOTAL ALERTS"   value={alertsData?.count??0}      color={C.greenL}/>
      </div>
      
      {/* Main row */}
      <div style={{ display: "grid", gridTemplateColumns: "230px 1fr", gap: 12, marginBottom: 12 }}>

        {/* Gauge */}
        <Card style={{ display: "flex", flexDirection: "column" }}>
          <CardHeader>
            <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
              color: C.textDim, letterSpacing: "0.1em" }}>GLOBAL THREAT</span>
          </CardHeader>
          <CardBody style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <ThreatGauge score={topThreat.score} riskLevel={topThreat.risk}/>
          </CardBody>
        </Card>

        {/* Threat Feed */}
        <Card>
          <CardHeader>
            <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
              color: C.textDim, letterSpacing: "0.1em" }}>ACTIVE THREAT FEED</span>
            <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 11,
              color: threats.length > 0 ? C.amberL : C.textDim }}>
              {threats.length} detected
            </span>
          </CardHeader>
          <CardBody style={{ maxHeight: 300, overflowY: "auto", paddingTop: 12 }}>
            {threats.length === 0 ? (
              <div style={{ padding: "28px 0", textAlign: "center",
                fontFamily: "'DM Mono',monospace", fontSize: 12, color: C.textDim }}>
                No active threats
              </div>
            ) : threats.map(t => <ThreatCard key={t.person_id} threat={t}/>)}
          </CardBody>
        </Card>
      </div>

      {/* Bottom row */}
      <div style={{ display: "grid", gridTemplateColumns: "230px 1fr 260px", gap: 12 }}>
        <VideoSelector/>

        {/* Trend */}
        <Card>
          <CardHeader>
            <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
              color: C.textDim, letterSpacing: "0.1em" }}>THREAT SCORE TREND</span>
            <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
              color: C.textDim }}>last 20 alerts · Y = score (0–100)</span>
          </CardHeader>
          <CardBody>
            {trendData.length < 2 ? (
              <div style={{ height: 140, display: "flex", alignItems: "center",
                justifyContent: "center", fontFamily: "'DM Mono',monospace",
                fontSize: 11, color: C.textDim }}>Waiting for data…</div>
            ) : (
              <ResponsiveContainer width="100%" height={140}>
                <AreaChart data={trendData} margin={{ top:4, right:4, bottom:0, left:-10 }}>
                  <defs>
                    <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor={C.blue} stopOpacity={0.2}/>
                      <stop offset="95%" stopColor={C.blue} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke={C.border} strokeDasharray="4 4"/>
                  <XAxis dataKey="time" tick={{ fill:C.textDim, fontSize:9, fontFamily:"'DM Mono',monospace" }}
                    tickLine={false} interval="preserveStartEnd"/>
                  <YAxis domain={[0,100]} tick={{ fill:C.textDim, fontSize:9 }}
                    tickLine={false} axisLine={false}/>
                  <Tooltip {...ttStyle} formatter={(v:number|string|undefined)=>[`${v??0} pts`,"Score"]}/>
                  <Area type="monotone" dataKey="score" stroke={C.blue} strokeWidth={1.5}
                    fill="url(#g1)" dot={false} activeDot={{ r:4, fill:C.amber }}/>
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardBody>
        </Card>

        {/* Behaviours */}
        <Card>
          <CardHeader>
            <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
              color: C.textDim, letterSpacing: "0.1em" }}>BEHAVIOUR FLAGS</span>
          </CardHeader>
          <CardBody>
            {behaviourData.length === 0 ? (
              <div style={{ height: 140, display: "flex", alignItems: "center",
                justifyContent: "center", fontFamily: "'DM Mono',monospace",
                fontSize: 11, color: C.textDim }}>No anomalies</div>
            ) : (
              <ResponsiveContainer width="100%" height={140}>
                <BarChart data={behaviourData} layout="vertical" margin={{ top:0, right:0, bottom:0, left:-18 }}>
                  <CartesianGrid stroke={C.border} strokeDasharray="4 4" horizontal={false}/>
                  <XAxis type="number" tick={{ fill:C.textDim, fontSize:9 }} tickLine={false}/>
                  <YAxis type="category" dataKey="name"
                    tick={{ fill:C.textSec, fontSize:9, fontFamily:"'DM Mono',monospace" }}
                    tickLine={false} axisLine={false} width={60}/>
                  <Tooltip {...ttStyle} formatter={(v:number|string|undefined)=>[`${v??0} persons`,"Count"]}/>
                  <Bar dataKey="count" fill={C.amber} radius={[0,3,3,0]}
                    background={{ fill:C.border, radius:3 }}/>
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

// ─── LIVE VIEW ───────────────────────────────────────────────────
function LiveView() {
  const { data: status } = usePolling(api.getStatus, 800);
  const threats = status?.threats ?? [];
  const stats = [
    { label: "Active Persons", value: status?.active_persons??0,                               color: C.blueL  },
    { label: "High Risk",      value: threats.filter(t=>t.risk_level==="High").length,          color: C.redL   },
    { label: "In Zone",        value: threats.filter(t=>t.in_zone).length,                     color: C.amberL },
    { label: "Loitering",      value: threats.filter(t=>(t.loiter_seconds??0)>0).length,       color: C.greenL },
  ];
  
  return (
    <div style={{ padding: "20px 24px", maxWidth: 1440, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between",
        alignItems: "center", marginBottom: 20 }}>
        <h1 style={{ fontFamily: "'DM Sans',sans-serif", fontSize: 22,
          fontWeight: 700, color: C.textPrim, margin: 0 }}>Live View</h1>
        <div style={{ display: "flex", alignItems: "center", gap: 6,
          fontFamily: "'DM Mono',monospace", fontSize: 11, color: C.online }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%",
            background: C.online, animation: "blink 1.5s infinite" }}/>
          Real-time · {status?.active_persons??0} persons
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: 12 }}>
        {/* Left column */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>

          {/* Camera panel */}
          <Card>
            <CardHeader>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ width: 7, height: 7, borderRadius: "50%",
                  background: C.red, animation: "blink 1.5s infinite" }}/>
                <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 12,
                  color: C.textPrim }}>
                  {status?.mode === "live" ? "Webcam — Live" : `File: ${status?.video_file??"—"}`}
                </span>
              </div>
              <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
                color: C.textDim }}>Mode: {status?.mode?.toUpperCase()??"—"}</span>
            </CardHeader>
            <div style={{ height: 260, background: "#060a0f",
              display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center", gap: 16, position: "relative" }}>
              {/* Subtle grid */}
              <div style={{ position: "absolute", inset: 0, opacity: 0.04,
                backgroundImage: `linear-gradient(${C.border} 1px, transparent 1px), linear-gradient(90deg, ${C.border} 1px, transparent 1px)`,
                backgroundSize: "32px 32px" }}/>
              <div style={{ width: 56, height: 56,
                border: `1px solid ${C.border2}`, borderRadius: "50%",
                display: "flex", alignItems: "center", justifyContent: "center" }}>
                <div style={{ width: 20, height: 20,
                  border: `1.5px solid ${C.blue}`, borderRadius: "50%",
                  animation: "blink 2s infinite" }}/>
              </div>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontFamily: "'DM Mono',monospace", fontSize: 11,
                  color: C.textDim, lineHeight: 2 }}>
                  OpenCV detection window running separately<br/>
                  This dashboard shows real-time AI analysis
                </div>
                <div style={{ marginTop: 10, display: "inline-flex", alignItems: "center", gap: 6,
                  padding: "5px 14px", borderRadius: 4,
                  background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.2)",
                  fontFamily: "'DM Mono',monospace", fontSize: 11, color: C.blueL }}>
                  <div style={{ width: 6, height: 6, borderRadius: "50%", background: C.online }}/>
                  127.0.0.1:5000 connected
                </div>
              </div>
            </div>
          </Card>
          
          {/* ML Analysis */}
          <Card>
            <CardHeader>
              <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
                color: C.textDim, letterSpacing: "0.1em" }}>ML PROBABILITY BREAKDOWN</span>
              <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
                color: C.textDim }}>bar = overall % · sub-bars = factor contributions</span>
            </CardHeader>
            <CardBody style={{ maxHeight: 280, overflowY: "auto", paddingTop: 12 }}>
              {threats.length === 0 ? (
                <div style={{ padding: "24px 0", textAlign: "center",
                  fontFamily: "'DM Mono',monospace", fontSize: 12, color: C.textDim }}>
                  No active threats
                </div>
              ) : threats.map(t => <ThreatCard key={t.person_id} threat={t}/>)}
            </CardBody>
          </Card>
        </div>
        
        {/* Right column */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>

          {/* Live stats */}
          <Card>
            <CardHeader>
              <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
                color: C.textDim, letterSpacing: "0.1em" }}>LIVE ANALYTICS</span>
            </CardHeader>
            <CardBody style={{ padding: "8px 18px" }}>
              {stats.map(({ label, value, color }, i) => (
                <div key={label}>
                  <div style={{ display: "flex", justifyContent: "space-between",
                    alignItems: "center", padding: "10px 0" }}>
                    <span style={{ fontFamily: "'DM Mono',monospace",
                      fontSize: 11, color: C.textSec }}>{label}</span>
                    <span style={{ fontFamily: "'DM Sans',sans-serif",
                      fontSize: 22, fontWeight: 700, color }}>{value}</span>
                  </div>
                  {i < stats.length - 1 && <Divider/>}
                </div>
              ))}
            </CardBody>
          </Card>

          {/* Radar */}
          {threats[0] && (
            <Card>
              <CardHeader>
                <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
                  color: C.textDim, letterSpacing: "0.1em" }}>
                  P{threats[0].person_id} · BEHAVIOUR RADAR
                </span>
              </CardHeader>
              <CardBody>
                <BehaviourRadar threat={threats[0]}/>
              </CardBody>
            </Card>
          )}

          <VideoSelector/>

          {/* Latest alert */}
          {status?.latest_alert && (
            <Card style={{ borderLeft: `3px solid ${C.red}` }}>
              <CardHeader>
                <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
                  color: C.redL, letterSpacing: "0.1em" }}>LATEST ALERT</span>
                <Tag level={status.latest_alert.risk_level}/>
              </CardHeader>
              <CardBody>
                <p style={{ fontSize: 12, color: C.textSec, lineHeight: 1.7,
                  margin: 0, marginBottom: 12 }}>{status.latest_alert.explanation}</p>
                <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
                  <span style={{ fontFamily: "'DM Sans',sans-serif", fontSize: 30,
                    fontWeight: 700, color: C.redL }}>{status.latest_alert.threat_score}</span>
                  <span style={{ fontFamily: "'DM Mono',monospace",
                    fontSize: 10, color: C.textDim }}>/100 threat score</span>
                </div>
              </CardBody>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── ALERTS PAGE ─────────────────────────────────────────────────
function AlertsPage() {
  const { data, loading } = usePolling(api.getAlerts, 3000);
  const alerts = [...(data?.alerts??[])].reverse();
  const high = alerts.filter(a => a.risk_level === "High").length;
  const med  = alerts.filter(a => a.risk_level === "Medium").length;
  const low  = alerts.filter(a => a.risk_level === "Low").length;

  return (
    <div style={{ padding: "20px 24px", maxWidth: 1440, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between",
        alignItems: "flex-start", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontFamily: "'DM Sans',sans-serif", fontSize: 22,
            fontWeight: 700, color: C.textPrim, margin: 0 }}>Alert History</h1>
          <div style={{ fontFamily: "'DM Mono',monospace", fontSize: 11,
            color: C.textDim, marginTop: 3 }}>
            {data?.count??0} events logged
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {[
            { label: `${high} High`,   color: C.red   },
            { label: `${med} Medium`,  color: C.amber  },
            { label: `${low} Low`,     color: C.green  },
          ].map(({ label, color }) => (
            <div key={label} style={{ padding: "6px 14px", borderRadius: 5,
              background: C.card, border: `1px solid ${C.border}`,
              fontFamily: "'DM Mono',monospace", fontSize: 11, color }}>
              {label}
            </div>
          ))}
        </div>
      </div>

      <Card>
        {loading ? (
          <div style={{ padding: 40, textAlign: "center",
            fontFamily: "'DM Mono',monospace", fontSize: 12, color: C.textDim }}>Loading…</div>
        ) : alerts.length === 0 ? (
          <div style={{ padding: 60, textAlign: "center",
            fontFamily: "'DM Mono',monospace", fontSize: 12, color: C.textDim }}>
            No alerts recorded yet
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                  {["Time","Person","Zone","Loiter","Score","Risk","Explanation"].map(h => (
                    <th key={h} style={{ padding: "10px 16px", textAlign: "left",
                      fontFamily: "'DM Mono',monospace", fontSize: 9,
                      color: C.textDim, letterSpacing: "0.1em", fontWeight: 400 }}>{h.toUpperCase()}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {alerts.map((a, i) => (
                  <tr key={a.id??i}
                    style={{ borderBottom: `1px solid ${C.border}`, transition: "background 0.1s" }}
                    onMouseEnter={e => (e.currentTarget.style.background = C.cardHov)}
                    onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
                    <td style={{ padding: "10px 16px", fontFamily: "'DM Mono',monospace",
                      fontSize: 11, color: C.textDim, whiteSpace: "nowrap" }}>
                      {new Date(a.timestamp).toLocaleTimeString()}
                    </td>
                    <td style={{ padding: "10px 16px", fontFamily: "'DM Mono',monospace",
                      fontSize: 12, color: C.blueL, fontWeight: 600 }}>P{a.person_id}</td>
                    <td style={{ padding: "10px 16px", fontFamily: "'DM Mono',monospace",
                      fontSize: 11, color: C.textSec }}>{a.zone_name??"—"}</td>
                    <td style={{ padding: "10px 16px", fontFamily: "'DM Mono',monospace",
                      fontSize: 11, color: C.textSec }}>
                      {a.loiter_time != null ? `${Number(a.loiter_time).toFixed(1)}s` : "—"}
                    </td>
                    <td style={{ padding: "10px 16px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontFamily: "'DM Sans',sans-serif", fontWeight: 700,
                          fontSize: 15, color: risk.color[a.risk_level]??C.textSec }}>
                          {a.threat_score}
                        </span>
                        <div style={{ width: 48, height: 3, background: C.border2, borderRadius: 2 }}>
                          <div style={{ height: "100%", width: `${a.threat_score}%`,
                            background: risk.color[a.risk_level]??C.textSec, borderRadius: 2 }}/>
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: "10px 16px" }}>
                      <Tag level={a.risk_level}/>
                    </td>
                    <td style={{ padding: "10px 16px", fontSize: 12, color: C.textSec,
                      maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis",
                      whiteSpace: "nowrap" }}>{a.explanation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

// ─── HISTORY PAGE ────────────────────────────────────────────────
function HistoryPage() {
  const { data } = usePolling(api.getAlerts, 5000);
  const alerts = data?.alerts ?? [];

  const counts = alerts.reduce((acc,a) => {
    if (a.risk_level) acc[a.risk_level] = (acc[a.risk_level]??0)+1;
    return acc;
  }, {} as Record<string,number>);

  const trendData = alerts.slice(-40).map((a,i) => ({
    i, score: a.threat_score,
    time: new Date(a.timestamp).toLocaleTimeString([],{ hour:"2-digit", minute:"2-digit" }),
  }));

  const total = alerts.length;
  const buckets = [
    { range:"0–20",   label:"Safe",         count:alerts.filter(a=>a.threat_score<=20).length,               color:C.green  },
    { range:"21–40",  label:"Low concern",  count:alerts.filter(a=>a.threat_score>20&&a.threat_score<=40).length, color:"#84cc16"},
    { range:"41–60",  label:"Moderate",     count:alerts.filter(a=>a.threat_score>40&&a.threat_score<=60).length, color:C.amber  },
    { range:"61–80",  label:"High concern", count:alerts.filter(a=>a.threat_score>60&&a.threat_score<=80).length, color:"#f97316"},
    { range:"81–100", label:"Critical",     count:alerts.filter(a=>a.threat_score>80).length,               color:C.red    },
  ];

  return (
    <div style={{ padding: "20px 24px", maxWidth: 1440, margin: "0 auto" }}>
      <h1 style={{ fontFamily: "'DM Sans',sans-serif", fontSize: 22,
        fontWeight: 700, color: C.textPrim, margin: 0, marginBottom: 20 }}>Threat History</h1>

      {/* Stats + Pie */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1.3fr", gap: 12, marginBottom: 12 }}>
        <StatCard label="HIGH RISK EVENTS"   value={counts["High"]??0}   color={C.redL}/>
        <StatCard label="MEDIUM RISK EVENTS" value={counts["Medium"]??0} color={C.amberL}/>
        <StatCard label="LOW RISK EVENTS"    value={counts["Low"]??0}    color={C.greenL}/>
        <Card>
          <CardHeader>
            <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
              color: C.textDim, letterSpacing: "0.1em" }}>RISK DISTRIBUTION</span>
          </CardHeader>
          <CardBody>
            <RiskPie high={counts["High"]??0} med={counts["Medium"]??0} low={counts["Low"]??0}/>
          </CardBody>
        </Card>
      </div>

      {/* Charts row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 12, marginBottom: 12 }}>

        {/* Area trend */}
        <Card>
          <CardHeader>
            <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
              color: C.textDim, letterSpacing: "0.1em" }}>THREAT SCORE OVER TIME</span>
            <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
              color: C.textDim }}>Y = score (0–100) · each point = one alert</span>
          </CardHeader>
          <CardBody>
            {trendData.length < 2 ? (
              <div style={{ height: 190, display: "flex", alignItems: "center",
                justifyContent: "center", fontFamily: "'DM Mono',monospace",
                fontSize: 12, color: C.textDim }}>Waiting for data…</div>
            ) : (
              <ResponsiveContainer width="100%" height={190}>
                <AreaChart data={trendData} margin={{ top:4, right:4, bottom:16, left:0 }}>
                  <defs>
                    <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor={C.blue} stopOpacity={0.2}/>
                      <stop offset="95%" stopColor={C.blue} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke={C.border} strokeDasharray="4 4"/>
                  <XAxis dataKey="time"
                    tick={{ fill:C.textDim, fontSize:9, fontFamily:"'DM Mono',monospace" }}
                    tickLine={false} interval="preserveStartEnd"
                    label={{ value:"Alert time", position:"insideBottom",
                      fill:C.textDim, fontSize:9, offset:-8 }}/>
                  <YAxis domain={[0,100]} tick={{ fill:C.textDim, fontSize:9 }}
                    tickLine={false} axisLine={false}
                    label={{ value:"Score", angle:-90, position:"insideLeft",
                      fill:C.textDim, fontSize:9 }}/>
                  <Tooltip {...ttStyle} formatter={(v:number|string|undefined)=>[`${v??0} / 100`,"Threat Score"]}/>
                  <Area type="monotone" dataKey="score" stroke={C.blue} strokeWidth={1.5}
                    fill="url(#g2)" dot={false} activeDot={{ r:4, fill:C.amber }}/>
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardBody>
        </Card>

        {/* Score distribution */}
        <Card>
          <CardHeader>
            <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
              color: C.textDim, letterSpacing: "0.1em" }}>SCORE DISTRIBUTION</span>
          </CardHeader>
          <CardBody>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {buckets.map(b => (
                <div key={b.range}>
                  <div style={{ display: "flex", justifyContent: "space-between",
                    alignItems: "baseline", marginBottom: 5 }}>
                    <div style={{ display: "flex", gap: 8, alignItems: "baseline" }}>
                      <span style={{ fontFamily: "'DM Mono',monospace",
                        fontSize: 11, color: C.textSec }}>{b.range}</span>
                      <span style={{ fontFamily: "'DM Mono',monospace",
                        fontSize: 9, color: C.textDim }}>{b.label}</span>
                    </div>
                    <span style={{ fontFamily: "'DM Sans',sans-serif",
                      fontSize: 13, fontWeight: 700, color: b.color }}>
                      {b.count}
                      <span style={{ fontFamily: "'DM Mono',monospace",
                        fontSize: 9, color: C.textDim, marginLeft: 4 }}>
                        {total > 0 ? `${Math.round((b.count/total)*100)}%` : ""}
                      </span>
                    </span>
                  </div>
                  <div style={{ height: 8, background: C.border2, borderRadius: 4, overflow: "hidden" }}>
                    <div style={{
                      height: "100%",
                      width: total > 0 ? `${(b.count/total)*100}%` : "0%",
                      background: b.color, borderRadius: 4,
                      transition: "width 0.8s ease",
                    }}/>
                  </div>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Explanation log */}
      <Card>
        <CardHeader>
          <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
            color: C.textDim, letterSpacing: "0.1em" }}>RECENT ALERT LOG</span>
          <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
            color: C.textDim }}>{Math.min(alerts.length, 25)} of {alerts.length}</span>
        </CardHeader>
        <div style={{ maxHeight: 320, overflowY: "auto" }}>
          {[...alerts].reverse().slice(0,25).map((a,i) => (
            <div key={i} style={{
              display: "grid",
              gridTemplateColumns: "80px 52px 30px 1fr",
              gap: 12, padding: "10px 18px",
              borderBottom: `1px solid ${C.border}`,
              alignItems: "start",
              transition: "background 0.1s",
            }}
              onMouseEnter={e=>(e.currentTarget.style.background=C.cardHov)}
              onMouseLeave={e=>(e.currentTarget.style.background="transparent")}>
              <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
                color: C.textDim, paddingTop: 1 }}>
                {new Date(a.timestamp).toLocaleTimeString()}
              </span>
              <Tag level={a.risk_level}/>
              <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10,
                color: C.blueL, paddingTop: 1 }}>P{a.person_id}</span>
              <span style={{ fontSize: 12, color: C.textSec, lineHeight: 1.5 }}>
                {a.explanation}
              </span>
            </div>
          ))}
          {alerts.length === 0 && (
            <div style={{ padding: "32px 0", textAlign: "center",
              fontFamily: "'DM Mono',monospace", fontSize: 12, color: C.textDim }}>
              No alerts yet
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}

// ─── ROOT ────────────────────────────────────────────────────────
export default function App() {
  return (
    <>
      <link rel="preconnect" href="https://fonts.googleapis.com"/>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@300;400;500&display=swap"
        rel="stylesheet"/>
      <style>{`
        *, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
        html { font-size:16px; }
        body {
          background: ${C.bg};
          color: ${C.textPrim};
          font-family: 'DM Sans', sans-serif;
          min-height: 100vh;
          -webkit-font-smoothing: antialiased;
        }
        a { text-decoration: none; color: inherit; }
        button { font-family: inherit; }
        button:hover:not(:disabled) { opacity: 0.85; }
        button:disabled { opacity: 0.4; cursor: not-allowed; }

        /* Subtle dot grid background */
        body::before {
          content: '';
          position: fixed; inset: 0;
          background-image: radial-gradient(circle, ${C.border} 1px, transparent 1px);
          background-size: 28px 28px;
          opacity: 0.35;
          pointer-events: none;
          z-index: 0;
        }
        
        /* All content above bg */
        #root { position: relative; z-index: 1; }

        @keyframes blink {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.3; }
        }
        
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: ${C.bg}; }
        ::-webkit-scrollbar-thumb { background: ${C.border2}; border-radius: 2px; }
        ::-webkit-scrollbar-thumb:hover { background: ${C.textDim}; }

        /* Table row hover handled inline */
        tr { transition: background 0.1s; }
      `}</style>

      <BrowserRouter>
        <Navbar/>
        <Routes>
          <Route path="/"        element={<Dashboard  />}/>
          <Route path="/live"    element={<LiveView   />}/>
          <Route path="/alerts"  element={<AlertsPage />}/>
          <Route path="/history" element={<HistoryPage/>}/>
        </Routes>
      </BrowserRouter>
    </>
  );
}