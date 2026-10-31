import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

export function DamCapacityChart({ dams = [], height = 240 }) {
  const chartData = dams.map((d) => ({
    name: d.name?.split(' ')[0] || d.dam_id || 'Dam',
    storagePct: d.fill_percentage != null ? d.fill_percentage : 72,
    outflowCusecs: d.spillway_outflow_cusecs || 0,
  }));

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E8F0EC" vertical={false} />
          <XAxis dataKey="name" stroke="#687B78" fontSize={11} tickLine={false} />
          <YAxis stroke="#687B78" fontSize={11} domain={[0, 100]} unit="%" tickLine={false} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#FFFFFF',
              borderColor: '#DFEAE6',
              color: '#152E2B',
              borderRadius: '8px',
              boxShadow: '0 4px 12px rgba(9, 47, 43, 0.08)',
            }}
            formatter={(val, name) => [name === 'Live Storage Fill' ? `${val}%` : `${val} cusecs`, name]}
          />
          <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
          <Bar dataKey="storagePct" name="Live Storage Fill" fill="#24B6A0" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default DamCapacityChart;
