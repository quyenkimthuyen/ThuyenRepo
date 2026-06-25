const RELATIONSHIP_DIMS = ['friendship', 'trust', 'respect', 'dependency'];

const DEFAULT_RELATIONSHIP = {
  friendship: 50,
  trust: 50,
  respect: 50,
  dependency: 20,
};

function initRelationships(state) {
  if (!state.relationships) state.relationships = {};
  return state.relationships;
}

function getRelationship(state, characterId) {
  initRelationships(state);
  if (!state.relationships[characterId]) {
    state.relationships[characterId] = { ...DEFAULT_RELATIONSHIP };
  }
  return state.relationships[characterId];
}

function applyRelationshipEffects(state, effects) {
  if (!effects) return [];
  initRelationships(state);
  const changes = [];

  Object.entries(effects).forEach(([charId, dims]) => {
    const rel = getRelationship(state, charId);
    Object.entries(dims).forEach(([dim, delta]) => {
      if (RELATIONSHIP_DIMS.includes(dim)) {
        const before = rel[dim];
        rel[dim] = Math.max(0, Math.min(100, rel[dim] + delta));
        if (before !== rel[dim]) {
          changes.push({ characterId: charId, dimension: dim, delta, newValue: rel[dim] });
        }
      }
    });
  });

  return changes;
}

function getAllRelationships(state) {
  initRelationships(state);
  return state.relationships;
}

function getCharacterName(characters, charId) {
  const char = characters.find(c => c.id === charId);
  return char ? tl(char.name) : charId;
}

function getRelationshipColor(value) {
  if (value >= 70) return 'var(--accent-green)';
  if (value >= 40) return 'var(--accent-gold)';
  return 'var(--accent-red)';
}
