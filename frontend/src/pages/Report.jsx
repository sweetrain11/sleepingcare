import { useState, useEffect } from 'react'
import WeeklyChart from '../components/WeeklyChart'

function scoreColor(score) {
  if (!score) return '#e5e7eb'
  if (score >= 85) return '#22c55e'
  if (score >= 70) return '#84cc16'
  if (score >= 55) return '#f59e0b'
  return '#ef4444'
}

/**
 * 수면 날짜 표시 기준: "취침 날짜" (수면 시작이 자정~정오 사이면 전날로 처리)
 * 예) 00:30 5/26 취침 → "5월 25일" 표시 (전날 밤 수면으로 인식)
 *     23:40 5/27 취침 → "5월 27일" 표시
 */
function sleepNightDate(startTimeStr) {
  const d = new Date(startTimeStr)
  if (d.getHours() < 12) {
    d.setDate(d.getDate() - 1)
  }
  return d
}

function sleepNightLabel(startTimeStr, options = {}) {
  return sleepNightDate(startTimeStr).toLocaleDateString('ko-KR', options)
}

function scoreLabel(score) {
  if (!score) return '—'
  if (score >= 85) return '매우 좋음'
  if (score >= 70) return '좋음'
  if (score >= 55) return '보통'
  return '나쁨'
}

// ── 항목별 점수 + 한 줄 설명 ──────────────────────────
function metaTemp(v) {
  if (v == null) return { score: 5, hint: '센서 데이터 없음' }
  if (v >= 15 && v <= 19) return { score: 10, hint: '최적 온도예요' }
  if ((v >= 13 && v < 15) || (v > 19 && v <= 21)) return { score: 6, hint: '적정 범위에 가까워요' }
  if (v > 21 && v <= 23) return { score: 3, hint: '조금 더 서늘하게 해보세요' }
  return { score: 0, hint: '수면에 적합하지 않은 온도예요' }
}

function metaHumidity(v) {
  if (v == null) return { score: 5, hint: '센서 데이터 없음' }
  if (v >= 40 && v <= 60) return { score: 10, hint: '최적 습도예요' }
  if ((v >= 35 && v < 40) || (v > 60 && v <= 65)) return { score: 6, hint: '적정 범위에 가까워요' }
  if ((v >= 30 && v < 35) || (v > 65 && v <= 70)) return { score: 3, hint: '습도 조절이 필요해요' }
  return { score: 0, hint: '습도가 수면을 방해하고 있어요' }
}

function metaLight(v) {
  if (v == null) return { score: 5, hint: '센서 데이터 없음' }
  if (v <= 5) return { score: 10, hint: '수면에 최적인 어둠이에요' }
  if (v <= 10) return { score: 8, hint: '약간 밝아요' }
  if (v <= 30) return { score: 5, hint: '더 어둡게 해보세요' }
  if (v <= 100) return { score: 2, hint: '빛이 수면을 방해해요' }
  return { score: 0, hint: '너무 밝아요' }
}

function metaSound(v) {
  if (v == null) return { score: 5, hint: '센서 데이터 없음' }
  if (v < 30) return { score: 10, hint: '조용한 환경이에요' }
  if (v < 40) return { score: 7, hint: '약간의 소음이 있어요' }
  if (v < 55) return { score: 4, hint: '소음을 줄여보세요' }
  if (v < 65) return { score: 1, hint: '소음이 수면을 방해해요' }
  return { score: 0, hint: '소음이 너무 심해요' }
}

function metaDuration(min) {
  if (min == null) return { score: 10, hint: '데이터 없음' }
  if (min >= 420 && min <= 540) return { score: 20, hint: '권장 수면 시간이에요' }
  if ((min >= 360 && min < 420) || (min > 540 && min <= 600)) return { score: 15, hint: '권장 범위에 가까워요' }
  if ((min >= 300 && min < 360) || (min > 600 && min <= 660)) return { score: 10, hint: '수면 시간을 조절해보세요' }
  if ((min >= 240 && min < 300) || min > 660) return { score: 5, hint: '권장 범위에서 많이 벗어났어요' }
  return { score: 0, hint: '수면이 너무 짧아요' }
}

function metaRegularity(diff) {
  if (diff == null) return { score: 10, hint: '첫 세션이에요' }
  if (diff < 30) return { score: 20, hint: '규칙적인 취침이에요' }
  if (diff < 60) return { score: 15, hint: '취침 시간이 조금 불규칙해요' }
  if (diff < 90) return { score: 10, hint: '취침 편차가 크네요' }
  if (diff < 120) return { score: 5, hint: '취침 시간이 많이 불규칙해요' }
  return { score: 0, hint: '취침 불규칙이 심해요' }
}

function metaMotion(count) {
  const c = count ?? 0
  if (c < 5) return { score: 20, hint: '거의 움직임이 없었어요' }
  if (c < 10) return { score: 15, hint: '뒤척임이 적었어요' }
  if (c < 15) return { score: 10, hint: '뒤척임이 있었어요' }
  if (c < 20) return { score: 5, hint: '뒤척임이 많았어요' }
  return { score: 0, hint: '뒤척임이 매우 많았어요' }
}

function ScoreHint({ score, max, hint }) {
  const ratio = score / max
  const color = ratio >= 0.8 ? '#22c55e' : ratio >= 0.5 ? '#f59e0b' : '#ef4444'
  return (
    <div className="mt-1.5 space-y-0.5">
      <span className="text-xs font-semibold" style={{ color }}>{score}/{max}점</span>
      <p className="text-xs text-gray-400 leading-tight">{hint}</p>
    </div>
  )
}

// ── 1일 상세 뷰 ─────────────────────────────────────
function DayDetail({ session }) {
  if (!session) return (
    <div className="card p-12 flex flex-col items-center justify-center text-center">
      <svg className="w-12 h-12 text-gray-200 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
      </svg>
      <p className="text-sm text-gray-400">완료된 수면 세션이 없어요</p>
    </div>
  )

  const dur = session.duration_min || 0
  const color = scoreColor(session.total_score)

  const envItems = [
    { label: '온도', value: session.avg_temperature != null ? `${session.avg_temperature.toFixed(1)}°C` : '—', meta: metaTemp(session.avg_temperature), max: 10 },
    { label: '습도', value: session.avg_humidity != null ? `${session.avg_humidity.toFixed(0)}%` : '—', meta: metaHumidity(session.avg_humidity), max: 10 },
    { label: '조도', value: session.avg_light != null ? `${session.avg_light.toFixed(1)} lux` : '—', meta: metaLight(session.avg_light), max: 10 },
    { label: '소음', value: session.avg_sound != null ? `${session.avg_sound.toFixed(1)} dB` : '—', meta: metaSound(session.avg_sound), max: 10 },
  ]

  const patternItems = [
    { label: '수면 시간',   value: `${Math.floor(dur / 60)}h ${dur % 60}m`, meta: metaDuration(session.duration_min), max: 20 },
    { label: '취침 규칙성', value: session.regularity_diff_min != null ? `편차 ${session.regularity_diff_min}분` : '첫 세션', meta: metaRegularity(session.regularity_diff_min), max: 20 },
    { label: '뒤척임',     value: `${session.motion_count ?? 0}회`, meta: metaMotion(session.motion_count), max: 20 },
  ]

  return (
    <div className="space-y-6">
      {/* 세션 헤더 */}
      <div className="card p-6">
        <div className="flex flex-col md:flex-row md:items-center gap-6">
          {/* 총점 */}
          <div className="flex flex-col items-center justify-center min-w-[120px]">
            <p className="font-display text-6xl font-bold" style={{ color }}>{session.total_score ?? '—'}</p>
            <p className="text-sm font-medium mt-1" style={{ color }}>{scoreLabel(session.total_score)}</p>
            <p className="text-xs text-gray-400 mt-0.5">/ 100점</p>
          </div>

          <div className="flex-1 space-y-3">
            {/* 날짜 & 시간 */}
            <div>
              <p className="font-medium text-gray-800">
                {sleepNightLabel(session.start_time, {
                  year: 'numeric', month: 'long', day: 'numeric', weekday: 'short',
                })}
              </p>
              <p className="text-sm text-gray-500 mt-0.5">
                {new Date(session.start_time).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
                {' → '}
                {session.end_time
                  ? new Date(session.end_time).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
                  : '—'}
                {' · '}
                {Math.floor(dur / 60)}시간 {dur % 60}분
              </p>
            </div>

            {/* 환경/패턴 점수 요약 바 */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-blue-50 rounded-xl p-3">
                <p className="text-xs text-gray-400">환경 점수</p>
                <div className="flex items-end gap-1 mt-0.5">
                  <span className="font-display text-2xl text-indigo-900">{session.env_score ?? '—'}</span>
                  <span className="text-xs text-gray-400 mb-0.5">/ 40</span>
                </div>
              </div>
              <div className="bg-purple-50 rounded-xl p-3">
                <p className="text-xs text-gray-400">패턴 점수</p>
                <div className="flex items-end gap-1 mt-0.5">
                  <span className="font-display text-2xl text-indigo-900">{session.pattern_score ?? '—'}</span>
                  <span className="text-xs text-gray-400 mb-0.5">/ 60</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 환경 점수 상세 */}
      <div className="card p-6">
        <p className="section-label mb-4">환경 점수 상세</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {envItems.map((item) => (
            <div key={item.label} className="bg-cream-50 rounded-xl p-4">
              <p className="text-xs text-gray-400 mb-1">{item.label}</p>
              <p className="font-display text-lg text-indigo-900">{item.value}</p>
              <ScoreHint score={item.meta.score} max={item.max} hint={item.meta.hint} />
            </div>
          ))}
        </div>
      </div>

      {/* 패턴 점수 상세 */}
      <div className="card p-6">
        <p className="section-label mb-4">패턴 점수 상세</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {patternItems.map((item) => (
            <div key={item.label} className="bg-cream-50 rounded-xl p-4">
              <p className="text-xs text-gray-400 mb-1">{item.label}</p>
              <p className="font-display text-xl text-indigo-900">{item.value}</p>
              <ScoreHint score={item.meta.score} max={item.max} hint={item.meta.hint} />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── 7일 가로 캘린더 ──────────────────────────────────
function WeekCalendar({ sessions }) {
  const scoreMap = {}
  if (sessions) {
    sessions.forEach((s) => {
      const d = sleepNightDate(s.start_time)
      const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
      if (!scoreMap[key] || (s.total_score ?? 0) > scoreMap[key]) {
        scoreMap[key] = s.total_score
      }
    })
  }

  const today = new Date()
  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(today)
    d.setDate(today.getDate() - 6 + i)
    return d
  })

  const DAY_LABELS = ['일', '월', '화', '수', '목', '금', '토']

  return (
    <div>
      <div className="grid grid-cols-7 gap-2">
        {days.map((d) => {
          const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
          const score = scoreMap[key]
          const isToday = d.toDateString() === today.toDateString()
          const color = scoreColor(score)
          return (
            <div key={key} className="flex flex-col items-center gap-1.5">
              <span className="text-xs font-medium text-gray-400">{DAY_LABELS[d.getDay()]}</span>
              <div
                className="w-full aspect-square rounded-xl flex flex-col items-center justify-center relative transition-transform hover:scale-105"
                style={{
                  backgroundColor: score ? `${color}22` : '#f9fafb',
                  border: isToday ? `2px solid ${color || '#1e3a5f'}` : '1px solid #f3f4f6',
                }}
                title={score ? `${d.getMonth()+1}/${d.getDate()} · ${score}점` : `${d.getMonth()+1}/${d.getDate()}`}
              >
                <span className="text-xs font-medium" style={{ color: score ? color : '#9ca3af' }}>
                  {d.getDate()}
                </span>
                {score && <span className="text-[10px] font-bold" style={{ color }}>{score}</span>}
                {isToday && <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-indigo-600" />}
              </div>
            </div>
          )
        })}
      </div>
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

// ── 월간 수면 패턴 캘린더 ─────────────────────────────────
function SleepCalendar({ sessions }) {
  const today = new Date()
  const year = today.getFullYear()
  const month = today.getMonth()
  const firstDay = new Date(year, month, 1).getDay()
  const lastDate = new Date(year, month + 1, 0).getDate()

  const scoreMap = {}
  if (sessions) {
    sessions.forEach((s) => {
      const d = sleepNightDate(s.start_time)
      const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
      if (!scoreMap[key] || (s.total_score ?? 0) > scoreMap[key]) {
        scoreMap[key] = s.total_score
      }
    })
  }

  const days = ['일', '월', '화', '수', '목', '금', '토']
  const cells = []
  for (let i = 0; i < firstDay; i++) cells.push(null)
  for (let d = 1; d <= lastDate; d++) cells.push(d)

  return (
    <div>
      <div className="grid grid-cols-7 mb-2">
        {days.map((d) => (
          <div key={d} className="text-center text-xs font-medium text-gray-400 py-1">{d}</div>
        ))}
      </div>
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
              className="aspect-square rounded-lg flex flex-col items-center justify-center relative cursor-default transition-transform hover:scale-110"
              style={{
                backgroundColor: score ? `${color}22` : '#f9fafb',
                border: isToday ? `2px solid ${color || '#1e3a5f'}` : '1px solid #f3f4f6',
              }}
              title={score ? `${date}일 · ${score}점` : `${date}일`}
            >
              <span className="text-xs font-medium" style={{ color: score ? color : '#9ca3af' }}>{date}</span>
              {score && <span className="text-[9px] font-semibold" style={{ color }}>{score}</span>}
              {isToday && <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-indigo-600" />}
            </div>
          )
        })}
      </div>
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

// ── 세션 목록 (인라인 토글 상세) ─────────────────────────
function SessionList({ sessions }) {
  const [expandedIds, setExpandedIds] = useState(new Set())

  function toggleId(id) {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  return (
    <div className="card p-6">
      <p className="section-label mb-4">수면 세션 기록</p>
      <div className="space-y-2">
        {sessions.map((s) => {
          const color = scoreColor(s.total_score)
          const dur = s.duration_min || 0
          const isOpen = expandedIds.has(s.session_id)

          const envItems = [
            { label: '온도', value: s.avg_temperature != null ? `${s.avg_temperature.toFixed(1)}°C` : '—', meta: metaTemp(s.avg_temperature), max: 10 },
            { label: '습도', value: s.avg_humidity    != null ? `${s.avg_humidity.toFixed(0)}%`      : '—', meta: metaHumidity(s.avg_humidity), max: 10 },
            { label: '조도', value: s.avg_light       != null ? `${s.avg_light.toFixed(1)} lux`     : '—', meta: metaLight(s.avg_light), max: 10 },
            { label: '소음', value: s.avg_sound       != null ? `${s.avg_sound.toFixed(1)} dB`      : '—', meta: metaSound(s.avg_sound), max: 10 },
          ]
          const patternItems = [
            { label: '수면 시간',   value: `${Math.floor(dur / 60)}h ${dur % 60}m`, meta: metaDuration(s.duration_min), max: 20 },
            { label: '취침 규칙성', value: s.regularity_diff_min != null ? `편차 ${s.regularity_diff_min}분` : '첫 세션', meta: metaRegularity(s.regularity_diff_min), max: 20 },
            { label: '뒤척임',     value: `${s.motion_count ?? 0}회`, meta: metaMotion(s.motion_count), max: 20 },
          ]

          return (
            <div key={s.session_id} className="rounded-xl border border-cream-200 overflow-hidden">
              {/* 행 */}
              <div
                className="flex items-center justify-between p-3 bg-cream-50 cursor-pointer hover:bg-cream-100 transition-colors"
                onClick={() => toggleId(s.session_id)}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-2 h-10 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-800">
                      {sleepNightLabel(s.start_time, { month: 'long', day: 'numeric', weekday: 'short' })}
                    </p>
                    <p className="text-xs text-gray-400 truncate">
                      {new Date(s.start_time).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
                      {' → '}
                      {s.end_time ? new Date(s.end_time).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }) : '—'}
                      {' · '}{Math.floor(dur / 60)}h {dur % 60}m
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <div className="text-right">
                    <p className="font-display text-lg" style={{ color }}>{s.total_score}점</p>
                    <p className="text-xs text-gray-400">환경 {s.env_score} / 패턴 {s.pattern_score}</p>
                  </div>
                  <svg
                    className="w-4 h-4 text-gray-400 transition-transform duration-200 flex-shrink-0"
                    style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)' }}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>

              {/* 토글 상세 */}
              {isOpen && (
                <div className="p-4 bg-white border-t border-cream-200 space-y-4">
                  {/* 점수 요약 */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-blue-50 rounded-xl p-3">
                      <p className="text-xs text-gray-400">환경 점수</p>
                      <div className="flex items-end gap-1 mt-0.5">
                        <span className="font-display text-2xl text-indigo-900">{s.env_score ?? '—'}</span>
                        <span className="text-xs text-gray-400 mb-0.5">/ 40</span>
                      </div>
                    </div>
                    <div className="bg-purple-50 rounded-xl p-3">
                      <p className="text-xs text-gray-400">패턴 점수</p>
                      <div className="flex items-end gap-1 mt-0.5">
                        <span className="font-display text-2xl text-indigo-900">{s.pattern_score ?? '—'}</span>
                        <span className="text-xs text-gray-400 mb-0.5">/ 60</span>
                      </div>
                    </div>
                  </div>

                  {/* 환경 상세 */}
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">환경</p>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      {envItems.map((item) => (
                        <div key={item.label} className="bg-cream-50 rounded-xl p-3">
                          <p className="text-xs text-gray-400">{item.label}</p>
                          <p className="font-display text-base text-indigo-900 mt-0.5">{item.value}</p>
                          <ScoreHint score={item.meta.score} max={item.max} hint={item.meta.hint} />
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 패턴 상세 */}
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">패턴</p>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                      {patternItems.map((item) => (
                        <div key={item.label} className="bg-cream-50 rounded-xl p-3 flex items-start justify-between sm:flex-col sm:items-start">
                          <p className="text-xs text-gray-400">{item.label}</p>
                          <div className="text-right sm:text-left">
                            <p className="font-display text-base text-indigo-900 mt-0.5">{item.value}</p>
                            <ScoreHint score={item.meta.score} max={item.max} hint={item.meta.hint} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── 메인 Report 컴포넌트 ─────────────────────────────
export default function Report() {
  const [range, setRange] = useState('day')
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

  // 차트 데이터 (week/month만 사용)
  const chartData = sessions.map((s) => ({
    label: sleepNightLabel(s.start_time, { month: 'short', day: 'numeric' }),
    score: s.total_score,
  })).reverse()

  // 통계 (week/month)
  const scores = sessions.map((s) => s.total_score).filter(Boolean)
  const avgScore    = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : null
  const maxScore    = scores.length ? Math.max(...scores) : null
  const minScore    = scores.length ? Math.min(...scores) : null
  const avgDuration = sessions.length
    ? Math.round(sessions.reduce((a, s) => a + (s.duration_min || 0), 0) / sessions.length)
    : null

  const stats = [
    { label: '평균 점수',     value: avgScore    ? `${avgScore}점`    : '—', sub: `${scores.length}회 수면` },
    { label: '최고 점수',     value: maxScore    ? `${maxScore}점`    : '—', sub: '이번 기간 최고' },
    { label: '최저 점수',     value: minScore    ? `${minScore}점`    : '—', sub: '이번 기간 최저' },
    { label: '평균 수면 시간', value: avgDuration ? `${Math.floor(avgDuration / 60)}h ${avgDuration % 60}m` : '—', sub: '권장 7~9시간' },
  ]

  const TABS = [
    { value: 'day',   label: '1일' },
    { value: 'week',  label: '7일' },
    { value: 'month', label: '30일' },
  ]

  return (
    <div className="space-y-8 animate-stagger">
      {/* 헤더 */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div>
          <h1 className="page-title">리포트</h1>
          <p className="page-subtitle">수면 점수 추이와 패턴을 분석해요</p>
        </div>
        {/* 기간 탭 */}
        <div className="flex gap-1 bg-cream-100 rounded-xl p-1 border border-cream-200 self-start">
          {TABS.map((opt) => (
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

      {isLoading ? (
        <div className="card p-12 flex items-center justify-center">
          <div className="w-8 h-8 rounded-full border-4 border-indigo-200 border-t-indigo-500 animate-spin" />
        </div>
      ) : range === 'day' ? (
        /* ── 1일 상세 뷰 ── */
        <DayDetail session={sessions[0] ?? null} />
      ) : (
        /* ── 7일 / 30일 뷰 ── */
        <>
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
            <div className="mb-6">
              <p className="section-label">수면 점수 추이</p>
              <p className="text-sm text-gray-500 mt-1">
                {range === 'week' ? '최근 7일' : '최근 30일'} 수면 점수 변화
              </p>
            </div>
            <WeeklyChart data={chartData} range={range} />
          </div>

          {/* 수면 패턴 캘린더 */}
          <div className="card p-6">
            <div className="mb-6">
              <p className="section-label">수면 패턴 캘린더</p>
              <p className="text-sm text-gray-500 mt-1">
                {range === 'week'
                  ? '최근 7일'
                  : new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long' })}
              </p>
            </div>
            {range === 'week'
              ? <WeekCalendar sessions={sessions} />
              : <SleepCalendar sessions={sessions} />}
          </div>

          {/* 세션 목록 */}
          {sessions.length > 0 && (
            <SessionList sessions={sessions} />
          )}
        </>
      )}
    </div>
  )
}
