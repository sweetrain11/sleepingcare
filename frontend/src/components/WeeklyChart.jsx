import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Area, AreaChart
} from 'recharts'

/**
 * WeeklyChart.jsx
 * Recharts AreaChart 기반 주간/월간 수면 점수 추이 차트
 * props: data (배열), range ('week' | 'month')
 */

// 커스텀 툴팁
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const score = payload[0]?.value
  const color = score >= 85 ? '#22c55e' : score >= 70 ? '#84cc16' : score >= 55 ? '#f59e0b' : '#ef4444'

  return (
    <div className="bg-white border border-cream-200 rounded-xl shadow-card px-4 py-3 text-sm">
      <p className="text-gray-500 mb-1">{label}</p>
      <p className="font-display text-xl" style={{ color }}>{score}점</p>
    </div>
  )
}

// 빈 데이터 플레이스홀더
function EmptyChart() {
  return (
    <div className="flex flex-col items-center justify-center h-48 gap-3">
      <svg className="w-10 h-10 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
      <p className="text-sm text-gray-400">아직 수면 데이터가 없어요</p>
    </div>
  )
}

export default function WeeklyChart({ data = [], range = 'week' }) {
  if (!data || data.length === 0) return <EmptyChart />

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#2563c4" stopOpacity={0.18} />
            <stop offset="95%" stopColor="#2563c4" stopOpacity={0} />
          </linearGradient>
        </defs>

        <CartesianGrid strokeDasharray="3 3" stroke="#e8e7e3" vertical={false} />

        <XAxis
          dataKey="label"
          tick={{ fontSize: 12, fill: '#9ca3af', fontFamily: 'DM Sans' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fontSize: 11, fill: '#9ca3af', fontFamily: 'DM Sans' }}
          axisLine={false}
          tickLine={false}
          ticks={[0, 25, 50, 75, 100]}
        />

        {/* 목표선 (70점) */}
        <ReferenceLine
          y={70}
          stroke="#84cc16"
          strokeDasharray="4 4"
          strokeWidth={1.5}
          label={{ value: '목표', position: 'right', fontSize: 10, fill: '#84cc16' }}
        />

        <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#c7d7ee', strokeWidth: 1 }} />

        <Area
          type="monotone"
          dataKey="score"
          stroke="#1e3a5f"
          strokeWidth={2.5}
          fill="url(#scoreGradient)"
          dot={{ r: 4, fill: '#1e3a5f', strokeWidth: 0 }}
          activeDot={{ r: 6, fill: '#2563c4', stroke: 'white', strokeWidth: 2 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
