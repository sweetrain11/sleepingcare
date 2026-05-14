import { useEffect, useRef } from 'react'

/**
 * ScoreGauge.jsx
 * SVG 기반 원형 게이지로 수면 점수 시각화
 * props: score(0~100), size, showLabel
 */

// 점수에 따른 색상 및 등급
function getScoreInfo(score) {
  if (score >= 85) return { color: '#22c55e', grade: '매우 좋음', emoji: '😴' }
  if (score >= 70) return { color: '#84cc16', grade: '좋음', emoji: '🙂' }
  if (score >= 55) return { color: '#f59e0b', grade: '보통', emoji: '😐' }
  return { color: '#ef4444', grade: '나쁨', emoji: '😟' }
}

export default function ScoreGauge({ score = 0, size = 200, showLabel = true }) {
  const circleRef = useRef(null)

  const radius = 54
  const circumference = 2 * Math.PI * radius  // ≈ 339.3
  const strokeWidth = 10
  const center = size / 2

  // 점수 → dashoffset 계산 (0점=전체, 100점=0)
  const dashOffset = circumference - (score / 100) * circumference
  const { color, grade, emoji } = getScoreInfo(score)

  useEffect(() => {
    const el = circleRef.current
    if (!el) return

    // 애니메이션: 0에서 목표 dashoffset까지
    el.style.setProperty('--dash-offset', dashOffset)
    el.style.strokeDashoffset = circumference  // 초기값 (빈 상태)

    // requestAnimationFrame으로 애니메이션 트리거
    const raf = requestAnimationFrame(() => {
      el.style.transition = 'stroke-dashoffset 1.2s cubic-bezier(0.34, 1.56, 0.64, 1)'
      el.style.strokeDashoffset = dashOffset
    })

    return () => cancelAnimationFrame(raf)
  }, [score, dashOffset, circumference])

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="drop-shadow-sm"
        >
          {/* 배경 트랙 */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="#e8e7e3"
            strokeWidth={strokeWidth}
          />

          {/* 점수 게이지 (상단 12시 방향 시작) */}
          <circle
            ref={circleRef}
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={circumference}
            transform={`rotate(-90 ${center} ${center})`}
            style={{ filter: `drop-shadow(0 0 6px ${color}60)` }}
          />

          {/* 중앙 텍스트 */}
          <text
            x={center}
            y={center - 10}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize="36"
            fontFamily="'DM Serif Display', Georgia, serif"
            fill={color}
            fontWeight="400"
          >
            {score}
          </text>
          <text
            x={center}
            y={center + 18}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize="11"
            fontFamily="'DM Sans', sans-serif"
            fill="#6b7280"
            letterSpacing="2"
          >
            / 100
          </text>

          {/* 이모지 */}
          <text
            x={center}
            y={center + 38}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize="18"
          >
            {emoji}
          </text>
        </svg>
      </div>

      {/* 등급 라벨 */}
      {showLabel && (
        <div className="text-center">
          <span
            className="inline-block px-4 py-1.5 rounded-full text-sm font-medium"
            style={{ backgroundColor: `${color}18`, color }}
          >
            {grade}
          </span>
        </div>
      )}
    </div>
  )
}
