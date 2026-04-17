"""
크론 스케줄러 모듈

Hermes 크론에서 주기적으로 실행할 비동기 작업 함수들을 정의합니다.
APScheduler 대신 간단한 async 함수만 제공하며, 실제 스케줄링은
Hermes 크론 시스템에서 관리합니다.

제공하는 작업:
  - run_trending_update(): GitHub 트렌딩 크롤링 + DB 저장
  - run_notion_sync(): Notion 데이터 캐시 갱신
  - run_weekly_digest(): 주간 요약 생성 + Tistory 발행
  - run_all(): 위 3개를 순차 실행
"""

from __future__ import annotations

import logging
from typing import Any

from backend.config import settings
from backend.data_store import DataStore
from backend.github_crawler import GitHubTrendingCrawler, DEFAULT_KEYWORDS
from backend.notion_client import NotionClient
from backend.tistory_publisher import TistoryPublisher

logger = logging.getLogger(__name__)


async def run_trending_update() -> dict[str, Any]:
    """
    GitHub 트렌딩 크롤링 + DB 저장 작업을 실행합니다.

    일일 및 주간 트렌딩 페이지를 크롤링하고,
    AI/iOS 관련 키워드로 필터링한 후 DB에 저장합니다.

    Returns:
        실행 결과 딕셔너리
        예: {"daily_count": 15, "weekly_count": 20, "status": "ok"}
    """
    logger.info("=== 트렌딩 업데이트 작업 시작 ===")

    store = DataStore(db_path=settings.db_path)
    crawler = GitHubTrendingCrawler(github_token=settings.github_token)

    try:
        await store.init()

        # ── 일일 트렌딩 크롤링 ──
        daily_repos = await crawler.fetch_trending(since="daily")
        daily_filtered = crawler.filter_by_keywords(daily_repos, DEFAULT_KEYWORDS)
        daily_saved = 0
        if daily_filtered:
            save_data = [
                {
                    "repo_name": r.get("repo_name", ""),
                    "description": r.get("description", ""),
                    "language": r.get("language", ""),
                    "stars": r.get("stars_count", 0),
                    "forks": r.get("forks_count", 0),
                    "today_stars": r.get("today_stars", 0),
                }
                for r in daily_filtered
            ]
            daily_saved = await store.save_trending_repos(save_data)

        # ── 주간 트렌딩 크롤링 ──
        weekly_repos = await crawler.fetch_trending(since="weekly")
        weekly_filtered = crawler.filter_by_keywords(weekly_repos, DEFAULT_KEYWORDS)
        weekly_saved = 0
        if weekly_filtered:
            save_data = [
                {
                    "repo_name": r.get("repo_name", ""),
                    "description": r.get("description", ""),
                    "language": r.get("language", ""),
                    "stars": r.get("stars_count", 0),
                    "forks": r.get("forks_count", 0),
                    "today_stars": r.get("today_stars", 0),
                }
                for r in weekly_filtered
            ]
            weekly_saved = await store.save_trending_repos(save_data)

        result = {
            "daily_count": daily_saved,
            "weekly_count": weekly_saved,
            "status": "ok",
        }
        logger.info("트렌딩 업데이트 완료: 일일=%d, 주간=%d", daily_saved, weekly_saved)
        return result

    except Exception as e:
        logger.error("트렌딩 업데이트 실패: %s", e, exc_info=True)
        return {"status": "error", "error": str(e)}

    finally:
        await crawler.close()
        await store.close()


async def run_notion_sync() -> dict[str, Any]:
    """
    Notion 데이터 캐시 갱신 작업을 실행합니다.

    설정된 모든 Notion 데이터베이스를 조회하고
    결과를 로컬 캐시에 저장합니다.

    Returns:
        실행 결과 딕셔너리
        예: {"ai_models": 12, "ios_trends": 5, "status": "ok"}
    """
    logger.info("=== Notion 동기화 작업 시작 ===")

    store = DataStore(db_path=settings.db_path)

    # 동기화 대상 Notion DB 매핑 (db_type → db_id)
    sync_targets = {
        "ai_models": settings.notion_ai_model_db,
        "performance": settings.notion_performance_db,
        "learning": settings.notion_learning_db,
        "ios_trends": settings.notion_ios_trend_db,
        "invest": settings.notion_invest_db,
    }

    result: dict[str, Any] = {}

    try:
        await store.init()

        async with NotionClient(settings.notion_api_key) as client:
            for db_type, db_id in sync_targets.items():
                if not db_id:
                    logger.warning("Notion DB ID가 설정되지 않음: %s", db_type)
                    result[db_type] = 0
                    continue

                try:
                    pages = await client.query_database(db_id)
                    count = 0
                    for page in pages:
                        await store.save_notion_cache(
                            db_type=db_type,
                            page_id=page.get("id", ""),
                            data=page,
                        )
                        count += 1
                    result[db_type] = count
                    logger.info("Notion %s 동기화 완료: %d건", db_type, count)
                except Exception as e:
                    logger.error("Notion %s 동기화 실패: %s", db_type, e)
                    result[db_type] = 0

        result["status"] = "ok"
        logger.info("Notion 동기화 작업 완료: %s", result)
        return result

    except Exception as e:
        logger.error("Notion 동기화 작업 실패: %s", e, exc_info=True)
        return {"status": "error", "error": str(e)}

    finally:
        await store.close()


async def run_weekly_digest() -> dict[str, Any]:
    """
    주간 요약 생성 + Tistory 발행 작업을 실행합니다.

    1. DB에서 최근 7일간의 트렌딩 리포지토리를 조회
    2. Notion 캐시에서 AI 모델 및 iOS 트렌드 데이터를 조회
    3. TistoryPublisher로 주간 요약 마크다운 생성
    4. Tistory 블로그에 발행

    Returns:
        실행 결과 딕셔너리
        예: {"status": "ok", "post_id": "123", "content_length": 5000}
    """
    logger.info("=== 주간 요약 발행 작업 시작 ===")

    store = DataStore(db_path=settings.db_path)
    publisher = TistoryPublisher(
        access_token=settings.tistory_access_token,
        blog_name=settings.tistory_blog_name,
    )

    try:
        await store.init()

        # ── 1. 트렌딩 리포지토리 조회 (최근 7일) ──
        trending_repos = await store.get_trending_repos(since_days=7)
        logger.info("트렌딩 리포지토리 %d건 조회 완료", len(trending_repos))

        # ── 2. Notion 캐시 데이터 조회 ──
        notion_data: dict[str, list[dict[str, Any]]] = {}
        for db_type in ("ai_models", "ios_trends"):
            cached = await store.get_notion_cache(db_type)
            notion_data[db_type] = [item.get("data", {}) for item in cached]
            logger.info("Notion %s 캐시 %d건 조회", db_type, len(notion_data[db_type]))

        # ── 3. 주간 요약 생성 ──
        title = "📋 이번 주 GitHub AI/iOS 트렌딩 + 기술 요약"
        content = await publisher.generate_weekly_digest(trending_repos, notion_data)
        logger.info("주간 요약 생성 완료 (길이: %d자)", len(content))

        # ── 4. Tistory 발행 ──
        publish_result = await publisher.publish(
            title=title,
            content=content,
            tags=["AI", "iOS", "GitHub", "트렌딩", "주간요약"],
        )

        post_id = publish_result.get("postId", "")
        result = {
            "status": "ok" if publish_result.get("status") == "200" else "publish_failed",
            "post_id": post_id,
            "content_length": len(content),
            "trending_count": len(trending_repos),
            "notion_data_keys": list(notion_data.keys()),
        }
        logger.info("주간 요약 발행 완료: postId=%s", post_id)
        return result

    except Exception as e:
        logger.error("주간 요약 발행 실패: %s", e, exc_info=True)
        return {"status": "error", "error": str(e)}

    finally:
        await store.close()


async def run_all() -> dict[str, Any]:
    """
    모든 스케줄링 작업을 순차적으로 실행합니다.

    실행 순서:
    1. GitHub 트렌딩 업데이트
    2. Notion 데이터 동기화
    3. 주간 요약 생성 + Tistory 발행

    Returns:
        각 작업의 실행 결과를 포함한 딕셔너리
        예: {
            "trending": {"status": "ok", ...},
            "notion": {"status": "ok", ...},
            "digest": {"status": "ok", ...}
        }
    """
    logger.info("=== 전체 스케줄 작업 순차 실행 시작 ===")
    results: dict[str, Any] = {}

    # 1. 트렌딩 업데이트
    try:
        results["trending"] = await run_trending_update()
    except Exception as e:
        logger.error("트렌딩 업데이트 예외: %s", e)
        results["trending"] = {"status": "error", "error": str(e)}

    # 2. Notion 동기화
    try:
        results["notion"] = await run_notion_sync()
    except Exception as e:
        logger.error("Notion 동기화 예외: %s", e)
        results["notion"] = {"status": "error", "error": str(e)}

    # 3. 주간 요약 발행
    try:
        results["digest"] = await run_weekly_digest()
    except Exception as e:
        logger.error("주간 요약 발행 예외: %s", e)
        results["digest"] = {"status": "error", "error": str(e)}

    logger.info("=== 전체 스케줄 작업 완료 ===")
    return results
