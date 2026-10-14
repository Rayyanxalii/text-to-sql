/**
 * Query Sentinel — Frontend Application Controller
 * Minimalist, developer-grade interface for AI-powered Text-to-SQL
 */

/* ==========================================================================
   1. State & Configuration
   ========================================================================== */
const APP_STATE = {
  // Configurable Backend API endpoint
  apiUrl: (typeof window !== 'undefined' && localStorage.getItem('qs_api_url')) 
    || (window.QUERY_SENTINEL_CONFIG && window.QUERY_SENTINEL_CONFIG.API_URL) 
    || 'http://127.0.0.1:8000',

  isOnline: false,
  isExecuting: false,
  pendingClarification: false,
  currentConversationId: null,
  activeSessionMessages: [],
  sessions: [],
  sidebarCollapsed: false,
};

/* ==========================================================================
   2. Lifecycle Initialization
   ========================================================================== */
document.addEventListener('DOMContentLoaded', () => {
  initStorage();
  initSidebarState();
  initIcons();
  checkBackendHealth();

  // Background health check polling
  const pollInterval = (window.QUERY_SENTINEL_CONFIG && window.QUERY_SENTINEL_CONFIG.HEALTH_CHECK_INTERVAL_MS) || 10000;
  setInterval(checkBackendHealth, pollInterval);

  // Global Keyboard Shortcuts
  document.addEventListener('keydown', handleGlobalKeydown);
});

function initIcons() {
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

/* ==========================================================================
   3. Backend Connectivity & Health Check
   ========================================================================== */
async function checkBackendHealth() {
  const dot = document.getElementById('connIndicator');
  const label = document.getElementById('connLabel');
  if (!dot || !label) return;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 4000);

    const res = await fetch(`${APP_STATE.apiUrl}/`, {
      method: 'GET',
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      APP_STATE.isOnline = true;
      dot.className = 'w-2 h-2 rounded-full bg-emerald-400';
      label.textContent = 'PostgreSQL Live';
      label.className = 'text-[11px] text-emerald-300 font-mono truncate';
    } else {
      setOfflineState(`HTTP ${res.status}`);
    }
  } catch (err) {
    setOfflineState('Offline');
  }
}

function setOfflineState(statusText) {
  APP_STATE.isOnline = false;
  const dot = document.getElementById('connIndicator');
  const label = document.getElementById('connLabel');
  if (dot && label) {
    dot.className = 'w-2 h-2 rounded-full bg-rose-400';
    label.textContent = `Backend ${statusText || 'Offline'}`;
    label.className = 'text-[11px] text-rose-300 font-mono truncate';
  }
}

/* ==========================================================================
   4. Sessions & History Persistence
   ========================================================================== */
function initStorage() {
  try {
    const saved = localStorage.getItem('qs_sessions');
    APP_STATE.sessions = saved ? JSON.parse(saved) : [];
  } catch (e) {
    APP_STATE.sessions = [];
  }

  if (APP_STATE.sessions.length === 0) {
    startNewSession(false);
  } else {
    loadSession(APP_STATE.sessions[0].id);
  }
  renderSessionHistory();
}

function generateConversationId() {
  return 'conv_' + Date.now().toString(36) + '_' + Math.random().toString(36).substring(2, 8);
}

function startNewSession(focusInput = true) {
  const newId = generateConversationId();
  APP_STATE.currentConversationId = newId;
  APP_STATE.activeSessionMessages = [];
  APP_STATE.pendingClarification = false;

  const newSession = {
    id: newId,
    title: 'New Query',
    createdAt: Date.now(),
    messages: []
  };

  APP_STATE.sessions.unshift(newSession);
  saveSessions();

  renderSessionHistory();
  renderCurrentMessages();
  updateSessionTitleHeader('New Query');
  updateClarificationNotice(false);

  if (focusInput) {
    const input = document.getElementById('queryInput');
    if (input) input.focus();
  }
}

function loadSession(id) {
  const session = APP_STATE.sessions.find(s => s.id === id);
  if (!session) return;

  APP_STATE.currentConversationId = session.id;
  APP_STATE.activeSessionMessages = session.messages || [];
  APP_STATE.pendingClarification = Boolean(session.pendingClarification);

  renderSessionHistory();
  renderCurrentMessages();
  updateSessionTitleHeader(session.title || 'New Query');
  updateClarificationNotice(APP_STATE.pendingClarification);

  // Close mobile sidebar drawer if open
  if (window.innerWidth < 768) {
    toggleSidebar(false);
  }
}

function saveSessions() {
  if (APP_STATE.sessions.length > 30) {
    APP_STATE.sessions = APP_STATE.sessions.slice(0, 30);
  }
  localStorage.setItem('qs_sessions', JSON.stringify(APP_STATE.sessions));

  const countBadge = document.getElementById('sessionCount');
  if (countBadge) countBadge.textContent = APP_STATE.sessions.length;
}

function updateSessionTitle(id, text) {
  const session = APP_STATE.sessions.find(s => s.id === id);
  if (session && (session.title === 'New Query' || !session.title)) {
    session.title = text.length > 34 ? text.substring(0, 34).trim() + '...' : text;
    saveSessions();
    renderSessionHistory();
    updateSessionTitleHeader(session.title);
  }
}

function updateSessionTitleHeader(title) {
  const el = document.getElementById('currentSessionTitle');
  if (el) el.textContent = title;
}

function deleteSession(event, id) {
  if (event) event.stopPropagation();
  APP_STATE.sessions = APP_STATE.sessions.filter(s => s.id !== id);
  saveSessions();

  if (APP_STATE.sessions.length === 0) {
    startNewSession(false);
  } else if (APP_STATE.currentConversationId === id) {
    loadSession(APP_STATE.sessions[0].id);
  } else {
    renderSessionHistory();
  }
}

function clearActiveThread() {
  APP_STATE.activeSessionMessages = [];
  APP_STATE.pendingClarification = false;

  const current = APP_STATE.sessions.find(s => s.id === APP_STATE.currentConversationId);
  if (current) {
    current.messages = [];
    current.pendingClarification = false;
    current.title = 'New Query';
    saveSessions();
  }

  renderSessionHistory();
  renderCurrentMessages();
  updateSessionTitleHeader('New Query');
  updateClarificationNotice(false);
}

function filterSessions(query) {
  const q = (query || '').toLowerCase().trim();
  const list = document.getElementById('sessionHistoryList');
  if (!list) return;

  const items = list.querySelectorAll('.session-item');
  items.forEach(item => {
    const title = item.getAttribute('data-title') || '';
    if (!q || title.toLowerCase().includes(q)) {
      item.classList.remove('hidden');
    } else {
      item.classList.add('hidden');
    }
  });
}

function renderSessionHistory() {
  const list = document.getElementById('sessionHistoryList');
  const empty = document.getElementById('emptySessionState');
  if (!list) return;

  list.innerHTML = '';

  if (APP_STATE.sessions.length === 0) {
    if (empty) empty.classList.remove('hidden');
    return;
  }
  if (empty) empty.classList.add('hidden');

  APP_STATE.sessions.forEach(session => {
    const isActive = session.id === APP_STATE.currentConversationId;
    const item = document.createElement('div');
    item.className = `session-item group flex items-center justify-between px-2.5 py-1.5 rounded-md cursor-pointer text-xs transition select-none ${
      isActive
        ? 'bg-brand-600/20 text-white font-medium border border-brand-500/40'
        : 'text-slate-400 hover:bg-dark-800 hover:text-slate-200 border border-transparent'
    }`;
    item.setAttribute('data-title', session.title || 'New Query');
    item.onclick = () => loadSession(session.id);

    item.innerHTML = `
      <div class="flex items-center gap-2 min-w-0 truncate">
        <i data-lucide="message-square" class="w-3.5 h-3.5 ${isActive ? 'text-brand-400' : 'text-slate-500'} flex-shrink-0"></i>
        <span class="truncate">${escapeHtml(session.title || 'New Query')}</span>
      </div>
      <button
        onclick="deleteSession(event, '${session.id}')"
        class="opacity-0 group-hover:opacity-100 hover:text-rose-400 p-1 rounded transition flex-shrink-0"
        title="Delete session"
      >
        <i data-lucide="trash-2" class="w-3 h-3"></i>
      </button>
    `;

    list.appendChild(item);
  });

  const countBadge = document.getElementById('sessionCount');
  if (countBadge) countBadge.textContent = APP_STATE.sessions.length;

  initIcons();
}

/* ==========================================================================
   5. Query Execution & API Communication
   ========================================================================== */
async function submitQuery() {
  if (APP_STATE.isExecuting) return;

  const input = document.getElementById('queryInput');
  const queryText = input ? input.value.trim() : '';
  if (!queryText) return;

  // If a clarification is currently pending, submit it as clarification answer
  if (APP_STATE.pendingClarification) {
    submitClarification(queryText);
    if (input) {
      input.value = '';
      autoResizeTextarea(input);
    }
    return;
  }

  // Clear input
  if (input) {
    input.value = '';
    autoResizeTextarea(input);
  }

  // Add User Message to thread
  const userMsg = {
    role: 'user',
    text: queryText,
    timestamp: formatTime(new Date())
  };
  addMessage(userMsg);
  updateSessionTitle(APP_STATE.currentConversationId, queryText);

  // Set loading state
  setExecuting(true);

  try {
    const res = await fetch(`${APP_STATE.apiUrl}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question: queryText,
        conversation_id: APP_STATE.currentConversationId
      })
    });

    if (!res.ok) {
      const errPayload = await res.json().catch(() => ({}));
      const errorMsg = errPayload.detail || `Server error (${res.status}: ${res.statusText})`;
      throw new Error(errorMsg);
    }

    const data = await res.json();
    handleBackendSuccess(data);
  } catch (err) {
    console.error('[QuerySentinel] Request failed:', err);
    addMessage({
      role: 'error',
      text: err.message || 'Failed to connect to the backend server. Please verify FastAPI is running at ' + APP_STATE.apiUrl,
      timestamp: formatTime(new Date())
    });
  } finally {
    setExecuting(false);
  }
}

async function submitClarification(answerText) {
  if (APP_STATE.isExecuting || !answerText || !answerText.trim()) return;

  const cleanText = answerText.trim();

  // Add user clarification message
  addMessage({
    role: 'user',
    text: cleanText,
    isClarificationReply: true,
    timestamp: formatTime(new Date())
  });

  setExecuting(true);
  updateClarificationNotice(false);

  try {
    const res = await fetch(`${APP_STATE.apiUrl}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        clarification_answer: cleanText,
        conversation_id: APP_STATE.currentConversationId
      })
    });

    if (!res.ok) {
      const errPayload = await res.json().catch(() => ({}));
      const errorMsg = errPayload.detail || `Clarification resume failed (${res.status})`;
      throw new Error(errorMsg);
    }

    const data = await res.json();
    APP_STATE.pendingClarification = false;
    handleBackendSuccess(data);
  } catch (err) {
    console.error('[QuerySentinel] Clarification error:', err);
    addMessage({
      role: 'error',
      text: `Clarification failed: ${err.message}`,
      timestamp: formatTime(new Date())
    });
  } finally {
    setExecuting(false);
  }
}

function handleBackendSuccess(data) {
  // Case 1: Clarification needed
  if (data && data.requires_clarification) {
    APP_STATE.pendingClarification = true;
    updateClarificationNotice(true);
    addMessage({
      role: 'clarification',
      question: data.clarification_question || 'Additional clarification required to form an exact query.',
      timestamp: formatTime(new Date())
    });
    return;
  }

  APP_STATE.pendingClarification = false;
  updateClarificationNotice(false);

  // Case 2: Plain string answer (FastAPI default)
  if (typeof data === 'string') {
    const parsed = parseRawAnswerString(data);
    addMessage({
      role: 'assistant',
      answer: parsed.answer,
      sql: parsed.sql,
      results: parsed.results,
      isSecurityRejection: parsed.isSecurityRejection,
      isQueryError: parsed.isQueryError,
      timestamp: formatTime(new Date())
    });
    return;
  }

  // Case 3: Structured object response
  if (data && typeof data === 'object') {
    const rawAnswer = data.answer || '';
    const parsed = parseRawAnswerString(rawAnswer);

    addMessage({
      role: 'assistant',
      answer: parsed.answer || 'Query completed successfully.',
      sql: data.sql || parsed.sql || null,
      results: data.results || (data.db_result ? formatDbTuples(data.db_result) : parsed.results) || null,
      isSecurityRejection: Boolean(data.permission_denied || !data.input_safe || parsed.isSecurityRejection),
      isQueryError: Boolean(data.sql_execution_error || parsed.isQueryError),
      timestamp: formatTime(new Date())
    });
  }
}

/* ==========================================================================
   6. Parsing & Content Extraction
   ========================================================================== */
function parseRawAnswerString(rawText) {
  if (!rawText) {
    return {
      answer: 'No answer generated.',
      sql: null,
      results: null,
      isSecurityRejection: false,
      isQueryError: false
    };
  }

  // Detect security policy rejections
  const isSecurityRejection = 
    rawText.includes('violates safety guidelines') ||
    rawText.includes('SQL security is in charge') ||
    rawText.includes('flagged as unsafe') ||
    rawText.includes('do not have permission') ||
    rawText.includes('contain sensitive information');

  // Detect query execution errors
  const isQueryError = rawText.includes('The query could not be executed:');

  let workingText = rawText;
  let extractedSql = null;
  let extractedResults = null;

  // 1. Extract markdown SQL block: ```sql ... ```
  const sqlFenceMatch = workingText.match(/```(?:sql)?\s*([\s\S]*?SELECT[\s\S]*?)```/i);
  if (sqlFenceMatch) {
    extractedSql = sqlFenceMatch[1].trim();
    // Remove the SQL fence from the natural language answer
    workingText = workingText.replace(sqlFenceMatch[0], '').trim();
  } else {
    // Check for inline SELECT ... ;
    const rawSqlMatch = workingText.match(/\b(SELECT\s+[\s\S]+?;)/i);
    if (rawSqlMatch && rawSqlMatch[1].length > 15) {
      extractedSql = rawSqlMatch[1].trim();
    }
  }

  // 2. Extract markdown table: | Col1 | Col2 | ...
  const tableMatch = workingText.match(/(\|[^\n]+\|\r?\n\|[-:\s|]+\|\r?\n(?:\|[^\n]+\|\r?\n?)+)/);
  if (tableMatch) {
    extractedResults = parseMarkdownTable(tableMatch[1]);
  }

  return {
    answer: workingText,
    sql: extractedSql,
    results: extractedResults,
    isSecurityRejection,
    isQueryError
  };
}

function parseMarkdownTable(tableString) {
  try {
    const lines = tableString.trim().split(/\r?\n/).filter(l => l.includes('|'));
    if (lines.length < 3) return null;

    const parseRow = line => line.split('|').slice(1, -1).map(c => c.trim());
    const headers = parseRow(lines[0]);
    const rows = [];

    for (let i = 2; i < lines.length; i++) {
      const values = parseRow(lines[i]);
      if (values.length === headers.length) {
        const rowObj = {};
        headers.forEach((h, idx) => {
          rowObj[h] = values[idx];
        });
        rows.push(rowObj);
      }
    }

    return rows.length > 0 ? rows : null;
  } catch (e) {
    return null;
  }
}

function formatDbTuples(tuples) {
  if (!Array.isArray(tuples) || tuples.length === 0) return null;
  return tuples.map((tuple, idx) => {
    if (Array.isArray(tuple)) {
      const row = {};
      tuple.forEach((val, colIdx) => {
        row[`column_${colIdx + 1}`] = val;
      });
      return row;
    }
    return { row_id: idx + 1, value: String(tuple) };
  });
}

/* ==========================================================================
   7. Rendering Messages & Thread Management
   ========================================================================== */
function addMessage(msg) {
  APP_STATE.activeSessionMessages.push(msg);

  const current = APP_STATE.sessions.find(s => s.id === APP_STATE.currentConversationId);
  if (current) {
    current.messages = APP_STATE.activeSessionMessages;
    current.pendingClarification = APP_STATE.pendingClarification;
    saveSessions();
  }

  renderCurrentMessages();
}

function renderCurrentMessages() {
  const hero = document.getElementById('welcomeHero');
  const container = document.getElementById('threadContainer');
  if (!container) return;

  if (APP_STATE.activeSessionMessages.length === 0) {
    if (hero) hero.classList.remove('hidden');
    container.innerHTML = '';
    return;
  }

  if (hero) hero.classList.add('hidden');
  container.innerHTML = '';

  APP_STATE.activeSessionMessages.forEach((msg, idx) => {
    const node = createMessageNode(msg, idx);
    container.appendChild(node);
  });

  // Scroll to bottom smoothly
  const scrollArea = document.getElementById('messagesContainer');
  if (scrollArea) {
    scrollArea.scrollTop = scrollArea.scrollHeight;
  }

  initIcons();
}

function createMessageNode(msg, index) {
  const wrap = document.createElement('div');
  wrap.className = 'w-full fade-in';

  // --- USER MESSAGE ---
  if (msg.role === 'user') {
    wrap.innerHTML = `
      <div class="flex justify-end items-start gap-2.5 pl-8 md:pl-16">
        <div class="space-y-1 text-right max-w-xl">
          <div class="inline-block bg-dark-800 border border-white/[0.08] text-slate-100 rounded-xl rounded-tr-xs px-3.5 py-2 text-xs sm:text-sm text-left leading-relaxed shadow-sm">
            ${escapeHtml(msg.text)}
          </div>
          <div class="text-[10px] text-slate-500 font-mono pr-1">${msg.timestamp || ''}</div>
        </div>
        <div class="w-6 h-6 rounded-md bg-dark-750 border border-white/[0.08] flex items-center justify-center text-slate-300 flex-shrink-0 mt-0.5">
          <i data-lucide="user" class="w-3.5 h-3.5"></i>
        </div>
      </div>
    `;
    return wrap;
  }

  // --- CLARIFICATION CARD ---
  if (msg.role === 'clarification') {
    wrap.innerHTML = `
      <div class="flex items-start gap-2.5 pr-4 md:pr-12">
        <div class="w-6 h-6 rounded-md bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400 flex-shrink-0 mt-0.5">
          <i data-lucide="help-circle" class="w-3.5 h-3.5"></i>
        </div>
        <div class="flex-1 max-w-2xl bg-dark-850 border border-amber-500/30 rounded-xl p-3.5 space-y-3 shadow-sm">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-semibold uppercase tracking-wider text-amber-400 font-mono">
              Clarification Requested
            </span>
            <span class="text-[10px] text-slate-500 font-mono">${msg.timestamp || ''}</span>
          </div>

          <p class="text-xs sm:text-sm text-slate-200 leading-relaxed font-medium">
            ${escapeHtml(msg.question)}
          </p>

          <div class="pt-1 space-y-2">
            <div class="flex items-center gap-2">
              <input
                type="text"
                id="clarify-input-${index}"
                placeholder="Type clarification to resume..."
                class="flex-1 px-3 py-1.5 rounded-lg bg-dark-950 border border-white/[0.08] text-xs text-white placeholder-slate-500 outline-none focus:border-amber-400/80 transition"
                onkeydown="if(event.key==='Enter') submitClarification(this.value)"
              />
              <button
                onclick="submitClarification(document.getElementById('clarify-input-${index}').value)"
                class="px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 active:bg-amber-600 text-slate-950 font-semibold text-xs transition"
              >
                Continue
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
    return wrap;
  }

  // --- SYSTEM / REQUEST ERROR ---
  if (msg.role === 'error') {
    wrap.innerHTML = `
      <div class="flex items-start gap-2.5 pr-4 md:pr-12">
        <div class="w-6 h-6 rounded-md bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400 flex-shrink-0 mt-0.5">
          <i data-lucide="alert-triangle" class="w-3.5 h-3.5"></i>
        </div>
        <div class="flex-1 max-w-2xl bg-dark-850 border border-rose-500/30 rounded-xl p-3.5 space-y-1.5 text-xs shadow-sm">
          <div class="flex items-center justify-between text-rose-400 font-semibold">
            <span>Query Notice</span>
            <span class="text-[10px] text-slate-500 font-mono font-normal">${msg.timestamp || ''}</span>
          </div>
          <p class="text-slate-300 leading-relaxed">${escapeHtml(msg.text)}</p>
        </div>
      </div>
    `;
    return wrap;
  }

  // --- ASSISTANT MESSAGE CARD ---
  const hasSql = Boolean(msg.sql);
  const hasResults = Boolean(msg.results && msg.results.length > 0);
  const showTabs = hasSql || hasResults;

  wrap.innerHTML = `
    <div class="flex items-start gap-2.5 pr-2 md:pr-12">
      <!-- Bot Avatar -->
      <div class="w-6 h-6 rounded-md bg-brand-600/20 border border-brand-500/30 flex items-center justify-center text-brand-400 flex-shrink-0 mt-0.5">
        <i data-lucide="bot" class="w-3.5 h-3.5"></i>
      </div>

      <div class="flex-1 max-w-2xl space-y-2 min-w-0">
        
        <!-- Main Card Container -->
        <div class="bg-dark-850 border border-white/[0.08] rounded-xl overflow-hidden shadow-sm">
          
          <!-- Card Header & Tab Bar -->
          <div class="flex items-center justify-between border-b border-white/[0.06] bg-dark-900/60 px-3 py-1.5">
            <div class="flex items-center gap-1">
              ${showTabs ? `
                <button
                  onclick="switchTab(${index}, 'answer')"
                  id="tab-btn-answer-${index}"
                  class="px-2.5 py-1 text-xs font-medium text-brand-400 border-b-2 border-brand-500 transition flex items-center gap-1.5"
                >
                  <i data-lucide="message-square" class="w-3 h-3"></i> Answer
                </button>

                ${hasSql ? `
                  <button
                    onclick="switchTab(${index}, 'sql')"
                    id="tab-btn-sql-${index}"
                    class="px-2.5 py-1 text-xs font-medium text-slate-400 hover:text-slate-200 border-b-2 border-transparent transition flex items-center gap-1.5"
                  >
                    <i data-lucide="terminal" class="w-3 h-3"></i> SQL
                  </button>
                ` : ''}

                ${hasResults ? `
                  <button
                    onclick="switchTab(${index}, 'results')"
                    id="tab-btn-results-${index}"
                    class="px-2.5 py-1 text-xs font-medium text-slate-400 hover:text-slate-200 border-b-2 border-transparent transition flex items-center gap-1.5"
                  >
                    <i data-lucide="table" class="w-3 h-3"></i> Results (${msg.results.length})
                  </button>
                ` : ''}
              ` : `
                <div class="flex items-center gap-1.5 text-xs text-slate-400">
                  <i data-lucide="shield" class="w-3 h-3 text-brand-400"></i>
                  <span class="font-medium text-slate-300">Query Sentinel</span>
                </div>
              `}
            </div>

            <!-- Header Actions -->
            <div class="flex items-center gap-1.5">
              ${msg.isSecurityRejection ? `
                <span class="px-2 py-0.5 rounded text-[10px] font-medium bg-dark-800 text-slate-300 border border-white/[0.08]">
                  Security Guardrail
                </span>
              ` : ''}

              <!-- Copy Answer Button -->
              <button
                onclick="copyAnswerText(${index}, this)"
                class="px-2 py-1 rounded text-[11px] text-slate-400 hover:text-slate-200 hover:bg-dark-800 transition flex items-center gap-1"
                title="Copy response to clipboard"
              >
                <i data-lucide="copy" class="w-3 h-3"></i>
                <span class="copy-label">Copy</span>
              </button>

              <span class="text-[10px] text-slate-500 font-mono pl-1">${msg.timestamp || ''}</span>
            </div>
          </div>

          <!-- Card Content Body -->
          <div class="p-3.5">
            
            <!-- Pane 1: Answer -->
            <div id="tab-pane-answer-${index}" class="block prose-content">
              ${renderMarkdownContent(msg.answer)}
            </div>

            <!-- Pane 2: SQL Panel -->
            ${hasSql ? `
              <div id="tab-pane-sql-${index}" class="hidden space-y-2">
                <div class="flex items-center justify-between text-xs text-slate-400 pb-1">
                  <span class="font-mono text-[11px] text-slate-400">Generated PostgreSQL Query</span>
                  <button
                    onclick="copySqlText(${index}, this)"
                    class="px-2 py-0.5 rounded bg-dark-800 hover:bg-dark-750 border border-white/[0.08] text-[11px] text-slate-300 transition flex items-center gap-1"
                  >
                    <i data-lucide="copy" class="w-3 h-3"></i> Copy SQL
                  </button>
                </div>
                <div class="sql-console p-3 overflow-x-auto text-xs text-slate-200 leading-relaxed">
                  <code>${highlightSql(msg.sql)}</code>
                </div>
              </div>
            ` : ''}

            <!-- Pane 3: Results Table -->
            ${hasResults ? `
              <div id="tab-pane-results-${index}" class="hidden space-y-2">
                <div class="flex items-center justify-between text-xs text-slate-400 pb-1">
                  <span class="font-mono text-[11px]">${msg.results.length} record(s) returned</span>
                  <button
                    onclick="downloadCsv(${index})"
                    class="px-2 py-0.5 rounded bg-dark-800 hover:bg-dark-750 border border-white/[0.08] text-[11px] text-slate-300 transition flex items-center gap-1"
                  >
                    <i data-lucide="download" class="w-3 h-3"></i> Export CSV
                  </button>
                </div>

                <div class="data-table-wrapper max-h-64 overflow-x-auto">
                  <table class="data-table">
                    <thead>
                      <tr>
                        ${Object.keys(msg.results[0]).map(col => `<th>${escapeHtml(col)}</th>`).join('')}
                      </tr>
                    </thead>
                    <tbody>
                      ${msg.results.map(row => `
                        <tr>
                          ${Object.values(row).map(val => `<td>${escapeHtml(String(val ?? ''))}</td>`).join('')}
                        </tr>
                      `).join('')}
                    </tbody>
                  </table>
                </div>
              </div>
            ` : ''}

          </div>
        </div>

      </div>
    </div>
  `;

  return wrap;
}

/* ==========================================================================
   8. Tab Controls & Utilities
   ========================================================================== */
function switchTab(index, targetTab) {
  const tabs = ['answer', 'sql', 'results'];

  tabs.forEach(tab => {
    const btn = document.getElementById(`tab-btn-${tab}-${index}`);
    const pane = document.getElementById(`tab-pane-${tab}-${index}`);

    if (btn && pane) {
      if (tab === targetTab) {
        btn.className = 'px-2.5 py-1 text-xs font-medium text-brand-400 border-b-2 border-brand-500 transition flex items-center gap-1.5';
        pane.classList.remove('hidden');
        pane.classList.add('block');
      } else {
        btn.className = 'px-2.5 py-1 text-xs font-medium text-slate-400 hover:text-slate-200 border-b-2 border-transparent transition flex items-center gap-1.5';
        pane.classList.remove('block');
        pane.classList.add('hidden');
      }
    }
  });

  initIcons();
}

function copyAnswerText(index, btn) {
  const msg = APP_STATE.activeSessionMessages[index];
  if (!msg) return;

  navigator.clipboard.writeText(msg.answer).then(() => {
    const label = btn.querySelector('.copy-label');
    if (label) label.textContent = 'Copied!';
    setTimeout(() => {
      if (label) label.textContent = 'Copy';
    }, 1800);
  });
}

function copySqlText(index, btn) {
  const msg = APP_STATE.activeSessionMessages[index];
  if (!msg || !msg.sql) return;

  navigator.clipboard.writeText(msg.sql).then(() => {
    const origHtml = btn.innerHTML;
    btn.innerHTML = `<i data-lucide="check" class="w-3 h-3 text-emerald-400"></i> Copied!`;
    initIcons();
    setTimeout(() => {
      btn.innerHTML = origHtml;
      initIcons();
    }, 1800);
  });
}

function downloadCsv(index) {
  const msg = APP_STATE.activeSessionMessages[index];
  if (!msg || !msg.results || msg.results.length === 0) return;

  const headers = Object.keys(msg.results[0]);
  const rows = [headers.join(',')];

  msg.results.forEach(row => {
    const vals = headers.map(h => {
      let v = String(row[h] ?? '').replace(/"/g, '""');
      return `"${v}"`;
    });
    rows.push(vals.join(','));
  });

  const blob = new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `query_sentinel_results_${Date.now()}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

/* ==========================================================================
   9. SQL Syntax Highlighting & Markdown
   ========================================================================== */
function highlightSql(rawSql) {
  if (!rawSql) return '';
  let s = escapeHtml(rawSql.trim());

  // 1. Comments: -- ...
  s = s.replace(/(--[^\n]*)/g, `<span class="sql-token-cmt">$1</span>`);

  // 2. Strings: '...'
  s = s.replace(/'([^']*)'/g, `<span class="sql-token-str">'$1'</span>`);

  // 3. Numbers
  s = s.replace(/\b(\d+(?:\.\d+)?)\b/g, `<span class="sql-token-num">$1</span>`);

  // 4. Functions
  const functions = [
    'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'ROUND', 'COALESCE', 'DATE_PART',
    'EXTRACT', 'NOW', 'LOWER', 'UPPER', 'CONCAT', 'CAST', 'SUBSTRING'
  ];
  functions.forEach(fn => {
    const regex = new RegExp(`\\b(${fn})\\b(?=\\s*\\()`, 'gi');
    s = s.replace(regex, `<span class="sql-token-fn">$1</span>`);
  });

  // 5. Keywords
  const keywords = [
    'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN',
    'FULL JOIN', 'ON', 'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'OFFSET',
    'AS', 'AND', 'OR', 'NOT', 'IN', 'IS NULL', 'IS NOT NULL', 'BETWEEN',
    'LIKE', 'ILIKE', 'UNION', 'ALL', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
    'ASC', 'DESC', 'DISTINCT', 'EXISTS'
  ];
  keywords.forEach(kw => {
    const regex = new RegExp(`\\b(${kw})\\b`, 'gi');
    s = s.replace(regex, `<span class="sql-token-kw">$1</span>`);
  });

  return s;
}

function renderMarkdownContent(text) {
  if (!text) return '';

  let html = escapeHtml(text);

  // Bold: **text**
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

  // Inline code: `code`
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Bullet points
  const lines = html.split('\n');
  let inList = false;
  let formatted = [];

  for (let line of lines) {
    const bulletMatch = line.match(/^\s*[-*]\s+(.*)/);
    if (bulletMatch) {
      if (!inList) {
        formatted.push('<ul>');
        inList = true;
      }
      formatted.push(`<li>${bulletMatch[1]}</li>`);
    } else {
      if (inList) {
        formatted.push('</ul>');
        inList = false;
      }
      if (line.trim().length > 0) {
        formatted.push(`<p>${line}</p>`);
      }
    }
  }

  if (inList) formatted.push('</ul>');

  return formatted.join('\n');
}

function escapeHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatTime(date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/* ==========================================================================
   10. User Input & Starter Prompts
   ========================================================================== */
function selectPrompt(promptText) {
  const input = document.getElementById('queryInput');
  if (!input) return;

  input.value = promptText;
  autoResizeTextarea(input);
  submitQuery();
}

function handleInputKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    submitQuery();
  }
}

function autoResizeTextarea(el) {
  if (!el) return;
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}

function setExecuting(isExec) {
  APP_STATE.isExecuting = isExec;
  const sendBtn = document.getElementById('sendBtn');
  const loading = document.getElementById('loadingIndicator');

  if (sendBtn) {
    sendBtn.disabled = isExec;
    sendBtn.innerHTML = isExec
      ? `<i data-lucide="loader-2" class="w-4 h-4 animate-spin text-white"></i>`
      : `<i data-lucide="arrow-up" class="w-4 h-4"></i>`;
  }

  if (loading) {
    if (isExec) {
      loading.classList.remove('hidden');
      const scrollArea = document.getElementById('messagesContainer');
      if (scrollArea) scrollArea.scrollTop = scrollArea.scrollHeight;
    } else {
      loading.classList.add('hidden');
    }
  }

  initIcons();
}

function updateClarificationNotice(show) {
  const notice = document.getElementById('clarifyNotice');
  const input = document.getElementById('queryInput');

  if (notice) {
    if (show) notice.classList.remove('hidden');
    else notice.classList.add('hidden');
  }

  if (input) {
    if (show) {
      input.placeholder = 'Provide clarification to resume query...';
      input.focus();
    } else {
      input.placeholder = 'Ask a question about your database in natural language...';
    }
  }
}

/* ==========================================================================
   11. Sidebar, Navigation & Settings Modal
   ========================================================================== */
function toggleSidebar(forceState) {
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  if (!sidebar) return;

  const isMobile = window.innerWidth < 768;

  if (isMobile) {
    const isClosed = sidebar.classList.contains('-translate-x-full');
    const shouldOpen = typeof forceState === 'boolean' ? forceState : isClosed;

    if (shouldOpen) {
      sidebar.classList.remove('-translate-x-full');
      if (backdrop) backdrop.classList.remove('hidden');
    } else {
      sidebar.classList.add('-translate-x-full');
      if (backdrop) backdrop.classList.add('hidden');
    }
  } else {
    // Desktop: toggle md:hidden or hidden
    const isCollapsed = sidebar.classList.contains('md:hidden') || sidebar.classList.contains('hidden');
    const shouldOpen = typeof forceState === 'boolean' ? forceState : isCollapsed;

    APP_STATE.sidebarCollapsed = !shouldOpen;
    localStorage.setItem('qs_sidebar_collapsed', APP_STATE.sidebarCollapsed ? 'true' : 'false');

    if (shouldOpen) {
      sidebar.classList.remove('md:hidden', 'hidden', '-translate-x-full');
    } else {
      sidebar.classList.add('md:hidden');
    }
  }

  initIcons();
}

function initSidebarState() {
  const collapsed = localStorage.getItem('qs_sidebar_collapsed') === 'true';
  APP_STATE.sidebarCollapsed = collapsed;
  const sidebar = document.getElementById('sidebar');
  if (sidebar && collapsed && window.innerWidth >= 768) {
    sidebar.classList.add('md:hidden');
  }
}

function openSettingsModal() {
  const modal = document.getElementById('settingsModal');
  const input = document.getElementById('apiUrlInput');
  const result = document.getElementById('modalConnResult');

  if (input) input.value = APP_STATE.apiUrl;
  if (result) result.classList.add('hidden');
  if (modal) modal.classList.remove('hidden');
}

function closeSettingsModal() {
  const modal = document.getElementById('settingsModal');
  if (modal) modal.classList.add('hidden');
}

async function testEndpointFromModal() {
  const input = document.getElementById('apiUrlInput');
  const result = document.getElementById('modalConnResult');
  const btn = document.getElementById('testConnBtn');
  const testUrl = input ? input.value.trim() : '';

  if (!testUrl || !result || !btn) return;

  btn.disabled = true;
  result.className = 'text-[11px] mt-2 text-slate-400 font-mono';
  result.textContent = 'Testing connection...';
  result.classList.remove('hidden');

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3500);
    const res = await fetch(`${testUrl}/`, { method: 'GET', signal: controller.signal });
    clearTimeout(timeout);

    if (res.ok) {
      result.className = 'text-[11px] mt-2 text-emerald-400 font-mono';
      result.textContent = 'Connection verified! Health check responded (200 OK).';
    } else {
      result.className = 'text-[11px] mt-2 text-rose-400 font-mono';
      result.textContent = `Server reachable, but returned HTTP ${res.status}.`;
    }
  } catch (err) {
    result.className = 'text-[11px] mt-2 text-rose-400 font-mono';
    result.textContent = `Failed to connect: ${err.message || 'Network error'}.`;
  } finally {
    btn.disabled = false;
  }
}

function saveSettings() {
  const input = document.getElementById('apiUrlInput');
  const newUrl = input ? input.value.trim() : '';

  if (newUrl) {
    APP_STATE.apiUrl = newUrl;
    localStorage.setItem('qs_api_url', newUrl);
  }

  closeSettingsModal();
  checkBackendHealth();
}

function handleGlobalKeydown(e) {
  // Ctrl+K -> New Query
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    startNewSession(true);
  }

  // Ctrl+\ -> Toggle Sidebar
  if ((e.ctrlKey || e.metaKey) && e.key === '\\') {
    e.preventDefault();
    toggleSidebarCollapse();
  }

  // Escape -> Close modal
  if (e.key === 'Escape') {
    closeSettingsModal();
    toggleSidebar(false);
  }
}
