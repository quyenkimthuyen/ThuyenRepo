/* Ôn Văn vào 10 */

const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

const TYPE_LABELS = {
  paragraph_200: "Đoạn 200 chữ",
  reading: "Đọc hiểu",
  essay_social: "NL xã hội",
  mock_exam: "Thi thử",
};

const CRITERION_LABELS = {
  hinh_thuc: "Hình thức", xac_dinh_de: "Xác định đề", noi_dung: "Nội dung",
  ngon_ngu: "Ngôn ngữ", sang_tao: "Sáng tạo", hieu_de: "Hiểu đề",
  luan_diem: "Luận điểm", bo_cuc: "Bố cục",
};

const TAB_FOR_TYPE = {
  paragraph_200: "paragraph",
  reading: "reading",
  essay_social: "essay",
  mock_exam: "exam",
  weakness: "roadmap",
};

let examData = null;
let timerInterval = null;
let secondsLeft = 7200;
let examStartedAt = null;
let readingQCount = 0;
let provinces = [];
let hcmExams = [];

function getProvince() {
  return "hcm";
}

function setProvince(id) {
  localStorage.setItem("province_id", id);
}

function countWords(text) {
  return text.trim().replace(/[^\w\s\u00C0-\u1EF9]/g, " ").split(/\s+/).filter(Boolean).length;
}

function updateWordMeter(text, metaId, barId, target = 200, min = 150, max = 250) {
  const n = countWords(text);
  const pct = Math.min(100, Math.round((n / target) * 100));
  const meta = $(metaId);
  const bar = $(barId);
  if (!meta || !bar) return;
  if (target === 200) {
    meta.textContent = `${n} / ~${target} từ`;
    meta.className = n >= min && n <= max ? "meta ok" : "meta warn";
  } else {
    meta.textContent = `${n} từ (gợi ý ${min}–${max})`;
    meta.className = n >= min && n <= max ? "meta ok" : "meta warn";
  }
  bar.style.width = `${pct}%`;
  bar.className = `word-bar-fill ${n >= min && n <= max ? "ok" : "warn"}`;
}

function showLoading(msg, sub) {
  $("#loadingMessage").textContent = msg;
  $("#loadingSub").textContent = sub || "";
  $("#loadingOverlay").classList.add("visible");
}
function hideLoading() { $("#loadingOverlay").classList.remove("visible"); }

function showError(msg) {
  const b = $("#errorBox");
  b.textContent = msg;
  b.style.display = "block";
}
function hideError() { $("#errorBox").style.display = "none"; }

async function api(path, opts = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  const text = await res.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { detail: text || res.statusText };
  }
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Lỗi API");
  return data;
}

async function withLoading(fn, msg, sub) {
  showLoading(msg, sub);
  try { return await fn(); } finally { hideLoading(); }
}

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function switchTab(tabId) {
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === tabId));
  $$(".panel").forEach((p) => p.classList.remove("active"));
  $(`#panel-${tabId}`)?.classList.add("active");
  if (tabId === "history") loadHistory();
  if (tabId === "roadmap") loadRoadmap();
}

/* ── Results ── */

function renderResult(data, title = "Kết quả chấm") {
  hideError();
  const total = Number(data.total) || 0;
  const max = Number(data.max_score) || 10;
  const pct = max > 0 ? Math.round((total / max) * 100) : 0;

  $("#resultBox").classList.add("visible");
  $("#resultTitle").textContent = title;
  $("#resultNum").textContent = total;
  $("#resultDen").textContent = `/ ${max}`;
  $("#scoreRing").style.setProperty("--pct", pct);

  const tags = $("#resultTags");
  tags.innerHTML = "";
  if (data.rubric_type) {
    const t = document.createElement("span");
    t.className = "tag";
    t.textContent = TYPE_LABELS[data.rubric_type] || data.rubric_type;
    tags.appendChild(t);
  }
  const pt = document.createElement("span");
  pt.className = "tag";
  pt.textContent = `${pct}%`;
  tags.appendChild(pt);

  const warnEl = $("#resultWarnings");
  const warnings = data.form_check?.warnings || [];
  if (warnings.length) {
    warnEl.style.display = "block";
    warnEl.innerHTML = warnings.map((w) => `<li>${escapeHtml(w)}</li>`).join("");
  } else warnEl.style.display = "none";

  const criteriaEl = $("#resultCriteria");
  criteriaEl.innerHTML = "";
  const addCriterion = (label, score, maxS, note) => {
    const pctBar = maxS > 0 ? (score / maxS) * 100 : 0;
    const row = document.createElement("div");
    row.className = "criterion-row";
    row.innerHTML = `
      <div class="criterion-head"><span>${escapeHtml(label)}</span><span>${score}/${maxS}</span></div>
      <div class="criterion-bar"><div class="criterion-bar-fill" style="width:${pctBar}%"></div></div>
      ${note ? `<div class="criterion-note">${escapeHtml(note)}</div>` : ""}`;
    criteriaEl.appendChild(row);
  };

  if (data.question_scores?.length) {
    for (const q of data.question_scores) {
      addCriterion(`Câu ${q.id}`, q.score, q.max, q.note);
    }
  }
  for (const [key, val] of Object.entries(data.breakdown || {})) {
    addCriterion(CRITERION_LABELS[key] || key, val.score, val.max, val.note);
  }

  // Đáp án khung
  const fwBox = $("#frameworkBox");
  const fwContent = $("#frameworkContent");
  const qs = data.question_scores?.filter((q) => q.framework_answer?.length || q.missing_points?.length) || [];
  if (qs.length) {
    fwBox.style.display = "block";
    fwContent.innerHTML = qs.map((q) => `
      <div class="framework-q">
        <strong>Câu ${escapeHtml(q.id)}</strong>
        ${q.missing_points?.length ? `<p class="meta warn">Thiếu: ${q.missing_points.map(escapeHtml).join("; ")}</p>` : ""}
        ${q.framework_answer?.length ? `<p>Đáp án khung:</p><ul>${q.framework_answer.map((a) => `<li>${escapeHtml(a)}</li>`).join("")}</ul>` : ""}
      </div>`).join("");
  } else fwBox.style.display = "none";

  // Hướng sửa
  const revBox = $("#revisionBox");
  const hints = data.revision_hints || [];
  if (hints.length || data.sample_opening || data.sample_argument) {
    revBox.style.display = "block";
    $("#revisionContent").innerHTML = hints.map((h) => `
      <div class="revision-item">
        <strong>${escapeHtml(h.target || "")}</strong>: ${escapeHtml(h.suggestion || "")}
        ${h.example_sentence ? `<blockquote style="margin:0.35rem 0;padding-left:0.75rem;border-left:3px solid var(--accent)">${escapeHtml(h.example_sentence)}</blockquote>` : ""}
      </div>`).join("");
    let sample = "";
    if (data.sample_opening) sample += `<p><strong>Gợi ý mở bài/đoạn:</strong> ${escapeHtml(data.sample_opening)}</p>`;
    if (data.sample_argument) sample += `<p><strong>Gợi ý luận điểm:</strong> ${escapeHtml(data.sample_argument)}</p>`;
    $("#sampleContent").innerHTML = sample;
  } else revBox.style.display = "none";

  const fill = (id, items) => {
    const el = $(id);
    el.innerHTML = "";
    (items?.length ? items : ["—"]).forEach((t) => {
      const li = document.createElement("li");
      li.textContent = t;
      el.appendChild(li);
    });
  };
  fill("#resultStrengths", data.strengths);
  fill("#resultWeaknesses", data.weaknesses);
  fill("#resultNext", data.next_steps);
  $("#resultBox").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderScoreSheet(data) {
  const sheet = $("#scoreSheet");
  const table = $("#scoreTable");
  if (!data.score_sheet?.length) { sheet.style.display = "none"; return; }
  sheet.style.display = "block";
  table.innerHTML = `
    <tr><th>Phần</th><th>Điểm</th></tr>
    ${data.score_sheet.map((r) => `<tr><td>${escapeHtml(r.section)}</td><td><strong>${r.score}/${r.max}</strong></td></tr>`).join("")}
    <tr><th>Tổng</th><th>${data.total}/${data.max_score}</th></tr>`;
}

/* ── Province ── */

async function initProvinces() {
  const data = await api("/api/provinces");
  provinces = data.provinces || [];
  const sel = $("#provinceSelect");
  const cur = "hcm";
  setProvince(cur);
  sel.innerHTML = provinces.map((p) =>
    `<option value="${p.id}" ${p.id === cur ? "selected" : ""}>${escapeHtml(p.name)}</option>`
  ).join("");
  sel.disabled = true;
  sel.addEventListener("change", () => {
    setProvince("hcm");
    sel.value = "hcm";
    loadExamList();
  });
}

function populateExamSelect(selectId, exams) {
  const sel = $(selectId);
  if (!sel) return;
  if (!exams.length) {
    sel.innerHTML = '<option value="hcm_01">Đề TP.HCM</option>';
    return;
  }
  const prev = sel.value;
  sel.innerHTML = exams.map((e) => `<option value="${e.id}">${escapeHtml(e.title)}</option>`).join("");
  if (prev && exams.some((e) => e.id === prev)) sel.value = prev;
}

async function loadHcmExamOptions() {
  const data = await api("/api/exams?province=hcm");
  hcmExams = data.exams || [];
  ["#p-exam-select", "#r-exam-select", "#e-exam-select", "#exam-select"].forEach((id) =>
    populateExamSelect(id, hcmExams)
  );
  return hcmExams;
}

function selectedExamId(selectId) {
  return $(selectId)?.value || hcmExams[0]?.id || "hcm_01";
}

/* ── Roadmap & weaknesses ── */

async function loadRoadmap() {
  const [roadmap, weak] = await Promise.all([
    api("/api/roadmap"),
    api("/api/weaknesses"),
  ]);

  const wBox = $("#weaknessBox");
  if (weak.top_weaknesses?.length) {
    wBox.innerHTML = `
      <p class="meta">${escapeHtml(weak.recommendation)}</p>
      ${weak.top_weaknesses.map((w) => `
        <div class="weakness-item">
          <strong>${escapeHtml(w.label)}</strong> (${w.count} lần)
          <br>${escapeHtml(w.tip)}
          <br><button type="button" class="btn-link" data-practice="${w.practice_type}">→ Luyện ngay</button>
        </div>`).join("")}`;
    wBox.querySelectorAll("[data-practice]").forEach((btn) => {
      btn.addEventListener("click", () => switchTab(TAB_FOR_TYPE[btn.dataset.practice] || "paragraph"));
    });
  } else {
    wBox.innerHTML = `<p>${escapeHtml(weak.recommendation)}</p>`;
  }

  $("#roadmapWeeks").innerHTML = (roadmap.weeks || []).map((w) => `
    <div class="card week-card">
      <div class="week-num">Tuần ${w.week}</div>
      <h3 class="card-title" style="margin:0.25rem 0">${escapeHtml(w.focus)}</h3>
      <p class="meta">Mục tiêu: ${escapeHtml(w.goal)}</p>
      <ul class="compact">${w.daily_tasks.map((t) => `<li>${escapeHtml(t)}</li>`).join("")}</ul>
      <button type="button" class="btn-link" data-week-practice="${w.practice_type}">Luyện dạng này →</button>
    </div>`).join("");

  $("#roadmapWeeks").querySelectorAll("[data-week-practice]").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(TAB_FOR_TYPE[btn.dataset.weekPractice] || "paragraph"));
  });
}

/* ── Health ── */

async function checkHealth() {
  const badge = $("#apiBadge");
  try {
    const d = await api("/api/health");
    badge.className = d.cursor_api_configured ? "status-badge ok" : "status-badge warn";
    $("#apiStatus").textContent = d.cursor_api_configured ? `Cursor API · ${d.model}` : "Chưa có API key";
  } catch {
    badge.className = "status-badge warn";
    $("#apiStatus").textContent = "Server offline";
  }
}

/* ── Tabs ── */

$("#tabs").addEventListener("click", (e) => {
  const btn = e.target.closest(".tab");
  if (!btn) return;
  switchTab(btn.dataset.tab);
});

/* ── Paragraph ── */

$("#p-answer").addEventListener("input", () =>
  updateWordMeter($("#p-answer").value, "#p-wordMeta", "#p-wordBar"));

async function loadSampleParagraph() {
  const exam = await api(`/api/exams/${selectedExamId("#p-exam-select")}`);
  $("#p-passage").value = exam.part1.literary_passage;
  $("#p-question").value = exam.part1.paragraph.prompt;
}

$("#p-loadSample").addEventListener("click", () => loadSampleParagraph().catch(showError));
$("#p-exam-select").addEventListener("change", () => loadSampleParagraph().catch(showError));
$("#p-clear").addEventListener("click", () => {
  $("#p-answer").value = "";
  updateWordMeter("", "#p-wordMeta", "#p-wordBar");
});

$("#p-gradeBtn").addEventListener("click", async () => {
  const btn = $("#p-gradeBtn");
  btn.disabled = true;
  try {
    const data = await withLoading(() => api("/api/grade/paragraph", {
      method: "POST",
      body: JSON.stringify({
        passage: $("#p-passage").value,
        question: $("#p-question").value,
        answer: $("#p-answer").value,
        province_id: getProvince(),
        target_words: 200,
      }),
    }), "Chấm đoạn văn...");
    renderResult(data, "Đoạn văn ~200 chữ");
  } catch (e) { showError(e.message); }
  finally { btn.disabled = false; }
});

/* ── Reading ── */

function addReadingQuestion(data = {}) {
  readingQCount += 1;
  const id = data.id || `c${readingQCount}`;
  const div = document.createElement("div");
  div.className = "reading-q";
  div.dataset.qid = id;
  div.innerHTML = `
    <div class="reading-q-header">
      <span class="field-label">Câu ${id}</span>
      <button type="button" class="btn-icon rq-remove">×</button>
    </div>
    <label>Điểm tối đa</label>
    <input type="number" class="rq-max" value="${data.max_score ?? 0.5}" step="0.25" min="0.25" style="width:5rem;margin-bottom:0.5rem">
    <label>Câu hỏi</label>
    <textarea class="rq-prompt" rows="2">${data.prompt || ""}</textarea>
    <label>Trả lời</label>
    <textarea class="rq-answer" rows="3">${data.answer || ""}</textarea>`;
  div.querySelector(".rq-remove").addEventListener("click", () => div.remove());
  $("#r-questions").appendChild(div);
}

$("#r-addQ").addEventListener("click", () => addReadingQuestion());

async function loadSampleReading() {
  const exam = await api(`/api/exams/${selectedExamId("#r-exam-select")}`);
  const part = $("#r-part-select").value === "part2" ? exam.part2 : exam.part1;
  $("#r-passage").value = part.info_passage || part.literary_passage || "";
  $("#r-questions").innerHTML = "";
  readingQCount = 0;
  part.reading_questions.forEach((q) => addReadingQuestion(q));
}

$("#r-exam-select").addEventListener("change", () => loadSampleReading().catch(showError));
$("#r-part-select").addEventListener("change", () => loadSampleReading().catch(showError));
$("#r-loadSample").addEventListener("click", () => loadSampleReading().catch(showError));

$("#r-gradeBtn").addEventListener("click", async () => {
  const questions = [...$$("#r-questions .reading-q")].map((el) => ({
    id: el.dataset.qid,
    prompt: el.querySelector(".rq-prompt").value,
    max_score: parseFloat(el.querySelector(".rq-max").value) || 0.5,
    answer: el.querySelector(".rq-answer").value,
  }));
  const btn = $("#r-gradeBtn");
  btn.disabled = true;
  try {
    const data = await withLoading(() => api("/api/grade/reading", {
      method: "POST",
      body: JSON.stringify({ passage: $("#r-passage").value, questions, province_id: getProvince() }),
    }), "Chấm đọc hiểu...");
    renderResult(data, "Đọc hiểu");
  } catch (e) { showError(e.message); }
  finally { btn.disabled = false; }
});

/* ── Essay ── */

$("#e-answer").addEventListener("input", () =>
  updateWordMeter($("#e-answer").value, "#e-wordMeta", "#e-wordBar", 450, 350, 600));

async function loadSampleEssay() {
  const exam = await api(`/api/exams/${selectedExamId("#e-exam-select")}`);
  $("#e-passage").value = exam.part2.info_passage;
  $("#e-question").value = exam.part2.essay.prompt;
}

$("#e-loadSample").addEventListener("click", () => loadSampleEssay().catch(showError));
$("#e-exam-select").addEventListener("change", () => loadSampleEssay().catch(showError));

$("#e-clear").addEventListener("click", () => {
  $("#e-answer").value = "";
  updateWordMeter("", "#e-wordMeta", "#e-wordBar", 450, 350, 600);
});

$("#e-gradeBtn").addEventListener("click", async () => {
  const btn = $("#e-gradeBtn");
  btn.disabled = true;
  try {
    const data = await withLoading(() => api("/api/grade/essay", {
      method: "POST",
      body: JSON.stringify({
        passage: $("#e-passage").value,
        question: $("#e-question").value,
        answer: $("#e-answer").value,
        province_id: getProvince(),
      }),
    }), "Chấm bài văn...");
    renderResult(data, "Nghị luận xã hội");
  } catch (e) { showError(e.message); }
  finally { btn.disabled = false; }
});

/* ── Exam ── */

function formatTime(s) {
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

async function loadExamList() {
  const exams = hcmExams.length ? hcmExams : await loadHcmExamOptions();
  populateExamSelect("#exam-select", exams);
}

function renderExamForm(exam) {
  examData = exam;
  const p1 = exam.part1, p2 = exam.part2;
  $("#exam-content").innerHTML = `
    <div class="exam-section card">
      <span class="part-badge">${escapeHtml(p1.title)}</span>
      <div class="passage-box">${escapeHtml(p1.literary_passage)}</div>
      ${p1.reading_questions.map((q) => `
        <div class="reading-q" data-part="1">
          <label>Câu ${escapeHtml(q.id)} (${q.max_score}đ): ${escapeHtml(q.prompt)}</label>
          <textarea class="ex-r-ans" data-id="${q.id}" data-max="${q.max_score}" rows="2"></textarea>
        </div>`).join("")}
      <label class="field-label">${escapeHtml(p1.paragraph.prompt)}</label>
      <textarea class="ex-paragraph" rows="6"></textarea>
    </div>
    <div class="exam-section card">
      <span class="part-badge">${escapeHtml(p2.title)}</span>
      <div class="passage-box">${escapeHtml(p2.info_passage)}</div>
      ${p2.reading_questions.map((q) => `
        <div class="reading-q" data-part="2">
          <label>Câu ${escapeHtml(q.id)} (${q.max_score}đ): ${escapeHtml(q.prompt)}</label>
          <textarea class="ex-r-ans" data-id="${q.id}" data-max="${q.max_score}" rows="2"></textarea>
        </div>`).join("")}
      <label class="field-label">${escapeHtml(p2.essay.prompt)}</label>
      <textarea class="ex-essay" rows="12"></textarea>
    </div>`;
  secondsLeft = (exam.duration_minutes || 120) * 60;
  $("#exam-timer").textContent = formatTime(secondsLeft);
  examStartedAt = null;
}

$("#exam-load").addEventListener("click", async () => {
  try {
    renderExamForm(await api(`/api/exams/${$("#exam-select").value}`));
  } catch (e) { showError(e.message); }
});

$("#exam-enter").addEventListener("click", () => {
  document.body.classList.add("exam-room");
  switchTab("exam");
});

$("#exam-exit").addEventListener("click", () => {
  document.body.classList.remove("exam-room");
});

$("#exam-start").addEventListener("click", () => {
  clearInterval(timerInterval);
  examStartedAt = Date.now();
  timerInterval = setInterval(() => {
    secondsLeft -= 1;
    const t = $("#exam-timer");
    t.textContent = formatTime(secondsLeft);
    t.classList.toggle("urgent", secondsLeft < 600);
    if (secondsLeft <= 0) clearInterval(timerInterval);
  }, 1000);
});

$("#exam-stop").addEventListener("click", () => clearInterval(timerInterval));

$("#exam-gradeBtn").addEventListener("click", async () => {
  if (!examData) return showError("Hãy tải đề trước.");

  const elapsed = examStartedAt ? (Date.now() - examStartedAt) / 60000 : 999;
  if (examStartedAt && elapsed < 30) {
    if (!confirm("Bạn mới làm chưa đầy 30 phút. Chắc chắn nộp bài?")) return;
  }

  const sections = $$(".exam-section");
  const p1 = examData.part1, p2 = examData.part2;

  const part1Qs = [...sections[0].querySelectorAll(".ex-r-ans")].map((el) => ({
    id: el.dataset.id,
    prompt: p1.reading_questions.find((x) => x.id === el.dataset.id)?.prompt || "",
    max_score: parseFloat(el.dataset.max),
    answer: el.value,
  })).filter((q) => q.answer.trim());

  const part2Qs = [...sections[1].querySelectorAll(".ex-r-ans")].map((el) => ({
    id: el.dataset.id,
    prompt: p2.reading_questions.find((x) => x.id === el.dataset.id)?.prompt || "",
    max_score: parseFloat(el.dataset.max),
    answer: el.value,
  })).filter((q) => q.answer.trim());

  const btn = $("#exam-gradeBtn");
  btn.disabled = true;
  hideError();
  showLoading("Chấm toàn bộ đề thi...", "Có thể mất 1–2 phút");

  try {
    const data = await api("/api/grade/mock-exam", {
      method: "POST",
      body: JSON.stringify({
        exam_id: examData.id,
        province_id: getProvince(),
        part1_reading: part1Qs,
        paragraph_answer: sections[0].querySelector(".ex-paragraph")?.value || "",
        part2_reading: part2Qs,
        essay_answer: sections[1].querySelector(".ex-essay")?.value || "",
      }),
    });
    hideLoading();
    document.body.classList.remove("exam-room");

    renderResult({
      ...data,
      breakdown: Object.fromEntries(
        (data.score_sheet || []).map((r) => [r.section, { score: r.score, max: r.max, note: "" }])
      ),
      revision_hints: data.revision_hints,
    }, "Thi thử — Tổng điểm");

    renderScoreSheet(data);
    clearInterval(timerInterval);
  } catch (e) {
    hideLoading();
    showError(e.message);
  } finally {
    btn.disabled = false;
  }
});

/* ── History ── */

async function loadHistory() {
  try {
    const stats = await api("/api/stats");
    $("#statsGrid").innerHTML = `
      <div class="stat-card"><div class="val">${stats.total_attempts}</div><div class="lbl">Lần chấm</div></div>
      ${Object.entries(stats.by_type || {}).map(([k, v]) => `
        <div class="stat-card"><div class="val">${v.avg_percent}%</div><div class="lbl">TB ${TYPE_LABELS[k] || k}</div></div>`).join("")}`;

    const entries = Object.entries(stats.by_type || {});
    $("#chartBars").innerHTML = entries.length
      ? entries.map(([k, v]) => `
        <div class="chart-row"><span>${TYPE_LABELS[k] || k}</span>
        <div class="chart-bar-bg"><div class="chart-bar-fill" style="width:${v.avg_percent}%"></div></div>
        <span>${v.avg_percent}%</span></div>`).join("")
      : "<p class='meta'>Chưa có dữ liệu.</p>";

    const { items } = await api("/api/history");
    $("#historyList").innerHTML = items.length
      ? items.map((i) => `
        <div class="history-item">
          <div><span class="history-type">${TYPE_LABELS[i.question_type] || i.question_type}</span>
          <div class="meta">${new Date(i.created_at).toLocaleString("vi-VN")}</div></div>
          <span class="history-score">${i.total}/${i.max_score}</span>
        </div>`).join("")
      : "<p class='meta'>Chưa có lịch sử.</p>";
  } catch (e) {
    $("#statsGrid").innerHTML = `<p class="meta">${e.message}</p>`;
  }
}

/* ── Init ── */

addReadingQuestion({ id: "1a", max_score: 0.5, prompt: "Nêu ý chính của văn bản." });
checkHealth();
initProvinces()
  .then(loadHcmExamOptions)
  .then(async (exams) => {
    if (!exams[0]) return;
    await Promise.all([
      loadSampleParagraph(),
      loadSampleReading(),
      loadSampleEssay(),
    ]);
    renderExamForm(await api(`/api/exams/${exams[0].id}`));
  })
  .catch(showError);
