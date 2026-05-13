const API = '';

// ============= AUTH =============
const TOKEN_KEY = 'authToken';
const USER_KEY  = 'authUser';
let _authMode = 'login'; // 'login' | 'signup'
let _currentUser = null;

function getToken()  { return localStorage.getItem(TOKEN_KEY) || null; }
function setToken(t) { if (t) localStorage.setItem(TOKEN_KEY, t); else localStorage.removeItem(TOKEN_KEY); }
function getUser()   { try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); } catch { return null; } }
function setUser(u)  { if (u) localStorage.setItem(USER_KEY, JSON.stringify(u)); else localStorage.removeItem(USER_KEY); _currentUser = u; renderAuthChip(); }
function isLoggedIn(){ return !!getToken(); }

function authHeader() {
  const t = getToken();
  return t ? {'Authorization': 'Bearer ' + t} : {};
}

function renderAuthChip() {
  const slot = document.getElementById('authSlot');
  if (!slot) return;
  const u = _currentUser || getUser();
  if (u) {
    const planClass = `plan-${u.plan || 'free'}`;
    slot.innerHTML = `<div class="user-chip" onclick="showPage('account', null)" title="החשבון שלי">
      <span class="uname">${escapeHtml(u.email)}</span>
      <span class="plan-badge ${planClass}">${u.plan || 'free'}</span>
    </div>`;
  } else {
    slot.innerHTML = '<button class="btn btn-blue" onclick="openLogin()" id="loginBtn">🔓 התחבר</button>';
  }
  // הצג/הסתר אזורים תלויי-משתמש
  const isAdm = u && u.is_admin;
  document.querySelectorAll('.admin-only').forEach(el => { el.style.display = isAdm ? '' : 'none'; });
  document.querySelectorAll('.logged-in-only').forEach(el => { el.style.display = u ? '' : 'none'; });
}

function openLogin() {
  _authMode = 'login';
  setAuthMode();
  document.getElementById('authModal').classList.add('show');
  setTimeout(() => document.getElementById('authEmail')?.focus(), 100);
}

function closeLogin() {
  document.getElementById('authModal').classList.remove('show');
  document.getElementById('authError').classList.remove('show');
  document.getElementById('authForm').reset();
}

function toggleAuthMode() {
  _authMode = (_authMode === 'login') ? 'signup' : 'login';
  setAuthMode();
}

function setAuthMode() {
  const isSignup = _authMode === 'signup';
  document.getElementById('authTitle').textContent       = isSignup ? '✨ הרשמה' : '🔓 התחברות';
  document.getElementById('authSubtitle').textContent    = isSignup ? 'צור חשבון בחינם לשמירת הרשימות והעדפות' : 'היכנס לחשבון שלך';
  document.getElementById('authSubmitBtn').textContent   = isSignup ? 'הירשם' : 'התחבר';
  document.getElementById('nameField').style.display     = isSignup ? '' : 'none';
  document.getElementById('switchPrompt').textContent    = isSignup ? 'יש לך כבר חשבון?' : 'אין לך חשבון?';
  document.getElementById('switchLink').textContent      = isSignup ? 'התחבר' : 'הירשם בחינם';
  document.getElementById('authPassword').autocomplete   = isSignup ? 'new-password' : 'current-password';
  document.getElementById('forgotLink').style.display    = isSignup ? 'none' : '';
  document.getElementById('termsRow').style.display      = isSignup ? '' : 'none';
  document.getElementById('authError').classList.remove('show');
}

async function submitAuth() {
  const email    = document.getElementById('authEmail').value.trim().toLowerCase();
  const password = document.getElementById('authPassword').value;
  const fullName = document.getElementById('authName').value.trim() || null;
  const errEl    = document.getElementById('authError');
  const btn      = document.getElementById('authSubmitBtn');

  errEl.classList.remove('show');
  btn.disabled = true; btn.textContent = '...';

  try {
    const endpoint = (_authMode === 'signup') ? '/api/auth/signup' : '/api/auth/login';
    const body = (_authMode === 'signup')
      ? {email, password, full_name: fullName}
      : {email, password};
    const r = await fetch(API + endpoint, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body),
    });
    const data = await r.json();
    if (!r.ok) {
      const msg = (data.detail && typeof data.detail === 'string') ? data.detail
                : (Array.isArray(data.detail) ? data.detail.map(d => d.msg).join(', ') : 'אירעה שגיאה');
      errEl.textContent = msg;
      errEl.classList.add('show');
      return;
    }
    setToken(data.access_token);
    setUser(data.user);
    closeLogin();
    toast((_authMode === 'signup') ? `ברוך הבא, ${data.user.email}` : `שלום, ${data.user.email}`);
    // סנכרון Watchlist מ-localStorage לשרת + רענון cache
    if (typeof wlSyncOnLogin === 'function') {
      await wlSyncOnLogin();
      _wlCache = null;
      await wlLoad(true);
    }
    // טען מחדש מידע שתלוי במשתמש
    if (typeof pollNotifications === 'function') pollNotifications();
    if (typeof loadDashboard === 'function') loadDashboard();
  } catch (e) {
    errEl.textContent = 'תקלת רשת: ' + (e.message || e);
    errEl.classList.add('show');
  } finally {
    btn.disabled = false;
    btn.textContent = (_authMode === 'signup') ? 'הירשם' : 'התחבר';
  }
}

function logout() {
  if (!confirm('להתנתק מהחשבון?')) return;
  setToken(null);
  setUser(null);
  _wlCache = null;          // ננקה cache של watchlist - יטען localStorage
  toast('התנתקת');
  loadDashboard();
  pollNotifications();
}

// אימות אוטומטי של ה-token בטעינה
async function validateSession() {
  if (!isLoggedIn()) { renderAuthChip(); return; }
  try {
    const r = await fetch(API + '/api/auth/me', {headers: authHeader()});
    if (r.ok) {
      const u = await r.json();
      setUser(u);
    } else if (r.status === 401) {
      // token פג תוקף
      setToken(null);
      setUser(null);
    }
  } catch (e) {
    // network issue - leave cached user info, don't clear
    _currentUser = getUser();
    renderAuthChip();
  }
}


function toggleMoreMenu(e) {
  if (e) e.stopPropagation();
  const menu = document.getElementById('moreMenu');
  const bg = document.getElementById('moreMenuBg');
  if (!menu) return;
  const isOpen = menu.style.display !== 'none';
  menu.style.display = isOpen ? 'none' : 'block';
  bg.style.display = isOpen ? 'none' : 'block';
}

function showPage(pageId, btn) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item, .mobile-nav-item').forEach(b => b.classList.remove('active'));
  document.getElementById('page-' + pageId).classList.add('active');
  document.querySelectorAll(`[onclick*="'${pageId}'"]`).forEach(b => b.classList.add('active'));
  window.scrollTo(0, 0);
  if (pageId === 'signals') loadSignals();
  if (pageId === 'watchlist') loadWatchlist();
  if (pageId === 'news') loadNews();
  if (pageId === 'journal') loadJournal();
  if (pageId === 'scans') loadScans();
  if (pageId === 'settings') loadHealth();
  if (pageId === 'plans') loadPlans();
  if (pageId === 'admin') loadAdmin();
  if (pageId === 'analytics') { setAnTab(_anCurrentTab || 'performance'); }
  if (pageId === 'account') loadAccount();
}

function updateClock() {
  const n = new Date();
  const dateStr = n.toLocaleDateString('he-IL');
  const timeStr = n.toLocaleTimeString('he-IL');
  // ה-sidebar (desktop)
  const sd = document.getElementById('sidebarDate');
  const st = document.getElementById('sidebarTime');
  if (sd) sd.textContent = dateStr;
  if (st) st.textContent = timeStr;
  // ה-topbar mobile fallback
  const c = document.getElementById('clock');
  if (c) c.textContent = `📅 ${dateStr} | ⏰ ${timeStr}`;
  const lu = document.getElementById('lastUpdate');
  if(lu) lu.textContent = `עדכון: ${timeStr}`;
}
setInterval(updateClock, 1000);
updateClock();

function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(window._toastT);
  window._toastT = setTimeout(() => t.classList.remove('show'), 2500);
}

async function api(path, options) {
  options = options || {};
  options.headers = Object.assign({}, options.headers || {}, authHeader());
  try {
    const r = await fetch(API + path, options);
    if (r.status === 401 && isLoggedIn()) {
      // token פג - ננקה ונציג הודעה
      setToken(null); setUser(null);
      toast('פג תוקף ההתחברות, התחבר שוב');
      return null;
    }
    if (!r.ok) throw new Error(r.statusText);
    return await r.json();
  } catch (e) {
    console.error('API error', path, e);
    return null;
  }
}

function strengthColor(v) {
  if (v >= 8) return 'linear-gradient(90deg,#00d4ff,#00ff88)';
  if (v >= 6) return 'linear-gradient(90deg,#00d4ff,#ffd700)';
  return 'linear-gradient(90deg,#ffd700,#ff4466)';
}

function strengthTextColor(v) {
  if (v >= 8) return '#00ff88';
  if (v >= 6) return '#ffd700';
  return '#ff4466';
}

function renderSignal(s) {
  const strength = s.strength || 0;
  const starred = wlHas(s.symbol);
  return `
    <div class="signal-card">
      <div class="signal-top">
        <div style="display:flex;align-items:center;gap:6px">
          <button class="star-btn ${starred?'active':''}" onclick="event.stopPropagation();wlToggle('${s.symbol}')" title="הוסף ל-Watchlist">${starred?'★':'☆'}</button>
          <div class="signal-symbol clickable-sym" onclick="openStock('${s.symbol}')">${s.symbol}</div>
        </div>
        <div class="signal-price">$${s.price.toFixed(2)}</div>
      </div>
      <div class="signal-badges">
        <div class="sbadge">RSI <span>${s.rsi.toFixed(1)}</span></div>
        <div class="sbadge">וולום <span>x${s.volume_ratio.toFixed(1)}</span></div>
        <div class="sbadge">סטטוס <span>${s.status === 'open' ? 'פתוח' : 'סגור'}</span></div>
      </div>
      <div class="strength-row">
        <div class="strength-label">חוזק</div>
        <div class="strength-bar"><div class="strength-fill" style="width:${strength*10}%;background:${strengthColor(strength)}"></div></div>
        <div class="strength-num" style="color:${strengthTextColor(strength)}">${strength.toFixed(1)}/10</div>
      </div>
      <div class="signal-targets">
        <div class="target-box t1"><div class="tl">יעד 1</div><div class="tv">$${s.target_1.toFixed(2)}</div></div>
        <div class="target-box t2"><div class="tl">יעד 2</div><div class="tv">$${s.target_2.toFixed(2)}</div></div>
        <div class="target-box sl"><div class="tl">סטופ</div><div class="tv">$${s.stop_loss.toFixed(2)}</div></div>
      </div>
    </div>`;
}

function renderEmpty(icon, title, hint) {
  return `<div class="empty"><div class="empty-icon">${icon}</div><div style="font-weight:bold;margin-bottom:6px">${title}</div><div>${hint}</div></div>`;
}

function renderNews(n) {
  const time = n.published_at ? new Date(n.published_at).toLocaleString('he-IL') : '';
  const author = n.source === 'twitter' ? `@${n.author}` : n.author;
  const srcClass = n.source === 'twitter' ? 'source-twitter' : 'source-rss';
  // הדגשה אם המנייה ב-watchlist
  const mentioned = (n.mentioned_symbols || '').split(',').filter(Boolean);
  const wlList = wlGet();
  const matchedWl = mentioned.filter(s => wlList.includes(s));
  const isWatched = matchedWl.length > 0;
  const wlBadges = matchedWl.map(s =>
    `<span class="wl-symbol-badge" onclick="event.stopPropagation();openStock('${s}')">⭐ ${s}</span>`
  ).join('');
  const allBadges = mentioned.filter(s => !matchedWl.includes(s)).map(s =>
    `<span class="sym-badge" onclick="event.stopPropagation();openStock('${s}')">${s}</span>`
  ).join('');
  const cardClass = isWatched ? 'news-card watched-news' : 'news-card';

  // עברית: קודם תרגום מלא (OpenAI), אחרת רמז ממילון מקומי
  let hebrewBlock = '';
  if (n.hebrew_translation) {
    hebrewBlock = `<div class="news-side heb"><span class="news-lang">🇮🇱 עברית</span><div class="text">${escapeHtml(n.hebrew_translation)}</div></div>`;
  } else if (n.hebrew_explanation) {
    hebrewBlock = `<div class="news-side heb"><span class="news-lang">🇮🇱 עברית (רמז)</span><div class="text">${escapeHtml(n.hebrew_explanation)}</div></div>`;
  } else {
    hebrewBlock = `<div class="news-side heb"><span class="news-lang">🇮🇱 עברית</span><div class="news-no-trans">— אין תרגום זמין —</div></div>`;
  }

  // הסבר נוסף - רק אם יש גם תרגום וגם הסבר נפרד
  const extra = (n.hebrew_translation && n.hebrew_explanation && n.hebrew_translation !== n.hebrew_explanation)
    ? `<div class="news-explanation">💡 ${escapeHtml(n.hebrew_explanation)}</div>` : '';

  return `
    <div class="${cardClass}">
      <div class="news-meta">
        <div class="news-author ${srcClass}">${author}</div>
        <div>${time}</div>
      </div>
      ${(wlBadges || allBadges) ? `<div class="news-symbols">${wlBadges}${allBadges}</div>` : ''}
      <div class="news-bilingual">
        <div class="news-side eng">
          <span class="news-lang">🇺🇸 EN</span>
          <div class="text">${escapeHtml(n.text)}</div>
        </div>
        ${hebrewBlock}
      </div>
      ${extra}
      ${n.url ? `<a class="news-link" href="${escapeAttr(n.url)}" target="_blank" rel="noopener">קישור למקור →</a>` : ''}
    </div>`;
}

function escapeHtml(s) {
  return String(s||'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function escapeAttr(s) { return escapeHtml(s); }

async function loadStats() {
  const s = await api('/api/stats');
  if (!s) return;
  document.getElementById('statSignalsToday').textContent = s.signals_today;
  document.getElementById('statWinRate').textContent = (s.win_rate_pct || 0).toFixed(0) + '%';
  document.getElementById('statMonthlyPnl').textContent = (s.monthly_pnl_pct >= 0 ? '+' : '') + (s.monthly_pnl_pct || 0).toFixed(1) + '%';
  document.getElementById('statOpenPos').textContent = s.open_positions;
}

async function loadSignals() {
  const sigs = await api('/api/signals?limit=50&status=open') || [];
  const el = document.getElementById('signalsList');
  el.innerHTML = sigs.length ? sigs.map(renderSignal).join('') : renderEmpty('🔍', 'אין סיגנלים פתוחים', 'הרץ סריקת שוק או חכה לסריקה מתוזמנת');
}

async function loadDashboard() {
  loadStats();
  await wlLoad(true);  // ודא ש-wlGet() יחזיר מצב מעודכן ל-renderNews
  const sigs = await api('/api/signals?limit=4&status=open') || [];
  document.getElementById('openCount').textContent = sigs.length;
  document.getElementById('dashSignals').innerHTML = sigs.length ? sigs.map(renderSignal).join('') : renderEmpty('🔍', 'אין סיגנלים פתוחים', 'הרץ סריקת שוק');

  const news = await api('/api/news?limit=5&hours_back=24') || [];
  document.getElementById('newsCount').textContent = news.length;
  document.getElementById('dashNews').innerHTML = news.length ? news.map(renderNews).join('') : renderEmpty('📭', 'אין חדשות', 'הרץ סריקת חדשות');

  // חדשות על Watchlist - מקטע מוצג רק אם המשתמש מחובר עם פריטים
  await loadWatchedNews();
}

async function loadWatchedNews(force) {
  const card = document.getElementById('watchedNewsCard');
  if (!isLoggedIn() || wlGet().length === 0) {
    if (card) card.style.display = 'none';
    updateTicker([]);
    return;
  }
  const news = await api('/api/news?watchlist_only=true&limit=40&hours_back=72') || [];
  card.style.display = '';
  document.getElementById('watchedNewsCount').textContent = news.length;

  // עדכון הטיקר
  updateTicker(news);

  if (!news.length) {
    document.getElementById('dashWatchedNews').innerHTML = '<div class="news-empty" style="text-align:center;padding:14px;color:var(--muted);font-size:12px">אין עדיין חדשות על המניות שלך</div>';
    return;
  }

  // קיבוץ לפי מנייה (primary symbol)
  const wl = new Set(wlGet());
  const bySymbol = {};
  for (const n of news) {
    const syms = (n.mentioned_symbols || '').split(',').filter(s => s && wl.has(s));
    if (!syms.length) continue;
    const primarySym = syms[0];
    if (!bySymbol[primarySym]) bySymbol[primarySym] = [];
    bySymbol[primarySym].push(n);
  }

  // סדר לפי מספר פריטים יורד
  const sorted = Object.entries(bySymbol).sort((a, b) => b[1].length - a[1].length);

  let html = '';
  for (const [sym, items] of sorted) {
    const top = items[0];
    const topHebrew = top.hebrew_translation || top.hebrew_explanation || '';
    const topText = (top.text || '').replace(/\[👍 \d+ \| 💬 \d+\] /, '').slice(0, 160);
    const time = top.fetched_at ? timeAgo(top.fetched_at) : '';
    html += `
      <div class="wl-group" style="background:#080c14;border:1px solid var(--border);border-right:3px solid var(--gold);border-radius:10px;padding:10px 12px;margin-bottom:8px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <div style="display:flex;gap:6px;align-items:center">
            <span class="wl-symbol-badge" onclick="openStock('${sym}')" style="cursor:pointer">⭐ ${sym}</span>
            <span style="color:var(--muted);font-size:10px">${items.length} כותרות</span>
          </div>
          <span style="color:var(--muted);font-size:10px">${time}</span>
        </div>
        <div style="font-size:12px;line-height:1.4;margin-bottom:4px">${escapeHtml(topText)}</div>
        ${topHebrew ? `<div style="font-size:11px;color:#bcc7d6;background:rgba(0,212,255,0.05);border-right:2px solid var(--blue);padding:4px 8px;border-radius:0 4px 4px 0;margin-top:6px">🇮🇱 ${escapeHtml(topHebrew)}</div>` : ''}
        ${items.length > 1 ? `<button class="btn" style="background:none;border:none;color:var(--blue);font-size:11px;padding:4px 0;cursor:pointer" onclick="this.nextElementSibling.style.display='block';this.style.display='none'">+ ${items.length - 1} עוד</button>
        <div style="display:none;margin-top:6px">${items.slice(1).map(n => `<div style="font-size:11px;color:var(--muted);padding:4px 0;border-top:1px dashed var(--border)">${escapeHtml((n.text || '').replace(/\\[👍 \\d+ \\| 💬 \\d+\\] /, '').slice(0, 130))} <a href="${escapeAttr(n.url||'#')}" target="_blank" style="color:var(--blue)">↗</a></div>`).join('')}</div>` : ''}
        ${top.url ? `<a href="${escapeAttr(top.url)}" target="_blank" style="font-size:10px;color:var(--blue);text-decoration:none;display:inline-block;margin-top:6px">📎 קישור למקור</a>` : ''}
      </div>`;
  }
  document.getElementById('dashWatchedNews').innerHTML = html;
}

// =========== WATCHLIST TICKER ===========
let _tickerDismissed = false;

function updateTicker(news) {
  const ticker = document.getElementById('wlTicker');
  const strip = document.getElementById('wlTickerStrip');
  if (!ticker || !strip) return;

  if (_tickerDismissed || !news.length || !isLoggedIn() || wlGet().length === 0) {
    ticker.classList.remove('show');
    document.body.classList.remove('has-ticker');
    return;
  }

  // קח עד 20 פריטים אחרונים, עם סמל שב-watchlist
  const wl = new Set(wlGet());
  const items = news.filter(n => {
    const syms = (n.mentioned_symbols || '').split(',').filter(Boolean);
    return syms.some(s => wl.has(s));
  }).slice(0, 20);

  if (!items.length) {
    ticker.classList.remove('show');
    document.body.classList.remove('has-ticker');
    return;
  }

  // כפילות לאנימציה רציפה
  const html = items.concat(items).map(n => {
    const sym = (n.mentioned_symbols || '').split(',').filter(s => wl.has(s))[0] || '?';
    const text = (n.text || '').replace(/\[👍 \d+ \| 💬 \d+\] /, '').slice(0, 120);
    const time = n.fetched_at ? timeAgo(n.fetched_at) : '';
    return `<div class="wl-ticker-item" onclick="openStock('${sym}')">
      <span class="wl-ticker-sym">${sym}</span>
      <span class="wl-ticker-text">${escapeHtml(text)}</span>
      <span class="wl-ticker-time">${time}</span>
    </div>`;
  }).join('');
  strip.innerHTML = html;

  ticker.classList.add('show');
  document.body.classList.add('has-ticker');
}

function dismissTicker() {
  _tickerDismissed = true;
  document.getElementById('wlTicker').classList.remove('show');
  document.body.classList.remove('has-ticker');
}

// === REAL-TIME WATCHLIST NEWS POLLING ===
let _lastWatchedNewsId = parseInt(localStorage.getItem('lastWatchedNewsId') || '0');

async function pollWatchlistNews() {
  if (!isLoggedIn() || wlGet().length === 0) return;
  const params = new URLSearchParams({
    watchlist_only: 'true',
    limit: '20',
    hours_back: '72',
  });
  // טוען לטיקר את כל הטריים, ל-popup רק חדשים מהביקור האחרון
  const allNews = await api('/api/news?' + params.toString());
  if (!allNews || !allNews.length) return;

  // עדכון הטיקר עם כל החדשות (זה מחליף את refreshTicker - אין double polling)
  updateTicker(allNews);

  const newest = allNews[0];
  if (newest.id <= _lastWatchedNewsId) return;

  // אם זאת לא הטעינה הראשונה - הצג popup + browser notification + החזר ticker אם הוסתר
  const isFirstLoad = _lastWatchedNewsId === 0;
  _lastWatchedNewsId = newest.id;
  localStorage.setItem('lastWatchedNewsId', String(_lastWatchedNewsId));

  if (!isFirstLoad) {
    // הופיעה חדשה - אם המשתמש הסתיר את הטיקר, נחזיר אותו (יש משהו חדש לראות)
    _tickerDismissed = false;
    updateTicker(allNews);

    const news = allNews.filter(n => n.id > _lastWatchedNewsId - 100); // החדשים יחסית
    news.slice(0, 3).forEach(n => showWatchlistPopup(n));
    // אם יש הרשאת browser - הודעה native
    if ('Notification' in window && Notification.permission === 'granted') {
      const sym = (n => (n.mentioned_symbols || '').split(',')[0])(newest);
      try {
        const notif = new Notification(`📰 ${sym}: חדשות חדשות`, {
          body: newest.text.slice(0, 200),
          icon: '/static/icon.svg',
          tag: 'wl-news-' + newest.id,
        });
        notif.onclick = () => { window.focus(); openStock(sym); notif.close(); };
      } catch (e) {}
    }
  }

  // רענון הדשבורד אם פתוח
  const active = document.querySelector('.page.active')?.id;
  if (active === 'page-dashboard') loadWatchedNews();
  if (active === 'page-news') loadNews();
}

function showWatchlistPopup(n) {
  const sym = (n.mentioned_symbols || '').split(',').filter(s => wlGet().includes(s))[0] || '?';
  const popup = document.createElement('div');
  popup.className = 'wl-popup';
  popup.innerHTML = `
    <button class="x" onclick="this.parentElement.remove()">✕</button>
    <div class="wl-popup-header">📰 חדשות על ${sym}</div>
    <div class="wl-popup-title">${escapeHtml(n.text.slice(0, 150))}</div>
    <div class="wl-popup-meta"><span>${escapeHtml(n.author)}</span><span>${new Date(n.fetched_at).toLocaleTimeString('he-IL')}</span></div>
  `;
  popup.onclick = (e) => {
    if (e.target.tagName === 'BUTTON') return;
    if (n.url) window.open(n.url, '_blank');
    popup.remove();
  };
  document.body.appendChild(popup);
  // הסרה אוטומטית אחרי 12 שניות
  setTimeout(() => popup.remove(), 12000);
}

let _newsMode = localStorage.getItem('newsMode') || 'digest';

function setNewsMode(mode) {
  _newsMode = mode;
  localStorage.setItem('newsMode', mode);
  document.querySelectorAll('.news-mode').forEach(b => {
    b.classList.toggle('active', b.dataset.mode === mode);
  });
  const hint = document.getElementById('newsModeHint');
  if (mode === 'digest') {
    hint.textContent = '⭐ Watchlist בראש · מקובץ לפי מנייה · הכי חשוב קודם';
  } else {
    hint.textContent = 'תצוגה שטוחה - כל הכותרות לפי סדר זמן';
  }
  loadNews();
}

async function loadNews() {
  // ודא שכפתורי המצב נכונים בטעינה ראשונה
  document.querySelectorAll('.news-mode').forEach(b => {
    b.classList.toggle('active', b.dataset.mode === _newsMode);
  });

  if (_newsMode === 'digest') {
    const groups = await api('/api/news/digest?limit=30&hours_back=24') || [];
    if (!groups.length) {
      document.getElementById('newsList').innerHTML = renderEmpty('📭', 'אין חדשות', 'הרץ סריקת חדשות');
      return;
    }
    document.getElementById('newsList').innerHTML = groups.map(renderDigestGroup).join('');
  } else {
    const news = await api('/api/news?limit=100&hours_back=24') || [];
    document.getElementById('newsList').innerHTML = news.length ? news.map(renderNews).join('') : renderEmpty('📭', 'אין חדשות', 'הרץ סריקת חדשות');
  }
}

function renderDigestGroup(g) {
  const symLabel = g.symbol || '🌐 כללי';
  const wlClass = g.is_watchlist ? ' wl' : '';
  const sentClass = (g.sentiment === 'bullish' || g.sentiment === 'bearish') ? ` ${g.sentiment}` : '';
  const sentLabel = {
    bullish: '📈 חיובי', bearish: '📉 שלילי', mixed: '⚖️ מעורב', neutral: '◽ ניטרלי',
  }[g.sentiment] || '◽';
  const time = new Date(g.latest_at).toLocaleString('he-IL');
  const topText = (g.top_item.text || '').replace(/\[👍 \d+ \| 💬 \d+\] /, '').slice(0, 220);
  const topHebrew = g.top_item.hebrew_translation || '';
  const hint = (!topHebrew && g.top_item.hebrew_explanation) ? g.top_item.hebrew_explanation : '';
  const sources = g.sources.map(s =>
    `<span class="digest-src ${s}">${({rss:'📺 RSS', stocktwits:'💬 StockTwits', reddit:'🔴 Reddit', twitter:'🐦 X'})[s] || s}</span>`
  ).join('');
  const extraToggle = g.headline_count > 1 ?
    `<button class="digest-expand" onclick="toggleDigestExtras(this, ${g.top_item.id})">+ ${g.headline_count - 1} כותרות נוספות</button>` : '';

  // עוד פריטים (נסתרים בהתחלה)
  const extras = g.items.filter(i => i.id !== g.top_item.id).map(i => {
    const ttime = new Date(i.fetched_at).toLocaleString('he-IL');
    const ttext = (i.text || '').replace(/\[👍 \d+ \| 💬 \d+\] /, '').slice(0, 180);
    return `<div class="digest-extra-item">
      <span class="auth">${escapeHtml(i.author)}</span>
      ${escapeHtml(ttext)}
      ${i.url ? ` · <a href="${escapeAttr(i.url)}" target="_blank" rel="noopener">קישור</a>` : ''}
      <span style="float:left;color:var(--muted)">${ttime}</span>
    </div>`;
  }).join('');

  return `
  <div class="digest-card${wlClass}${sentClass}">
    <div class="digest-header">
      <div>
        <div class="digest-sym" onclick="${g.symbol ? `openStock('${g.symbol}')` : ''}">
          ${g.is_watchlist ? '⭐ ' : ''}${symLabel}
        </div>
      </div>
      <div class="digest-meta">
        <span class="digest-sent ${g.sentiment}">${sentLabel}</span>
        <span class="digest-time">${time}</span>
      </div>
    </div>
    <div class="digest-headline">${escapeHtml(topText)}</div>
    ${topHebrew ? `<div class="digest-heb">🇮🇱 ${escapeHtml(topHebrew)}</div>` : (hint ? `<div class="digest-heb" style="border-right-color:var(--muted)">💡 ${escapeHtml(hint)}</div>` : '')}
    <div class="digest-footer">
      <div class="digest-sources">${sources}</div>
      <div>
        ${g.top_item.url ? `<a href="${escapeAttr(g.top_item.url)}" target="_blank" rel="noopener" style="color:var(--blue)">📎 מקור</a>` : ''}
        ${extraToggle}
      </div>
    </div>
    ${extras ? `<div class="digest-extras">${extras}</div>` : ''}
  </div>`;
}

function toggleDigestExtras(btn, topId) {
  const card = btn.closest('.digest-card');
  const extras = card.querySelector('.digest-extras');
  if (!extras) return;
  const showing = extras.classList.toggle('show');
  btn.textContent = showing ? '− הסתר' : btn.textContent.replace('− הסתר', '+ עוד');
  if (!showing && !btn.textContent.includes('+')) {
    // restore original count text
    const count = extras.querySelectorAll('.digest-extra-item').length;
    btn.textContent = `+ ${count} כותרות נוספות`;
  }
}

async function loadJournal() {
  const sigs = await api('/api/signals?limit=100') || [];
  document.getElementById('journalCount').textContent = sigs.length;
  const body = document.getElementById('journalBody');
  if (!sigs.length) {
    body.innerHTML = `<tr><td colspan="9" style="text-align:center;color:var(--muted);padding:30px">אין רשומות</td></tr>`;
    return;
  }
  body.innerHTML = sigs.map(s => {
    const date = new Date(s.created_at).toLocaleDateString('he-IL');
    const pnl = s.pnl_pct != null ? `<span class="${s.pnl_pct >= 0 ? 'pos' : 'neg'}">${s.pnl_pct >= 0 ? '+' : ''}${s.pnl_pct.toFixed(1)}%</span>` : '-';
    const badge = s.status === 'open' ? `<span class="badge-open">פתוח</span>` : `<span class="badge-closed">${s.status === 'closed' ? 'סגור' : 'דילוג'}</span>`;
    const starred = wlHas(s.symbol);
    return `<tr>
      <td>${date}</td>
      <td>
        <button class="star-btn ${starred?'active':''}" onclick="event.stopPropagation();wlToggle('${s.symbol}')" style="font-size:14px">${starred?'★':'☆'}</button>
        <span class="sym clickable-sym" onclick="openStock('${s.symbol}')">${s.symbol}</span>
      </td>
      <td>$${s.price.toFixed(2)}</td>
      <td>${s.rsi.toFixed(1)}</td>
      <td>x${s.volume_ratio.toFixed(1)}</td>
      <td style="color:${strengthTextColor(s.strength)}">${s.strength.toFixed(1)}</td>
      <td>$${s.target_1.toFixed(2)}</td>
      <td>$${s.stop_loss.toFixed(2)}</td>
      <td>${badge}</td>
    </tr>`;
  }).join('');
}

async function loadScans() {
  const scans = await api('/api/stats/scans?limit=30') || [];
  const body = document.getElementById('scansBody');
  if (!scans.length) {
    body.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--muted);padding:30px">אין ריצות</td></tr>`;
    return;
  }
  body.innerHTML = scans.map(sc => {
    const start = new Date(sc.started_at);
    const end = sc.finished_at ? new Date(sc.finished_at) : null;
    const dur = end ? Math.round((end - start) / 1000) + 's' : '...';
    const cls = sc.status === 'success' ? 'badge-open' : sc.status === 'failed' ? 'badge-failed' : 'badge-running';
    const label = {success:'הצלחה', failed:'כשלון', running:'רץ'}[sc.status] || sc.status;
    return `<tr>
      <td>${start.toLocaleString('he-IL')}</td>
      <td>${sc.kind === 'news' ? '📰 חדשות' : '📊 שוק'}</td>
      <td><span class="${cls}">${label}</span></td>
      <td>${sc.items_found}</td>
      <td>${dur}</td>
    </tr>`;
  }).join('');
}

async function loadHealth() {
  const h = await api('/api/system/health');
  if (!h) return;
  const hidden = '🔒 נדרשת התחברות כאדמין';
  const setText = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

  setText('cfgEnv', h.env || hidden);
  setText('cfgMode', h.trading_mode === 'paper' ? '📝 paper (סימולציה)' : (h.trading_mode === 'live' ? '💰 live' : (h.trading_mode || '--')));
  setText('cfgX', h.use_x_api === undefined ? hidden : (h.use_x_api ? '✅ פעיל' : '❌ לא מוגדר (משתמש ב-RSS)'));
  setText('cfgAI', h.use_openai === undefined ? hidden : (h.use_openai ? '✅ פעיל' : '❌ לא מוגדר'));
  setText('cfgTg', h.telegram_alerts === undefined ? hidden : (h.telegram_alerts ? '✅ פעיל' : '❌ כבוי'));

  // מצב שווקים - תמיד מוצג, גם לאנונימיים
  _marketStatus = {us: h.us_market_open, il: h.il_market_open};
  renderMarketStatus();

  const anyOpen = h.us_market_open || h.il_market_open;
  const lbl = anyOpen ? '🟢 שוק פתוח - בוט פעיל' : '🌙 שוק סגור - הבוט במנוחה';
  setText('botStatusLabel', lbl);
  setText('botStatusLabelMobile', lbl);
  const mode = `מצב: ${h.trading_mode || '--'}`;
  setText('botStatusMode', mode);
  setText('botStatusModeMobile', mode);
}

// ============= MARKET STATUS BADGE =============
let _marketStatus = {us: null, il: null};

function renderMarketStatus() {
  const u = _marketStatus.us, i = _marketStatus.il;

  // עדכון ב-sidebar (desktop)
  const sidebar = document.getElementById('sidebarMarkets');
  const sidebarRows = document.getElementById('sidebarMarketRows');
  if (sidebar && sidebarRows) {
    if (u === null || i === null) {
      sidebar.style.display = 'none';
    } else {
      sidebar.style.display = '';
      sidebarRows.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>🇺🇸 NYSE</span>
          <span style="color:${u ? 'var(--green)' : 'var(--red)'};font-weight:bold;font-size:10px">${u ? '🟢 פתוח' : '🔴 סגור'}</span>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>🇮🇱 TASE</span>
          <span style="color:${i ? 'var(--green)' : 'var(--red)'};font-weight:bold;font-size:10px">${i ? '🟢 פתוח' : '🔴 סגור'}</span>
        </div>`;
    }
  }

  // עדכון ב-topbar (mobile fallback)
  const slot = document.getElementById('marketStatusSlot');
  if (slot) {
    if (u === null || i === null) { slot.innerHTML = ''; }
    else {
      slot.innerHTML = `
        <div class="mkt-status">
          <span>${u ? '🟢' : '🔴'} 🇺🇸</span>
          <span>${i ? '🟢' : '🔴'} 🇮🇱</span>
        </div>`;
    }
  }
}

function getAdminKey() {
  let k = localStorage.getItem('adminKey');
  if (!k) {
    k = prompt('הזן Admin API Key (שמור פעם אחת בדפדפן):');
    if (k) localStorage.setItem('adminKey', k.trim());
  }
  return k;
}

async function runScan(kind) {
  // הרשאה: JWT של משתמש מחובר מספיק. אחרת ננסה Admin Key.
  const headers = Object.assign({'Content-Type': 'application/json'}, authHeader());
  const stored = localStorage.getItem('adminKey');
  if (stored) headers['X-Admin-Key'] = stored;

  // אזהרה אם סריקת שוק כששני השווקים סגורים - לא יווצרו סיגנלים חדשים
  if (kind === 'market' && _marketStatus.us === false && _marketStatus.il === false) {
    if (!confirm('⚠️ שני השווקים סגורים כרגע (NYSE + TASE).\n\nהסריקה תרוץ אבל לא יווצרו סיגנלים חדשים - הבוט נמנע מסיגנל על נתונים סטטיים.\n\nלהמשיך?')) return;
  }

  toast(`מפעיל סריקת ${kind === 'news' ? 'חדשות' : 'שוק'}...`);
  const r = await fetch(API + `/api/system/scan/${kind}`, {method: 'POST', headers});

  if (r.status === 401 || r.status === 402) {
    if (isLoggedIn()) {
      // מחובר אבל אין הרשאה - כנראה FREE plan
      const data = await r.json().catch(() => ({}));
      toast(data.detail || '❌ סריקה ידנית זמינה ל-Pro+. שדרג מנוי');
      return;
    }
    // לא מחובר - הצע התחברות או Admin Key
    if (confirm('להפעלת סריקה צריך להתחבר. ללחוץ OK להתחברות, או Cancel להזין Admin Key?')) {
      openLogin();
      return;
    }
    localStorage.removeItem('adminKey');
    const k = getAdminKey();
    if (!k) { toast('❌ בוטל'); return; }
    return runScan(kind);
  }
  if (r.status === 429) { toast('❌ יותר מדי בקשות - חכה דקה'); return; }
  if (!r.ok) { toast('❌ נכשל - בדוק logs'); return; }

  toast('✅ הסריקה רצה ברקע');
  // רענון אוטומטי של הדשבורד אחרי 8 שניות (חדשות) / 90 שניות (שוק)
  const refreshDelay = kind === 'news' ? 8000 : 90000;
  setTimeout(() => {
    toast(`🔄 מרענן ${kind === 'news' ? 'חדשות' : 'סיגנלים'}...`);
    if (kind === 'news') {
      loadNews();
      if (document.querySelector('.page.active')?.id === 'page-dashboard') loadDashboard();
    } else {
      loadDashboard();
      loadSignals();
    }
  }, refreshDelay);
}

// ============= STOCK DETAIL MODAL =============
function toggleDisclaimer() {
  document.getElementById('disclaimerFull').classList.toggle('show');
}

function closeStockModal() {
  document.getElementById('stockModal').classList.remove('show');
  document.getElementById('tvChart').src = 'about:blank';
  document.body.style.overflow = '';
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeStockModal();
});

function fmtNum(n) {
  if (n == null) return '—';
  if (Math.abs(n) >= 1e12) return (n/1e12).toFixed(2) + 'T';
  if (Math.abs(n) >= 1e9)  return (n/1e9).toFixed(2) + 'B';
  if (Math.abs(n) >= 1e6)  return (n/1e6).toFixed(2) + 'M';
  if (Math.abs(n) >= 1e3)  return (n/1e3).toFixed(2) + 'K';
  return n.toLocaleString('en-US');
}
function fmtPct(n) { return n == null ? '—' : (n*100).toFixed(2) + '%'; }
function fmtMoney(n) { return n == null ? '—' : '$' + n.toFixed(2); }

function row(label, val, cls='') {
  return `<div class="info-row"><span class="info-label">${label}</span><span class="info-val ${cls}">${val}</span></div>`;
}

function buildTvUrl(symbol, interval, range) {
  // TradingView Advanced Chart - widget חינמי, תומך בכל הזמנים
  const params = new URLSearchParams({
    symbol: symbol,
    interval: interval,           // 1, 5, 15, 60, D, W, M
    range: range,                 // 1D, 5D, 1M, 3M, 6M, 12M, 60M, ALL
    theme: 'dark',
    style: '1',                   // 1=candles
    locale: 'he_IL',
    enable_publishing: 'false',
    allow_symbol_change: 'true',
    save_image: 'false',
    studies: '[]',
    backgroundColor: '#080c14',
    gridColor: '#1e2d3d',
    hide_side_toolbar: 'false',
    withdateranges: 'true',
  });
  return `https://s.tradingview.com/widgetembed/?${params.toString()}`;
}

function setTvFrame(symbol, interval, range) {
  document.getElementById('tvChart').src = buildTvUrl(symbol, interval, range);
}

async function loadStockNews(symbol) {
  const target = document.getElementById('infoStockNews');
  if (!target) return;
  // פילטור בשרת - מהיר ויעיל יותר
  const news = await api(`/api/news?symbol=${encodeURIComponent(symbol)}&limit=10&hours_back=72`) || [];

  if (!news.length) {
    target.innerHTML = '<div style="text-align:center;color:var(--muted);padding:12px;font-size:11px">אין חדשות אחרונות על ' + symbol + '</div>';
    return;
  }

  target.innerHTML = news.map(n => {
    const text = (n.text || '').replace(/\[👍 \d+ \| 💬 \d+\] /, '').slice(0, 180);
    const heb = n.hebrew_translation || n.hebrew_explanation || '';
    const time = n.fetched_at ? timeAgo(n.fetched_at) : '';
    const srcLabel = ({rss:'📺', stocktwits:'💬', reddit:'🔴', twitter:'🐦'})[n.source] || '📰';
    return `<div style="padding:10px;border-bottom:1px solid var(--border);font-size:12px">
      <div style="display:flex;justify-content:space-between;gap:8px;margin-bottom:4px">
        <span style="font-weight:bold;color:var(--blue);font-size:11px">${srcLabel} ${escapeHtml(n.author || '')}</span>
        <span style="color:var(--muted);font-size:10px">${time}</span>
      </div>
      <div style="line-height:1.4">${escapeHtml(text)}</div>
      ${heb ? `<div style="margin-top:4px;font-size:11px;color:#bcc7d6;border-right:2px solid var(--blue);padding:3px 6px;background:rgba(0,212,255,0.04);border-radius:0 4px 4px 0">🇮🇱 ${escapeHtml(heb)}</div>` : ''}
      ${n.url ? `<a href="${escapeAttr(n.url)}" target="_blank" rel="noopener" style="color:var(--blue);font-size:10px;text-decoration:none">📎 קישור →</a>` : ''}
    </div>`;
  }).join('');
}

async function openStock(symbol) {
  symbol = (symbol || '').toUpperCase();
  const modal = document.getElementById('stockModal');
  modal.classList.add('show');
  document.body.style.overflow = 'hidden';

  // עדכון כוכב מועדפים בכותרת ה-modal
  const starBtn = document.getElementById('mStarBtn');
  if (starBtn) {
    const update = () => {
      const inWl = wlHas(symbol);
      starBtn.textContent = inWl ? '★' : '☆';
      starBtn.classList.toggle('active', inWl);
      starBtn.title = inWl ? 'הסר מ-Watchlist' : 'הוסף ל-Watchlist';
    };
    update();
    starBtn.onclick = async () => {
      await wlToggle(symbol);
      update();
    };
  }

  // אתחול בסיסי
  document.getElementById('mSymbol').textContent = symbol;
  document.getElementById('mName').textContent = 'טוען...';
  document.getElementById('mPrice').textContent = '--';
  document.getElementById('mChange').textContent = '';
  ['infoGeneral','infoTrading','infoFundamentals','infoAnalysts','infoStockNews'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = '<div class="modal-loading">טוען...</div>';
  });
  document.getElementById('infoSummary').textContent = '';
  document.getElementById('finvizImg').src = '';
  document.getElementById('finvizLink').href = `https://finviz.com/quote.ashx?t=${symbol}`;

  // טען חדשות פר-סמל במקביל
  loadStockNews(symbol);

  // גרף - ברירת מחדל 6 חודשים יומי
  document.querySelectorAll('.tf-btn').forEach(b => b.classList.remove('active'));
  const defaultBtn = document.querySelector('.tf-btn[data-int="D"][data-range="6M"]');
  if (defaultBtn) defaultBtn.classList.add('active');
  setTvFrame(symbol, 'D', '6M');

  // טעינת נתוני yfinance
  const data = await api(`/api/stocks/${symbol}`);
  if (!data) {
    document.getElementById('mName').textContent = '⚠️ שגיאה בטעינת נתונים';
    return;
  }

  document.getElementById('mName').textContent = data.name || symbol;
  if (data.price != null) {
    document.getElementById('mPrice').textContent = fmtMoney(data.price);
  }
  if (data.day_change_pct != null) {
    const sign = data.day_change_pct >= 0 ? '+' : '';
    const ch = document.getElementById('mChange');
    ch.textContent = `${sign}${data.day_change_pct.toFixed(2)}%`;
    ch.className = 'modal-change ' + (data.day_change_pct >= 0 ? 'pos' : 'neg');
  }

  // כללי
  document.getElementById('infoGeneral').innerHTML = [
    row('שם מלא', data.name || '—'),
    row('בורסה', data.exchange || '—'),
    row('סקטור', data.sector || '—'),
    row('תחום', data.industry || '—'),
    row('מדינה', data.country || '—'),
  ].join('');
  document.getElementById('infoSummary').textContent = data.summary || '';
  const ws = document.getElementById('infoWebsite');
  if (data.website) {
    ws.href = data.website;
    ws.style.display = '';
    ws.textContent = '🌐 ' + data.website.replace(/^https?:\/\//, '');
  } else {
    ws.style.display = 'none';
  }

  // מסחר
  document.getElementById('infoTrading').innerHTML = [
    row('מחיר נוכחי', fmtMoney(data.price)),
    row('סגירה קודמת', fmtMoney(data.previous_close)),
    row('שיא יום', fmtMoney(data.day_high)),
    row('שפל יום', fmtMoney(data.day_low)),
    row('שיא 52 שב\'', fmtMoney(data.fifty_two_week_high)),
    row('שפל 52 שב\'', fmtMoney(data.fifty_two_week_low)),
    row('נפח יום', fmtNum(data.volume)),
    row('נפח ממוצע', fmtNum(data.avg_volume)),
    row('שווי שוק', '$' + fmtNum(data.market_cap)),
  ].join('');

  // יסודות
  document.getElementById('infoFundamentals').innerHTML = [
    row('P/E (שולל)', data.pe_ratio != null ? data.pe_ratio.toFixed(2) : '—'),
    row('P/E (עתידי)', data.forward_pe != null ? data.forward_pe.toFixed(2) : '—'),
    row('EPS', fmtMoney(data.eps)),
    row('Beta', data.beta != null ? data.beta.toFixed(2) : '—'),
    row('תשואת דיבידנד', fmtPct(data.dividend_yield)),
    row('שולי רווח', fmtPct(data.profit_margin), data.profit_margin >= 0 ? 'pos' : 'neg'),
    row('הכנסות שנתיות', '$' + fmtNum(data.revenue)),
    row('צמיחת הכנסות', fmtPct(data.revenue_growth), data.revenue_growth >= 0 ? 'pos' : 'neg'),
    row('צמיחת רווחים', fmtPct(data.earnings_growth), data.earnings_growth >= 0 ? 'pos' : 'neg'),
    row('חוב/הון', data.debt_to_equity != null ? data.debt_to_equity.toFixed(2) : '—'),
    row('ROE', fmtPct(data.return_on_equity)),
  ].join('');

  // אנליסטים
  const recMap = {strong_buy: '🟢 קנייה חזקה', buy: '🟢 קנייה', hold: '🟡 החזק', sell: '🔴 מכירה', strong_sell: '🔴 מכירה חזקה'};
  document.getElementById('infoAnalysts').innerHTML = [
    row('המלצה', recMap[data.recommendation] || data.recommendation || '—'),
    row('מספר אנליסטים', data.analyst_count != null ? data.analyst_count : '—'),
    row('יעד ממוצע', fmtMoney(data.target_mean_price)),
    row('יעד גבוה', fmtMoney(data.target_high_price)),
    row('יעד נמוך', fmtMoney(data.target_low_price)),
    row('פוטנציאל מהמחיר',
        (data.target_mean_price && data.price)
          ? fmtPct((data.target_mean_price - data.price) / data.price)
          : '—',
        (data.target_mean_price && data.price && data.target_mean_price > data.price) ? 'pos' : 'neg'),
  ].join('');

  // Finviz snapshot
  document.getElementById('finvizImg').src = data.finviz_chart_url + `&_=${Date.now()}`;
}

// ============= PLANS =============
async function loadPlans() {
  const grid = document.getElementById('plansGrid');
  const plans = await api('/api/me/plans/all') || [];
  let myPlan = null;
  if (isLoggedIn()) myPlan = await api('/api/me/plan');

  const planColors = {free:'#4a5568', pro:'#00d4ff', vip:'#ffd700'};
  grid.innerHTML = plans.map(p => {
    const isCurrent = myPlan && myPlan.name === p.name;
    const c = planColors[p.name] || '#4a5568';
    const price = p.monthly_price_ils === 0 ? 'חינם' : `₪${p.monthly_price_ils}/חודש`;
    const wl = p.watchlist_max === 0 ? 'ללא הגבלה' : p.watchlist_max;
    return `<div class="signal-card" style="border-right:3px solid ${c};${isCurrent?'box-shadow:0 0 0 2px '+c+' inset;':''}">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
        <div style="font-size:20px;font-weight:bold;color:${c}">${p.display_name}</div>
        ${isCurrent ? '<span class="plan-badge" style="background:'+c+';color:#080c14">המנוי שלך</span>' : ''}
      </div>
      <div style="font-size:28px;font-weight:bold;margin-bottom:14px">${price}</div>
      <ul style="list-style:none;padding:0;font-size:13px;line-height:2;color:var(--text)">
        <li>✓ Watchlist: ${wl} מניות</li>
        <li>${p.can_manual_scan?'✓':'✗'} סריקה ידנית</li>
        <li>${p.can_custom_strategy?'✓':'✗'} אסטרטגיות מותאמות</li>
        <li>${p.can_export?'✓':'✗'} ייצוא לאקסל</li>
        <li>✓ היסטוריית התראות: ${p.notifications_history_days} יום</li>
      </ul>
      ${isCurrent ? '' : `<button class="btn btn-blue" style="width:100%;margin-top:14px" onclick="upgradeRequest('${p.name}')">${p.monthly_price_ils === 0 ? 'בחר תוכנית' : 'שדרג עכשיו'}</button>`}
    </div>`;
  }).join('');
}

async function upgradeRequest(planName) {
  if (!isLoggedIn()) { openLogin(); return; }
  if (planName === 'free') { toast('כבר ב-FREE'); return; }

  toast('פותח דף תשלום...');
  // בדוק אם Stripe מוגדר
  const status = await api('/api/billing/status');
  if (!status || !status.stripe_enabled) {
    // Stripe לא מוגדר - חזרה לבקשה ידנית
    const subject = encodeURIComponent(`בקשת שדרוג ל-${planName}`);
    const body = encodeURIComponent(`היי,\nאני רוצה לשדרג את החשבון שלי ל-${planName}.\nהמייל שלי: ${getUser()?.email || ''}`);
    window.location.href = `mailto:${status?.contact_email || 'admin@tradingpro.app'}?subject=${subject}&body=${body}`;
    return;
  }

  // יצירת Checkout Session
  try {
    const r = await fetch(API + '/api/billing/checkout', {
      method: 'POST',
      headers: Object.assign({'Content-Type':'application/json'}, authHeader()),
      body: JSON.stringify({plan: planName}),
    });
    const data = await r.json();
    if (!r.ok) {
      toast(data.detail || 'שגיאה ביצירת תשלום');
      return;
    }
    if (data.url) {
      // הפניה ל-Stripe Checkout
      window.location.href = data.url;
    } else if (data.mode === 'manual') {
      // fallback
      alert(data.message || 'יצירת קשר ידנית - שלח מייל ל-admin');
    }
  } catch (e) {
    toast('שגיאה: ' + e.message);
  }
}

// ============= ACCOUNT =============
async function loadAccount() {
  const gate = document.getElementById('accountAuthGate');
  const content = document.getElementById('accountContent');
  if (!isLoggedIn()) {
    if (gate) gate.style.display = '';
    if (content) content.style.display = 'none';
    return;
  }
  if (gate) gate.style.display = 'none';
  if (content) content.style.display = '';

  const u = await api('/api/auth/me');
  if (!u) return;
  document.getElementById('acEmail').textContent = u.email;
  document.getElementById('acName').value = u.full_name || '';
  document.getElementById('acPlan').textContent = (u.plan || 'free').toUpperCase();
  document.getElementById('acVerified').textContent = u.email_verified
    ? '✅ מאומת'
    : '⚠️ לא אומת — נשלח לך מייל בעת ההרשמה';
  document.getElementById('acJoined').textContent = new Date(u.created_at).toLocaleDateString('he-IL');
}

async function acSaveName() {
  const name = document.getElementById('acName').value.trim();
  const r = await fetch(API + '/api/auth/me', {
    method: 'PATCH',
    headers: Object.assign({'Content-Type':'application/json'}, authHeader()),
    body: JSON.stringify({full_name: name}),
  });
  if (r.ok) {
    toast('השם עודכן');
    const u = await api('/api/auth/me');
    if (u) { setUser(u); }
  } else {
    toast('שגיאה בעדכון');
  }
}

async function acChangePassword() {
  const current = document.getElementById('acCurrentPwd').value;
  const next = document.getElementById('acNewPwd').value;
  if (next.length < 8) { toast('סיסמה חדשה - 8 תווים לפחות'); return; }
  const r = await fetch(API + '/api/auth/change-password', {
    method: 'POST',
    headers: Object.assign({'Content-Type':'application/json'}, authHeader()),
    body: JSON.stringify({current_password: current, new_password: next}),
  });
  if (r.ok) {
    toast('הסיסמה עודכנה');
    document.getElementById('acCurrentPwd').value = '';
    document.getElementById('acNewPwd').value = '';
  } else {
    const e = await r.json();
    toast(e.detail || 'עדכון נכשל');
  }
}

async function acDeleteAccount() {
  if (!confirm('האם אתה בטוח? פעולה זו לא ניתנת לביטול. תאשר שוב למחיקה.')) return;
  if (!confirm('אישור אחרון - למחוק לצמיתות את החשבון, ה-Watchlist וההתראות?')) return;
  const r = await fetch(API + '/api/auth/me', {method: 'DELETE', headers: authHeader()});
  if (r.ok) {
    toast('החשבון נמחק');
    setToken(null); setUser(null);
    window.location.hash = '';
    showPage('dashboard', null);
  } else {
    toast('מחיקה נכשלה');
  }
}

// =========== FORGOT PASSWORD + RESET (via URL hash) =============
async function forgotPassword() {
  const email = prompt('הזן כתובת מייל לקבלת קישור איפוס:');
  if (!email) return;
  const r = await fetch(API + '/api/auth/forgot-password', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({email: email.trim().toLowerCase()}),
  });
  if (r.ok) {
    toast('אם הכתובת רשומה - יישלח אליה מייל');
  } else {
    toast('שגיאה. נסה שוב.');
  }
}

// טיפול בחזרה מ-Stripe Checkout
async function handlePostPayment() {
  const params = new URLSearchParams(window.location.search);
  const upgrade = params.get('upgrade');
  if (!upgrade) return;

  // נקה את ה-URL כדי שזה לא יתבצע שוב ברענון
  history.replaceState(null, '', window.location.pathname);

  if (upgrade === 'cancel') {
    setTimeout(() => toast('תשלום בוטל'), 800);
    return;
  }

  if (upgrade === 'success') {
    const sessionId = params.get('session_id');
    if (!sessionId) { toast('חוזר מהתשלום...'); return; }

    // ממתין מעט שהsession יעודכן ב-Stripe
    setTimeout(async () => {
      const r = await api('/api/billing/verify-session?session_id=' + encodeURIComponent(sessionId));
      if (r && r.ok) {
        alert(`🎉 ברוך הבא ל-${(r.plan || '').toUpperCase()}!\n\nהחשבון שלך שודרג בהצלחה.\nהפיצ'רים החדשים זמינים מיד.`);
        // רענון משתמש
        await validateSession();
        loadDashboard();
      } else {
        toast(r?.message || 'תשלום מאושר אך השדרוג טרם הופעל - יישלח אישור במייל');
      }
    }, 1500);
  }
}

// פענוח hash בטעינה - תמיכה ב-reset-password ו-verify-email
async function handleAuthHash() {
  const hash = window.location.hash || '';
  if (hash.startsWith('#reset-password=')) {
    const token = hash.slice('#reset-password='.length);
    const newPwd = prompt('הזן סיסמה חדשה (8 תווים לפחות):');
    if (!newPwd || newPwd.length < 8) { toast('סיסמה לא תקינה'); return; }
    const r = await fetch(API + '/api/auth/reset-password', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({token, new_password: newPwd}),
    });
    if (r.ok) {
      toast('הסיסמה אופסה - אפשר להתחבר');
      window.location.hash = '';
      openLogin();
    } else {
      const e = await r.json();
      toast(e.detail || 'איפוס נכשל');
    }
  } else if (hash.startsWith('#verify-email=')) {
    const token = hash.slice('#verify-email='.length);
    const r = await fetch(API + '/api/auth/verify-email?token=' + encodeURIComponent(token), {method: 'POST'});
    if (r.ok) {
      toast('✅ המייל אומת בהצלחה');
      window.location.hash = '';
      if (isLoggedIn()) validateSession();
    } else {
      const e = await r.json();
      toast(e.detail || 'אימות נכשל');
    }
  }
}

// ============= ANALYTICS SUB-TABS =============
let _anCurrentTab = 'performance';

function setAnTab(tab) {
  _anCurrentTab = tab;
  document.querySelectorAll('.sub-tab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.getElementById('anTabPerformance').style.display = tab === 'performance' ? '' : 'none';
  document.getElementById('anTabAnalysts').style.display = tab === 'analysts' ? '' : 'none';
  if (tab === 'performance') loadAnalytics();
  if (tab === 'analysts') loadAnalysts(7);
}

// ============= ANALYSTS =============
let _anDays = 7;

async function loadAnalysts(days) {
  if (days) {
    _anDays = days;
    // עדכון UI של כפתורי תקופה
    ['7','14','30'].forEach(d => {
      const btn = document.getElementById('anDaysBtn' + d);
      if (btn) {
        const active = parseInt(d) === days;
        btn.classList.toggle('btn-blue', active);
        btn.style.background = active ? '' : '#1a2744';
      }
    });
  }
  const target = document.getElementById('analystsList');
  if (!target) return;
  target.innerHTML = '<div style="text-align:center;padding:30px;color:var(--muted)">⏳ אוסף המלצות אנליסטים... (עד 30 שניות)</div>';
  const recs = await api(`/api/analysts/recent?days=${_anDays}&limit=60`) || [];
  if (!recs.length) {
    target.innerHTML = '<div style="text-align:center;padding:30px;color:var(--muted)"><div style="font-size:48px">🎯</div>אין המלצות אנליסטים בטווח הזה</div>';
    return;
  }

  // קיבוץ לפי סמל
  const bySymbol = {};
  for (const r of recs) {
    if (!bySymbol[r.symbol]) bySymbol[r.symbol] = [];
    bySymbol[r.symbol].push(r);
  }
  const sorted = Object.entries(bySymbol).sort((a, b) => b[1].length - a[1].length);

  target.innerHTML = sorted.map(([sym, list]) => {
    const starred = wlHas(sym);
    return `<div class="signal-card" style="margin-bottom:10px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
        <div style="display:flex;gap:8px;align-items:center">
          <button class="star-btn ${starred?'active':''}" onclick="event.stopPropagation();wlToggle('${sym}')" style="font-size:18px">${starred?'★':'☆'}</button>
          <span class="signal-symbol clickable-sym" onclick="openStock('${sym}')">${sym}</span>
          <span style="color:var(--muted);font-size:11px">${list.length} המלצות</span>
        </div>
      </div>
      ${list.map(r => {
        const ts = new Date(r.date).toLocaleDateString('he-IL');
        const grade = r.to_grade || r.action || '';
        const color = /buy|outperform|overweight|positive|strong|upgrade/i.test(grade) ? 'var(--green)' :
                      /sell|underperform|underweight|negative|downgrade/i.test(grade) ? 'var(--red)' :
                      'var(--muted)';
        return `<div style="font-size:12px;padding:6px 0;border-top:1px solid var(--border);display:flex;justify-content:space-between;gap:10px">
          <div><b>${escapeHtml(r.firm||'?')}</b>: <span style="color:${color}">${escapeHtml(grade||'?')}</span>
          ${r.from_grade ? ` <span style="color:var(--muted)">(היה: ${escapeHtml(r.from_grade)})</span>` : ''}
          </div>
          <div style="color:var(--muted);font-size:11px;white-space:nowrap">${ts}</div>
        </div>`;
      }).join('')}
    </div>`;
  }).join('');
}

// ============= AI CHAT =============
async function aiAsk(question, signalId, symbol) {
  const r = await fetch(API + '/api/ai/ask', {
    method: 'POST',
    headers: Object.assign({'Content-Type':'application/json'}, authHeader()),
    body: JSON.stringify({question, signal_id: signalId, symbol}),
  });
  if (!r.ok) {
    const e = await r.json().catch(()=>({}));
    return {answer: e.detail || 'שגיאה בבקשה', source: 'error'};
  }
  return await r.json();
}

async function sendAiQuestion() {
  if (!isLoggedIn()) { toast('נדרשת התחברות'); openLogin(); return; }
  const input = document.getElementById('aiInput');
  const q = (input.value || '').trim();
  if (!q) return;

  const log = document.getElementById('aiChatLog');
  // הוסף שאלת המשתמש
  log.innerHTML += `<div class="ai-msg user"><b>אתה:</b> ${escapeHtml(q)}</div>`;
  log.innerHTML += `<div class="ai-msg ai" id="aiPending"><b>AI:</b> <i>חושב...</i></div>`;
  log.scrollTop = log.scrollHeight;
  input.value = '';

  const sym = (document.getElementById('mSymbol')?.textContent || '').trim();
  const result = await aiAsk(q, null, sym);

  document.getElementById('aiPending').remove();
  const tag = result.source === 'openai' ? '🤖' : '📊';
  log.innerHTML += `<div class="ai-msg ai"><b>${tag} AI:</b><br>${escapeHtml(result.answer).replace(/\n/g,'<br>')}</div>`;
  log.scrollTop = log.scrollHeight;
}

// ============= ANALYTICS =============
async function loadAnalytics(force) {
  const gate = document.getElementById('analyticsAuthGate');
  const content = document.getElementById('analyticsContent');
  if (!isLoggedIn()) {
    gate.style.display = ''; content.style.display = 'none'; return;
  }
  gate.style.display = 'none'; content.style.display = '';

  // טעינה - הצג spinner
  document.getElementById('anStats').innerHTML = '<div class="stat-card blue" style="grid-column:1/-1;text-align:center"><div class="stat-icon">⏳</div><div class="stat-label">טוען נתוני שוק...</div></div>';

  const data = await api('/api/me/analytics');
  if (!data) { toast('שגיאה בטעינת הנתונים'); return; }

  if (data.total_symbols === 0) {
    document.getElementById('anStats').innerHTML = '<div class="stat-card" style="grid-column:1/-1;text-align:center;padding:30px"><div class="stat-icon">📭</div><div class="stat-label">ה-Watchlist ריק. הוסף מניות כדי לראות ניתוח.</div></div>';
    document.getElementById('anHighlights').innerHTML = '';
    document.getElementById('anTable').innerHTML = '';
    return;
  }

  // Stats cards
  const cards = [
    {icon:'📊', value: data.total_symbols, label: 'מניות', color:'blue', sub:'במעקב'},
    {icon:'📅', value: fmtPct(data.avg_day_change_pct), label: 'ממוצע יומי', color: pctColor(data.avg_day_change_pct), sub:'24 שעות'},
    {icon:'📆', value: fmtPct(data.avg_week_change_pct), label: 'ממוצע שבועי', color: pctColor(data.avg_week_change_pct), sub:'5 ימי מסחר'},
    {icon:'🗓', value: fmtPct(data.avg_month_change_pct), label: 'ממוצע חודשי', color: pctColor(data.avg_month_change_pct), sub:'21 ימי מסחר'},
  ];
  document.getElementById('anStats').innerHTML = cards.map(c => `
    <div class="stat-card ${c.color}">
      <div class="stat-icon">${c.icon}</div>
      <div class="stat-number">${c.value}</div>
      <div class="stat-label">${c.label}</div>
      <div class="stat-change">${c.sub}</div>
    </div>`).join('');

  // Best / worst
  const hl = [];
  if (data.best_day) {
    hl.push(`<div class="signal-card" style="border-right:3px solid var(--green)" onclick="openStock('${data.best_day.symbol}')">
      <div style="display:flex;justify-content:space-between"><div><b style="color:var(--green)">🏆 הטוב ביותר היום</b><br><span class="signal-symbol clickable-sym">${data.best_day.symbol}</span> ${escapeHtml(data.best_day.name||'')}</div>
      <div style="text-align:left"><div class="wl-price pos">${fmtPct(data.best_day.day_change_pct)}</div><div style="color:var(--muted);font-size:11px">$${data.best_day.price}</div></div></div>
    </div>`);
  }
  if (data.worst_day && data.worst_day.symbol !== data.best_day?.symbol) {
    hl.push(`<div class="signal-card" style="border-right:3px solid var(--red)" onclick="openStock('${data.worst_day.symbol}')">
      <div style="display:flex;justify-content:space-between"><div><b style="color:var(--red)">⚠️ החלש ביותר היום</b><br><span class="signal-symbol clickable-sym">${data.worst_day.symbol}</span> ${escapeHtml(data.worst_day.name||'')}</div>
      <div style="text-align:left"><div class="wl-price neg">${fmtPct(data.worst_day.day_change_pct)}</div><div style="color:var(--muted);font-size:11px">$${data.worst_day.price}</div></div></div>
    </div>`);
  }
  document.getElementById('anHighlights').innerHTML = hl.join('') || '<div style="text-align:center;color:var(--muted);padding:20px">אין נתונים</div>';

  // Table
  const sorted = [...data.items].sort((a,b) => (b.day_change_pct ?? -999) - (a.day_change_pct ?? -999));
  document.getElementById('anTable').innerHTML = sorted.map(it => {
    if (it.error) return `<tr><td><span class="sym clickable-sym" onclick="openStock('${it.symbol}')">${it.symbol}</span></td><td colspan="7" style="color:var(--red);font-size:11px">${escapeHtml(it.error)}</td></tr>`;
    const ma = it.above_ma20 === null ? '—' : (it.above_ma20 ? '<span style="color:var(--green)">▲</span>' : '<span style="color:var(--red)">▼</span>');
    const rsiCls = it.rsi == null ? '' : (it.rsi > 70 ? 'neg' : (it.rsi < 30 ? 'pos' : ''));
    return `<tr>
      <td><span class="sym clickable-sym" onclick="openStock('${it.symbol}')">${it.symbol}</span></td>
      <td style="font-size:11px;color:var(--muted)">${escapeHtml((it.name||'').slice(0,28))}</td>
      <td>$${(it.price||0).toFixed(2)}</td>
      <td class="${pctClass(it.day_change_pct)}">${fmtPct(it.day_change_pct)}</td>
      <td class="${pctClass(it.week_change_pct)}">${fmtPct(it.week_change_pct)}</td>
      <td class="${pctClass(it.month_change_pct)}">${fmtPct(it.month_change_pct)}</td>
      <td class="${rsiCls}">${it.rsi != null ? it.rsi.toFixed(1) : '—'}</td>
      <td>${ma}</td>
    </tr>`;
  }).join('');
}

function fmtPct(v) {
  if (v == null) return '—';
  const sign = v >= 0 ? '+' : '';
  return sign + v.toFixed(2) + '%';
}
function pctColor(v) {
  if (v == null) return 'blue';
  return v >= 0 ? 'green' : 'red';
}
function pctClass(v) {
  if (v == null) return '';
  return v >= 0 ? 'pos' : 'neg';
}

// ============= ADMIN =============
async function loadAdmin() {
  const gate = document.getElementById('adminAuthGate');
  const content = document.getElementById('adminContent');
  if (!getUser()?.is_admin) {
    if (gate) gate.style.display = '';
    if (content) content.style.display = 'none';
    return;
  }
  if (gate) gate.style.display = 'none';
  if (content) content.style.display = '';
  await Promise.all([loadAdminStats(), loadAdminUsers()]);
}

async function loadAdminStats() {
  const s = await api('/api/admin/stats');
  if (!s) return;
  const cards = [
    {icon:'👥', value:s.total_users, label:`משתמשים סה"כ`, color:'blue', sub:`${s.active_users} פעילים`},
    {icon:'🆕', value:s.new_today, label:'נרשמו היום', color:'green', sub:`${s.new_week} השבוע`},
    {icon:'💰', value:`₪${s.total_revenue_ils}`, label:'הכנסה חודשית', color:'gold', sub:`${s.pro_users + s.vip_users} משלמים`},
    {icon:'💎', value:`${s.pro_users}/${s.vip_users}`, label:'Pro / VIP', color:'red', sub:`${s.free_users} חינם`},
  ];
  document.getElementById('adminStats').innerHTML = cards.map(c => `
    <div class="stat-card ${c.color}">
      <div class="stat-icon">${c.icon}</div>
      <div class="stat-number">${c.value}</div>
      <div class="stat-label">${c.label}</div>
      <div class="stat-change">${c.sub}</div>
    </div>`).join('');
}

async function loadAdminUsers() {
  const users = await api('/api/admin/users');
  const tbody = document.getElementById('adminUsersBody');
  if (!users || !users.length) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--muted)">אין משתמשים</td></tr>';
    return;
  }
  tbody.innerHTML = users.map(u => {
    const date = new Date(u.created_at).toLocaleDateString('he-IL');
    const lastLogin = u.last_login_at ? new Date(u.last_login_at).toLocaleDateString('he-IL') : '—';
    return `<tr>
      <td>${u.id}</td>
      <td style="direction:ltr;text-align:left;font-size:11px">${escapeHtml(u.email)}${u.is_admin?' 👑':''}</td>
      <td>${escapeHtml(u.full_name || '—')}</td>
      <td>
        <select onchange="adminSetPlan(${u.id}, this.value)" style="background:#080c14;border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
          <option value="free" ${u.plan==='free'?'selected':''}>free</option>
          <option value="pro" ${u.plan==='pro'?'selected':''}>pro</option>
          <option value="vip" ${u.plan==='vip'?'selected':''}>vip</option>
        </select>
      </td>
      <td><span class="${u.is_active?'badge-open':'badge-closed'}" style="cursor:pointer" onclick="adminToggleActive(${u.id}, ${!u.is_active})">${u.is_active?'פעיל':'מושבת'}</span></td>
      <td style="font-size:11px">${date}</td>
      <td style="font-size:11px">${lastLogin}</td>
      <td>${u.watchlist_count}</td>
      <td><button onclick="adminDelete(${u.id})" style="background:none;border:none;color:var(--red);cursor:pointer;font-size:14px" title="מחק">🗑</button></td>
    </tr>`;
  }).join('');
}

async function adminSetPlan(uid, plan) {
  const r = await fetch(API + `/api/admin/users/${uid}`, {
    method: 'PATCH',
    headers: Object.assign({'Content-Type':'application/json'}, authHeader()),
    body: JSON.stringify({plan}),
  });
  if (r.ok) { toast(`התוכנית עודכנה ל-${plan}`); loadAdmin(); }
  else toast('עדכון נכשל');
}

async function adminToggleActive(uid, newState) {
  const r = await fetch(API + `/api/admin/users/${uid}`, {
    method: 'PATCH',
    headers: Object.assign({'Content-Type':'application/json'}, authHeader()),
    body: JSON.stringify({is_active: newState}),
  });
  if (r.ok) { toast(newState?'הופעל':'הושבת'); loadAdmin(); }
}

async function adminDelete(uid) {
  if (!confirm('למחוק את המשתמש לצמיתות?')) return;
  const r = await fetch(API + `/api/admin/users/${uid}`, {method:'DELETE', headers: authHeader()});
  if (r.ok) { toast('נמחק'); loadAdmin(); }
  else { const e = await r.json(); toast(e.detail || 'מחיקה נכשלה'); }
}

// ============= NOTIFICATIONS =============
let _lastSeenId = parseInt(localStorage.getItem('lastSeenNotifId') || '0');
let _bellOpen = false;
const _baseTitle = document.title;

function toggleBell(e) {
  if (e) e.stopPropagation();
  _bellOpen = !_bellOpen;
  const dd = document.getElementById('bellDropdown');
  dd.classList.toggle('show', _bellOpen);
  if (_bellOpen) loadNotifications();
}

document.addEventListener('click', () => {
  if (_bellOpen) { _bellOpen = false; document.getElementById('bellDropdown').classList.remove('show'); }
});

function timeAgo(iso) {
  const d = new Date(iso);
  const sec = Math.floor((Date.now() - d.getTime()) / 1000);
  if (sec < 60) return 'כעת';
  if (sec < 3600) return `לפני ${Math.floor(sec/60)} דק'`;
  if (sec < 86400) return `לפני ${Math.floor(sec/3600)} שע'`;
  return d.toLocaleDateString('he-IL');
}

async function loadNotifications() {
  const items = await api('/api/notifications?limit=30') || [];
  const list = document.getElementById('bellList');
  if (!items.length) {
    list.innerHTML = '<div class="notif-empty">📭 אין התראות עדיין<br><span style="font-size:11px">סיגנלים חדשים יופיעו כאן אוטומטית</span></div>';
    return;
  }
  list.innerHTML = items.map(n => `
    <div class="notif-item ${n.read_at?'':'unread'}" onclick="onNotifClick(${n.id}, ${n.symbol?`'${n.symbol}'`:'null'})">
      <div class="notif-icon">${n.icon || '🔔'}</div>
      <div class="notif-body">
        <div class="notif-title">${escapeHtml(n.title)}</div>
        <div class="notif-msg">${escapeHtml(n.message)}</div>
        <div class="notif-time">${timeAgo(n.created_at)}</div>
      </div>
    </div>`).join('');
}

async function onNotifClick(nid, sym) {
  try { await fetch(API + `/api/notifications/${nid}/read`, {method:'POST'}); } catch(e){}
  if (sym) openStock(sym);
  refreshBadge();
  if (_bellOpen) loadNotifications();
}

async function markAllRead() {
  await fetch(API + '/api/notifications/read-all', {method:'POST'});
  refreshBadge();
  loadNotifications();
}

function ensureBrowserNotifyPermission() {
  if (!('Notification' in window)) return;
  if (Notification.permission === 'default') {
    Notification.requestPermission();
  }
}

function showBrowserNotification(n) {
  if (!('Notification' in window) || Notification.permission !== 'granted') return;
  try {
    const notif = new Notification(n.title, {
      body: n.message,
      icon: '/static/favicon.ico',
      tag: 'sig-' + n.id,
      silent: false,
    });
    notif.onclick = () => { window.focus(); if (n.symbol) openStock(n.symbol); notif.close(); };
  } catch(e) {}
}

async function refreshBadge() {
  const r = await api('/api/notifications/count');
  const badge = document.getElementById('bellBadge');
  const count = (r && r.unread) || 0;
  if (count > 0) {
    badge.textContent = count > 99 ? '99+' : count;
    badge.style.display = '';
    document.title = `(${count}) ${_baseTitle}`;
  } else {
    badge.style.display = 'none';
    document.title = _baseTitle;
  }
}

async function pollNotifications() {
  const items = await api('/api/notifications?limit=10');
  if (!items || !items.length) return;
  const newest = items[0];
  if (newest.id > _lastSeenId) {
    // הופיעו חדשות מאז הביקור האחרון - הצג browser notif לכל חדש
    if (_lastSeenId > 0) {  // לא מציג בטעינה ראשונה
      const fresh = items.filter(n => n.id > _lastSeenId).slice(0, 3);
      fresh.reverse().forEach(showBrowserNotification);
    }
    _lastSeenId = newest.id;
    localStorage.setItem('lastSeenNotifId', String(_lastSeenId));
  }
  refreshBadge();
}

// ============= WATCHLIST =============
// אם מחובר - נשמר בשרת. אחרת ב-localStorage.
const WL_KEY = 'watchlist';
let _wlCache = null;  // cache בזמן ריצה

function wlLocalGet() {
  try { return JSON.parse(localStorage.getItem(WL_KEY) || '[]'); } catch { return []; }
}
function wlLocalSet(arr) { localStorage.setItem(WL_KEY, JSON.stringify(arr)); }

async function wlLoad(force) {
  if (_wlCache !== null && !force) return _wlCache;
  if (isLoggedIn()) {
    const rows = await api('/api/me/watchlist');
    _wlCache = rows ? rows.map(r => r.symbol) : [];
  } else {
    _wlCache = wlLocalGet();
  }
  return _wlCache;
}

// סינכרוני - מהcache לרינדור מהיר. wlSync() מרענן את ה-cache אסינכרונית.
function wlGet() { return _wlCache || wlLocalGet(); }
function wlHas(sym) { return wlGet().includes(sym.toUpperCase()); }

async function wlToggle(sym) {
  sym = sym.toUpperCase();
  const list = wlGet();
  const i = list.indexOf(sym);
  const isRemoving = i >= 0;

  if (isLoggedIn()) {
    if (isRemoving) {
      await fetch(API + `/api/me/watchlist/${sym}`, {method: 'DELETE', headers: authHeader()});
    } else {
      const r = await fetch(API + '/api/me/watchlist', {
        method: 'POST',
        headers: Object.assign({'Content-Type':'application/json'}, authHeader()),
        body: JSON.stringify({symbol: sym}),
      });
      if (r.status === 402) {
        const e = await r.json();
        toast(e.detail || 'הגעת למגבלת התוכנית');
        return;
      }
    }
  } else {
    if (isRemoving) list.splice(i, 1); else list.push(sym);
    wlLocalSet(list);
  }

  // עדכון cache
  _wlCache = isRemoving ? list.filter(s => s !== sym) : Array.from(new Set([...list, sym]));
  toast(isRemoving ? `${sym} הוסר מה-Watchlist` : `${sym} נוסף ל-Watchlist`);

  // אם הוספנו מנייה והשוק פתוח - סריקה מהירה ברקע ליצירת סיגנל אם רלוונטי
  if (!isRemoving && isLoggedIn()) {
    triggerSingleSymbolScan(sym);
  }

  // רענון UI
  const active = document.querySelector('.page.active')?.id;
  if (active === 'page-signals') loadSignals();
  else if (active === 'page-dashboard') loadDashboard();
  else if (active === 'page-watchlist') loadWatchlist();
  else if (active === 'page-journal') loadJournal();
}

async function wlAdd() {
  const input = document.getElementById('wlAddInput');
  const sym = (input.value || '').trim().toUpperCase();
  // אפשר NVDA, גם BRK.B וגם POLI.TA
  if (!/^[A-Z]{1,6}(\.[A-Z]{1,3})?$/.test(sym)) { toast('סמל לא תקין (דוגמה: NVDA, POLI.TA)'); return; }
  if (wlHas(sym)) { toast('כבר ב-Watchlist'); return; }
  await wlToggle(sym);
  input.value = '';
}

function wlRefresh() { _wlCache = null; loadWatchlist(true); }

// סנכרון localStorage → שרת בהתחברות
async function wlSyncOnLogin() {
  const local = wlLocalGet();
  if (!local.length) return;
  try {
    const r = await fetch(API + '/api/me/watchlist/sync', {
      method: 'POST',
      headers: Object.assign({'Content-Type':'application/json'}, authHeader()),
      body: JSON.stringify({symbols: local}),
    });
    const data = await r.json();
    if (data.added > 0) toast(`${data.added} מניות סונכרנו לחשבון`);
    if (data.truncated > 0) {
      setTimeout(() => {
        alert(`⚠️ ${data.truncated} מניות לא נוספו כי הגעת למגבלת התוכנית שלך (${data.plan_limit} מניות).\n\nשדרג ל-Pro או VIP כדי להוסיף עוד.`);
      }, 600);
    }
    localStorage.removeItem(WL_KEY);
  } catch (e) {}
}

// סריקה חד-סמלית - מופעלת אחרי הוספה ל-Watchlist (אם השוק פתוח)
async function triggerSingleSymbolScan(sym) {
  const headers = Object.assign({'Content-Type':'application/json'}, authHeader());
  try {
    await fetch(API + `/api/system/scan/symbol/${encodeURIComponent(sym)}`, {
      method: 'POST', headers,
    });
  } catch (e) {}
}

async function loadWatchlist(force) {
  const list = await wlLoad(force);
  const grid = document.getElementById('watchlistGrid');
  if (!list.length) {
    const popular = ['NVDA','AAPL','TSLA','MSFT','META','GOOG','AMD','PLTR','TEVA','CHKP'];
    const popularHtml = popular.map(s =>
      `<button class="btn btn-blue" style="margin:4px;padding:6px 12px;font-size:12px" onclick="wlToggle('${s}')">+ ${s}</button>`
    ).join('');
    grid.innerHTML = `
      <div style="grid-column:1/-1;text-align:center;padding:40px 20px;background:var(--card);border:1px dashed var(--border);border-radius:12px">
        <div style="font-size:64px;margin-bottom:14px">⭐</div>
        <div style="font-size:18px;font-weight:bold;margin-bottom:8px">ה-Watchlist שלך ריק</div>
        <div style="color:var(--muted);font-size:13px;margin-bottom:20px">הוסף מניות שאתה רוצה לעקוב אחריהן - תקבל התראות מיידיות על חדשות וסיגנלים</div>
        <div style="margin-bottom:14px">
          <input type="text" placeholder="הקלד סמל (NVDA)" maxlength="10" id="wlQuickAdd"
                 oninput="this.value=this.value.toUpperCase()"
                 onkeydown="if(event.key==='Enter'){const v=this.value.trim();if(v){wlToggle(v);this.value='';}}"
                 style="background:#080c14;border:1px solid var(--border);color:var(--text);padding:10px 14px;border-radius:8px;font-size:14px;width:200px;direction:ltr;text-align:left">
        </div>
        <div style="color:var(--muted);font-size:11px;margin:14px 0 8px">או בחר מהפופולריים:</div>
        <div style="display:flex;flex-wrap:wrap;justify-content:center;max-width:500px;margin:0 auto">${popularHtml}</div>
      </div>`;
    return;
  }
  grid.innerHTML = list.map(sym => `<div class="wl-card" id="wl-${sym}"><div class="modal-loading">טוען ${sym}...</div></div>`).join('');

  // טען מקבילית את כל המניות (כל אחת מ-/api/stocks)
  await Promise.all(list.map(async sym => {
    const data = await api(`/api/stocks/${sym}`);
    const el = document.getElementById(`wl-${sym}`);
    if (!el) return;
    if (!data) {
      el.innerHTML = `<button class="x-btn" onclick="wlToggle('${sym}')">✕</button>
        <div class="wl-symbol">${sym}</div>
        <div class="wl-name" style="color:var(--red)">⚠ נכשלה טעינה</div>`;
      return;
    }
    const ch = data.day_change_pct;
    const chClass = ch == null ? '' : (ch >= 0 ? 'pos' : 'neg');
    const sign = ch >= 0 ? '+' : '';
    el.innerHTML = `
      <button class="x-btn" onclick="wlToggle('${sym}')">✕</button>
      <div class="wl-top" onclick="openStock('${sym}')">
        <div class="wl-symbol">${sym}</div>
        <div class="wl-price ${chClass}">$${(data.price||0).toFixed(2)}</div>
      </div>
      <div class="wl-name">${escapeHtml(data.name || '')}</div>
      <div class="wl-meta">
        <span class="wl-change ${chClass}">${ch != null ? sign+ch.toFixed(2)+'%' : '—'}</span>
        <span>RSI? לחץ על הכרטיס לפרטים</span>
      </div>`;
  }));
}

// חיפוש מנייה ידני
function doSearch() {
  const input = document.getElementById('symSearch');
  const sym = (input.value || '').trim().toUpperCase();
  if (!sym) { toast('הזן סמל מנייה'); return; }
  if (!/^[A-Z]{1,6}(\.[A-Z]{1,3})?$/.test(sym)) { toast('סמל לא תקין (דוגמה: NVDA, POLI.TA)'); return; }
  openStock(sym);
  input.blur();
}

// כפתורי timeframe
document.addEventListener('click', e => {
  const btn = e.target.closest('.tf-btn');
  if (!btn) return;
  document.querySelectorAll('.tf-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const sym = document.getElementById('mSymbol').textContent;
  if (sym && sym !== '--') {
    setTvFrame(sym, btn.dataset.int, btn.dataset.range);
  }
});

function exportCSV() {
  fetch(API + '/api/signals?limit=500').then(r => r.json()).then(sigs => {
    const rows = [['תאריך','מנייה','כניסה','RSI','וולום','חוזק','יעד1','יעד2','סטופ','סטטוס']];
    sigs.forEach(s => {
      rows.push([
        new Date(s.created_at).toLocaleDateString('he-IL'),
        s.symbol, s.price, s.rsi, s.volume_ratio, s.strength,
        s.target_1, s.target_2, s.stop_loss, s.status
      ]);
    });
    const csv = rows.map(r => r.join(',')).join('\n');
    const blob = new Blob(['﻿' + csv], {type: 'text/csv;charset=utf-8'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `signals_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    toast('✅ הקובץ ירד');
  });
}

// PWA - רישום service worker (מאפשר התקנה כאפליקציה)
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/sw.js', {scope: '/'}).catch(()=>{});
  });
}

// ========== THEME ==========
function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  const btn = document.getElementById('themeBtn');
  if (btn) btn.textContent = theme === 'light' ? '🌙' : '☀️';
  localStorage.setItem('theme', theme);
}
function toggleTheme() {
  const cur = localStorage.getItem('theme') || 'dark';
  applyTheme(cur === 'light' ? 'dark' : 'light');
}
applyTheme(localStorage.getItem('theme') || 'dark');

// אתחול
handleAuthHash();             // אם יש hash עם reset/verify token - לטפל
handlePostPayment();          // אם הגיע אחרי תשלום - אמת + שדרג
validateSession();           // קודם כל לאמת token אם יש
loadDashboard();
loadHealth();
ensureBrowserNotifyPermission();
pollNotifications();
pollWatchlistNews();          // טעינה ראשונית - לא מציג popup, רק שומר last id
// pollWatchlistNews מטפל גם בטיקר וגם בהתראות - אין צורך ב-refreshTicker נפרד
setInterval(loadDashboard, 60000);
setInterval(pollNotifications, 30000);
setInterval(pollWatchlistNews, 30000);  // real-time alerts + ticker refresh