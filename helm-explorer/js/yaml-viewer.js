/**
 * YAML / code viewer with basic syntax highlighting
 */
const YamlViewer = (() => {
  function escapeHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function highlightYaml(text) {
    return text.split('\n').map(line => {
      const commentIdx = line.indexOf('#');
      let code = line;
      let comment = '';
      if (commentIdx >= 0) {
        code = line.slice(0, commentIdx);
        comment = line.slice(commentIdx);
      }

      const keyMatch = code.match(/^(\s*)([a-zA-Z0-9_.-]+)(\s*:\s*)(.*)/);
      if (keyMatch) {
        const [, indent, key, colon, val] = keyMatch;
        const valHtml = val
          ? `<span class="yaml-val">${colorizeValue(val)}</span>`
          : '';
        return `<span class="yaml-line"><span class="yaml-indent">${escapeHtml(indent)}</span><span class="yaml-key">${escapeHtml(key)}</span><span class="yaml-colon">${escapeHtml(colon)}</span>${valHtml}${comment ? `<span class="yaml-comment">${escapeHtml(comment)}</span>` : ''}</span>`;
      }

      if (code.trim().startsWith('- ')) {
        return `<span class="yaml-line"><span class="yaml-dash">-</span> ${colorizeValue(escapeHtml(code.trim().slice(2)))}${comment ? `<span class="yaml-comment">${escapeHtml(comment)}</span>` : ''}</span>`;
      }

      return `<span class="yaml-line">${escapeHtml(line)}</span>`;
    }).join('\n');
  }

  function colorizeValue(val) {
    const v = escapeHtml(val.trim());
    if (/^(true|false|null|~)$/i.test(val.trim())) return `<span class="yaml-bool">${v}</span>`;
    if (/^-?\d+(\.\d+)?$/.test(val.trim())) return `<span class="yaml-num">${v}</span>`;
    if (/^["'].*["']$/.test(val.trim())) return `<span class="yaml-str">${v}</span>`;
    if (val.includes('{{')) return `<span class="yaml-helm">${v}</span>`;
    return v;
  }

  function highlightHelm(text) {
    return text.split('\n').map(line => {
      let html = escapeHtml(line);
      html = html.replace(/(\{\{[-~]?[\s\S]*?[-~]?\}\})/g, '<span class="yaml-helm">$1</span>');
      html = html.replace(/(\{\{-\s*define\s+"[^"]+"\s*-?\}\})/g, '<span class="yaml-define">$1</span>');
      html = html.replace(/(\{\{-\s*template\s+"[^"]+"\s*\.?\s*-?\}\})/g, '<span class="yaml-template">$1</span>');
      if (line.trim().startsWith('#')) html = `<span class="yaml-comment">${html}</span>`;
      return `<span class="yaml-line">${html}</span>`;
    }).join('\n');
  }

  function render(text, lang = 'yaml') {
    const highlighted = lang === 'helm' ? highlightHelm(text) : highlightYaml(text);
    const lines = text.split('\n');
    const lineNums = lines.map((_, i) => `<span class="ln">${i + 1}</span>`).join('');
    return `
      <div class="code-viewer">
        <div class="code-gutter">${lineNums}</div>
        <pre class="code-content"><code>${highlighted}</code></pre>
      </div>
    `;
  }

  function renderValuesTree(nodes, depth = 0) {
    if (!nodes || !nodes.length) return '<span class="text-dim">Không có values.yaml</span>';
    return `<ul class="values-tree">${nodes.map(n => `
      <li style="--depth:${n.depth}">
        <span class="vt-key">${escapeHtml(n.key)}</span>
        ${n.value !== undefined ? `<span class="vt-val">${escapeHtml(n.value)}</span>` : ''}
        ${n.children?.length ? renderValuesTree(n.children, depth + 1) : ''}
      </li>
    `).join('')}</ul>`;
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      return false;
    }
  }

  return { render, renderValuesTree, copyText, escapeHtml };
})();
