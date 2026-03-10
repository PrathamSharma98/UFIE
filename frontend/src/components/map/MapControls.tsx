import React, { useState } from 'react';
import {
  Layers,
  Droplets,
  Map,
  Activity,
  ChevronLeft,
  ChevronRight,
  Filter,
  MapPin,
} from 'lucide-react';
import type { MapLayers, WardProperties } from '../../types';

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */
interface MapControlsProps {
  layers: MapLayers;
  onLayerChange: (layers: MapLayers) => void;
  wards: { ward_id: number; ward_name: string }[];
  onWardSelect: (wardId: number | null) => void;
  onSeverityFilter: (severity: string | null) => void;
  selectedWardId: number | null;
}

/* ------------------------------------------------------------------ */
/*  Layer definitions                                                  */
/* ------------------------------------------------------------------ */
const LAYER_ITEMS: {
  key: keyof MapLayers;
  label: string;
  icon: React.ReactNode;
  color: string;
}[] = [
  { key: 'hotspots', label: 'Hotspots', icon: <Droplets size={16} />, color: '#dc2626' },
  { key: 'heatmap', label: 'Heatmap', icon: <Activity size={16} />, color: '#ea580c' },
  { key: 'wards', label: 'Wards', icon: <Map size={16} />, color: '#3b82f6' },
  { key: 'drainage', label: 'Drainage', icon: <Droplets size={16} />, color: '#0ea5e9' },
  { key: 'pumps', label: 'Pumps', icon: <MapPin size={16} />, color: '#22c55e' },
];

const SEVERITIES = ['All', 'Critical', 'High', 'Moderate', 'Low'] as const;

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */
const MapControls: React.FC<MapControlsProps> = ({
  layers,
  onLayerChange,
  wards,
  onWardSelect,
  onSeverityFilter,
  selectedWardId,
}) => {
  const [collapsed, setCollapsed] = useState(false);
  const [severity, setSeverity] = useState<string>('All');

  const toggleLayer = (key: keyof MapLayers) => {
    onLayerChange({ ...layers, [key]: !layers[key] });
  };

  const handleSeverity = (val: string) => {
    setSeverity(val);
    onSeverityFilter(val === 'All' ? null : val);
  };

  return (
    <div
      className={`absolute top-4 left-4 z-[1000] transition-all duration-300 ${
        collapsed ? 'w-10' : 'w-64'
      }`}
    >
      {/* ---- Collapse Toggle ---- */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-3 z-10 bg-slate-800 border border-slate-600
                   rounded-full w-6 h-6 flex items-center justify-center
                   text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
        title={collapsed ? 'Expand controls' : 'Collapse controls'}
      >
        {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>

      {/* ---- Collapsed Icon ---- */}
      {collapsed && (
        <div
          className="bg-slate-800/90 backdrop-blur border border-slate-700 rounded-lg
                      p-2 flex items-center justify-center cursor-pointer hover:bg-slate-700/90"
          onClick={() => setCollapsed(false)}
        >
          <Layers size={20} className="text-slate-300" />
        </div>
      )}

      {/* ---- Expanded Panel ---- */}
      {!collapsed && (
        <div className="bg-slate-800/95 backdrop-blur border border-slate-700 rounded-xl shadow-2xl overflow-hidden max-h-[calc(100vh-120px)]">
          <div className="panel-scroll max-h-[calc(100vh-120px)]">
          {/* Header */}
          <div className="px-4 py-3 border-b border-slate-700 flex items-center gap-2">
            <Layers size={18} className="text-sky-400" />
            <span className="text-sm font-semibold text-white tracking-wide">
              Map Controls
            </span>
          </div>

          {/* Layer Toggles */}
          <div className="px-4 py-3 space-y-2 border-b border-slate-700">
            <p className="text-[11px] uppercase tracking-wider text-slate-400 font-medium mb-2">
              Layers
            </p>
            {LAYER_ITEMS.map(({ key, label, icon, color }) => (
              <label
                key={key}
                className="flex items-center gap-3 cursor-pointer group py-0.5"
              >
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={layers[key]}
                    onChange={() => toggleLayer(key)}
                    className="sr-only peer"
                  />
                  <div
                    className="w-4 h-4 rounded border-2 transition-all peer-checked:border-transparent"
                    style={{
                      borderColor: layers[key] ? color : '#475569',
                      backgroundColor: layers[key] ? color : 'transparent',
                    }}
                  >
                    {layers[key] && (
                      <svg
                        viewBox="0 0 16 16"
                        className="w-full h-full text-white"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth={2.5}
                      >
                        <path d="M3 8l3 3 7-7" />
                      </svg>
                    )}
                  </div>
                </div>
                <span className="text-slate-400 group-hover:text-slate-200 transition-colors">
                  {icon}
                </span>
                <span className="text-sm text-slate-300 group-hover:text-white transition-colors">
                  {label}
                </span>
              </label>
            ))}
          </div>

          {/* Severity Filter */}
          <div className="px-4 py-3 border-b border-slate-700">
            <p className="text-[11px] uppercase tracking-wider text-slate-400 font-medium mb-2 flex items-center gap-1.5">
              <Filter size={12} />
              Severity Filter
            </p>
            <select
              value={severity}
              onChange={(e) => handleSeverity(e.target.value)}
              className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-1.5
                         text-sm text-slate-200 focus:outline-none focus:border-sky-500
                         transition-colors cursor-pointer"
            >
              {SEVERITIES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          {/* Ward Selector */}
          <div className="px-4 py-3">
            <p className="text-[11px] uppercase tracking-wider text-slate-400 font-medium mb-2 flex items-center gap-1.5">
              <MapPin size={12} />
              Select Ward
            </p>
            <select
              value={selectedWardId ?? ''}
              onChange={(e) => {
                const val = e.target.value;
                onWardSelect(val ? Number(val) : null);
              }}
              className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-1.5
                         text-sm text-slate-200 focus:outline-none focus:border-sky-500
                         transition-colors cursor-pointer"
            >
              <option value="">All Wards</option>
              {wards
                .sort((a, b) => a.ward_name.localeCompare(b.ward_name))
                .map((w) => (
                  <option key={w.ward_id} value={w.ward_id}>
                    {w.ward_name}
                  </option>
                ))}
            </select>
          </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default React.memo(MapControls);
