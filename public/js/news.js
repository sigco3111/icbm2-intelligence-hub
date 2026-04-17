/**
 * ICBM2 Intelligence Hub — News Feed
 *
 * 뉴스 피드 페이지의 트렌딩 리포지토리 로딩, 카드 렌더링,
 * 기간 토글 및 키워드 필터링을 담당합니다.
 */

// ─── 전역 상태 ──────────────────────────────────────────────────────────────
let currentPeriod = 'daily';
let allRepos = [];
let currentFilter = '';

// ─── 초기화 ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadTrending();
});

// ─── 트렌딩 데이터 로딩 ─────────────────────────────────────────────────────
async function loadTrending() {
    showState('newsLoading', 'newsContainer', 'newsEmpty', 'newsError');

    try {
        const repos = await fetchTrending(currentPeriod);
        allRepos = repos;
        renderNewsCards(allRepos);
        showState(null, 'newsContainer', null, null);
    } catch (e) {
        console.error('트렌딩 로딩 오류:', e);
        showState(null, null, null, 'newsError');
    }
}

// ─── API 호출 ───────────────────────────────────────────────────────────────
async function fetchTrending(period) {
    const url = `/api/trending/${period}`;
    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return data.repos || [];
}

// ─── 기간 토글 ──────────────────────────────────────────────────────────────
function switchPeriod(period, btn) {
    if (period === currentPeriod) return;

    currentPeriod = period;

    // 버튼 활성 상태 업데이트
    document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    // 데이터 재로딩
    loadTrending();
}

// ─── 키워드 필터 ────────────────────────────────────────────────────────────
function filterCards(keyword, btn) {
    currentFilter = keyword;

    // 버튼 활성 상태 업데이트
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');

    filterByKeyword(keyword);
}

function filterByKeyword(keyword) {
    const grid = document.getElementById('newsGrid');

    if (!keyword || keyword === '') {
        // 전체 표시
        renderNewsCards(allRepos);
        return;
    }

    const lowerKeyword = keyword.toLowerCase();
    const filtered = allRepos.filter(repo => {
        const name = (repo.name || '').toLowerCase();
        const desc = (repo.description || '').toLowerCase();
        const lang = (repo.language || '').toLowerCase();
        return name.includes(lowerKeyword) ||
               desc.includes(lowerKeyword) ||
               lang.includes(lowerKeyword);
    });

    renderNewsCards(filtered);
}

// ─── 카드 렌더링 ────────────────────────────────────────────────────────────
function renderNewsCards(repos) {
    const grid = document.getElementById('newsGrid');

    if (!repos || repos.length === 0) {
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
                <div class="icon">📭</div>
                <div class="message">해당 조건에 맞는 리포지토리가 없습니다</div>
            </div>
        `;
        document.getElementById('newsContainer').style.display = '';
        return;
    }

    grid.innerHTML = repos.map(repo => createRepoCardHtml(repo)).join('');
    document.getElementById('newsContainer').style.display = '';
}

// ─── 리포지토리 카드 HTML 생성 ──────────────────────────────────────────────
function createRepoCardHtml(repo) {
    const name = repo.name || '';
    const description = repo.description || '설명 없음';
    const language = repo.language || '';
    const stars = formatNumber(repo.stars || 0);
    const forks = formatNumber(repo.forks || 0);
    const todayStars = repo.today_stars || 0;

    const langClass = getLanguageClass(language);
    const repoUrl = `https://github.com/${name}`;

    return `
        <div class="repo-card">
            <div class="repo-card-header">
                <a href="${repoUrl}" target="_blank" rel="noopener" class="repo-name">
                    ${escapeHtml(name)}
                </a>
                ${todayStars > 0 ? `<span class="today-stars">⭐ ${todayStars}</span>` : ''}
            </div>
            <div class="repo-description">${escapeHtml(description)}</div>
            <div class="repo-meta">
                ${language ? `
                    <span class="repo-meta-item">
                        <span class="dot ${langClass}"></span>
                        ${escapeHtml(language)}
                    </span>
                ` : ''}
                <span class="repo-meta-item">⭐ ${stars}</span>
                <span class="repo-meta-item">🍴 ${forks}</span>
            </div>
        </div>
    `;
}

// ─── UI 상태 전환 헬퍼 ─────────────────────────────────────────────────────
function showState(loadingId, contentId, emptyId, errorId) {
    ['newsLoading', 'newsContainer', 'newsEmpty', 'newsError'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });

    if (loadingId) {
        const el = document.getElementById(loadingId);
        if (el) el.style.display = '';
    }
    if (contentId) {
        const el = document.getElementById(contentId);
        if (el) el.style.display = '';
    }
    if (emptyId) {
        const el = document.getElementById(emptyId);
        if (el) el.style.display = '';
    }
    if (errorId) {
        const el = document.getElementById(errorId);
        if (el) el.style.display = '';
    }
}

// ─── 유틸리티 ──────────────────────────────────────────────────────────────
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatNumber(num) {
    if (num >= 1000) return (num / 1000).toFixed(1).replace(/\.0$/, '') + 'k';
    return String(num);
}

function getLanguageClass(lang) {
    const mapping = {
        'Python': 'lang-python',
        'JavaScript': 'lang-javascript',
        'TypeScript': 'lang-typescript',
        'Swift': 'lang-swift',
        'Rust': 'lang-rust',
        'Go': 'lang-go',
        'C++': 'lang-cpp',
    };
    return mapping[lang] || 'lang-default';
}
