/**
 * CoachingCard.jsx
 * Claude AI 코칭 결과를 표시하는 카드 컴포넌트
 * props: coaching (객체), sessionDate, totalScore
 */

function ScoreBadge({ score }) {
  const color = score >= 85 ? '#22c55e' : score >= 70 ? '#84cc16' : score >= 55 ? '#f59e0b' : '#ef4444'
  const label = score >= 85 ? '매우 좋음' : score >= 70 ? '좋음' : score >= 55 ? '보통' : '나쁨'
  return (
    <span
      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium"
      style={{ backgroundColor: `${color}18`, color }}
    >
      <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ backgroundColor: color }} />
      {score}점 · {label}
    </span>
  )
}

// 섹션 블록 (잘된 점 / 개선할 점 / 목표)
function CoachingSection({ icon, title, content, accentColor, bgColor }) {
  return (
    <div
      className="rounded-xl p-4 border"
      style={{ backgroundColor: bgColor, borderColor: `${accentColor}30` }}
    >
      <div className="flex items-center gap-2 mb-2">
        <span className="text-base">{icon}</span>
        <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: accentColor }}>
          {title}
        </p>
      </div>
      <p className="text-sm text-gray-700 leading-relaxed">{content}</p>
    </div>
  )
}

export default function CoachingCard({ coaching, sessionDate, totalScore, rangeLabel, range }) {
  const goalLabel = range === 'day' ? '오늘 밤 목표' : range === 'month' ? '이번 달 목표' : '이번 주 목표'
  const formattedDate = sessionDate
    ? new Date(sessionDate).toLocaleDateString('ko-KR', {
        month: 'long', day: 'numeric', weekday: 'short',
      })
    : '날짜 없음'

  return (
    <div className="card p-6 space-y-5">
      {/* 헤더 */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <svg className="w-4 h-4 text-indigo-800 opacity-60" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <p className="text-xs text-gray-400">{rangeLabel ?? formattedDate}</p>
          </div>
          <h3 className="font-display text-xl text-indigo-900">AI 수면 코칭</h3>
        </div>
        {totalScore !== undefined && <ScoreBadge score={totalScore} />}
      </div>

      {/* 구분선 */}
      <div className="h-px bg-cream-200" />

      {/* 코칭 섹션 3개 */}
      <div className="space-y-3">
        <CoachingSection
          icon="✅"
          title="잘된 점"
          content={coaching?.good_points || '데이터를 불러오는 중...'}
          accentColor="#22c55e"
          bgColor="#f0fdf4"
        />
        <CoachingSection
          icon="💡"
          title="개선할 점"
          content={coaching?.bad_points || '데이터를 불러오는 중...'}
          accentColor="#f59e0b"
          bgColor="#fffbeb"
        />
        <CoachingSection
          icon="🎯"
          title={goalLabel}
          content={coaching?.weekly_goal || '데이터를 불러오는 중...'}
          accentColor="#2563c4"
          bgColor="#eff6ff"
        />
      </div>

      {/* 푸터 - 생성 시각 */}
      {coaching?.created_at && (
        <p className="text-xs text-gray-400 text-right">
          Claude AI 생성 · {new Date(coaching.created_at).toLocaleString('ko-KR', {
            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
          })}
        </p>
      )}
    </div>
  )
}
