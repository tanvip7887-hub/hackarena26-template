import { usePolling } from "../hooks/usePolling";
import { getAlerts }  from "../api/client";
import AlertsTable    from "../components/AlertsTable";

export default function Alerts() {
  const { data, loading } = usePolling(getAlerts, 3000);
  const alerts = data?.alerts ?? [];

  const high   = alerts.filter(a => a.risk === "High").length;
  const medium = alerts.filter(a => a.risk === "Medium").length;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-head text-2xl font-black text-text-bright tracking-wide">
            Alert History
          </h2>
          <p className="text-text-dim text-sm mt-1">
            Total: <span className="text-cyan font-bold">{data?.count ?? 0}</span> events logged
          </p>
        </div>
        <div className="flex gap-3">
          <span className="px-3 py-1 rounded border border-danger/30 bg-danger/10
                           text-danger text-xs font-mono">{high} HIGH</span>
          <span className="px-3 py-1 rounded border border-amber/30 bg-amber/10
                           text-amber text-xs font-mono">{medium} MED</span>
        </div>
      </div>

      <div className="bg-bg2 border border-border rounded-lg">
        {loading ? (
          <div className="py-12 text-center font-mono text-xs text-text-dim animate-pulse">
            LOADING ALERTS...
          </div>
        ) : alerts.length === 0 ? (
          <div className="py-12 text-center font-mono text-xs text-text-dim">
            NO ALERTS RECORDED YET
          </div>
        ) : (
          <AlertsTable alerts={[...alerts].reverse()} />
        )}
      </div>
    </div>
  );
}     alerts.tsx