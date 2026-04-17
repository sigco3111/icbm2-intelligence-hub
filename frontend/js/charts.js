/**
 * ICBM2 Intelligence Hub — Dashboard Charts & Data
 *
 * 대시보드 메인 페이지의 데이터 로딩, 차트 렌더링, 테이블 생성을 담당합니다.
 * 3개 API 엔드포인트를 병렬로 호출하고 각 영역에 렌더링합니다.
 */

// ─── 전역 상태 ──────────────────────────────────────────────────────────────
let performanceChartInstance = null;
let allTrendingRepos = [];

// ─── 초기화 ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    fetchDashboardData();
});

// ─── 데이터 로딩 ────────────────────────────────────────────────────────────
async function fetchDashboardData() {
    // 로딩 상태 초기화
    showLoading('chartLoading', 'chartContainer', 'chartError');
    showLoading('modelsLoading', 'modelsContainer', 'modelsError');
    showLoading('trendingLoading', 'trendingContainer', 'trendingError');

    const endpoints = [
        { url: '/api/notion/performance', key: 'performance' },
        { url: '/api/notion/ai-models', key: 'models' },
        { url: '/api/trending/daily', key: 'repos' },
    ];

    const results = await Promise.allSettled(
        endpoints.map(ep => fetch(ep.url).then(r => {
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            return r.json();
        }))
    );

    // ─── 성과 차트 ──────────────────────────────────────────────────────
    if (results[0].status === 'fulfilled') {
        try {
            renderPerformanceChart(results[0].value);
            showContent('chartContainer', 'chartLoading', 'chartError');
        } catch (e) {
            console.error('차트 렌더링 오류:', e);
            showError('chartError', 'chartLoading', 'chartContainer');
        }
    } else {
        console.error('성과 API 오류:', results[0].reason);
        showError('chartError', 'chartLoading', 'chartContainer');
    }

    // ─── AI 모델 테이블 ─────────────────────────────────────────────────
    if (results[1].status === 'fulfilled') {
        try {
            renderAIModels(results[1].value);
            showContent('modelsContainer', 'modelsLoading', 'modelsError');
        } catch (e) {
            console.error('모델 테이블 렌더링 오류:', e);
            showError('modelsError', 'modelsLoading', 'modelsContainer');
        }
    } else {
        console.error('AI 모델 API 오류:', results[1].reason);
        showError('modelsError', 'modelsLoading', 'modelsContainer');
    }

    // ─── 트렌딩 카드 ────────────────────────────────────────────────────
    if (results[2].status === 'fulfilled') {
        try {
            renderTrendingCards(results[2].value);
            showContent('trendingContainer', 'trendingLoading', 'trendingError');
        } catch (e) {
            console.error('트렌딩 카드 렌더링 오류:', e);
            showError('trendingError', 'trendingLoading', 'trendingContainer');
        }
    } else {
        console.error('트렌딩 API 오류:', results[2].reason);
        showError('trendingError', 'trendingLoading', 'trendingContainer');
    }
}

// ─── UI 상태 전환 헬퍼 ─────────────────────────────────────────────────────
function showLoading(loadingId, contentId, errorId) {
    const loading = document.getElementById(loadingId);
    const content = document.getElementById(contentId);
    const error = document.getElementById(errorId);
    if (loading) loading.style.display = '';
    if (content) content.style.display = 'none';
    if (error) error.style.display = 'none';
}

function showContent(contentId, loadingId, errorId) {
    const loading = document.getElementById(loadingId);
    const content = document.getElementById(contentId);
    const error = document.getElementById(errorId);
    if (loading) loading.style.display = 'none';
    if (content) content.style.display = '';
    if (error) error.style.display = 'none';
}

function showError(errorId, loadingId, contentId) {
    const loading = document.getElementById(loadingId);
    const content = document.getElementById(contentId);
    const error = document.getElementById(errorId);
    if (loading) loading.style.display = 'none';
    if (content) content.style.display = 'none';
    if (error) error.style.display = '';
}

// ─── 성과 차트 렌더링 ──────────────────────────────────────────────────────
function renderPerformanceChart(data) {
    const items = data.performance || [];

    if (items.length === 0) {
        // 데이터 없음 fallback
        document.getElementById('chartContainer').innerHTML = `
            <div class="empty-state">
                <div class="icon">📭</div>
                <div class="message">아직 성과 데이터가 없습니다</div>
            </div>
        `;
        return;
    }

    const canvas = document.getElementById('performanceChart');
    const ctx = canvas.getContext('2d');

    // 데이터 전처리: 날짜별 그룹핑
    const dateMap = new Map();
    for (const item of items) {
        const props = item.properties || item;
        const date = props.date || props.Date || '';
        const value = parseFloat(props.value || props.Value || props.value_num || 0);
        const category = props.category || props.Category || '기타';

        if (!date) continue;

        if (!dateMap.has(date)) {
            dateMap.set(date, {});
        }
        const dateData = dateMap.get(date);
        dateData[category] = (dateData[category] || 0) + value;
    }

    const dates = [...dateMap.keys()].sort();
    const categories = [...new Set(items.map(item => {
        const props = item.properties || item;
        return props.category || props.Category || '기타';
    }))];

    // 카테고리별 색상
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

    // 기존 차트 인스턴스 정리
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
                        font: { size: 12 },
                        padding: 16,
                        usePointStyle: true,
                        pointStyleWidth: 12,
                    },
                },
                tooltip: {
                    backgroundColor: '#1a1d2e',
                    titleColor: '#e2e8f0',
                    bodyColor: '#94a3b8',
                    borderColor: '#2d3748',
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12,
                },
            },
            scales: {
                x: {
                    grid: { color: 'rgba(45, 55, 72, 0.5)' },
                    ticks: { color: '#64748b', font: { size: 11 } },
                },
                y: {
                    grid: { color: 'rgba(45, 55, 72, 0.5)' },
                    ticks: { color: '#64748b', font: { size: 11 } },
                    beginAtZero: true,
                },
            },
        },
    });
}

// ─── AI 모델 테이블 렌더링 ─────────────────────────────────────────────────
function renderAIModels(data) {
    const models = data.models || [];
    const container = document.getElementById('modelsTableContainer');

    if (models.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="icon">📭</div>
                <div class="message">아직 AI 모델 데이터가 없습니다</div>
            </div>
        `;
        return;
    }

    // properties에서 키 추출
    const sampleProps = models[0].properties || models[0];
    const keys = Object.keys(sampleProps).filter(
        k => !['id', 'created_time', 'last_edited_time', 'object'].includes(k)
    );

    // 표시할 컬럼 최대 6개로 제한
    const displayKeys = keys.slice(0, 6);

    // 컬럼명 한국어 매핑
    const keyLabels = {
        'Name': '이름', 'name': '이름', '이름': '이름',
        'Model': '모델', 'model': '모델', '모델': '모델',
        'Category': '카테고리', 'category': '카테고리', '카테고리': '카테고리',
        'Status': '상태', 'status': '상태', '상태': '상태',
        'Score': '점수', 'score': '점수', '점수': '점수',
        'Provider': '제공자', 'provider': '제공자', '제공자': '제공자',
        'Type': '유형', 'type': '유형', '유형': '유형',
        'Description': '설명', 'description': '설명', '설명': '설명',
        'Benchmark': '벤치마크', 'benchmark': '벤치마크', '벤치마크': '벤치마크',
        'Date': '날짜', 'date': '날짜', '날짜': '날짜',
    };

    const thHtml = displayKeys.map(k => {
        const label = keyLabels[k] || k;
        return `<th>${escapeHtml(label)}</th>`;
    }).join('');

    const tbodyHtml = models.map(model => {
        const props = model.properties || model;
        const tds = displayKeys.map(k => {
            const val = props[k];
            const display = extractNotionValue(val);
            return `<td>${escapeHtml(display)}</td>`;
        }).join('');
        return `<tr>${tds}</tr>`;
    }).join('');

    container.innerHTML = `
        <table class="models-table">
            <thead><tr>${thHtml}</tr></thead>
            <tbody>${tbodyHtml}</tbody>
        </table>
    `;
}

// ─── 트렌딩 카드 렌더링 ────────────────────────────────────────────────────
function renderTrendingCards(data) {
    const repos = data.repos || [];
    const grid = document.getElementById('trendingGrid');

    if (repos.length === 0) {
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
                <div class="icon">📭</div>
                <div class="message">오늘의 트렌딩 리포지토리가 없습니다</div>
            </div>
        `;
        return;
    }

    allTrendingRepos = repos;

    grid.innerHTML = repos.map(repo => createRepoCardHtml(repo)).join('');
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
        if (val.formula) {
            return extractNotionValue(val.formula);
        }
        if (val.rollup) {
            return extractNotionValue(val.rollup);
        }
    }

    return String(val);
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
