# Vercel에서 FastAPI를 서버리스로 실행하기 위한 래퍼
# Vercel Python 런타임은 이 모듈에서 `app` 변수를 ASGI 앱으로 인식함

import os
import sys

# ─── Vercel 서버리스 환경 변수 설정 ─────────────────────────────────────────
# DB_PATH: Vercel은 /tmp만 쓰기 가능하므로 기본값을 /tmp로 설정
# 다른 환경변수(NOTION_API_KEY 등)는 Vercel 대시보드에서 설정
os.environ.setdefault("DB_PATH", "/tmp/cache.db")

# ─── 모듈 임포트 경로 설정 ───────────────────────────────────────────────────
# Vercel 빌드 시 프로젝트 루트를 Python path에 추가
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# ─── FastAPI 앱 임포트 및 Vercel에 노출 ─────────────────────────────────────
# Vercel은 이 모듈의 `app` 변수를 ASGI 앱으로 사용함
from backend.main import app  # noqa: E402
