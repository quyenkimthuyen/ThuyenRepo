(function () {
const ROOT_TYPE = "ROOT";

const NODE_TYPES = {
  FACT: {
    label: "Fact",
    icon: "●",
    question: "Điều gì thực sự xảy ra?",
    colorClass: "node--fact"
  },
  INTERPRETATION: {
    label: "Interpretation",
    icon: "◆",
    question: "Tôi đang diễn giải điều này như thế nào?",
    colorClass: "node--interpretation"
  },
  BELIEF: {
    label: "Belief",
    icon: "■",
    question: "Tôi đang tin điều gì?",
    colorClass: "node--belief"
  },
  EMOTION: {
    label: "Emotion",
    icon: "♥",
    question: "Tôi cảm thấy gì?",
    colorClass: "node--emotion"
  },
  ACTION: {
    label: "Action",
    icon: "➜",
    question: "Tôi đã làm gì?",
    colorClass: "node--action"
  },
  CONSEQUENCE: {
    label: "Consequence",
    icon: "⬟",
    question: "Kết quả là gì?",
    colorClass: "node--consequence"
  }
};

const ROOT_META = {
  label: "Root Problem",
  icon: "◎",
  question: "Vấn đề gốc bạn đang quan sát là gì?",
  colorClass: "node--root"
};

function createId(prefix) {
  if (globalThis.crypto?.randomUUID) {
    return `${prefix}_${globalThis.crypto.randomUUID()}`;
  }
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function createTree(title, rootContent) {
  const now = new Date().toISOString();
  const rootId = createId("node");

  return {
    id: createId("tree"),
    title: title.trim(),
    relationshipGroup: "Tự tạo",
    createdAt: now,
    updatedAt: now,
    rootId,
    nodes: [
      {
        id: rootId,
        parentId: null,
        type: ROOT_TYPE,
        content: rootContent.trim(),
        order: 0,
        createdAt: now
      }
    ]
  };
}

function getNodeMeta(type) {
  return type === ROOT_TYPE ? ROOT_META : NODE_TYPES[type];
}

function addNode(tree, parentId, type, content) {
  const siblings = tree.nodes.filter((node) => node.parentId === parentId);
  const node = {
    id: createId("node"),
    parentId,
    type,
    content: content.trim(),
    order: siblings.length,
    createdAt: new Date().toISOString()
  };

  tree.nodes.push(node);
  touchTree(tree);
  return node;
}

function updateNode(tree, nodeId, updates) {
  const node = tree.nodes.find((item) => item.id === nodeId);
  if (!node) return;

  node.content = updates.content?.trim() || node.content;
  if (node.type !== ROOT_TYPE && updates.type) {
    node.type = updates.type;
  }
  touchTree(tree);
}

function deleteNode(tree, nodeId) {
  if (nodeId === tree.rootId) return;

  const idsToDelete = collectDescendantIds(tree, nodeId);
  idsToDelete.add(nodeId);
  tree.nodes = tree.nodes.filter((node) => !idsToDelete.has(node.id));
  normalizeSiblingOrder(tree);
  touchTree(tree);
}

function moveNode(tree, nodeId, nextParentId) {
  const node = tree.nodes.find((item) => item.id === nodeId);
  if (!node || node.id === tree.rootId || node.id === nextParentId) return false;
  if (collectDescendantIds(tree, nodeId).has(nextParentId)) return false;

  node.parentId = nextParentId;
  node.order = tree.nodes.filter((item) => item.parentId === nextParentId).length;
  normalizeSiblingOrder(tree);
  touchTree(tree);
  return true;
}

function buildTreeLevels(tree) {
  const byParent = new Map();
  tree.nodes.forEach((node) => {
    const list = byParent.get(node.parentId) || [];
    list.push(node);
    byParent.set(node.parentId, list);
  });

  byParent.forEach((list) => {
    list.sort((a, b) => a.order - b.order || a.createdAt.localeCompare(b.createdAt));
  });

  const levels = [];
  const root = tree.nodes.find((node) => node.id === tree.rootId);
  if (!root) return levels;

  let currentLevel = [root];
  while (currentLevel.length) {
    levels.push(currentLevel);
    currentLevel = currentLevel.flatMap((node) => byParent.get(node.id) || []);
  }

  return levels;
}

function getNodeCount(tree) {
  return tree.nodes.length;
}

function collectDescendantIds(tree, nodeId) {
  const result = new Set();
  const queue = tree.nodes.filter((node) => node.parentId === nodeId);

  while (queue.length) {
    const current = queue.shift();
    result.add(current.id);
    queue.push(...tree.nodes.filter((node) => node.parentId === current.id));
  }

  return result;
}

function normalizeSiblingOrder(tree) {
  const parentIds = new Set(tree.nodes.map((node) => node.parentId));
  parentIds.forEach((parentId) => {
    tree.nodes
      .filter((node) => node.parentId === parentId)
      .sort((a, b) => a.order - b.order || a.createdAt.localeCompare(b.createdAt))
      .forEach((node, index) => {
        node.order = index;
      });
  });
}

function touchTree(tree) {
  tree.updatedAt = new Date().toISOString();
}

window.CognitiveTree = {
  ROOT_TYPE,
  NODE_TYPES,
  ROOT_META,
  createTree,
  getNodeMeta,
  addNode,
  updateNode,
  deleteNode,
  moveNode,
  buildTreeLevels,
  getNodeCount
};
})();
