/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 메인 인디고 계열
        indigo: {
          950: '#0f1f3d',
          900: '#1e3a5f',
          800: '#1e4d8c',
          700: '#2563c4',
          600: '#3b82f6',
        },
        // 배경 크림/슬레이트 계열
        cream: {
          50: '#fafaf7',
          100: '#f5f4ef',
          200: '#edecea',
        },
        // 액센트 - 소프트 스카이
        sky: {
          accent: '#7eb8f7',
        },
        // 수면 점수 컬러
        score: {
          excellent: '#22c55e',
          good: '#84cc16',
          fair: '#f59e0b',
          poor: '#ef4444',
        }
      },
      fontFamily: {
        display: ['"DM Serif Display"', 'Georgia', 'serif'],
        body: ['"DM Sans"', 'sans-serif'],
      },
      boxShadow: {
        card: '0 2px 12px 0 rgba(30,58,95,0.08), 0 1px 3px 0 rgba(30,58,95,0.06)',
        'card-hover': '0 8px 30px 0 rgba(30,58,95,0.14), 0 2px 8px 0 rgba(30,58,95,0.08)',
        gauge: '0 4px 24px 0 rgba(30,58,95,0.15)',
      },
      backgroundImage: {
        'dot-pattern': 'radial-gradient(circle, #c7d7ee 1px, transparent 1px)',
        'gradient-mesh': 'linear-gradient(135deg, #f5f4ef 0%, #eef4fd 50%, #f5f4ef 100%)',
      },
      backgroundSize: {
        'dot-sm': '20px 20px',
      },
      animation: {
        'fade-up': 'fadeUp 0.5s ease forwards',
        'score-fill': 'scoreFill 1.2s cubic-bezier(0.34, 1.56, 0.64, 1) forwards',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
      },
      keyframes: {
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scoreFill: {
          '0%': { strokeDashoffset: '339.3' },
          '100%': { strokeDashoffset: 'var(--dash-offset)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
      },
    },
  },
  plugins: [],
}
