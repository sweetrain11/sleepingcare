import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import SensorCard from '../components/SensorCard'
import { useWebSocket } from '../hooks/useWebSocket'

/**
 * Dashboard.jsx
 * - 수면 제어 카드 (수동 시작/종료 + 현재 상태)
 * - 실시간 센서 카드 6개 (WebSocket)
 * - 연결 상태 표시
 */
export default function Dashboard() {
  const { sensorData, isConnected, lastUpdated, sleepState } = useWebSocket()

  // 수면 상태
  const [sleepStatus, setSleepStatus] = useState(null)
  const [isStatusLoading, setIsStatusLoading] = useState(true)
  const [isControlling, setIsControlling] = useState(false)
  const [controlMsg, setControlMsg] = useState(null)
  const [lastSession, setLastSession] = useState(null)   // 종료 후 결과 카드용

  // 수면 상태 조회
  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/sleep/status')
      if (!res.ok) throw new Error()
      const data = await res.json()
      setSleepStatus(data)
    } catch {
      setSleepStatus(null)
    } finally {
      setIsStatusLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  // 다른 클라이언트가 수면 시작/종료 시 WebSocket으로 즉시 반영
  useEffect(() => {
    if (sleepState === null) return
    setSleepStatus({
      is_sleeping: sleepState.is_sleeping,
      session_id: sleepState.session_id,
      start_time: sleepState.start_time,
    })
    setIsStatusLoading(false)
  }, [sleepState])

  // 수면 시작 / 종료 공통 핸들러
  const handleControl = async (action) => {
    setIsControlling(true)
    setControlMsg(null)
    try {
      const res = await fetch(`/api/sleep/${action}`, { method: 'POST' })
      const data = await res.json()
      setControlMsg({ ok: data.success, text: data.message })
      await fetchStatus()

      // 수면 종료 성공 시 세션 결과 조회
      if (action === 'end' && data.success && data.session_id) {
        try {
          const sr = await fetch(`/api/sleep/score/${data.session_id}`)
          if (sr.ok) setLastSession(await sr.json())
        } catch { /* 결과 조회 실패는 무시 */ }
      }
      // 수면 시작 시 이전 결과 초기화
      if (action === 'start' && data.success) {
        setLastSession(null)
      }
    } catch {
      setControlMsg({ ok: false, text: '서버 오류가 발생했어요' })
    } finally {
      setIsControlling(false)
      setTimeout(() => setControlMsg(null), 3000)
    }
  }

  // 센서 데이터 매핑
  const sensors = [
    { type: 'temperature', value: sensorData?.temperature ?? null, unit: '°C',  label: '온도' },
    { type: 'humidity',    value: sensorData?.humidity    ?? null, unit: '%',   label: '습도' },
    { type: 'light',       value: sensorData?.light       ?? null, unit: 'lux', label: '조도' },
    { type: 'sound',       value: sensorData?.sound       ?? null, unit: 'dB',  label: '소음' },
    { type: 'motion',      value: sensorData?.motion      ?? null, unit: '',    label: 'PIR 모션' },
    { type: 'time',        value: lastUpdated ?? null,              unit: '',   label: '측정 시각' },
  ]

  const isSleeping = sleepStatus?.is_sleeping ?? false

  // 수면 시작 시각 포맷
  const sleepStartStr = sleepStatus?.start_time
    ? new Date(sleepStatus.start_time).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
    : null

  return (
    <div className="space-y-8 animate-stagger">
      {/* 페이지 헤더 */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="page-title">대시보드</h1>
          <p className="page-subtitle">수면 환경을 실시간으로 모니터링해요</p>
        </div>
        {/* 연결 상태 */}
        <div className="flex items-center gap-2 bg-white border border-cream-200 rounded-xl px-3 py-2 shadow-sm flex-shrink-0">
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400 animate-pulse' : 'bg-gray-300'}`} />
          <span className="text-sm text-gray-600">
            {isConnected ? 'Live' : '끊김'}
          </span>
        </div>
      </div>

      {/* 메인 그리드: 수면 제어 + 센서 */}
      <div className="grid grid-cols-12 gap-6">

        {/* 수면 제어 카드 */}
        <div className="col-span-12 lg:col-span-4">
          <div className="card p-6 h-full flex flex-col">
            <div className="mb-5">
              <p className="section-label">수면 제어</p>
            </div>

            <div className="flex-1 flex flex-col items-center justify-center gap-6">

              {/* 현재 수면 상태 표시 */}
              {isStatusLoading ? (
                <div className="w-24 h-24 rounded-full bg-cream-100 animate-pulse" />
              ) : (
                <div className="flex flex-col items-center gap-3">
                  <div className={`w-24 h-24 rounded-full flex items-center justify-center transition-colors duration-500
                    ${isSleeping ? 'bg-indigo-100' : 'bg-amber-50'}`}>
                    {isSleeping ? (
                      /* 달 아이콘 */
                      <svg className="w-10 h-10 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                      </svg>
                    ) : (
                      /* 해 아이콘 */
                      <svg className="w-10 h-10 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0z" />
                      </svg>
                    )}
                  </div>

                  <div className="text-center">
                    <p className={`font-display text-xl font-semibold ${isSleeping ? 'text-indigo-600' : 'text-amber-500'}`}>
                      {isSleeping ? '수면 중' : '깨어있음'}
                    </p>
                    {isSleeping && sleepStartStr && (
                      <p className="text-xs text-gray-400 mt-1">{sleepStartStr}부터</p>
                    )}
                    <p className="text-xs text-gray-400 mt-1">● 자동 감지 중</p>
                  </div>
                </div>
              )}

              {/* 피드백 메시지 */}
              {controlMsg && (
                <p className={`text-xs px-3 py-1.5 rounded-lg ${
                  controlMsg.ok
                    ? 'bg-green-50 text-green-600'
                    : 'bg-red-50 text-red-500'
                }`}>
                  {controlMsg.text}
                </p>
              )}

              {/* 제어 버튼 */}
              <div className="flex flex-col gap-3 w-full">
                <button
                  onClick={() => handleControl('start')}
                  disabled={isControlling || isStatusLoading || isSleeping}
                  className={`w-full py-3 rounded-xl text-sm font-medium transition-all duration-200
                    ${isSleeping || isControlling || isStatusLoading
                      ? 'bg-gray-100 text-gray-300 cursor-not-allowed'
                      : 'bg-indigo-500 hover:bg-indigo-600 text-white shadow-sm hover:shadow-md active:scale-95'
                    }`}
                >
                  🌙 수면 시작
                </button>
                <button
                  onClick={() => handleControl('end')}
                  disabled={isControlling || isStatusLoading || !isSleeping}
                  className={`w-full py-3 rounded-xl text-sm font-medium transition-all duration-200
                    ${!isSleeping || isControlling || isStatusLoading
                      ? 'bg-gray-100 text-gray-300 cursor-not-allowed'
                      : 'bg-amber-400 hover:bg-amber-500 text-white shadow-sm hover:shadow-md active:scale-95'
                    }`}
                >
                  ☀️ 수면 종료
                </button>
              </div>

              <p className="text-xs text-gray-300 text-center">
                자동 감지가 안 될 때 수동으로 조작하세요
              </p>
            </div>
          </div>
        </div>

        {/* 센서 카드 6개 */}
        <div className="col-span-12 lg:col-span-8">
          <div className="mb-3">
            <p className="section-label">실시간 센서</p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-2 xl:grid-cols-3 gap-3 md:gap-4 animate-stagger">
            {sensors.map((s) => (
              <SensorCard
                key={s.type}
                type={s.type}
                value={s.value}
                unit={s.unit}
                label={s.label}
                isLoading={!isConnected && s.value === null}
              />
            ))}
          </div>
        </div>
      </div>

      {/* 수면 종료 결과 카드 */}
      {lastSession && (
        <div className="card p-6 border-l-4 border-indigo-400">
          <div className="flex items-center justify-between mb-4">
            <p className="section-label">방금 수면 결과</p>
            <button
              onClick={() => setLastSession(null)}
              className="text-gray-300 hover:text-gray-500 text-lg leading-none"
            >✕</button>
          </div>

          <div className="flex flex-col md:flex-row gap-6">
            {/* 총점 */}
            <div className="flex flex-col items-center justify-center min-w-[100px]">
              <p
                className="font-display text-5xl font-bold"
                style={{
                  color: lastSession.total_score >= 85 ? '#22c55e'
                       : lastSession.total_score >= 70 ? '#84cc16'
                       : lastSession.total_score >= 55 ? '#f59e0b'
                       : '#ef4444'
                }}
              >
                {lastSession.total_score}
              </p>
              <p className="text-xs text-gray-400 mt-1">/ 100점</p>
            </div>

            {/* 세션 정보 */}
            <div className="flex-1 space-y-3">
              {/* 시간 */}
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <span>
                  {new Date(lastSession.start_time).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
                  {' → '}
                  {lastSession.end_time
                    ? new Date(lastSession.end_time).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
                    : '—'}
                </span>
                <span className="text-gray-400">·</span>
                <span>{Math.floor((lastSession.duration_min || 0) / 60)}h {(lastSession.duration_min || 0) % 60}m</span>
              </div>

              {/* 점수 분해 */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-blue-50 rounded-xl p-3">
                  <p className="text-xs text-gray-400 mb-0.5">환경 점수</p>
                  <p className="font-display text-xl text-indigo-900">
                    {lastSession.env_score}
                    <span className="text-xs text-gray-400 font-normal"> / 40</span>
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    온도 {lastSession.avg_temperature?.toFixed(1)}°C · 습도 {lastSession.avg_humidity?.toFixed(0)}%
                  </p>
                </div>
                <div className="bg-purple-50 rounded-xl p-3">
                  <p className="text-xs text-gray-400 mb-0.5">패턴 점수</p>
                  <p className="font-display text-xl text-indigo-900">
                    {lastSession.pattern_score}
                    <span className="text-xs text-gray-400 font-normal"> / 60</span>
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    뒤척임 {lastSession.motion_count}회
                    {lastSession.regularity_diff_min != null && ` · 취침 편차 ${lastSession.regularity_diff_min}분`}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <Link
            to="/report"
            className="mt-4 flex items-center gap-1 text-sm text-indigo-500 hover:text-indigo-700 font-medium"
          >
            리포트에서 자세히 보기
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </Link>
        </div>
      )}
    </div>
  )
}
