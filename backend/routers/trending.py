"""
GitHub Trending 라우터

GitHub Trending 리포지토리 조회 및 히스토리 엔드포인트를 제공합니다.
AI/iOS 관련 키워드 필터링을 기본으로 적용합니다.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query, Request

from backend.github_crawler import GitHubTrendingCrawler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trending", tags=["trending"])

# 기본 필터링 키워드 — AI/iOS 관련 리포지토리만 추출
DEFAULT_FILTER_KEYWORDS = [
    "ai", "llm", "agent", "gpt", "claude", "gemini",
    "machine-learning", "deep-learning", "ios", "swift",
]


def _get_crawler(request: Request) -> GitHubTrendingCrawler:
    """요청 컨텍스트에서 GitHubTrendingCrawler 인스턴스를 생성합니다."""
    return GitHubTrendingCrawler()


async def _get_store(request: Request) -> Any:
    """요청 컨텍스트에서 DataStore 인스턴스를 가져옵니다."""
    return request.app.state.store


def _normalize_repo_for_save(repo: dict[str, Any]) -> dict[str, Any]:
    """
    크롤러 응답을 DataStore 저장 형식으로 정규화합니다.

    크롤러가 반환하는 키(stars_count, forks_count)를
    DataStore가 기대하는 키(stars, forks)로 매핑합니다.

    Args:
        repo: 크롤러에서 반환한 리포지토리 딕셔너리

    Returns:
        DataStore 저장용 정규화된 딕셔너리
    """
    return {
        "repo_name": repo.get("repo_name", ""),
        "description": repo.get("description", ""),
        "language": repo.get("language", ""),
        "stars": repo.get("stars_count", 0),
        "forks": repo.get("forks_count", 0),
        "today_stars": repo.get("today_stars", 0),
    }


# ─── 일일 트렌딩 ──────────────────────────────────────────────────────


@router.get("/daily")
async def get_daily_trending(
    request: Request,
    language: str = Query("", description="프로그래밍 언어 필터 (예: python, swift)"),
) -> dict[str, Any]:
    """
    일일 GitHub 트렌딩 리포지토리를 반환합니다.

    GitHub Trending 페이지에서 일일 기준으로 인기 리포지토리를 조회하고,
    AI/iOS 관련 키워드로 필터링합니다. 결과를 로컬 DB에 캐시합니다.

    Args:
        language: 프로그래밍 언어 필터 (빈 문자열이면 전체)

    Returns:
        {"repos": [{"name": "...", "description": "...", "stars": N, ...}, ...]}
    """
    crawler = _get_crawler(request)
    store = await _get_store(request)

    # 트렌딩 페이지 크롤링
    repos = await crawler.fetch_trending(language=language, since="daily")

    # AI/iOS 키워드 필터링
    filtered = crawler.filter_by_keywords(repos, DEFAULT_FILTER_KEYWORDS)

    # 캐시 저장
    if filtered:
        save_data = [_normalize_repo_for_save(repo) for repo in filtered]
        saved_count = await store.save_trending_repos(save_data)
        logger.info("일일 트렌딩 %d건 캐시 저장 완료", saved_count)

    # 응답 형식 변환
    result_repos = [
        {
            "name": repo.get("repo_name", ""),
            "description": repo.get("description", ""),
            "language": repo.get("language", ""),
            "stars": repo.get("stars_count", 0),
            "forks": repo.get("forks_count", 0),
            "today_stars": repo.get("today_stars", 0),
        }
        for repo in filtered
    ]

    return {"repos": result_repos}


# ─── 주간 트렌딩 ──────────────────────────────────────────────────────


@router.get("/weekly")
async def get_weekly_trending(
    request: Request,
    language: str = Query("", description="프로그래밍 언어 필터 (예: python, swift)"),
) -> dict[str, Any]:
    """
    주간 GitHub 트렌딩 리포지토리를 반환합니다.

    GitHub Trending 페이지에서 주간 기준으로 인기 리포지토리를 조회하고,
    AI/iOS 관련 키워드로 필터링합니다. 결과를 로컬 DB에 캐시합니다.

    Args:
        language: 프로그래밍 언어 필터 (빈 문자열이면 전체)

    Returns:
        {"repos": [{"name": "...", "description": "...", "stars": N, ...}, ...]}
    """
    crawler = _get_crawler(request)
    store = await _get_store(request)

    repos = await crawler.fetch_trending(language=language, since="weekly")
    filtered = crawler.filter_by_keywords(repos, DEFAULT_FILTER_KEYWORDS)

    if filtered:
        save_data = [_normalize_repo_for_save(repo) for repo in filtered]
        saved_count = await store.save_trending_repos(save_data)
        logger.info("주간 트렌딩 %d건 캐시 저장 완료", saved_count)

    result_repos = [
        {
            "name": repo.get("repo_name", ""),
            "description": repo.get("description", ""),
            "language": repo.get("language", ""),
            "stars": repo.get("stars_count", 0),
            "forks": repo.get("forks_count", 0),
            "today_stars": repo.get("today_stars", 0),
        }
        for repo in filtered
    ]

    return {"repos": result_repos}


# ─── 히스토리 조회 ────────────────────────────────────────────────────


@router.get("/history")
async def get_trending_history(
    request: Request,
    days: int = Query(7, ge=1, le=90, description="조회할 기간(일)"),
) -> dict[str, Any]:
    """
    트렌딩 리포지토리 히스토리를 반환합니다.

    로컬 DB에 캐시된 트렌딩 리포지토리 기록을 지정한 기간 동안 조회합니다.

    Args:
        days: 조회할 기간(일). 1~90일 범위, 기본값 7일

    Returns:
        {"repos": [{"repo_name": "...", "description": "...", ...}, ...]}
    """
    store = await _get_store(request)

    repos = await store.get_trending_repos(since_days=days)
    logger.info("트렌딩 히스토리 %d건 조회 (기간: %d일)", len(repos), days)

    return {"repos": repos}
