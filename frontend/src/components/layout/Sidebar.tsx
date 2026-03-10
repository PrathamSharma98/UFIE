import React, { useMemo } from 'react';
import {
  AlertTriangle,
  Droplets,
  Shield,
  Activity,
  Gauge,
  Wrench,
  X,
  ChevronRight,
} from 'lucide-react';
import type { DashboardSummary, WardScore } from '../../types';
import { categoryColor } from '../../utils/helpers';

interface SidebarProps {
  summary: DashboardSummary | null;
  wardScores: WardScore[] | null;
  isOpen: boolean;
  onClose: () => void;
}

interface StatCardProps {
  icon: React.ElementType;
  label: string;
  value: number | string | null;
  color: string;
  subtext?: string;
}

function StatCard({ icon: Icon, label, value, color, subtext }: StatCardProps) {
  if (value === null || value === undefined) {
    return (
      <div className="bg-slate-800/50 rounded-xl p-3 border border-slate-700/30">
        <div className="loading-shimmer h-3 w-16 mb-2" />
        <div className="loading-shimmer h-6 w-12" />
      </div>
    );
  }
  return (
    <div className="bg-slate-800/50 rounded-xl p-3 border border-slate-700/30 card-hover group">
      <div className="flex items-center gap-1.5 mb-1.5">
        <Icon size={13} className={color} />
        <span className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">{label}</span>
      </div>
      <p className="text-xl font-bold text-white leading-none">{value}</p>
      {subtext && <p className="text-[10px] text-slate-500 mt-1">{subtext}</p>}
    </div>
  );
}

function Sidebar({ summary, wardScores, isOpen, onClose }: SidebarProps) {
  const topRiskWards = useMemo(() => {
    if (!wardScores) return [];
    return [...wardScores]
      .sort((a, b) => a.readiness_score - b.readiness_score)
      .slice(0, 5);
  }, [wardScores]);

  const categoryDist = useMemo(() => {
    if (!wardScores) return [];
    const cats: Record<string, number> = {};
    wardScores.forEach((w) => {
      cats[w.category] = (cats[w.category] || 0) + 1;
    });
    const total = wardScores.length || 1;
    return [
      { name: 'Critical Risk', count: cats['Critical Risk'] || 0, pct: ((cats['Critical Risk'] || 0) / total) * 100 },
      { name: 'Moderate Risk', count: cats['Moderate Risk'] || 0, pct: ((cats['Moderate Risk'] || 0) / total) * 100 },
      { name: 'Prepared', count: cats['Prepared'] || 0, pct: ((cats['Prepared'] || 0) / total) * 100 },
      { name: 'Resilient', count: cats['Resilient'] || 0, pct: ((cats['Resilient'] || 0) / total) * 100 },
    ];
  }, [wardScores]);

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden backdrop-blur-sm animate-fade-in"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed top-14 left-0 bottom-0 w-72 z-40 bg-slate-900/95 backdrop-blur-xl border-r border-slate-700/40 flex flex-col
          transition-transform duration-300 ease-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0`}
      >
        {/* Sticky Header */}
        <div className="sticky-header px-4 py-3 border-b border-slate-700/30 flex items-center justify-between">
          <div>
            <h2 className="text-xs font-bold text-white uppercase tracking-wider">Dashboard</h2>
            <p className="text-[10px] text-slate-500">Overview & Stats</p>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-slate-700/60 rounded-lg lg:hidden text-slate-400"
          >
            <X size={16} />
          </button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 panel-scroll px-3 py-3 space-y-4">
          {/* Summary Stats Grid */}
          <div>
            <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-2 px-1">Key Metrics</p>
            <div className="grid grid-cols-2 gap-2">
              <StatCard icon={AlertTriangle} label="Hotspots" value={summary?.total_hotspots ?? null} color="text-red-400" subtext="flood micro-hotspots" />
              <StatCard icon={Droplets} label="Critical" value={summary?.critical_hotspots ?? null} color="text-orange-400" subtext="high severity" />
              <StatCard icon={Shield} label="At Risk" value={summary?.high_risk_wards ?? null} color="text-yellow-400" subtext="wards below 30" />
              <StatCard icon={Gauge} label="Avg Score" value={summary ? summary.avg_readiness_score.toFixed(1) : null} color="text-blue-400" subtext="readiness / 100" />
              <StatCard icon={Activity} label="Pumps" value={summary?.total_pump_stations ?? null} color="text-cyan-400" subtext="stations" />
              <StatCard icon={Wrench} label="Undersized" value={summary?.undersized_drains ?? null} color="text-pink-400" subtext="drain segments" />
            </div>
          </div>

          {/* Top At-Risk Wards */}
          <div>
            <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-2 px-1">Top At-Risk Wards</p>
            <div className="space-y-1.5">
              {!wardScores ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="loading-shimmer h-12 w-full" />
                ))
              ) : topRiskWards.length === 0 ? (
                <p className="text-xs text-slate-500 px-1">No ward data available</p>
              ) : (
                topRiskWards.map((ward, i) => (
                  <div
                    key={ward.ward_id}
                    className="flex items-center gap-2.5 bg-slate-800/40 rounded-xl px-3 py-2 border border-slate-700/20 card-hover group"
                  >
                    <span className="text-[10px] font-bold text-slate-500 w-4">{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-white truncate">{ward.ward_name}</p>
                      <p className="text-[10px] text-slate-500">
                        Pop: {(ward.population / 1000).toFixed(0)}K &middot; {ward.area_km2} km²
                      </p>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <p className="text-sm font-bold text-white">{ward.readiness_score.toFixed(0)}</p>
                      <p
                        className="text-[9px] font-semibold"
                        style={{ color: categoryColor(ward.category) }}
                      >
                        {ward.category}
                      </p>
                    </div>
                    <ChevronRight size={12} className="text-slate-600 group-hover:text-slate-400 transition-colors flex-shrink-0" />
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Category Distribution */}
          <div>
            <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-2 px-1">Readiness Distribution</p>
            <div className="space-y-2">
              {!wardScores ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="loading-shimmer h-6 w-full" />
                ))
              ) : (
                categoryDist.map((cat) => (
                  <div key={cat.name}>
                    <div className="flex items-center justify-between mb-0.5 px-1">
                      <span className="text-[11px] text-slate-300">{cat.name}</span>
                      <span className="text-[10px] font-semibold text-slate-400">
                        {cat.count} ({cat.pct.toFixed(0)}%)
                      </span>
                    </div>
                    <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-700 ease-out"
                        style={{
                          width: `${cat.pct}%`,
                          backgroundColor: categoryColor(cat.name),
                        }}
                      />
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        {summary && (
          <div className="px-4 py-2 border-t border-slate-700/30 bg-slate-900/60">
            <p className="text-[9px] text-slate-600">
              Last updated: {new Date(summary.last_updated).toLocaleTimeString()}
            </p>
          </div>
        )}
      </aside>
    </>
  );
}

export default React.memo(Sidebar);
