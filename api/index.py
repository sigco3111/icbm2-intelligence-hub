# Vercel에서 FastAPI를 서버리스로 실행하기 위한 래퍼
# 주의: Vercel Python 런타임에서는 aiosqlite가 작동하지 않을 수 있음
# DataStore를 메모리/임시 DB로 폴백하도록 처리

import sys
sys.path.insert(0, '.')

# Vercel 환경에서 data_store 경로를 /tmp로 변경
import os
os.environ.setdefault("DB_PATH", "/tmp/cache.db")

# 환경변수에서 설정 로드 (Vercel 환경변수)
# notion_api_key, github_token, tistory_access_token 등은
# Vercel 대시보드에서 설정 필요

from backend.main import app

# Vercel은 이 모듈을 WSGI/ASGI 앱으로 인식함
