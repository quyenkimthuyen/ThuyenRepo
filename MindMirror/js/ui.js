(function () {
const { NODE_TYPES, ROOT_TYPE, getNodeMeta, buildTreeLevels, getNodeCount } = window.CognitiveTree;
const { getInsightQuestions, CONVICTION_ITEMS, TRUTH_ITEMS } = window.CognitiveInsight;

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(isoDate) {
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(isoDate));
}

function setActiveView(viewName) {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("is-active", tab.dataset.view === viewName);
  });

  document.querySelectorAll(".view").forEach((view) => {
    view.classList.remove("is-active");
  });

  const targetId = viewName === "trees" ? "treesView" : `${viewName}View`;
  document.getElementById(targetId)?.classList.add("is-active");
}

function showEditor() {
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("is-active"));
  document.getElementById("editorView").classList.add("is-active");
  document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("is-active"));
}

function renderTreeList(container, emptyState, trees) {
  emptyState.hidden = trees.length > 0;

  const sortedTrees = trees
    .slice()
    .sort((a, b) => {
      const groupCompare = getRelationshipGroup(a).localeCompare(getRelationshipGroup(b), "vi");
      return groupCompare || new Date(b.updatedAt) - new Date(a.updatedAt);
    });

  const groupedTrees = sortedTrees.reduce((groups, tree) => {
    const group = getRelationshipGroup(tree);
    const items = groups.get(group) || [];
    items.push(tree);
    groups.set(group, items);
    return groups;
  }, new Map());

  container.innerHTML = Array.from(groupedTrees.entries())
    .map(([group, groupTrees]) => `
      <section class="tree-group">
        <div class="tree-group__header">
          <h2>${escapeHtml(group)}</h2>
          <span>${groupTrees.length} tình huống</span>
        </div>
        <div class="tree-group__items">
          ${groupTrees.map(renderTreeListItem).join("")}
        </div>
      </section>
    `)
    .join("");
}

function renderTreeListItem(tree) {
  return `
      <article class="tree-list-item" data-tree-id="${escapeHtml(tree.id)}" tabindex="0" role="button">
        <div>
          <h2>${escapeHtml(tree.title)}</h2>
          <p>Ngày tạo: ${formatDate(tree.createdAt)}</p>
        </div>
        <span class="node-count">${getNodeCount(tree)} node</span>
      </article>
    `;
}

function getRelationshipGroup(tree) {
  return tree.relationshipGroup || "Tự tạo";
}

function renderTreeCanvas(container, tree, selectedNodeId) {
  if (!tree) {
    container.innerHTML = "";
    return;
  }

  const levels = buildTreeLevels(tree);
  const nodesByParent = new Map();

  tree.nodes.forEach((node) => {
    const siblings = nodesByParent.get(node.parentId) || [];
    siblings.push(node);
    nodesByParent.set(node.parentId, siblings);
  });

  nodesByParent.forEach((nodes) => {
    nodes.sort((a, b) => a.order - b.order || a.createdAt.localeCompare(b.createdAt));
  });

  const root = levels[0]?.[0];
  container.innerHTML = root
    ? `<div class="tree-visual">${renderBranch(root, nodesByParent, selectedNodeId)}</div>`
    : "<p class=\"empty-state\">Cây này chưa có root node hợp lệ.</p>";
}

function renderBranch(node, nodesByParent, selectedNodeId) {
  const children = nodesByParent.get(node.id) || [];
  const meta = getNodeMeta(node.type);
  const selectedClass = node.id === selectedNodeId ? " is-selected" : "";
  const draggable = node.type === ROOT_TYPE ? "false" : "true";

  return `
    <div class="branch">
      <article class="node-card ${meta.colorClass}${selectedClass}"
        data-node-id="${escapeHtml(node.id)}"
        draggable="${draggable}"
        tabindex="0">
        <div class="node-card__top">
          <span class="node-icon" aria-hidden="true">${meta.icon}</span>
          <span class="node-type">${meta.label}</span>
        </div>
        <p class="node-question">${escapeHtml(meta.question)}</p>
        <p class="node-content">${escapeHtml(node.content)}</p>
        <div class="node-actions">
          <button class="button button--tiny" data-action="edit-node" data-node-id="${escapeHtml(node.id)}" type="button">Edit</button>
          ${node.type === ROOT_TYPE ? "" : `<button class="button button--tiny button--danger" data-action="delete-node" data-node-id="${escapeHtml(node.id)}" type="button">Delete</button>`}
          <button class="button button--tiny button--primary" data-action="add-child" data-node-id="${escapeHtml(node.id)}" type="button">Add Child</button>
        </div>
      </article>
      ${children.length ? `<div class="children">${children.map((child) => renderBranch(child, nodesByParent, selectedNodeId)).join("")}</div>` : ""}
    </div>
  `;
}

function renderInsight(container, node) {
  if (!node) {
    container.innerHTML = "<p class=\"empty-state\">Chạm vào một node trong cây để xem câu hỏi phản biện.</p>";
    return;
  }

  const questions = getInsightQuestions(node.type);
  container.innerHTML = `
    <div class="insight-node">
      <strong>${escapeHtml(getNodeMeta(node.type).label)}</strong>
      <p>${escapeHtml(node.content)}</p>
    </div>
    <ul class="question-list">
      ${questions.map((question) => `<li>${escapeHtml(question)}</li>`).join("")}
    </ul>
  `;
}

function renderNodeTypeOptions(select) {
  select.innerHTML = Object.entries(NODE_TYPES)
    .map(([value, meta]) => `<option value="${value}">${meta.label} - ${meta.question}</option>`)
    .join("");
}

function renderChecklist(container, items, answers, name) {
  container.innerHTML = items
    .map((item, index) => `
      <label class="check-item">
        <input type="checkbox" name="${name}" value="${index}" ${answers[index] ? "checked" : ""}>
        <span>${escapeHtml(item)}</span>
      </label>
    `)
    .join("");
}

function renderConvictionChecklist(container, answers) {
  renderChecklist(container, CONVICTION_ITEMS, answers, "conviction");
}

function renderTruthChecklist(container, answers) {
  renderChecklist(container, TRUTH_ITEMS, answers, "truth");
}

function updateGauge(element, value) {
  element.style.setProperty("--value", `${value}%`);
}

function updateProgress(element, value) {
  element.style.width = `${value}%`;
}

function downloadFile(filename, content, type = "application/json") {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

window.CognitiveUI = {
  escapeHtml,
  formatDate,
  setActiveView,
  showEditor,
  renderTreeList,
  renderTreeCanvas,
  renderInsight,
  renderNodeTypeOptions,
  renderConvictionChecklist,
  renderTruthChecklist,
  updateGauge,
  updateProgress,
  downloadFile
};
})();
