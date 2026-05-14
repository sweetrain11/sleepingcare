import { useState, useEffect } from 'react'
import WeeklyChart from '../components/WeeklyChart'

/**
 * Report.jsx
 * - 주간/월간 수면 점수 차트
 * - 수면 패턴 캘린더 (월 단위)
 * - 통계 요약 카드
 */

// 점수 → 색상
function scoreColor(score) {
  if (!score) return '#e5e7eb'
  if (score >= 85) return '#22c55e'
  if (score >= 70) return '#84cc16'
  if (score >= 55) return '#f59e0b'
  return '#ef4444'
}

// 캘린더 컴포넌트
function SleepCalendar({ sessions }) {
  const today = new Date()
  const year = today.getFullYear()
  const month = today.getMonth()

  // 이번 달 첫날 요일 (0=일)
  const firstDay = new Date(year, month, 1).getDay()
  // 이번 달 마지막 날
  const lastDate = new Date(year, month + 1, 0).getDate()

  // session 날짜 → 점수 맵
  const scoreMap = {}
  if (sessions) {
    sessions.forEach((s) => {
      const d = new Date(s.start_time)
      const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
      scoreMap[key] = s.total_score
    })
  }

  const days = ['일', '월', '화', '수', '목', '금', '토']
  const cells = []

  // 빈 칸 (첫째 날 이전)
  for (let i = 0; i < firstDay; i++) {
    cells.push(null)
  }
  // 날짜 채우기
  for (let d = 1; d <= lastDate; d++) {
    cells.push(d)
  }

  return (
    <div>
      {/* 요일 헤더 */}
      <div className="grid grid-cols-7 mb-2">
        {days.map((d) => (
          <div key={d} className="text-center text-xs font-medium text-gray-400 py-1">
            {d}
          </div>
        ))}
      </div>
      {/* 날짜 그리드 */}
      <div className="grid grid-cols-7 gap-1.5">
        {cells.map((date, i) => {
          if (!date) return <div key={`empty-${i}`} />
          const key = `${year}-${month}-${date}`
          const score = scoreMap[key]
          const isToday = date === today.getDate()
          const color = scoreColor(score)

          return (
            <div
              key={key}
              className="aspect-square rounded-lg flex flex-col items-center justify-center relative group cursor-default transition-transform hover:scale-110"
              style={{
                backgroundColor: score ? `${color}22` : '#f9fafb',
                border: isToday ? `2px solid ${color || '#1e3a5f'}` : '1px solid #f3f4f6',
              }}
              title={score ? `${date}일 · ${score}점` : `${date}일`}
            >
              <span
                className="text-xs font-medium"
                style={{ color: score ? color : '#9ca3af' }}
              >
                {date}
              </span>
              {score && (
                <span className="text-[9px] font-semibold" style={{ color }}>
                  {score}
                </span>
              )}
              {/* 오늘 표시 */}
              {isToday && (
                <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-indigo-600" />
              )}
            </div>
          )
        })}
      </div>

      {/* 범례 */}
      <div className="flex items-center gap-4 mt-4 flex-wrap">
        {[
          { color: '#22c55e', label: '매우 좋음 (85+)' },
          { color: '#84cc16', label: '좋음 (70+)' },
          { color: '#f59e0b', label: '보통 (55+)' },
          { color: '#ef4444', label: '나쁨' },
          { color: '#e5e7eb', label: '데이터 없음' },
        ].map((item) => (
          <div key={item.label} className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: item.color }} />
            <span className="text-xs text-gray-400">{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Report() {
  const [range, setRange] = useState('week')
  const [sessions, setSessions] = useState([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function fetchHistory() {
      setIsLoading(true)
      try {
        const res = await fetch(`/api/sleep/history?range=${range}`)
        if (!res.ok) throw new Error()
        const data = await res.json()
        setSessions(data?.sessions || [])
      } catch {
        setSessions([])
      } finally {
        setIsLoading(false)
      }
    }
    fetchHistory()
  }, [range])

  // 차트 데이터 변환
  const chartData = sessions.map((s) => ({
    label: new Date(s.start_time).toLocaleDateString('ko-KR', {
      month: 'short', day: 'numeric',
    }),
    score: s.total_score,
  })).reverse()

  // 통계 계산
  const scores = sessions.map((s) => s.total_score).filter(Boolean)
  const avgScore = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : null
  const maxScore = scores.length ? Math.max(...scores) : null
  const minScore = scores.length ? Math.min(...scores) : null
  const avgDuration = sessions.length
    ? Math.round(sessions.reduce((a, s) => a + (s.duration_min || 0), 0) / sessions.length)
    : null

  const stats = [
    { label: '평균 점수', value: avgScore ? `${avgScore}점` : '—', sub: `${scores.length}회 수면` },
    { label: '최고 점수', value: maxScore ? `${maxScore}점` : '—', sub: '이번 기간 최고' },
    { label: '최저 점수', value: minScore ? `${minScore}점` : '—', sub: '이번 기간 최저' },
    {
      label: '평균 수면 시간',
      value: avgDuration ? `${Math.floor(avgDuration / 60)}h ${avgDuration % 60}m` : '—',
      sub: '권장 7~9시간',
    },
  ]

  return (
    <div className="space-y-8 animate-stagger">
      {/* 헤더 */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="page-title">리포트</h1>
          <p className="page-subtitle">수면 점수 추이와 패턴을 분석해요</p>
        </div>
        {/* 기간 선택 탭 */}
        <div className="flex gap-1 bg-cream-100 rounded-xl p-1 border border-cream-200">
          {[
            { value: 'week', label: '7일' },
            { value: 'month', label: '30일' },
          ].map((opt) => (
            <button
              key={opt.value}
              onClick={() => setRange(opt.value)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                range === opt.value
                  ? 'bg-indigo-900 text-white shadow-sm'
                  : 'text-gray-500 hover:text-indigo-900'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* 통계 요약 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s) => (
          <div key={s.label} className="card p-4">
            <p className="text-xs text-gray-400 mb-1">{s.label}</p>
            <p className="font-display text-2xl text-indigo-900">{s.value}</p>
            <p className="text-xs text-gray-400 mt-0.5">{s.sub}</p>
          </div>
        ))}
      </div>

      {/* 점수 차트 */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <p className="section-label">수면 점수 추이</p>
            <p className="text-sm text-gray-500 mt-1">
              {range === 'week' ? '최근 7일' : '최근 30일'} 수면 점수 변화
            </p>
          </div>
        </div>
        {isLoading ? (
          <div className="h-56 bg-cream-50 rounded-xl animate-pulse" />
        ) : (
          <WeeklyChart data={chartData} range={range} />
        )}
      </div>

      {/* 수면 패턴 캘린더 */}
      <div className="card p-6">
        <div className="mb-6">
          <p className="section-label">수면 패턴 캘린더</p>
          <p className="text-sm text-gray-500 mt-1">
            {new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long' })}
          </p>
        </div>
        <SleepCalendar sessions={sessions} />
      </div>

      {/* 세션 목록 */}
      {sessions.length > 0 && (
        <div className="card p-6">
          <p className="section-label mb-4">수면 세션 기록</p>
          <div className="space-y-3">
            {sessions.map((s) => {
              const color = scoreColor(s.total_score)
              const dur = s.duration_min || 0
              return (
                <div
                  key={s.id}
                  className="flex items-center justify-between p-3 rounded-xl bg-cream-50 border border-cream-200"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className="w-2 h-10 rounded-full flex-shrink-0"
                      style={{ backgroundColor: color }}
                    />
                    <div>
                      <p className="text-sm font-medium text-gray-800">
                        {new Date(s.start_time).toLocaleDateString('ko-KR', {
                          month: 'long', day: 'numeric', weekday: 'short',
                        })}
                      </p>
                      <p className="text-xs text-gray-400">
                        {new Date(s.start_time).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
                        {' → '}
                        {s.end_time
                          ? new Date(s.end_time).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
                          : '—'}
                        {' · '}
                        {Math.floor(dur / 60)}h {dur % 60}m
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-display text-xl" style={{ color }}>{s.total_score}점</p>
                    <p className="text-xs text-gray-400">환경 {s.env_score} / 패턴 {s.pattern_score}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
