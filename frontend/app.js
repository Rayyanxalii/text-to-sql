/**
 * QuerySentinel — Frontend Application Logic
 * Minimalist Natural Language Database Interface
 */

/* -------------------------------------------------------------------------
   State & Configuration
   ------------------------------------------------------------------------- */
const APP_STATE = {
  apiUrl: localStorage.getItem('qm_api_url') || 'http://127.0.0.1:8000',
  isOnline: false,
  demoFallback: localStorage.getItem('qm_demo_fallback') !== 'false',
  currentConversationId: null,
  sessions: JSON.parse(localStorage.getItem('qm_sessions') || '[]'),
  activeSessionMessages: [],
  pendingClarification: false,
  isExecuting: false,
  chartInstances: {},
};

/* -------------------------------------------------------------------------
   Initialization
   ------------------------------------------------------------------------- */
document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  initSession();
  checkBackendHealth();
  setInterval(checkBackendHealth, 7000);
});

/* -------------------------------------------------------------------------
   Backend Connectivity Check
   ------------------------------------------------------------------------- */
async function checkBackendHealth() {
  const dot = document.getElementById('connIndicator');
  const label = document.getElementById('connLabel');

  try {
    const res = await fetch(`${APP_STATE.apiUrl}/`, {
      method: 'GET',
      signal: AbortSignal.timeout(2800)
    });

    if (res.ok) {
      APP_STATE.isOnline = true;
      dot.className = 'w-2 h-2 rounded-full bg-emerald-400';
      label.innerHTML = `<span class="text-emerald-400 font-semibold">Live</span> (8000)`;
    } else {
      setOfflineState();
    }
  } catch (err) {
    setOfflineState();
  }
}

function setOfflineState() {
  APP_STATE.isOnline = false;
  const dot = document.getElementById('connIndicator');
  const label = document.getElementById('connLabel');
  dot.className = 'w-2 h-2 rounded-full bg-cyan-400';
  label.innerHTML = `<span class="text-cyan-400 font-medium">Demo Mode</span>`;
}

/* -------------------------------------------------------------------------
   Session & History Management
   ------------------------------------------------------------------------- */
function generateId() {
  return 'conv-' + Math.random().toString(36).substring(2, 10);
}

function initSession() {
  if (APP_STATE.sessions.length === 0) {
    startNewSession();
  } else {
    loadSession(APP_STATE.sessions[0].id);
  }
  renderSessionHistory();
}

function startNewSession() {
  const newId = generateId();
  APP_STATE.currentConversationId = newId;
  APP_STATE.activeSessionMessages = [];
  APP_STATE.pendingClarification = false;

  const newSession = {
    id: newId,
    title: 'New Query',
    timestamp: Date.now(),
    messages: []
  };
  APP_STATE.sessions.unshift(newSession);
  saveSessions();

  renderSessionHistory();
  renderCurrentMessages();
  document.getElementById('queryInput').focus();
}

function loadSession(id) {
  const session = APP_STATE.sessions.find(s => s.id === id);
  if (!session) return;
  APP_STATE.currentConversationId = session.id;
  APP_STATE.activeSessionMessages = session.messages || [];
  APP_STATE.pendingClarification = false;

  renderSessionHistory();
  renderCurrentMessages();
}

function saveSessions() {
  if (APP_STATE.sessions.length > 20) APP_STATE.sessions.pop();
  localStorage.setItem('qm_sessions', JSON.stringify(APP_STATE.sessions));
  document.getElementById('sessionCount').textContent = APP_STATE.sessions.length;
}

function updateSessionTitle(id, title) {
  const session = APP_STATE.sessions.find(s => s.id === id);
  if (session && session.title === 'New Query') {
    session.title = title.length > 32 ? title.substring(0, 32) + '...' : title;
    saveSessions();
    renderSessionHistory();
  }
}

function deleteSession(event, id) {
  event.stopPropagation();
  APP_STATE.sessions = APP_STATE.sessions.filter(s => s.id !== id);
  saveSessions();
  if (APP_STATE.sessions.length === 0) {
    startNewSession();
  } else if (APP_STATE.currentConversationId === id) {
    loadSession(APP_STATE.sessions[0].id);
  } else {
    renderSessionHistory();
  }
}

function renderSessionHistory() {
  const list = document.getElementById('sessionHistoryList');
  list.innerHTML = '';

  APP_STATE.sessions.forEach(session => {
    const isActive = session.id === APP_STATE.currentConversationId;
    const item = document.createElement('div');
    item.className = `group flex items-center justify-between px-2.5 py-2 rounded-lg cursor-pointer text-xs transition ${
      isActive 
        ? 'bg-brand-500/15 text-white font-medium border border-brand-500/30' 
        : 'text-slate-400 hover:bg-dark-800 hover:text-slate-200 border border-transparent'
    }`;
    item.onclick = () => loadSession(session.id);

    item.innerHTML = `
      <div class="flex items-center gap-2 truncate">
        <i data-lucide="message-square" class="w-3.5 h-3.5 ${isActive ? 'text-brand-400' : 'text-slate-500'} flex-shrink-0"></i>
        <span class="truncate">${escapeHtml(session.title)}</span>
      </div>
      <button onclick="deleteSession(event, '${session.id}')" class="opacity-0 group-hover:opacity-100 hover:text-rose-400 p-0.5 rounded transition">
        <i data-lucide="trash-2" class="w-3 h-3"></i>
      </button>
    `;
    list.appendChild(item);
  });

  document.getElementById('sessionCount').textContent = APP_STATE.sessions.length;
  lucide.createIcons();
}

/* -------------------------------------------------------------------------
   Query Execution & Response Handling
   ------------------------------------------------------------------------- */
async function submitQuery() {
  if (APP_STATE.isExecuting) return;
  const input = document.getElementById('queryInput');
  const question = input.value.trim();
  if (!question) return;

  input.value = '';
  autoResizeTextarea(input);

  const userMsg = {
    role: 'user',
    text: question,
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  };
  addMessage(userMsg);
  updateSessionTitle(APP_STATE.currentConversationId, question);

  setExecuting(true);

  try {
    if (APP_STATE.isOnline) {
      const response = await fetch(`${APP_STATE.apiUrl}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: question,
          conversation_id: APP_STATE.currentConversationId
        })
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error (${response.status})`);
      }

      const result = await response.json();
      handleApiResponse(result, question);
    } else {
      // Demo response when backend is offline
      await new Promise(r => setTimeout(r, 600));
      const mockResult = generateMockAgentResponse(question);
      handleApiResponse(mockResult, question);
    }
  } catch (err) {
    console.error('Execution error:', err);
    addMessage({
      role: 'error',
      text: `Request failed: ${err.message}`,
      timestamp: new Date().toLocaleTimeString()
    });
  } finally {
    setExecuting(false);
  }
}

async function submitClarification(clarificationText) {
  if (APP_STATE.isExecuting || !clarificationText.trim()) return;

  const userMsg = {
    role: 'user',
    text: clarificationText,
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  };
  addMessage(userMsg);
  setExecuting(true);

  try {
    if (APP_STATE.isOnline) {
      const response = await fetch(`${APP_STATE.apiUrl}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          clarification_answer: clarificationText,
          conversation_id: APP_STATE.currentConversationId
        })
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Resume failed (${response.status})`);
      }

      const result = await response.json();
      handleApiResponse(result, clarificationText);
    } else {
      await new Promise(r => setTimeout(r, 600));
      const simulatedResumeResult = {
        answer: `Filtered results using clarification: "${clarificationText}". Total 34 patients matched.`,
        sql: `SELECT p.patient_id, p.full_name, p.age, d.name AS department, p.admission_date\nFROM patients p\nJOIN departments d ON p.department_id = d.department_id\nWHERE LOWER(d.name) = 'cardiology'\nORDER BY p.admission_date DESC\nLIMIT 10;`,
        results: [
          { patient_id: 104, full_name: "Sarah Miller", age: 54, department: "Cardiology", admission_date: "2025-08-14" },
          { patient_id: 189, full_name: "James Wilson", age: 67, department: "Cardiology", admission_date: "2025-09-02" },
          { patient_id: 201, full_name: "Fatima Noor", age: 43, department: "Cardiology", admission_date: "2025-09-18" },
          { patient_id: 233, full_name: "David Chen", age: 61, department: "Cardiology", admission_date: "2025-10-01" }
        ],
        cache_hit: false,
        latency_ms: 380,
      };
      handleApiResponse(simulatedResumeResult, clarificationText);
    }
  } catch (err) {
    addMessage({
      role: 'error',
      text: `Failed to resume: ${err.message}`,
      timestamp: new Date().toLocaleTimeString()
    });
  } finally {
    setExecuting(false);
  }
}

function handleApiResponse(data, originalQuery) {
  // Clarification request
  if (data && data.requires_clarification) {
    APP_STATE.pendingClarification = true;
    addMessage({
      role: 'clarification',
      question: data.clarification_question || 'Additional clarification required to form an exact query.',
      timestamp: new Date().toLocaleTimeString()
    });
    return;
  }

  // Plain string answer (FastAPI default)
  if (typeof data === 'string') {
    addMessage({
      role: 'assistant',
      answer: data,
      sql: extractSqlFromString(data) || null,
      results: null,
      cache_hit: false,
      latency_ms: null,
      timestamp: new Date().toLocaleTimeString()
    });
    return;
  }

  // Structured response object
  addMessage({
    role: 'assistant',
    answer: data.answer || 'Query completed successfully.',
    sql: data.sql || null,
    results: data.results || (data.db_result ? formatDbResult(data.db_result) : null),
    cache_hit: Boolean(data.cache_hit),
    latency_ms: data.latency_ms || null,
    timestamp: new Date().toLocaleTimeString()
  });
}

/* -------------------------------------------------------------------------
   Render Messages & Views
   ------------------------------------------------------------------------- */
function addMessage(msg) {
  APP_STATE.activeSessionMessages.push(msg);

  const current = APP_STATE.sessions.find(s => s.id === APP_STATE.currentConversationId);
  if (current) {
    current.messages = APP_STATE.activeSessionMessages;
    saveSessions();
  }

  renderCurrentMessages();
}

function renderCurrentMessages() {
  const hero = document.getElementById('welcomeHero');
  const container = document.getElementById('threadContainer');

  if (APP_STATE.activeSessionMessages.length === 0) {
    hero.classList.remove('hidden');
    container.innerHTML = '';
    return;
  }

  hero.classList.add('hidden');
  container.innerHTML = '';

  APP_STATE.activeSessionMessages.forEach((msg, idx) => {
    const msgNode = createMessageElement(msg, idx);
    container.appendChild(msgNode);
  });

  const scrollArea = document.getElementById('messagesContainer');
  scrollArea.scrollTop = scrollArea.scrollHeight;
  lucide.createIcons();
}

function createMessageElement(msg, index) {
  const wrap = document.createElement('div');
  wrap.className = 'w-full animate-fade-in';

  if (msg.role === 'user') {
    wrap.innerHTML = `
      <div class="flex justify-end items-start gap-3 pl-12">
        <div class="space-y-1 text-right">
          <div class="inline-block bg-gradient-to-r from-brand-600 to-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm shadow-md shadow-brand-500/10 leading-relaxed max-w-xl text-left">
            ${escapeHtml(msg.text)}
          </div>
          <div class="text-[10px] text-slate-500 pr-1">${msg.timestamp || ''}</div>
        </div>
        <div class="w-7 h-7 rounded-lg bg-dark-800 border border-white/[0.08] flex items-center justify-center text-slate-400 flex-shrink-0 mt-0.5">
          <i data-lucide="user" class="w-3.5 h-3.5"></i>
        </div>
      </div>
    `;
    return wrap;
  }

  if (msg.role === 'clarification') {
    wrap.innerHTML = `
      <div class="flex items-start gap-3 pr-12">
        <div class="w-7 h-7 rounded-lg bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400 flex-shrink-0 mt-0.5">
          <i data-lucide="help-circle" class="w-3.5 h-3.5"></i>
        </div>
        <div class="flex-1 max-w-2xl bg-amber-500/[0.06] border border-amber-500/30 rounded-2xl p-4 space-y-3 shadow-lg shadow-amber-500/5">
          <div class="flex items-center gap-2">
            <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/30">
              Clarification Needed
            </span>
          </div>
          <p class="text-sm text-slate-200 leading-relaxed font-medium">
            ${escapeHtml(msg.question)}
          </p>

          <div class="space-y-2 pt-1">
            <div class="flex gap-2">
              <input
                type="text"
                id="clarify-input-${index}"
                placeholder="Type your clarification..."
                class="flex-1 px-3 py-2 rounded-xl bg-dark-900 border border-amber-500/30 text-xs text-white placeholder-slate-500 outline-none focus:border-amber-400"
                onkeydown="if(event.key==='Enter') submitClarification(this.value)"
              />
              <button
                onclick="submitClarification(document.getElementById('clarify-input-${index}').value)"
                class="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-dark-950 font-semibold text-xs transition"
              >
                Continue
              </button>
            </div>

            <div class="flex items-center gap-1.5 flex-wrap text-[11px] text-slate-400 pt-1">
              <span class="text-slate-500">Quick options:</span>
              <button onclick="submitClarification('Count patients by admission dates')" class="px-2 py-0.5 rounded bg-dark-800 hover:bg-dark-750 text-slate-300 border border-white/[0.06]">
                "By admission dates"
              </button>
              <button onclick="submitClarification('Count patients by appointment consultation dates')" class="px-2 py-0.5 rounded bg-dark-800 hover:bg-dark-750 text-slate-300 border border-white/[0.06]">
                "By consultation dates"
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
    return wrap;
  }

  if (msg.role === 'error') {
    wrap.innerHTML = `
      <div class="flex items-start gap-3 pr-12">
        <div class="w-7 h-7 rounded-lg bg-rose-500/20 border border-rose-500/30 flex items-center justify-center text-rose-400 flex-shrink-0 mt-0.5">
          <i data-lucide="alert-triangle" class="w-3.5 h-3.5"></i>
        </div>
        <div class="bg-rose-500/[0.07] border border-rose-500/30 rounded-2xl p-4 text-xs text-rose-300 space-y-1">
          <div class="font-semibold">Notice</div>
          <p class="leading-relaxed">${escapeHtml(msg.text)}</p>
        </div>
      </div>
    `;
    return wrap;
  }

  // Assistant Response Card
  const hasSql = Boolean(msg.sql);
  const hasResults = msg.results && msg.results.length > 0;
  const canChart = hasResults && detectChartableData(msg.results);

  wrap.innerHTML = `
    <div class="flex items-start gap-3 pr-4 md:pr-12">
      <div class="w-7 h-7 rounded-lg bg-gradient-to-tr from-brand-500 to-cyan-500 flex items-center justify-center text-white flex-shrink-0 mt-0.5 shadow-md shadow-brand-500/20">
        <i data-lucide="bot" class="w-3.5 h-3.5"></i>
      </div>

      <div class="flex-1 space-y-3 max-w-2xl">
        <div class="glass-panel bg-dark-850/90 border border-white/[0.08] rounded-2xl p-4 space-y-3 shadow-xl">
          <div class="flex items-center justify-between border-b border-white/[0.06] pb-2">
            <div class="flex items-center gap-2">
              ${msg.cache_hit 
                ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                     Cache HIT
                   </span>`
                : ''
              }
              ${msg.latency_ms ? `
                <span class="text-[10px] text-slate-500 font-mono">
                  ${msg.latency_ms}ms
                </span>
              ` : ''}
            </div>

            <div class="text-[10px] text-slate-500 font-mono">${msg.timestamp || ''}</div>
          </div>

          <div class="text-sm text-slate-200 leading-relaxed font-sans">
            ${formatMarkdownAnswer(msg.answer)}
          </div>
        </div>

        ${(hasSql || hasResults) ? `
          <div class="border border-white/[0.08] bg-dark-900 rounded-2xl overflow-hidden shadow-xl">
            <div class="flex items-center justify-between border-b border-white/[0.06] bg-dark-850/60 px-3">
              <div class="flex items-center gap-1">
                ${hasSql ? `
                  <button onclick="switchTab(${index}, 'sql')" id="tab-btn-sql-${index}" class="px-3 py-2 text-xs font-semibold text-brand-400 border-b-2 border-brand-500 flex items-center gap-1.5 transition">
                    <i data-lucide="terminal" class="w-3.5 h-3.5"></i> SQL
                  </button>
                ` : ''}
                ${hasResults ? `
                  <button onclick="switchTab(${index}, 'table')" id="tab-btn-table-${index}" class="px-3 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 border-b-2 border-transparent flex items-center gap-1.5 transition">
                    <i data-lucide="table" class="w-3.5 h-3.5"></i> Results (${msg.results.length})
                  </button>
                ` : ''}
                ${canChart ? `
                  <button onclick="switchTab(${index}, 'chart')" id="tab-btn-chart-${index}" class="px-3 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 border-b-2 border-transparent flex items-center gap-1.5 transition">
                    <i data-lucide="pie-chart" class="w-3.5 h-3.5"></i> Chart
                  </button>
                ` : ''}
              </div>

              <div class="flex items-center gap-1">
                ${hasSql ? `
                  <button onclick="copyToClipboard('${encodeURIComponent(msg.sql)}', this)" class="px-2 py-1 rounded text-[11px] text-slate-400 hover:text-white hover:bg-dark-800 transition flex items-center gap-1">
                    <i data-lucide="copy" class="w-3 h-3"></i> Copy
                  </button>
                ` : ''}
                ${hasResults ? `
                  <button onclick="exportCsv(${index})" class="px-2 py-1 rounded text-[11px] text-slate-400 hover:text-white hover:bg-dark-800 transition flex items-center gap-1">
                    <i data-lucide="download" class="w-3 h-3"></i> CSV
                  </button>
                ` : ''}
              </div>
            </div>

            <div class="p-3">
              ${hasSql ? `
                <div id="tab-pane-sql-${index}" class="block">
                  <div class="p-3 bg-dark-950 rounded-xl border border-white/[0.04] overflow-x-auto font-mono text-xs leading-relaxed text-slate-300">
                    ${highlightSql(msg.sql)}
                  </div>
                </div>
              ` : ''}

              ${hasResults ? `
                <div id="tab-pane-table-${index}" class="${hasSql ? 'hidden' : 'block'} space-y-2">
                  <div class="overflow-x-auto rounded-xl border border-white/[0.06] max-h-72">
                    <table class="w-full text-left text-xs text-slate-300">
                      <thead class="bg-dark-800 text-slate-400 uppercase text-[10px] font-semibold sticky top-0 border-b border-white/[0.06]">
                        <tr>
                          ${Object.keys(msg.results[0]).map(col => `<th class="px-3 py-2.5 font-mono">${escapeHtml(col)}</th>`).join('')}
                        </tr>
                      </thead>
                      <tbody class="divide-y divide-white/[0.04] bg-dark-950/60 font-mono text-[11px]">
                        ${msg.results.map(row => `
                          <tr class="hover:bg-dark-800/40 transition">
                            ${Object.values(row).map(val => `<td class="px-3 py-2 whitespace-nowrap text-slate-300">${escapeHtml(String(val ?? ''))}</td>`).join('')}
                          </tr>
                        `).join('')}
                      </tbody>
                    </table>
                  </div>
                </div>
              ` : ''}

              ${canChart ? `
                <div id="tab-pane-chart-${index}" class="hidden p-2">
                  <div class="h-64 relative">
                    <canvas id="chart-canvas-${index}"></canvas>
                  </div>
                </div>
              ` : ''}
            </div>
          </div>
        ` : ''}
      </div>
    </div>
  `;

  return wrap;
}

/* -------------------------------------------------------------------------
   Tab Switching & Auto-Charting (Chart.js)
   ------------------------------------------------------------------------- */
function switchTab(index, tabName) {
  const tabs = ['sql', 'table', 'chart'];
  tabs.forEach(t => {
    const btn = document.getElementById(`tab-btn-${t}-${index}`);
    const pane = document.getElementById(`tab-pane-${t}-${index}`);
    if (!btn || !pane) return;

    if (t === tabName) {
      btn.className = 'px-3 py-2 text-xs font-semibold text-brand-400 border-b-2 border-brand-500 flex items-center gap-1.5 transition';
      pane.classList.remove('hidden');
      pane.classList.add('block');
    } else {
      btn.className = 'px-3 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 border-b-2 border-transparent flex items-center gap-1.5 transition';
      pane.classList.remove('block');
      pane.classList.add('hidden');
    }
  });

  if (tabName === 'chart') {
    const msg = APP_STATE.activeSessionMessages[index];
    if (msg && msg.results) {
      renderChartForMessage(index, msg.results);
    }
  }
}

function detectChartableData(results) {
  if (!results || results.length < 2) return false;
  const sample = results[0];
  const keys = Object.keys(sample);
  const hasNumeric = keys.some(k => typeof sample[k] === 'number');
  const hasCategorical = keys.some(k => typeof sample[k] === 'string');
  return hasNumeric && hasCategorical;
}

function renderChartForMessage(index, results) {
  const canvas = document.getElementById(`chart-canvas-${index}`);
  if (!canvas) return;

  if (APP_STATE.chartInstances[index]) {
    APP_STATE.chartInstances[index].destroy();
  }

  const keys = Object.keys(results[0]);
  const labelKey = keys.find(k => typeof results[0][k] === 'string') || keys[0];
  const dataKey = keys.find(k => typeof results[0][k] === 'number') || keys[1];

  const labels = results.map(r => r[labelKey]);
  const dataValues = results.map(r => r[dataKey]);

  const ctx = canvas.getContext('2d');
  APP_STATE.chartInstances[index] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: dataKey.replace(/_/g, ' ').toUpperCase(),
        data: dataValues,
        backgroundColor: 'rgba(99, 102, 241, 0.65)',
        borderColor: '#818cf8',
        borderWidth: 1.5,
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: '#94a3b8', font: { family: 'Inter', size: 11 } }
        }
      },
      scales: {
        x: {
          ticks: { color: '#94a3b8', font: { family: 'Inter', size: 10 } },
          grid: { color: 'rgba(255, 255, 255, 0.05)' }
        },
        y: {
          ticks: { color: '#94a3b8', font: { family: 'Inter', size: 10 } },
          grid: { color: 'rgba(255, 255, 255, 0.05)' }
        }
      }
    }
  });
}

/* -------------------------------------------------------------------------
   CSV & Clipboard Utilities
   ------------------------------------------------------------------------- */
function exportCsv(index) {
  const msg = APP_STATE.activeSessionMessages[index];
  if (!msg || !msg.results || msg.results.length === 0) return;

  const keys = Object.keys(msg.results[0]);
  const rows = [keys.join(',')];

  msg.results.forEach(row => {
    const values = keys.map(k => {
      let val = String(row[k] ?? '').replace(/"/g, '""');
      return `"${val}"`;
    });
    rows.push(values.join(','));
  });

  const csvContent = 'data:text/csv;charset=utf-8,' + encodeURIComponent(rows.join('\n'));
  const link = document.createElement('a');
  link.setAttribute('href', csvContent);
  link.setAttribute('download', `query_results_${Date.now()}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function copyToClipboard(encoded, btn) {
  const text = decodeURIComponent(encoded);
  navigator.clipboard.writeText(text);
  const originalText = btn.innerHTML;
  btn.innerHTML = `<i data-lucide="check" class="w-3 h-3 text-emerald-400"></i> Copied!`;
  lucide.createIcons();
  setTimeout(() => {
    btn.innerHTML = originalText;
    lucide.createIcons();
  }, 2000);
}

/* -------------------------------------------------------------------------
   SQL Syntax Highlighter
   ------------------------------------------------------------------------- */
function highlightSql(rawSql) {
  if (!rawSql) return '';
  let s = escapeHtml(rawSql);

  const keywords = [
    'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN', 
    'FULL OUTER JOIN', 'ON', 'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'OFFSET',
    'AS', 'AND', 'OR', 'NOT', 'IN', 'IS NULL', 'IS NOT NULL', 'BETWEEN', 'LIKE',
    'UNION', 'ALL', 'EXISTS', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'ASC', 'DESC'
  ];

  keywords.forEach(kw => {
    const reg = new RegExp(`\\b${kw}\\b`, 'gi');
    s = s.replace(reg, m => `<span class="sql-kw">${m.toUpperCase()}</span>`);
  });

  const functions = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'DATE_PART', 'EXTRACT', 'ROUND', 'COALESCE', 'LOWER', 'UPPER', 'NOW'];
  functions.forEach(fn => {
    const reg = new RegExp(`\\b${fn}\\b(?=\\s*\\()`, 'gi');
    s = s.replace(reg, m => `<span class="sql-fn">${m.toUpperCase()}</span>`);
  });

  s = s.replace(/'([^']*)'/g, `<span class="sql-str">'$1'</span>`);
  s = s.replace(/\b(\d+)\b/g, `<span class="sql-num">$1</span>`);

  return s;
}

function formatMarkdownAnswer(text) {
  if (!text) return '';
  let escaped = escapeHtml(text);
  escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>');
  escaped = escaped.replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded bg-dark-800 text-brand-300 font-mono text-xs">$1</code>');
  return escaped;
}

function escapeHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function extractSqlFromString(str) {
  const match = str.match(/SELECT[\s\S]*?;/i);
  return match ? match[0] : null;
}

function formatDbResult(tuples) {
  if (!Array.isArray(tuples) || tuples.length === 0) return null;
  return tuples.map((t, idx) => ({
    row_id: idx + 1,
    result: String(t)
  }));
}

function usePrompt(text) {
  const input = document.getElementById('queryInput');
  input.value = text;
  input.focus();
  autoResizeTextarea(input);
}

/* -------------------------------------------------------------------------
   Settings
   ------------------------------------------------------------------------- */
function toggleSettingsModal() {
  const modal = document.getElementById('settingsModal');
  modal.classList.toggle('hidden');
}

function saveSettings() {
  const url = document.getElementById('apiUrlInput').value.trim();
  const demo = document.getElementById('demoFallbackToggle').checked;

  APP_STATE.apiUrl = url || 'http://127.0.0.1:8000';
  APP_STATE.demoFallback = demo;

  localStorage.setItem('qm_api_url', APP_STATE.apiUrl);
  localStorage.setItem('qm_demo_fallback', demo);

  toggleSettingsModal();
  checkBackendHealth();
}

/* -------------------------------------------------------------------------
   Input Helpers
   ------------------------------------------------------------------------- */
function handleInputKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    submitQuery();
  }
}

function autoResizeTextarea(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function setExecuting(isExec) {
  APP_STATE.isExecuting = isExec;
  const sendBtn = document.getElementById('sendBtn');
  if (isExec) {
    sendBtn.disabled = true;
    sendBtn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin text-white"></i>`;
  } else {
    sendBtn.disabled = false;
    sendBtn.innerHTML = `<i data-lucide="arrow-up" class="w-4 h-4"></i>`;
  }
  lucide.createIcons();
}

/* -------------------------------------------------------------------------
   Mock Agent Engine (Demo / Offline Fallback)
   ------------------------------------------------------------------------- */
function generateMockAgentResponse(query) {
  const q = query.toLowerCase();

  if (q.includes('cardiology') || q.includes('unclear') || q.includes('clarif')) {
    return {
      requires_clarification: true,
      clarification_question: "Do you want to count cardiology patients based on admission visit dates, or appointment consultation bookings?"
    };
  }

  if (q.includes('patient') && (q.includes('2025') || q.includes('admit'))) {
    return {
      answer: "In **2025**, a total of **150 patients** were admitted to the hospital across all operational departments.",
      sql: "SELECT COUNT(*) AS total_admissions, EXTRACT(YEAR FROM admission_date) AS admission_year\nFROM patients\nWHERE EXTRACT(YEAR FROM admission_date) = 2025\nGROUP BY admission_year;",
      results: [
        { admission_year: 2025, total_admissions: 150 }
      ],
      cache_hit: false,
      latency_ms: 220
    };
  }

  if (q.includes('doctor') || q.includes('top')) {
    return {
      answer: "Here are the **top 5 doctors** ranked by total completed patient consultations. **Dr. Marcus Vance** leads with 142 appointments.",
      sql: "SELECT d.name AS doctor_name, d.specialization, COUNT(a.appointment_id) AS total_appointments\nFROM doctors d\nJOIN appointments a ON d.doctor_id = a.doctor_id\nGROUP BY d.doctor_id, d.name, d.specialization\nORDER BY total_appointments DESC\nLIMIT 5;",
      results: [
        { doctor_name: "Dr. Marcus Vance", specialization: "Cardiology", total_appointments: 142 },
        { doctor_name: "Dr. Elena Rostova", specialization: "Neurology", total_appointments: 128 },
        { doctor_name: "Dr. Tariq Mahmood", specialization: "Pediatrics", total_appointments: 115 },
        { doctor_name: "Dr. Sarah Jenkins", specialization: "Orthopedics", total_appointments: 98 },
        { doctor_name: "Dr. Claire Dubois", specialization: "General Medicine", total_appointments: 89 }
      ],
      cache_hit: true,
      latency_ms: 45
    };
  }

  if (q.includes('wait') || q.includes('time') || q.includes('department')) {
    return {
      answer: "The average patient wait time is highest in **Emergency** (38.5 mins) and lowest in **Pediatrics** (14.1 mins).",
      sql: "SELECT dep.name AS department, ROUND(AVG(a.wait_time_minutes), 1) AS avg_wait_mins\nFROM departments dep\nJOIN doctors doc ON dep.department_id = doc.department_id\nJOIN appointments a ON doc.doctor_id = a.doctor_id\nGROUP BY dep.department_id, dep.name\nORDER BY avg_wait_mins DESC;",
      results: [
        { department: "Emergency", avg_wait_mins: 38.5 },
        { department: "Orthopedics", avg_wait_mins: 26.2 },
        { department: "Cardiology", avg_wait_mins: 22.0 },
        { department: "Neurology", avg_wait_mins: 18.4 },
        { department: "Pediatrics", avg_wait_mins: 14.1 }
      ],
      cache_hit: false,
      latency_ms: 310
    };
  }

  return {
    answer: `Executed query for: "${query}". Found 4 matching records meeting your criteria.`,
    sql: `SELECT p.patient_id, p.full_name, p.status, d.name AS department\nFROM patients p\nLEFT JOIN departments d ON p.department_id = d.department_id\nLIMIT 4;`,
    results: [
      { patient_id: 1, full_name: "Alice Johnson", status: "Active", department: "Cardiology" },
      { patient_id: 2, full_name: "Robert Smith", status: "Discharged", department: "Neurology" },
      { patient_id: 3, full_name: "Emma Watson", status: "Active", department: "Pediatrics" },
      { patient_id: 4, full_name: "Liam Davis", status: "Admitted", department: "Orthopedics" }
    ],
    cache_hit: false,
    latency_ms: 280
  };
}
