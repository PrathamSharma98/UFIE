import React from 'react';

/* ------------------------------------------------------------------ */
/*  Legend Section Data                                                 */
/* ------------------------------------------------------------------ */
const SEVERITY_ITEMS = [
  { label: 'Critical', color: '#dc2626' },
  { label: 'High', color: '#ea580c' },
  { label: 'Moderate', color: '#eab308' },
  { label: 'Low', color: '#22c55e' },
];

const READINESS_ITEMS = [
  { label: 'Critical Risk', color: '#dc2626' },
  { label: 'Moderate Risk', color: '#ea580c' },
  { label: 'Prepared', color: '#eab308' },
  { label: 'Resilient', color: '#22c55e' },
];

const DRAINAGE_ITEMS = [
  { label: '> 90% Load', color: '#dc2626' },
  { label: '70-90% Load', color: '#ea580c' },
  { label: '50-70% Load', color: '#eab308' },
  { label: '< 50% Load', color: '#22c55e' },
];

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */
const MapLegend: React.FC = () => {
  return (
    <div
      className="absolute bottom-6 right-4 z-[1000] bg-slate-800/95 backdrop-blur
                 border border-slate-700 rounded-xl shadow-2xl p-4 min-w-[180px]
                 max-h-[calc(100vh-120px)] overflow-y-auto text-xs"
    >
      <h4 className="text-white font-semibold text-sm mb-3 tracking-wide">
        Legend
      </h4>

      {/* Flood Probability Gradient */}
      <div className="mb-4">
        <p className="text-slate-400 uppercase tracking-wider text-[10px] font-medium mb-1.5">
          Flood Probability
        </p>
        <div
          className="h-3 rounded-sm"
          style={{
            background:
              'linear-gradient(to right, #22c55e, #eab308, #ea580c, #dc2626, #7f1d1d)',
          }}
        />
        <div className="flex justify-between mt-0.5 text-[10px] text-slate-400">
          <span>Low</span>
          <span>High</span>
        </div>
      </div>

      {/* Severity */}
      <LegendSection title="Hotspot Severity" items={SEVERITY_ITEMS} />

      {/* Ward Readiness */}
      <LegendSection title="Ward Readiness" items={READINESS_ITEMS} />

      {/* Drainage */}
      <LegendSection title="Drainage Load" items={DRAINAGE_ITEMS} />

      {/* Pump Status */}
      <div className="mb-1">
        <p className="text-slate-400 uppercase tracking-wider text-[10px] font-medium mb-1.5">
          Pump Stations
        </p>
        <div className="space-y-1">
          <LegendDot color="#0ea5e9" label="Operational" />
          <LegendDot color="#f43f5e" label="Non-operational" />
        </div>
      </div>
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */
interface LegendSectionProps {
  title: string;
  items: { label: string; color: string }[];
}

const LegendSection: React.FC<LegendSectionProps> = ({ title, items }) => (
  <div className="mb-3">
    <p className="text-slate-400 uppercase tracking-wider text-[10px] font-medium mb-1.5">
      {title}
    </p>
    <div className="space-y-1">
      {items.map((item) => (
        <LegendDot key={item.label} color={item.color} label={item.label} />
      ))}
    </div>
  </div>
);

const LegendDot: React.FC<{ color: string; label: string }> = ({
  color,
  label,
}) => (
  <div className="flex items-center gap-2">
    <span
      className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0"
      style={{ backgroundColor: color }}
    />
    <span className="text-slate-300">{label}</span>
  </div>
);

export default React.memo(MapLegend);
