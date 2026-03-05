import { useState, useEffect } from "react";
import { getVideos, setMode } from "../api/client";

export default function VideoSelector() {
  const [videos,  setVideos]  = useState<string[]>([]);
  const [current, setCurrent] = useState("demo1.mp4");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getVideos().then(setVideos);
  }, []);

  const switchVideo = async (video: string) => {
    setLoading(true);
    await setMode("demo", video);
    setCurrent(video);
    setLoading(false);
  };

  const switchLive = async () => {
    setLoading(true);
    await setMode("live");
    setCurrent("LIVE");
    setLoading(false);
  };

  return (
    <div className="bg-bg2 border border-border rounded-lg p-4">
      <div className="text-xs font-mono text-text-dim mb-3 tracking-widest">
        VIDEO SOURCE
      </div>

      {/* Live button */}
      <button onClick={switchLive}
        className={`w-full mb-2 py-2 rounded text-sm font-bold font-head tracking-wider transition-all
          ${current === "LIVE"
            ? "bg-green text-bg"
            : "border border-green/40 text-green hover:bg-green/10"}`}>
        ● WEBCAM LIVE
      </button>

      {/* Demo video buttons */}
      <div className="grid grid-cols-2 gap-2">
        {videos.map(v => (
          <button key={v} onClick={() => switchVideo(v)} disabled={loading}
            className={`py-2 px-3 rounded text-xs font-mono transition-all
              ${current === v
                ? "bg-cyan/20 border border-cyan text-cyan"
                : "border border-border text-text-dim hover:border-cyan/50 hover:text-cyan"}`}>
            {v.replace(".mp4", "")}
          </button>
        ))}
      </div>

      {loading && (
        <div className="text-xs font-mono text-amber mt-2 text-center animate-pulse">
          SWITCHING...
        </div>
      )}
    </div>
  );
}   videoslector.tsx