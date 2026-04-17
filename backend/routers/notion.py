"""
Notion API 라우터

Notion 데이터베이스 조회 엔드포인트를 제공합니다.
각 엔드포인트는 1시간 캐시를 적용하여 Notion API 호출을 최소화합니다.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Request

from backend.config import settings
from backend.notion_client import NotionClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notion", tags=["notion"])

# 캐시 유효 기간 (1시간)
CACHE_TTL = timedelta(hours=1)


async def _get_store(request: Request) -> Any:
    """요청 컨텍스트에서 DataStore 인스턴스를 가져옵니다."""
    return request.app.state.store


async def _is_cache_fresh(cached_items: list[dict[str, Any]]) -> bool:
    """
    캐시가 유효한지 확인합니다.

    가장 최근 캐시 항목의 fetched_at이 CACHE_TTL 이내이면 유효로 간주합니다.

    Args:
        cached_items: 캐시된 데이터 항목 목록

    Returns:
        캐시가 유효하면 True, 아니면 False
    """
    if not cached_items:
        return False

    # 가장 최근 항목의 시간 확인
    latest = cached_items[0].get("fetched_at", "")
    if not latest:
        return False

    try:
        fetched_at = datetime.fromisoformat(latest)
        now = datetime.now(timezone.utc)
        return (now - fetched_at) < CACHE_TTL
    except (ValueError, TypeError):
        return False


async def _fetch_and_cache_notion(
    db_type: str, db_id: str, store: Any
) -> list[dict[str, Any]]:
    """
    Notion 데이터베이스를 조회하고 결과를 캐시에 저장합니다.

    Args:
        db_type: 캐시 구분 키 (예: "ai_models", "performance")
        db_id: Notion 데이터베이스 ID
        store: DataStore 인스턴스

    Returns:
        정규화된 Notion 페이지 목록
    """
    async with NotionClient(settings.notion_api_key) as client:
        pages = await client.query_database(db_id)

    # 각 페이지를 개별적으로 캐시에 저장
    for page in pages:
        await store.save_notion_cache(
            db_type=db_type,
            page_id=page.get("id", ""),
            data=page,
        )

    logger.info("Notion %s 데이터 %d건 조회 및 캐시 저장 완료", db_type, len(pages))
    return pages


# ─── AI 모델 트래커 ─────────────────────────────────────────────────────


@router.get("/ai-models")
async def get_ai_models(request: Request) -> dict[str, Any]:
    """
    AI 모델 트래커 데이터를 반환합니다.

    Notion AI 모델 데이터베이스에서 모델 정보를 조회합니다.
    캐시가 유효하면 캐시 데이터를 반환합니다.

    Returns:
        {"models": [{"id": "...", "properties": {...}, ...}, ...]}
    """
    store = await _get_store(request)
    db_type = "ai_models"

    # 캐시 확인
    cached = await store.get_notion_cache(db_type)
    if await _is_cache_fresh(cached):
        logger.debug("AI 모델 캐시 히트 (%d건)", len(cached))
        return {"models": [item["data"] for item in cached]}

    # 캐시 미스 — Notion API 호출
    pages = await _fetch_and_cache_notion(
        db_type=db_type, db_id=settings.notion_ai_model_db, store=store
    )
    return {"models": pages}


# ─── 일별 성과 데이터 ──────────────────────────────────────────────────


@router.get("/performance")
async def get_performance(request: Request) -> dict[str, Any]:
    """
    일별 성과 데이터를 반환합니다.

    Notion 성과 데이터베이스에서 카테고리별 메트릭을 조회합니다.

    Returns:
        {"performance": [{"id": "...", "properties": {...}, ...}, ...]}
    """
    store = await _get_store(request)
    db_type = "performance"

    cached = await store.get_notion_cache(db_type)
    if await _is_cache_fresh(cached):
        logger.debug("성과 데이터 캐시 히트 (%d건)", len(cached))
        return {"performance": [item["data"] for item in cached]}

    pages = await _fetch_and_cache_notion(
        db_type=db_type, db_id=settings.notion_performance_db, store=store
    )
    return {"performance": pages}


# ─── 학습 로그 ─────────────────────────────────────────────────────────


@router.get("/learning")
async def get_learning(request: Request) -> dict[str, Any]:
    """
    학습 로그 데이터를 반환합니다.

    Notion 학습 로그 데이터베이스에서 학습 기록을 조회합니다.

    Returns:
        {"learning": [{"id": "...", "properties": {...}, ...}, ...]}
    """
    store = await _get_store(request)
    db_type = "learning"

    cached = await store.get_notion_cache(db_type)
    if await _is_cache_fresh(cached):
        logger.debug("학습 로그 캐시 히트 (%d건)", len(cached))
        return {"learning": [item["data"] for item in cached]}

    pages = await _fetch_and_cache_notion(
        db_type=db_type, db_id=settings.notion_learning_db, store=store
    )
    return {"learning": pages}


# ─── iOS 트렌드 ────────────────────────────────────────────────────────


@router.get("/ios-trends")
async def get_ios_trends(request: Request) -> dict[str, Any]:
    """
    iOS 트렌드 데이터를 반환합니다.

    Notion iOS 트렌드 데이터베이스에서 iOS 생태계 관련 트렌드를 조회합니다.

    Returns:
        {"ios_trends": [{"id": "...", "properties": {...}, ...}, ...]}
    """
    store = await _get_store(request)
    db_type = "ios_trends"

    cached = await store.get_notion_cache(db_type)
    if await _is_cache_fresh(cached):
        logger.debug("iOS 트렌드 캐시 히트 (%d건)", len(cached))
        return {"ios_trends": [item["data"] for item in cached]}

    pages = await _fetch_and_cache_notion(
        db_type=db_type, db_id=settings.notion_ios_trend_db, store=store
    )
    return {"ios_trends": pages}


# ─── 투자 메모 ─────────────────────────────────────────────────────────


@router.get("/invest")
async def get_invest(request: Request) -> dict[str, Any]:
    """
    투자 메모 데이터를 반환합니다.

    Notion 투자 메모 데이터베이스에서 투자 관련 메모를 조회합니다.

    Returns:
        {"invest": [{"id": "...", "properties": {...}, ...}, ...]}
    """
    store = await _get_store(request)
    db_type = "invest"

    cached = await store.get_notion_cache(db_type)
    if await _is_cache_fresh(cached):
        logger.debug("투자 메모 캐시 히트 (%d건)", len(cached))
        return {"invest": [item["data"] for item in cached]}

    pages = await _fetch_and_cache_notion(
        db_type=db_type, db_id=settings.notion_invest_db, store=store
    )
    return {"invest": pages}
