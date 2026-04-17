"""
애플리케이션 설정 모듈

pydantic-settings 기반으로 환경변수(.env 파일)에서 설정값을 로드합니다.
모든 Notion DB ID, API 키, 서버 설정을 중앙에서 관리합니다.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    ICBM2 Intelligence Hub 전체 설정을 담는 클래스.

    환경변수 또는 .env 파일에서 값을 읽어옵니다.
    필수값(notion_api_key, Notion DB ID 등)이 없으면 ValidationError가 발생합니다.
    """

    model_config = SettingsConfigDict(
        # 프로젝트 루트의 .env 파일을 자동으로 로드
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        # 환경변수 접두사 (예: ICBM_NOTION_API_KEY)
        env_prefix="",
        # .env 파일 누락 시 에러 대신 경고만 출력
        case_sensitive=False,
    )

    # ─── Notion API ─────────────────────────────────────────────────────────
    notion_api_key: str = ""

    # ─── GitHub ─────────────────────────────────────────────────────────────
    github_token: str = ""

    # ─── Tistory 블로그 ────────────────────────────────────────────────────
    tistory_access_token: str = ""
    tistory_blog_name: str = ""

    # ─── 서버 설정 ─────────────────────────────────────────────────────────
    port: int = 8100
    host: str = "0.0.0.0"

    # ─── Notion 데이터베이스 ID ────────────────────────────────────────────
    notion_ai_model_db: str = ""
    notion_performance_db: str = ""
    notion_learning_db: str = ""
    notion_ios_trend_db: str = ""
    notion_invest_db: str = ""

    # ─── 로컬 캐시 DB ─────────────────────────────────────────────────────
    db_path: str = "data/cache.db"


# 싱글톤 인스턴스 — 모듈 임포트 시 한 번만 생성됨
settings = Settings()
