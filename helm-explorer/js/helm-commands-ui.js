/**
 * Helm Commands UI renderer
 */
const HelmCommandsUI = (() => {
  const MODE_LABELS = {
    platform: { label: 'Platform Chart', color: '#00a0e3', icon: '🏗' },
    'umbrella-subchart': { label: 'Umbrella Subchart', color: '#7b68ee', icon: '📦' },
    'nested-subchart': { label: 'Nested Subchart', color: '#a78bfa', icon: '📎' },
    library: { label: 'Library Chart', color: '#ff8c42', icon: '📚' },
    standalone: { label: 'Standalone', color: '#2dd4a0', icon: '⎈' },
  };

  const CAT_LABELS = {
    deploy: 'Deploy',
    debug: 'Debug / Test',
    utility: 'Tiện ích',
    ops: 'Vận hành',
    config: 'Cấu hình',
  };

  function escapeHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function renderModeBadge(hc) {
    const mode = MODE_LABELS[hc.deployMode] || MODE_LABELS.standalone;
    return `<span class="helm-mode-badge" style="--mode-color:${mode.color}">${mode.icon} ${mode.label}</span>`;
  }

  function renderCommandBlock(cmd, index) {
    const cat = CAT_LABELS[cmd.category] || cmd.category || 'deploy';
    return `
      <div class="helm-cmd-block" data-cmd-idx="${index}">
        <div class="helm-cmd-header">
          <div>
            <span class="helm-cmd-title">${escapeHtml(cmd.title)}</span>
            <span class="helm-cmd-cat cat-${cmd.category || 'deploy'}">${cat}</span>
          </div>
          <button class="btn btn-ghost btn-copy-cmd" data-cmd="${index}" title="Copy lệnh">📋 Copy</button>
        </div>
        ${cmd.desc ? `<p class="helm-cmd-desc">${cmd.desc}</p>` : ''}
        <pre class="helm-cmd-pre"><code>${escapeHtml(cmd.cmd)}</code></pre>
      </div>
    `;
  }

  function renderPanel(node, platformSequence) {
    const hc = node.helmCommands;
    if (!hc) {
      return `<div class="callout">Không có thông tin Helm command cho mục này.</div>`;
    }

    const notesHtml = (hc.notes || []).map(n => `<li>${n}</li>`).join('');
    const cmdsHtml = (hc.commands || []).map((c, i) => renderCommandBlock(c, i)).join('');

    const readmeHtml = (hc.readmeCommands || []).length ? `
      <div class="panel" style="margin-top:1rem">
        <div class="panel-header">📖 Lệnh từ README (trong repo)</div>
        <div class="panel-body">
          ${hc.readmeCommands.map((c, i) => `
            <div class="helm-cmd-block readme-cmd" data-readme-idx="${i}">
              <div class="helm-cmd-header">
                <span class="helm-cmd-cat cat-utility">README</span>
                <button class="btn btn-ghost btn-copy-readme" data-idx="${i}">📋 Copy</button>
              </div>
              <pre class="helm-cmd-pre"><code>${escapeHtml(c)}</code></pre>
            </div>
          `).join('')}
        </div>
      </div>
    ` : '';

    const contextHtml = hc.umbrellaChart ? `
      <div class="helm-context-grid">
        <div class="helm-ctx-item"><span>Umbrella chart</span><strong>${escapeHtml(hc.umbrellaChart)}</strong></div>
        <div class="helm-ctx-item"><span>Đường dẫn parent</span><code>./${escapeHtml(hc.umbrellaPath || '')}</code></div>
        ${hc.tagKey ? `<div class="helm-ctx-item"><span>Tag key</span><code>tags.${escapeHtml(hc.tagKey)}</code></div>` : ''}
        ${hc.platformOrder ? `<div class="helm-ctx-item"><span>Thứ tự platform</span><strong>#${hc.platformOrder}</strong></div>` : ''}
      </div>
    ` : (hc.platformOrder ? `
      <div class="helm-context-grid">
        <div class="helm-ctx-item"><span>Thứ tự cài platform</span><strong>Bước #${hc.platformOrder} / 5</strong></div>
      </div>
    ` : '');

    const platformBlock = hc.deployMode === 'platform' && platformSequence ? `
      <div class="callout" style="margin-bottom:1rem">
        <strong>Chuỗi cài đặt Altiplano Platform:</strong>
        <ol class="platform-sequence">
          ${platformSequence.map(p => `
            <li class="${p.chart === node.chart?.name ? 'current' : ''}">
              <span class="ps-order">${p.order}</span>
              <span class="ps-name">${p.chart}</span>
              ${p.chart === node.chart?.name ? '<span class="tag">← chart này</span>' : ''}
            </li>
          `).join('')}
        </ol>
      </div>
    ` : '';

    return `
      <div class="helm-commands-panel">
        <div class="helm-cmd-intro">
          ${renderModeBadge(hc)}
          <p class="helm-cmd-summary">
            ${getSummary(hc, node)}
          </p>
        </div>
        ${platformBlock}
        ${contextHtml}
        ${notesHtml ? `<ul class="helm-notes">${notesHtml}</ul>` : ''}
        <div class="helm-cmd-list">${cmdsHtml}</div>
        ${readmeHtml}
      </div>
    `;
  }

  function getSummary(hc, node) {
    const name = node.chart?.name || node.name;
    switch (hc.deployMode) {
      case 'platform':
        return `Chart platform <strong>${name}</strong> — deploy độc lập bằng Helm release riêng.`;
      case 'umbrella-subchart':
        return `Microservice <strong>${name}</strong> — deploy qua umbrella <strong>${hc.umbrellaChart}</strong>, enable bằng tags/values.`;
      case 'nested-subchart':
        return `Subchart lồng nhau <strong>${name}</strong> — render khi parent chart được deploy.`;
      case 'library':
        return `Library <strong>${name}</strong> — không có lệnh install riêng, dùng qua dependency/subchart.`;
      default:
        return `Chart <strong>${name}</strong> — có thể deploy trực tiếp.`;
    }
  }

  function renderPlatformGuide(platformSequence) {
    return `
      <div class="panel">
        <div class="panel-header">⎈ Chuỗi lệnh Helm cài đặt Altiplano Platform</div>
        <div class="panel-body">
          <p style="font-size:.82rem;color:var(--text-muted);margin-bottom:1rem">
            Thứ tự deploy chuẩn cho Nokia Altiplano. Thay <code>&lt;namespace&gt;</code> và <code>custom-values.yaml</code> bằng giá trị thực tế.
          </p>
          ${platformSequence.map(p => `
            <div class="helm-cmd-block platform-step">
              <div class="helm-cmd-header">
                <span class="helm-cmd-title">Bước ${p.order}: ${p.chart}</span>
                <button class="btn btn-ghost btn-copy-platform" data-order="${p.order}">📋 Copy</button>
              </div>
              <p class="helm-cmd-desc">${p.desc}</p>
              <pre class="helm-cmd-pre"><code>${escapeHtml(p.command)}</code></pre>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  function wireCopyHandlers(container, node) {
    const hc = node.helmCommands;
    if (!hc) return;

    container.querySelectorAll('.btn-copy-cmd').forEach(btn => {
      btn.addEventListener('click', async () => {
        const idx = parseInt(btn.dataset.cmd, 10);
        const cmd = hc.commands[idx]?.cmd;
        if (cmd) {
          await navigator.clipboard.writeText(cmd);
          window.dispatchEvent(new CustomEvent('toast', { detail: 'Đã copy lệnh Helm!' }));
        }
      });
    });

    container.querySelectorAll('.btn-copy-readme').forEach(btn => {
      btn.addEventListener('click', async () => {
        const idx = parseInt(btn.dataset.idx, 10);
        const cmd = hc.readmeCommands[idx];
        if (cmd) {
          await navigator.clipboard.writeText(cmd);
          window.dispatchEvent(new CustomEvent('toast', { detail: 'Đã copy lệnh từ README!' }));
        }
      });
    });
  }

  return { renderPanel, renderPlatformGuide, wireCopyHandlers, renderModeBadge };
})();
