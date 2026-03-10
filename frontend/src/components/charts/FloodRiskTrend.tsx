import React, { useMemo, useState } from 'react';
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { RainfallRecord } from '../../types';

interface Props {
  rainfallData: RainfallRecord[];
}

type RangeKey = '1yr' | '3yr' | '5yr' | 'All';
const rangeMonths: Record<RangeKey, number> = { '1yr': 12, '3yr': 36, '5yr': 60, All: Infinity };

const monthLabel = (r: RainfallRecord) => {
  const m = String(r.month).padStart(2, '0');
  return `${r.year}-${m}`;
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        background: '#1e293b',
        border: '1px solid #334155',
        borderRadius: 8,
        padding: '10px 14px',
        color: '#e2e8f0',
        fontSize: 13,
      }}
    >
      <p style={{ fontWeight: 700, marginBottom: 4, color: '#f8fafc' }}>{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {typeof p.value === 'number' ? p.value.toFixed(1) : p.value}
        </p>
      ))}
    </div>
  );
};

const btnStyle = (active: boolean): React.CSSProperties => ({
  padding: '4px 12px',
  borderRadius: 6,
  border: active ? '1px solid #3b82f6' : '1px solid #334155',
  background: active ? '#1e3a5f' : 'transparent',
  color: active ? '#60a5fa' : '#94a3b8',
  cursor: 'pointer',
  fontSize: 12,
  fontWeight: 600,
});

const FloodRiskTrend: React.FC<Props> = ({ rainfallData }) => {
  const [range, setRange] = useState<RangeKey>('3yr');

  const sorted = useMemo(
    () =>
      [...rainfallData].sort(
        (a, b) => a.year - b.year || a.month - b.month
      ),
    [rainfallData]
  );

  const filtered = useMemo(() => {
    const limit = rangeMonths[range];
    if (limit === Infinity) return sorted;
    return sorted.slice(-limit);
  }, [sorted, range]);

  const data = useMemo(
    () => filtered.map((r) => ({ ...r, label: monthLabel(r) })),
    [filtered]
  );

  return (
    <div style={{ width: '100%' }}>
      <div style={{ display: 'flex', gap: 6, marginBottom: 12, justifyContent: 'flex-end' }}>
        {(['1yr', '3yr', '5yr', 'All'] as RangeKey[]).map((k) => (
          <button key={k} style={btnStyle(range === k)} onClick={() => setRange(k)}>
            {k}
          </button>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={360}>
        <ComposedChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
          <defs>
            <linearGradient id="rainfallGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.35} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
          <XAxis
            dataKey="label"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            axisLine={{ stroke: '#334155' }}
            tickLine={false}
            interval="preserveStartEnd"
            angle={-35}
            textAnchor="end"
            height={50}
          />
          <YAxis
            yAxisId="left"
            tick={{ fill: '#94a3b8', fontSize: 12 }}
            axisLine={{ stroke: '#334155' }}
            tickLine={false}
            label={{ value: 'Rainfall (mm)', angle: -90, position: 'insideLeft', fill: '#94a3b8', fontSize: 12 }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            tick={{ fill: '#94a3b8', fontSize: 12 }}
            axisLine={{ stroke: '#334155' }}
            tickLine={false}
            label={{ value: 'Events', angle: 90, position: 'insideRight', fill: '#94a3b8', fontSize: 12 }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ color: '#94a3b8', fontSize: 12, paddingTop: 8 }}
          />
          <Area
            yAxisId="left"
            type="monotone"
            dataKey="total_rainfall_mm"
            name="Total Rainfall (mm)"
            stroke="#3b82f6"
            fill="url(#rainfallGrad)"
            strokeWidth={2}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="flood_events"
            name="Flood Events"
            stroke="#ef4444"
            strokeWidth={2}
            dot={{ r: 3, fill: '#ef4444' }}
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="max_hourly_intensity_mmh"
            name="Max Intensity (mm/h)"
            stroke="#f97316"
            strokeWidth={2}
            strokeDasharray="5 3"
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

export default FloodRiskTrend;
