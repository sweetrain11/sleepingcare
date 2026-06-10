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
    """여러 수면 세션 집계 데이터 → 범위 코칭 프롬프트"""
    range_label = {"day": "어젯밤", "week": "최근 7일", "month": "최근 30일"}.get(range, range)
    n = len(sessions)

    def avg(key):
        vals = [s[key] for s in sessions if s.get(key) is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    avg_duration   = avg("duration_min")
    avg_temp       = avg("avg_temperature")
    avg_humidity   = avg("avg_humidity")
    avg_light      = avg("avg_light")
    avg_sound      = avg("avg_sound")
    avg_motion     = avg("motion_count")
    avg_score      = avg("total_score")
    avg_regularity = avg("regularity_diff_min")

    dur_h = int(avg_duration // 60) if avg_duration else 0
    dur_m = int(avg_duration % 60) if avg_duration else 0

    lines = [
        f"아래는 사용자의 {range_label} 수면 데이터 요약이에요. (총 {n}개 세션 평균)",
        "",
        f"- 평균 수면 시간: {dur_h}시간 {dur_m}분  (권장 7~9시간)",
        f"- 평균 취침 규칙성 편차: {avg_regularity if avg_regularity is not None else '알 수 없음'}분  (0분 최적)",
        f"- 평균 뒤척임 횟수: {avg_motion if avg_motion is not None else 0}회",
        f"- 평균 온도: {avg_temp}°C  (권장 16~20°C)",
        f"- 평균 습도: {avg_humidity}%  (권장 40~60%)",
        f"- 평균 조도: {avg_light} lux  (5 lux 이하 권장)",
        f"- 평균 소음: {avg_sound} dB  (30 dB 이하 권장)",
        f"- 평균 종합 점수: {avg_score}점 / 100점",
        "",
        "위 데이터를 바탕으로 수면 코칭을 아래 JSON 형식으로만 응답해줘.",
        "마크다운 코드블록 없이 순수 JSON만 출력할 것.",
        "",
        '{"good_points": "잘된 점 1~2가지 (2~3문장)", "bad_points": "개선할 점 1~2가지 (2~3문장)", "weekly_goal": "앞으로의 실천 목표 1가지 (1~2문장)"}',
    ]
    return "\n".join(lines)


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
