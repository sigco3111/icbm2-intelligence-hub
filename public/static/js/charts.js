/**
 * ICBM2 Intelligence Hub — Mobile Dashboard
 *
 * 모바일 최적화 대시보드: 6개 탭 섹션, 카드 레이아웃, Notion 데이터 표시.
 * 순수 HTML/CSS/JS, Chart.js 사용.
 */

// ─── 전역 상태 ──────────────────────────────────────────────────────────────
let performanceChartInstance = null;

// 각 섹션별 캐시
const sectionCache = {
    models: null,
    performance: null,
    ios: null,
    invest: null,
    learning: null,
    trending: null,
};

// 섹션별 API 설정
const SECTION_CONFIG = {
    models: {
        url: '/api/notion/ai-models',
        dataKey: 'models',
    },
    performance: {
        url: '/api/notion/performance',
        dataKey: 'performance',
    },
    ios: {
        url: '/api/notion/ios-trends',
        dataKey: 'ios_trends',
    },
    invest: {
        url: '/api/notion/invest',
        dataKey: 'invest',
    },
    learning: {
        url: '/api/notion/learning',
        dataKey: 'learning',
    },
    trending: {
        url: '/api/trending/daily',
        dataKey: 'repos',
    },
};

// 섹션별 ID 매핑
const SECTION_IDS = {
    models:      { loading: 'modelsLoading',    content: 'modelsContent',    error: 'modelsError' },
    performance: { loading: 'chartLoading',     content: 'chartContent',     error: 'chartError' },
    ios:         { loading: 'iosLoading',       content: 'iosContent',       error: 'iosError' },
    invest:      { loading: 'investLoading',    content: 'investContent',    error: 'investError' },
    learning:    { loading: 'learningLoading',  content: 'learningContent',  error: 'learningError' },
    trending:    { loading: 'trendingLoading',  content: 'trendingContent',  error: 'trendingError' },
};

// ─── 초기화 ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    loadAllSections();
    updateTimestamp();
});

// ─── 탭 네비게이션 ──────────────────────────────────────────────────────────
function initTabs() {
    const nav = document.getElementById('tabNav');
    nav.addEventListener('click', (e) => {
        const btn = e.target.closest('.tab-btn');
        if (!btn) return;

        const tab = btn.dataset.tab;
        switchTab(tab);
    });
}

function switchTab(tab) {
    // 버튼 active 상태
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    const activeBtn = document.querySelector(`.tab-btn[data-tab="${tab}"]`);
    if (activeBtn) activeBtn.classList.add('active');

    // 패널 표시
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    const panel = document.getElementById(`panel-${tab}`);
    if (panel) panel.classList.add('active');

    // 해당 섹션 데이터 로드 (캐시 없으면)
    if (!sectionCache[tab]) {
        loadSection(tab);
    }
}

// ─── 데이터 로딩 ────────────────────────────────────────────────────────────
async function loadAllSections() {
    const promises = Object.keys(SECTION_CONFIG).map(key => loadSection(key));
    await Promise.allSettled(promises);
}

async function loadSection(sectionKey) {
    const config = SECTION_CONFIG[sectionKey];
    const ids = SECTION_IDS[sectionKey];
    if (!config || !ids) return;

    showLoading(ids.loading, ids.content, ids.error);

    try {
        const res = await fetch(config.url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        sectionCache[sectionKey] = data;
        renderSection(sectionKey, data);
        showContent(ids.content, ids.loading, ids.error);
    } catch (err) {
        console.error(`${sectionKey} API 오류:`, err);
        showError(ids.error, ids.loading, ids.content);
    }
}

function retrySection(sectionKey) {
    sectionCache[sectionKey] = null;
    loadSection(sectionKey);
}

// ─── 섹션 렌더링 디스패치 ──────────────────────────────────────────────────
function renderSection(sectionKey, data) {
    switch (sectionKey) {
        case 'models':      renderModels(data); break;
        case 'performance': renderPerformanceChart(data); break;
        case 'ios':         renderIosTrends(data); break;
        case 'invest':      renderInvest(data); break;
        case 'learning':    renderLearning(data); break;
        case 'trending':    renderTrending(data); break;
    }
}

// ─── UI 상태 전환 헬퍼 ─────────────────────────────────────────────────────
function showLoading(loadingId, contentId, errorId) {
    const el = (id) => document.getElementById(id);
    if (el(loadingId)) el(loadingId).style.display = '';
    if (el(contentId)) el(contentId).style.display = 'none';
    if (el(errorId)) el(errorId).style.display = 'none';
}

function showContent(contentId, loadingId, errorId) {
    const el = (id) => document.getElementById(id);
    if (el(loadingId)) el(loadingId).style.display = 'none';
    if (el(contentId)) el(contentId).style.display = '';
    if (el(errorId)) el(errorId).style.display = 'none';
}

function showError(errorId, loadingId, contentId) {
    const el = (id) => document.getElementById(id);
    if (el(loadingId)) el(loadingId).style.display = 'none';
    if (el(contentId)) el(contentId).style.display = 'none';
    if (el(errorId)) el(errorId).style.display = '';
}

// ═════════════════════════════════════════════════════════════════════════════
// 섹션별 렌더링
// ═════════════════════════════════════════════════════════════════════════════

// ─── 1. AI 모델 트래커 ─────────────────────────────────────────────────────
function renderModels(data) {
    const models = data.models || [];
    const container = document.getElementById('modelsContent');

    if (models.length === 0) {
        container.innerHTML = emptyStateHtml('📭', '아직 AI 모델 데이터가 없습니다');
        return;
    }

    // 속성 키 분석
    const sampleProps = models[0].properties || {};
    const keys = Object.keys(sampleProps).filter(
        k => !['id', 'created_time', 'last_edited_time', 'object', 'cover', 'icon'].includes(k)
    );

    // 카드에 표시할 속성: title → 첫 번째 텍스트 필드, 그 다음 3개
    const titleKey = keys.find(k => {
        const v = sampleProps[k];
        // Notion title 객체
        if (v && typeof v === 'object' && v.title) return true;
        // 스칼라 문자열 (긴 텍스트 = 제목일 확률 높음)
        if (typeof v === 'string' && v.length > 10) return true;
        return false;
    }) || keys[0];

    const metaKeys = keys.filter(k => k !== titleKey).slice(0, 3);
    const descKey = keys.find(k => {
        const v = sampleProps[k];
        if (v && typeof v === 'object' && (v.rich_text || (v.title && k !== titleKey))) return true;
        // 스칼라 문자열 (URL은 제외)
        if (typeof v === 'string' && v.length > 20 && !v.startsWith('http')) return true;
        return false;
    });

    container.innerHTML = models.map(model => {
        const props = model.properties || {};
        const title = extractNotionValue(props[titleKey]) || '제목 없음';
        const url = extractNotionUrl(props);
        const tags = metaKeys.map(k => {
            const label = getShortLabel(k);
            const val = extractNotionValue(props[k]);
            if (!val) return '';
            return `<span class="data-card-tag">${escapeHtml(label)} ${escapeHtml(val)}</span>`;
        }).filter(Boolean).join('');

        let descHtml = '';
        if (descKey && descKey !== titleKey) {
            const desc = extractNotionValue(props[descKey]);
            if (desc) {
                descHtml = `<div class="data-card-desc">${escapeHtml(desc)}</div>`;
            }
        }

        const cardInner = `
            <div class="data-card-title">${escapeHtml(title)}${url ? ' <span class="data-card-link-icon">↗</span>' : ''}</div>
            ${tags ? `<div class="data-card-meta">${tags}</div>` : ''}
            ${descHtml}
        `;

        if (url) {
            return `<a href="${escapeHtml(url)}" target="_blank" rel="noopener" class="data-card data-card--link">${cardInner}</a>`;
        }
        return `<div class="data-card">${cardInner}</div>`;
    }).join('');
}

// ─── 2. 성과 대시보드 (Chart.js) ───────────────────────────────────────────
function renderPerformanceChart(data) {
    const items = data.performance || [];
    const container = document.getElementById('chartContent');

    if (items.length === 0) {
        container.innerHTML = `<div class="chart-card">${emptyStateHtml('📭', '아직 성과 데이터가 없습니다')}</div>`;
        return;
    }

    // Notion property 처리
    const dateMap = new Map();
    const categorySet = new Set();

    for (const item of items) {
        const props = item.properties || item;
        const rawDate = extractNotionDate(props);
        const rawValue = extractNotionNumber(props);
        const category = extractNotionCategory(props);

        if (!rawDate || rawValue === null) continue;

        const dateStr = formatDateLabel(rawDate);
        if (!dateStr) continue;

        categorySet.add(category);
        if (!dateMap.has(dateStr)) dateMap.set(dateStr, {});
        const dm = dateMap.get(dateStr);
        dm[category] = (dm[category] || 0) + rawValue;
    }

    const dates = [...dateMap.keys()];
    const categories = [...categorySet];

    const colorPalette = [
        '#3b82f6', '#10b981', '#f59e0b', '#ef4444',
        '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'
    ];

    const datasets = categories.map((cat, i) => ({
        label: cat,
        data: dates.map(d => dateMap.get(d)[cat] || 0),
        backgroundColor: colorPalette[i % colorPalette.length] + 'cc',
        borderColor: colorPalette[i % colorPalette.length],
        borderWidth: 1,
        borderRadius: 6,
    }));

    // 차트 캔버스 보장
    if (!document.getElementById('performanceChart')) {
        container.innerHTML = `<div class="chart-container"><canvas id="performanceChart"></canvas></div>`;
    }

    const canvas = document.getElementById('performanceChart');
    const ctx = canvas.getContext('2d');

    if (performanceChartInstance) {
        performanceChartInstance.destroy();
    }

    performanceChartInstance = new Chart(ctx, {
        type: 'bar',
        data: { labels: dates, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#94a3b8',
                        font: { size: 11 },
                        padding: 12,
                        usePointStyle: true,
                        pointStyleWidth: 10,
                    },
                },
                tooltip: {
                    backgroundColor: '#1a1d2e',
                    titleColor: '#e2e8f0',
                    bodyColor: '#94a3b8',
                    borderColor: '#2d3748',
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 10,
                },
            },
            scales: {
                x: {
                    grid: { color: 'rgba(45, 55, 72, 0.5)' },
                    ticks: { color: '#64748b', font: { size: 10 } },
                },
                y: {
                    grid: { color: 'rgba(45, 55, 72, 0.5)' },
                    ticks: { color: '#64748b', font: { size: 10 } },
                    beginAtZero: true,
                },
            },
        },
    });
}

// ─── 3. iOS 트렌드 ──────────────────────────────────────────────────────────
function renderIosTrends(data) {
    const items = data.ios_trends || [];
    const container = document.getElementById('iosContent');

    if (items.length === 0) {
        container.innerHTML = emptyStateHtml('📭', '아직 iOS 트렌드 데이터가 없습니다');
        return;
    }

    container.innerHTML = items.map(item => createNotionCard(item, {
        titleKeys: ['이름', 'Name', 'name', '제목', 'Title', 'title'],
        metaKeys: ['카테고리', 'Category', 'category', '상태', 'Status', 'status', '버전', 'Version', 'version'],
        descKeys: ['설명', 'Description', 'description', '메모', 'Note', 'note', '내용', '내용'],
        dateKeys: ['날짜', 'Date', 'date'],
    })).join('');
}

// ─── 4. 투자 메모 ───────────────────────────────────────────────────────────
function renderInvest(data) {
    const items = data.invest || [];
    const container = document.getElementById('investContent');

    if (items.length === 0) {
        container.innerHTML = emptyStateHtml('📭', '아직 투자 메모가 없습니다');
        return;
    }

    container.innerHTML = items.map(item => createNotionCard(item, {
        titleKeys: ['이름', 'Name', 'name', '제목', 'Title', 'title', '종목', 'Ticker'],
        metaKeys: ['카테고리', 'Category', 'category', '상태', 'Status', 'status', '유형', 'Type', 'type', '가격', 'Price', 'price'],
        descKeys: ['설명', 'Description', 'description', '메모', 'Note', 'note', '내용', '의견', 'Comment'],
        dateKeys: ['날짜', 'Date', 'date', '매수일', 'Buy Date'],
    })).join('');
}

// ─── 5. 학습 로그 ───────────────────────────────────────────────────────────
function renderLearning(data) {
    const items = data.learning || [];
    const container = document.getElementById('learningContent');

    if (items.length === 0) {
        container.innerHTML = emptyStateHtml('📭', '아직 학습 로그가 없습니다');
        return;
    }

    container.innerHTML = items.map(item => createNotionCard(item, {
        titleKeys: ['이름', 'Name', 'name', '제목', 'Title', 'title', '주제', 'Topic', 'topic'],
        metaKeys: ['카테고리', 'Category', 'category', '상태', 'Status', 'status', '난이도', 'Level', 'level', '진행도', 'Progress'],
        descKeys: ['설명', 'Description', 'description', '메모', 'Note', 'note', '내용', '요약', 'Summary'],
        dateKeys: ['날짜', 'Date', 'date', '학습일', 'Start Date'],
    })).join('');
}

// ─── 6. GitHub 트렌딩 ───────────────────────────────────────────────────────
function renderTrending(data) {
    const repos = data.repos || [];
    const container = document.getElementById('trendingContent');

    if (repos.length === 0) {
        container.innerHTML = emptyStateHtml('📭', '오늘의 트렌딩 리포지토리가 없습니다');
        return;
    }

    container.innerHTML = repos.map(repo => createRepoCardHtml(repo)).join('');
}

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

// ═════════════════════════════════════════════════════════════════════════════
// Notion 데이터 처리 헬퍼
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Notion properties에서 URL 추출
 */
function extractNotionUrl(props) {
    // URL 키를 직접 찾기
    const urlKeyCandidates = ['URL', 'url', 'Url', '링크', 'Link', 'link'];
    for (const k of Object.keys(props)) {
        const v = props[k];
        if (v === null || v === undefined) continue;
        const kLower = k.toLowerCase();
        if (urlKeyCandidates.some(c => c.toLowerCase() === kLower)) {
            // 스칼라 문자열 URL
            if (typeof v === 'string' && v.startsWith('http')) return v;
            // Notion url property
            if (typeof v === 'object' && v.url) return v.url;
        }
    }
    return null;
}

/**
 * 범용 Notion 카드 생성
 * URL이 있으면 카드 전체를 클릭 가능한 링크로 만듭니다.
 * @param {Object} item - Notion page object {id, properties}
 * @param {Object} opts - {titleKeys, metaKeys, descKeys, dateKeys}
 */
function createNotionCard(item, opts) {
    const props = item.properties || {};

    // 키 매칭
    const allKeys = Object.keys(props);
    const titleKey = findFirstKey(allKeys, opts.titleKeys);
    const metaKeyList = findKeys(allKeys, opts.metaKeys, 3);
    const descKey = findFirstKey(allKeys, opts.descKeys);
    const dateKey = findFirstKey(allKeys, opts.dateKeys);

    const title = extractNotionValue(props[titleKey]) || '제목 없음';

    // URL 추출
    const url = extractNotionUrl(props);

    // 메타 태그 생성
    const tags = [];
    // 날짜 추출: dateKey가 있으면 해당 값에서, 아니면 extractNotionDate로
    if (dateKey) {
        const rawVal = props[dateKey];
        let dateStr = '';
        if (typeof rawVal === 'string' && rawVal) {
            dateStr = formatDateLabel(rawVal);
        } else if (rawVal && typeof rawVal === 'object' && rawVal.date && rawVal.date.start) {
            dateStr = formatDateLabel(rawVal.date.start);
        }
        if (!dateStr) {
            const fallback = extractNotionDate(props);
            dateStr = formatDateLabel(fallback);
        }
        if (dateStr) {
            tags.push(`<span class="data-card-tag tag-accent">📅 ${escapeHtml(dateStr)}</span>`);
        }
    }
    for (const k of metaKeyList) {
        const val = extractNotionValue(props[k]);
        if (!val) continue;
        const label = getShortLabel(k);
        const tagClass = getTagClass(k, val);
        tags.push(`<span class="data-card-tag ${tagClass}">${escapeHtml(label)} ${escapeHtml(val)}</span>`);
    }

    // 설명
    let descHtml = '';
    if (descKey) {
        const desc = extractNotionValue(props[descKey]);
        if (desc) {
            descHtml = `<div class="data-card-desc">${escapeHtml(desc)}</div>`;
        }
    }

    // 카드 내용
    const cardInner = `
        <div class="data-card-title">${escapeHtml(title)}${url ? ' <span class="data-card-link-icon">↗</span>' : ''}</div>
        ${tags.length ? `<div class="data-card-meta">${tags.join('')}</div>` : ''}
        ${descHtml}
    `;

    if (url) {
        return `<a href="${escapeHtml(url)}" target="_blank" rel="noopener" class="data-card data-card--link">${cardInner}</a>`;
    }
    return `<div class="data-card">${cardInner}</div>`;
}

// ─── Notion 값 추출 헬퍼 ───────────────────────────────────────────────────
function extractNotionValue(val) {
    if (val === null || val === undefined) return '';

    // 스칼라 값
    if (typeof val === 'string' || typeof val === 'number') return String(val);

    // Notion property 객체
    if (typeof val === 'object') {
        if (val.title) {
            return (Array.isArray(val.title) ? val.title : [val.title])
                .map(t => t.plain_text || t.text?.content || '')
                .join('');
        }
        if (val.rich_text) {
            return (Array.isArray(val.rich_text) ? val.rich_text : [val.rich_text])
                .map(t => t.plain_text || t.text?.content || '')
                .join('');
        }
        if (val.select) return val.select.name || '';
        if (val.multi_select) {
            return (val.multi_select || []).map(s => s.name || '').join(', ');
        }
        if (val.number !== undefined) return String(val.number);
        if (val.checkbox !== undefined) return val.checkbox ? '✅' : '❌';
        if (val.date) return val.date.start || '';
        if (val.url) return val.url;
        if (val.email) return val.email;
        if (val.phone_number) return val.phone_number;
        if (val.status) return val.status.name || '';
        if (val.formula) return extractNotionValue(val.formula);
        if (val.rollup) return extractNotionValue(val.rollup);
    }

    return String(val);
}

/**
 * Notion properties에서 날짜값 추출
 * 스칼라 문자열("2026-04-08") 또는 Notion date 객체({date:{start:"..."}}) 모두 지원
 */
function extractNotionDate(props) {
    // 날짜 키를 우선 찾기
    const dateKeyCandidates = ['날짜', 'Date', 'date', '일자', '날짜'];
    for (const k of Object.keys(props)) {
        const v = props[k];
        if (v === null || v === undefined) continue;
        // Notion date 객체
        if (typeof v === 'object' && v.date && v.date.start) {
            return v.date.start;
        }
        // 스칼라 문자열 날짜 (YYYY-MM-DD 형식)
        if (typeof v === 'string' && /^\d{4}-\d{2}-\d{2}/.test(v)) {
            return v;
        }
    }
    return null;
}

/**
 * Notion properties에서 숫자값 추출
 * 스칼라 숫자 또는 Notion number 객체 모두 지원
 * 키 이름으로 의미 있는 숫자 필드를 우선 찾기
 */
function extractNotionNumber(props) {
    const numKeyCandidates = ['값', 'Value', 'value', '수치', '점수', 'Score', 'score'];
    for (const k of Object.keys(props)) {
        const v = props[k];
        if (v === null || v === undefined) continue;
        // 키 이름 매칭 우선
        const kLower = k.toLowerCase();
        if (numKeyCandidates.some(c => c.toLowerCase() === kLower)) {
            if (typeof v === 'number') return v;
            if (typeof v === 'object' && v.number !== undefined) return v.number;
        }
    }
    // 키 매칭 실패 시, 첫 번째 숫자 필드 반환
    for (const k of Object.keys(props)) {
        const v = props[k];
        if (v === null || v === undefined) continue;
        if (typeof v === 'number') return v;
        if (typeof v === 'object' && v.number !== undefined) return v.number;
    }
    return null;
}

/**
 * Notion properties에서 카테고리(select/multi_select/string) 추출
 */
function extractNotionCategory(props) {
    const catKeyCandidates = ['카테고리', 'Category', 'category', '유형', 'Type', 'type'];
    for (const k of Object.keys(props)) {
        const v = props[k];
        if (v === null || v === undefined) continue;
        const kLower = k.toLowerCase();
        if (catKeyCandidates.some(c => c.toLowerCase() === kLower)) {
            if (typeof v === 'object') {
                if (v.select && v.select.name) return v.select.name;
                if (v.multi_select && v.multi_select.length > 0) return v.multi_select[0].name;
            }
            if (typeof v === 'string' && v.trim()) return v.trim();
        }
    }
    // 키 매칭 실패 시 select/multi_select 객체 찾기
    for (const k of Object.keys(props)) {
        const v = props[k];
        if (v && typeof v === 'object') {
            if (v.select && v.select.name) return v.select.name;
            if (v.multi_select && v.multi_select.length > 0) return v.multi_select[0].name;
        }
    }
    return '기타';
}

// ─── 키 매칭 헬퍼 ─────────────────────────────────────────────────────────
/**
 * candidates 중 allKeys에 존재하는 첫 번째 키 반환
 */
function findFirstKey(allKeys, candidates) {
    for (const c of candidates) {
        const found = allKeys.find(k => k.toLowerCase() === c.toLowerCase());
        if (found) return found;
    }
    return allKeys[0] || null;
}

/**
 * candidates 중 allKeys에 존재하는 키를 최대 maxCount개 반환
 */
function findKeys(allKeys, candidates, maxCount) {
    const result = [];
    for (const c of candidates) {
        if (result.length >= maxCount) break;
        const found = allKeys.find(k => k.toLowerCase() === c.toLowerCase());
        if (found) result.push(found);
    }
    return result;
}

// ─── 레이블 / 스타일 헬퍼 ──────────────────────────────────────────────────
function getShortLabel(key) {
    const labels = {
        '카테고리': '카테고리', 'Category': '카테고리', 'category': '카테고리',
        '상태': '상태', 'Status': '상태', 'status': '상태',
        '유형': '유형', 'Type': '유형', 'type': '유형',
        '버전': '버전', 'Version': '버전', 'version': '버전',
        '가격': '가격', 'Price': '가격', 'price': '가격',
        '난이도': '난이도', 'Level': '난이도', 'level': '난이도',
        '진행도': '진행도', 'Progress': '진행도', 'progress': '진행도',
        '종목': '종목', 'Ticker': '종목', 'ticker': '종목',
    };
    return labels[key] || key;
}

function getTagClass(key, val) {
    const lower = (val || '').toLowerCase();
    if (lower === '완료' || lower === 'done' || lower === 'completed' || lower === '✅') return 'tag-success';
    if (lower === '진행중' || lower === 'in progress' || lower === 'active') return 'tag-accent';
    if (lower === '중요' || lower === 'important' || lower === 'urgent') return 'tag-danger';
    if (lower === '보류' || lower === 'hold' || lower === 'pending') return 'tag-warning';
    return '';
}

// ─── 날짜 포맷 ─────────────────────────────────────────────────────────────
function formatDateLabel(dateStr) {
    if (!dateStr) return '';
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        const month = d.getMonth() + 1;
        const day = d.getDate();
        return `${String(month).padStart(2, '0')}/${String(day).padStart(2, '0')}`;
    } catch {
        return dateStr;
    }
}

// ─── 빈 상태 HTML ──────────────────────────────────────────────────────────
function emptyStateHtml(icon, message) {
    return `
        <div class="empty-state">
            <div class="empty-icon">${icon}</div>
            <div class="empty-message">${escapeHtml(message)}</div>
        </div>
    `;
}

// ─── 타임스탬프 ─────────────────────────────────────────────────────────────
function updateTimestamp() {
    const el = document.getElementById('lastUpdated');
    if (!el) return;
    const now = new Date();
    const h = String(now.getHours()).padStart(2, '0');
    const m = String(now.getMinutes()).padStart(2, '0');
    el.textContent = `업데이트 ${h}:${m}`;
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
