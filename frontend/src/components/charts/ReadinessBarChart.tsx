import React, { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from 'recharts';
import { WardScore } from '../../types';

interface Props {
  wardScores: WardScore[];
}

const categoryColors: Record<string, string> = {
  'Critical Risk': '#ef4444',
  'Moderate Risk': '#f97316',
  'Prepared': '#eab308',
  'Resilient': '#22c55e',
};

const truncate = (str: string, max: number) =>
  str.length > max ? str.slice(0, max) + '...' : str;

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as WardScore;
  return (
    <div
      style={{
        background: '#1e293b',
        border: '1px solid #334155',
        borderRadius: 8,
        padding: '12px 16px',
        color: '#e2e8f0',
        fontSize: 13,
      }}
    >
      <p style={{ fontWeight: 700, marginBottom: 6, color: '#f8fafc' }}>
        {d.ward_name}
      </p>
      <p style={{ color: categoryColors[d.category], fontWeight: 600 }}>
        Readiness Score: {d.readiness_score.toFixed(1)} ({d.category})
      </p>
      <hr style={{ border: 'none', borderTop: '1px solid #334155', margin: '8px 0' }} />
      <p>Drainage Capacity: {d.drainage_capacity_index.toFixed(1)}</p>
      <p>Emergency Infra: {d.emergency_infrastructure_coverage.toFixed(1)}</p>
      <p>Hotspot Density: {d.flood_hotspot_density.toFixed(1)}</p>
      <p>Rainfall Vulnerability: {d.rainfall_vulnerability.toFixed(1)}</p>
      <p>Pump Availability: {d.pump_station_availability.toFixed(1)}</p>
    </div>
  );
};

const ReadinessBarChart: React.FC<Props> = ({ wardScores }) => {
  const sorted = useMemo(
    () => [...wardScores].sort((a, b) => a.readiness_score - b.readiness_score),
    [wardScores]
  );

  const chartHeight = Math.max(400, sorted.length * 32);

  return (
    <div style={{ width: '100%', height: chartHeight }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={sorted}
          layout="vertical"
          margin={{ top: 10, right: 30, left: 10, bottom: 10 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(148, 163, 184, 0.1)"
            horizontal={false}
          />
          <XAxis
            type="number"
            domain={[0, 100]}
            tick={{ fill: '#94a3b8', fontSize: 12 }}
            axisLine={{ stroke: '#334155' }}
            tickLine={{ stroke: '#334155' }}
          />
          <YAxis
            type="category"
            dataKey="ward_name"
            width={120}
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            tickFormatter={(v: string) => truncate(v, 16)}
            axisLine={{ stroke: '#334155' }}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(148,163,184,0.06)' }} />
          <ReferenceLine x={30} stroke="#ef4444" strokeDasharray="4 4" strokeOpacity={0.5} />
          <ReferenceLine x={60} stroke="#f97316" strokeDasharray="4 4" strokeOpacity={0.5} />
          <ReferenceLine x={80} stroke="#eab308" strokeDasharray="4 4" strokeOpacity={0.5} />
          <Bar dataKey="readiness_score" radius={[0, 4, 4, 0]} barSize={18}>
            {sorted.map((entry, idx) => (
              <Cell key={idx} fill={categoryColors[entry.category] || '#64748b'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ReadinessBarChart;
