import React, { useMemo } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts';
import { InfrastructureGap } from '../../types';

interface Props {
  gaps: InfrastructureGap[];
}

const TYPE_COLORS: Record<string, string> = {
  drainage: '#3b82f6',
  pump_station: '#22c55e',
  shelter: '#eab308',
  green_cover: '#10b981',
  soil: '#a78bfa',
  capacity: '#f97316',
  maintenance: '#ef4444',
};

const fallbackColors = ['#6366f1', '#ec4899', '#14b8a6', '#f43f5e', '#84cc16', '#0ea5e9'];

const getColor = (type: string, idx: number): string =>
  TYPE_COLORS[type.toLowerCase()] || fallbackColors[idx % fallbackColors.length];

const severityColors: Record<string, string> = {
  Critical: '#ef4444',
  High: '#f97316',
  Moderate: '#eab308',
  Low: '#22c55e',
};

const TooltipContent = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
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
      <p style={{ fontWeight: 700, color: '#f8fafc' }}>{d.name || d.severity}</p>
      <p>Count: {d.value ?? d.count}</p>
      {d.cost !== undefined && <p>Cost: {d.cost.toFixed(2)} Cr</p>}
    </div>
  );
};

const InfrastructureGapChart: React.FC<Props> = ({ gaps }) => {
  const pieData = useMemo(() => {
    const map = new Map<string, number>();
    gaps.forEach((g) => map.set(g.gap_type, (map.get(g.gap_type) || 0) + 1));
    return Array.from(map.entries()).map(([name, value]) => ({ name, value }));
  }, [gaps]);

  const barData = useMemo(() => {
    const map = new Map<string, { count: number; cost: number }>();
    gaps.forEach((g) => {
      const prev = map.get(g.severity) || { count: 0, cost: 0 };
      map.set(g.severity, {
        count: prev.count + 1,
        cost: prev.cost + g.estimated_cost_inr_crores,
      });
    });
    return Array.from(map.entries())
      .map(([severity, v]) => ({ severity, ...v }))
      .sort((a, b) => b.cost - a.cost);
  }, [gaps]);

  return (
    <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', width: '100%' }}>
      {/* Donut chart */}
      <div style={{ flex: '1 1 300px', minWidth: 280, height: 320 }}>
        <p style={{ color: '#94a3b8', fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
          Gaps by Type
        </p>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={pieData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={100}
              paddingAngle={3}
              dataKey="value"
              nameKey="name"
              stroke="none"
            >
              {pieData.map((entry, idx) => (
                <Cell key={idx} fill={getColor(entry.name, idx)} />
              ))}
            </Pie>
            <Tooltip content={<TooltipContent />} />
            <Legend
              wrapperStyle={{ fontSize: 12, color: '#94a3b8' }}
              formatter={(v: string) => <span style={{ color: '#cbd5e1' }}>{v}</span>}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Bar chart */}
      <div style={{ flex: '1 1 340px', minWidth: 300, height: 320 }}>
        <p style={{ color: '#94a3b8', fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
          Cost by Severity (Crores)
        </p>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={barData} margin={{ top: 10, right: 10, left: 0, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
            <XAxis
              dataKey="severity"
              tick={{ fill: '#94a3b8', fontSize: 12 }}
              axisLine={{ stroke: '#334155' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: '#94a3b8', fontSize: 12 }}
              axisLine={{ stroke: '#334155' }}
              tickLine={false}
            />
            <Tooltip content={<TooltipContent />} />
            <Bar dataKey="cost" name="Cost (Cr)" radius={[6, 6, 0, 0]} barSize={36}>
              {barData.map((entry, idx) => (
                <Cell key={idx} fill={severityColors[entry.severity] || '#64748b'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default InfrastructureGapChart;
