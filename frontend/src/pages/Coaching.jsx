import { useState, useEffect } from 'react'
import CoachingCard from '../components/CoachingCard'

/**
 * Coaching.jsx
 * - 최근 수면 세션 목록 조회
 * - 세션 선택 후 AI 코칭 생성 요청
 * - 생성된 코칭 카드 목록 표시
 */
export default function Coaching() {
  const [sessions, setSessions] = useState([])
  const [coachingList, setCoachingList] = useState([])
  const [isLoadingSessions, setIsLoadingSessions] = useState(true)
  const [generatingId, setGeneratingId] = useState(null) // 생성 중인 세션 ID
  const [error, setError] = useState(null)

  // 수면 세션 목록 불러오기
  useEffect(() => {
    async function fetchSessions() {
      try {
        const res = await fetch('/api/sleep/history?range=month')
        if (!res.ok) throw new Error()
        const data = await res.json()
        setSessions(data?.sessions || [])
      } catch {
        setSessions([])
      } finally {
        setIsLoadingSessions(false)
      }
    }
    fetchSessions()
  }, [])

  // 기존 코칭 결과 불러오기 (세션 목록 기반으로 각 세션의 코칭 조회)
  useEffect(() => {
    if (!sessions.length) return
    async function fetchCoachings() {
      const results = []
      for (const session of sessions.slice(0, 5)) {
        try {
          const res = await fetch(`/api/sleep/score/${session.session_id}`)
          if (!res.ok) continue
          const data = await res.json()
          if (data?.coaching) {
            results.push({ session, coaching: data.coaching })
          }
        } catch { /* 무시 */ }
      }
      setCoachingList(results)
    }
    fetchCoachings()
  }, [sessions])

  // AI 코칭 생성 요청
  async function generateCoaching(session) {
    setGeneratingId(session.session_id)
    setError(null)
    try {
      const res = await fetch('/api/coaching/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: session.session_id }),
      })
      if (!res.ok) throw new Error('코칭 생성에 실패했어요')
      const data = await res.json()
      setCoachingList((prev) => {
        // 이미 있으면 교체, 없으면 앞에 추가
        const exists = prev.findIndex((c) => c.session.session_id === session.session_id)
        const newItem = { session, coaching: data }
        if (exists >= 0) {
          const updated = [...prev]
          updated[exists] = newItem
          return updated
        }
        return [newItem, ...prev]
      })
    } catch (e) {
      setError(e.message || '코칭 생성 중 오류가 발생했어요')
    } finally {
      setGeneratingId(null)
    }
  }

  // 코칭이 있는 세션 ID 집합
  const coachedIds = new Set(coachingList.map((c) => c.session.session_id))

  return (
    <div className="space-y-8 animate-stagger">
      {/* 헤더 */}
      <div>
        <h1 className="page-title">AI 코칭</h1>
        <p className="page-subtitle">Claude AI가 수면 데이터를 분석하고 개선 방향을 제시해요</p>
      </div>

      {/* 세션 선택 영역 */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <p className="section-label">코칭 생성</p>
          <span className="hidden sm:inline text-xs text-gray-400">수면 세션을 선택해 AI 코칭을 받아보세요</span>
        </div>

        {isLoadingSessions ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-14 bg-cream-100 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-sm text-gray-400">수면 세션이 없어요</p>
            <p className="text-xs text-gray-400 mt-1">수면 데이터가 쌓이면 코칭을 받을 수 있어요</p>
          </div>
        ) : (
          <div className="space-y-2">
            {sessions.slice(0, 7).map((s) => {
              const hasCouching = coachedIds.has(s.session_id)
              const isGenerating = generatingId === s.session_id
              const dur = s.duration_min || 0

              return (
                <div
                  key={s.session_id}
                  className="flex items-center justify-between p-3.5 rounded-xl bg-cream-50 border border-cream-200"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                      style={{ backgroundColor: hasCouching ? '#eff6ff' : '#f9fafb' }}
                    >
                      {hasCouching ? (
                        <svg className="w-4 h-4 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      ) : (
                        <svg className="w-4 h-4 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                        </svg>
                      )}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-800">
                        {new Date(s.start_time).toLocaleDateString('ko-KR', {
                          month: 'long', day: 'numeric', weekday: 'short',
                        })}
                      </p>
                      <p className="text-xs text-gray-400">
                        {Math.floor(dur / 60)}h {dur % 60}m · 종합 {s.total_score}점
                      </p>
                    </div>
                  </div>

                  <button
                    onClick={() => generateCoaching(s)}
                    disabled={isGenerating}
                    className={`text-xs font-medium px-3 py-1.5 rounded-lg transition-all duration-200 flex-shrink-0 ${
                      isGenerating
                        ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                        : hasCouching
                        ? 'bg-cream-100 text-indigo-700 hover:bg-indigo-50 border border-indigo-100'
                        : 'bg-indigo-900 text-white hover:bg-indigo-800'
                    }`}
                  >
                    {isGenerating ? (
                      <span className="flex items-center gap-1.5">
                        <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        생성 중…
                      </span>
                    ) : hasCouching ? '재생성' : 'AI 코칭 받기'}
                  </button>
                </div>
              )
            })}
          </div>
        )}

        {/* 에러 메시지 */}
        {error && (
          <div className="mt-3 p-3 bg-red-50 border border-red-100 rounded-xl">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}
      </div>

      {/* 코칭 카드 목록 */}
      {coachingList.length > 0 && (
        <div className="space-y-4">
          <p className="section-label">코칭 결과</p>
          {coachingList.map(({ session, coaching }) => (
            <CoachingCard
              key={session.session_id}
              coaching={coaching}
              sessionDate={session.start_time}
              totalScore={session.total_score}
            />
          ))}
        </div>
      )}

      {/* 코칭 없을 때 빈 상태 */}
      {!isLoadingSessions && coachingList.length === 0 && sessions.length > 0 && (
        <div className="card p-10 text-center">
          <div className="w-16 h-16 rounded-2xl bg-indigo-50 flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-indigo-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <p className="font-display text-lg text-indigo-900 mb-1">아직 코칭이 없어요</p>
          <p className="text-sm text-gray-400">위에서 수면 세션을 선택해 AI 코칭을 받아보세요</p>
        </div>
      )}
    </div>
  )
}
