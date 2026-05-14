import { NavLink, Outlet } from 'react-router-dom'

// 네비게이션 아이템 정의
const NAV_ITEMS = [
  {
    to: '/dashboard',
    label: '대시보드',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
  },
  {
    to: '/report',
    label: '리포트',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
  {
    to: '/coaching',
    label: 'AI 코칭',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
  },
  {
    to: '/help',
    label: '도움말',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
]

export default function Layout() {
  return (
    <div className="flex min-h-screen bg-mesh">
      {/* 사이드바 */}
      <aside className="fixed left-0 top-0 h-full w-60 bg-white border-r border-cream-200 shadow-sm z-20 flex flex-col">
        {/* 로고 영역 */}
        <div className="px-6 py-6 border-b border-cream-200">
          <div className="flex items-center gap-3">
            {/* 달 아이콘 */}
            <div className="w-9 h-9 rounded-xl bg-indigo-900 flex items-center justify-center flex-shrink-0">
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none">
                <path
                  d="M17 9C13.134 9 10 12.134 10 16C10 19.866 13.134 23 17 23C18.105 23 19.148 22.726 20.062 22.244C18.474 23.372 16.52 24 14.4 24C9.203 24 5 19.797 5 14.6C5 9.403 9.203 5.2 14.4 5.2C16.026 5.2 17.554 5.62 18.878 6.356C17.706 7.068 17 8.452 17 9Z"
                  fill="white"
                  opacity="0.9"
                />
                <circle cx="20" cy="7" r="1.2" fill="#7eb8f7" />
                <circle cx="21.5" cy="10.5" r="0.8" fill="#7eb8f7" opacity="0.6" />
              </svg>
            </div>
            <div>
              <p className="font-display text-lg leading-tight text-indigo-900">Sleeping</p>
              <p className="font-display text-lg leading-tight text-indigo-900 -mt-1">Care</p>
            </div>
          </div>
        </div>

        {/* 네비게이션 */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto scrollbar-thin">
          <p className="section-label px-4 mb-3">메뉴</p>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `nav-link ${isActive ? 'active' : ''}`
              }
            >
              {item.icon}
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* 하단 버전 정보 */}
        <div className="px-6 py-4 border-t border-cream-200">
          <p className="text-xs text-gray-400 font-body">v0.0.1 · AIoT 텀 프로젝트</p>
          <p className="text-xs text-gray-400 mt-0.5">2201318 김단비</p>
        </div>
      </aside>

      {/* 메인 콘텐츠 영역 */}
      <main className="flex-1 ml-60 min-h-screen">
        {/* 배경 도트 패턴 (옅게) */}
        <div className="fixed inset-0 ml-60 bg-dots opacity-30 pointer-events-none z-0" />
        <div className="relative z-10 p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
