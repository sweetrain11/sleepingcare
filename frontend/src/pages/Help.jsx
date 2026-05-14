/**
 * Help.jsx
 * 도움말 페이지
 * - 전체 시스템 아키텍처
 * - 사용된 라이브러리 설명
 * - 수면 점수 로직 설명
 * - 버전 v0.0.1
 */

// 아키텍처 플로우 단계
const ARCH_STEPS = [
  {
    step: '01',
    title: 'Arduino Uno',
    subtitle: '센서 수집',
    desc: 'DHT11(온습도), CDS(조도), PIR(모션), 사운드 센서, RTC 모듈에서 데이터를 수집하고 JSON 형태로 HC-06 블루투스 모듈을 통해 전송',
    color: '#f97316',
    icon: '🔌',
  },
  {
    step: '02',
    title: 'Raspberry Pi',
    subtitle: '엣지 전처리',
    desc: '블루투스 수신 후 이동평균(N=5) 노이즈 필터링 적용. 조도 기반 수면 시작/종료 이벤트 감지 후 Mosquitto MQTT 브로커로 publish',
    color: '#8b5cf6',
    icon: '🍓',
  },
  {
    step: '03',
    title: 'FastAPI Backend',
    subtitle: '분석 · 점수 · DB',
    desc: 'MQTT 구독으로 센서 데이터 수신, TimescaleDB에 시계열 저장. 수면 세션 감지 시 환경(40점) + 패턴(60점) 기준으로 100점 만점 점수 산출',
    color: '#1e3a5f',
    icon: '⚡',
  },
  {
    step: '04',
    title: 'Claude API',
    subtitle: 'AI 코칭 생성',
    desc: '수면 데이터를 프롬프트로 변환해 Anthropic Claude API 호출. 잘된 점 / 개선할 점 / 이번 주 목표 3가지 항목으로 구성된 코칭 텍스트 생성 후 DB 저장',
    color: '#ec4899',
    icon: '🤖',
  },
  {
    step: '05',
    title: 'React Dashboard',
    subtitle: '사용자 확인',
    desc: 'WebSocket으로 실시간 센서 데이터 수신. REST API로 수면 점수·이력·코칭 조회. Recharts로 점수 추이 시각화. PWA 적용으로 모바일 접근 가능',
    color: '#06b6d4',
    icon: '📱',
  },
]

// 라이브러리 목록
const LIBRARIES = [
  {
    category: '프론트엔드',
    color: '#06b6d4',
    items: [
      { name: 'React 18', desc: 'UI 컴포넌트 기반 프레임워크. Hooks API로 상태 및 사이드이펙트 관리' },
      { name: 'Vite 5', desc: '빠른 개발 서버 및 빌드 도구. ESM 기반 HMR으로 즉각적인 반영' },
      { name: 'TailwindCSS 3', desc: '유틸리티 퍼스트 CSS 프레임워크. 커스텀 디자인 토큰으로 일관된 스타일 적용' },
      { name: 'React Router 6', desc: '클라이언트 사이드 라우팅. Outlet 기반 중첩 레이아웃 구조' },
      { name: 'Recharts 2', desc: 'React 기반 차트 라이브러리. AreaChart로 수면 점수 추이 시각화' },
    ],
  },
  {
    category: '백엔드',
    color: '#1e3a5f',
    items: [
      { name: 'FastAPI', desc: 'Python 비동기 웹 프레임워크. 자동 OpenAPI 문서화 및 Pydantic 스키마 검증' },
      { name: 'asyncpg', desc: 'PostgreSQL/TimescaleDB 비동기 클라이언트. 고성능 DB I/O 처리' },
      { name: 'pydantic-settings', desc: '.env 파일 기반 설정 관리. 타입 안전한 환경변수 로드' },
      { name: 'paho-mqtt', desc: 'MQTT 클라이언트 라이브러리. 라즈베리파이 → 서버 센서 데이터 구독' },
    ],
  },
  {
    category: '인프라 · AI',
    color: '#ec4899',
    items: [
      { name: 'TimescaleDB', desc: 'PostgreSQL 기반 시계열 DB. 센서 데이터 하이퍼테이블로 고속 시계열 쿼리' },
      { name: 'Mosquitto', desc: '경량 MQTT 브로커. 라즈베리파이와 서버 간 IoT 메시지 중계' },
      { name: 'Anthropic Claude API', desc: '수면 분석 결과를 자연어 코칭으로 변환. claude-sonnet 모델 사용' },
      { name: 'Docker', desc: 'TimescaleDB 컨테이너 운영. 로컬 개발 환경 DB 격리' },
    ],
  },
]

// 점수 기준 데이터
const SCORE_CRITERIA = [
  {
    category: '환경 점수 (40점)',
    color: '#06b6d4',
    items: [
      { name: '온도 (10점)', rule: '18~22°C 만점, 1°C 벗어날 때마다 2점 감점' },
      { name: '습도 (10점)', rule: '40~60% 만점, 5% 벗어날 때마다 2점 감점' },
      { name: '조도 (10점)', rule: '100 이하 만점, 초과 시 선형 감점' },
      { name: '소음 (10점)', rule: '300 이하 만점, 초과 시 선형 감점' },
    ],
  },
  {
    category: '패턴 점수 (60점)',
    color: '#1e3a5f',
    items: [
      { name: '수면 시간 (20점)', rule: '7~9시간 만점, 1시간 벗어날 때마다 5점 감점' },
      { name: '규칙성 (20점)', rule: '전날 대비 취침 편차 0분 만점, 30분마다 5점 감점' },
      { name: '뒤척임 (20점)', rule: '0회 만점, 5회마다 5점 감점' },
    ],
  },
]

// API 엔드포인트
const ENDPOINTS = [
  { method: 'GET',  path: '/health',                        desc: '서버 상태 확인' },
  { method: 'POST', path: '/api/sensors/data',              desc: '라즈베리파이 센서 데이터 수신' },
  { method: 'POST', path: '/api/sensors/mock',              desc: '수동 테스트 데이터 생성' },
  { method: 'GET',  path: '/api/sleep/score/{session_id}',  desc: '수면 세션 점수 조회' },
  { method: 'GET',  path: '/api/sleep/history?range=week|month', desc: '수면 이력 조회' },
  { method: 'POST', path: '/api/coaching/generate',         desc: 'AI 코칭 생성' },
  { method: 'WS',   path: '/ws/realtime',                   desc: '실시간 센서 데이터 스트림' },
]

const METHOD_COLORS = {
  GET:  { bg: '#eff6ff', text: '#1d4ed8' },
  POST: { bg: '#f0fdf4', text: '#15803d' },
  WS:   { bg: '#fdf4ff', text: '#7e22ce' },
}

export default function Help() {
  return (
    <div className="space-y-10 animate-stagger max-w-4xl">
      {/* 헤더 */}
      <div>
        <h1 className="page-title">도움말</h1>
        <p className="page-subtitle">Sleeping Care 시스템 구조와 사용 기술을 설명해요</p>
      </div>

      {/* 시스템 아키텍처 */}
      <section className="card p-6">
        <p className="section-label mb-6">시스템 아키텍처</p>
        <div className="space-y-4">
          {ARCH_STEPS.map((step, i) => (
            <div key={step.step} className="flex gap-4">
              {/* 스텝 번호 + 연결선 */}
              <div className="flex flex-col items-center flex-shrink-0">
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center text-white text-sm font-bold flex-shrink-0"
                  style={{ backgroundColor: step.color }}
                >
                  {step.step}
                </div>
                {i < ARCH_STEPS.length - 1 && (
                  <div className="w-0.5 h-full mt-1 bg-cream-200 flex-1 min-h-4" />
                )}
              </div>
              {/* 내용 */}
              <div className="pb-4 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span>{step.icon}</span>
                  <p className="font-semibold text-gray-800">{step.title}</p>
                  <span
                    className="text-xs px-2 py-0.5 rounded-full font-medium"
                    style={{ backgroundColor: `${step.color}18`, color: step.color }}
                  >
                    {step.subtitle}
                  </span>
                </div>
                <p className="text-sm text-gray-600 leading-relaxed">{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 수면 점수 로직 */}
      <section className="card p-6">
        <p className="section-label mb-6">수면 점수 산출 기준</p>
        <div className="grid md:grid-cols-2 gap-6">
          {SCORE_CRITERIA.map((cat) => (
            <div key={cat.category}>
              <div
                className="text-sm font-semibold mb-3 px-3 py-1.5 rounded-lg inline-block"
                style={{ backgroundColor: `${cat.color}18`, color: cat.color }}
              >
                {cat.category}
              </div>
              <div className="space-y-2">
                {cat.items.map((item) => (
                  <div key={item.name} className="bg-cream-50 rounded-xl p-3 border border-cream-200">
                    <p className="text-sm font-medium text-gray-800 mb-0.5">{item.name}</p>
                    <p className="text-xs text-gray-500">{item.rule}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* API 엔드포인트 */}
      <section className="card p-6">
        <p className="section-label mb-4">API 엔드포인트</p>
        <div className="space-y-2">
          {ENDPOINTS.map((ep) => {
            const mc = METHOD_COLORS[ep.method] || METHOD_COLORS.GET
            return (
              <div key={ep.path} className="flex items-center gap-3 p-3 bg-cream-50 rounded-xl border border-cream-200">
                <span
                  className="text-xs font-bold px-2 py-0.5 rounded-md font-mono flex-shrink-0 w-12 text-center"
                  style={{ backgroundColor: mc.bg, color: mc.text }}
                >
                  {ep.method}
                </span>
                <code className="text-xs text-indigo-800 font-mono flex-1">{ep.path}</code>
                <p className="text-xs text-gray-400 hidden sm:block">{ep.desc}</p>
              </div>
            )
          })}
        </div>
      </section>

      {/* 라이브러리 */}
      <section className="card p-6">
        <p className="section-label mb-6">사용된 라이브러리</p>
        <div className="space-y-6">
          {LIBRARIES.map((lib) => (
            <div key={lib.category}>
              <p
                className="text-sm font-semibold mb-3"
                style={{ color: lib.color }}
              >
                {lib.category}
              </p>
              <div className="grid sm:grid-cols-2 gap-2">
                {lib.items.map((item) => (
                  <div key={item.name} className="bg-cream-50 rounded-xl p-3 border border-cream-200">
                    <p className="text-sm font-semibold text-gray-800 mb-0.5">{item.name}</p>
                    <p className="text-xs text-gray-500 leading-relaxed">{item.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 버전 정보 */}
      <section className="card p-6">
        <p className="section-label mb-4">버전 정보</p>
        <div className="flex items-center justify-between">
          <div>
            <p className="font-display text-2xl text-indigo-900">v0.0.1</p>
            <p className="text-sm text-gray-500 mt-1">AIoT응용및실습 텀 프로젝트</p>
            <p className="text-xs text-gray-400 mt-0.5">국립군산대학교 소프트웨어학과 · 2201318 김단비</p>
          </div>
          <div className="text-right">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-indigo-50 rounded-xl border border-indigo-100">
              <span className="w-2 h-2 rounded-full bg-green-400" />
              <span className="text-xs text-indigo-700 font-medium">Stable</span>
            </div>
            <p className="text-xs text-gray-400 mt-2">2026년 1학기</p>
          </div>
        </div>

        {/* 변경 이력 */}
        <div className="mt-5 pt-5 border-t border-cream-200">
          <p className="text-xs font-semibold text-gray-500 mb-3">변경 이력</p>
          <div className="space-y-2">
            <div className="flex items-start gap-3">
              <span className="text-xs font-mono text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded flex-shrink-0">v0.0.1</span>
              <div>
                <p className="text-xs font-medium text-gray-700">최초 릴리즈</p>
                <p className="text-xs text-gray-400">대시보드 · 리포트 · AI 코칭 · 도움말 페이지 구현. WebSocket 실시간 센서 · PWA 적용</p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
