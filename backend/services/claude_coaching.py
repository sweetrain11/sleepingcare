"""
claude_coaching.py
Claude API를 사용해 수면 데이터 기반 코칭 텍스트 생성
응답 구조: 잘된 점 / 개선할 점 / 이번 주 목표
"""
import json
import anthropic
from core.config import settings


def _build_prompt(session: dict) -> str:
    """수면 세션 데이터 → Claude 프롬프트 변환"""
    dur_h = (session.get("duration_min") or 0) // 60
    dur_m = (session.get("duration_min") or 0) % 60

    lines = [
        "아래는 사용자의 어젯밤 수면 데이터예요.",
        "",
        f"- 수면 시간: {dur_h}시간 {dur_m}분",
        f"- 취침 시각 편차 (전날 대비): {session.get('regularity_diff_min', '알 수 없음')}분",
        f"- 뒤척임 횟수: {session.get('motion_count', 0)}회",
        f"- 평균 온도: {session.get('avg_temperature', '알 수 없음')}°C  (권장: 15~19°C)",
        f"- 평균 습도: {session.get('avg_humidity', '알 수 없음')}%  (권장: 40~60%)",
        f"- 평균 조도: {session.get('avg_light', '알 수 없음')} lux  (5 lux 이하 권장)",
        f"- 평균 소음: {session.get('avg_sound', '알 수 없음')} dB  (30 dB 이하 권장)",
        f"- 환경 점수: {session.get('env_score', '—')}점 / 40점",
        f"- 패턴 점수: {session.get('pattern_score', '—')}점 / 60점",
        f"- 종합 점수: {session.get('total_score', '—')}점 / 100점",
        "",
        "위 데이터를 바탕으로 수면 코칭을 아래 JSON 형식으로만 응답해줘.",
        "마크다운 코드블록 없이 순수 JSON만 출력할 것.",
        "",
        '{"good_points": "잘된 점 1~2가지 (2~3문장)", "bad_points": "개선할 점 1~2가지 (2~3문장)", "weekly_goal": "이번 주 실천 목표 1가지 (1~2문장)"}',
    ]
    return "\n".join(lines)


def _build_range_prompt(sessions: list[dict], range: str) -> str:
    """범위별 완전히 다른 분석 관점의 코칭 프롬프트"""

    def avg(key):
        vals = [s[key] for s in sessions if s.get(key) is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    def fmt_dur(minutes):
        if minutes is None:
            return "알 수 없음"
        return f"{int(minutes // 60)}시간 {int(minutes % 60)}분"

    n = len(sessions)
    scores = [s["total_score"] for s in sessions if s.get("total_score") is not None]

    json_format = '{"good_points": "...", "bad_points": "...", "weekly_goal": "..."}'
    suffix = [
        "",
        "위 데이터를 바탕으로 수면 코칭을 아래 JSON 형식으로만 응답해줘.",
        "마크다운 코드블록 없이 순수 JSON만 출력할 것.",
        "",
        json_format,
    ]

    # ── 1일: 어젯밤 단일 세션 심층 분석 ──────────────────────────────
    if range == "day":
        s = sessions[0]
        dur_h = (s.get("duration_min") or 0) // 60
        dur_m = (s.get("duration_min") or 0) % 60
        lines = [
            "아래는 사용자의 어젯밤 수면 데이터예요.",
            "단일 세션의 세부 수치를 분석해 오늘 밤 바로 실천 가능한 구체적 피드백을 줘.",
            "",
            f"- 수면 시간: {dur_h}시간 {dur_m}분  (권장: 7~9시간)",
            f"- 취침 시각 편차 (전날 대비): {s.get('regularity_diff_min', '알 수 없음')}분  (0분 최적)",
            f"- 뒤척임 횟수: {s.get('motion_count', 0)}회",
            f"- 온도: {s.get('avg_temperature', '알 수 없음')}°C  (권장: 15~19°C)",
            f"- 습도: {s.get('avg_humidity', '알 수 없음')}%  (권장: 40~60%)",
            f"- 조도: {s.get('avg_light', '알 수 없음')} lux  (5 lux 이하 권장)",
            f"- 소음: {s.get('avg_sound', '알 수 없음')} dB  (30 dB 이하 권장)",
            f"- 환경 점수: {s.get('env_score', '—')}점 / 40점",
            f"- 패턴 점수: {s.get('pattern_score', '—')}점 / 60점",
            f"- 종합 점수: {s.get('total_score', '—')}점 / 100점",
            "",
            "good_points: 어젯밤 실제로 잘된 항목을 수치와 함께 구체적으로 언급해줘 (예: '소음이 XX dB로 조용했어요').",
            "bad_points: 수치가 권장 범위를 벗어난 항목을 짚고, 그것이 수면에 미치는 영향을 설명해줘.",
            "weekly_goal: 오늘 밤부터 바로 실천할 수 있는 단 한 가지 행동을 구체적으로 알려줘.",
        ]
        return "\n".join(lines + suffix)

    # ── 7일: 추세·패턴 분석 ─────────────────────────────────────────
    if range == "week":
        # 일별 요약 (최신순 → 오래된 순으로 정렬해서 표시)
        session_lines = ["[일별 수면 기록 (최신순)]"]
        for i, s in enumerate(sessions):
            session_lines.append(
                f"  {i+1}일 전: 점수={s.get('total_score','—')}점, "
                f"수면={fmt_dur(s.get('duration_min'))}, "
                f"뒤척임={s.get('motion_count',0)}회, "
                f"취침편차={s.get('regularity_diff_min','?')}분, "
                f"온도={s.get('avg_temperature','?')}°C, 습도={s.get('avg_humidity','?')}%"
            )

        best = max(scores) if scores else None
        worst = min(scores) if scores else None
        trend = "개선" if len(scores) >= 2 and scores[0] > scores[-1] else \
                "악화" if len(scores) >= 2 and scores[0] < scores[-1] else "유지"

        lines = [
            "아래는 사용자의 최근 7일 수면 일별 기록이에요.",
            "단순 평균이 아닌 추세와 패턴을 분석해줘.",
            "",
            *session_lines,
            "",
            f"- 7일 점수 추세: {trend} (최고 {best}점 / 최저 {worst}점)",
            f"- 평균 수면 시간: {fmt_dur(avg('duration_min'))}  (권장: 7~9시간)",
            f"- 평균 취침 규칙성 편차: {avg('regularity_diff_min')}분",
            f"- 평균 뒤척임: {avg('motion_count')}회",
            f"- 평균 온도/습도: {avg('avg_temperature')}°C / {avg('avg_humidity')}%",
            "",
            "good_points: 이번 주 전반적으로 잘 유지된 점, 또는 점수가 오른 날이 있다면 그 원인을 분석해줘.",
            "bad_points: 점수가 낮았던 날의 공통 원인이나 반복되는 문제 패턴을 짚어줘. 평균보다 추세를 중심으로.",
            "weekly_goal: 다음 주 7일 동안 꾸준히 실천할 루틴 개선 목표를 1가지 알려줘. '오늘 밤'이 아닌 '이번 주' 단위로.",
        ]
        return "\n".join(lines + suffix)

    # ── 30일: 장기 습관·구조적 패턴 분석 ────────────────────────────
    # 주별 평균으로 집계
    week_buckets: list[list[dict]] = [[], [], [], []]
    for i, s in enumerate(sessions):
        bucket = min(i // 7, 3)
        week_buckets[bucket].append(s)

    def bucket_avg(bucket, key):
        vals = [s[key] for s in bucket if s.get(key) is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    week_summaries = []
    for w, bucket in enumerate(week_buckets):
        if not bucket:
            continue
        w_avg = bucket_avg(bucket, "total_score")
        w_dur = bucket_avg(bucket, "duration_min")
        week_summaries.append(
            f"  {w+1}주차 ({len(bucket)}세션): 평균 점수={w_avg}점, 평균 수면={fmt_dur(w_dur)}"
        )

    score_trend = "개선" if len(scores) >= 2 and scores[0] > scores[-1] else \
                  "악화" if len(scores) >= 2 and scores[0] < scores[-1] else "유지"

    lines = [
        "아래는 사용자의 최근 30일 수면 데이터예요.",
        "단기 변동이 아닌 장기 습관과 구조적 패턴을 분석해줘.",
        "",
        "[주별 요약]",
        *week_summaries,
        "",
        f"- 30일 점수 추세: {score_trend} (최고 {max(scores) if scores else '—'}점 / 최저 {min(scores) if scores else '—'}점)",
        f"- 30일 평균 수면 시간: {fmt_dur(avg('duration_min'))}",
        f"- 30일 평균 취침 규칙성 편차: {avg('regularity_diff_min')}분",
        f"- 30일 평균 뒤척임: {avg('motion_count')}회",
        f"- 30일 평균 온도/습도/소음: {avg('avg_temperature')}°C / {avg('avg_humidity')}% / {avg('avg_sound')} dB",
        f"- 총 {n}회 수면 기록",
        "",
        "good_points: 30일 동안 꾸준히 잘 지켜진 생활 습관이나 장기적으로 개선된 점을 분석해줘.",
        "bad_points: 한 달 내내 반복되는 구조적 문제(예: 만성적인 늦은 취침, 지속적인 환경 문제 등)를 짚어줘.",
        "weekly_goal: 이번 달 데이터를 바탕으로, 앞으로 한 달간 집중할 핵심 습관 변화 1가지를 제안해줘. 구체적인 수치 목표 포함.",
    ]
    return "\n".join(lines + suffix)


async def generate_range_coaching(sessions: list[dict], range: str) -> dict:
    """범위 기반 Claude 코칭 생성"""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    prompt = _build_range_prompt(sessions, range)

    message = await client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1000,
        system=(
            "당신은 수면 전문 코치예요. "
            "사용자의 수면 데이터를 분석해 친절하고 실용적인 피드백을 한국어로 제공해요. "
            "요청한 JSON 형식으로만 응답하고, 절대 다른 텍스트를 추가하지 마세요."
        ),
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("AI 응답을 처리하지 못했어요. 잠시 후 다시 시도해주세요.")

    return {
        "good_points": result.get("good_points", ""),
        "bad_points": result.get("bad_points", ""),
        "weekly_goal": result.get("weekly_goal", ""),
    }


async def generate_coaching(session: dict) -> dict:
    """
    Claude API 호출 → 코칭 텍스트 생성
    Returns: {"good_points": ..., "bad_points": ..., "weekly_goal": ...}
    """
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    prompt = _build_prompt(session)

    message = await client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1000,
        system=(
            "당신은 수면 전문 코치예요. "
            "사용자의 수면 데이터를 분석해 친절하고 실용적인 피드백을 한국어로 제공해요. "
            "요청한 JSON 형식으로만 응답하고, 절대 다른 텍스트를 추가하지 마세요."
        ),
        messages=[{"role": "user", "content": prompt}],
    )

    # 응답 파싱
    raw = message.content[0].text.strip()
    # 혹시 코드블록이 포함된 경우 제거
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("AI 응답을 처리하지 못했어요. 잠시 후 다시 시도해주세요.")

    # 필수 키 보장
    return {
        "good_points": result.get("good_points", ""),
        "bad_points": result.get("bad_points", ""),
        "weekly_goal": result.get("weekly_goal", ""),
    }
