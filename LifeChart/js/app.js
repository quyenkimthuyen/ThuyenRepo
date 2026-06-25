import { ALL_TRADES } from './data/trades.js';
import { createInitialState, clamp } from './game/state.js';
import {
  canAffordTrade,
  executeTrade,
  advanceWeek,
  getWeeklyTradeOptions,
  normalizePortfolio,
  getEventModifier,
} from './game/engine.js';
import { analyzePatterns, classifyArchetype } from './game/ai-mirror.js';
import { saveGame, loadGame, clearSave } from './storage.js';
import { initChart, updateChart } from './ui/chart.js';

const PORTFOLIO_COLORS = {
  career: '#58a6ff',
  learning: '#bc8cff',
  health: '#3fb950',
  family: '#f778ba',
  fun: '#d29922',
};

const PORTFOLIO_LABELS = {
  career: 'Career',
  learning: 'Learning',
  health: 'Health',
  family: 'Family',
  fun: 'Fun',
};

let state = createInitialState();
let weeklyOptions = [];
let selectedTrade = null;
let currentFilter = 'all';

function init() {
  initChart();
  bindEvents();

  const saved = loadGame();
  if (saved) {
    state = saved;
    weeklyOptions = getWeeklyTradeOptions(ALL_TRADES, state);
    showToast('Đã tải game đã lưu', 'info');
  } else {
    weeklyOptions = getWeeklyTradeOptions(ALL_TRADES, state);
    recordHistory(state);
  }

  render();
}

function bindEvents() {
  document.getElementById('btn-save').addEventListener('click', () => {
    if (saveGame(state)) showToast('Đã lưu game!', 'success');
    else showToast('Lỗi khi lưu', 'error');
  });

  document.getElementById('btn-load').addEventListener('click', () => {
    const saved = loadGame();
    if (saved) {
      state = saved;
      weeklyOptions = getWeeklyTradeOptions(ALL_TRADES, state);
      render();
      showToast('Đã tải game!', 'success');
    } else {
      showToast('Không có save game', 'error');
    }
  });

  document.getElementById('btn-new-game').addEventListener('click', () => {
    if (confirm('Bắt đầu game mới? Tiến trình hiện tại sẽ mất.')) {
      clearSave();
      state = createInitialState();
      weeklyOptions = getWeeklyTradeOptions(ALL_TRADES, state);
      recordHistory(state);
      render();
      showToast('Game mới bắt đầu!', 'info');
    }
  });

  document.getElementById('btn-next-week').addEventListener('click', () => {
    if (state.weekTrades.length === 0) {
      showToast('Hãy chọn ít nhất 1 trade trước khi kết thúc tuần', 'error');
      return;
    }

    const resolved = advanceWeek(state);

    if (resolved.length > 0) {
      const successes = resolved.filter(t => t.success).length;
      showToast(`${resolved.length} trade đã đóng (${successes} thành công)`, 'info');
    }

    if (state.totalDecisions > 0 && state.totalDecisions % 50 === 0) {
      state.archetype = classifyArchetype(state);
    }

    weeklyOptions = getWeeklyTradeOptions(ALL_TRADES, state);
    render();

    if (state.gameOver) {
      showGameOver();
    }
  });

  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.dataset.filter;
      renderAvailableTrades();
    });
  });

  document.getElementById('modal-close').addEventListener('click', closeModal);
  document.getElementById('modal-confirm').addEventListener('click', confirmTrade);
  document.getElementById('trade-modal').addEventListener('click', (e) => {
    if (e.target.id === 'trade-modal') closeModal();
  });
}

function recordHistory(s) {
  s.history.push({
    week: s.week,
    age: s.age,
    health: s.health,
    wealth: s.wealth,
    happiness: s.happiness,
    knowledge: s.knowledge,
    relationships: s.relationships,
    confidence: s.confidence,
    money: s.money,
  });
}

function render() {
  renderHeader();
  renderAssets();
  renderPortfolio();
  renderEmotions();
  renderDrawdowns();
  renderMarket();
  renderAvailableTrades();
  renderOpenTrades();
  renderClosedTrades();
  renderJournal();
  renderAIMirror();
  renderArchetype();
  updateChart(state);

  const nextBtn = document.getElementById('btn-next-week');
  nextBtn.disabled = state.weekTrades.length === 0 || state.gameOver;
}

function renderHeader() {
  document.getElementById('stat-age').textContent = state.age;
  document.getElementById('stat-week').textContent = state.week;
  document.getElementById('stat-time').textContent = `${state.timeCapital}h`;
  document.getElementById('stat-energy').textContent = Math.round(state.energy);
  document.getElementById('stat-money').textContent = `$${state.money}`;
}

function renderAssets() {
  const stats = ['health', 'wealth', 'happiness', 'knowledge', 'relationships', 'confidence', 'reputation'];
  for (const stat of stats) {
    const val = stat === 'knowledge' ? state[stat] : state[stat];
    const max = stat === 'knowledge' ? Math.max(100, val) : 100;
    const pct = Math.min(100, (val / max) * 100);
    const bar = document.getElementById(`bar-${stat}`);
    const valEl = document.getElementById(`val-${stat}`);
    if (bar) bar.style.width = `${pct}%`;
    if (valEl) valEl.textContent = Math.round(val);
  }
}

function renderPortfolio() {
  const chart = document.getElementById('portfolio-chart');
  const sliders = document.getElementById('portfolio-sliders');
  state.portfolio = normalizePortfolio(state.portfolio);

  chart.innerHTML = Object.entries(state.portfolio).map(([key, val]) =>
    `<div class="portfolio-segment" style="flex:${val};background:${PORTFOLIO_COLORS[key]}" title="${PORTFOLIO_LABELS[key]}: ${val}%">${val > 12 ? val + '%' : ''}</div>`
  ).join('');

  sliders.innerHTML = Object.entries(state.portfolio).map(([key, val]) =>
    `<div class="portfolio-row">
      <span style="color:${PORTFOLIO_COLORS[key]}">${PORTFOLIO_LABELS[key]}</span>
      <input type="range" min="5" max="60" value="${val}" data-portfolio="${key}">
      <span>${val}%</span>
    </div>`
  ).join('');

  sliders.querySelectorAll('input[type="range"]').forEach(input => {
    input.addEventListener('input', () => {
      const key = input.dataset.portfolio;
      state.portfolio[key] = parseInt(input.value);
      state.portfolio = normalizePortfolio(state.portfolio);
      renderPortfolio();
    });
  });
}

function renderEmotions() {
  const grid = document.getElementById('emotion-grid');
  const emotionColors = {
    fear: '#f85149',
    greed: '#d29922',
    stress: '#f0883e',
    confidence: '#58a6ff',
    discipline: '#3fb950',
  };

  grid.innerHTML = Object.entries(state.emotions).map(([key, val]) =>
    `<div class="emotion-item">
      <span>${capitalize(key)}</span>
      <div class="emotion-bar"><div class="emotion-fill" style="width:${val}%;background:${emotionColors[key]}"></div></div>
      <span>${val}</span>
    </div>`
  ).join('');
}

function renderDrawdowns() {
  const list = document.getElementById('drawdown-list');
  const entries = Object.entries(state.drawdowns);

  if (entries.length === 0) {
    list.innerHTML = '<div class="drawdown-empty">Không có drawdown đáng kể ✓</div>';
    return;
  }

  list.innerHTML = entries.map(([key, val]) =>
    `<div class="drawdown-item">
      <span>${capitalize(key)} Drawdown</span>
      <span class="value">-${val}%</span>
    </div>`
  ).join('');
}

function renderMarket() {
  const el = document.getElementById('market-event');
  if (!state.currentEvent) {
    el.className = 'market-event empty';
    el.innerHTML = 'Chưa có sự kiện thị trường — có thể xuất hiện tuần tới.';
    return;
  }

  const ev = state.currentEvent;
  el.className = 'market-event';
  el.innerHTML = `
    <div class="event-name">${ev.name}</div>
    <div class="event-desc">${ev.description}</div>
    <div class="event-duration">Còn ${ev.weeksRemaining} tuần</div>
  `;
}

function renderAvailableTrades() {
  const container = document.getElementById('available-trades');
  const filtered = currentFilter === 'all'
    ? weeklyOptions
    : weeklyOptions.filter(t => t.category === currentFilter);

  container.innerHTML = filtered.map(trade => {
    const affordable = canAffordTrade(state, trade, state.currentEvent);
    const catMod = getEventModifier(state.currentEvent, trade.category);
    const evBonus = catMod > 1 ? ' ↑' : catMod < 1 ? ' ↓' : '';

    return `<div class="trade-card ${affordable ? '' : 'disabled'}" data-trade-id="${trade.id}">
      <span class="trade-cat ${trade.category}">${trade.category}${evBonus}</span>
      <h4>${trade.title}</h4>
      <div class="trade-meta">
        ${trade.cost.time}h · ${Math.round(trade.successRate * 100)}% · Delay ${trade.delay}w
      </div>
    </div>`;
  }).join('');

  container.querySelectorAll('.trade-card:not(.disabled)').forEach(card => {
    card.addEventListener('click', () => {
      const trade = ALL_TRADES.find(t => t.id === card.dataset.tradeId);
      if (trade) openModal(trade);
    });
  });
}

function renderOpenTrades() {
  const list = document.getElementById('open-trades-list');
  document.getElementById('open-count').textContent = state.openTrades.length;

  if (state.openTrades.length === 0) {
    list.innerHTML = '<div class="trade-item pending">Không có open trades</div>';
    return;
  }

  list.innerHTML = state.openTrades.map(t =>
    `<div class="trade-item pending">
      <div class="trade-title">${t.title}</div>
      <div class="trade-info">Tuần ${t.weekOpened} · Còn ${t.weeksRemaining}w · ${Math.round(t.successRate * 100)}%</div>
    </div>`
  ).join('');
}

function renderClosedTrades() {
  const list = document.getElementById('closed-trades-list');
  const trades = state.closedTrades.slice(0, 20);

  if (trades.length === 0) {
    list.innerHTML = '<div class="trade-item">Chưa có closed trades</div>';
    return;
  }

  list.innerHTML = trades.map(t =>
    `<div class="trade-item ${t.outcome}">
      <div class="trade-title">${t.title}</div>
      <div class="trade-info">Tuần ${t.weekOpened} · ${t.outcome === 'success' ? '✓ Thành công' : '✗ Thất bại'}</div>
    </div>`
  ).join('');
}

function renderJournal() {
  const list = document.getElementById('journal-list');
  const entries = state.journal.slice(0, 15);

  if (entries.length === 0) {
    list.innerHTML = '<p style="color:var(--text-secondary);font-size:0.8rem">Journal trống — bắt đầu trade để ghi nhật ký.</p>';
    return;
  }

  list.innerHTML = entries.map(j =>
    `<div class="journal-entry">
      <div class="journal-week">Tuần ${j.week} · ${j.emotion || '—'}</div>
      <div class="journal-decision">${j.decision}</div>
      <div class="journal-detail">Lý do: ${j.reason}</div>
      <div class="journal-detail">Kết quả: ${j.outcome}</div>
    </div>`
  ).join('');
}

function renderAIMirror() {
  const el = document.getElementById('ai-mirror');
  const insights = analyzePatterns(state);

  if (state.journal.length < 3) {
    el.innerHTML = '<p class="mirror-placeholder">Thực hiện thêm quyết định để AI Mirror phản chiếu hành vi của bạn.</p>';
    return;
  }

  el.innerHTML = `
    <p style="margin-bottom:0.5rem;color:var(--text-secondary);font-size:0.75rem">Trong ${Math.min(30, state.journal.length)} quyết định gần đây:</p>
    ${insights.map(i => `<div class="mirror-insight">${i}</div>`).join('')}
  `;
}

function renderArchetype() {
  const box = document.getElementById('archetype');
  if (!state.archetype) {
    box.classList.add('hidden');
    return;
  }

  box.classList.remove('hidden');
  box.innerHTML = `
    <h3>${state.archetype.name}</h3>
    <p><strong>${state.archetype.traits}</strong></p>
    <p>${state.archetype.description}</p>
    <p style="margin-top:0.5rem;font-size:0.7rem;color:var(--text-secondary)">Phân loại sau ${state.totalDecisions} quyết định — chỉ phản chiếu, không đánh giá.</p>
  `;
}

function openModal(trade) {
  selectedTrade = trade;
  document.getElementById('modal-title').textContent = trade.title;
  document.getElementById('modal-desc').textContent = trade.description;

  const costList = document.getElementById('modal-cost');
  costList.innerHTML = formatEffects(trade.cost);

  const rewardList = document.getElementById('modal-reward');
  rewardList.innerHTML = formatEffects(trade.reward);

  const riskList = document.getElementById('modal-risk');
  riskList.innerHTML = Object.keys(trade.risk).length > 0
    ? formatEffects(trade.risk)
    : '<li>Không có rủi ro rõ ràng</li>';

  const catMod = getEventModifier(state.currentEvent, trade.category);
  document.getElementById('modal-prob').textContent =
    `Success Rate: ${Math.round(trade.successRate * catMod * 100)}%${catMod !== 1 ? ' (market adjusted)' : ''} · Delay: ${trade.delay} tuần`;

  document.getElementById('modal-reason').value = '';
  document.getElementById('trade-modal').classList.remove('hidden');
}

function closeModal() {
  document.getElementById('trade-modal').classList.add('hidden');
  selectedTrade = null;
}

function confirmTrade() {
  if (!selectedTrade) return;

  const reason = document.getElementById('modal-reason').value.trim();
  const emotion = document.getElementById('modal-emotion').value;

  const result = executeTrade(state, selectedTrade, reason, emotion, state.currentEvent);

  closeModal();
  render();

  const msg = selectedTrade.delay > 0
    ? `Trade mở — kết quả sau ${selectedTrade.delay} tuần`
    : result.success
      ? 'Trade thành công!'
      : 'Trade thất bại — rủi ro đã xảy ra';

  showToast(msg, result.success ? 'success' : 'error');
}

function formatEffects(effects) {
  const labels = {
    time: 'giờ', energy: 'năng lượng', money: '$',
    health: 'sức khỏe', wealth: 'tài sản', happiness: 'hạnh phúc',
    knowledge: 'kiến thức', relationships: 'quan hệ', confidence: 'tự tin',
    reputation: 'uy tín', stress: 'stress', discipline: 'kỷ luật',
  };

  return Object.entries(effects)
    .filter(([, v]) => v !== 0)
    .map(([k, v]) => {
      const sign = v > 0 ? '+' : '';
      const suffix = k === 'time' ? 'h' : k === 'money' ? '' : '';
      return `<li>${sign}${v}${suffix} ${labels[k] || k}</li>`;
    })
    .join('') || '<li>—</li>';
}

function showToast(message, type = 'info') {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.className = `toast ${type}`;
  setTimeout(() => toast.classList.add('hidden'), 3000);
  toast.classList.remove('hidden');
}

function showGameOver() {
  const balance = Math.round(
    (state.health + state.wealth + state.happiness + state.knowledge + state.relationships) / 5
  );

  setTimeout(() => {
    alert(
      `Game Over!\n\nTuổi: ${state.age} · Tuần: ${state.week}\n` +
      `Life Balance Score: ${balance}/100\n\n` +
      `Health: ${state.health} · Wealth: ${state.wealth}\n` +
      `Happiness: ${state.happiness} · Knowledge: ${state.knowledge}\n` +
      `Relationships: ${state.relationships}\n\n` +
      `Mục tiêu không phải Wealth Max — mà là cân bằng dài hạn.`
    );
  }, 500);
}

function capitalize(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

document.addEventListener('DOMContentLoaded', init);
