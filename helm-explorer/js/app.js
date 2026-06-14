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
      return;
    }
    el.innerHTML = renderChartDetail(node);
    setupDetailTabs();
  }

  function renderFolderDetail(node) {
    const meta = node.meta || manifest.topLevelMeta[node.name] || {};
    const childCharts = (node.children || []).filter(c => c.type === 'chart');
    const totalCharts = countCharts(node);

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
          </div>
        </div>
      </div>
      <div class="callout">
        <strong>Helm Umbrella Chart:</strong> Thư mục này là một chart cha (umbrella) chứa các subchart trong <code>charts/</code>.
        Mỗi subchart độc lập deploy một hoặc nhiều Kubernetes resources.
      </div>
      <div class="panel">
        <div class="panel-header">Thành phần con trực tiếp (${node.children?.length || 0})</div>
        <div class="panel-body">
          ${(node.children || []).map(ch => `
            <div class="shared-link" data-nav="${ch.id}">
              <span>${ch.type === 'chart' ? '⎈' : '📁'}</span>
              <span>${ch.name}</span>
              ${ch.type === 'chart' ? `<span class="dep-ver">${ch.templateCount} templates</span>` : ''}
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  function renderChartDetail(node) {
    const chart = node.chart || {};
    const isShared = isSharedChart(node);
    const sharedInstances = isShared ? manifest.sharedCharts[chart.name] : [];
    const kinds = Object.entries(node.resourceSummary || {}).sort((a, b) => b[1] - a[1]);

    const depsHtml = (chart.dependencies || []).map(dep => {
      const instances = manifest.sharedCharts[dep.name] || [];
      const shared = instances.length > 1;
      return `
        <li class="dep-item">
          <span>${shared ? '↗' : '→'}</span>
          <span class="dep-name" data-dep="${dep.name}">${dep.name}</span>
          ${shared ? `<span class="tag shared">${instances.length} instances</span>` : ''}
          <span class="dep-ver">v${dep.version}</span>
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

    const resourcesHtml = (node.resources || []).map(r => {
      const info = manifest.k8sKindInfo[r.kind] || {};
      const cat = info.category || 'other';
      return `
        <tr>
          <td><span class="kind-badge cat-${cat}">${r.kind}</span></td>
          <td>${r.apiVersion || '—'}</td>
          <td>${r.file}</td>
          <td style="color:var(--text-muted);font-family:var(--font-sans)">${info.desc || '—'}</td>
        </tr>
      `;
    }).join('');

    const templatesHtml = (node.templateFiles || []).map(f =>
      `<li class="tpl-item"><span>📄</span><span style="font-family:var(--font-mono);font-size:.78rem">${f}</span></li>`
    ).join('');

    return `
      <div class="detail-header">
        <div class="type-icon" style="background:rgba(0,160,227,.15);color:#00a0e3">⎈</div>
        <div>
          <h2>${chart.name || node.name}</h2>
          <div class="path">${node.path}</div>
          <p class="desc">${chart.description || 'Helm chart microservice'}</p>
          <div class="detail-tags">
            <span class="tag version">v${chart.version || '?'}</span>
            <span class="tag chart">${node.templateCount} templates</span>
            ${node.hasValues ? `<span class="tag">${node.valuesKeyCount} values keys</span>` : ''}
            ${isShared ? '<span class="tag shared">Shared library</span>' : ''}
          </div>
        </div>
      </div>

      ${sharedHtml}

      <div class="callout">
        <strong>Kubernetes Resources:</strong> Chart này render
        <strong>${kinds.reduce((s, [, c]) => s + c, 0)}</strong> resource manifests
        thuộc <strong>${kinds.length}</strong> loại K8s API kind khác nhau qua Helm templates.
      </div>

      <div class="detail-grid">
        <div class="panel">
          <div class="panel-header">Dependencies (${(chart.dependencies || []).length})</div>
          <div class="panel-body"><ul class="dep-list">${depsHtml}</ul></div>
        </div>
        <div class="panel">
          <div class="panel-header">Resource Summary</div>
          <div class="panel-body">
            ${kinds.map(([k, c]) => {
              const info = manifest.k8sKindInfo[k] || {};
              const cat = info.category || 'other';
              return `<div class="kind-chip" style="margin-bottom:.35rem" data-kind="${k}">
                <span class="kind-dot" style="background:${CATEGORY_COLORS[cat]}"></span>
                <span>${k}</span><span class="count">×${c}</span>
              </div>`;
            }).join('') || '<span style="color:var(--text-dim)">Không có template YAML</span>'}
          </div>
        </div>
      </div>

      <div class="tabs">
        <div class="tab active" data-tab="resources">K8s Resources (${(node.resources || []).length})</div>
        <div class="tab" data-tab="templates">Template Files (${(node.templateFiles || []).length})</div>
        <div class="tab" data-tab="helm-info">Helm & K8s Guide</div>
      </div>

      <div class="tab-content active" id="tab-resources">
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
        <div class="panel">
          <div class="panel-body">
            <ul class="template-list">${templatesHtml || '<li style="color:var(--text-dim)">Không có templates</li>'}</ul>
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

  function getHelmGuide(node) {
    const kinds = Object.keys(node.resourceSummary || {});
    const hasWorkload = kinds.some(k => ['Deployment', 'StatefulSet', 'DaemonSet', 'Job'].includes(k));
    const hasNet = kinds.some(k => ['Service', 'Ingress', 'HTTPRoute'].includes(k));
    const hasSecret = kinds.some(k => ['Secret', 'ExternalSecret'].includes(k));

    let guide = `<p><strong>Cấu trúc Helm Chart:</strong></p>
    <ul style="margin:.5rem 0 1rem 1.25rem">
      <li><code>Chart.yaml</code> — metadata, version, dependencies</li>
      <li><code>values.yaml</code> — giá trị mặc định, override khi deploy</li>
      <li><code>templates/</code> — Go templates → Kubernetes manifests</li>
      <li><code>charts/</code> — subcharts (dependencies đóng gói local)</li>
    </ul>`;

    if (hasWorkload) {
      guide += `<p><strong>Workload:</strong> Chart deploy ứng dụng container qua Deployment/StatefulSet.
      Pod nhận config từ ConfigMap/Secret, expose qua Service.</p>`;
    }
    if (hasNet) {
      guide += `<p><strong>Networking:</strong> Ingress/HTTPRoute route traffic từ Kong Gateway vào Service.
      Altiplano dùng Kong plugins cho auth, path manipulation.</p>`;
    }
    if (hasSecret) {
      guide += `<p><strong>Secrets:</strong> ExternalSecret đồng bộ credentials từ vault.
      Certificates quản lý TLS cho inter-service communication.</p>`;
    }

    if (isSharedChart(node)) {
      guide += `<p><strong>Shared Library:</strong> Chart này là thư viện dùng chung — không deploy độc lập
      mà được include vào nhiều microservice charts qua <code>charts/</code> subfolder.</p>`;
    }

    return guide;
  }

  function setupDetailTabs() {
    $$('.tab').forEach(tab => {
      tab.addEventListener('click', () => {
        const name = tab.dataset.tab;
        $$('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
        $$('.tab-content').forEach(c => c.classList.toggle('active', c.id === `tab-${name}`));
      });
    });

    $$('[data-nav]').forEach(el => {
      el.addEventListener('click', () => selectNode(el.dataset.nav));
    });

    $$('.dep-name').forEach(el => {
      el.addEventListener('click', () => {
        const depName = el.dataset.dep;
        const instances = manifest.sharedCharts[depName];
        if (instances && instances.length > 0) {
          selectNode(instances[0].id);
        }
      });
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
      item.chartName.toLowerCase().includes(q)
    ).slice(0, 20);

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
