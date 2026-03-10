import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { AlertTriangle, MapPin, Loader2, RefreshCw, Filter, ChevronDown, ChevronRight } from 'lucide-react';
import { fetchRiskAlerts } from '../../services/api';
import type { RiskAlert } from '../../types';

const severityPriority: Record<string, number> = { critical: 0, high: 1, moderate: 2, low: 3 };

const severityStyles: Record<string, { dot: string; bg: string; border: string; text: string }> = {
  critical: { dot: 'bg-red-500', bg: 'bg-red-950/30', border: 'border-red-800/30', text: 'text-red-300' },
  high: { dot: 'bg-orange-500', bg: 'bg-orange-950/20', border: 'border-orange-800/20', text: 'text-orange-300' },
  moderate: { dot: 'bg-yellow-500', bg: 'bg-yellow-950/20', border: 'border-yellow-800/20', text: 'text-yellow-300' },
  low: { dot: 'bg-green-500', bg: 'bg-green-950/20', border: 'border-green-800/20', text: 'text-green-300' },
};

function formatAlertType(type: string): string {
  return type
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function AlertsPanel() {
  const [alerts, setAlerts] = useState<RiskAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string | null>(null);
  const [groupByWard, setGroupByWard] = useState(false);
  const [expandedWards, setExpandedWards] = useState<Set<string>>(new Set());

  const loadAlerts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRiskAlerts();
      setAlerts(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load alerts');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadAlerts(); }, [loadAlerts]);

  const filtered = useMemo(() => {
    let result = [...alerts].sort(
      (a, b) => (severityPriority[a.severity?.toLowerCase()] ?? 9) - (severityPriority[b.severity?.toLowerCase()] ?? 9)
    );
    if (severityFilter) {
      result = result.filter((a) => a.severity?.toLowerCase() === severityFilter);
    }
    return result;
  }, [alerts, severityFilter]);

  const grouped = useMemo(() => {
    if (!groupByWard) return null;
    const map = new Map<string, RiskAlert[]>();
    filtered.forEach((a) => {
      const key = a.ward_name || `Ward ${a.ward_id}`;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(a);
    });
    return map;
  }, [filtered, groupByWard]);

  const toggleWard = (ward: string) => {
    setExpandedWards((prev) => {
      const next = new Set(prev);
      next.has(ward) ? next.delete(ward) : next.add(ward);
      return next;
    });
  };

  const filters = ['critical', 'high', 'moderate', 'low'];

  if (loading) {
    return (
      <div className="space-y-3">
        <div className="loading-shimmer h-10 w-full rounded-xl" />
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="loading-shimmer h-16 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <AlertTriangle size={40} className="text-red-400 mb-3" />
        <p className="text-sm text-slate-400 mb-4">{error}</p>
        <button
          onClick={loadAlerts}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-xl text-xs font-semibold text-white"
        >
          <RefreshCw size={14} /> Retry
        </button>
      </div>
    );
  }

  const renderAlert = (alert: RiskAlert, idx: number) => {
    const sev = alert.severity?.toLowerCase() || 'moderate';
    const styles = severityStyles[sev] || severityStyles.moderate;
    return (
      <div
        key={`${alert.ward_id}-${alert.alert_type}-${idx}`}
        className={`${styles.bg} border ${styles.border} rounded-xl px-3.5 py-2.5 card-hover animate-fade-in`}
      >
        <div className="flex items-start gap-2.5">
          <div className={`w-2 h-2 rounded-full ${styles.dot} mt-1.5 flex-shrink-0`} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2 mb-0.5">
              <span className="text-xs font-semibold text-white truncate">{alert.ward_name}</span>
              <span className={`text-[9px] font-bold uppercase tracking-wider ${styles.text}`}>
                {alert.severity}
              </span>
            </div>
            <p className="text-[10px] font-medium text-slate-400 mb-0.5">
              {formatAlertType(alert.alert_type)}
            </p>
            <p className="text-[11px] text-slate-300 leading-relaxed">{alert.message}</p>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-3">
      {/* Header with filters */}
      <div className="sticky-header py-2 -mx-4 px-4 -mt-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <AlertTriangle size={16} className="text-orange-400" />
            Risk Alerts
            <span className="text-[10px] font-normal text-slate-500">({filtered.length})</span>
          </h2>
          <button
            onClick={() => setGroupByWard((p) => !p)}
            className={`flex items-center gap-1 px-2 py-1 text-[10px] font-semibold rounded-lg transition-colors ${
              groupByWard
                ? 'bg-blue-600/20 text-blue-300 border border-blue-500/30'
                : 'bg-slate-800/50 text-slate-400 border border-slate-700/30 hover:text-white'
            }`}
          >
            <MapPin size={10} /> Group by Ward
          </button>
        </div>

        <div className="flex gap-1">
          <button
            onClick={() => setSeverityFilter(null)}
            className={`px-2.5 py-1 text-[10px] font-semibold rounded-lg transition-colors ${
              !severityFilter
                ? 'bg-blue-600/20 text-blue-300 border border-blue-500/30'
                : 'bg-slate-800/50 text-slate-400 border border-slate-700/30 hover:text-white'
            }`}
          >
            All
          </button>
          {filters.map((f) => {
            const s = severityStyles[f];
            return (
              <button
                key={f}
                onClick={() => setSeverityFilter(severityFilter === f ? null : f)}
                className={`flex items-center gap-1 px-2.5 py-1 text-[10px] font-semibold rounded-lg transition-colors ${
                  severityFilter === f
                    ? `${s.bg} ${s.text} border ${s.border}`
                    : 'bg-slate-800/50 text-slate-400 border border-slate-700/30 hover:text-white'
                }`}
              >
                <div className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            );
          })}
        </div>
      </div>

      {/* Alerts list */}
      {filtered.length === 0 ? (
        <div className="text-center py-12">
          <Filter size={32} className="text-slate-600 mx-auto mb-2" />
          <p className="text-sm text-slate-500">No alerts match the filter</p>
        </div>
      ) : groupByWard && grouped ? (
        <div className="space-y-2">
          {Array.from(grouped.entries()).map(([ward, wardAlerts]) => {
            const isExpanded = expandedWards.has(ward);
            return (
              <div key={ward} className="glass-panel-sm overflow-hidden">
                <button
                  onClick={() => toggleWard(ward)}
                  className="w-full flex items-center gap-2 px-3 py-2 hover:bg-slate-700/20 transition-colors"
                >
                  {isExpanded ? <ChevronDown size={12} className="text-slate-400" /> : <ChevronRight size={12} className="text-slate-400" />}
                  <MapPin size={12} className="text-blue-400" />
                  <span className="text-xs font-semibold text-white flex-1 text-left">{ward}</span>
                  <span className="text-[10px] text-slate-500">{wardAlerts.length} alerts</span>
                </button>
                {isExpanded && (
                  <div className="px-2 pb-2 space-y-1.5 animate-fade-in">
                    {wardAlerts.map((a, i) => renderAlert(a, i))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((a, i) => renderAlert(a, i))}
        </div>
      )}
    </div>
  );
}

export default React.memo(AlertsPanel);
