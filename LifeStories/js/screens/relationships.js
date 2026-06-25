function renderRelationships(container, state) {
  const relationships = getAllRelationships(state);
  const allChars = getAllCharacters();
  const entries = Object.entries(relationships);

  let html = `
    <div class="screen-header">
      <h1 data-i18n="relationships">${t('relationships')}</h1>
    </div>
  `;

  if (entries.length === 0) {
    html += '<div class="empty-state" data-i18n="noRelationships">' + t('noRelationships') + '</div>';
  } else {
    entries.forEach(([charId, rel]) => {
      const char = allChars[charId] || { name: { en: charId, vi: charId }, emoji: '👤' };
      html += `
        <div class="relationship-card">
          <div class="relationship-header">
            <span class="avatar">${char.emoji || '👤'}</span>
            <h4>${tl(char.name)}</h4>
          </div>
      `;

      RELATIONSHIP_DIMS.forEach(dim => {
        const val = rel[dim] || 0;
        html += `
          <div class="rel-dim">
            <div class="rel-dim-label">
              <span data-i18n="${dim}">${t(dim)}</span>
              <span>${val}%</span>
            </div>
            <div class="rel-bar">
              <div class="rel-bar-fill" style="width:${val}%;background:${getRelationshipColor(val)}"></div>
            </div>
          </div>
        `;
      });

      html += '</div>';
    });
  }

  container.innerHTML = html;
  applyI18n(container);
}
