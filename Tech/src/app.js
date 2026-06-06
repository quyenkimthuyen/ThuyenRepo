const data = window.TechKnowledgeData;

const state = {
  selectedNodeId: "information-technology",
  expanded: new Set(["information-technology", "software-development", "artificial-intelligence", "data"]),
  query: "",
  difficulty: "all",
  productId: data.productTemplates[0].id,
  careerId: data.careerMaps[0].id,
  roadmapId: data.roadmaps[0].id,
};

const elements = {
  searchInput: document.querySelector("#searchInput"),
  knowledgeTree: document.querySelector("#knowledgeTree"),
  mindmapView: document.querySelector("#mindmapView"),
  detailTitle: document.querySelector("#detailTitle"),
  difficultyBadge: document.querySelector("#difficultyBadge"),
  detailContent: document.querySelector("#detailContent"),
  nodeCount: document.querySelector("#nodeCount"),
  resetViewButton: document.querySelector("#resetViewButton"),
  systemMap: document.querySelector("#systemMap"),
  productSelect: document.querySelector("#productSelect"),
  productMap: document.querySelector("#productMap"),
  careerSelect: document.querySelector("#careerSelect"),
  careerMap: document.querySelector("#careerMap"),
  roadmapSelect: document.querySelector("#roadmapSelect"),
  roadmapMap: document.querySelector("#roadmapMap"),
  askTutorButton: document.querySelector("#askTutorButton"),
  tutorAnswer: document.querySelector("#tutorAnswer"),
};

function flattenTree(root, parentId = null, depth = 0) {
  const current = { ...root, parentId, depth };
  const children = root.children || [];
  return [current, ...children.flatMap((child) => flattenTree(child, root.id, depth + 1))];
}

const flatNodes = flattenTree(data.knowledgeTree);
const nodeMap = new Map(flatNodes.map((node) => [node.id, node]));

function getNode(id) {
  return nodeMap.get(id) || data.knowledgeTree;
}

function normalize(text) {
  return String(text || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function listText(items) {
  return (items || []).join(" ");
}

function nodeMatches(node) {
  const matchesDifficulty = state.difficulty === "all" || node.difficulty === state.difficulty;
  if (!matchesDifficulty) return false;

  if (!state.query) return true;
  const haystack = normalize(
    [
      node.title,
      node.category,
      node.simple,
      listText(node.solves),
      listText(node.examples),
      listText(node.careers),
      listText(node.keywords),
      listText(node.misconceptions),
      listText(node.askAi),
      listText(node.nextSteps),
    ].join(" "),
  );
  return haystack.includes(normalize(state.query));
}

function subtreeMatches(node) {
  return nodeMatches(node) || (node.children || []).some(subtreeMatches);
}

function countNodes(root) {
  return flattenTree(root).length;
}

function createButton(className, text, attributes = {}) {
  const button = document.createElement("button");
  button.className = className;
  button.textContent = text;
  Object.entries(attributes).forEach(([key, value]) => button.setAttribute(key, value));
  return button;
}

function renderTreeNode(node, container, depth = 0) {
  if (!subtreeMatches(node)) return;

  const row = document.createElement("div");
  row.className = `tree-row ${state.selectedNodeId === node.id ? "selected" : ""}`;
  row.style.setProperty("--depth", depth);

  const hasChildren = (node.children || []).length > 0;
  const toggle = createButton("tree-toggle", hasChildren ? (state.expanded.has(node.id) ? "−" : "+") : "•", {
    "aria-label": hasChildren ? `Mở hoặc đóng ${node.title}` : node.title,
  });
  toggle.disabled = !hasChildren;
  toggle.addEventListener("click", (event) => {
    event.stopPropagation();
    if (state.expanded.has(node.id)) {
      state.expanded.delete(node.id);
    } else {
      state.expanded.add(node.id);
    }
    renderAll();
  });

  const label = createButton("tree-label", node.title);
  label.addEventListener("click", () => selectNode(node.id));

  const meta = document.createElement("span");
  meta.className = "tree-meta";
  meta.textContent = data.difficulty[node.difficulty].stars;

  row.append(toggle, label, meta);
  container.appendChild(row);

  if (hasChildren && state.expanded.has(node.id)) {
    node.children.forEach((child) => renderTreeNode(child, container, depth + 1));
  }
}

function renderTree() {
  elements.knowledgeTree.innerHTML = "";
  renderTreeNode(data.knowledgeTree, elements.knowledgeTree);

  if (!elements.knowledgeTree.children.length) {
    elements.knowledgeTree.innerHTML = `<div class="empty-state small">Không tìm thấy node phù hợp.</div>`;
  }
}

function renderMindmap() {
  const selected = getNode(state.selectedNodeId);
  const children = selected.children || [];
  const parent = selected.parentId ? getNode(selected.parentId) : null;

  const renderMapNode = (item) => `
    <button class="map-node ${item.type}" data-node-id="${item.node.id}">
      <span>${item.label}</span>
      <strong>${item.node.title}</strong>
      <small>${item.node.category}</small>
    </button>
  `;

  elements.mindmapView.innerHTML = `
    ${
      parent
        ? `<div class="mindmap-row parent-row">${renderMapNode({ type: "parent", label: "Node cha", node: parent })}</div>
           <div class="map-connector">↓</div>`
        : ""
    }
    <div class="mindmap-row current-row">
      ${renderMapNode({ type: "current", label: "Đang xem", node: selected })}
    </div>
    ${
      children.length
        ? `<div class="map-connector">↓</div>
           <div class="mindmap-row children-row">
             ${children.map((child) => renderMapNode({ type: "child", label: "Node con", node: child })).join("")}
           </div>`
        : '<div class="empty-state small">Node này chưa có nhánh con.</div>'
    }
  `;

  elements.mindmapView.querySelectorAll("[data-node-id]").forEach((button) => {
    button.addEventListener("click", () => selectNode(button.dataset.nodeId));
  });
}

function renderList(title, items) {
  if (!items || !items.length) return "";
  return `
    <section class="detail-section">
      <h4>${title}</h4>
      <ul>${items.map((item) => `<li>${item}</li>`).join("")}</ul>
    </section>
  `;
}

function renderDetail() {
  const selected = getNode(state.selectedNodeId);
  const difficulty = data.difficulty[selected.difficulty];

  elements.detailTitle.textContent = selected.title;
  elements.difficultyBadge.textContent = `${difficulty.stars} ${difficulty.label}`;
  elements.difficultyBadge.dataset.level = selected.difficulty;

  elements.detailContent.className = "detail-content";
  elements.detailContent.innerHTML = `
    <section class="detail-section intro">
      <h4>Khái niệm đơn giản</h4>
      <p>${selected.simple}</p>
    </section>
    ${renderList("Vấn đề nó giải quyết", selected.solves)}
    ${renderList("Khi nào nên dùng", selected.useWhen)}
    ${renderList("Không nên dùng khi", selected.avoidWhen)}
    ${renderList("Ví dụ thực tế", selected.examples)}
    <section class="detail-section">
      <h4>Mối quan hệ với công nghệ khác</h4>
      <div class="relation-line">${(selected.relations || []).map((item) => `<span>${item}</span>`).join("<b>→</b>")}</div>
    </section>
    ${renderList("Giá trị nghề nghiệp", selected.careers)}
    ${renderList("Hiểu lầm thường gặp", selected.misconceptions)}
    ${renderList("Câu hỏi nên hỏi AI", selected.askAi)}
    ${renderList("Bước học tiếp theo", selected.nextSteps)}
    <section class="detail-section trend">
      <h4>Xu hướng tương lai</h4>
      <p>${selected.trend}</p>
    </section>
  `;
}

function selectNode(id) {
  state.selectedNodeId = id;
  let parentId = getNode(id).parentId;
  while (parentId) {
    state.expanded.add(parentId);
    parentId = getNode(parentId).parentId;
  }
  renderAll();
}

function renderFlowMap(container, steps, options = {}) {
  container.innerHTML = steps
    .map((step, index) => {
      const title = typeof step === "string" ? step : step.title;
      const body = typeof step === "string" ? "" : step.role || step.description || "";
      const tech = typeof step === "string" ? [] : step.technologies || [];
      const example = typeof step === "string" ? "" : step.example || "";
      const isLast = index === steps.length - 1;

      return `
        <article class="flow-step ${options.compact ? "compact" : ""}">
          <span class="step-index">${index + 1}</span>
          <div>
            <h4>${title}</h4>
            ${body ? `<p>${body}</p>` : ""}
            ${tech.length ? `<div class="mini-tags">${tech.map((item) => `<span>${item}</span>`).join("")}</div>` : ""}
            ${example ? `<small>${example}</small>` : ""}
          </div>
        </article>
        ${!isLast ? '<div class="flow-arrow">↓</div>' : ""}
      `;
    })
    .join("");
}

function renderSystemMap() {
  renderFlowMap(elements.systemMap, data.systemMap);
}

function fillSelect(select, items, selectedId) {
  select.innerHTML = items.map((item) => `<option value="${item.id}">${item.title}</option>`).join("");
  select.value = selectedId;
}

function renderProductMap() {
  const template = data.productTemplates.find((item) => item.id === state.productId) || data.productTemplates[0];
  renderFlowMap(
    elements.productMap,
    [
      { title: template.title, role: template.description, technologies: ["Product Goal"] },
      ...template.steps.map((step) => ({ title: step, role: describeProductStep(step) })),
    ],
    { compact: true },
  );
}

function describeProductStep(step) {
  const dictionary = {
    Frontend: "Màn hình để người dùng thao tác.",
    Backend: "Nơi xử lý nghiệp vụ và kết nối dịch vụ.",
    Database: "Nơi lưu dữ liệu bền vững.",
    "AI Speech": "AI nhận diện và đánh giá giọng nói.",
    Payment: "Thu phí, subscription hoặc đơn hàng.",
    Analytics: "Đo hành vi và hiệu quả sản phẩm.",
    Cloud: "Hạ tầng triển khai và mở rộng.",
    Monitoring: "Theo dõi lỗi, tốc độ và độ ổn định.",
    "Mobile App": "Ứng dụng cài trên iOS/Android, tối ưu trải nghiệm cá nhân và thông báo.",
    "API Gateway": "Cửa vào kiểm soát request, bảo mật, logging và rate limit.",
    "Notification Service": "Gửi email, SMS, push notification hoặc in-app message.",
    "Search": "Giúp người dùng tìm nội dung, sản phẩm hoặc tài liệu nhanh.",
    "CMS": "Nơi team nội dung quản lý bài viết, bài học hoặc landing page.",
    "CRM": "Quản lý khách hàng, lead, lịch sử chăm sóc và pipeline bán hàng.",
    "ERP": "Quản lý vận hành như kho, kế toán, mua hàng và nhân sự.",
    "Workflow Engine": "Điều phối các bước phê duyệt, tác vụ và tự động hóa nội bộ.",
    "Data Warehouse": "Kho dữ liệu phân tích gom từ nhiều nguồn để làm BI và AI.",
    "Vector Database": "Lưu embedding để tìm kiếm ngữ nghĩa cho RAG và AI search.",
    "Audit Log": "Ghi lại ai làm gì, khi nào, phục vụ bảo mật và truy vết.",
    "Human Approval": "Bước con người duyệt trước khi AI thực hiện hành động rủi ro.",
    "Recommendation AI": "Gợi ý nội dung hoặc sản phẩm phù hợp từng người dùng.",
    "Inventory": "Quản lý tồn kho, biến động hàng hóa và đồng bộ đơn hàng.",
    "Billing": "Tính phí định kỳ, hóa đơn, gói dịch vụ và trạng thái thanh toán.",
    "Admin Dashboard": "Màn hình nội bộ để quản trị dữ liệu, người dùng và vận hành.",
    "DevOps": "Tự động build, deploy, rollback và theo dõi hệ thống.",
    "Knowledge Tree": "Cây tri thức giúp người học nhìn tổng thể các chủ đề và mối quan hệ.",
    "Learning Roadmap": "Lộ trình học theo cấp độ để người học biết nên học gì trước.",
    "AI Tutor": "Trợ lý giải thích, gợi ý câu hỏi và cá nhân hóa cách học.",
    "Progress Tracking": "Theo dõi tiến độ học, điểm yếu và milestone của người học.",
    "Content CMS": "Nơi quản lý nội dung học, node tri thức, bài viết và ví dụ.",
    "Feedback Loop": "Thu thập phản hồi và hành vi để cải thiện nội dung, UX hoặc AI.",
    "Form Builder": "Công cụ tạo biểu mẫu để thu thập dữ liệu và khởi động workflow.",
    "Approval Rules": "Luật duyệt giúp xác định ai cần phê duyệt bước nào trong quy trình.",
    "Integration API": "Kết nối hệ thống nội bộ, SaaS hoặc dịch vụ bên ngoài.",
    Observability: "Theo dõi log, metric, trace, alert và chất lượng vận hành.",
    "Document Ingestion": "Nạp tài liệu từ file, website hoặc hệ thống nội bộ vào pipeline AI.",
    Chunking: "Chia tài liệu thành đoạn nhỏ để embedding và truy xuất hiệu quả hơn.",
    Embedding: "Chuyển văn bản thành vector để tìm kiếm ngữ nghĩa.",
    RAG: "Kết hợp tìm kiếm tài liệu với LLM để trả lời dựa trên dữ liệu riêng.",
    LLM: "Mô hình ngôn ngữ lớn dùng để hiểu, tạo và tóm tắt nội dung.",
    Evaluation: "Đánh giá chất lượng câu trả lời, độ chính xác và mức độ an toàn của AI.",
    "AI Safety": "Guardrail giảm rủi ro hallucination, dữ liệu nhạy cảm và hành động nguy hiểm.",
    "Data Sources": "Các hệ thống nguồn như CRM, ERP, app, file hoặc database vận hành.",
    "ETL/ELT": "Pipeline lấy, biến đổi và nạp dữ liệu vào kho phân tích.",
    "Data Quality": "Kiểm tra độ đúng, đủ, nhất quán và cập nhật của dữ liệu.",
    "Metrics Layer": "Lớp định nghĩa metric chung để các dashboard dùng cùng một cách tính.",
    "Access Control": "Kiểm soát ai được xem, sửa hoặc xuất dữ liệu.",
    Governance: "Quy định sở hữu, chất lượng, bảo mật và vòng đời dữ liệu.",
    Security: "Bảo vệ định danh, dữ liệu, quyền truy cập và bề mặt tấn công.",
    BI: "Báo cáo KPI và insight kinh doanh.",
  };
  return dictionary[step] || "Một thành phần cần có để sản phẩm vận hành đúng mục tiêu.";
}

function renderCareerMap() {
  const career = data.careerMaps.find((item) => item.id === state.careerId) || data.careerMaps[0];
  elements.careerMap.innerHTML = `
    <div class="career-center">${career.center}</div>
    <div class="career-branches">
      ${career.skills.map((skill) => `<button class="branch-node">${skill}</button>`).join("")}
    </div>
  `;
}

function renderRoadmap() {
  const roadmap = data.roadmaps.find((item) => item.id === state.roadmapId) || data.roadmaps[0];
  elements.roadmapMap.innerHTML = roadmap.levels
    .map(
      (level, index) => `
        <article class="roadmap-level">
          <span>Level ${index + 1}</span>
          <h4>${level.title}</h4>
          <div class="mini-tags">${level.items.map((item) => `<span>${item}</span>`).join("")}</div>
        </article>
      `,
    )
    .join("");
}

function renderTutorAnswer() {
  const selected = getNode(state.selectedNodeId);
  elements.tutorAnswer.innerHTML = `
    <div class="tutor-card">
      <p class="eyebrow">AI Tutor mô phỏng</p>
      <h4>${selected.title} là gì?</h4>
      <p><strong>Nói dễ hiểu:</strong> ${selected.simple}</p>
      <p><strong>Ví dụ đời sống:</strong> Hãy tưởng tượng ${selected.title} như một phần trong cửa hàng: nó có nhiệm vụ riêng để cả cửa hàng phục vụ khách tốt hơn.</p>
      <p><strong>Ví dụ doanh nghiệp:</strong> ${selected.examples?.[0] || "Doanh nghiệp dùng nó để giảm thao tác thủ công và kiểm soát quy trình."}</p>
      <p><strong>Trong hệ thống lớn:</strong> ${selected.relations?.join(" → ") || "Nó kết nối với nhiều lớp công nghệ khác để tạo thành một sản phẩm hoàn chỉnh."}</p>
      <p><strong>Nên nhớ:</strong> Dùng khi ${selected.useWhen?.[0]?.toLowerCase() || "nó giải quyết đúng vấn đề"}, và tránh lạm dụng khi ${selected.avoidWhen?.[0]?.toLowerCase() || "bài toán chưa cần đến nó"}.</p>
      ${
        selected.misconceptions?.length
          ? `<p><strong>Đừng nhầm:</strong> ${selected.misconceptions[0]}</p>`
          : ""
      }
      ${
        selected.askAi?.length
          ? `<p><strong>Câu hỏi hay để hỏi AI:</strong> ${selected.askAi[0]}</p>`
          : ""
      }
    </div>
  `;
}

function renderTabs() {
  renderSystemMap();
  renderProductMap();
  renderCareerMap();
  renderRoadmap();
}

function renderAll() {
  renderTree();
  renderMindmap();
  renderDetail();
}

function initEvents() {
  elements.searchInput.addEventListener("input", (event) => {
    state.query = event.target.value.trim();
    if (state.query) {
      flatNodes.forEach((item) => {
        if (subtreeMatches(item)) state.expanded.add(item.id);
      });
    }
    renderTree();
  });

  document.querySelectorAll("[data-difficulty]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-difficulty]").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      state.difficulty = button.dataset.difficulty;
      renderTree();
    });
  });

  document.querySelectorAll("[data-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      const tab = button.dataset.tab;
      document.querySelectorAll("[data-tab]").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.remove("active"));
      button.classList.add("active");
      document.querySelector(`#${tab}Panel`).classList.add("active");
    });
  });

  elements.resetViewButton.addEventListener("click", () => {
    state.query = "";
    state.difficulty = "all";
    state.selectedNodeId = "information-technology";
    state.expanded = new Set(["information-technology", "software-development", "artificial-intelligence", "data"]);
    elements.searchInput.value = "";
    document.querySelectorAll("[data-difficulty]").forEach((item) => {
      item.classList.toggle("active", item.dataset.difficulty === "all");
    });
    renderAll();
  });

  elements.productSelect.addEventListener("change", (event) => {
    state.productId = event.target.value;
    renderProductMap();
  });

  elements.careerSelect.addEventListener("change", (event) => {
    state.careerId = event.target.value;
    renderCareerMap();
  });

  elements.roadmapSelect.addEventListener("change", (event) => {
    state.roadmapId = event.target.value;
    renderRoadmap();
  });

  elements.askTutorButton.addEventListener("click", renderTutorAnswer);
}

function init() {
  elements.nodeCount.textContent = countNodes(data.knowledgeTree);
  fillSelect(elements.productSelect, data.productTemplates, state.productId);
  fillSelect(elements.careerSelect, data.careerMaps, state.careerId);
  fillSelect(elements.roadmapSelect, data.roadmaps, state.roadmapId);
  initEvents();
  renderAll();
  renderTabs();
}

init();
