/**
 * Altiplano Helm Explorer — Main Application
 */
(() => {
  'use strict';

  let manifest = null;
  let nodeIndex = new Map();
  let expandedNodes = new Set(['root']);
  let activeNodeId = null;
  let searchIndex = [];
  let kindFilter = '';

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const CATEGORY_COLORS = {
    workload: '#00a0e3', network: '#a78bfa', config: '#fbbf24',
    storage: '#f4a261', rbac: '#f87171', crd: '#ff6b35',
    gateway: '#2dd4a0', autoscale: '#38bdf8', reliability: '#c084fc',
    other: '#8b9cb8',
  };

  const TYPE_ICONS = {
    chart: '⎈', folder: '📁', root: '🏠',
  };

  async function init() {
    try {
      const res = await fetch('manifest.json');
      manifest = await res.json();
      buildNodeIndex(manifest.tree);
      buildSearchIndex();
      await FileLoader.getBase();
      renderHeaderStats();
      renderKindFilter();
      renderTree();
      renderWelcome();
      setupEvents();
      GraphView.init($('#graphSvg'));
      hideLoading();
    } catch (err) {
      $('#loading p').textContent = 'Lỗi tải manifest.json — chạy: python3 generate-manifest.py';
      console.error(err);
    }
  }

  function buildNodeIndex(node) {
    nodeIndex.set(node.id, node);
    (node.children || []).forEach(buildNodeIndex);
  }

  function buildSearchIndex() {
    searchIndex = [];
    nodeIndex.forEach((node) => {
      const entry = {
        id: node.id,
        name: node.name,
        path: node.path,
        type: node.type,
        chartName: node.chart?.name || '',
        kinds: Object.keys(node.resourceSummary || {}),
        highlights: (node.valuesHighlights || []).map(h => h.key).join(' '),
        deployMode: node.helmCommands?.deployMode || '',
      };
      searchIndex.push(entry);

      if (node.type === 'chart') {
        (node.resources || []).forEach(r => {
          searchIndex.push({
            id: node.id,
            name: r.kind,
            path: `${node.path} → ${r.file}`,
            type: 'resource',
            chartName: node.chart?.name,
            kinds: [r.kind],
            resource: r,
          });
        });
      }
    });
  }

  function hideLoading() {
    const el = $('#loading');
    el.classList.add('hidden');
    setTimeout(() => el.remove(), 400);
  }

  function renderHeaderStats() {
    const s = manifest.stats;
    $('#headerStats').innerHTML = `
      <div class="stat-pill"><span class="val">${s.totalCharts}</span><span class="lbl">Charts</span></div>
      <div class="stat-pill"><span class="val">${s.totalTemplates}</span><span class="lbl">Templates</span></div>
      <div class="stat-pill"><span class="val">${Object.keys(s.resourceKinds).length}</span><span class="lbl">K8s Kinds</span></div>
      <div class="stat-pill"><span class="val">${Object.keys(manifest.sharedCharts).length}</span><span class="lbl">Shared</span></div>
    `;
  }

  function renderKindFilter() {
    const select = $('#filterKind');
    const kinds = Object.entries(manifest.stats.resourceKinds).sort((a, b) => b[1] - a[1]);
    kinds.forEach(([kind, count]) => {
      const opt = document.createElement('option');
      opt.value = kind;
      opt.textContent = `${kind} (${count})`;
      select.appendChild(opt);
    });
  }

  function nodeMatchesFilter(node) {
    if (!kindFilter) return true;
    if (node.type !== 'chart') {
      return (node.children || []).some(nodeMatchesFilter);
    }
    return (node.resourceSummary || {})[kindFilter] > 0;
  }

  function isSharedChart(node) {
    if (node.type !== 'chart' || !node.chart) return false;
    return (manifest.sharedCharts[node.chart.name] || []).length > 1;
  }

  function renderTree() {
    const nav = $('#treeNav');
    nav.innerHTML = '';
    manifest.tree.children.forEach(child => {
      if (nodeMatchesFilter(child)) {
        nav.appendChild(renderTreeNode(child, 0));
      }
    });
  }

  function renderTreeNode(node, depth) {
    const wrapper = document.createElement('div');
    wrapper.className = 'tree-node';
    wrapper.dataset.id = node.id;

    const hasChildren = node.children && node.children.length > 0;
    const isExpanded = expandedNodes.has(node.id);
    const isActive = activeNodeId === node.id;

    const row = document.createElement('div');
    row.className = 'tree-row' + (isActive ? ' active' : '');
    row.style.setProperty('--indent', `${depth * 16 + 8}px`);
    row.style.paddingLeft = `calc(${depth * 16 + 8}px)`;

    const toggle = document.createElement('span');
    toggle.className = 'tree-toggle' + (hasChildren ? (isExpanded ? ' expanded' : '') : ' empty');
    toggle.textContent = hasChildren ? '▶' : '';
    toggle.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleExpand(node.id);
    });

    const icon = document.createElement('span');
    icon.className = 'tree-icon';
    icon.textContent = node.type === 'chart' ? '⎈' : '📁';

    const label = document.createElement('span');
    label.className = 'tree-label';
    label.textContent = node.name;
    label.title = node.path;

    row.appendChild(toggle);
    row.appendChild(icon);
    row.appendChild(label);

    if (node.type === 'chart') {
      const badge = document.createElement('span');
      badge.className = 'tree-badge chart';
      badge.textContent = node.templateCount || 0;
      row.appendChild(badge);
      if (node.helmCommands?.deployMode) {
        const helmBadge = document.createElement('span');
        helmBadge.className = 'tree-badge helm';
        helmBadge.title = 'Helm deploy mode: ' + node.helmCommands.deployMode;
        const icons = { platform: 'P', 'umbrella-subchart': 'S', library: 'L', 'nested-subchart': 'N' };
        helmBadge.textContent = icons[node.helmCommands.deployMode] || 'H';
        row.appendChild(helmBadge);
      }
    }
    if (isSharedChart(node)) {
      const shared = document.createElement('span');
      shared.className = 'tree-badge shared';
      shared.textContent = '↗';
      shared.title = 'Shared subchart — dùng ở nhiều nơi';
      row.appendChild(shared);
    }

    row.addEventListener('click', () => selectNode(node.id));

    wrapper.appendChild(row);

    if (hasChildren) {
      const childrenEl = document.createElement('div');
      childrenEl.className = 'tree-children' + (isExpanded ? ' open' : '');
      node.children.forEach(child => {
        if (nodeMatchesFilter(child)) {
          childrenEl.appendChild(renderTreeNode(child, depth + 1));
        }
      });
      wrapper.appendChild(childrenEl);
    }

    return wrapper;
  }

  function toggleExpand(id) {
    if (expandedNodes.has(id)) expandedNodes.delete(id);
    else expandedNodes.add(id);
    renderTree();
  }

  function expandPathTo(id) {
    const node = nodeIndex.get(id);
    if (!node || !node.path) return;
    const parts = node.path.split('/');
    let current = '';
    parts.forEach((part, i) => {
      current = i === 0 ? part : `${current}/${part}`;
      const n = [...nodeIndex.values()].find(x => x.path === current);
      if (n) expandedNodes.add(n.id);
    });
    expandedNodes.add('root');
    manifest.tree.children.forEach(c => {
      if (node.path.startsWith(c.path)) expandedNodes.add(c.id);
    });
  }

  function selectNode(id) {
    activeNodeId = id;
    const node = nodeIndex.get(id);
    if (!node) return;

    expandPathTo(id);
    renderTree();
    renderDetail(node);
    updateBreadcrumb(node);
    renderGraph(node);

    $('#welcomeView').classList.add('hidden');
    $('#detailView').classList.remove('hidden');
  }

  function updateBreadcrumb(node) {
    const parts = node.path ? node.path.split('/') : [];
    let html = '<span data-id="root">Altiplano</span>';
    let path = '';
    parts.forEach(part => {
      path = path ? `${path}/${part}` : part;
      const n = [...nodeIndex.values()].find(x => x.path === path);
      if (n) {
        html += '<span class="sep">/</span>';
        html += `<span data-id="${n.id}">${part}</span>`;
      }
    });
    $('#breadcrumb').innerHTML = html;
    $('#breadcrumb').querySelectorAll('span[data-id]').forEach(span => {
      span.addEventListener('click', () => {
        const nid = span.dataset.id;
        if (nid === 'root') showWelcome();
        else selectNode(nid);
      });
    });
  }

  function showWelcome() {
    activeNodeId = null;
    $('#welcomeView').classList.remove('hidden');
    $('#detailView').classList.add('hidden');
    $('#breadcrumb').innerHTML = '<span>Altiplano Helm Explorer</span>';
    renderTree();
    GraphView.clear();
  }

  function renderWelcome() {
    const cards = $('#moduleCards');
    cards.innerHTML = '';
    manifest.tree.children.forEach(child => {
      const meta = manifest.topLevelMeta[child.name] || {};
      const chartCount = countCharts(child);
      const card = document.createElement('div');
      card.className = 'module-card';
      card.style.setProperty('--card-color', meta.color || '#00a0e3');
      card.innerHTML = `
        <div class="role">${meta.role || 'Module'}</div>
        <h3>${meta.title || child.name}</h3>
        <p>${meta.desc || ''}</p>
        <div class="counts">
          <span>${chartCount} charts</span>
          <span>${child.subchartCount || child.children?.length || 0} thành phần</span>
        </div>
      `;
      card.addEventListener('click', () => {
        expandedNodes.add(child.id);
        selectNode(child.id);
      });
      cards.appendChild(card);
    });

    const overview = $('#resourceOverview');
    const kinds = Object.entries(manifest.stats.resourceKinds).slice(0, 24);
    overview.innerHTML = `
      <h3>Kubernetes Resources — Tổng quan (${Object.keys(manifest.stats.resourceKinds).length} loại)</h3>
      <div class="kind-grid" id="kindGrid"></div>
    `;
    const grid = $('#kindGrid');
    kinds.forEach(([kind, count]) => {
      const info = manifest.k8sKindInfo[kind] || {};
      const cat = info.category || 'other';
      const chip = document.createElement('div');
      chip.className = 'kind-chip';
      chip.innerHTML = `
        <span class="kind-dot" style="background:${CATEGORY_COLORS[cat]}"></span>
        <span>${kind}</span>
        <span class="count">${count}</span>
      `;
      chip.title = info.desc || kind;
      chip.addEventListener('click', () => {
        $('#filterKind').value = kind;
        kindFilter = kind;
        renderTree();
      });
      grid.appendChild(chip);
    });

    if (manifest.platformInstallSequence) {
      const helmSection = document.createElement('div');
      helmSection.className = 'resource-overview';
      helmSection.style.marginTop = '2rem';
      helmSection.innerHTML = HelmCommandsUI.renderPlatformGuide(manifest.platformInstallSequence);
      overview.parentElement.appendChild(helmSection);
      helmSection.querySelectorAll('.btn-copy-platform').forEach(btn => {
        btn.addEventListener('click', async () => {
          const step = manifest.platformInstallSequence.find(p => p.order === parseInt(btn.dataset.order, 10));
          if (step) {
            await navigator.clipboard.writeText(step.command);
            showToast(`Đã copy lệnh bước ${step.order}!`);
          }
        });
      });
    }
  }

  function countCharts(node) {
    let c = node.type === 'chart' ? 1 : 0;
    (node.children || []).forEach(ch => { c += countCharts(ch); });
    return c;
  }

  function renderDetail(node) {
    const el = $('#detailView');
    if (node.type === 'folder' || node.type === 'root') {
      el.innerHTML = renderFolderDetail(node);
      setupDetailTabs();
      return;
    }
    el.innerHTML = renderChartDetail(node);
    setupDetailTabs();
  }

  function renderFolderDetail(node) {
    const meta = node.meta || manifest.topLevelMeta[node.name] || {};
    const totalCharts = countCharts(node);
    const allKinds = {};
    collectKinds(node, allKinds);

    return `
      <div class="detail-header">
        <div class="type-icon" style="background:${meta.color || '#243049'}33;color:${meta.color || '#00a0e3'}">📁</div>
        <div>
          <h2>${meta.title || node.name}</h2>
          <div class="path">${node.path}</div>
          <p class="desc">${meta.desc || `Thư mục chứa ${node.children?.length || 0} thành phần con.`}</p>
          <div class="detail-tags">
            <span class="tag">${meta.role || 'Folder'}</span>
            <span class="tag">${totalCharts} Helm charts</span>
            ${node.subchartCount ? `<span class="tag">${node.subchartCount} subcharts</span>` : ''}
            <span class="tag">${Object.keys(allKinds).length} K8s kinds</span>
          </div>
        </div>
      </div>
      <div class="callout">
        <strong>Helm Umbrella Chart:</strong> Thư mục này là chart cha (umbrella) chứa subcharts trong <code>charts/</code>.
        Deploy bằng <code>helm install ${node.name}</code> sẽ render tất cả subcharts cùng lúc.
      </div>
      ${Object.keys(allKinds).length ? `
        <div class="panel" style="margin-bottom:1rem">
          <div class="panel-header">K8s Resources tổng hợp (${Object.values(allKinds).reduce((a,b)=>a+b,0)})</div>
          <div class="panel-body">
            ${Object.entries(allKinds).sort((a,b)=>b[1]-a[1]).slice(0,15).map(([k,c]) =>
              `<span class="kind-badge cat-other" style="margin:.15rem">${k} ×${c}</span>`
            ).join('')}
          </div>
        </div>
      ` : ''}
      <div class="panel">
        <div class="panel-header">Thành phần con trực tiếp (${node.children?.length || 0})</div>
        <div class="panel-body">
          ${(node.children || []).map(ch => `
            <div class="shared-link" data-nav="${ch.id}">
              <span>${ch.type === 'chart' ? '⎈' : '📁'}</span>
              <span>${ch.name}</span>
              ${ch.type === 'chart' ? `<span class="dep-ver">${ch.templateCount} tpl · ${Object.keys(ch.resourceSummary||{}).length} kinds</span>` : ''}
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  function collectKinds(node, acc) {
    if (node.resourceSummary) {
      Object.entries(node.resourceSummary).forEach(([k, v]) => { acc[k] = (acc[k] || 0) + v; });
    }
    (node.children || []).forEach(ch => collectKinds(ch, acc));
  }

  function renderChartDetail(node) {
    const chart = node.chart || {};
    const isShared = isSharedChart(node);
    const sharedInstances = isShared ? manifest.sharedCharts[chart.name] : [];
    const kinds = Object.entries(node.resourceSummary || {}).sort((a, b) => b[1] - a[1]);
    const highlights = node.valuesHighlights || [];
    const deployFlow = node.deployFlow || [];
    const templateDetails = node.templateDetails || [];
    const chartFiles = node.chartFiles || [];
    const defines = node.helmDefines || [];

    const depsHtml = (chart.dependencies || []).map(dep => {
      const instances = manifest.sharedCharts[dep.name] || [];
      const shared = instances.length > 1;
      return `
        <li class="dep-item">
          <span>${shared ? '↗' : '→'}</span>
          <span class="dep-name" data-dep="${dep.name}">${dep.name}</span>
          ${shared ? `<span class="tag shared">${instances.length} instances</span>` : ''}
          <span class="dep-ver">v${dep.version}</span>
          ${dep.repository ? `<span class="dep-ver" title="Repository">${truncate(dep.repository, 30)}</span>` : ''}
        </li>
      `;
    }).join('') || '<li class="dep-item" style="color:var(--text-dim)">Không có dependency khai báo</li>';

    const sharedHtml = isShared ? `
      <div class="panel" style="margin-bottom:1rem">
        <div class="panel-header">↗ Shared Subchart — ${sharedInstances.length} vị trí</div>
        <div class="panel-body">
          <p style="font-size:.8rem;color:var(--text-muted);margin-bottom:.75rem">
            Chart <strong>${chart.name}</strong> được nhúng (vendor) tại nhiều nơi trong cây Helm.
            Đây là library chart dùng chung templates/helpers.
          </p>
          ${sharedInstances.map(inst => `
            <div class="shared-link" data-nav="${inst.id}">
              <span>⎈</span>
              <span>${inst.path}</span>
              <span class="dep-ver">v${inst.version}</span>
            </div>
          `).join('')}
        </div>
      </div>
    ` : '';

    const resourcesByCat = renderResourcesByCategory(node);
    const resourcesHtml = (node.resources || []).map(r => {
      const info = manifest.k8sKindInfo[r.kind] || {};
      const cat = info.category || 'other';
      return `
        <tr class="resource-row" data-file="${r.file}" style="cursor:pointer">
          <td><span class="kind-badge cat-${cat}">${r.kind}</span></td>
          <td>${r.apiVersion || '—'}</td>
          <td class="file-link" style="color:var(--accent)">${r.file}</td>
          <td style="color:var(--text-muted);font-family:var(--font-sans)">${info.desc || '—'}</td>
        </tr>
      `;
    }).join('');

    const highlightsHtml = highlights.length ? `
      <div class="panel" style="margin-bottom:1rem">
        <div class="panel-header">⚙ Cấu hình quan trọng (values.yaml)</div>
        <div class="panel-body">
          <div class="highlights-grid">
            ${highlights.map(h => `
              <div class="highlight-card">
                <span class="hk">${h.key}</span>
                <span class="hv">${h.value || '—'}</span>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    ` : '';

    const tplSidebarHtml = templateDetails.map((t, i) => `
      <div class="tpl-sidebar-item${i === 0 ? ' active' : ''}" data-tpl="${t.path}">
        <span class="tpl-name">${t.path.split('/').pop()}</span>
        <span class="tpl-meta">${t.lines} dòng · ${formatBytes(t.size)}${t.kinds?.length ? ' · ' + t.kinds.join(', ') : ''}${t.defines?.length ? ' · ' + t.defines.length + ' defines' : ''}</span>
      </div>
    `).join('');

    const deployFlowHtml = deployFlow.map(step => {
      const color = CATEGORY_COLORS[step.category] || '#8b9cb8';
      return `
        <div class="deploy-step" style="--step-color:${color}">
          <div class="step-kind"><span class="kind-badge cat-${step.category}">${step.kind}</span></div>
          <div class="step-desc">${step.desc || ''}</div>
          <div class="step-files">${step.files.join(', ')}</div>
        </div>
      `;
    }).join('');

    const chartFilesHtml = chartFiles.map(f => {
      if (f.subcharts) {
        return `<li class="file-item"><span>📦</span><span>charts/ (${f.count} subcharts)</span><span class="fi-size">${f.subcharts.slice(0, 3).join(', ')}…</span></li>`;
      }
      return `<li class="file-item" data-file="${f.name}"><span>📄</span><span>${f.name}</span><span class="fi-size">${f.lines} lines · ${formatBytes(f.size)}</span></li>`;
    }).join('');

    return `
      <div class="detail-header">
        <div class="type-icon" style="background:rgba(0,160,227,.15);color:#00a0e3">⎈</div>
        <div style="flex:1">
          <h2>${chart.name || node.name}</h2>
          <div class="path" id="chartPath">${node.path}</div>
          <p class="desc">${chart.description || 'Helm chart microservice'}</p>
          <div class="detail-tags">
            <span class="tag version">v${chart.version || '?'}</span>
            <span class="tag chart">${node.templateCount} templates</span>
            ${node.hasValues ? `<span class="tag">${node.valuesKeyCount} values keys</span>` : ''}
            ${isShared ? '<span class="tag shared">Shared library</span>' : ''}
            ${defines.length ? `<span class="tag">${defines.length} helm defines</span>` : ''}
          </div>
          <div class="action-bar" style="margin-top:.75rem;margin-bottom:0">
            <button class="btn" id="btnCopyPath">📋 Copy path</button>
            <button class="btn" data-tab-jump="helm-commands">⎈ Helm Commands</button>
            <button class="btn" data-tab-jump="templates">📄 Templates</button>
            <button class="btn" data-tab-jump="values">⚙ Values</button>
          </div>
          ${node.helmCommands ? `<div style="margin-top:.5rem">${HelmCommandsUI.renderModeBadge(node.helmCommands)}</div>` : ''}
        </div>
      </div>

      ${sharedHtml}
      ${highlightsHtml}

      <div class="callout">
        <strong>Kubernetes Resources:</strong> Chart render
        <strong>${kinds.reduce((s, [, c]) => s + c, 0)}</strong> manifests,
        <strong>${kinds.length}</strong> loại kind.
        ${node.hasValues ? 'Cấu hình qua <code>values.yaml</code> và <code>global</code> overrides.' : ''}
      </div>

      <div class="detail-grid">
        <div class="panel">
          <div class="panel-header">Dependencies (${(chart.dependencies || []).length})</div>
          <div class="panel-body"><ul class="dep-list">${depsHtml}</ul></div>
        </div>
        <div class="panel">
          <div class="panel-header">Resources theo nhóm</div>
          <div class="panel-body">${resourcesByCat}</div>
        </div>
      </div>

      <div class="tabs">
        <div class="tab active" data-tab="helm-commands">⎈ Helm Commands</div>
        <div class="tab" data-tab="resources">K8s Resources (${(node.resources || []).length})</div>
        <div class="tab" data-tab="templates">Templates (${templateDetails.length})</div>
        <div class="tab" data-tab="values">Values</div>
        <div class="tab" data-tab="chart-yaml">Chart.yaml</div>
        <div class="tab" data-tab="architecture">Kiến trúc deploy</div>
        <div class="tab" data-tab="files">Chart Files</div>
        <div class="tab" data-tab="helm-info">Helm Guide</div>
      </div>

      <div class="tab-content active" id="tab-helm-commands">
        ${HelmCommandsUI.renderPanel(node, manifest.platformInstallSequence)}
      </div>

      <div class="tab-content" id="tab-resources">
        <div class="panel">
          <div class="panel-body" style="padding:0;overflow-x:auto">
            <table class="resource-table">
              <thead><tr><th>Kind</th><th>API Version</th><th>Template File</th><th>Mô tả</th></tr></thead>
              <tbody>${resourcesHtml || '<tr><td colspan="4" style="padding:1rem;color:var(--text-dim)">Không phát hiện kind trong templates</td></tr>'}</tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="tab-content" id="tab-templates">
        <div class="split-pane">
          <div class="tpl-sidebar">${tplSidebarHtml || '<div class="tpl-preview-empty">Không có templates</div>'}</div>
          <div class="tpl-preview" id="tplPreview">
            <div class="tpl-preview-empty">Chọn file template bên trái để xem nội dung</div>
          </div>
        </div>
      </div>

      <div class="tab-content" id="tab-values">
        <div class="detail-grid">
          <div class="panel">
            <div class="panel-header">Cây cấu hình values.yaml</div>
            <div class="panel-body" style="max-height:400px;overflow:auto">
              ${YamlViewer.renderValuesTree(node.valuesTree || [])}
            </div>
          </div>
          <div class="panel">
            <div class="panel-header">
              Nội dung values.yaml
              <button class="btn btn-ghost" id="btnCopyValues" style="font-size:.7rem">Copy</button>
            </div>
            <div class="panel-body" style="padding:0" id="valuesPreview">
              <div class="loading-inline">Đang tải values.yaml…</div>
            </div>
          </div>
        </div>
      </div>

      <div class="tab-content" id="tab-chart-yaml">
        <div class="panel">
          <div class="panel-header">
            Chart.yaml
            <button class="btn btn-ghost" id="btnCopyChartYaml" style="font-size:.7rem">Copy</button>
          </div>
          <div class="panel-body" style="padding:0" id="chartYamlPreview">
            <div class="loading-inline">Đang tải Chart.yaml…</div>
          </div>
        </div>
        ${defines.length ? `
          <div class="panel" style="margin-top:1rem">
            <div class="panel-header">Helm Template Defines (${defines.length})</div>
            <div class="panel-body">
              <div class="define-chips">${defines.map(d => `<span class="define-chip">${d}</span>`).join('')}</div>
            </div>
          </div>
        ` : ''}
      </div>

      <div class="tab-content" id="tab-architecture">
        <div class="callout">
          <strong>Luồng deploy điển hình:</strong> Helm render templates theo thứ tự phụ thuộc —
          RBAC → Config/Secrets → Storage → Workload → Network → Gateway → Autoscale.
        </div>
        <div class="panel">
          <div class="panel-header">Deploy Pipeline (${deployFlow.length} bước)</div>
          <div class="panel-body">
            <div class="deploy-flow">${deployFlowHtml || '<span class="text-dim">Không có resources</span>'}</div>
          </div>
        </div>
        ${renderMermaidFlow(node)}
      </div>

      <div class="tab-content" id="tab-files">
        <div class="panel">
          <div class="panel-header">Files trong chart</div>
          <div class="panel-body" style="padding:0">
            <ul class="file-list">${chartFilesHtml || '<li class="file-item">Không có files</li>'}</ul>
          </div>
        </div>
        <div class="panel" style="margin-top:1rem">
          <div class="panel-header">Preview file</div>
          <div class="panel-body" style="padding:0" id="filePreview">
            <div class="tpl-preview-empty">Click file ở trên để xem</div>
          </div>
        </div>
      </div>

      <div class="tab-content" id="tab-helm-info">
        <div class="panel">
          <div class="panel-body" style="font-size:.82rem;color:var(--text-muted);line-height:1.7">
            ${getHelmGuide(node)}
          </div>
        </div>
      </div>
    `;
  }

  function renderResourcesByCategory(node) {
    const byCat = node.resourcesByCategory || {};
    const cats = Object.entries(byCat).sort((a, b) => b[1].total - a[1].total);
    if (!cats.length) return '<span class="text-dim">Không có resources</span>';

    return cats.map(([cat, data]) => `
      <div class="cat-group">
        <div class="cat-group-header">
          <span class="kind-dot" style="background:${CATEGORY_COLORS[cat] || '#8b9cb8'}"></span>
          ${cat} <span style="color:var(--text-dim);font-weight:400">(${data.total})</span>
        </div>
        <div class="cat-group-body">
          ${Object.entries(data.kinds).map(([k, c]) => `
            <span class="kind-badge cat-${cat}" style="margin:.15rem">${k} ×${c}</span>
          `).join('')}
        </div>
      </div>
    `).join('');
  }

  function renderMermaidFlow(node) {
    const flow = (node.deployFlow || []).slice(0, 10);
    if (flow.length < 2) return '';

    const nodes = flow.map((s, i) => `  S${i}["${s.kind}"]`);
    const links = flow.slice(1).map((_, i) => `  S${i} --> S${i + 1}`);

    return `
      <div class="panel" style="margin-top:1rem">
        <div class="panel-header">Sơ đồ luồng (Mermaid)</div>
        <div class="panel-body">
          <pre class="mermaid">flowchart TD
${nodes.join('\n')}
${links.join('\n')}</pre>
        </div>
      </div>
    `;
  }

  function formatBytes(n) {
    if (n < 1024) return n + ' B';
    if (n < 1048576) return (n / 1024).toFixed(1) + ' KB';
    return (n / 1048576).toFixed(1) + ' MB';
  }

  function truncate(s, n) {
    return s.length > n ? s.slice(0, n) + '…' : s;
  }

  function showToast(msg) {
    const t = document.createElement('div');
    t.className = 'toast';
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 2000);
  }

  async function loadTemplatePreview(node, tplPath) {
    const el = $('#tplPreview');
    el.innerHTML = '<div class="loading-inline">Đang tải…</div>';
    try {
      const text = await FileLoader.fetchTemplate(node.path, tplPath);
      const lang = tplPath.endsWith('.tpl') ? 'helm' : 'yaml';
      el.innerHTML = `
        <div class="code-panel">
          <div class="code-panel-header">
            <span>${tplPath}</span>
            <button class="btn btn-ghost btn-copy-tpl" style="font-size:.7rem">Copy</button>
          </div>
          ${YamlViewer.render(text, lang)}
        </div>
      `;
      el.querySelector('.btn-copy-tpl')?.addEventListener('click', async () => {
        await YamlViewer.copyText(text);
        showToast('Đã copy!');
      });
    } catch {
      el.innerHTML = '<div class="tpl-preview-empty">Không tải được file. Kiểm tra Live Server root = helm-explorer/</div>';
    }
  }

  async function loadFilePreview(node, fileName, targetId) {
    const el = document.getElementById(targetId);
    if (!el) return;
    el.innerHTML = '<div class="loading-inline">Đang tải…</div>';
    try {
      const text = await FileLoader.fetchFile(node.path, fileName);
      el.innerHTML = YamlViewer.render(text, fileName.endsWith('.tpl') ? 'helm' : 'yaml');
    } catch {
      el.innerHTML = '<div class="tpl-preview-empty">Không tải được ' + fileName + '</div>';
    }
  }

  function renderMermaid() {
    if (typeof mermaid !== 'undefined') {
      mermaid.initialize({ startOnLoad: false, theme: 'dark', securityLevel: 'loose' });
      document.querySelectorAll('.mermaid').forEach(el => {
        try { mermaid.run({ nodes: [el] }); } catch { /* ignore */ }
      });
    }
  }

  function getHelmGuide(node) {
    const kinds = Object.keys(node.resourceSummary || {});
    const chart = node.chart || {};
    const hasWorkload = kinds.some(k => ['Deployment', 'StatefulSet', 'DaemonSet', 'Job'].includes(k));
    const hasNet = kinds.some(k => ['Service', 'Ingress', 'HTTPRoute', 'TCPIngress'].includes(k));
    const hasSecret = kinds.some(k => ['Secret', 'ExternalSecret'].includes(k));
    const hasRbac = kinds.some(k => ['ServiceAccount', 'Role', 'ClusterRole'].includes(k));
    const hasGateway = kinds.some(k => ['KongPlugin', 'KongIngress'].includes(k));
    const hasStorage = kinds.some(k => ['PersistentVolumeClaim'].includes(k));
    const hasHpa = kinds.includes('HorizontalPodAutoscaler');

    let guide = `
    <h3 style="color:var(--text);margin-bottom:.75rem">Cấu trúc Helm Chart</h3>
    <table class="resource-table" style="margin-bottom:1rem">
      <tr><td><code>Chart.yaml</code></td><td>Metadata: name=<strong>${chart.name}</strong>, version=${chart.version}</td></tr>
      <tr><td><code>values.yaml</code></td><td>${node.valuesKeyCount || 0} keys cấu hình, override khi <code>helm install -f</code></td></tr>
      <tr><td><code>templates/</code></td><td>${node.templateCount} files Go-template → K8s YAML</td></tr>
      <tr><td><code>charts/</code></td><td>${(chart.dependencies || []).length} dependencies (subcharts)</td></tr>
    </table>

    <h3 style="color:var(--text);margin-bottom:.75rem">Kubernetes Components trong chart này</h3>
    <ul style="margin:0 0 1rem 1.25rem;line-height:1.8">`;

    if (hasRbac) guide += `<li><strong>RBAC:</strong> ServiceAccount + Role/RoleBinding kiểm soát quyền truy cập K8s API</li>`;
    if (hasSecret) guide += `<li><strong>Secrets:</strong> ExternalSecret pull từ Vault; Secret mount vào Pod qua volume</li>`;
    if (hasStorage) guide += `<li><strong>Storage:</strong> PVC gắn persistent disk cho database/cache</li>`;
    if (hasWorkload) guide += `<li><strong>Workload:</strong> Deployment/StatefulSet chạy container, liveness/readiness probes</li>`;
    if (hasNet) guide += `<li><strong>Service:</strong> ClusterIP expose port nội bộ; Ingress/HTTPRoute cho northbound traffic</li>`;
    if (hasGateway) guide += `<li><strong>Kong Gateway:</strong> KongPlugin xử lý auth, header manipulation, rate limiting</li>`;
    if (hasHpa) guide += `<li><strong>HPA:</strong> Tự động scale replica theo CPU/memory/custom metrics</li>`;

    guide += `</ul>

    <h3 style="color:var(--text);margin-bottom:.75rem">Lệnh deploy tham khảo</h3>
    <pre style="background:#161b22;padding:1rem;border-radius:6px;font-size:.75rem;overflow-x:auto;color:#7ee787">
# Dry-run render manifests
helm template ${chart.name} ./${node.path} -f custom-values.yaml

# Install / upgrade
helm upgrade --install ${chart.name} ./${node.path} \\
  --namespace altiplano --create-namespace \\
  -f custom-values.yaml

# Xem values mặc định
helm show values ./${node.path}
    </pre>`;

    if (isSharedChart(node)) {
      guide += `<p style="margin-top:1rem"><strong>📚 Shared Library Chart:</strong> Không deploy trực tiếp.
      Được include như subchart, cung cấp templates <code>_helpers.tpl</code> và patterns chung cho microservices.</p>`;
    }

    if ((chart.dependencies || []).length) {
      guide += `<p style="margin-top:.75rem"><strong>Dependencies:</strong> ${chart.dependencies.map(d => d.name).join(', ')}
      — render cùng parent chart, values nested dưới key tên subchart.</p>`;
    }

    return guide;
  }

  function setupDetailTabs() {
    const node = nodeIndex.get(activeNodeId);
    if (!node) return;

    $$('.tab').forEach(tab => {
      tab.addEventListener('click', () => {
        const name = tab.dataset.tab;
        $$('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
        $$('.tab-content').forEach(c => c.classList.toggle('active', c.id === `tab-${name}`));
        if (name === 'architecture') setTimeout(renderMermaid, 50);
        if (name === 'values' && node.hasValues) loadFilePreview(node, 'values.yaml', 'valuesPreview');
        if (name === 'chart-yaml') loadFilePreview(node, 'Chart.yaml', 'chartYamlPreview');
      });
    });

    $$('[data-tab-jump]').forEach(btn => {
      btn.addEventListener('click', () => {
        const name = btn.dataset.tabJump;
        $$('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
        $$('.tab-content').forEach(c => c.classList.toggle('active', c.id === `tab-${name}`));
        if (name === 'values' && node.hasValues) loadFilePreview(node, 'values.yaml', 'valuesPreview');
        if (name === 'architecture') setTimeout(renderMermaid, 50);
      });
    });

    HelmCommandsUI.wireCopyHandlers($('#detailView'), node);

    $$('[data-nav]').forEach(el => {
      el.addEventListener('click', () => selectNode(el.dataset.nav));
    });

    $$('.dep-name').forEach(el => {
      el.addEventListener('click', () => {
        const depName = el.dataset.dep;
        const instances = manifest.sharedCharts[depName];
        if (instances && instances.length > 0) selectNode(instances[0].id);
      });
    });

    // Template sidebar
    const firstTpl = node.templateDetails?.[0];
    if (firstTpl) loadTemplatePreview(node, firstTpl.path);

    $$('.tpl-sidebar-item').forEach(item => {
      item.addEventListener('click', () => {
        $$('.tpl-sidebar-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        loadTemplatePreview(node, item.dataset.tpl);
      });
    });

    // Resource row → jump to template
    $$('.resource-row').forEach(row => {
      row.addEventListener('click', () => {
        const file = row.dataset.file;
        const tplPath = node.templateDetails?.find(t => t.path.endsWith(file))?.path
          || `templates/${file}`;
        $$('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === 'templates'));
        $$('.tab-content').forEach(c => c.classList.toggle('active', c.id === 'tab-templates'));
        $$('.tpl-sidebar-item').forEach(i => {
          i.classList.toggle('active', i.dataset.tpl === tplPath);
        });
        loadTemplatePreview(node, tplPath);
      });
    });

    // Chart files preview
    $$('.file-item[data-file]').forEach(item => {
      item.addEventListener('click', () => {
        loadFilePreview(node, item.dataset.file, 'filePreview');
      });
    });

    // Copy buttons
    $('#btnCopyPath')?.addEventListener('click', async () => {
      await YamlViewer.copyText(node.path);
      showToast('Đã copy path!');
    });

    $('#btnCopyValues')?.addEventListener('click', async () => {
      try {
        const text = await FileLoader.fetchFile(node.path, 'values.yaml');
        await YamlViewer.copyText(text);
        showToast('Đã copy values.yaml!');
      } catch { showToast('Lỗi copy'); }
    });

    $('#btnCopyChartYaml')?.addEventListener('click', async () => {
      try {
        const text = await FileLoader.fetchFile(node.path, 'Chart.yaml');
        await YamlViewer.copyText(text);
        showToast('Đã copy Chart.yaml!');
      } catch { showToast('Lỗi copy'); }
    });
  }

  function renderGraph(node) {
    if ($('#graphPanel').classList.contains('hidden')) return;
    const fullNode = nodeIndex.get(node.id);
    GraphView.render(fullNode, manifest, manifest.dependencyLinks);
    $('#graphHint').textContent = fullNode.chart
      ? `Dependencies & liên kết của ${fullNode.chart.name}`
      : `Cấu trúc con của ${fullNode.name}`;
  }

  function setupEvents() {
    $('#globalSearch').addEventListener('input', debounce(onSearch, 200));
    $('#globalSearch').addEventListener('focus', () => {
      if ($('#globalSearch').value.trim()) onSearch();
    });
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.search-box') && !e.target.closest('.search-results')) {
        $('#searchResults').classList.add('hidden');
      }
    });

    $('#filterKind').addEventListener('change', (e) => {
      kindFilter = e.target.value;
      renderTree();
    });

    $('#expandAll').addEventListener('click', () => {
      nodeIndex.forEach((_, id) => expandedNodes.add(id));
      renderTree();
    });
    $('#collapseAll').addEventListener('click', () => {
      expandedNodes.clear();
      expandedNodes.add('root');
      manifest.tree.children.forEach(c => expandedNodes.add(c.id));
      renderTree();
    });

    $('#btnGraph').addEventListener('click', () => {
      const panel = $('#graphPanel');
      panel.classList.toggle('hidden');
      $('#btnGraph').classList.toggle('active', !panel.classList.contains('hidden'));
      $('#graphLegend').innerHTML = `
        <span class="legend-item"><span class="legend-line dep"></span> Dependency</span>
        <span class="legend-item"><span class="legend-line shared" style="border-top:2px dashed #ff8c42;height:0"></span> Shared subchart</span>
        <span class="legend-item"><span style="width:10px;height:10px;border-radius:50%;background:#2dd4a0;display:inline-block"></span> Parent chart</span>
        <span class="legend-item"><span style="width:10px;height:10px;border-radius:50%;background:#e63946;display:inline-block"></span> Dependent</span>
      `;
      if (!panel.classList.contains('hidden') && activeNodeId) {
        GraphView.render(nodeIndex.get(activeNodeId), manifest, manifest.dependencyLinks);
        GraphView.resize();
      }
    });
    $('#graphClose').addEventListener('click', () => {
      $('#graphPanel').classList.add('hidden');
      $('#btnGraph').classList.remove('active');
    });
    $('#graphFit').addEventListener('click', () => {
      if (activeNodeId) GraphView.render(nodeIndex.get(activeNodeId), manifest, manifest.dependencyLinks);
    });

    $('#btnDashboard').addEventListener('click', showWelcome);

    window.addEventListener('graph-navigate', (e) => selectNode(e.detail.id));
    window.addEventListener('toast', (e) => showToast(e.detail));

    // Keyboard shortcut
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        $('#globalSearch').focus();
      }
      if (e.key === 'Escape') {
        $('#searchResults').classList.add('hidden');
        $('#globalSearch').blur();
      }
    });

    // Sidebar resize
    setupResize();
  }

  function onSearch() {
    const q = $('#globalSearch').value.trim().toLowerCase();
    const results = $('#searchResults');
    if (!q) { results.classList.add('hidden'); return; }

    const matches = searchIndex.filter(item =>
      item.name.toLowerCase().includes(q) ||
      item.path.toLowerCase().includes(q) ||
      item.chartName.toLowerCase().includes(q) ||
      (item.highlights || '').toLowerCase().includes(q) ||
      (item.deployMode || '').toLowerCase().includes(q)
    ).slice(0, 25);

    if (!matches.length) {
      results.innerHTML = '<div class="search-item"><span class="si-name">Không tìm thấy</span></div>';
    } else {
      results.innerHTML = matches.map((m, i) => `
        <div class="search-item${i === 0 ? ' focused' : ''}" data-id="${m.id}">
          <span class="si-name">${highlight(m.name, q)} ${m.type === 'resource' ? '<span class="tag">resource</span>' : ''}</span>
          <span class="si-path">${highlight(m.path, q)}</span>
          ${m.chartName ? `<span class="si-meta">Chart: ${m.chartName}</span>` : ''}
        </div>
      `).join('');
      results.querySelectorAll('.search-item').forEach(item => {
        item.addEventListener('click', () => {
          selectNode(item.dataset.id);
          results.classList.add('hidden');
          $('#globalSearch').value = '';
        });
      });
    }
    results.classList.remove('hidden');
  }

  function highlight(text, q) {
    const idx = text.toLowerCase().indexOf(q);
    if (idx < 0) return text;
    return text.slice(0, idx) + '<mark style="background:rgba(0,160,227,.3);color:inherit">' +
      text.slice(idx, idx + q.length) + '</mark>' + text.slice(idx + q.length);
  }

  function debounce(fn, ms) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
  }

  function setupResize() {
    const handle = $('#resizeHandle');
    const sidebar = $('#sidebar');
    let startX, startW;

    handle.addEventListener('mousedown', (e) => {
      e.preventDefault();
      startX = e.clientX;
      startW = sidebar.offsetWidth;
      handle.classList.add('dragging');
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });

    function onMove(e) {
      const w = Math.max(200, Math.min(window.innerWidth * 0.5, startW + e.clientX - startX));
      sidebar.style.width = w + 'px';
    }
    function onUp() {
      handle.classList.remove('dragging');
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
