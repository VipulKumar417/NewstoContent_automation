/* dashboard/static/app.js */

let globalArticles = [];
let generatedVault = [];

document.addEventListener('DOMContentLoaded', () => {
    fetchNews(false);
});

// Navigation Switcher
function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.getElementById(`tab-${tabId}`).classList.remove('hidden');

    ['news', 'library'].forEach(t => {
        const nav = document.getElementById(`nav-${t}`);
        if (t === tabId) {
            nav.classList.add('bg-brand-600/20', 'text-brand-300');
            nav.classList.remove('text-slate-400');
        } else {
            nav.classList.remove('bg-brand-600/20', 'text-brand-300');
            nav.classList.add('text-slate-400');
        }
    });

    document.getElementById('page-title').innerText = tabId === 'news' ? 'Trend Radar' : 'Content Vault';
}

// Step 1: Ingest News
async function fetchNews(force = false) {
    const grid = document.getElementById('news-grid');
    const loading = document.getElementById('news-loading');

    grid.innerHTML = '';
    grid.classList.add('hidden');
    loading.classList.remove('hidden');

    // Start Visual Node Animation
    startNodeAnimation();

    try {
        const response = await fetch(`/api/news?force=${force}`);
        const data = await response.json();
        globalArticles = data.articles;

        // Ensure animation reaches end before popping grid if it was super fast
        setTimeout(() => {
            stopNodeAnimation();
            renderNewsGrid(globalArticles);
        }, 1200);

    } catch (e) {
        console.error("Failed to fetch news:", e);
        document.getElementById('pipeline-status-text').innerHTML = '<span class="text-red-500 font-bold">Failed to connect to the backend server. Check terminal.</span>';
    }
}

// Visual Node Animator Array
let nodeTimerInt;
const wait = (ms) => new Promise(res => setTimeout(res, ms));

async function startNodeAnimation() {
    // Reset states
    for (let i = 1; i <= 4; i++) {
        document.getElementById(`node-${i}`).className = "w-16 h-16 rounded-xl bg-slate-800 border-2 border-slate-700 flex items-center justify-center shadow-lg transition-all duration-500 relative z-10 flex-shrink-0";
        document.getElementById(`icon-${i}`).className = `fa-solid fa-${['rss', 'database', 'brain', 'filter'][i - 1]} text-2xl text-slate-400 transition-colors duration-500`;
        if (i < 4) document.getElementById(`wire-${i}`).style.width = "0%";
    }

    const statuses = [
        "Pinging NewsData.io & GNews APIs...",
        "Deduplicating cross-references in Cache...",
        "Executing Gemini 2.5 Flash context analyzers...",
        "Applying EpiCred startup restrictions..."
    ];

    for (let i = 1; i <= 4; i++) {
        document.getElementById('pipeline-status-text').innerText = statuses[i - 1];

        // Light up Node
        document.getElementById(`node-${i}`).classList.replace('bg-slate-800', 'bg-brand-50');
        document.getElementById(`node-${i}`).classList.replace('border-slate-700', 'border-brand-500');
        document.getElementById(`node-${i}`).classList.add('shadow-[0_0_15px_rgba(99,102,241,0.5)]');

        // Spin icon if it's the brain
        document.getElementById(`icon-${i}`).classList.replace('text-slate-400', 'text-brand-600');
        if (i === 3) document.getElementById(`icon-${i}`).classList.add('fa-fade');

        // Light up wire
        if (i < 4) {
            await wait(800);
            document.getElementById(`wire-${i}`).style.width = "100%";
            await wait(800);
        }
    }
}

function stopNodeAnimation() { }

// Step 2: Render Feeds
function renderNewsGrid(articles) {
    const grid = document.getElementById('news-grid');
    const loading = document.getElementById('news-loading');

    loading.classList.add('hidden');
    grid.classList.remove('hidden');
    grid.classList.remove('grid', 'grid-cols-1', 'xl:grid-cols-2'); // Swap layout to block

    if (!articles || articles.length === 0) {
        grid.innerHTML = `
        <div class="py-20 text-center flex flex-col items-center">
            <div class="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center mb-4 text-slate-300">
                <i class="fa-solid fa-calendar-xmark text-3xl"></i>
            </div>
            <p class="text-slate-600 font-medium text-lg">No relevant content found recently.</p>
            <p class="text-slate-400 text-sm mt-2 max-w-xs mx-auto">Gemini filtered out non-Fintech/UPSC news. NewsData.io Free Tier restricts us to the last 48 hours.</p>
        </div>`;
        return;
    }

    const topTier = articles.filter(a => (a.score?.overall_score || 0) >= 7);
    const midTier = articles.filter(a => {
        const s = a.score?.overall_score || 0;
        return s >= 6 && s < 7;
    });

    let html = '';

    // Helper func for card renderer
    const renderCard = (a, index, isTop) => {
        const score = a.score ? a.score.overall_score : '?';
        const reason = a.score ? a.score.reason : 'Waiting for AI analysis...';
        const displayTitle = (a.score && a.score.suggested_title) ? a.score.suggested_title : a.title;
        const hookLine = (a.score && a.score.hook_line) ? a.score.hook_line : '';
        const contentAngle = (a.score && a.score.content_angle) ? a.score.content_angle.replace('_', ' ') : '';

        return `
        <div class="bg-white rounded-2xl p-6 border ${isTop ? 'border-brand-200 shadow-md transform hover:-translate-y-1' : 'border-slate-200 shadow-sm opacity-90 hover:opacity-100'} transition-all animate-fade-in flex flex-col justify-between" style="animation-delay: ${index * 50}ms">
            <div>
                <div class="flex justify-between items-start mb-4">
                    <div class="flex items-center gap-2 flex-wrap">
                        <span class="px-3 py-1 bg-slate-100 text-slate-600 text-xs font-semibold rounded-lg border border-slate-200 flex items-center gap-2"><i class="fa-regular fa-clock"></i> ${new Date(a.published_at).toLocaleDateString()} &middot; ${a.source || 'Intel'}</span>
                        ${contentAngle ? `<span class="px-2 py-1 bg-brand-50 text-brand-700 text-xs font-semibold rounded-md border border-brand-100">${contentAngle}</span>` : ''}
                    </div>
                    <div class="w-10 h-10 rounded-full ${isTop ? 'bg-green-100 text-green-600 border-green-200' : 'bg-orange-100 text-orange-600 border-orange-200'} flex items-center justify-center font-bold text-lg border shrink-0 shadow-inner">
                        ${score}
                    </div>
                </div>
                <h3 class="text-xl font-bold text-slate-800 mb-1 leading-tight">${displayTitle}</h3>
                ${hookLine ? `<p class="text-sm text-brand-600 font-medium mb-3 italic">${hookLine}</p>` : ''}
                <p class="text-sm text-slate-500 mb-4 line-clamp-2">${a.source || ''} &middot; Original: ${a.title.length > 60 ? a.title.substring(0, 60) + '...' : a.title}</p>
                
                <div class="${isTop ? 'bg-indigo-50/50 border-indigo-100/50' : 'bg-slate-50 border-slate-100'} p-4 rounded-xl border mb-6">
                    <p class="text-xs ${isTop ? 'text-indigo-900' : 'text-slate-600'} leading-relaxed"><i class="fa-solid fa-lightbulb mr-1 ${isTop ? 'text-amber-500' : 'text-slate-400'}"></i> <strong>Student Impact:</strong> ${reason}</p>
                </div>
            </div>
            
            <button onclick='generateContent(${globalArticles.indexOf(a)})' class="w-full py-3 ${isTop ? 'bg-brand-600 hover:bg-brand-700 shadow-[0_4px_14px_0_rgba(99,102,241,0.39)] text-white' : 'bg-slate-100 hover:bg-slate-200 text-slate-700'} rounded-xl font-medium transition-colors flex items-center justify-center gap-2">
                <i class="fa-solid fa-wand-magic-sparkles"></i> Build Campaign
            </button>
        </div>`;
    };

    // Render Top Candidates
    if (topTier.length > 0) {
        html += `<h3 class="text-xl font-extrabold text-slate-800 mb-4 flex items-center gap-2"><i class="fa-solid fa-fire text-orange-500"></i> Priority Recommendations (7-10)</h3>`;
        html += `<div class="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-12">`;
        topTier.forEach((a, i) => html += renderCard(a, i, true));
        html += `</div>`;
    }

    // Render Mid Candidates
    if (midTier.length > 0) {
        html += `<h3 class="text-lg font-bold text-slate-500 mb-4 flex items-center gap-2"><i class="fa-solid fa-box-archive text-slate-400"></i> Worth Monitoring (6)</h3>`;
        html += `<div class="grid grid-cols-1 xl:grid-cols-2 gap-6">`;
        midTier.forEach((a, i) => html += renderCard(a, i, false));
        html += `</div>`;
    }

    grid.innerHTML = html;
}

// Step 3: Trigger Phase 3 AI Pipeline
async function generateContent(articleIndex) {
    const article = globalArticles[articleIndex];
    if (!article) return;

    showModal('Generating Content...', 'Firing 6 sequential Gemini invocations across 16 load-balanced keys. ETA: 30-40s');

    try {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ article: article })
        });

        const data = await response.json();

        if (data.bundle) {
            const platformCount = Object.values(data.bundle).filter(v => v !== null).length;
            if (platformCount === 0) {
                alert("Critical API Error: Generation failed for all channels. Google Gemini API Daily Quota is likely exhausted. Please try again tomorrow or add fresh billing keys.");
                hideModal();
                return;
            }
            generatedVault.unshift({ "article": article, "bundle": data.bundle });
            renderVault();
            hideModal();
            switchTab('library');
        } else {
            alert("Error generating content.");
            hideModal();
        }
    } catch (e) {
        console.error("Gen logic failure:", e);
        alert("Server failed. Monitor backend terminal.");
        hideModal();
    }
}

// Step 4: Render Content Output Screen
function renderVault() {
    const empty = document.getElementById('library-empty');
    const content = document.getElementById('library-content');

    if (generatedVault.length === 0) {
        empty.classList.remove('hidden');
        content.classList.add('hidden');
        return;
    }

    empty.classList.add('hidden');
    content.classList.remove('hidden');

    let html = '';
    generatedVault.forEach((item, idx) => {
        const platformCount = Object.values(item.bundle).filter(v => v !== null).length;

        html += `
        <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mb-6 animate-fade-in relative overflow-hidden group hover:border-slate-300 transition-colors">
            
            <!-- Floating accent -->
            <div class="absolute -right-16 -top-16 w-32 h-32 bg-brand-50 rounded-full blur-3xl opacity-50 group-hover:opacity-100 transition-opacity"></div>
            
            <div class="flex flex-col md:flex-row justify-between md:items-center gap-4 mb-6 pb-6 border-b border-slate-100 relative z-10">
                <div>
                    <h3 class="text-xl font-bold text-slate-800">${item.article.title}</h3>
                    <p class="text-sm text-slate-500 mt-1 font-medium"><i class="fa-solid fa-layer-group text-fuchsia-500 mr-1"></i> ${platformCount} Channels Formatted</p>
                </div>
                <button onclick="saveToGoogle(${idx})" id="sync-btn-${idx}" class="shrink-0 px-6 py-3 bg-slate-900 text-white rounded-xl font-medium hover:bg-slate-800 transition-colors shadow flex items-center justify-center gap-2">
                    <i class="fa-brands fa-google drive-icon"></i> Execute Sync
                </button>
            </div>
            
            <div class="grid grid-cols-2 lg:grid-cols-3 gap-3 relative z-10">`;

        Object.keys(item.bundle).forEach(platform => {
            if (item.bundle[platform]) {
                const nameMap = {
                    'instagram_reel': '<i class="fa-brands fa-instagram text-fuchsia-500 mr-2"></i> Reel Pipeline',
                    'instagram_carousel': '<i class="fa-brands fa-instagram text-fuchsia-500 mr-2"></i> Carousel Pipeline',
                    'instagram_post': '<i class="fa-brands fa-instagram text-fuchsia-500 mr-2"></i> Post Strategy',
                    'linkedin_post': '<i class="fa-brands fa-linkedin text-blue-600 mr-2"></i> LinkedIn Story',
                    'twitter_thread': '<i class="fa-brands fa-twitter text-sky-500 mr-2"></i> Twitter Matrix',
                    'youtube_shorts': '<i class="fa-brands fa-youtube text-red-500 mr-2"></i> YT Shorts Script'
                };
                html += `
                <button onclick="openEditor(${idx}, '${platform}')" class="p-3 bg-slate-50 rounded-lg border border-slate-100 flex items-center text-sm font-semibold text-slate-700 hover:bg-white hover:shadow-md transition-all active:scale-95 text-left">
                    ${nameMap[platform] || platform}
                </button>`;
            }
        });

        html += `
            </div>
        </div>`;
    });

    content.innerHTML = html;
}

// Step 5: Phase 4 Workspace Integration
async function saveToGoogle(idx) {
    const btn = document.getElementById(`sync-btn-${idx}`);
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Pushing...`;
    btn.disabled = true;

    const vaultItem = generatedVault[idx];

    try {
        const response = await fetch('/api/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bundle: vaultItem.bundle, article: vaultItem.article })
        });

        const data = await response.json();

        if (data.success) {
            btn.innerHTML = `<i class="fa-solid fa-check text-green-500"></i> Workspace Active`;
            btn.classList.add('bg-green-50', 'text-green-700', 'border', 'border-green-200');
            btn.classList.remove('bg-slate-900', 'text-white');

            // Show Success Modal
            document.getElementById('modal-generate').classList.add('hidden');
            document.getElementById('modal-confirm').classList.remove('hidden');
            document.getElementById('modal-overlay').classList.remove('hidden');
            document.getElementById('modal-overlay').classList.remove('opacity-0');
        } else {
            alert("Workspace error: " + data.error);
            btn.innerHTML = `<i class="fa-brands fa-google"></i> Retry Sync`;
            btn.disabled = false;
        }
    } catch (e) {
        console.error("Sync error:", e);
        btn.innerHTML = `<i class="fa-brands fa-google text-red-500"></i> Fatal Sync Out`;
    }
}

// Modals
function showModal(title, subtitle) {
    document.getElementById('modal-title').innerText = title;
    document.getElementById('modal-subtitle').innerText = subtitle;

    document.getElementById('modal-generate').classList.remove('hidden');
    document.getElementById('modal-confirm').classList.add('hidden');

    document.getElementById('modal-overlay').classList.remove('hidden');
    setTimeout(() => { document.getElementById('modal-overlay').classList.remove('opacity-0'); }, 10);
}

function hideModal() {
    closeModal();
}

function closeModal() {
    document.getElementById('modal-overlay').classList.add('opacity-0');
    setTimeout(() => { document.getElementById('modal-overlay').classList.add('hidden'); }, 300);
}

// Inline Content Editing
function openEditor(vaultIdx, platform) {
    const item = generatedVault[vaultIdx];
    const data = item.bundle[platform];

    document.getElementById('editor-title').innerText = `Edit ${platform.replace('_', ' ').toUpperCase()}`;
    const textarea = document.getElementById('editor-textarea');
    textarea.value = JSON.stringify(data, null, 2);

    document.getElementById('editor-error').classList.add('hidden');

    // Bind save logic
    const saveBtn = document.getElementById('editor-save-btn');
    saveBtn.onclick = () => {
        try {
            const parsed = JSON.parse(textarea.value);
            // Re-inject back into vault
            generatedVault[vaultIdx].bundle[platform] = parsed;
            closeModal();
            // Pulse the pill to show saved? Render vault naturally keeps state.
        } catch (e) {
            document.getElementById('editor-error').classList.remove('hidden');
        }
    };

    // Show Modal
    document.getElementById('modal-generate').classList.add('hidden');
    document.getElementById('modal-confirm').classList.add('hidden');
    document.getElementById('modal-editor').classList.remove('hidden');

    document.getElementById('modal-overlay').classList.remove('hidden');
    setTimeout(() => { document.getElementById('modal-overlay').classList.remove('opacity-0'); }, 10);
}
