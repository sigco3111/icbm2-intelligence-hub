# Vercel 서버리스 진입점
# Vercel Python 런타임이 이 모듈의 `app` 변수를 ASGI 앱으로 사용합니다

import os
import sys

# ─── Vercel 환경 설정 ─────────────────────────────────────────────
# Vercel 서버리스는 /tmp만 쓰기 가능
os.environ.setdefault("DB_PATH", "/tmp/icbm2_hub_cache.db")

# 프로젝트 루트를 Python path에 추가 (backend 패키지 import용)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# ─── FastAPI 앱 임포트 ────────────────────────────────────────────
from backend.main import app  # noqa: E402

# ─── 디버그 엔드포인트 (배포 후 제거) ──────────────────────────────
@app.get("/api/debug")
async def debug_env():
    """환경변수 디버그 — 배포 확인 후 삭제"""
    from backend.config import settings
    return {
        "notion_api_key": settings.notion_api_key[:10] + "..." if settings.notion_api_key else "EMPTY",
        "notion_key_len": len(settings.notion_api_key),
        "notion_key_has_newline": "\\n" in settings.notion_api_key,
        "github_token": settings.github_token[:10] + "..." if settings.github_token else "EMPTY",
        "ai_model_db": settings.notion_ai_model_db or "EMPTY",
        "db_path": settings.db_path,
        "env_keys": [k for k in os.environ if "NOTION" in k or "GITHUB" in k or "DB_PATH" in k],
    }
