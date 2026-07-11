function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function pct(v, digits = 1) {
  if (v == null || Number.isNaN(Number(v))) return '—';
  return `${(Number(v) * 100).toFixed(digits)}%`;
}

function num(v, digits = 2) {
  if (v == null || Number.isNaN(Number(v))) return '—';
  return Number(v).toFixed(digits);
}

function banner(kind, title, text) {
  return `
    <div class="result-banner ${kind}">
      <strong>${esc(title)}</strong>
      ${text ? `<p>${esc(text)}</p>` : ''}
    </div>
  `;
}

function statGrid(items, gridClass = '') {
  const cls = gridClass ? `stat-grid ${gridClass}` : 'stat-grid';
  return `
    <div class="${cls}">
      ${items
        .map(
          (it) => `
        <div class="stat-card">
          <span class="stat-label">${esc(it.label)}</span>
          <span class="stat-value ${it.cls || ''}">${esc(it.value)}</span>
          ${it.hint ? `<span class="stat-hint">${esc(it.hint)}</span>` : ''}
        </div>`,
        )
        .join('')}
    </div>
  `;
}

function formatBoolRule(value, label) {
  if (value == null) return null;
  return `${label}: ${value ? 'Có' : 'Không'}`;
}

function renderTagSignatures(data) {
  const signatures = data?.tag_signatures || {};
  const entries = Object.entries(signatures);
  if (!entries.length) return '';

  return `
    <section class="result-section">
      <h3>Signature tag (mẫu học từ label)</h3>
      <p class="section-note">Mỗi tag có vùng feature đặc trưng — app dùng để nhận diện tình huống giá tương tự.</p>
      <div class="mini-table-wrap">
        <table class="mini-table">
          <thead>
            <tr><th>Tag</th><th>Mẫu</th><th>H4 tăng %</th><th>Dist EMA50</th></tr>
          </thead>
          <tbody>
            ${entries
              .map(([tag, sig]) => {
                const h4 = sig.bool_rates?.h4_trend_up;
                const dist = sig.features?.dist_ema50_pips?.mean;
                return `<tr>
                  <td>${esc(tag)}</td>
                  <td>${sig.count ?? 0}</td>
                  <td>${h4 != null ? pct(h4) : '—'}</td>
                  <td>${num(dist, 1)} pips</td>
                </tr>`;
              })
              .join('')}
          </tbody>
        </table>
      </div>
    </section>
  `;
}

function renderTagProfileCard(tag, profile) {
  if (!profile?.enabled) {
    return `
      <div class="rule-card disabled tag-profile">
        <div class="rule-head">${esc(tag)}</div>
        <p class="muted">${esc(profile?.reason || 'Chưa kích hoạt')}</p>
      </div>
    `;
  }

  const rules = profile.rules || {};
  return `
    <div class="rule-card tag-profile">
      <div class="rule-head">${esc(tag)} <span class="pill">${pct(profile.win_rate)} · ${profile.total} setup</span></div>
      <div class="rule-grid nested">
        ${renderRuleCard('long', rules.long, { hideTagLine: true })}
        ${renderRuleCard('short', rules.short, { hideTagLine: true })}
      </div>
    </div>
  `;
}

function renderTagProfiles(data) {
  const profiles = data?.tag_profiles || {};
  const entries = Object.entries(profiles);
  if (!entries.length) return '';

  const mode = data.rule_mode || 'global';
  const coverage = data.tag_coverage;
  const coverageText = coverage
    ? `${coverage.tagged}/${coverage.total} setup có tag (${pct(coverage.ratio, 0)})`
    : '';

  return `
    <section class="result-section">
      <h3>Pattern theo tag ${mode === 'tag_driven' ? '(đang dùng cho backtest)' : ''}</h3>
      <p class="section-note">
        Mỗi tag học rule riêng từ setup bạn đánh dấu.
        ${mode === 'tag_driven'
          ? 'Backtest vào lệnh khi khớp <strong>bất kỳ profile tag</strong> nào bên dưới.'
          : 'Chưa đủ tag — backtest vẫn dùng rule global.'}
        ${coverageText ? ` · ${esc(coverageText)}` : ''}
      </p>
      ${data.tag_warning ? `<p class="tag-note bad">${esc(data.tag_warning)}</p>` : ''}
      <div class="tag-profile-grid">
        ${entries.map(([tag, prof]) => renderTagProfileCard(tag, prof)).join('')}
      </div>
    </section>
  `;
}

function renderRuleCard(direction, rule, { hideTagLine = false } = {}) {
  const title = direction === 'long' ? 'Long' : 'Short';
  if (!rule?.enabled) {
    return `
      <div class="rule-card disabled">
        <div class="rule-head">${title}</div>
        <p class="muted">${esc(rule?.reason || 'Chưa có quy tắc')}</p>
      </div>
    `;
  }

  const lines = [
    rule.h4_rsi_above != null
      ? `RSI H4 > ${rule.h4_rsi_above} (ưu tiên long)`
      : rule.h4_rsi_below != null
        ? `RSI H4 < ${rule.h4_rsi_below} (ưu tiên short)`
        : rule.h4_trend_up != null
          ? `Xu hướng H4: ${rule.h4_trend_up ? 'tăng (EMA50 > EMA200)' : 'giảm'}`
          : 'Xu hướng H4: RSI > 50 long / < 50 short',
    rule.rsi_min != null && rule.rsi_max != null
      ? `RSI từ ${rule.rsi_min} đến ${rule.rsi_max} (legacy)`
      : null,
    formatBoolRule(rule.trend_up, 'Xu hướng 1H tăng'),
    formatBoolRule(rule.close_above_ema50, 'Giá trên EMA50'),
    formatBoolRule(rule.close_above_ema200, 'Giá trên EMA200'),
    rule.max_dist_ema50_pips != null
      ? `Entry cách EMA50 tối đa ${rule.max_dist_ema50_pips} pips`
      : null,
    !hideTagLine && rule.preferred_tags?.length
      ? `Ưu tiên tag: ${rule.preferred_tags.join(', ')}`
      : null,
  ].filter(Boolean);

  const excludes = (rule.exclude || [])
    .map((ex) => {
      const op = ex.op === '<' ? 'thấp hơn' : ex.op === '>' ? 'cao hơn' : ex.op;
      return `Loại trừ khi ${ex.feature} ${op} ${ex.value} — ${ex.reason || ''}`;
    })
    .join('');

  return `
    <div class="rule-card ${direction}">
      <div class="rule-head">${title}</div>
      <ul class="rule-list">
        ${lines.map((l) => `<li>${esc(l)}</li>`).join('')}
      </ul>
      ${excludes ? `<p class="rule-exclude">${esc(excludes)}</p>` : ''}
    </div>
  `;
}

function renderRiskBlock(risk) {
  if (!risk) return '';
  const def = risk.default || {};
  const rows = [
    ['Mặc định', def],
    ['Long', risk.long],
    ['Short', risk.short],
  ].filter(([, block]) => block);

  return `
    <section class="result-section">
      <h3>Quản lý rủi ro (từ label của bạn)</h3>
      <div class="mini-table-wrap">
        <table class="mini-table">
          <thead>
            <tr>
              <th>Hướng</th>
              <th>SL × ATR</th>
              <th>RR mục tiêu</th>
              <th>TP × ATR</th>
            </tr>
          </thead>
          <tbody>
            ${rows
              .map(
                ([name, block]) => `
              <tr>
                <td>${esc(name)}</td>
                <td>${num(block.sl_atr_mult, 2)}</td>
                <td>${num(block.target_rr, 2)}</td>
                <td>${num(block.tp_atr_mult, 2)}</td>
              </tr>`,
              )
              .join('')}
          </tbody>
        </table>
      </div>
      <p class="section-note">Backtest dùng SL/TP theo ATR14 tại nến vào lệnh, không dùng giá cố định từng setup.</p>
    </section>
  `;
}

function renderTagTable(tagInfo) {
  const rows = tagInfo?.tags || [];
  if (!rows.length) return '';

  return `
    <section class="result-section">
      <h3>Tags &amp; win rate</h3>
      ${
        tagInfo.preferred_tags?.length
          ? `<p class="tag-note good">Tag tốt: ${esc(tagInfo.preferred_tags.join(', '))}</p>`
          : ''
      }
      ${
        tagInfo.avoid_tags?.length
          ? `<p class="tag-note bad">Tag nên tránh: ${esc(tagInfo.avoid_tags.join(', '))}</p>`
          : ''
      }
      <div class="mini-table-wrap">
        <table class="mini-table">
          <thead>
            <tr><th>Tag</th><th>Win</th><th>Loss</th><th>Win rate</th></tr>
          </thead>
          <tbody>
            ${rows
              .map(
                (r) => `
              <tr>
                <td>${esc(r.tag)}</td>
                <td>${r.win}</td>
                <td>${r.loss}</td>
                <td>${pct(r.win_rate)}</td>
              </tr>`,
              )
              .join('')}
          </tbody>
        </table>
      </div>
    </section>
  `;
}

function renderFeatureInsights(rows) {
  if (!rows?.length) return '';
  const labels = {
    rsi14: 'RSI14',
    dist_ema50_pips: 'Khoảng cách EMA50 (pips)',
    trend_up: 'Xu hướng tăng',
    close_above_ema50: 'Giá trên EMA50',
    close_above_ema200: 'Giá trên EMA200',
  };

  return `
    <section class="result-section">
      <h3>Win vs Loss — trung bình feature</h3>
      <div class="mini-table-wrap">
        <table class="mini-table">
          <thead>
            <tr><th>Feature</th><th>Win</th><th>Loss</th></tr>
          </thead>
          <tbody>
            ${rows
              .map(
                (r) => `
              <tr>
                <td>${esc(labels[r.feature] || r.feature)}</td>
                <td>${num(r.win_avg, 3)}</td>
                <td>${num(r.loss_avg, 3)}</td>
              </tr>`,
              )
              .join('')}
          </tbody>
        </table>
      </div>
    </section>
  `;
}

function boolLabel(value) {
  if (value == null) return '—';
  return value ? 'Bật' : 'Tắt';
}

const PARAM_LABELS = {
  entry_cooldown_bars: { label: 'Cooldown entry', hint: 'Số nến H1 tối thiểu giữa 2 lệnh' },
  ema_tolerance_atr: { label: 'Dung sai EMA50', hint: 'Khoảng cách giá–EMA50 tối đa (× ATR14)' },
  lookback_bars: { label: 'Lookback', hint: 'Số nến H1 nhìn lại để nhận pattern' },
  cross_lookback_bars: { label: 'Cross lookback', hint: 'Cửa sổ tìm golden/death cross gần nhất' },
  rsi_rise_min: { label: 'RSI bounce min', hint: 'Mức RSI phải bật tối thiểu sau retest' },
};

function renderRsiBandVisual(bands) {
  const b = bands || { low: [28, 32], mid: [48, 52], high: [68, 72] };
  const zones = [
    { label: 'Vùng 30', range: b.low, cls: 'zone-low' },
    { label: 'Vùng 50', range: b.mid, cls: 'zone-mid' },
    { label: 'Vùng 70', range: b.high, cls: 'zone-high' },
  ];

  const track = zones
    .map((z) => {
      const lo = Number(z.range?.[0] ?? 0);
      const hi = Number(z.range?.[1] ?? lo);
      return `
        <div class="rsi-zone-segment ${z.cls}" style="left:${lo}%;width:${Math.max(hi - lo, 1)}%" title="${esc(z.label)} ${lo}–${hi}">
          <span class="rsi-zone-label">${esc(z.label)}</span>
          <span class="rsi-zone-range">${lo}–${hi}</span>
        </div>`;
    })
    .join('');

  return `
    <div class="rsi-zone-visual" aria-hidden="true">
      <div class="rsi-zone-scale"><span>0</span><span>50</span><span>100</span></div>
      <div class="rsi-zone-track">${track}</div>
    </div>
  `;
}

export function renderRsiBandLegend(bands) {
  const b = bands || { low: [28, 32], mid: [48, 52], high: [68, 72] };
  const items = [
    { cls: 'legend-low', label: `30 · ${b.low?.[0]}–${b.low?.[1]}` },
    { cls: 'legend-mid', label: `50 · ${b.mid?.[0]}–${b.mid?.[1]}` },
    { cls: 'legend-high', label: `70 · ${b.high?.[0]}–${b.high?.[1]}` },
  ];
  return items
    .map((it) => `<span class="rsi-legend-item ${it.cls}">${esc(it.label)}</span>`)
    .join('');
}

function renderEntryConfig(strat, extraKeys = []) {
  const keys = [
    'lookback_bars',
    'ema_tolerance_atr',
    'cross_lookback_bars',
    'rsi_rise_min',
    'entry_cooldown_bars',
  ].filter((k) => strat[k] != null || extraKeys.includes(k));
  const rows = keys.map((key) => [key, strat[key]]);
  return `
    <div class="config-card">
      <h4>Entry &amp; lọc tín hiệu</h4>
      <ul class="config-list">
        ${rows
          .map(([key, val]) => {
            const meta = PARAM_LABELS[key] || { label: key, hint: '' };
            const display = key === 'ema_tolerance_atr' ? `× ${num(val, 2)} ATR` : String(val ?? '—');
            return `<li><span class="config-key">${esc(meta.label)}</span><span class="config-val">${esc(display)}</span><span class="config-hint">${esc(meta.hint)}</span></li>`;
          })
          .join('')}
      </ul>
    </div>
  `;
}

function renderRiskConfig(strat) {
  const risk = strat.risk || {};
  const bands = strat.bands || {};
  const mid = bands.mid || [48, 52];
  const low = bands.low || [28, 32];
  const high = bands.high || [68, 72];

  return `
    <div class="config-card">
      <h4>SL / TP (backtest)</h4>
      <ul class="config-list">
        <li>
          <span class="config-key">Take profit</span>
          <span class="config-val good">RSI H4 chạm vùng đích</span>
          <span class="config-hint">Long → ${high[0]}–${high[1]} · Short → ${low[0]}–${low[1]}</span>
        </li>
        <li>
          <span class="config-key">SL thủng vùng 50</span>
          <span class="config-val ${risk.sl_on_mid_break ? 'good' : 'muted'}">${boolLabel(risk.sl_on_mid_break)}</span>
          <span class="config-hint">Long SL nếu RSI &lt; ${mid[0]} · Short SL nếu RSI &gt; ${mid[1]}</span>
        </li>
        <li>
          <span class="config-key">SL mất EMA H1</span>
          <span class="config-val ${risk.sl_on_ema_break ? 'good' : 'muted'}">${boolLabel(risk.sl_on_ema_break)}</span>
          <span class="config-hint">Đóng khi giá phá EMA50 ngược hướng lệnh</span>
        </li>
        <li>
          <span class="config-key">SL dự phòng ATR</span>
          <span class="config-val">${num(risk.sl_atr_mult, 2)} × ATR14</span>
          <span class="config-hint">Stop tại entry ± ATR khi chưa chạm điều kiện RSI</span>
        </li>
        <li>
          <span class="config-key">Chế độ</span>
          <span class="config-val">TP theo RSI band</span>
          <span class="config-hint">Không dùng RR cố định từ setup label</span>
        </li>
      </ul>
    </div>
  `;
}

function renderSetupCards(strat, setupsDesc, setupIds = null) {
  const cfg = strat.setups || {};
  const desc = setupsDesc || strat.setups_description || [];
  const byId = Object.fromEntries(desc.map((s) => [s.id, s]));
  const ids = setupIds || Object.keys(cfg);

  const cards = ids.map((id) => {
    const setupCfg = cfg[id] || {};
    const meta = byId[id] || {};
    const enabled = setupCfg.enabled !== false;
    return `
      <article class="setup-card ${enabled ? 'enabled' : 'disabled'}">
        <header class="setup-card-head">
          <span class="setup-card-title">${esc(meta.title || setupCfg.label || id)}</span>
          <span class="pill ${enabled ? 'good' : ''}">${enabled ? 'Đang bật' : 'Tắt'}</span>
        </header>
        <div class="setup-card-dir">
          <p><span class="dir-long">LONG</span> ${esc(meta.long || '—')}</p>
          <p><span class="dir-short">SHORT</span> ${esc(meta.short || '—')}</p>
        </div>
        ${
          id === 'extreme_bounce' && setupCfg.max_mid_touches != null
            ? `<p class="section-note">Tối đa ${setupCfg.max_mid_touches} lần chạm vùng 50.</p>`
            : ''
        }
      </article>`;
  });

  return `<div class="setup-card-grid">${cards.join('')}</div>`;
}

function renderZoneRiskConfig(strat) {
  const risk = strat.risk || {};
  const bands = strat.bands || {};
  const mid = bands.mid || [48, 52];
  const low = bands.low || [28, 32];
  const high = bands.high || [68, 72];

  return `
    <div class="config-card">
      <h4>SL / TP (backtest)</h4>
      <ul class="config-list">
        <li>
          <span class="config-key">LONG — TP</span>
          <span class="config-val good">RSI chạm vùng 70 (${high[0]}–${high[1]})</span>
          <span class="config-hint">Vào khi rời vùng 30</span>
        </li>
        <li>
          <span class="config-key">SHORT — TP</span>
          <span class="config-val good">RSI chạm vùng 30 (${low[0]}–${low[1]})</span>
          <span class="config-hint">Vào khi rời vùng 70</span>
        </li>
        <li>
          <span class="config-key">SL thủng vùng 50</span>
          <span class="config-val ${risk.sl_on_mid_break ? 'good' : 'muted'}">${boolLabel(risk.sl_on_mid_break)}</span>
          <span class="config-hint">Long SL nếu RSI &lt; ${mid[0]} · Short SL nếu RSI &gt; ${mid[1]}</span>
        </li>
        <li>
          <span class="config-key">SL dự phòng ATR</span>
          <span class="config-val">${num(risk.sl_atr_mult, 2)} × ATR14</span>
          <span class="config-hint">Stop tại entry ± ATR</span>
        </li>
      </ul>
    </div>
  `;
}

function renderEmaRiskConfig(strat) {
  const risk = strat.risk || {};
  const sl = risk.sl_atr_mult ?? 1.2;
  const rr = risk.target_rr ?? 2.0;
  return `
    <div class="config-card">
      <h4>SL / TP (backtest)</h4>
      <ul class="config-list">
        <li>
          <span class="config-key">Stop loss</span>
          <span class="config-val">${num(sl, 2)} × ATR14</span>
          <span class="config-hint">Stop cố định theo ATR tại entry</span>
        </li>
        <li>
          <span class="config-key">Take profit</span>
          <span class="config-val good">${num(rr, 2)}R</span>
          <span class="config-hint">TP = entry ± SL × ${num(rr, 2)}</span>
        </li>
        <li>
          <span class="config-key">SL phá EMA50</span>
          <span class="config-val ${risk.sl_on_ema_break ? 'good' : 'muted'}">${boolLabel(risk.sl_on_ema_break)}</span>
          <span class="config-hint">Đóng sớm nếu giá phá EMA50 ngược hướng</span>
        </li>
      </ul>
    </div>
  `;
}

function renderTrainSetupStats(stats) {
  const bySetup = stats?.by_setup || {};
  const rows = Object.entries(bySetup)
    .map(([name, c]) => {
      const wr = c.total ? c.win / c.total : 0;
      return `<tr><td>${esc(name)}</td><td>${c.total}</td><td>${c.win}/${c.loss}</td><td class="${wr >= 0.55 ? 'good' : ''}">${pct(wr)}</td></tr>`;
    })
    .join('');
  if (!rows) return '';
  return `
    <section class="result-section compact-section">
      <h3>Thống kê setup trên năm train</h3>
      <div class="mini-table-wrap">
        <table class="mini-table">
          <thead><tr><th>Loại</th><th>Số</th><th>W/L</th><th>Win rate</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </section>`;
}

function renderPipelineBlock(data) {
  const pipe = data?.pipeline || {};
  const flow = data?.pipeline_flow || 'nến → tag → setup → chiến lược → backtest';
  return `
    <section class="result-section pipeline-section">
      <h3>Luồng dữ liệu</h3>
      <p class="section-note"><strong>${esc(flow)}</strong></p>
      ${statGrid([
        { label: 'Tag nến', value: String(pipe.bar_annotations ?? data?.bar_annotation_count ?? 0) },
        { label: 'Setup train', value: String(pipe.setups ?? data?.setup_count ?? 0) },
        { label: 'Setup có tag', value: String(pipe.tagged_setups ?? '—') },
        { label: 'Setup + nến', value: String(pipe.setups_with_bar_context ?? '—') },
      ])}
    </section>
  `;
}

function renderOptimizationBlock(data) {
  const opt = data.optimization;
  const base = data.baseline_metrics || opt?.baseline;
  const tuned = data.optimized_metrics || opt?.optimized_metrics;
  if (!base && !tuned) return '';

  const valPeriod = data.validation_period || opt?.validation_period;
  const pass = data.optimization_pass ?? opt?.pass;
  const params = data.best_params || opt?.best_params;
  const skipped = opt?.skipped || opt?.skip_reason;

  const row = (label, m) => {
    if (!m) return '';
    return statGrid([
      { label: 'Lệnh', value: String(m.trades ?? 0) },
      { label: 'Win rate', value: pct(m.win_rate), cls: (m.win_rate || 0) >= 0.35 ? 'good' : '' },
      { label: 'PF', value: num(m.profit_factor, 2), cls: (m.profit_factor || 0) >= 1.3 ? 'good' : 'bad' },
      { label: 'DD', value: `${num(m.max_drawdown_pips, 1)} pips`, cls: (m.max_drawdown_pips || 0) <= 250 ? 'good' : 'bad' },
      { label: 'Pass', value: m.pass ? '✓' : '✗', cls: m.pass ? 'good' : 'bad' },
    ]);
  };

  const skipNote =
    skipped === true
      ? `<p class="section-note">${esc(
          opt?.skip_reason === 'baseline_already_passes'
            ? 'Validation đã PASS — giữ nguyên tham số.'
            : 'Tối ưu không cải thiện — giữ bản baseline.',
        )}</p>`
      : '';

  const paramRows = params
    ? Object.entries(params)
        .map(([key, val]) => {
          const meta = PARAM_LABELS[key] || { label: key, hint: '' };
          const display =
            key === 'ema_tolerance_atr' ? `× ${num(val, 2)} ATR` : String(val ?? '—');
          return `<tr><td>${esc(meta.label)}</td><td><strong>${esc(display)}</strong></td><td class="muted">${esc(meta.hint)}</td></tr>`;
        })
        .join('')
    : '';

  return `
    <section class="result-section">
      <h3>Tối ưu walk-forward</h3>
      ${banner(
        pass ? 'ok' : 'warn',
        pass ? 'Validation đạt tiêu chí' : 'Validation chưa đạt',
        valPeriod
          ? `Kiểm tra trên <strong>${esc(valPeriod)}</strong> — PF ≥ 1.3 · DD ≤ 250 pips · ≥ 30 lệnh.`
          : 'Tinh chỉnh tham số entry trên năm validation.',
      )}
      ${skipNote}
      <div class="opt-compare-grid">
        <div class="opt-compare-col">
          <p class="section-note"><strong>Trước tối ưu</strong></p>
          ${row('baseline', base)}
        </div>
        <div class="opt-compare-col">
          <p class="section-note"><strong>Sau tối ưu</strong></p>
          ${row('optimized', tuned)}
        </div>
      </div>
      ${
        paramRows
          ? `
      <details class="tree-details" open>
        <summary>Tham số entry đang dùng</summary>
        <div class="mini-table-wrap">
          <table class="mini-table">
            <thead><tr><th>Tham số</th><th>Giá trị</th><th>Ý nghĩa</th></tr></thead>
            <tbody>${paramRows}</tbody>
          </table>
        </div>
      </details>`
          : ''
      }
    </section>
  `;
}

function renderRsiH4Strategy(data) {
  const strat = data.strategy || {};
  const bands = strat.bands || { low: [28, 32], mid: [48, 52], high: [68, 72] };
  const stats = data.train_stats || strat.train_stats || {};
  const tagStats = (stats.by_tag || [])
    .map(
      (r) =>
        `<tr><td><code>${esc(r.tag)}</code></td><td>${r.total}</td><td class="${r.win_rate >= 0.55 ? 'good' : ''}">${pct(r.win_rate)}</td></tr>`,
    )
    .join('');

  return `
    <section class="result-section strategy-hero">
      <h3>Vùng RSI H4 trên biểu đồ</h3>
      <p class="section-note">Đường đứt nét trên panel RSI = biên vùng chiến lược (đỏ 30 · xanh 50 · lá 70).</p>
      ${renderRsiBandVisual(bands)}
    </section>

    <section class="result-section">
      <h3>Cấu hình chiến lược</h3>
      <div class="config-grid">
        ${renderEntryConfig(strat)}
        ${renderRiskConfig(strat)}
      </div>
    </section>

    <section class="result-section">
      <h3>Hai setup entry</h3>
      <p class="section-note">Vào lệnh khi <strong>một setup đang bật</strong> khớp + EMA H1 xác nhận.</p>
      ${renderSetupCards(strat, data.setups_description, ['break_retest', 'extreme_bounce'])}
    </section>

    ${renderTrainSetupStats(stats)}

    ${
      tagStats
        ? `
    <section class="result-section compact-section">
      <h3>Tag trên setup train</h3>
      <div class="mini-table-wrap">
        <table class="mini-table">
          <thead><tr><th>Tag</th><th>Số setup</th><th>Win rate</th></tr></thead>
          <tbody>${tagStats}</tbody>
        </table>
      </div>
    </section>`
        : ''
    }
  `;
}

function renderRsiH4ZoneStrategy(data) {
  const strat = data.strategy || {};
  const bands = strat.bands || { low: [28, 32], mid: [48, 52], high: [68, 72] };
  const stats = data.train_stats || strat.train_stats || {};

  return `
    <section class="result-section strategy-hero">
      <h3>RSI H4 — rời vùng 70/30</h3>
      <p class="section-note"><strong>Rời vùng 70 → SHORT</strong> (TP RSI 30) · <strong>Rời vùng 30 → LONG</strong> (TP RSI 70).</p>
      ${renderRsiBandVisual(bands)}
    </section>

    <section class="result-section">
      <h3>Cấu hình chiến lược</h3>
      <div class="config-grid">
        ${renderEntryConfig(strat)}
        ${renderZoneRiskConfig(strat)}
      </div>
    </section>

    <section class="result-section">
      <h3>Hai setup</h3>
      ${renderSetupCards(strat, data.setups_description, ['exit_low_long', 'exit_high_short'])}
    </section>

    ${renderTrainSetupStats(stats)}
  `;
}

function renderEmaCrossStrategy(data) {
  const strat = data.strategy || {};
  const stats = data.train_stats || strat.train_stats || {};

  return `
    <section class="result-section strategy-hero">
      <h3>EMA 50/200 H1</h3>
      <p class="section-note">Pullback về EMA50 trong trend hoặc golden/death cross mới + hồi EMA50.</p>
    </section>

    <section class="result-section">
      <h3>Cấu hình chiến lược</h3>
      <div class="config-grid">
        ${renderEntryConfig(strat)}
        ${renderEmaRiskConfig(strat)}
      </div>
    </section>

    <section class="result-section">
      <h3>Bốn setup</h3>
      ${renderSetupCards(strat, data.setups_description, [
        'pullback_long',
        'pullback_short',
        'cross_long',
        'cross_short',
      ])}
    </section>

    ${renderTrainSetupStats(stats)}
  `;
}

function renderStrategyModeView(data) {
  const mode = data.rule_mode || 'global';
  const opt = data.optimization;
  const valPass = opt?.pass;
  const modeLabels = {
    rsi_h4_zone: 'RSI H4 zone exit',
    ema_cross: 'EMA 50/200 H1',
    rsi_h4: 'RSI H4 band + EMA H1',
  };
  const stratName = modeLabels[mode] || mode;
  const sid = data.strategy_id ? ` · ${data.strategy_id}` : '';

  let body = '';
  if (mode === 'rsi_h4_zone') body = renderRsiH4ZoneStrategy(data);
  else if (mode === 'ema_cross') body = renderEmaCrossStrategy(data);
  else if (mode === 'rsi_h4') body = renderRsiH4Strategy(data);

  if (!body) return '';

  return `
    ${banner(
      'ok',
      `${stratName}${sid} · Train ${data.train_year || ''}`,
      data.pipeline_flow || 'setup → chiến lược → backtest',
    )}
    ${statGrid([
      { label: 'Setup train', value: String(data.setup_count ?? 0) },
      { label: 'Win rate train', value: pct(data.win_rate_train), cls: 'good' },
      { label: 'RR label TB', value: `${num(data.avg_rr_train, 2)}R`, hint: 'Từ setup gốc' },
      {
        label: 'Validation',
        value: valPass ? 'PASS ✓' : 'Chưa pass',
        cls: valPass ? 'good' : 'bad',
        hint: data.validation_period || opt?.validation_period || '',
      },
    ])}
    ${body}
    ${renderOptimizationBlock(data)}
    ${renderPipelineBlock(data)}
  `;
}

export function renderAnalyzeView(data) {
  if (!data) return '<p class="muted">Chưa có kết quả.</p>';

  if (data.status === 'insufficient_data') {
    return `
      ${banner('warn', 'Chưa đủ dữ liệu', data.message)}
      ${statGrid([
        { label: 'Setup train', value: String(data.setup_count ?? 0) },
        { label: 'Có kết quả win/loss', value: String(data.labeled_outcomes ?? 0) },
      ])}
      <p class="section-note">Cần ít nhất 5 setup train đã biết kết quả. Hãy đánh dấu thêm setup trên năm train đã chọn.</p>
    `;
  }

  if (data.status !== 'ok') {
    return banner('error', 'Lỗi phân tích', data.message || 'Không rõ nguyên nhân');
  }

  const mode = data.rule_mode || 'global';
  const modeLabels = {
    rsi_h4_zone: 'RSI H4 zone exit',
    ema_cross: 'EMA 50/200 H1',
    rsi_h4: 'RSI H4 band + EMA H1',
    similarity: 'Similarity (legacy)',
    tag_driven: 'Tag profile (legacy)',
    global: 'Global (legacy)',
  };

  if (mode === 'rsi_h4_zone' || mode === 'ema_cross' || mode === 'rsi_h4') {
    return renderStrategyModeView(data);
  }

  const rules = data.rules || {};
  return `
    ${banner('ok', 'Phân tích hoàn tất', data.train_year ? `Chiến lược học từ setup train ${data.train_year}.` : 'Chiến lược học từ các setup train (mỗi setup = nến entry + tag + SL/TP).')}
    ${renderPipelineBlock(data)}
    ${statGrid([
      { label: 'Setup train', value: String(data.setup_count ?? 0) },
      { label: 'Win rate train', value: pct(data.win_rate_train), cls: 'good' },
      { label: 'RR trung bình', value: `${num(data.avg_rr_train, 2)}R` },
      { label: 'Chế độ', value: modeLabels[mode] || mode, cls: mode === 'similarity' ? 'good' : '' },
      { label: 'Tag nến', value: String(data.bar_annotation_count ?? 0), cls: 'good' },
    ])}

    ${mode === 'similarity'
      ? banner(
          'ok',
          'Backtest theo pipeline',
          'Mỗi lệnh: nến đạt score → nhận diện tag → khớp setup train cùng tag → vào lệnh theo hướng/SL/TP setup đó.',
        )
      : banner(
          'warn',
          'Chế độ fallback',
          'Chưa đủ tag trên setup — backtest dùng rule global. Gắn tag đủ trên setup train để bật pipeline đầy đủ.',
        )}

    ${renderTagSignatures(data)}
    ${renderTagProfiles(data)}

    <section class="result-section">
      <h3>Quy tắc global (tham khảo)</h3>
      <p class="section-note">Học từ toàn bộ setup train — dùng khi chưa đủ tag hoặc để so sánh.</p>
      <div class="rule-grid">
        ${renderRuleCard('long', rules.long)}
        ${renderRuleCard('short', rules.short)}
      </div>
    </section>

    ${renderRiskBlock(data.risk)}
    ${renderTagTable(data.tag_insights)}
    ${renderFeatureInsights(data.feature_insights)}

    ${renderOptimizationBlock(data)}

    ${
      data.tree_summary
        ? `
      <details class="tree-details">
        <summary>Decision tree (tham khảo)</summary>
        <pre class="tree-pre">${esc(data.tree_summary)}</pre>
        <p class="section-note">Backtest không dùng cây này — chỉ dùng quy tắc ở trên.</p>
      </details>`
        : ''
    }
  `;
}

function renderTradeRows(trades) {
  if (!trades?.length) {
    return '<tr><td colspan="8" class="muted">Không có lệnh nào.</td></tr>';
  }
  return trades
    .slice()
    .reverse()
    .map((t) => {
      const win = t.result === 'win';
      const time = (t.entry_time || '').slice(0, 16).replace('T', ' ');
      const tagParts = [];
      if (t.tag) tagParts.push(`<span class="pill">${esc(t.tag)}</span>`);
      if (t.setup_type) tagParts.push(`<span class="pill" title="Loại setup">${esc(t.setup_type)}</span>`);
      if (t.importance_score != null) tagParts.push(`<span class="pill" title="Importance score">S${t.importance_score}</span>`);
      if (t.similarity != null) tagParts.push(`<span class="pill" title="Setup similarity">${Math.round(t.similarity * 100)}%</span>`);
      if ((t.sequence_tags || []).length) {
        tagParts.push(`<span class="pill" title="Sequence tags">${esc(t.sequence_tags.join('+'))}</span>`);
      }
      const tagCell = tagParts.length ? tagParts.join(' ') : '—';
      return `
        <tr class="${win ? 'row-win' : 'row-loss'}">
          <td>${esc(time)}</td>
          <td>${esc((t.direction || '').toUpperCase())}</td>
          <td>${tagCell}</td>
          <td>${num(t.entry, 5)}</td>
          <td>${num(t.exit, 5)}</td>
          <td class="${win ? 'good' : 'bad'}">${esc((t.result || '').toUpperCase())}</td>
          <td class="${Number(t.pnl_pips) >= 0 ? 'good' : 'bad'}">${num(t.pnl_pips, 1)}</td>
          <td>${num(t.rr, 2)}R</td>
        </tr>
      `;
    })
    .join('');
}

export function renderBacktestView(data, { title, subtitle, includeTrades = false } = {}) {
  if (!data) return '<p class="muted">Chưa có kết quả.</p>';

  if (data.status === 'no_strategy') {
    return `
      ${banner('warn', 'Chưa có chiến lược', data.message || 'Chạy Analyze trước.')}
      <p class="section-note">Vào tab <strong>Analyze</strong> và bấm 「Phân tích + tối ưu」 sau khi đã label đủ setup train.</p>
    `;
  }

  if (data.status !== 'ok') {
    return banner('error', 'Lỗi backtest', data.message || 'Không rõ nguyên nhân');
  }

  const m = data.metrics || {};
  const passed = m.pass === true;
  const total = data.trade_count_total ?? m.trades ?? 0;
  const isRsi = data.rule_mode === 'rsi_h4';
  const risk = data.risk || {};

  const rsiConfigBlock =
    isRsi && risk
      ? `
    <section class="result-section compact-section">
      <h3>Quy tắc SL / TP đang chạy</h3>
      <ul class="criteria-list criteria-list-inline">
        <li>TP: RSI H4 chạm vùng 70 (long) / 30 (short)</li>
        <li>SL vùng 50: ${risk.sl_on_mid_break ? 'Bật' : 'Tắt'}</li>
        <li>SL EMA H1: ${risk.sl_on_ema_break ? 'Bật' : 'Tắt'}</li>
        <li>SL ATR: × ${num(risk.sl_atr_mult, 2)}</li>
      </ul>
    </section>`
      : '';

  const metricsBlock = `
    ${banner(
      passed ? 'ok' : 'warn',
      passed ? `${title} — ĐẠT` : `${title} — CHƯA ĐẠT`,
      isRsi
        ? `${subtitle} · Entry RSI H4 + EMA H1 · TP/SL theo vùng RSI.`
        : `${subtitle} · Pipeline: nến → tag → setup train → vào lệnh.`,
    )}

    ${statGrid(
      [
        { label: 'Tổng lệnh', value: String(total) },
        { label: 'Win rate', value: pct(m.win_rate), cls: Number(m.win_rate) >= 0.5 ? 'good' : '' },
        { label: 'Profit factor', value: num(m.profit_factor, 2), cls: Number(m.profit_factor) >= 1.3 ? 'good' : '' },
        { label: 'Expectancy', value: `${num(m.expectancy_pips, 1)} pips` },
        { label: 'Max drawdown', value: `${num(m.max_drawdown_pips, 1)} pips`, cls: Number(m.max_drawdown_pips) <= 250 ? '' : 'bad' },
        { label: 'RR trung bình', value: `${num(m.avg_rr, 2)}R` },
      ],
      'stat-grid-6',
    )}

    <section class="result-section">
      <h3>Tiêu chí đánh giá</h3>
      <ul class="criteria-list criteria-list-inline">
        <li class="${total >= 30 ? 'met' : ''}">≥ 30 lệnh ${total >= 30 ? '✓' : `(hiện ${total})`}</li>
        <li class="${Number(m.profit_factor) >= 1.3 ? 'met' : ''}">Profit factor ≥ 1.3 ${Number(m.profit_factor) >= 1.3 ? '✓' : ''}</li>
        <li class="${Number(m.max_drawdown_pips) <= 250 ? 'met' : ''}">Max DD ≤ 250 pips ${Number(m.max_drawdown_pips) <= 250 ? '✓' : ''}</li>
      </ul>
    </section>
    ${rsiConfigBlock}
  `;

  if (!includeTrades) {
    return metricsBlock;
  }

  const previewTrades = (data.trades || []).slice(-50);
  const shown = previewTrades.length;

  return `
    ${metricsBlock}
    <section class="result-section">
      <h3>Lệnh gần đây ${shown < total ? `(hiển thị ${shown}/${total})` : ''}</h3>
      <div class="mini-table-wrap trades-wrap">
        <table class="mini-table">
          <thead>
            <tr>
              <th>Thời gian</th>
              <th>Hướng</th>
              <th>Tag / Score</th>
              <th>Entry</th>
              <th>Exit</th>
              <th>KQ</th>
              <th>PnL</th>
              <th>RR</th>
            </tr>
          </thead>
          <tbody>${renderTradeRows(previewTrades)}</tbody>
        </table>
      </div>
    </section>
  `;
}

export function renderBacktestTradesPanel(trades, { focusedKey = null, onRowClick = null } = {}) {
  const sorted = [...(trades || [])].sort((a, b) => (a.entry_time || '').localeCompare(b.entry_time || ''));
  const total = sorted.length;

  if (!total) {
    return `
      <div class="trades-table-toolbar">
        <h3>Danh sách lệnh</h3>
      </div>
      <p class="muted section-note">Chưa có lệnh. Chạy backtest hoặc mở kết quả đã lưu.</p>
    `;
  }

  const rows = sorted
    .map((t) => {
      const win = t.result === 'win';
      const time = (t.entry_time || '').slice(0, 16).replace('T', ' ');
      const key = `${t.entry_time}|${t.direction}|${t.entry}`;
      const selected = focusedKey && focusedKey === key;
      const tagParts = [];
      if (t.tag) tagParts.push(`<span class="pill">${esc(t.tag)}</span>`);
      if (t.setup_type) tagParts.push(`<span class="pill" title="Loại setup">${esc(t.setup_type)}</span>`);
      if (t.importance_score != null) tagParts.push(`<span class="pill">S${t.importance_score}</span>`);
      if (t.similarity != null) tagParts.push(`<span class="pill">${Math.round(t.similarity * 100)}%</span>`);
      return `
        <tr class="${win ? 'row-win' : 'row-loss'}${selected ? ' selected' : ''}" data-trade-key="${esc(key)}">
          <td>${esc(time)}</td>
          <td>${esc((t.direction || '').toUpperCase())}</td>
          <td>${tagParts.join(' ') || '—'}</td>
          <td>${num(t.entry, 5)}</td>
          <td>${num(t.exit, 5)}</td>
          <td class="${win ? 'good' : 'bad'}">${esc((t.result || '').toUpperCase())}</td>
          <td class="${Number(t.pnl_pips) >= 0 ? 'good' : 'bad'}">${num(t.pnl_pips, 1)}</td>
          <td>${num(t.rr, 2)}R</td>
        </tr>
      `;
    })
    .join('');

  return `
    <div class="trades-table-toolbar">
      <h3>Danh sách lệnh · ${total}</h3>
      <span class="muted" style="font-size:11px">Click hàng để xem trên chart</span>
    </div>
    <div class="trades-table-wrap">
      <table class="mini-table trades-table">
        <thead>
          <tr>
            <th>Thời gian</th>
            <th>Hướng</th>
            <th>Tag / Score</th>
            <th>Entry</th>
            <th>Exit</th>
            <th>KQ</th>
            <th>PnL</th>
            <th>RR</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

export function renderBacktestSidebarSummary(data) {
  if (!data || data.status !== 'ok') {
    return 'Chưa có kết quả — bấm Chạy backtest.';
  }
  const m = data.metrics || {};
  const pass = m.pass === true;
  const label = data.period_label || data.period || 'BT';
  return `${pass ? '✓ ĐẠT' : '✗ Chưa đạt'} · ${label} · ${m.trades ?? 0} lệnh · WR ${pct(m.win_rate)} · PF ${num(m.profit_factor, 2)} · DD ${num(m.max_drawdown_pips, 1)} pips`;
}

export function renderBacktestCompare(runs) {
  if (!runs?.length) {
    return '<p class="muted section-note">Chọn ít nhất 1 kết quả đã lưu để so sánh.</p>';
  }
  return `
    <section class="result-section bt-compare-section">
      <h3>So sánh ${runs.length} backtest</h3>
      <div class="mini-table-wrap">
        <table class="mini-table bt-compare-table">
          <thead>
            <tr>
              <th>Tên</th>
              <th>Giai đoạn</th>
              <th>Lệnh</th>
              <th>Win%</th>
              <th>PF</th>
              <th>Expect.</th>
              <th>Max DD</th>
              <th>RR</th>
              <th>Đạt</th>
            </tr>
          </thead>
          <tbody>
            ${runs
              .map((r) => {
                const m = r.metrics || {};
                const pass = m.pass === true;
                const periodShort = r.period_label || r.period || '—';
                return `<tr class="${pass ? 'row-win' : 'row-loss'}">
                  <td><strong>${esc(r.name)}</strong></td>
                  <td>${esc(periodShort)}</td>
                  <td>${esc(r.trade_count ?? m.trades ?? '—')}</td>
                  <td>${pct(m.win_rate)}</td>
                  <td class="${Number(m.profit_factor) >= 1.3 ? 'good' : ''}">${num(m.profit_factor, 2)}</td>
                  <td>${num(m.expectancy_pips, 1)}</td>
                  <td class="${Number(m.max_drawdown_pips) <= 250 ? '' : 'bad'}">${num(m.max_drawdown_pips, 1)}</td>
                  <td>${num(m.avg_rr, 2)}R</td>
                  <td>${pass ? '✓' : '—'}</td>
                </tr>`;
              })
              .join('')}
          </tbody>
        </table>
      </div>
    </section>
  `;
}

export function renderStrategySettingsForm(strategy) {
  if (!strategy) {
    return '<p class="muted section-note">Chưa có file chiến lược — chạy Analyze hoặc tải từ năm train đã phân tích.</p>';
  }

  const mode = strategy.rule_mode || strategy.strategy_id || '';
  const setups = strategy.setups || {};
  const risk = strategy.risk || {};
  const bands = strategy.bands || { low: [28, 32], mid: [48, 52], high: [68, 72] };

  const setupToggles = Object.entries(setups)
    .map(([id, cfg]) => {
      const checked = cfg?.enabled !== false ? 'checked' : '';
      return `
        <label class="strategy-setup-toggle">
          <input type="checkbox" data-setup-id="${esc(id)}" ${checked}>
          <span>${esc(cfg?.label || id)}</span>
        </label>`;
    })
    .join('');

  const numField = (key, val, step = '1', label = key) => `
    <label class="strat-field">
      <span>${esc(label)}</span>
      <input type="number" data-strat-key="${esc(key)}" value="${val ?? ''}" step="${step}">
    </label>`;

  const boolField = (key, val, label) => `
    <label class="strat-check">
      <input type="checkbox" data-strat-bool="${esc(key)}" ${val ? 'checked' : ''}>
      <span>${esc(label)}</span>
    </label>`;

  let body = `
    <h3 class="strat-settings-title">Cấu hình chiến lược</h3>
    <p class="section-note">Chỉnh tham số tại đây — <strong>không dùng tag</strong> để cấu hình. Setup backtest theo settings bên dưới.</p>
    <div class="strat-setup-toggles">${setupToggles || '<span class="muted">—</span>'}</div>
  `;

  if (mode === 'rsi_h4_zone' || mode === 'rsi_h4') {
    body += `
      <div class="strat-field-grid">
        <label class="strat-field"><span>RSI thấp (min)</span><input type="number" data-band="low0" value="${bands.low?.[0] ?? 28}" step="1"></label>
        <label class="strat-field"><span>RSI thấp (max)</span><input type="number" data-band="low1" value="${bands.low?.[1] ?? 32}" step="1"></label>
        <label class="strat-field"><span>RSI giữa (min)</span><input type="number" data-band="mid0" value="${bands.mid?.[0] ?? 48}" step="1"></label>
        <label class="strat-field"><span>RSI giữa (max)</span><input type="number" data-band="mid1" value="${bands.mid?.[1] ?? 52}" step="1"></label>
        <label class="strat-field"><span>RSI cao (min)</span><input type="number" data-band="high0" value="${bands.high?.[0] ?? 68}" step="1"></label>
        <label class="strat-field"><span>RSI cao (max)</span><input type="number" data-band="high1" value="${bands.high?.[1] ?? 72}" step="1"></label>
        ${numField('lookback_bars', strategy.lookback_bars, '1', 'Lookback')}
        ${numField('entry_cooldown_bars', strategy.entry_cooldown_bars, '1', 'Cooldown entry')}
        ${numField('sl_atr_mult', risk.sl_atr_mult, '0.1', 'SL × ATR')}
      </div>
      <div class="strat-bool-grid">
        ${boolField('sl_on_mid_break', risk.sl_on_mid_break, 'SL khi RSI thủng vùng 50')}
        ${boolField('sl_on_ema_break', risk.sl_on_ema_break, 'SL khi mất EMA H1')}
      </div>`;
  } else if (mode === 'ema_cross') {
    body += `
      <div class="strat-field-grid">
        ${numField('lookback_bars', strategy.lookback_bars, '1', 'Lookback')}
        ${numField('cross_lookback_bars', strategy.cross_lookback_bars, '1', 'Cross lookback')}
        ${numField('entry_cooldown_bars', strategy.entry_cooldown_bars, '1', 'Cooldown entry')}
        ${numField('ema_tolerance_atr', strategy.ema_tolerance_atr, '0.05', 'Dung sai EMA50 (×ATR)')}
        ${numField('min_trend_sep_atr', strategy.min_trend_sep_atr, '0.01', 'Tách trend min (×ATR)')}
        ${numField('sl_atr_mult', risk.sl_atr_mult, '0.1', 'SL × ATR')}
        ${numField('target_rr', risk.target_rr, '0.1', 'Target RR')}
      </div>
      <div class="strat-bool-grid">
        ${boolField('sl_on_ema_break', risk.sl_on_ema_break, 'SL khi phá EMA50')}
      </div>`;
  } else {
    body += `<p class="muted">Chưa hỗ trợ form cho rule_mode: ${esc(mode)}</p>`;
  }

  return `<section class="strategy-settings-form">${body}</section>`;
}

export function collectStrategySettingsFromForm(root, strategy) {
  if (!root || !strategy) return null;
  const mode = strategy.rule_mode || strategy.strategy_id || '';
  const patch = {
    train_period: strategy.train_period,
    strategy_id: strategy.strategy_id,
    setups: {},
    risk: { ...(strategy.risk || {}) },
  };

  root.querySelectorAll('[data-setup-id]').forEach((el) => {
    const id = el.dataset.setupId;
    patch.setups[id] = { enabled: el.checked };
  });

  root.querySelectorAll('[data-strat-key]').forEach((el) => {
    patch[el.dataset.stratKey] = Number(el.value);
  });

  root.querySelectorAll('[data-strat-bool]').forEach((el) => {
    const key = el.dataset.stratBool;
    if (key === 'sl_on_mid_break' || key === 'sl_on_ema_break') {
      patch.risk[key] = el.checked;
    }
  });

  const slAtr = root.querySelector('[data-strat-key="sl_atr_mult"]');
  if (slAtr) patch.risk.sl_atr_mult = Number(slAtr.value);
  const targetRr = root.querySelector('[data-strat-key="target_rr"]');
  if (targetRr) patch.risk.target_rr = Number(targetRr.value);

  if (mode === 'rsi_h4_zone' || mode === 'rsi_h4') {
    const g = (sel) => Number(root.querySelector(sel)?.value);
    patch.bands = {
      low: [g('[data-band="low0"]'), g('[data-band="low1"]')],
      mid: [g('[data-band="mid0"]'), g('[data-band="mid1"]')],
      high: [g('[data-band="high0"]'), g('[data-band="high1"]')],
    };
  }

  return patch;
}

export function renderLoading(message = 'Đang xử lý...') {
  return `<div class="result-loading"><span class="spinner"></span> ${esc(message)}</div>`;
}

export function renderError(message) {
  return banner('error', 'Lỗi', message);
}
