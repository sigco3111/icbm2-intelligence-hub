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
