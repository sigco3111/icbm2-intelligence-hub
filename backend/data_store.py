"""
로컬 캐시 데이터 저장소 모듈

aiosqlite 기반의 비동기 데이터베이스 관리 클래스입니다.
GitHub Trending 리포지토리 정보와 Notion 쿼리 결과를 로컬에 캐싱합니다.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import aiosqlite


class DataStore:
    """
    SQLite 기반 비동기 데이터 저장소.

    테이블:
        - trending_repos: GitHub 트렌딩 리포지토리 캐시
        - notion_cache: Notion 데이터베이스 쿼리 결과 캐시

    사용 예:
        store = DataStore("data/cache.db")
        await store.init()
        await store.save_trending_repos(repos)
        repos = await store.get_trending_repos(since_days=7)
    """

    def __init__(self, db_path: str = "data/cache.db") -> None:
        """
        DataStore 초기화

        Args:
            db_path: SQLite 데이터베이스 파일 경로
        """
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def init(self) -> None:
        """
        데이터베이스 초기화 — 필요한 디렉토리와 테이블을 생성합니다.

        앱 시작 시 반드시 호출해야 합니다.
        """
        # DB 파일 경로의 상위 디렉토리가 없으면 생성
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        self._conn = await aiosqlite.connect(self.db_path)
        # 딕셔너리 형태로 Row 접근 (row["column_name"])
        self._conn.row_factory = aiosqlite.Row

        await self._conn.executescript("""
            -- GitHub 트렌딩 리포지토리 캐시 테이블
            CREATE TABLE IF NOT EXISTS trending_repos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_name TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                language TEXT DEFAULT '',
                stars INTEGER DEFAULT 0,
                forks INTEGER DEFAULT 0,
                today_stars INTEGER DEFAULT 0,
                fetched_at TEXT NOT NULL
            );

            -- Notion 쿼리 결과 캐시 테이블
            CREATE TABLE IF NOT EXISTS notion_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                db_type TEXT NOT NULL,
                page_id TEXT NOT NULL,
                data_json TEXT NOT NULL,
                fetched_at TEXT NOT NULL
            );

            -- 조회 성능 향상을 위한 인덱스
            CREATE INDEX IF NOT EXISTS idx_trending_repos_fetched_at
                ON trending_repos(fetched_at);
            CREATE INDEX IF NOT EXISTS idx_notion_cache_db_type
                ON notion_cache(db_type);
        """)
        await self._conn.commit()

    async def close(self) -> None:
        """데이터베이스 연결을 안전하게 종료합니다."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def _ensure_conn(self) -> aiosqlite.Connection:
        """연결이 활성 상태인지 확인하고 반환합니다."""
        if self._conn is None:
            raise RuntimeError("DataStore가 초기화되지 않았습니다. init()을 먼저 호출하세요.")
        return self._conn

    # ─── GitHub Trending 리포지토리 관련 메서드 ──────────────────────────

    async def save_trending_repos(self, repos: list[dict[str, Any]]) -> int:
        """
        트렌딩 리포지토리 목록을 UPSERT 방식으로 저장합니다.

        같은 repo_name이 이미 존재하면 stars, forks, today_stars, fetched_at을 갱신합니다.

        Args:
            repos: GitHub API 응답에서 추출한 리포지토리 딕셔너리 목록.
                   각 딕셔너리는 repo_name, description, language,
                   stars, forks, today_stars 키를 포함해야 합니다.

        Returns:
            저장(또는 갱신)된 행의 수
        """
        conn = await self._ensure_conn()
        now = datetime.now(timezone.utc).isoformat()
        saved = 0

        for repo in repos:
            await conn.execute(
                """
                INSERT INTO trending_repos
                    (repo_name, description, language, stars, forks, today_stars, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(repo_name) DO UPDATE SET
                    description = excluded.description,
                    language = excluded.language,
                    stars = excluded.stars,
                    forks = excluded.forks,
                    today_stars = excluded.today_stars,
                    fetched_at = excluded.fetched_at
                """,
                (
                    repo.get("repo_name", ""),
                    repo.get("description", ""),
                    repo.get("language", ""),
                    repo.get("stars", 0),
                    repo.get("forks", 0),
                    repo.get("today_stars", 0),
                    now,
                ),
            )
            saved += 1

        await conn.commit()
        return saved

    async def get_trending_repos(self, since_days: int = 7) -> list[dict[str, Any]]:
        """
        지정한 기간 내에 수집된 트렌딩 리포지토리 목록을 조회합니다.

        Args:
            since_days: 조회할 기간(일). 기본값 7일.

        Returns:
            리포지토리 딕셔너리 목록 (fetched_at 내림차순 정렬)
        """
        conn = await self._ensure_conn()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()

        cursor = await conn.execute(
            """
            SELECT repo_name, description, language, stars, forks, today_stars, fetched_at
            FROM trending_repos
            WHERE fetched_at >= ?
            ORDER BY fetched_at DESC
            """,
            (cutoff,),
        )

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    # ─── Notion 캐시 관련 메서드 ─────────────────────────────────────────

    async def save_notion_cache(
        self, db_type: str, page_id: str, data: dict[str, Any]
    ) -> None:
        """
        Notion 데이터베이스 쿼리 결과를 캐시에 저장합니다.

        Args:
            db_type: Notion 데이터베이스 유형 (예: "ai_model", "performance")
            page_id: Notion 페이지 ID
            data: 캐시할 데이터 딕셔너리 (JSON 직렬화 후 저장)
        """
        conn = await self._ensure_conn()
        now = datetime.now(timezone.utc).isoformat()
        data_json = json.dumps(data, ensure_ascii=False, default=str)

        await conn.execute(
            """
            INSERT INTO notion_cache (db_type, page_id, data_json, fetched_at)
            VALUES (?, ?, ?, ?)
            """,
            (db_type, page_id, data_json, now),
        )
        await conn.commit()

    async def get_notion_cache(self, db_type: str) -> list[dict[str, Any]]:
        """
        특정 Notion 데이터베이스 유형의 캐시된 데이터를 조회합니다.

        Args:
            db_type: 조회할 Notion 데이터베이스 유형

        Returns:
            캐시된 데이터 딕셔너리 목록 (fetched_at 내림차순 정렬)
        """
        conn = await self._ensure_conn()

        cursor = await conn.execute(
            """
            SELECT db_type, page_id, data_json, fetched_at
            FROM notion_cache
            WHERE db_type = ?
            ORDER BY fetched_at DESC
            """,
            (db_type,),
        )

        rows = await cursor.fetchall()
        result = []
        for row in rows:
            item = dict(row)
            # JSON 문자열을 파이썬 딕셔너리로 복원
            try:
                item["data"] = json.loads(item.pop("data_json"))
            except json.JSONDecodeError:
                item["data"] = {}
            result.append(item)

        return result
