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

function statGrid(items) {
  return `
    <div class="stat-grid">
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
            <tr><th>Tag</th><th>Mẫu</th><th>RSI trung bình</th><th>Dist EMA50</th></tr>
          </thead>
          <tbody>
            ${entries
              .map(([tag, sig]) => {
                const rsi = sig.features?.rsi14?.mean;
                const dist = sig.features?.dist_ema50_pips?.mean;
                return `<tr>
                  <td>${esc(tag)}</td>
                  <td>${sig.count ?? 0}</td>
                  <td>${num(rsi, 1)}</td>
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
    `RSI từ ${rule.rsi_min} đến ${rule.rsi_max}`,
    formatBoolRule(rule.trend_up, 'Xu hướng tăng (EMA50 > EMA200)'),
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

export function renderAnalyzeView(data) {
  if (!data) return '<p class="muted">Chưa có kết quả.</p>';

  if (data.status === 'insufficient_data') {
    return `
      ${banner('warn', 'Chưa đủ dữ liệu', data.message)}
      ${statGrid([
        { label: 'Setup train', value: String(data.setup_count ?? 0) },
        { label: 'Có kết quả win/loss', value: String(data.labeled_outcomes ?? 0) },
      ])}
      <p class="section-note">Cần ít nhất 5 setup train đã biết kết quả. Hãy đánh dấu thêm setup trên năm 2022.</p>
    `;
  }

  if (data.status !== 'ok') {
    return banner('error', 'Lỗi phân tích', data.message || 'Không rõ nguyên nhân');
  }

  const rules = data.rules || {};
  const mode = data.rule_mode || 'global';
  const modeLabels = {
    similarity: 'Similarity (tag + setup gần nhất)',
    tag_driven: 'Tag profile',
    global: 'Global',
  };
  return `
    ${banner('ok', 'Phân tích hoàn tất', 'Chiến lược học từ các setup train (mỗi setup = nến entry + tag + SL/TP).')}
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

export function renderBacktestView(data, { title, subtitle }) {
  if (!data) return '<p class="muted">Chưa có kết quả.</p>';

  if (data.status === 'no_strategy') {
    return `
      ${banner('warn', 'Chưa có chiến lược', data.message || 'Chạy Analyze trước.')}
      <p class="section-note">Vào tab <strong>Analyze</strong> và bấm 「Chạy phân tích」 sau khi đã label đủ setup train.</p>
    `;
  }

  if (data.status !== 'ok') {
    return banner('error', 'Lỗi backtest', data.message || 'Không rõ nguyên nhân');
  }

  const m = data.metrics || {};
  const passed = m.pass === true;
  const total = data.trade_count_total ?? m.trades ?? 0;
  const previewTrades = (data.trades || []).slice(-50);
  const shown = previewTrades.length;

  return `
    ${banner(
      passed ? 'ok' : 'warn',
      passed ? `${title} — ĐẠT` : `${title} — CHƯA ĐẠT`,
      `${subtitle} · Pipeline: nến → tag → setup train → vào lệnh.`,
    )}

    ${statGrid([
      { label: 'Tổng lệnh', value: String(total) },
      { label: 'Win rate', value: pct(m.win_rate), cls: Number(m.win_rate) >= 0.5 ? 'good' : '' },
      { label: 'Profit factor', value: num(m.profit_factor, 2), cls: Number(m.profit_factor) >= 1.3 ? 'good' : '' },
      { label: 'Expectancy', value: `${num(m.expectancy_pips, 1)} pips` },
      { label: 'Max drawdown', value: `${num(m.max_drawdown_pips, 1)} pips`, cls: Number(m.max_drawdown_pips) <= 250 ? '' : 'bad' },
      { label: 'RR trung bình', value: `${num(m.avg_rr, 2)}R` },
    ])}

    <section class="result-section">
      <h3>Tiêu chí đánh giá</h3>
      <ul class="criteria-list">
        <li class="${total >= 30 ? 'met' : ''}">≥ 30 lệnh ${total >= 30 ? '✓' : `(hiện ${total})`}</li>
        <li class="${Number(m.profit_factor) >= 1.3 ? 'met' : ''}">Profit factor ≥ 1.3 ${Number(m.profit_factor) >= 1.3 ? '✓' : ''}</li>
        <li class="${Number(m.max_drawdown_pips) <= 250 ? 'met' : ''}">Max DD ≤ 250 pips ${Number(m.max_drawdown_pips) <= 250 ? '✓' : ''}</li>
      </ul>
    </section>

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
                const periodShort = r.period === 'validation' ? '2023' : r.period === 'test' ? '2024–26' : r.period;
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

export function renderLoading(message = 'Đang xử lý...') {
  return `<div class="result-loading"><span class="spinner"></span> ${esc(message)}</div>`;
}

export function renderError(message) {
  return banner('error', 'Lỗi', message);
}
