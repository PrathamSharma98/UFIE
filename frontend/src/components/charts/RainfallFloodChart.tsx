import React, { useMemo } from 'react';
import {
  ComposedChart,
  Area,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { SimulationResult } from '../../types';

interface Props {
  simulationResults: SimulationResult[];
}

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
      <p style={{ fontWeight: 700, marginBottom: 4, color: '#f8fafc' }}>
        Intensity: {label} mm/hr
      </p>
      {payload.map((p: any) => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {typeof p.value === 'number' ? p.value.toLocaleString() : p.value}
        </p>
      ))}
    </div>
  );
};

const RainfallFloodChart: React.FC<Props> = ({ simulationResults }) => {
  const data = useMemo(
    () =>
      [...simulationResults]
        .sort((a, b) => a.intensity_mmh - b.intensity_mmh)
        .map((r) => ({
          intensity: r.intensity_mmh,
          activated_hotspots: r.activated_hotspots,
          affected_wards: r.affected_wards.length,
          runoff_volume: r.runoff_volume_m3,
          peak_discharge: r.peak_discharge_m3s,
        })),
    [simulationResults]
  );

  return (
    <div style={{ width: '100%' }}>
      <ResponsiveContainer width="100%" height={380}>
        <ComposedChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
          <defs>
            <linearGradient id="hotspotGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f97316" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#f97316" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
          <XAxis
            dataKey="intensity"
            tick={{ fill: '#94a3b8', fontSize: 12 }}
            axisLine={{ stroke: '#334155' }}
            tickLine={false}
            label={{ value: 'Rainfall Intensity (mm/hr)', position: 'insideBottom', offset: -4, fill: '#94a3b8', fontSize: 12 }}
          />
          <YAxis
            yAxisId="left"
            tick={{ fill: '#94a3b8', fontSize: 12 }}
            axisLine={{ stroke: '#334155' }}
            tickLine={false}
            label={{ value: 'Hotspots / Wards', angle: -90, position: 'insideLeft', fill: '#94a3b8', fontSize: 12 }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            tick={{ fill: '#94a3b8', fontSize: 12 }}
            axisLine={{ stroke: '#334155' }}
            tickLine={false}
            label={{ value: 'Runoff (m\u00B3) / Discharge', angle: 90, position: 'insideRight', fill: '#94a3b8', fontSize: 12 }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12, paddingTop: 8 }} />
          <Area
            yAxisId="left"
            type="monotone"
            dataKey="activated_hotspots"
            name="Activated Hotspots"
            stroke="#f97316"
            fill="url(#hotspotGrad)"
            strokeWidth={2}
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="affected_wards"
            name="Affected Wards"
            stroke="#a78bfa"
            strokeWidth={2}
            dot={{ r: 3, fill: '#a78bfa' }}
          />
          <Bar
            yAxisId="right"
            dataKey="peak_discharge"
            name="Peak Discharge (m\u00B3/s)"
            fill="#3b82f6"
            opacity={0.45}
            barSize={20}
            radius={[4, 4, 0, 0]}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="runoff_volume"
            name="Runoff Volume (m\u00B3)"
            stroke="#22d3ee"
            strokeWidth={2}
            strokeDasharray="5 3"
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

export default RainfallFloodChart;
