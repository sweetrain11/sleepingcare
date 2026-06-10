/**
 * SensorCard.jsx
 * 개별 센서 값을 표시하는 카드 컴포넌트
 * props: type, value, unit, label, icon, status
 */

// 센서 타입별 설정 (색상, 정상 범위 표시)
const SENSOR_CONFIG = {
  temperature: {
    color: '#f97316',
    bgColor: '#fff7ed',
    borderColor: '#fed7aa',
    good: (v) => v >= 16 && v <= 20,
    hint: '적정 16~20°C',
  },
  humidity: {
    color: '#06b6d4',
    bgColor: '#ecfeff',
    borderColor: '#a5f3fc',
    good: (v) => v >= 40 && v <= 60,
    hint: '적정 40~60%',
  },
  light: {
    color: '#eab308',
    bgColor: '#fefce8',
    borderColor: '#fef08a',
    good: (v) => v <= 5,
    hint: '5 lux 이하 최적',
  },
  sound: {
    color: '#8b5cf6',
    bgColor: '#f5f3ff',
    borderColor: '#ddd6fe',
    good: (v) => v < 30,
    hint: '30 dB 이하 최적',
  },
  motion: {
    color: '#ec4899',
    bgColor: '#fdf2f8',
    borderColor: '#fbcfe8',
    good: (v) => !v,
    hint: '미감지 최적',
  },
  time: {
    color: '#1e3a5f',
    bgColor: '#eff6ff',
    borderColor: '#bfdbfe',
    good: () => true,
    hint: '마지막 수신 시각',
  },
}

// 센서 아이콘
function SensorIcon({ type }) {
  const icons = {
    temperature: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
      </svg>
    ),
    humidity: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 3C12 3 6 10 6 14a6 6 0 0012 0c0-4-6-11-6-11z" />
      </svg>
    ),
    light: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m8.66-9h-1M4.34 12h-1m15.07-6.07l-.71.71M6.34 17.66l-.71.71m12.73 0l-.71-.71M6.34 6.34l-.71-.71M12 7a5 5 0 100 10A5 5 0 0012 7z" />
      </svg>
    ),
    sound: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.536 8.464a5 5 0 010 7.072M12 6v12m0-12l-3.536 3.464A5 5 0 007 12m5-6l3.536 3.464A5 5 0 0117 12" />
      </svg>
    ),
    motion: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
    time: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  }
  return icons[type] || null
}

export default function SensorCard({ type, value, unit, label, isLoading = false }) {
  const config = SENSOR_CONFIG[type] || SENSOR_CONFIG.temperature
  const isGood = value !== null && value !== undefined ? config.good(value) : null

  // 값 포맷
  const displayValue = () => {
    if (isLoading || value === null || value === undefined) return '—'
    if (type === 'motion') return value ? '감지됨' : '없음'
    if (type === 'time') {
      try {
        return new Date(value).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      } catch { return value }
    }
    if (typeof value === 'number') return value.toFixed(type === 'temperature' || type === 'humidity' ? 1 : 0)
    return String(value)
  }

  return (
    <div
      className="card p-5 flex flex-col gap-3"
      style={{ borderTop: `3px solid ${config.color}` }}
    >
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div
          className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ backgroundColor: config.bgColor, color: config.color, border: `1px solid ${config.borderColor}` }}
        >
          <SensorIcon type={type} />
        </div>

        {/* 상태 배지 */}
        {!isLoading && value !== null && value !== undefined && type !== 'time' && (
          <span
            className="text-xs font-medium px-2 py-0.5 rounded-full"
            style={{
              backgroundColor: isGood ? '#dcfce7' : '#fef2f2',
              color: isGood ? '#15803d' : '#dc2626',
            }}
          >
            {isGood ? '정상' : '주의'}
          </span>
        )}
      </div>

      {/* 값 */}
      <div>
        <div className="flex items-end gap-1.5">
          <span
            className={`font-display text-3xl leading-none ${isLoading ? 'animate-pulse-soft text-gray-300' : ''}`}
            style={{ color: isLoading ? undefined : config.color }}
          >
            {displayValue()}
          </span>
          {unit && !isLoading && value !== null && (
            <span className="text-sm text-gray-400 mb-0.5">{unit}</span>
          )}
        </div>
        <p className="text-sm text-gray-600 font-medium mt-1">{label}</p>
      </div>

      {/* 힌트 */}
      <p className="text-xs text-gray-400">{config.hint}</p>
    </div>
  )
}
