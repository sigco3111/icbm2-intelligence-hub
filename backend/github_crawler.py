"""
GitHub Trending 크롤러 모듈

GitHub Trending 페이지를 크롤링하여 인기 리포지토리 정보를 수집하고,
GitHub API를 통해 상세 정보를 조회하는 기능을 제공합니다.
"""

import os
import re
import logging
from typing import Optional

import httpx
from bs4 import BeautifulSoup

# 로깅 설정
logger = logging.getLogger(__name__)

# 기본 필터링 키워드
DEFAULT_KEYWORDS = [
    "ai", "llm", "agent", "gpt", "claude", "gemini",
    "machine-learning", "deep-learning", "ios", "swift",
]


class GitHubTrendingCrawler:
    """GitHub Trending 페이지 크롤러 및 GitHub API 클라이언트

    httpx.AsyncClient를 기반으로 GitHub Trending 페이지를 크롤링하고,
    필요시 GitHub REST API를 통해 리포지토리 상세 정보를 조회합니다.
    """

    def __init__(
        self,
        github_token: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """크롤러 초기화

        Args:
            github_token: GitHub API 인증 토큰 (기본값: GITHUB_TOKEN 환경변수)
            timeout: HTTP 요청 타임아웃 (초)
        """
        self.github_token = (github_token or os.getenv("GITHUB_TOKEN", "")).strip()
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """httpx 비동기 클라이언트를 반환 (lazy 초기화)

        Returns:
            httpx.AsyncClient: 설정된 비동기 HTTP 클라이언트
        """
        if self._client is None or self._client.is_closed:
            headers = {
                "User-Agent": "ICBM2-Intelligence-Hub/1.0",
            }
            if self.github_token:
                headers["Authorization"] = f"Bearer {self.github_token}"

            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """HTTP 클라이언트 연결을 종료합니다."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ─── 트렌딩 페이지 크롤링 ───────────────────────────────────────────

    async def fetch_trending(
        self,
        language: str = "",
        since: str = "daily",
    ) -> list[dict]:
        """GitHub Trending 페이지를 크롤링하여 인기 리포지토리 목록을 반환합니다.

        Args:
            language: 프로그래밍 언어 필터 (예: "python", "typescript", "" 전체)
            since: 수집 기간 ("daily", "weekly", "monthly")

        Returns:
            list[dict]: 트렌딩 리포지토리 정보 딕셔너리 목록
        """
        # URL 구성
        url = "https://github.com/trending"
        if language:
            url += f"/{language}"
        url += f"?since={since}"

        logger.info("트렌딩 페이지 요청: %s", url)

        client = await self._get_client()
        response = await client.get(url)

        if response.status_code != 200:
            logger.error(
                "트렌딩 페이지 요청 실패: status=%d, url=%s",
                response.status_code,
                url,
            )
            return []

        # HTML 파싱
        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.select("article.Box-row")

        repos: list[dict] = []
        for article in articles:
            repo = self._parse_trending_article(article, since)
            if repo:
                repos.append(repo)

        logger.info("트렌딩 리포지토리 %d개 수집 완료 (language=%s, since=%s)", len(repos), language, since)
        return repos

    def _parse_trending_article(self, article: "BeautifulSoup", since: str) -> Optional[dict]:
        """개별 article 요소에서 리포지토리 정보를 파싱합니다.

        Args:
            article: BeautifulSoup article 요소
            since: 수집 기간 (today_stars 라벨 생성에 사용)

        Returns:
            Optional[dict]: 파싱된 리포지토리 정보 또는 None
        """
        try:
            # ── 리포지토리 이름 (owner/repo) ──
            name_tag = article.select_one("h2 a")
            if not name_tag:
                return None

            href = name_tag.get("href", "")
            # href는 "/owner/repo" 형식이므로 앞의 '/' 제거
            repo_name = href.strip("/")

            # ── 설명 ──
            desc_tag = article.select_one("p.color-fg-muted")
            description = desc_tag.get_text(strip=True) if desc_tag else ""

            # ── 프로그래밍 언어 ──
            lang_tag = article.select_one("[itemprop='programmingLanguage']")
            language = lang_tag.get_text(strip=True) if lang_tag else ""

            # ── 스타 수 ──
            stars_count = self._get_stars_count(article)

            # ── 포크 수 ──
            forks_count = self._get_forks_count(article)

            # ── 기간별 스타 수 (예: "★ 123 today") ──
            today_stars = self._parse_period_stars(article)

            return {
                "repo_name": repo_name,
                "description": description,
                "language": language,
                "stars_count": stars_count,
                "forks_count": forks_count,
                "today_stars": today_stars,
                "trending_since": since,
            }

        except Exception as e:
            logger.warning("트렌딩 아티클 파싱 실패: %s", e)
            return None

    @staticmethod
    def _parse_link_number(article: "BeautifulSoup", css_selector: str) -> int:
        """CSS 셀렉터로 링크를 찾아 숫자를 파싱합니다.

        GitHub trending 페이지의 스타/포크 링크에서 숫자를 추출합니다.
        숫자에 콤마가 포함될 수 있습니다 (예: "1,234").

        Args:
            article: BeautifulSoup article 요소
            css_selector: 대상 링크를 찾기 위한 CSS 셀렉터

        Returns:
            int: 파싱된 숫자 (실패 시 0)
        """
        link = article.select_one(css_selector)
        if link:
            text = link.get_text(strip=True).replace(",", "")
            match = re.search(r"\d+", text)
            if match:
                return int(match.group())
        return 0

    def _get_stars_count(self, article: "BeautifulSoup") -> int:
        """스타 수를 추출합니다. 여러 선택자를 순차적으로 시도합니다."""
        for selector in [
            'a[href*="/stargazers"]',
            'a.Link--muted[href*="stargazers"]',
        ]:
            link = article.select_one(selector)
            if link:
                text = link.get_text(strip=True).replace(",", "")
                match = re.search(r"\d+", text)
                if match:
                    return int(match.group())
        return 0

    def _get_forks_count(self, article: "BeautifulSoup") -> int:
        """포크 수를 추출합니다. 여러 선택자를 순차적으로 시도합니다."""
        for selector in [
            'a[href*="/forks"]',
            'a.Link--muted[href*="forks"]',
        ]:
            link = article.select_one(selector)
            if link:
                text = link.get_text(strip=True).replace(",", "")
                match = re.search(r"\d+", text)
                if match:
                    return int(match.group())
        return 0
    @staticmethod
    def _parse_period_stars(article: "BeautifulSoup") -> int:
        """기간별 스타 수를 파싱합니다 (예: "★ 123 today", "★ 1,234 this week").

        Args:
            article: BeautifulSoup article 요소

        Returns:
            int: 기간별 스타 수 (실패 시 0)
        """
        # 날짜 범위 스타는 보통 링크에 포함되지 않은 별도 스팬에 표시됨
        # "1,234 stars today" / "★ 123 today" 등의 형태
        all_text = article.get_text()
        # "N stars today/week/month" 또는 "★ N today/week/month" 패턴 매칭
        match = re.search(
            r"[\u2605]?\s*([\d,]+)\s+stars?\s+(?:today|this\s+week|this\s+month)",
            all_text,
        )
        if match:
            return int(match.group(1).replace(",", ""))

        # 대안 패턴: 스판 클래스 기반
        star_spans = article.select("span.d-inline-block.float-sm-right")
        for span in star_spans:
            text = span.get_text(strip=True)
            num_match = re.search(r"([\d,]+)", text)
            if num_match:
                return int(num_match.group(1).replace(",", ""))

        return 0

    # ─── GitHub API 상세 조회 ────────────────────────────────────────────

    async def fetch_repos_info(
        self,
        repo_full_names: list[str],
    ) -> list[dict]:
        """GitHub API를 통해 리포지토리 상세 정보를 일괄 조회합니다.

        각 리포지토리에 대해 topics, created_at, license 등의
        추가 정보를 GitHub REST API로 조회합니다.

        Args:
            repo_full_names: "owner/repo" 형식의 리포지토리 전체 이름 목록

        Returns:
            list[dict]: 상세 정보가 추가된 리포지토리 정보 목록
        """
        client = await self._get_client()
        results: list[dict] = []

        for full_name in repo_full_names:
            try:
                repo_info = await self._fetch_single_repo(client, full_name)
                if repo_info:
                    results.append(repo_info)
                # API Rate limit 방지를 위한 짧은 대기
                await self._rate_limit_delay()
            except Exception as e:
                logger.warning("리포지토리 상세 조회 실패 (%s): %s", full_name, e)

        logger.info(
            "리포지토리 상세 조회 완료: %d/%d 성공",
            len(results),
            len(repo_full_names),
        )
        return results

    async def _fetch_single_repo(
        self,
        client: httpx.AsyncClient,
        full_name: str,
    ) -> Optional[dict]:
        """단일 리포지토리의 GitHub API 상세 정보를 조회합니다.

        Args:
            client: httpx 비동기 클라이언트
            full_name: "owner/repo" 형식의 리포지토리 전체 이름

        Returns:
            Optional[dict]: 리포지토리 상세 정보 또는 None
        """
        url = f"https://api.github.com/repos/{full_name}"
        response = await client.get(url)

        if response.status_code != 200:
            logger.warning(
                "GitHub API 응답 오류: status=%d, repo=%s",
                response.status_code,
                full_name,
            )
            return None

        data = response.json()

        # 라이선스 정보 추출 (spdx_id 우선, 없으면 name)
        license_info = data.get("license")
        license_key = ""
        if license_info:
            license_key = license_info.get("spdx_id") or license_info.get("name") or ""

        return {
            "repo_name": full_name,
            "full_name": data.get("full_name", full_name),
            "description": data.get("description") or "",
            "html_url": data.get("html_url", ""),
            "topics": data.get("topics", []),
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
            "pushed_at": data.get("pushed_at", ""),
            "language": data.get("language") or "",
            "stars_count": data.get("stargazers_count", 0),
            "forks_count": data.get("forks_count", 0),
            "open_issues_count": data.get("open_issues_count", 0),
            "license": license_key,
            "default_branch": data.get("default_branch", "main"),
            "archived": data.get("archived", False),
        }

    @staticmethod
    async def _rate_limit_delay() -> None:
        """API Rate limit 방지를 위해 짧은 대기를 수행합니다.

        비인증 시 60 req/hour, 인증 시 5,000 req/hour 제한이 있으므로
        안전하게 요청 간 간격을 둡니다.
        """
        import asyncio

        await asyncio.sleep(0.5)

    # ─── 필터링 ──────────────────────────────────────────────────────────

    @staticmethod
    def filter_by_keywords(
        repos: list[dict],
        keywords: Optional[list[str]] = None,
    ) -> list[dict]:
        """리포지토리 목록을 키워드 기반으로 필터링합니다.

        리포지토리 이름, 설명, 언어, 토픽 중 하나라도 키워드가
        포함되면 매칭된 것으로 간주합니다.

        Args:
            repos: 리포지토리 정보 딕셔너리 목록
            keywords: 필터링 키워드 목록 (기본값: DEFAULT_KEYWORDS)

        Returns:
            list[dict]: 필터링된 리포지토리 목록
        """
        if keywords is None:
            keywords = DEFAULT_KEYWORDS

        # 소문자 키워드 셋 생성 (대소문자 무시 매칭)
        keyword_set = {kw.lower() for kw in keywords}

        filtered: list[dict] = []
        for repo in repos:
            # 검색 대상 텍스트 결합 (이름 + 설명 + 언어 + 토픽)
            name = repo.get("repo_name", "").lower()
            description = repo.get("description", "").lower()
            language = repo.get("language", "").lower()

            # topics는 리스트일 수 있으므로 결합
            topics = repo.get("topics", [])
            if isinstance(topics, list):
                topics_text = " ".join(topics).lower()
            else:
                topics_text = str(topics).lower()

            combined_text = f"{name} {description} {language} {topics_text}"

            # 키워드 매칭 검사
            if any(kw in combined_text for kw in keyword_set):
                filtered.append(repo)

        logger.info(
            "키워드 필터링 완료: %d/%d 매칭 (키워드=%s)",
            len(filtered),
            len(repos),
            keywords,
        )
        return filtered
