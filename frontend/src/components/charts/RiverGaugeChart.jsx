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

export function RiverGaugeChart({ stations = [], readings = {}, height = 260 }) {
  const chartData = stations.map((st) => {
    const reading = readings[st.station_id] || {};
    return {
      name: st.name?.split(' ')[0] || st.station_id || 'Gauge',
      current: reading.water_level_meters || st.warning_level_meters - 0.4,
      warning: st.warning_level_meters || 235,
      danger: st.danger_level_meters || 236,
    };
  });

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E8F0EC" vertical={false} />
          <XAxis dataKey="name" stroke="#687B78" fontSize={11} tickLine={false} />
          <YAxis stroke="#687B78" fontSize={11} domain={['dataMin - 3', 'dataMax + 2']} tickLine={false} unit=" m" />
          <Tooltip
            contentStyle={{
              backgroundColor: '#FFFFFF',
              borderColor: '#DFEAE6',
              color: '#152E2B',
              borderRadius: '8px',
              boxShadow: '0 4px 12px rgba(9, 47, 43, 0.08)',
            }}
            formatter={(val) => [`${Number(val).toFixed(2)} m`, '']}
          />
          <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
          <Bar dataKey="current" name="Current Stage" fill="#16865F" radius={[4, 4, 0, 0]} />
          <Bar dataKey="warning" name="Warning Threshold" fill="#E99A36" radius={[4, 4, 0, 0]} />
          <Bar dataKey="danger" name="Danger Limit" fill="#D94A4A" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default RiverGaugeChart;
