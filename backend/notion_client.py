"""
Notion API 연동 모듈

Notion 데이터베이스를 조회하고 속성을 Python 기본 타입으로 정규화하는 비동기 클라이언트.
httpx.AsyncClient를 기반으로 동작하며, 비동기 컨텍스트 매니저를 지원합니다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, AsyncIterator

import httpx

# Notion API 기본 설정
NOTION_BASE_URL = "https://api.notion.com/v1/"
NOTION_VERSION = "2022-06-28"

# 기본 데이터베이스 ID 목록
DEFAULT_DATABASE_IDS: dict[str, str] = {
    "ai_model_tracker": "33c76f2e-9097-8132-9033-e434f4055b56",
    "performance": "33f76f2e-9097-8116-a225-c0c23f1a8a9d",
    "learning_log": "33c76f2e-9097-8184-b51e-fa09efcf6d4d",
    "ios_trend": "33c76f2e-9097-8112-84f6-c60096cc0e11",
    "invest_memo": "33c76f2e-9097-8107-800f-efc2f699aa93",
}


# ─── 데이터 정규화 헬퍼 함수들 ─────────────────────────────────────────────


def format_title(prop: dict[str, Any]) -> str:
    """
    Notion Title 속성을 문자열로 변환합니다.

    Args:
        prop: Notion title 속성 객체 (예: {"type": "title", "title": [{"plain_text": "..."}]})

    Returns:
        제목 문자열. 빈 값이면 빈 문자열 반환.
    """
    if not prop or prop.get("type") != "title":
        return ""
    title_parts = prop.get("title", [])
    return "".join(part.get("plain_text", "") for part in title_parts)


def format_date(prop: dict[str, Any]) -> str:
    """
    Notion Date 속성을 'YYYY-MM-DD' 형식 문자열로 변환합니다.

    Args:
        prop: Notion date 속성 객체 (예: {"type": "date", "date": {"start": "2024-01-15"}})

    Returns:
        'YYYY-MM-DD' 형식 문자열. 빈 값이면 빈 문자열 반환.
    """
    if not prop or prop.get("type") != "date":
        return ""
    date_obj = prop.get("date")
    if not date_obj or not date_obj.get("start"):
        return ""
    # 시작일만 사용 (시간 포함 시 날짜 부분만 추출)
    start_str = date_obj["start"]
    # "2024-01-15T00:00:00.000+09:00" 같은 ISO 형식에서 날짜만 추출
    if "T" in start_str:
        start_str = start_str.split("T")[0]
    return start_str


def format_number(prop: dict[str, Any]) -> float:
    """
    Notion Number 속성을 float로 변환합니다.

    Args:
        prop: Notion number 속성 객체 (예: {"type": "number", "number": 42.5})

    Returns:
        숫자 값. 빈 값이면 0.0 반환.
    """
    if not prop or prop.get("type") != "number":
        return 0.0
    return prop.get("number", 0.0) or 0.0


def format_select(prop: dict[str, Any]) -> str:
    """
    Notion Select 속성을 문자열로 변환합니다.

    Args:
        prop: Notion select 속성 객체 (예: {"type": "select", "select": {"name": "GPT-4"}})

    Returns:
        선택된 옵션 이름. 빈 값이면 빈 문자열 반환.
    """
    if not prop or prop.get("type") != "select":
        return ""
    select_obj = prop.get("select")
    if not select_obj:
        return ""
    return select_obj.get("name", "")


def format_rich_text(prop: dict[str, Any]) -> str:
    """
    Notion Rich Text 속성을 일반 문자열로 변환합니다.

    Args:
        prop: Notion rich_text 속성 객체 (예: {"type": "rich_text", "rich_text": [{"plain_text": "..."}]})

    Returns:
        결합된 텍스트 문자열. 빈 값이면 빈 문자열 반환.
    """
    if not prop:
        return ""
    # rich_text 타입 또는 내부에 rich_text 배열이 있는 경우
    prop_type = prop.get("type", "")
    if prop_type == "rich_text":
        rich_parts = prop.get("rich_text", [])
    elif prop_type == "url":
        return prop.get("url", "") or ""
    elif prop_type == "email":
        return prop.get("email", "") or ""
    elif prop_type == "phone_number":
        return prop.get("phone_number", "") or ""
    else:
        return ""
    return "".join(part.get("plain_text", "") for part in rich_parts)


def format_relation(prop: dict[str, Any]) -> list[str]:
    """
    Notion Relation 속성을 관련 페이지 ID 리스트로 변환합니다.

    Args:
        prop: Notion relation 속성 객체 (예: {"type": "relation", "relation": [{"id": "..."}]})

    Returns:
        관련 페이지 ID 문자열 리스트. 빈 값이면 빈 리스트 반환.
    """
    if not prop or prop.get("type") != "relation":
        return []
    relations = prop.get("relation", [])
    return [rel.get("id", "") for rel in relations if rel.get("id")]


# ─── 속성 타입별 포맷터 매핑 ────────────────────────────────────────────────

_FORMATTERS: dict[str, Any] = {
    "title": format_title,
    "date": format_date,
    "number": format_number,
    "select": format_select,
    "multi_select": lambda p: [opt.get("name", "") for opt in (p.get("multi_select") or [])],
    "rich_text": format_rich_text,
    "url": lambda p: p.get("url", "") or "" if p else "",
    "email": lambda p: p.get("email", "") or "" if p else "",
    "phone_number": lambda p: p.get("phone_number", "") or "" if p else "",
    "checkbox": lambda p: p.get("checkbox", False) if p else False,
    "status": lambda p: (p.get("status") or {}).get("name", "") if p else "",
    "relation": format_relation,
    "formula": lambda p: _format_formula(p),
    "rollup": lambda p: _format_rollup(p),
    "people": lambda p: [person.get("name", "") for person in (p.get("people") or [])],
    "files": lambda p: [f.get("name", "") for f in (p.get("files") or [])],
    "created_time": lambda p: _format_datetime(p.get("created_time", "")),
    "last_edited_time": lambda p: _format_datetime(p.get("last_edited_time", "")),
}


def _format_formula(prop: dict[str, Any]) -> Any:
    """Notion Formula 속성을 처리합니다."""
    if not prop:
        return None
    formula = prop.get("formula", {})
    if "string" in formula:
        return formula["string"]
    if "number" in formula:
        return formula["number"]
    if "boolean" in formula:
        return formula["boolean"]
    if "date" in formula:
        start = formula["date"].get("start", "")
        if "T" in start:
            start = start.split("T")[0]
        return start
    return None


def _format_rollup(prop: dict[str, Any]) -> Any:
    """Notion Rollup 속성을 처리합니다."""
    if not prop:
        return None
    rollup = prop.get("rollup", {})
    rollup_type = rollup.get("type", "")
    if rollup_type == "number":
        return rollup.get("number", 0.0) or 0.0
    if rollup_type == "date":
        date_val = rollup.get("date", {})
        start = date_val.get("start", "")
        if "T" in start:
            start = start.split("T")[0]
        return start
    if rollup_type == "array":
        return rollup.get("array", [])
    if rollup_type == "select":
        sel = rollup.get("select")
        return sel.get("name", "") if sel else ""
    return None


def _format_datetime(dt_str: str) -> str:
    """ISO 8601 날짜시간 문자열에서 날짜 부분만 추출합니다."""
    if not dt_str:
        return ""
    if "T" in dt_str:
        return dt_str.split("T")[0]
    return dt_str


# ─── NotionClient 클래스 ───────────────────────────────────────────────────


class NotionClient:
    """
    Notion API 비동기 클라이언트

    httpx.AsyncClient를 사용하여 Notion 데이터베이스를 조회하고
    속성을 정규화된 Python 데이터로 변환합니다.

    사용 예:
        async with NotionClient("secret_xxx") as client:
            pages = await client.query_database("db_id_here")
            for page in pages:
                print(page["properties"]["Name"])
    """

    def __init__(self, api_key: str, base_url: str = NOTION_BASE_URL) -> None:
        """
        NotionClient를 초기화합니다.

        Args:
            api_key: Notion Integration API 키 (내부 통합 토큰)
            base_url: Notion API 베이스 URL (기본값: https://api.notion.com/v1/)
        """
        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None
        # httpx 클라이언트 공통 헤더 설정
        self._headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    # ── 비동기 컨텍스트 매니저 ──────────────────────────────────────────

    async def __aenter__(self) -> "NotionClient":
        """비동기 컨텍스트 진입 — httpx 클라이언트를 생성합니다."""
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=30.0,
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """비동기 컨텍스트 종료 — httpx 클라이언트를 정리합니다."""
        if self._client:
            await self._client.aclose()
            self._client = None

    # ── 내부 헬퍼 ─────────────────────────────────────────────────────

    def _ensure_client(self) -> httpx.AsyncClient:
        """클라이언트가 초기화되었는지 확인합니다."""
        if self._client is None:
            raise RuntimeError(
                "NotionClient가 초기화되지 않았습니다. "
                "'async with NotionClient(...) as client:' 형태로 사용하세요."
            )
        return self._client

    # ── 주요 API 메서드 ────────────────────────────────────────────────

    async def query_database(
        self,
        db_id: str,
        *,
        filter_cond: dict[str, Any] | None = None,
        sorts: list[dict[str, Any]] | None = None,
        start_cursor: str | None = None,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Notion 데이터베이스를 조회합니다. 자동 페이지네이션을 지원합니다.

        Args:
            db_id: 조회할 Notion 데이터베이스 ID
            filter_cond: Notion 필터 조건 (POST body의 filter 필드)
            sorts: 정렬 조건 리스트 (예: [{"property": "Date", "direction": "descending"}])
            start_cursor: 페이지네이션 커서 (다음 페이지 요청 시 사용)
            page_size: 한 페이지당 조회할 항목 수 (최대 100)

        Returns:
            정규화된 페이지 속성을 포함한 딕셔너리 리스트.
            각 항목은 {"id": "...", "properties": {...}, "created_time": "..."} 형태입니다.
        """
        client = self._ensure_client()
        all_results: list[dict[str, Any]] = []

        # 첫 번째 요청 body 구성
        body: dict[str, Any] = {"page_size": page_size}
        if filter_cond is not None:
            body["filter"] = filter_cond
        if sorts is not None:
            body["sorts"] = sorts
        if start_cursor is not None:
            body["start_cursor"] = start_cursor

        # 첫 번째 요청
        response = await client.post(f"/databases/{db_id}/query", json=body)
        response.raise_for_status()
        data = response.json()

        # 결과 정규화
        all_results.extend(self._normalize_pages(data.get("results", [])))

        # 자동 페이지네이션 — has_more가 true면 다음 페이지를 계속 조회
        while data.get("has_more", False):
            next_cursor = data.get("next_cursor")
            body["start_cursor"] = next_cursor
            response = await client.post(f"/databases/{db_id}/query", json=body)
            response.raise_for_status()
            data = response.json()
            all_results.extend(self._normalize_pages(data.get("results", [])))

        return all_results

    async def get_database_properties(self, db_id: str) -> dict[str, Any]:
        """
        Notion 데이터베이스의 메타데이터를 조회합니다.

        Args:
            db_id: Notion 데이터베이스 ID

        Returns:
            데이터베이스 속성 정보 딕셔너리.
            예: {"Name": {"type": "title", ...}, "Date": {"type": "date", ...}}
        """
        client = self._ensure_client()
        response = await client.get(f"/databases/{db_id}")
        response.raise_for_status()
        data = response.json()
        return data.get("properties", {})

    def format_property(self, prop: dict[str, Any]) -> Any:
        """
        Notion 속성 객체를 Python 기본 타입으로 정규화합니다.

        속성 타입을 자동 감지하여 적절한 포매터를 적용합니다.
        지원하지 않는 타입이면 원본 딕셔너리를 반환합니다.

        Args:
            prop: Notion 속성 객체 (예: {"type": "title", "title": [...]})

        Returns:
            정규화된 Python 값 (str, float, list, bool 등)
        """
        if not prop:
            return None
        prop_type = prop.get("type", "")
        formatter = _FORMATTERS.get(prop_type)
        if formatter:
            return formatter(prop)
        # 지원하지 않는 타입이면 원본 반환
        return prop

    # ── 내부 정규화 ────────────────────────────────────────────────────

    def _normalize_pages(self, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Notion 페이지 리스트를 정규화합니다.

        각 페이지의 properties를 format_property를 통해 변환합니다.

        Args:
            pages: Notion API 응답의 results 리스트

        Returns:
            정규화된 페이지 리스트
        """
        normalized: list[dict[str, Any]] = []
        for page in pages:
            props = page.get("properties", {})
            normalized_props: dict[str, Any] = {}
            for key, value in props.items():
                normalized_props[key] = self.format_property(value)
            normalized.append(
                {
                    "id": page.get("id", ""),
                    "properties": normalized_props,
                    "created_time": page.get("created_time", ""),
                    "last_edited_time": page.get("last_edited_time", ""),
                }
            )
        return normalized
