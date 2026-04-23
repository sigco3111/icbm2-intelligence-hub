# 🚀 ICBM2 Intelligence Hub

Notion 데이터 시각화 + GitHub Trending 기술 뉴스 요약이 통합된 모바일 우선 웹 대시보드

**라이브:** [icbm2-hub.vercel.app](https://icbm2-hub.vercel.app)

## ✨ 기능

| 탭 | 설명 | 데이터 소스 |
|---|---|---|
| 🤖 AI 모델 | AI 모델 릴리즈/업데이트 트래커 | Notion DB |
| 📱 iOS | iOS/Swift 기술 트렌드 | Notion DB |
| 📚 학습 | 주간 학습 로그 | Notion DB |
| 🔥 GitHub | GitHub 트렌딩 (AI/iOS 필터링) | GitHub API |

## 🛠 기술 스택

- **Backend:** Python 3.11 + FastAPI (Vercel Serverless)
- **Frontend:** HTML/CSS/JS (모바일 우선 다크 테마) + Chart.js
- **Database:** SQLite (aiosqlite, 1시간 캐시)
- **API:** Notion API, GitHub API
- **배포:** Vercel (Python 런타임)

## 📁 구조

```
icbm2-intelligence-hub/
├── api/
│   └── index.py              # Vercel 서버리스 진입점
├── backend/
│   ├── main.py               # FastAPI 앱 (CORS, 정적 파일, healthcheck)
│   ├── config.py             # 설정 (Pydantic Settings)
│   ├── notion_client.py      # Notion API 연동
│   ├── github_crawler.py     # GitHub Trending 크롤러
│   ├── data_store.py         # SQLite 캐시 저장/조회
│   ├── tistory_publisher.py  # Tistory 자동 발행
│   ├── scheduler.py          # 크론 스케줄러
│   └── routers/
│       ├── notion.py          # /api/notion/* 엔드포인트
│       └── trending.py        # /api/trending/* 엔드포인트
├── public/                    # 정적 파일 (Vercel 서빙)
│   ├── index.html             # 메인 대시보드 (SPA 탭 네비게이션)
│   ├── static/
│   │   ├── css/style.css      # 모바일 우선 다크 테마 스타일
│   │   ├── js/charts.js       # 차트 + 데이터 페칭 로직
│   │   └── js/news.js         # 뉴스 피드 로직
│   │   └── news.html          # 뉴스 페이지
│   └── ...
├── vercel.json                # Vercel 라우팅 설정
├── requirements.txt           # Python 의존성
└── README.md
```

## 🔌 API 엔드포인트

| 엔드포인트 | 설명 |
|---|---|
| `GET /api/notion/models` | AI 모델 트래커 데이터 |
| `GET /api/notion/ios` | iOS 트렌드 데이터 |
| `GET /api/notion/learning` | 학습 로그 데이터 |
| `GET /api/trending` | GitHub 트렌딩 (AI/iOS 필터) |
| `GET /api/trending/history` | 트렌딩 히스토리 |
| `GET /health` | 헬스체크 |

## 🚀 로컬 개발

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env

# 서버 실행
uvicorn backend.main:app --reload --port 8000
```

## 📦 배포

Vercel에 연동되어 자동 배포됩니다. `main` 브랜치에 push하면 반영됩니다.
