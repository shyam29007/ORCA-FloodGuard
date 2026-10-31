import React from 'react';
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

export function RainfallChart({ rainfall24h = 42.5, rainfall48h = 75.0, rainfall72h = 110.0, height = 240 }) {
  const data = [
    { horizon: '24 Hours', amount: rainfall24h || 0 },
    { horizon: '48 Hours', amount: rainfall48h || 0 },
    { horizon: '72 Hours', amount: rainfall72h || 0 },
  ];

  const getColor = (val) => {
    if (val >= 120) return '#D94A4A'; // Critical
    if (val >= 75) return '#EA5454';  // High
    if (val >= 40) return '#E99A36';  // Moderate
    return '#16865F';                 // Normal
  };

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E8F0EC" vertical={false} />
          <XAxis dataKey="horizon" stroke="#687B78" fontSize={12} tickLine={false} />
          <YAxis stroke="#687B78" fontSize={12} tickLine={false} unit=" mm" />
          <Tooltip
            contentStyle={{
              backgroundColor: '#FFFFFF',
              borderColor: '#DFEAE6',
              color: '#152E2B',
              borderRadius: '8px',
              boxShadow: '0 4px 12px rgba(9, 47, 43, 0.08)',
            }}
            formatter={(value) => [`${value} mm`, 'Rainfall']}
          />
          <ReferenceLine y={40} stroke="#E99A36" strokeDasharray="3 3" label={{ value: 'Moderate (40mm)', fill: '#E99A36', fontSize: 10 }} />
          <ReferenceLine y={75} stroke="#EA5454" strokeDasharray="3 3" label={{ value: 'High (75mm)', fill: '#EA5454', fontSize: 10 }} />
          <ReferenceLine y={120} stroke="#D94A4A" strokeDasharray="3 3" label={{ value: 'Critical (120mm)', fill: '#D94A4A', fontSize: 10 }} />
          <Bar dataKey="amount" radius={[6, 6, 0, 0]}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getColor(entry.amount)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default RainfallChart;
