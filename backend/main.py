"""
ICBM2 Intelligence Hub — FastAPI 메인 애플리케이션

Notion 데이터 시각화 + GitHub Trending 뉴스 요약 웹 대시보드의 엔트리포인트입니다.
CORS 미들웨어, 정적 파일 서빙, healthcheck 엔드포인트를 설정합니다.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.data_store import DataStore


# ─── 전역 데이터 저장소 인스턴스 ────────────────────────────────────────────
# 라우터 및 엔드포인트에서 app.state.store로 접근 가능
data_store = DataStore(db_path=settings.db_path)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    애플리케이션 수명 주기 관리자.

    시작 시: DataStore 초기화 (테이블 생성)
    종료 시: DataStore 연결 종료
    """
    # ─── 시작 ───────────────────────────────────────────────────────────
    await data_store.init()
    app.state.store = data_store
    yield
    # ─── 종료 ───────────────────────────────────────────────────────────
    await data_store.close()


# ─── FastAPI 앱 생성 ────────────────────────────────────────────────────────
app = FastAPI(
    title="ICBM2 Intelligence Hub",
    description="Notion 데이터 시각화 + GitHub Trending 뉴스 요약 대시보드",
    version="0.1.0",
    lifespan=lifespan,
)


# ─── CORS 미들웨어 설정 (개발용: 모든 오리진 허용) ─────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── 정적 파일 마운트 ───────────────────────────────────────────────────────
# frontend/ 디렉토리를 /static 경로로 서빙
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


# ─── Healthcheck 엔드포인트 ─────────────────────────────────────────────────
@app.get("/api/health", tags=["health"])
async def healthcheck() -> dict[str, str]:
    """
    서버 상태 확인 엔드포인트.

    Returns:
        {"status": "ok"} — 서버가 정상 동작 중임을 나타냄
    """
    return {"status": "ok"}


# ─── API 라우터 등록 ──────────────────────────────────────────────────────────
from backend.routers import notion, trending

app.include_router(notion.router)
app.include_router(trending.router)


# ─── 수동 작업 실행 엔드포인트 (크론 대신 수동 트리거용) ─────────────────────
from backend.scheduler import run_trending_update, run_notion_sync, run_weekly_digest


@app.post("/api/trending/refresh", tags=["admin"])
async def refresh_trending() -> dict:
    """
    GitHub 트렌딩 데이터를 수동으로 갱신합니다.

    일일/주간 트렌딩 페이지를 크롤링하여 AI/iOS 관련 리포지토리를 DB에 저장합니다.

    Returns:
        {"daily_count": N, "weekly_count": M, "status": "ok"}
    """
    from backend.scheduler import run_trending_update
    return await run_trending_update()


@app.post("/api/notion/refresh", tags=["admin"])
async def refresh_notion() -> dict:
    """
    Notion 데이터 캐시를 수동으로 갱신합니다.

    모든 Notion 데이터베이스를 조회하여 로컬 캐시를 업데이트합니다.

    Returns:
        {"ai_models": N, "ios_trends": M, ..., "status": "ok"}
    """
    from backend.scheduler import run_notion_sync
    return await run_notion_sync()


@app.post("/api/publish/weekly", tags=["admin"])
async def publish_weekly_digest() -> dict:
    """
    주간 요약을 생성하여 Tistory에 발행합니다.

    최근 7일간의 트렌딩 리포지토리와 Notion 데이터를 결합하여
    주간 요약 글을 생성하고 Tistory 블로그에 발행합니다.

    Returns:
        {"status": "ok", "post_id": "123", "content_length": N}
    """
    from backend.scheduler import run_weekly_digest
    return await run_weekly_digest()
