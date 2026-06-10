import { useState, useEffect } from 'react'
import CoachingCard from '../components/CoachingCard'

const TABS = [
  { value: 'day',   label: '1일',  desc: '어젯밤 수면 기반' },
  { value: 'week',  label: '7일',  desc: '최근 7일 평균 기반' },
  { value: 'month', label: '30일', desc: '최근 30일 평균 기반' },
]

export default function Coaching() {
  const [range, setRange] = useState('week')
  const [coaching, setCoaching] = useState(null)   // 현재 범위의 저장된 코칭
  const [isLoading, setIsLoading] = useState(true)
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState(null)

  // 범위 변경 시 저장된 코칭 조회
  useEffect(() => {
    async function fetchCoaching() {
      setIsLoading(true)
      setError(null)
      try {
        const res = await fetch(`/api/coaching/range?range=${range}`)
        if (res.ok) {
          const data = await res.json()
          setCoaching(data)
        } else {
          setCoaching(null)
        }
      } catch {
        setCoaching(null)
      } finally {
        setIsLoading(false)
      }
    }
    fetchCoaching()
  }, [range])

  async function handleGenerate() {
    setIsGenerating(true)
    setError(null)
    try {
      const res = await fetch('/api/coaching/range/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ range }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || '코칭 생성에 실패했어요')
      }
      const data = await res.json()
      setCoaching(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setIsGenerating(false)
    }
  }

  const currentTab = TABS.find((t) => t.value === range)

  return (
    <div className="space-y-8 animate-stagger">
      {/* 헤더 */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div>
          <h1 className="page-title">AI 코칭</h1>
          <p className="page-subtitle">Claude AI가 수면 데이터를 분석하고 개선 방향을 제시해요</p>
        </div>
        {/* 기간 탭 */}
        <div className="flex gap-1 bg-cream-100 rounded-xl p-1 border border-cream-200 self-start">
          {TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setRange(tab.value)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                range === tab.value
                  ? 'bg-indigo-900 text-white shadow-sm'
                  : 'text-gray-500 hover:text-indigo-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* 코칭 영역 */}
      {isLoading ? (
        <div className="card p-12 flex items-center justify-center">
          <div className="w-8 h-8 rounded-full border-4 border-indigo-200 border-t-indigo-500 animate-spin" />
        </div>
      ) : coaching ? (
        /* 저장된 코칭 결과 */
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="section-label">코칭 결과</p>
              <p className="text-xs text-gray-400 mt-0.5">{currentTab.desc}</p>
            </div>
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className={`text-xs font-medium px-3 py-1.5 rounded-lg transition-all duration-200 flex-shrink-0 ${
                isGenerating
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-cream-100 text-indigo-700 hover:bg-indigo-50 border border-indigo-100'
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
              ) : '재생성'}
            </button>
          </div>

          <CoachingCard
            coaching={coaching}
            sessionDate={coaching.created_at}
            rangeLabel={currentTab.desc}
          />
        </div>
      ) : (
        /* 코칭 없음 — 생성 유도 */
        <div className="card p-10 text-center">
          <div className="w-16 h-16 rounded-2xl bg-indigo-50 flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-indigo-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <p className="font-display text-lg text-indigo-900 mb-1">
            {currentTab.desc} 코칭이 없어요
          </p>
          <p className="text-sm text-gray-400 mb-6">
            {range === 'day' ? '어젯밤' : `최근 ${range === 'week' ? '7일' : '30일'}`} 수면 데이터를 분석해 코칭을 생성해요
          </p>
          <button
            onClick={handleGenerate}
            disabled={isGenerating}
            className={`inline-flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
              isGenerating
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-indigo-900 text-white hover:bg-indigo-800 shadow-sm hover:shadow-md active:scale-95'
            }`}
          >
            {isGenerating ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                생성 중…
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                AI 코칭 받기
              </>
            )}
          </button>
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-50 border border-red-100 rounded-xl">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}
    </div>
  )
}
