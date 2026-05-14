import { useState, useEffect } from 'react'
import SensorCard from '../components/SensorCard'
import ScoreGauge from '../components/ScoreGauge'
import { useWebSocket } from '../hooks/useWebSocket'

/**
 * Dashboard.jsx
 * - 실시간 센서 카드 6개 (WebSocket)
 * - 오늘 수면 점수 게이지 (REST API)
 * - 연결 상태 표시
 */
export default function Dashboard() {
  const { sensorData, isConnected, lastUpdated } = useWebSocket()
  const [todaySession, setTodaySession] = useState(null)
  const [isLoadingScore, setIsLoadingScore] = useState(true)

  // 오늘 가장 최근 수면 세션 불러오기
  useEffect(() => {
    async function fetchTodayScore() {
      try {
        const res = await fetch('/api/sleep/history?range=week')
        if (!res.ok) throw new Error()
        const data = await res.json()
        // 가장 최근 세션 사용
        if (data?.sessions?.length > 0) {
          setTodaySession(data.sessions[0])
        }
      } catch {
        // 에러 시 null 유지
      } finally {
        setIsLoadingScore(false)
      }
    }
    fetchTodayScore()
  }, [])

  // 센서 데이터 매핑
  const sensors = [
    { type: 'temperature', value: sensorData?.temperature ?? null, unit: '°C', label: '온도' },
    { type: 'humidity',    value: sensorData?.humidity    ?? null, unit: '%',  label: '습도' },
    { type: 'light',       value: sensorData?.light       ?? null, unit: '',   label: '조도' },
    { type: 'sound',       value: sensorData?.sound       ?? null, unit: '',   label: '소음' },
    { type: 'motion',      value: sensorData?.motion      ?? null, unit: '',   label: 'PIR 모션' },
    { type: 'time',        value: sensorData?.arduino_time ?? null, unit: '',   label: '측정 시각' },
  ]

  // 마지막 업데이트 포맷
  const lastUpdatedStr = lastUpdated
    ? lastUpdated.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : null

  return (
    <div className="space-y-8 animate-stagger">
      {/* 페이지 헤더 */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="page-title">대시보드</h1>
          <p className="page-subtitle">수면 환경을 실시간으로 모니터링해요</p>
        </div>
        {/* 연결 상태 */}
        <div className="flex items-center gap-2 bg-white border border-cream-200 rounded-xl px-4 py-2 shadow-sm">
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400 animate-pulse' : 'bg-gray-300'}`} />
          <span className="text-sm text-gray-600">
            {isConnected ? 'Live' : '연결 끊김'}
          </span>
          {lastUpdatedStr && (
            <span className="text-xs text-gray-400 ml-1">{lastUpdatedStr}</span>
          )}
        </div>
      </div>

      {/* 메인 그리드: 점수 + 센서 */}
      <div className="grid grid-cols-12 gap-6">
        {/* 오늘 수면 점수 카드 */}
        <div className="col-span-12 lg:col-span-4">
          <div className="card p-6 h-full flex flex-col">
            <div className="mb-4">
              <p className="section-label">오늘의 수면 점수</p>
            </div>
            <div className="flex-1 flex flex-col items-center justify-center py-4">
              {isLoadingScore ? (
                <div className="flex flex-col items-center gap-3">
                  <div className="w-40 h-40 rounded-full border-8 border-cream-200 animate-pulse" />
                  <div className="w-20 h-4 bg-cream-200 rounded animate-pulse" />
                </div>
              ) : todaySession ? (
                <>
                  <ScoreGauge score={todaySession.total_score ?? 0} size={180} />
                  <div className="mt-4 w-full grid grid-cols-2 gap-3">
                    <div className="bg-cream-50 rounded-xl p-3 text-center">
                      <p className="text-xs text-gray-400 mb-1">환경 점수</p>
                      <p className="font-display text-2xl text-indigo-900">{todaySession.env_score}</p>
                      <p className="text-xs text-gray-400">/ 40</p>
                    </div>
                    <div className="bg-cream-50 rounded-xl p-3 text-center">
                      <p className="text-xs text-gray-400 mb-1">패턴 점수</p>
                      <p className="font-display text-2xl text-indigo-900">{todaySession.pattern_score}</p>
                      <p className="text-xs text-gray-400">/ 60</p>
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-center space-y-3">
                  <div className="w-20 h-20 rounded-full bg-cream-100 flex items-center justify-center mx-auto">
                    <svg className="w-8 h-8 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                    </svg>
                  </div>
                  <p className="text-sm text-gray-400">아직 수면 세션이 없어요</p>
                  <p className="text-xs text-gray-400">수면을 완료하면 점수가 표시돼요</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 센서 카드 6개 */}
        <div className="col-span-12 lg:col-span-8">
          <div className="mb-3">
            <p className="section-label">실시간 센서</p>
          </div>
          <div className="grid grid-cols-2 xl:grid-cols-3 gap-4 animate-stagger">
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

      {/* 수면 상태 요약 (세션 있을 때) */}
      {todaySession && (
        <div className="card p-5">
          <p className="section-label mb-4">마지막 수면 세션 요약</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: '수면 시간', value: `${Math.floor((todaySession.duration_min || 0) / 60)}h ${(todaySession.duration_min || 0) % 60}m` },
              { label: '평균 온도', value: `${(todaySession.avg_temperature || 0).toFixed(1)}°C` },
              { label: '평균 습도', value: `${(todaySession.avg_humidity || 0).toFixed(1)}%` },
              { label: '뒤척임 횟수', value: `${todaySession.motion_count || 0}회` },
            ].map((item) => (
              <div key={item.label} className="bg-cream-50 rounded-xl p-3">
                <p className="text-xs text-gray-400 mb-1">{item.label}</p>
                <p className="font-display text-xl text-indigo-900">{item.value}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
