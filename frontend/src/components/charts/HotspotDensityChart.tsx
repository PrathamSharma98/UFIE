import React, { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

interface WardHotspotEntry {
  ward_name: string;
  count: number;
}

interface HotspotSummary {
  by_ward: Record<string, number>;
  [key: string]: any;
}

interface Props {
  hotspotSummary: HotspotSummary;
}

const interpolateColor = (ratio: number): string => {
  // From teal (#14b8a6) to red (#ef4444) based on density ratio
  const r = Math.round(20 + ratio * (239 - 20));
  const g = Math.round(184 - ratio * (184 - 68));
  const b = Math.round(166 - ratio * (166 - 68));
  return `rgb(${r},${g},${b})`;
};

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as WardHotspotEntry;
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
      <p style={{ fontWeight: 700, color: '#f8fafc', marginBottom: 2 }}>{d.ward_name}</p>
      <p>Hotspots: <span style={{ fontWeight: 600, color: '#f97316' }}>{d.count}</span></p>
    </div>
  );
};

const HotspotDensityChart: React.FC<Props> = ({ hotspotSummary }) => {
  const data = useMemo(() => {
    const byWard = hotspotSummary?.by_ward || {};
    const entries: WardHotspotEntry[] = Object.entries(byWard).map(
      ([ward_name, count]) => ({ ward_name, count: count as number })
    );
    return entries.sort((a, b) => b.count - a.count);
  }, [hotspotSummary]);

  const maxCount = useMemo(() => Math.max(...data.map((d) => d.count), 1), [data]);

  const chartHeight = Math.max(340, data.length * 30);

  return (
    <div style={{ width: '100%', height: chartHeight }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 10, right: 30, left: 10, bottom: 10 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fill: '#94a3b8', fontSize: 12 }}
            axisLine={{ stroke: '#334155' }}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="ward_name"
            width={120}
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            tickFormatter={(v: string) => (v.length > 16 ? v.slice(0, 16) + '...' : v)}
            axisLine={{ stroke: '#334155' }}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(148,163,184,0.06)' }} />
          <Bar dataKey="count" name="Hotspots" radius={[0, 6, 6, 0]} barSize={18}>
            {data.map((entry, idx) => (
              <Cell key={idx} fill={interpolateColor(entry.count / maxCount)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default HotspotDensityChart;
