"""
Tistory 블로그 발행 모듈

Tistory Open API를 통해 블로그 글을 발행하는 비동기 클라이언트입니다.
주간 GitHub 트렌딩 + Notion 데이터 요약을 자동으로 생성하고 Tistory에 발행합니다.

⚠️ Tistory API 주의사항 (매우 중요):
  1. thumbnail 파라미터 사용 절대 금지 — kage@ URL 전달 시 500 에러 발생
     반드시 thumbnailUrl만 사용하세요.
  2. content를 빈 문자열로 전송하면 해당 글이 전체 삭제됨 — 빈값 검증 필수
  3. daumLike 파라미터는 반드시 "401"으로 설정 (Tistory API 규칙)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class TistoryPublisher:
    """
    Tistory Open API 블로그 발행 클라이언트

    httpx.AsyncClient를 사용하여 Tistory 블로그에 글을 발행합니다.
    주간 요약 생성, 카테고리 조회, 글 발행 기능을 제공합니다.

    사용 예:
        publisher = TistoryPublisher("access_token", "my-blog")
        content = await publisher.generate_weekly_digest(repos, notion_data)
        result = await publisher.publish("제목", content, tags=["AI", "iOS"])
    """

    def __init__(self, access_token: str, blog_name: str):
        """
        TistoryPublisher 초기화

        Args:
            access_token: Tistory Open API 액세스 토큰
            blog_name: Tistory 블로그 이름 (예: "my-tistory-blog")
        """
        self.token = access_token
        self.blog_name = blog_name
        self.base_url = "https://www.tistory.com/apis"

    # ─── 주간 요약 생성 ─────────────────────────────────────────────────

    async def generate_weekly_digest(
        self,
        trending_repos: list[dict[str, Any]],
        notion_data: dict[str, Any],
    ) -> str:
        """
        주간 요약 마크다운을 생성합니다.

        GitHub 트렌딩 리포지토리와 Notion 데이터를 결합하여
        블로그 발행용 마크다운 형식의 주간 요약을 생성합니다.

        Args:
            trending_repos: 트렌딩 리포지토리 목록
                            (repo_name, description, language, stars, today_stars 등 포함)
            notion_data: Notion에서 조회한 데이터 딕셔너리
                         키별로 ai_models, ios_trends, performance 등 포함 가능

        Returns:
            마크다운 형식의 주간 요약 문자열
        """
        now = datetime.now(timezone.utc)
        # 한국 시간 기준으로 날짜 표시
        kst_offset = timezone(timedelta(hours=9)) if self._has_kst() else timezone.utc
        # timezone import를 위해 간단히 처리
        from datetime import timedelta as _td
        kst = timezone(_td(hours=9))
        now_kst = now.astimezone(kst)
        week_str = now_kst.strftime("%Y년 %m월 %d일")

        lines: list[str] = []

        # ── 헤더 ──
        lines.append(f"# 📋 이번 주 GitHub AI/iOS 트렌딩 + 기술 요약")
        lines.append(f"\n> 📅 {week_str} 기준 자동 생성\n")

        # ── 섹션 1: 인기 리포지토리 ──
        lines.append("---\n")
        lines.append("## 🔥 인기 리포지토리\n")
        if trending_repos:
            for i, repo in enumerate(trending_repos[:20], 1):
                name = repo.get("repo_name", "")
                desc = repo.get("description", "")
                lang = repo.get("language", "")
                stars = repo.get("stars", repo.get("stars_count", 0))
                today = repo.get("today_stars", 0)

                lines.append(f"### {i}. [{name}](https://github.com/{name})")
                if desc:
                    lines.append(f"- {desc}")
                meta_parts = []
                if lang:
                    meta_parts.append(f"언어: {lang}")
                if stars:
                    meta_parts.append(f"⭐ {stars:,}")
                if today:
                    meta_parts.append(f"📈 +{today:,} today")
                if meta_parts:
                    lines.append(f"- {', '.join(meta_parts)}")
                lines.append("")
        else:
            lines.append("_이번 주 수집된 트렌딩 리포지토리가 없습니다._\n")

        # ── 섹션 2: AI 모델 업데이트 ──
        lines.append("---\n")
        lines.append("## 📊 AI 모델 업데이트\n")
        ai_models = notion_data.get("ai_models", [])
        if ai_models:
            for i, model in enumerate(ai_models[:10], 1):
                props = model.get("properties", {})
                # properties에서 주요 필드 추출
                model_name = self._extract_text_value(props, "Name") or self._extract_text_value(props, "이름") or f"모델 {i}"
                lines.append(f"### {i}. {model_name}")
                # 추가 속성이 있으면 나열
                for key, val in props.items():
                    if key in ("Name", "이름", "id"):
                        continue
                    text_val = self._extract_text_value(props, key)
                    if text_val:
                        lines.append(f"- **{key}**: {text_val}")
                lines.append("")
        else:
            lines.append("_이번 주 업데이트된 AI 모델 정보가 없습니다._\n")

        # ── 섹션 3: iOS 트렌드 ──
        lines.append("---\n")
        lines.append("## 📱 iOS 트렌드\n")
        ios_trends = notion_data.get("ios_trends", [])
        if ios_trends:
            for i, trend in enumerate(ios_trends[:10], 1):
                props = trend.get("properties", {})
                trend_name = self._extract_text_value(props, "Name") or self._extract_text_value(props, "이름") or f"트렌드 {i}"
                lines.append(f"### {i}. {trend_name}")
                for key, val in props.items():
                    if key in ("Name", "이름", "id"):
                        continue
                    text_val = self._extract_text_value(props, key)
                    if text_val:
                        lines.append(f"- **{key}**: {text_val}")
                lines.append("")
        else:
            lines.append("_이번 주 iOS 트렌드 정보가 없습니다._\n")

        # ── 푸터 ──
        lines.append("---\n")
        lines.append("*이 요약은 ICBM2 Intelligence Hub에서 자동 생성되었습니다.*")

        content = "\n".join(lines)
        logger.info("주간 요약 생성 완료 (길이: %d자)", len(content))
        return content

    @staticmethod
    def _has_kst() -> bool:
        """timezone KST 사용 가능 여부 확인 (항상 True)"""
        return True

    @staticmethod
    def _extract_text_value(props: dict[str, Any], key: str) -> str:
        """
        Notion properties 딕셔너리에서 텍스트 값을 추출합니다.

        Args:
            props: Notion 정규화된 properties 딕셔너리
            key: 추출할 속성 키

        Returns:
            텍스트 값. 없으면 빈 문자열
        """
        val = props.get(key)
        if val is None:
            return ""
        if isinstance(val, str):
            return val
        if isinstance(val, (int, float)):
            return str(val)
        if isinstance(val, list):
            return ", ".join(str(v) for v in val if v)
        return str(val)

    # ─── 블로그 글 발행 ─────────────────────────────────────────────────

    async def publish(
        self,
        title: str,
        content: str,
        tags: list[str] | None = None,
        category_id: int = 0,
        thumbnail_url: str = "",
    ) -> dict[str, Any]:
        """
        Tistory 블로그에 글을 발행합니다.

        ⚠️ 중요: content가 빈 문자열이면 글이 전체 삭제됩니다.
        반드시 빈값 검증을 수행합니다.

        ⚠️ thumbnail 파라미터는 절대 사용하지 마세요 (500 에러).
        thumbnailUrl만 사용 가능합니다.

        ⚠️ daumLike는 반드시 "401"으로 설정해야 합니다.

        Args:
            title: 글 제목
            content: 글 내용 (마크다운 또는 HTML)
            tags: 태그 목록 (예: ["AI", "iOS", "GitHub"])
            category_id: 카테고리 ID (기본값: 0 — 미분류)
            thumbnail_url: 썸네일 이미지 URL (thumbnailUrl 파라미터로 전달)

        Returns:
            Tistory API 응답 딕셔너리
            성공 시: {"status": "200", "postId": "123", ...}
            실패 시: {"status": "400", "error": "..."} (예외 발생)

        Raises:
            ValueError: title이나 content가 빈 문자열인 경우
            httpx.HTTPStatusError: Tistory API 호출 실패
        """
        # ── 빈값 검증 (매우 중요!) ──
        # content를 빈 문자열로 보내면 글이 전체 삭제됨
        if not title or not title.strip():
            raise ValueError("제목(title)은 빈 문자열일 수 없습니다. 글이 삭제될 수 있습니다.")
        if not content or not content.strip():
            raise ValueError("내용(content)은 빈 문자열일 수 없습니다. 글이 전체 삭제됩니다.")

        # ── API 파라미터 구성 ──
        params: dict[str, Any] = {
            "access_token": self.token,
            "blogName": self.blog_name,
            "title": title.strip(),
            "content": content.strip(),
            # 공개 설정: 3 = 공개, 1 = 비공개, 0 = 보호
            "visibility": 3,
            "category": category_id,
            # ⚠️ daumLike는 반드시 "401"로 설정 (Tistory API 규칙)
            "daumLike": "401",
            "tag": ",".join(tags) if tags else "",
        }

        # thumbnailUrl만 사용 (thumbnail 파라미터 절대 금지 — kage@ URL → 500 에러)
        if thumbnail_url:
            params["thumbnailUrl"] = thumbnail_url

        logger.info("Tistory 글 발행 요청: title='%s' (길이: %d자)", title[:50], len(content))

        # ── API 호출 ──
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/post/write",
                data=params,
            )

        # 응답 처리
        try:
            result = response.json()
        except Exception:
            result = {"status": str(response.status_code), "raw": response.text}

        if response.status_code == 200 and result.get("status") == "200":
            post_id = result.get("postId", "")
            logger.info("Tistory 글 발행 성공: postId=%s", post_id)
        else:
            logger.error(
                "Tistory 글 발행 실패: status=%s, error=%s",
                result.get("status"),
                result.get("error_message", result),
            )

        return result

    # ─── 카테고리 조회 ──────────────────────────────────────────────────

    async def get_categories(self) -> list[dict[str, Any]]:
        """
        Tistory 블로그의 카테고리 목록을 조회합니다.

        Returns:
            카테고리 딕셔너리 목록
            예: [{"id": "123", "name": "AI", "label": "AI", "entries": 5}, ...]
        """
        params = {
            "access_token": self.token,
            "blogName": self.blog_name,
        }

        logger.info("Tistory 카테고리 조회 요청: blog=%s", self.blog_name)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/category/list",
                params=params,
            )

        if response.status_code != 200:
            logger.error("Tistory 카테고리 조회 실패: status=%d", response.status_code)
            return []

        try:
            data = response.json()
            categories = data.get("categories", {}).get("category", [])
            if isinstance(categories, dict):
                # 단일 카테고리인 경우 리스트로 변환
                categories = [categories]
            logger.info("Tistory 카테고리 %d개 조회 완료", len(categories))
            return categories
        except Exception as e:
            logger.error("Tistory 카테고리 응답 파싱 실패: %s", e)
            return []
