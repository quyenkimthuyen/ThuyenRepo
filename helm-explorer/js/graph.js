/**
 * Altiplano Helm Explorer — Relationship Graph (SVG)
 */
const GraphView = (() => {
  const CATEGORY_COLORS = {
    workload: '#00a0e3',
    network: '#a78bfa',
    config: '#fbbf24',
    storage: '#f4a261',
    rbac: '#f87171',
    crd: '#ff6b35',
    gateway: '#2dd4a0',
    other: '#8b9cb8',
  };

  let svg, width, height, nodes = [], links = [], simulation = null;

  function init(svgEl) {
    svg = svgEl;
    resize();
    window.addEventListener('resize', resize);
  }

  function resize() {
    const wrap = svg.parentElement;
    width = wrap.clientWidth;
    height = wrap.clientHeight || 400;
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  }

  function clear() {
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    nodes = [];
    links = [];
  }

  function render(centerNode, manifest, depLinks) {
    clear();
    if (!centerNode) return;

    const defs = el('defs');
    const marker = el('marker');
    marker.setAttribute('id', 'arrow');
    marker.setAttribute('viewBox', '0 0 10 10');
    marker.setAttribute('refX', '20');
    marker.setAttribute('refY', '5');
    marker.setAttribute('markerWidth', '6');
    marker.setAttribute('markerHeight', '6');
    marker.setAttribute('orient', 'auto');
    marker.appendChild(el('path', { d: 'M 0 0 L 10 5 L 0 10 z', fill: '#00a0e3' }));
    defs.appendChild(marker);

    const markerShared = el('marker');
    markerShared.setAttribute('id', 'arrow-shared');
    markerShared.setAttribute('viewBox', '0 0 10 10');
    markerShared.setAttribute('refX', '20');
    markerShared.setAttribute('refY', '5');
    markerShared.setAttribute('markerWidth', '6');
    markerShared.setAttribute('markerHeight', '6');
    markerShared.setAttribute('orient', 'auto');
    markerShared.appendChild(el('path', { d: 'M 0 0 L 10 5 L 0 10 z', fill: '#ff8c42' }));
    defs.appendChild(markerShared);
    svg.appendChild(defs);

    const gLinks = el('g', { class: 'links' });
    const gNodes = el('g', { class: 'nodes' });
    svg.appendChild(gLinks);
    svg.appendChild(gNodes);

    // Build graph around center node
    const nodeMap = new Map();
    const cx = width / 2;
    const cy = height / 2;

    nodeMap.set(centerNode.id, {
      id: centerNode.id,
      label: centerNode.chart?.name || centerNode.name,
      type: 'center',
      x: cx,
      y: cy,
      r: 36,
      color: '#00a0e3',
    });

    // Dependencies (outgoing)
    const deps = (centerNode.chart?.dependencies || []);
    const depAngleStep = deps.length ? (Math.PI * 0.8) / Math.max(deps.length - 1, 1) : 0;
    const depStart = -Math.PI * 0.4;

    deps.forEach((dep, i) => {
      const depId = `dep:${dep.name}`;
      const instances = manifest.sharedCharts[dep.name] || [];
      const isShared = instances.length > 1;
      const angle = depStart + depAngleStep * i;
      const dist = 130;
      const x = cx + Math.cos(angle - Math.PI / 2) * dist;
      const y = cy + Math.sin(angle - Math.PI / 2) * dist;

      if (!nodeMap.has(depId)) {
        nodeMap.set(depId, {
          id: depId,
          label: dep.name,
          type: isShared ? 'shared' : 'dependency',
          x, y,
          r: isShared ? 28 : 24,
          color: isShared ? '#ff8c42' : '#7b68ee',
          instances,
        });
      }

      links.push({
        source: centerNode.id,
        target: depId,
        type: isShared ? 'shared' : 'dependency',
      });

      // If shared, show instance nodes
      if (isShared && instances.length <= 6) {
        instances.forEach((inst, j) => {
          const instId = `inst:${inst.id}`;
          const subAngle = angle + (j - (instances.length - 1) / 2) * 0.35;
          const subDist = 90;
          const ix = x + Math.cos(subAngle - Math.PI / 2) * subDist;
          const iy = y + Math.sin(subAngle - Math.PI / 2) * subDist;
          const shortName = inst.path.split('/').pop();

          nodeMap.set(instId, {
            id: instId,
            label: shortName,
            fullPath: inst.path,
            type: 'instance',
            x: ix,
            y: iy,
            r: 18,
            color: '#5a6d8a',
            navigateId: inst.id,
          });

          links.push({ source: depId, target: instId, type: 'instance' });
        });
      }
    });

    // Parent chart (if nested)
    const pathParts = centerNode.path.split('/');
    if (pathParts.length > 1) {
      const parentPath = pathParts.slice(0, -1).join('/');
      const parentEntry = Object.values(manifest.flatIndex).find(n => n.path === parentPath);
      if (parentEntry) {
        const parentId = `parent:${parentEntry.id}`;
        nodeMap.set(parentId, {
          id: parentId,
          label: parentEntry.name,
          type: 'parent',
          x: cx,
          y: cy - 120,
          r: 26,
          color: '#2dd4a0',
          navigateId: parentEntry.id,
        });
        links.push({ source: parentId, target: centerNode.id, type: 'parent' });
      }
    }

    // Charts that depend on this one (reverse deps)
    const chartName = centerNode.chart?.name;
    if (chartName && manifest.sharedCharts[chartName]) {
      const dependents = manifest.dependencyLinks.filter(
        l => l.targetName === chartName && l.source !== centerNode.id
      ).slice(0, 5);

      dependents.forEach((dep, i) => {
        const depNodeId = `revdep:${dep.source}`;
        const entry = manifest.flatIndex[dep.source];
        if (!entry) return;
        const angle = Math.PI + (i - (dependents.length - 1) / 2) * 0.5;
        const x = cx + Math.cos(angle) * 140;
        const y = cy + Math.sin(angle) * 100;

        nodeMap.set(depNodeId, {
          id: depNodeId,
          label: entry.name,
          type: 'dependent',
          x, y,
          r: 22,
          color: '#e63946',
          navigateId: dep.source,
        });
        links.push({ source: depNodeId, target: centerNode.id, type: 'dependent' });
      });
    }

    nodes = [...nodeMap.values()];

    // Draw links
    links.forEach(link => {
      const s = nodes.find(n => n.id === link.source);
      const t = nodes.find(n => n.id === link.target);
      if (!s || !t) return;

      const line = el('line');
      line.setAttribute('x1', s.x);
      line.setAttribute('y1', s.y);
      line.setAttribute('x2', t.x);
      line.setAttribute('y2', t.y);
      line.setAttribute('stroke', link.type === 'shared' ? '#ff8c42' : link.type === 'parent' ? '#2dd4a0' : link.type === 'dependent' ? '#e63946' : '#00a0e3');
      line.setAttribute('stroke-width', link.type === 'instance' ? '1' : '2');
      line.setAttribute('opacity', '0.6');
      if (link.type === 'shared' || link.type === 'instance') {
        line.setAttribute('stroke-dasharray', '5,3');
      }
      if (link.type === 'dependency' || link.type === 'shared') {
        line.setAttribute('marker-end', link.type === 'shared' ? 'url(#arrow-shared)' : 'url(#arrow)');
      }
      gLinks.appendChild(line);
    });

    // Draw nodes
    nodes.forEach(node => {
      const g = el('g', { class: 'graph-node', cursor: node.navigateId ? 'pointer' : 'default' });
      g.style.cursor = node.navigateId ? 'pointer' : 'default';

      const circle = el('circle');
      circle.setAttribute('cx', node.x);
      circle.setAttribute('cy', node.y);
      circle.setAttribute('r', node.r);
      circle.setAttribute('fill', node.color + '33');
      circle.setAttribute('stroke', node.color);
      circle.setAttribute('stroke-width', node.type === 'center' ? '3' : '2');
      g.appendChild(circle);

      const label = el('text');
      label.setAttribute('x', node.x);
      label.setAttribute('y', node.y + node.r + 14);
      label.setAttribute('text-anchor', 'middle');
      label.setAttribute('fill', '#e8edf5');
      label.setAttribute('font-size', node.type === 'center' ? '11' : '9');
      label.setAttribute('font-family', 'IBM Plex Sans, sans-serif');
      const displayLabel = node.label.length > 18 ? node.label.slice(0, 16) + '…' : node.label;
      label.textContent = displayLabel;
      g.appendChild(label);

      if (node.type === 'center') {
        const sub = el('text');
        sub.setAttribute('x', node.x);
        sub.setAttribute('y', node.y + 4);
        sub.setAttribute('text-anchor', 'middle');
        sub.setAttribute('fill', '#e8edf5');
        sub.setAttribute('font-size', '10');
        sub.setAttribute('font-weight', '600');
        sub.setAttribute('font-family', 'IBM Plex Sans, sans-serif');
        const lines = wrapText(node.label, 14);
        lines.forEach((ln, i) => {
          const t = el('tspan');
          t.setAttribute('x', node.x);
          t.setAttribute('dy', i === 0 ? 0 : 12);
          t.textContent = ln;
          sub.appendChild(t);
        });
        g.appendChild(sub);
      }

      if (node.navigateId) {
        g.addEventListener('click', () => {
          window.dispatchEvent(new CustomEvent('graph-navigate', { detail: { id: node.navigateId } }));
        });
      }

      gNodes.appendChild(g);
    });
  }

  function wrapText(text, maxLen) {
    if (text.length <= maxLen) return [text];
    const mid = Math.floor(text.length / 2);
    const split = text.lastIndexOf('-', mid + 5);
    if (split > 0) return [text.slice(0, split), text.slice(split + 1)];
    return [text.slice(0, maxLen), text.slice(maxLen)];
  }

  function el(tag, attrs = {}) {
    const e = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v));
    return e;
  }

  return { init, render, resize, clear };
})();
