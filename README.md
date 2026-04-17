# ICBM2 Intelligence Hub

Notion 데이터 시각화 + GitHub Trending 기술 뉴스 요약이 통합된 웹 대시보드

## 기능
- 📊 Notion 데이터 시각화 (AI 모델 트래커, 성과, 학습 로그)
- 📰 GitHub Trending 크롤링 + AI/iOS 필터링 요약
- 📝 Tistory 자동 발행 (주간 요약 뉴스레터)
- ⏰ 크론 기반 자동 업데이트

## 기술 스택
- Backend: Python 3.11 + FastAPI
- Frontend: HTML/CSS/JS + Chart.js
- Database: SQLite (간단한 캐시)
- API: Notion API, GitHub API, Tistory API

## 구조
```
icbm2-intelligence-hub/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # 설정 (Notion DB IDs, API keys)
│   ├── notion_client.py     # Notion API 연동
│   ├── github_crawler.py    # GitHub Trending 크롤러
│   ├── data_store.py        # SQLite 데이터 저장/조회
│   ├── tistory_publisher.py # Tistory 발행
│   └── scheduler.py         # 크론 스케줄러
├── frontend/
│   ├── index.html           # 메인 대시보드
│   ├── news.html            # 뉴스 피드
│   ├── css/style.css        # 스타일
│   └── js/
│       ├── charts.js        # Chart.js 차트
│       └── news.js          # 뉴스 피드 로직
├── tests/
│   ├── test_notion.py
│   ├── test_github.py
│   └── test_api.py
├── CLAUDE.md
├── requirements.txt
└── README.md
```
