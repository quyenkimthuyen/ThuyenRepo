(function () {
const Storage = window.CognitiveStorage;
const Tree = window.CognitiveTree;
const Insight = window.CognitiveInsight;
const UI = window.CognitiveUI;

const state = {
  data: Storage.loadData(),
  currentTreeId: null,
  selectedNodeId: null,
  editingNodeId: null,
  pendingParentId: null,
  draggedNodeId: null
};

const QUICK_EXAMPLES = {
  conviction: {
    gentleParenting: {
      text: "Tôi tin rằng không nên dạy con bằng la mắng và trừng phạt khi con phạm lỗi.",
      certainty: 78,
      evidenceFor: "Khi con bị la, con khóc và im lặng. Con có vẻ sợ hơn là hiểu mình cần sửa gì.",
      evidenceAgainst: "Vợ tôi cũng muốn con có kỷ luật. Có thể cô ấy đang mệt và lo rằng nếu không nghiêm thì con sẽ coi thường quy tắc.",
      egoCost: "Nếu tôi sai một phần, tôi sợ mình không còn là người hiểu con nhất hoặc bị xem là quá mềm yếu.",
      changeCondition: "Tôi sẽ điều chỉnh nếu thấy cách bao dung nhưng không có giới hạn khiến con lặp lại lỗi mà không chịu trách nhiệm.",
      balancedThought: "Tôi vẫn tin cần dạy con bằng bao dung, thuyết phục và làm gương, nhưng tôi cần cùng vợ thống nhất giới hạn rõ ràng thay vì chỉ phản đối cách của cô ấy."
    },
    spouseRespect: {
      text: "Tôi tin rằng bạn đời không tôn trọng tôi.",
      certainty: 70,
      evidenceFor: "Người ấy phản bác tôi trước mặt con và nói tôi quá nghiêm khắc.",
      evidenceAgainst: "Người ấy vẫn chăm sóc gia đình và có thể đang phản ứng vì lo cho cảm xúc của con.",
      egoCost: "Tôi sợ mất vai trò trong gia đình và sợ con nghĩ lời tôi không có trọng lượng.",
      changeCondition: "Tôi sẽ đổi cách nhìn nếu người ấy giải thích rằng mục tiêu là bảo vệ con, không phải hạ thấp tôi.",
      balancedThought: "Tôi cảm thấy không được tôn trọng, nhưng cần kiểm tra xem người ấy đang chống lại tôi hay đang bảo vệ một giá trị khác."
    },
    childDiscipline: {
      text: "Tôi tin rằng con phải nghe lời ngay khi cha mẹ nói.",
      certainty: 82,
      evidenceFor: "Khi tôi nhắc, con trì hoãn nhiều lần và tiếp tục làm việc riêng.",
      evidenceAgainst: "Con có thể chưa biết chuyển hoạt động, đang mệt hoặc chưa hiểu hậu quả của việc trì hoãn.",
      egoCost: "Tôi sợ nếu con không nghe ngay thì mình mất quyền làm cha mẹ.",
      changeCondition: "Tôi sẽ đổi ý nếu thấy con hợp tác hơn khi có cảnh báo trước, lựa chọn rõ và hậu quả nhất quán.",
      balancedThought: "Tôi muốn con tôn trọng quy tắc, nhưng nghe lời ngay không phải cách duy nhất để đo sự tôn trọng."
    }
  },
  truth: {
    parentingConflict: {
      situation: "Tôi phản ứng mạnh khi vợ nói tôi quá nuông chiều con.",
      truthValue: "Tôi muốn bảo vệ sự an toàn cảm xúc của con và cách dạy con bằng tôn trọng.",
      selfImage: "Tôi muốn được nhìn nhận là người cha hiểu con, bình tĩnh và đúng đắn hơn.",
      mirrorTest: "Nếu vợ cũng nói rằng chỉ cô ấy hiểu con và phủ nhận tôi, tôi sẽ thấy khó chịu.",
      admitCost: "Tôi phải thừa nhận mình có thể đã góp phần làm vợ thấy đơn độc trong việc giữ kỷ luật.",
      truthAction: "Tôi sẽ hỏi vợ điều cô ấy sợ nhất nếu không phạt con, rồi đề xuất một cách vừa có giới hạn vừa không la mắng."
    },
    apology: {
      situation: "Tôi biết mình đã nóng giận nhưng vẫn thấy khó xin lỗi.",
      truthValue: "Sự thật là tôi đã nói quá lời và làm người kia tổn thương.",
      selfImage: "Tôi muốn giữ hình ảnh mình là người có lý và không yếu thế.",
      mirrorTest: "Nếu người kia sai mà không xin lỗi, tôi sẽ nghĩ họ cố chấp.",
      admitCost: "Tôi sợ mất mặt và sợ lời xin lỗi bị dùng để kết luận rằng tôi sai toàn bộ.",
      truthAction: "Tôi sẽ xin lỗi phần mình nóng giận, đồng thời hẹn lúc bình tĩnh để nói tiếp vấn đề chính."
    },
    beingRight: {
      situation: "Tôi muốn chứng minh rằng cách nhìn của tôi mới đúng.",
      truthValue: "Tôi muốn bảo vệ điều đúng và tránh quyết định gây hại cho gia đình.",
      selfImage: "Tôi muốn được xem là người sáng suốt và có phán đoán tốt.",
      mirrorTest: "Nếu người khác chỉ cố chứng minh họ đúng mà không nghe tôi, tôi sẽ thấy họ không tôn trọng mình.",
      admitCost: "Tôi sẽ phải thừa nhận mình có điểm mù và cần nghe thêm dữ kiện.",
      truthAction: "Tôi sẽ hỏi: 'Có dữ kiện nào khiến mình nên đổi cách nhìn không?' trước khi tiếp tục tranh luận."
    }
  }
};

const els = {
  homeButton: document.getElementById("homeButton"),
  newTreeButton: document.getElementById("newTreeButton"),
  tabs: document.querySelectorAll(".tab"),
  treeList: document.getElementById("treeList"),
  emptyTreeList: document.getElementById("emptyTreeList"),
  exportAllButton: document.getElementById("exportAllButton"),
  importFile: document.getElementById("importFile"),
  backToListButton: document.getElementById("backToListButton"),
  downloadTreeButton: document.getElementById("downloadTreeButton"),
  editorTitle: document.getElementById("editorTitle"),
  editorMeta: document.getElementById("editorMeta"),
  treeCanvas: document.getElementById("treeCanvas"),
  insightContent: document.getElementById("insightContent"),
  treeDialog: document.getElementById("treeDialog"),
  treeForm: document.getElementById("treeForm"),
  treeTitleInput: document.getElementById("treeTitleInput"),
  treeRootInput: document.getElementById("treeRootInput"),
  nodeDialog: document.getElementById("nodeDialog"),
  nodeForm: document.getElementById("nodeForm"),
  nodeDialogTitle: document.getElementById("nodeDialogTitle"),
  nodeTypeField: document.getElementById("nodeTypeField"),
  nodeTypeInput: document.getElementById("nodeTypeInput"),
  nodeContentInput: document.getElementById("nodeContentInput"),
  emotionalStateFields: document.querySelectorAll("[data-healing-field='emotionalState']"),
  emotionalSafetyFeedback: document.getElementById("emotionalSafetyFeedback"),
  healingCheckFields: document.querySelectorAll("[data-healing-check]"),
  healingChoiceFields: document.querySelectorAll("[data-healing-choice]"),
  repairCheckFields: document.querySelectorAll("[data-repair-check]"),
  healingBar: document.getElementById("healingBar"),
  healingScore: document.getElementById("healingScore"),
  healingResultLabel: document.getElementById("healingResultLabel"),
  healingFeedback: document.getElementById("healingFeedback"),
  quizTreeSelect: document.getElementById("quizTreeSelect"),
  quizPathControls: document.getElementById("quizPathControls"),
  quizSelectedText: document.getElementById("quizSelectedText"),
  quizPathTrail: document.getElementById("quizPathTrail"),
  quizChoiceFields: document.querySelectorAll("[data-quiz-choice]"),
  quizBar: document.getElementById("quizBar"),
  quizScore: document.getElementById("quizScore"),
  quizResultLabel: document.getElementById("quizResultLabel"),
  quizFeedback: document.getElementById("quizFeedback"),
  relationshipQuizSourceText: document.getElementById("relationshipQuizSourceText"),
  applyRelationshipNodeButton: document.getElementById("applyRelationshipNodeButton"),
  relationshipFields: document.querySelectorAll("[data-relationship-field]"),
  maturityChoiceFields: document.querySelectorAll("[data-maturity-choice]"),
  maturityCheckFields: document.querySelectorAll("[data-maturity-check]"),
  relationshipBar: document.getElementById("relationshipBar"),
  relationshipScore: document.getElementById("relationshipScore"),
  relationshipResultLabel: document.getElementById("relationshipResultLabel"),
  relationshipFeedback: document.getElementById("relationshipFeedback"),
  convictionQuizSourceText: document.getElementById("convictionQuizSourceText"),
  applyConvictionNodeButton: document.getElementById("applyConvictionNodeButton"),
  convictionFields: document.querySelectorAll("[data-conviction-field]"),
  convictionChoiceFields: document.querySelectorAll("[data-conviction-choice]"),
  certaintyValue: document.getElementById("certaintyValue"),
  convictionChecklist: document.getElementById("convictionChecklist"),
  convictionGauge: document.getElementById("convictionGauge"),
  stubbornGauge: document.getElementById("stubbornGauge"),
  convictionScore: document.getElementById("convictionScore"),
  stubbornScore: document.getElementById("stubbornScore"),
  convictionResultLabel: document.getElementById("convictionResultLabel"),
  convictionFeedback: document.getElementById("convictionFeedback"),
  truthQuizSourceText: document.getElementById("truthQuizSourceText"),
  applyTruthNodeButton: document.getElementById("applyTruthNodeButton"),
  truthFields: document.querySelectorAll("[data-truth-field]"),
  truthChoiceFields: document.querySelectorAll("[data-truth-choice]"),
  truthChecklist: document.getElementById("truthChecklist"),
  truthBar: document.getElementById("truthBar"),
  egoBar: document.getElementById("egoBar"),
  truthScore: document.getElementById("truthScore"),
  egoScore: document.getElementById("egoScore"),
  truthResultLabel: document.getElementById("truthResultLabel"),
  truthFeedback: document.getElementById("truthFeedback")
};

function init() {
  UI.renderNodeTypeOptions(els.nodeTypeInput);
  bindEvents();
  renderAll();
}

function bindEvents() {
  els.newTreeButton.addEventListener("click", () => openDialog(els.treeDialog));
  els.homeButton.addEventListener("click", showTreeList);
  els.backToListButton.addEventListener("click", showTreeList);

  els.tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      state.currentTreeId = null;
      state.selectedNodeId = null;
      UI.setActiveView(tab.dataset.view);
      renderAll();
    });
  });

  document.querySelectorAll("[data-close-dialog]").forEach((button) => {
    button.addEventListener("click", () => button.closest("dialog").close());
  });

  els.treeForm.addEventListener("submit", handleCreateTree);
  els.nodeForm.addEventListener("submit", handleSaveNode);
  els.treeList.addEventListener("click", handleTreeListAction);
  els.treeList.addEventListener("keydown", handleTreeListKeyboard);
  els.treeCanvas.addEventListener("click", handleTreeCanvasClick);
  els.treeCanvas.addEventListener("keydown", handleTreeCanvasKeyboard);
  els.treeCanvas.addEventListener("dragstart", handleDragStart);
  els.treeCanvas.addEventListener("dragover", handleDragOver);
  els.treeCanvas.addEventListener("dragleave", handleDragLeave);
  els.treeCanvas.addEventListener("drop", handleDrop);
  els.treeCanvas.addEventListener("dragend", handleDragEnd);

  els.exportAllButton.addEventListener("click", handleExportAll);
  els.importFile.addEventListener("change", handleImport);
  els.downloadTreeButton.addEventListener("click", handleDownloadTree);

  document.querySelectorAll("[data-fill-example]").forEach((button) => {
    button.addEventListener("click", () => applyQuickExample(button.dataset.fillExample));
  });

  els.quizTreeSelect.addEventListener("change", () => {
    const quiz = state.data.moduleState.quiz;
    quiz.treeId = els.quizTreeSelect.value;
    quiz.path = [];
    persist();
    renderQuizPicker();
    renderQuizSourceSummaries();
    updateModuleScores();
  });

  els.quizPathControls.addEventListener("change", (event) => {
    if (!event.target.matches("[data-quiz-path-step]")) return;
    const step = Number(event.target.dataset.quizPathStep);
    const quiz = state.data.moduleState.quiz;
    quiz.path = [...(quiz.path || []).slice(0, step), event.target.value].filter(Boolean);
    persist();
    renderQuizPathControls();
    renderQuizSourceSummaries();
    updateModuleScores();
  });

  els.quizChoiceFields.forEach((field) => {
    field.addEventListener("change", () => {
      state.data.moduleState.quiz.choices[field.dataset.quizChoice] = field.value;
      persistAndRenderModules();
    });
  });

  els.applyRelationshipNodeButton.addEventListener("click", () => applyQuizResultToModule("relationship"));
  els.applyConvictionNodeButton.addEventListener("click", () => applyQuizResultToModule("conviction"));
  els.applyTruthNodeButton.addEventListener("click", () => applyQuizResultToModule("truth"));

  els.emotionalStateFields.forEach((field) => {
    field.addEventListener("change", () => {
      state.data.moduleState.healing.emotionalState = field.value;
      persistAndRenderModules();
    });
  });

  els.healingCheckFields.forEach((field) => {
    field.addEventListener("change", () => {
      state.data.moduleState.healing.checks[field.dataset.healingCheck] = field.checked;
      persistAndRenderModules();
    });
  });

  els.healingChoiceFields.forEach((field) => {
    field.addEventListener("change", () => {
      state.data.moduleState.healing.boundaries[field.dataset.healingChoice] = field.value;
      persistAndRenderModules();
    });
  });

  els.repairCheckFields.forEach((field) => {
    field.addEventListener("change", () => {
      state.data.moduleState.healing.repair[field.dataset.repairCheck] = field.checked;
      persistAndRenderModules();
    });
  });

  els.relationshipFields.forEach((field) => {
    field.addEventListener("input", () => {
      state.data.moduleState.relationship[field.dataset.relationshipField] = field.value;
      persistAndRenderModules();
    });
  });

  els.maturityChoiceFields.forEach((field) => {
    field.addEventListener("change", () => {
      state.data.moduleState.relationship.choices[field.dataset.maturityChoice] = field.value;
      persistAndRenderModules();
    });
  });

  els.maturityCheckFields.forEach((field) => {
    field.addEventListener("change", () => {
      state.data.moduleState.relationship.checks[field.dataset.maturityCheck] = field.checked;
      persistAndRenderModules();
    });
  });

  els.convictionFields.forEach((field) => {
    field.addEventListener("input", () => {
      state.data.moduleState.conviction[field.dataset.convictionField] = field.value;
      persistAndRenderModules();
    });
  });

  els.convictionChoiceFields.forEach((field) => {
    field.addEventListener("change", () => {
      state.data.moduleState.conviction.choices[field.dataset.convictionChoice] = field.value;
      persistAndRenderModules();
    });
  });

  els.convictionChecklist.addEventListener("change", (event) => {
    if (!event.target.matches("input[type='checkbox']")) return;
    state.data.moduleState.conviction.answers[event.target.value] = event.target.checked;
    persistAndRenderModules();
  });

  els.truthFields.forEach((field) => {
    field.addEventListener("input", () => {
      state.data.moduleState.truth[field.dataset.truthField] = field.value;
      persistAndRenderModules();
    });
  });

  els.truthChoiceFields.forEach((field) => {
    field.addEventListener("change", () => {
      state.data.moduleState.truth.choices[field.dataset.truthChoice] = field.value;
      persistAndRenderModules();
    });
  });

  els.truthChecklist.addEventListener("change", (event) => {
    if (!event.target.matches("input[type='checkbox']")) return;
    state.data.moduleState.truth.answers[event.target.value] = event.target.checked;
    persistAndRenderModules();
  });
}

function applyQuickExample(exampleKey) {
  const [moduleName, exampleName] = exampleKey.split(":");
  const example = QUICK_EXAMPLES[moduleName]?.[exampleName];
  if (!example) return;

  state.data.moduleState[moduleName] = {
    ...state.data.moduleState[moduleName],
    ...example
  };

  persist();
  renderModules();
}

function applyQuizResultToModule(moduleName) {
  const selection = getQuizSelection();
  if (!selection) {
    alert("Hãy chọn một nhánh trong phần Trắc nghiệm từ cây trước.");
    return;
  }

  const draft = buildReflectionDraft(selection.tree, selection.node);
  state.data.moduleState[moduleName] = {
    ...state.data.moduleState[moduleName],
    ...draft[moduleName]
  };

  persist();
  renderModules();
}

function handleCreateTree(event) {
  event.preventDefault();
  const title = els.treeTitleInput.value.trim();
  const rootContent = els.treeRootInput.value.trim();
  if (!title || !rootContent) return;

  const tree = Tree.createTree(title, rootContent);
  state.data.trees.push(tree);
  state.currentTreeId = tree.id;
  state.selectedNodeId = tree.rootId;
  els.treeForm.reset();
  els.treeDialog.close();
  persist();
  renderEditor();
  UI.showEditor();
}

function handleSaveNode(event) {
  event.preventDefault();
  const tree = getCurrentTree();
  const content = els.nodeContentInput.value.trim();
  if (!tree || !content) return;

  if (state.editingNodeId) {
    Tree.updateNode(tree, state.editingNodeId, {
      type: els.nodeTypeInput.value,
      content
    });
    state.selectedNodeId = state.editingNodeId;
  } else {
    const node = Tree.addNode(tree, state.pendingParentId, els.nodeTypeInput.value, content);
    state.selectedNodeId = node.id;
  }

  closeNodeDialog();
  persist();
  renderEditor();
}

function handleTreeListAction(event) {
  const item = event.target.closest("[data-tree-id]");
  if (item) openTree(item.dataset.treeId);
}

function handleTreeListKeyboard(event) {
  if (event.key !== "Enter" && event.key !== " ") return;
  const item = event.target.closest("[data-tree-id]");
  if (!item) return;
  event.preventDefault();
  openTree(item.dataset.treeId);
}

function handleTreeCanvasClick(event) {
  const actionButton = event.target.closest("[data-action]");
  const card = event.target.closest("[data-node-id]");
  const tree = getCurrentTree();
  if (!tree || !card) return;

  const nodeId = card.dataset.nodeId;
  state.selectedNodeId = nodeId;

  if (actionButton) {
    runNodeAction(actionButton.dataset.action, actionButton.dataset.nodeId);
    return;
  }

  renderEditor();
}

function handleTreeCanvasKeyboard(event) {
  if (event.key !== "Enter" && event.key !== " ") return;
  const card = event.target.closest("[data-node-id]");
  if (!card) return;
  event.preventDefault();
  state.selectedNodeId = card.dataset.nodeId;
  renderEditor();
}

function runNodeAction(action, nodeId) {
  const tree = getCurrentTree();
  if (!tree) return;

  if (action === "add-child") {
    openNodeDialog({ parentId: nodeId });
  }

  if (action === "edit-node") {
    const node = tree.nodes.find((item) => item.id === nodeId);
    if (node) openNodeDialog({ node });
  }

  if (action === "delete-node") {
    const node = tree.nodes.find((item) => item.id === nodeId);
    if (!node) return;
    const confirmed = confirm("Xoá node này và toàn bộ node con?");
    if (!confirmed) return;

    Tree.deleteNode(tree, nodeId);
    state.selectedNodeId = tree.rootId;
    persist();
    renderEditor();
  }
}

function handleDragStart(event) {
  const card = event.target.closest("[data-node-id]");
  if (!card || card.getAttribute("draggable") !== "true") return;

  state.draggedNodeId = card.dataset.nodeId;
  card.classList.add("is-dragging");
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", state.draggedNodeId);
}

function handleDragOver(event) {
  const card = event.target.closest("[data-node-id]");
  if (!card || !state.draggedNodeId || card.dataset.nodeId === state.draggedNodeId) return;

  event.preventDefault();
  card.classList.add("is-drop-target");
}

function handleDragLeave(event) {
  const card = event.target.closest("[data-node-id]");
  card?.classList.remove("is-drop-target");
}

function handleDrop(event) {
  const card = event.target.closest("[data-node-id]");
  const tree = getCurrentTree();
  if (!card || !tree || !state.draggedNodeId) return;

  event.preventDefault();
  const moved = Tree.moveNode(tree, state.draggedNodeId, card.dataset.nodeId);
  clearDragClasses();

  if (moved) {
    state.selectedNodeId = state.draggedNodeId;
    persist();
    renderEditor();
  }
}

function handleDragEnd() {
  state.draggedNodeId = null;
  clearDragClasses();
}

function handleExportAll() {
  UI.downloadFile("cognitive-tree-export.json", Storage.exportData(state.data));
}

function handleImport(event) {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = () => {
    try {
      state.data = Storage.importData(reader.result);
      state.currentTreeId = null;
      state.selectedNodeId = null;
      renderAll();
      UI.setActiveView("trees");
    } catch (error) {
      alert("File JSON không hợp lệ.");
      console.error(error);
    } finally {
      event.target.value = "";
    }
  };
  reader.readAsText(file);
}

function handleDownloadTree() {
  const tree = getCurrentTree();
  if (!tree) return;

  const safeTitle = tree.title
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "") || "tree";

  UI.downloadFile(`${safeTitle}.json`, JSON.stringify(tree, null, 2));
}

function openTree(treeId) {
  const tree = state.data.trees.find((item) => item.id === treeId);
  if (!tree) return;

  state.currentTreeId = treeId;
  state.selectedNodeId = tree.rootId;
  renderEditor();
  UI.showEditor();
}

function showTreeList() {
  state.currentTreeId = null;
  state.selectedNodeId = null;
  UI.setActiveView("trees");
  renderAll();
}

function openNodeDialog({ parentId = null, node = null }) {
  state.pendingParentId = parentId;
  state.editingNodeId = node?.id || null;
  els.nodeDialogTitle.textContent = node ? "Sửa node" : "Thêm node con";
  els.nodeTypeField.hidden = node?.type === Tree.ROOT_TYPE;
  els.nodeTypeInput.value = node?.type === Tree.ROOT_TYPE ? "FACT" : node?.type || "FACT";
  els.nodeContentInput.value = node?.content || "";
  openDialog(els.nodeDialog);
  els.nodeContentInput.focus();
}

function closeNodeDialog() {
  state.pendingParentId = null;
  state.editingNodeId = null;
  els.nodeForm.reset();
  els.nodeDialog.close();
}

function openDialog(dialog) {
  if (typeof dialog.showModal === "function") {
    dialog.showModal();
    return;
  }
  dialog.setAttribute("open", "");
}

function renderAll() {
  UI.renderTreeList(els.treeList, els.emptyTreeList, state.data.trees);
  renderModules();
  if (state.currentTreeId) renderEditor();
}

function renderEditor() {
  const tree = getCurrentTree();
  if (!tree) return;

  const selectedNode = tree.nodes.find((node) => node.id === state.selectedNodeId) || tree.nodes.find((node) => node.id === tree.rootId);
  state.selectedNodeId = selectedNode?.id || null;
  els.editorTitle.textContent = tree.title;
  els.editorMeta.textContent = `${tree.relationshipGroup || "Tự tạo"} · Ngày tạo: ${UI.formatDate(tree.createdAt)} · ${Tree.getNodeCount(tree)} node`;
  UI.renderTreeCanvas(els.treeCanvas, tree, state.selectedNodeId);
  UI.renderInsight(els.insightContent, selectedNode);
}

function renderModules() {
  const healing = state.data.moduleState.healing;
  const quiz = state.data.moduleState.quiz;
  const relationship = state.data.moduleState.relationship;
  const conviction = state.data.moduleState.conviction;
  const truth = state.data.moduleState.truth;

  renderQuizPicker();
  renderQuizSourceSummaries();
  els.emotionalStateFields.forEach((field) => {
    field.checked = healing.emotionalState === field.value;
  });
  els.quizChoiceFields.forEach((field) => {
    field.value = quiz.choices?.[field.dataset.quizChoice] || "";
  });
  els.healingCheckFields.forEach((field) => {
    field.checked = Boolean(healing.checks?.[field.dataset.healingCheck]);
  });
  els.healingChoiceFields.forEach((field) => {
    field.value = healing.boundaries?.[field.dataset.healingChoice] || "";
  });
  els.repairCheckFields.forEach((field) => {
    field.checked = Boolean(healing.repair?.[field.dataset.repairCheck]);
  });
  els.relationshipFields.forEach((field) => {
    field.value = relationship[field.dataset.relationshipField] ?? "";
  });
  els.maturityChoiceFields.forEach((field) => {
    field.value = relationship.choices?.[field.dataset.maturityChoice] || "";
  });
  els.maturityCheckFields.forEach((field) => {
    field.checked = Boolean(relationship.checks?.[field.dataset.maturityCheck]);
  });
  els.convictionFields.forEach((field) => {
    field.value = conviction[field.dataset.convictionField] ?? "";
  });
  els.convictionChoiceFields.forEach((field) => {
    field.value = conviction.choices?.[field.dataset.convictionChoice] || "";
  });
  els.certaintyValue.textContent = `${conviction.certainty ?? 50}%`;
  UI.renderConvictionChecklist(els.convictionChecklist, conviction.answers || {});
  els.truthFields.forEach((field) => {
    field.value = truth[field.dataset.truthField] ?? "";
  });
  els.truthChoiceFields.forEach((field) => {
    field.value = truth.choices?.[field.dataset.truthChoice] || "";
  });
  UI.renderTruthChecklist(els.truthChecklist, truth.answers || {});
  updateModuleScores();
}

function renderQuizPicker() {
  const quiz = state.data.moduleState.quiz;
  const treesWithChildren = state.data.trees.filter((tree) => getQuizChildCandidates(tree, tree.rootId).length > 0);
  const selectedTreeId = treesWithChildren.some((tree) => tree.id === quiz.treeId)
    ? quiz.treeId
    : treesWithChildren[0]?.id || "";

  els.quizTreeSelect.innerHTML = "";

  if (!treesWithChildren.length) {
    els.quizTreeSelect.append(new Option("Chưa có tình huống phù hợp", ""));
    els.quizTreeSelect.disabled = true;
    els.quizPathControls.innerHTML = "<p class=\"empty-state\">Chưa có nhánh nào để chọn.</p>";
    updateQuizSelectedNode();
    return;
  }

  els.quizTreeSelect.disabled = false;
  treesWithChildren.forEach((tree) => {
    els.quizTreeSelect.append(new Option(`${tree.relationshipGroup || "Tự tạo"} · ${tree.title}`, tree.id));
  });
  els.quizTreeSelect.value = selectedTreeId;
  quiz.treeId = selectedTreeId;
  renderQuizPathControls();
}

function renderQuizPathControls() {
  const quiz = state.data.moduleState.quiz;
  const tree = state.data.trees.find((item) => item.id === quiz.treeId);
  if (!tree) {
    els.quizPathControls.innerHTML = "<p class=\"empty-state\">Hãy chọn tình huống trước.</p>";
    updateQuizSelectedNode();
    return;
  }

  const validPath = [];
  let parentId = tree.rootId;
  let depth = 0;
  let controlsHtml = "";

  while (true) {
    const children = getQuizChildCandidates(tree, parentId);
    if (!children.length) break;

    const savedNodeId = quiz.path?.[depth] || "";
    const selectedNodeId = children.some((node) => node.id === savedNodeId) ? savedNodeId : "";
    const label = depth === 0 ? "Bước 1 - Chọn nút bắt đầu" : `Bước ${depth + 1} - Chọn nút con tiếp theo`;
    const selectedClass = selectedNodeId ? " is-complete" : "";
    const options = [
      `<option value="">Chọn một nút</option>`,
      ...children.map((node) => {
        const selected = node.id === selectedNodeId ? " selected" : "";
        return `<option value="${UI.escapeHtml(node.id)}"${selected}>${UI.escapeHtml(getSourceNodeOptionText(node))}</option>`;
      })
    ].join("");

    controlsHtml += `
      <label class="field quiz-step-field${selectedClass}">
        <span>
          <b>${label}</b>
          <small>${selectedNodeId ? "Đã chọn, có thể đi tiếp nếu nút này còn con." : "Chọn một nút để app hiện bước tiếp theo."}</small>
        </span>
        <select data-quiz-path-step="${depth}">
          ${options}
        </select>
      </label>
    `;

    if (!selectedNodeId) break;
    validPath.push(selectedNodeId);
    parentId = selectedNodeId;
    depth += 1;
  }

  quiz.path = validPath;
  els.quizPathControls.innerHTML = controlsHtml || "<p class=\"empty-state\">Tình huống này chưa có nút con để đi tiếp.</p>";
  updateQuizSelectedNode();
}

function updateQuizSelectedNode() {
  const quiz = state.data.moduleState.quiz;
  const tree = state.data.trees.find((item) => item.id === quiz.treeId);
  const pathNodes = (quiz.path || [])
    .map((nodeId) => tree?.nodes.find((node) => node.id === nodeId))
    .filter(Boolean);

  if (!tree || !pathNodes.length) {
    els.quizSelectedText.textContent = "Hãy chọn một tình huống rồi đi từng bước trong cây.";
    els.quizPathTrail.innerHTML = "";
    return;
  }

  els.quizSelectedText.textContent = `${tree.title} - bạn đã đi qua ${pathNodes.length} bước.`;
  els.quizPathTrail.innerHTML = pathNodes.map((node, index) => `
    <article class="quiz-path-card">
      <span class="quiz-path-card__step">Bước ${index + 1}</span>
      <strong>${UI.escapeHtml(getSourceNodeLabel(node))}</strong>
      <p>${UI.escapeHtml(node.content)}</p>
    </article>
  `).join("");
}

function renderQuizSourceSummaries() {
  const selection = getQuizSelection();
  const message = selection
    ? `${selection.tree.title} - nút cuối: ${getSourceNodeLabel(selection.node)} · ${selection.node.content}`
    : "Hãy hoàn thành phần Trắc nghiệm từ cây trước, rồi quay lại đây để dùng nhánh đã chọn.";

  [
    els.relationshipQuizSourceText,
    els.convictionQuizSourceText,
    els.truthQuizSourceText
  ].forEach((element) => {
    element.textContent = message;
  });

  const disabled = !selection;
  els.applyRelationshipNodeButton.disabled = disabled;
  els.applyConvictionNodeButton.disabled = disabled;
  els.applyTruthNodeButton.disabled = disabled;
}

function getQuizSelection() {
  const quiz = state.data.moduleState.quiz;
  const tree = state.data.trees.find((item) => item.id === quiz.treeId);
  const path = quiz.path || [];
  const nodeId = path[path.length - 1];
  const node = tree?.nodes.find((item) => item.id === nodeId);
  return tree && node ? { tree, node } : null;
}

function getQuizChildCandidates(tree, parentId) {
  if (!parentId) return [];
  return tree.nodes
    .filter((node) => node.parentId === parentId && node.type !== Tree.ROOT_TYPE)
    .sort((a, b) => a.order - b.order || a.createdAt.localeCompare(b.createdAt));
}

function getSourceNodeLabel(node) {
  const labels = {
    ROOT: "Vấn đề gốc",
    FACT: "Sự kiện",
    INTERPRETATION: "Diễn giải",
    BELIEF: "Niềm tin",
    EMOTION: "Cảm xúc",
    ACTION: "Hành động",
    CONSEQUENCE: "Hậu quả"
  };

  return labels[node.type] || "Node";
}

function getSourceNodeOptionText(node) {
  return `${getSourceNodeLabel(node)} · ${node.content}`;
}

function buildReflectionDraft(tree, targetNode) {
  const root = tree.nodes.find((node) => node.id === tree.rootId);
  const ancestors = getAncestors(tree, targetNode);
  const descendants = getDescendants(tree, targetNode.id);
  const siblings = tree.nodes.filter((node) => node.parentId === targetNode.parentId && node.id !== targetNode.id);
  const contextNodes = uniqueNodes([...ancestors, targetNode, ...descendants]);
  const facts = contextNodes.filter((node) => node.type === "FACT");
  const alternatives = siblings.filter((node) => node.type === "INTERPRETATION" || node.type === "BELIEF");
  const emotions = descendants.filter((node) => node.type === "EMOTION");
  const actions = descendants.filter((node) => node.type === "ACTION");
  const consequences = descendants.filter((node) => node.type === "CONSEQUENCE");
  const firstAlternative = alternatives[0]?.content;
  const firstEmotion = emotions[0]?.content;
  const firstAction = actions[0]?.content;
  const firstConsequence = consequences[0]?.content;

  const evidenceFor = facts.length
    ? `Sự kiện liên quan từ cây tư duy:\n${formatNodeList(facts)}`
    : "Cây này chưa có FACT trực tiếp trong nhánh này. Hãy thêm sự kiện quan sát được trước khi kết luận.";

  const evidenceAgainst = [
    alternatives.length ? `Cách hiểu/niềm tin khác trong cùng tình huống:\n${formatNodeList(alternatives)}` : "",
    consequences.length ? `Hậu quả cần cân nhắc:\n${formatNodeList(consequences)}` : ""
  ].filter(Boolean).join("\n\n") || "Chưa thấy node phản chứng rõ. Hãy thử thêm một Interpretation khác: người kia có thể đang nghĩ gì?";

  const egoCost = emotions.length
    ? `Cảm xúc liên quan:\n${formatNodeList(emotions)}\n\nNếu phải đổi ý, tôi cần xem mình đang sợ mất vai trò, quyền kiểm soát hay cảm giác mình đúng ở điểm nào.`
    : "Tôi cần kiểm tra: nếu quan điểm này không đúng hoàn toàn, tôi sợ mất điều gì?";

  const balancedThought = firstAlternative
    ? `Tôi đang nghiêng về: "${targetNode.content}". Nhưng cũng có khả năng: "${firstAlternative}". Tôi cần dựa thêm vào sự kiện và hậu quả thay vì chỉ bảo vệ kết luận ban đầu.`
    : `Tôi đang nghiêng về: "${targetNode.content}". Tôi có thể giữ giá trị của mình, nhưng cần tìm thêm sự kiện và một cách giải thích khác trước khi kết luận chắc chắn.`;

  return {
    relationship: {
      situation: `${tree.title}${root ? `\nRoot Problem: ${root.content}` : ""}\nĐiểm tôi đang bám vào: ${targetNode.content}`,
      myView: targetNode.type === "BELIEF" ? `Tôi đang tin rằng: ${targetNode.content}` : `Tôi đang diễn giải rằng: ${targetNode.content}`,
      myNeed: firstEmotion
        ? `Cảm xúc trong nhánh này: ${firstEmotion}\nNhu cầu có thể đứng sau: được tôn trọng, an toàn, lắng nghe, công nhận hoặc có quyền ảnh hưởng.`
        : "Tôi cần gọi tên nhu cầu phía sau cảm xúc: được tôn trọng, an toàn, lắng nghe, công nhận hay công bằng?",
      otherView: firstAlternative
        ? `Đối phương có thể nhìn khác: ${firstAlternative}`
        : "Nếu đối phương không xấu, họ có thể đang hiểu tình huống này theo cách nào khác?",
      otherNeed: "Đối phương có thể cũng đang cần được hiểu, được tôn trọng, được yên tâm hoặc được tham gia vào quyết định.",
      conflictLoop: [
        `Tôi nghĩ: ${targetNode.content}`,
        firstEmotion ? `Tôi cảm thấy: ${firstEmotion}` : "",
        firstAction ? `Tôi phản ứng: ${firstAction}` : "",
        firstConsequence ? `Hậu quả: ${firstConsequence}` : "",
        "Hậu quả đó có thể làm niềm tin ban đầu mạnh hơn."
      ].filter(Boolean).join(" -> "),
      myResponsibility: "Phần tôi có thể xem lại: giọng nói, cách kết luận ý định của người kia, cách ngắt lời, im lặng, áp đặt hoặc phản ứng khi đang nóng.",
      needStatement: `Khi chuyện này xảy ra, tôi cảm thấy ..., vì tôi cần ..., tôi mong chúng ta ...`,
      commitment: "Lần tới tôi sẽ dừng lại trước khi kết luận, hỏi thêm một câu để hiểu người kia và nói nhu cầu của mình thay vì trách móc.",
      choices: {
        fact: "mature",
        interpretation: firstAlternative ? "aware" : "mature",
        belief: "aware",
        emotion: firstEmotion ? "aware" : "",
        action: firstAction ? "mature" : "",
        consequence: firstConsequence ? "aware" : ""
      }
    },
    conviction: {
      text: targetNode.type === "BELIEF" ? targetNode.content : `Tôi đang diễn giải rằng: ${targetNode.content}`,
      certainty: 70,
      evidenceFor,
      evidenceAgainst,
      egoCost,
      changeCondition: "Tôi sẽ điều chỉnh quan điểm nếu có sự kiện mới, phản hồi đáng tin cậy, hoặc hậu quả thực tế cho thấy cách hiểu hiện tại đang làm vấn đề tệ hơn.",
      balancedThought,
      choices: {
        evidence: facts.length ? "mature" : "aware",
        counterEvidence: alternatives.length ? "mature" : "aware",
        flexibility: "aware",
        egoAwareness: firstEmotion ? "aware" : "",
        respect: "mature"
      }
    },
    truth: {
      situation: `${tree.title}${root ? `\nRoot Problem: ${root.content}` : ""}\nĐiểm đang xét: ${targetNode.content}`,
      truthValue: `Giá trị/sự thật có thể đang được bảo vệ: ${targetNode.content}\nHãy viết lại thành giá trị cụ thể như an toàn, tôn trọng, trách nhiệm, công bằng hoặc tình thương.`,
      selfImage: emotions.length
        ? `Cảm xúc trong nhánh này:\n${formatNodeList(emotions)}\n\nTôi cần kiểm tra mình đang muốn được nhìn nhận là người đúng, người tốt, người có quyền hay người hiểu chuyện.`
        : "Tôi cần kiểm tra hình ảnh bản thân nào đang bị đe doạ khi người khác không đồng ý với mình.",
      mirrorTest: `Nếu người kia cũng bám vào câu "${targetNode.content}" với cùng cách phản ứng của tôi, tôi có thấy công bằng và chấp nhận được không?`,
      admitCost: firstAlternative
        ? `Tôi có thể phải thừa nhận rằng góc nhìn "${firstAlternative}" cũng có một phần hợp lý. Cái giá là tôi không còn giữ được cảm giác mình đúng tuyệt đối.`
        : "Nếu thừa nhận mình sai một phần, tôi có thể mất mặt, mất quyền kiểm soát hoặc phải xin lỗi phần mình chưa khéo.",
      truthAction: actions.length
        ? `Hành động trong nhánh này:\n${formatNodeList(actions)}\n\nBước theo sự thật: chọn một hành động làm dữ kiện rõ hơn, ví dụ hỏi thêm, xác nhận lại, xin lỗi phần mình nóng giận hoặc đề nghị cùng thử một cách khác.`
        : "Bước theo sự thật: hỏi thêm một câu để hiểu người kia, hoặc thừa nhận một điểm hợp lý trước khi tiếp tục bảo vệ quan điểm.",
      choices: {
        value: "aware",
        selfImage: firstEmotion ? "aware" : "",
        mirror: alternatives.length ? "aware" : "",
        humility: alternatives.length ? "aware" : "",
        truthAction: actions.length ? "aware" : ""
      }
    }
  };
}

function getAncestors(tree, node) {
  const ancestors = [];
  let current = node;

  while (current?.parentId) {
    current = tree.nodes.find((item) => item.id === current.parentId);
    if (current) ancestors.unshift(current);
  }

  return ancestors;
}

function getDescendants(tree, nodeId) {
  const descendants = [];
  const queue = tree.nodes.filter((node) => node.parentId === nodeId);

  while (queue.length) {
    const current = queue.shift();
    descendants.push(current);
    queue.push(...tree.nodes.filter((node) => node.parentId === current.id));
  }

  return descendants;
}

function uniqueNodes(nodes) {
  return Array.from(new Map(nodes.map((node) => [node.id, node])).values());
}

function formatNodeList(nodes) {
  return nodes.map((node) => `- ${node.content}`).join("\n");
}

function persistAndRenderModules() {
  persist();
  updateModuleScores();
}

function calculateQuizScore(quizState = {}) {
  const choiceScores = {
    reactive: 0,
    aware: 0.55,
    mature: 1
  };
  const choiceKeys = ["fact", "otherView", "emotion", "action", "repair"];
  const answeredCount = choiceKeys.filter((key) => quizState.choices?.[key]).length;
  const scoreTotal = choiceKeys.reduce((sum, key) => {
    return sum + (choiceScores[quizState.choices?.[key]] ?? 0);
  }, 0);
  const score = Math.round((scoreTotal / choiceKeys.length) * 100);

  if (!quizState.path?.length || answeredCount === 0) {
    return {
      score: 0,
      label: "Chưa bắt đầu",
      feedback: "Hãy chọn một nút con trong cây rồi trả lời vài câu trắc nghiệm để nhìn lại chính mình."
    };
  }

  if (answeredCount < choiceKeys.length) {
    return {
      score,
      label: "Đang trả lời",
      feedback: "Bạn đã bắt đầu soi lại nhánh này. Hãy trả lời hết các câu để kết quả rõ hơn."
    };
  }

  if (score >= 75) {
    return {
      score,
      label: "Đang nhìn lại chính mình khá tốt",
      feedback: "Bạn đã biết nhìn chuyện thật, thử hiểu người kia, để ý cảm xúc và chọn một việc có thể sửa."
    };
  }

  if (score >= 45) {
    return {
      score,
      label: "Đang bắt đầu nhìn lại",
      feedback: "Bạn đã thấy một phần cách mình nghĩ và phản ứng. Hãy xem lại câu nào còn nghiêng về cảm xúc hoặc muốn thắng."
    };
  }

  return {
    score,
    label: "Còn phản ứng nhanh",
    feedback: "Nhánh này có thể đang bị cảm xúc kéo đi. Hãy quay lại xem: chuyện thật là gì, mình đang nghĩ thêm gì, và có thể làm gì nhẹ hơn?"
  };
}

function updateModuleScores() {
  const quizScores = calculateQuizScore(state.data.moduleState.quiz);
  UI.updateProgress(els.quizBar, quizScores.score);
  els.quizScore.textContent = `${quizScores.score}%`;
  els.quizResultLabel.textContent = quizScores.label;
  els.quizFeedback.textContent = quizScores.feedback;

  const healingScores = calculateHealingScore(state.data.moduleState.healing);
  UI.updateProgress(els.healingBar, healingScores.score);
  els.healingScore.textContent = `${healingScores.score}%`;
  els.healingResultLabel.textContent = healingScores.label;
  els.healingFeedback.textContent = healingScores.feedback;
  els.emotionalSafetyFeedback.textContent = healingScores.safetyPrompt;

  const relationshipScores = calculateRelationshipScore(state.data.moduleState.relationship);
  UI.updateProgress(els.relationshipBar, relationshipScores.score);
  els.relationshipScore.textContent = `${relationshipScores.score}%`;
  els.relationshipResultLabel.textContent = relationshipScores.label;
  els.relationshipFeedback.textContent = relationshipScores.feedback;

  const convictionState = state.data.moduleState.conviction;
  const convictionScores = Insight.calculateConvictionScore(convictionState.answers || {}, convictionState);
  UI.updateGauge(els.convictionGauge, convictionScores.conviction);
  UI.updateGauge(els.stubbornGauge, convictionScores.stubborn);
  els.convictionScore.textContent = `${convictionScores.conviction}%`;
  els.stubbornScore.textContent = `${convictionScores.stubborn}%`;
  els.certaintyValue.textContent = `${convictionState.certainty ?? 50}%`;
  els.convictionResultLabel.textContent = getConvictionLabel(convictionScores.conviction, Number(convictionState.certainty ?? 50));
  els.convictionFeedback.textContent = convictionScores.feedback;

  const truthState = state.data.moduleState.truth;
  const truthScores = Insight.calculateTruthScore(truthState.answers || {}, truthState);
  UI.updateProgress(els.truthBar, truthScores.truth);
  UI.updateProgress(els.egoBar, truthScores.ego);
  els.truthScore.textContent = `${truthScores.truth}%`;
  els.egoScore.textContent = `${truthScores.ego}%`;
  els.truthResultLabel.textContent = getTruthLabel(truthScores.truth);
  els.truthFeedback.textContent = truthScores.feedback;
}

function calculateHealingScore(healingState = {}) {
  const stateScores = {
    calm: 1,
    tense: 0.75,
    angry: 0.25,
    hurt: 0.35,
    notReady: 0.15
  };
  const boundaryScores = {
    low: 0.2,
    medium: 0.6,
    high: 1
  };
  const boundaryKeys = ["empathy", "nonNegotiable", "boundary", "protection"];
  const repairKeys = ["apology", "need", "calmTalk", "reassureChild"];
  const selfBlameRisk = ["selfBlame", "ignoreBoundary", "acceptHarm"].reduce((sum, key) => {
    return sum + (healingState.checks?.[key] ? 1 : 0);
  }, 0);
  const boundaryScore = boundaryKeys.reduce((sum, key) => {
    return sum + (boundaryScores[healingState.boundaries?.[key]] || 0);
  }, 0);
  const repairScore = repairKeys.reduce((sum, key) => {
    return sum + (healingState.repair?.[key] ? 1 : 0);
  }, 0);
  const emotionalScore = stateScores[healingState.emotionalState] ?? 0;
  const score = Math.max(0, Math.min(100, Math.round(
    (emotionalScore * 25) +
    ((boundaryScore / boundaryKeys.length) * 30) +
    ((repairScore / repairKeys.length) * 25) +
    ((1 - Math.min(selfBlameRisk, 3) / 3) * 20)
  )));
  const safetyPrompt = getSafetyPrompt(healingState.emotionalState);

  if (score >= 75) {
    return {
      score,
      label: "Đang có nền an toàn để chữa lành",
      feedback: "Bạn đã chú ý đến cảm xúc, ranh giới và phục hồi kết nối. Hãy tiếp tục chọn một hành động nhỏ, an toàn và cụ thể.",
      safetyPrompt
    };
  }

  if (score >= 45) {
    return {
      score,
      label: "Đang bắt đầu ổn định lại",
      feedback: "Bạn đã có vài yếu tố an toàn. Hãy xem lại ranh giới tối thiểu và đừng biến việc nhìn lại chính mình thành tự trách.",
      safetyPrompt
    };
  }

  return {
    score,
    label: "Cần ưu tiên an toàn cảm xúc",
    feedback: "Tạm thời chưa nên phân tích sâu. Hãy ổn định cảm xúc trước, kiểm tra ranh giới và tìm hỗ trợ nếu có nguy cơ bị tổn hại.",
    safetyPrompt
  };
}

function getSafetyPrompt(emotionalState) {
  if (emotionalState === "angry" || emotionalState === "hurt" || emotionalState === "notReady") {
    return "Gợi ý: dừng 3 phút, thở chậm, không nhắn tin/cãi tiếp lúc này, và quay lại khi bình tĩnh hơn.";
  }

  if (emotionalState === "tense") {
    return "Gợi ý: nói chậm lại, thở vài nhịp và chỉ phân tích khi bạn còn đủ khả năng lắng nghe.";
  }

  if (emotionalState === "calm") {
    return "Bạn có thể tiếp tục phân tích, nhưng vẫn nên giữ sự dịu dàng với chính mình và người kia.";
  }

  return "Hãy chọn trạng thái cảm xúc trước khi phân tích.";
}

function calculateRelationshipScore(relationshipState = {}) {
  const choiceScores = {
    reactive: 0,
    aware: 0.55,
    mature: 1
  };
  const choiceKeys = ["fact", "interpretation", "belief", "emotion", "action", "consequence"];
  const checkKeys = ["separateFact", "otherView", "ownPart", "needNotBlame", "repair"];
  const choiceScore = choiceKeys.reduce((sum, key) => {
    return sum + (choiceScores[relationshipState.choices?.[key]] ?? 0);
  }, 0);
  const checkScore = checkKeys.reduce((sum, key) => {
    return sum + (relationshipState.checks?.[key] ? 1 : 0);
  }, 0);
  const score = Math.round(
    ((choiceScore / choiceKeys.length) * 70) +
    ((checkScore / checkKeys.length) * 30)
  );

  if (score >= 75) {
    return {
      score,
      label: "Ứng xử trưởng thành",
      feedback: "Bạn đã chọn cách phản ứng dựa trên sự kiện, có nhìn góc của đối phương và có cam kết sửa phần mình. Hãy bắt đầu bằng một hành động nhỏ, cụ thể."
    };
  }

  if (score >= 45) {
    return {
      score,
      label: "Đang chuyển từ phản ứng sang trưởng thành",
      feedback: "Bạn đã bắt đầu rời khỏi câu hỏi ai đúng ai sai. Hãy xem lại các tầng còn đang chọn phản ứng bản năng, đặc biệt là cảm xúc, hành động và hậu quả."
    };
  }

  return {
    score,
    label: "Còn thiên về phản ứng ban đầu",
    feedback: "Hãy bắt đầu từ cây tư duy: chọn tình huống, rồi chọn một phản ứng trưởng thành hơn ở tầng FACT, INTERPRETATION và ACTION."
  };
}

function getConvictionLabel(conviction, certainty) {
  if (conviction >= 75) return "Kiên định có tự phản biện";
  if (certainty >= 80 && conviction < 55) return "Dễ nghiêng sang cố chấp";
  if (conviction >= 45) return "Đang kiểm tra lại";
  return "Phản ứng ban đầu";
}

function getTruthLabel(truth) {
  if (truth >= 75) return "Đang ưu tiên sự thật";
  if (truth >= 45) return "Đang tách sự thật khỏi cái tôi";
  return "Cái tôi còn chi phối mạnh";
}

function persist() {
  Storage.saveData(state.data);
}

function getCurrentTree() {
  return state.data.trees.find((tree) => tree.id === state.currentTreeId);
}

function clearDragClasses() {
  document.querySelectorAll(".is-dragging, .is-drop-target").forEach((element) => {
    element.classList.remove("is-dragging", "is-drop-target");
  });
}

init();
})();
