const detailState = {
  exam: null,
  activeTab: "questions",
  timedMode: null,
  timerId: null,
};

const $ = (selector) => document.querySelector(selector);

const detailElements = {
  navToggle: $("[data-nav-toggle]"),
  navLinks: $("[data-nav-links]"),
  examCount: $("#detailExamCount"),
  yearCount: $("#detailYearCount"),
  yearFilter: $("#detailYearFilter"),
  subjectFilter: $("#detailSubjectFilter"),
  examHeader: $("#detailExamHeader"),
  primaryAction: $("#detailPrimaryAction"),
  sources: $("#detailSources"),
  sourcesTitle: $("#detailSourcesTitle"),
  structure: $("#detailStructure"),
  structureTitle: $("#detailStructureTitle"),
  questions: $("#detailQuestions"),
  answers: $("#detailAnswers"),
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function sourceTypeLabel(sourceType) {
  if (sourceType === "official_mirror_public") return "Nguồn dẫn công bố chính thức";
  if (sourceType === "mirror_public") return "Nguồn công khai";
  if (sourceType === "text_public_reference") return "Nguồn text công khai";
  if (sourceType === "answer_suggestion_public") return "Nguồn gợi ý đáp án";
  return sourceType || "Nguồn tham chiếu";
}

function renderReviewGuide(reviewGuide) {
  if (!reviewGuide) return "";
  const formulas = Array.isArray(reviewGuide.formulas) ? reviewGuide.formulas : [];
  const tips = Array.isArray(reviewGuide.practiceTips) ? reviewGuide.practiceTips : [];
  const relatedTopics = Array.isArray(reviewGuide.relatedTopics) ? reviewGuide.relatedTopics : [];

  return `
    <aside class="review-guide-card">
      <div class="review-guide-head">
        <span>Kiến thức cần ôn</span>
        <strong>${escapeHtml(reviewGuide.title || "Ôn lại chuyên đề liên quan")}</strong>
      </div>
      ${reviewGuide.knowledge ? `<p>${escapeHtml(reviewGuide.knowledge)}</p>` : ""}
      ${formulas.length ? `
        <div class="review-guide-block">
          <b>Công thức / cấu trúc cần nhớ</b>
          <ul>${formulas.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        </div>
      ` : ""}
      ${tips.length ? `
        <div class="review-guide-block">
          <b>Cách ôn nhanh</b>
          <ul>${tips.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        </div>
      ` : ""}
      ${relatedTopics.length ? `
        <div class="review-topic-links" aria-label="Chuyên đề liên quan">
          ${relatedTopics.map((topic) => `
            <a href="${escapeHtml(topic.href || "./index.html#practice")}" title="Mở phần luyện tập">
              ${escapeHtml(topic.label || topic.topic)}
            </a>
          `).join("")}
        </div>
      ` : ""}
    </aside>
  `;
}

function getExamFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("exam");
}

function selectInitialExam(data) {
  const id = getExamFromUrl();
  if (id) {
    const fromUrl = data.exams.find((exam) => exam.id === id);
    if (fromUrl) return fromUrl;
  }
  return data.exams[0] || null;
}

function populateFilters(data) {
  detailElements.yearFilter.innerHTML = data.years
    .map((year) => `<option value="${year}">${year}</option>`)
    .join("");

  detailElements.subjectFilter.innerHTML = data.subjects
    .map((subject) => `<option value="${subject.id}">${escapeHtml(subject.label)}</option>`)
    .join("");
}

function syncFilters(exam) {
  detailElements.yearFilter.value = String(exam.year);
  detailElements.subjectFilter.value = exam.subject;
}

function findSelectedExam() {
  const year = Number(detailElements.yearFilter.value);
  const subject = detailElements.subjectFilter.value;
  return window.REAL_EXAM_DETAILS.exams.find((exam) => exam.year === year && exam.subject === subject);
}

function renderExamHeader(exam) {
  const statusHelp = exam.contentStatus === "verbatim_text_available"
    ? "Đề hiển thị nguyên văn; bấm Đáp án dưới từng câu để tra cứu."
    : "Trang đã sẵn sàng hiển thị câu hỏi/đáp án khi có bản text được xác minh.";

  detailElements.examHeader.innerHTML = `
    <article class="mini-stat">
      <span>Năm thi</span>
      <strong>${escapeHtml(exam.year)}</strong>
      <small>Năm học ${escapeHtml(exam.schoolYear)}</small>
    </article>
    <article class="mini-stat">
      <span>Môn thi</span>
      <strong>${escapeHtml(exam.subjectLabel)}</strong>
      <small>${escapeHtml(exam.durationMinutes)} phút</small>
    </article>
    <article class="mini-stat real-exam-note">
      <span>Trạng thái nội dung</span>
      <strong>${escapeHtml(exam.contentStatusLabel)}</strong>
      <small>${escapeHtml(statusHelp)}</small>
    </article>
  `;
}

function renderPrimaryAction(exam) {
  if (!detailElements.primaryAction) return;
  const questionCount = exam.questions?.length || 0;
  const answerCount = exam.answerGuide?.length || 0;
  const canGradeEnglish = isEnglishGradableExam(exam);
  const canPracticeMath = isMathPracticeExam(exam);
  const isTimedPractice = canGradeEnglish || canPracticeMath;
  const actionTitle = canGradeEnglish
    ? "Làm bài Tiếng Anh có tính giờ và chấm điểm"
    : canPracticeMath
      ? "Làm bài Toán có tính giờ và tự đối chiếu"
      : "Xem đề theo từng câu, mở đáp án khi cần";
  const actionDescription = canGradeEnglish
    ? `Đề có ${questionCount} câu và ${answerCount} đáp án đối chiếu. Đồng hồ chạy ${exam.durationMinutes} phút, nộp bài sẽ nhận điểm /10.`
    : canPracticeMath
      ? `Đề có ${questionCount} bài và ${answerCount} gợi ý đáp án. Đồng hồ chạy ${exam.durationMinutes} phút, nộp bài để xem hướng dẫn và tự chấm theo ý.`
      : `Đề có ${questionCount} câu/bài và ${answerCount} gợi ý đáp án. Dùng tab Câu hỏi để đọc đề, bấm đáp án dưới từng câu để tự kiểm tra.`;

  detailElements.primaryAction.innerHTML = `
    <article class="primary-action-card ${isTimedPractice ? "english-mode" : ""}">
      <div>
        <p class="eyebrow">${isTimedPractice ? "Chế độ thi có tính giờ" : "Chế độ đọc và tra cứu"}</p>
        <h3>${actionTitle}</h3>
        <p>${actionDescription}</p>
      </div>
      <div class="primary-action-buttons">
        ${canGradeEnglish ? `
          <button class="button primary" type="button" data-start-english-exam>Bắt đầu làm bài</button>
        ` : ""}
        ${canPracticeMath ? `
          <button class="button primary" type="button" data-start-math-exam>Bắt đầu thi Toán</button>
        ` : ""}
        <button class="button ghost" type="button" data-scroll-questions>Xem câu hỏi</button>
        <button class="button subtle" type="button" data-open-answers>Xem đáp án tổng hợp</button>
      </div>
    </article>
  `;
}

function renderSources(exam) {
  if (detailElements.sourcesTitle) detailElements.sourcesTitle.textContent = "Nguồn đối chiếu";
  detailElements.sources.innerHTML = `
    <ul class="detail-source-list">
      ${exam.sources.map((source) => `
        <li>
          <a href="${escapeHtml(source.url)}" target="_blank" rel="noopener">
            ${escapeHtml(source.host || source.title)}
          </a>
          <small>${escapeHtml(sourceTypeLabel(source.sourceType))}</small>
        </li>
      `).join("")}
    </ul>
    <a class="button ghost detail-metadata-link" href="${escapeHtml(exam.metadataPath)}" target="_blank" rel="noopener">
      Mở metadata nội bộ
    </a>
  `;
}

function renderStructure(exam) {
  if (detailElements.structureTitle) detailElements.structureTitle.hidden = false;
  detailElements.structure.hidden = false;
  detailElements.structure.innerHTML = exam.structureNotes
    .map((note) => `<li>${escapeHtml(note)}</li>`)
    .join("");
}

function renderTimedExamSidebar(exam, endsAt, options = {}) {
  const formId = options.formId || "englishTimedExamForm";
  const heading = options.heading || `Đang thi ${exam.subjectLabel}`;
  const note = options.note || "Đáp án được ẩn trong lúc làm bài. Hãy nộp bài để xem điểm và câu cần ôn lại.";
  const submitText = options.submitText || "Nộp bài và chấm điểm";

  if (detailElements.sourcesTitle) detailElements.sourcesTitle.textContent = heading;
  if (detailElements.structureTitle) detailElements.structureTitle.hidden = true;
  detailElements.structure.hidden = true;
  detailElements.sources.innerHTML = `
    <section class="timed-exam-card active sidebar-exam-card">
      <div>
        <p class="eyebrow">Chế độ làm bài</p>
        <h3>${escapeHtml(exam.subjectLabel)} ${escapeHtml(exam.year)} - ${escapeHtml(exam.durationMinutes)} phút</h3>
        <p>${escapeHtml(note)}</p>
      </div>
      <div class="exam-timer" aria-live="polite">
        <span>Thời gian còn lại</span>
        <strong data-exam-timer>${formatDuration((endsAt - Date.now()) / 1000)}</strong>
      </div>
      <div class="timed-exam-actions">
        <button class="button primary" type="submit" form="${escapeHtml(formId)}">${escapeHtml(submitText)}</button>
        <button class="button ghost" type="button" data-cancel-english-exam>Thoát chế độ thi</button>
      </div>
    </section>
  `;
}

function answersForQuestion(exam, questionNumber) {
  if (!questionNumber) return [];
  const questionKey = String(questionNumber);
  const numericQuestion = /^\d+$/.test(questionKey);

  return exam.answerGuide.filter((answer) => {
    if (!answer.number) return false;
    const answerKey = String(answer.number);
    if (answerKey === questionKey) return true;
    return !numericQuestion && answerKey.startsWith(questionKey);
  });
}

function isEnglishGradableExam(exam) {
  return exam?.subject === "TiengAnh" && exam.questions?.length && exam.answerGuide?.length;
}

function isMathPracticeExam(exam) {
  return exam?.subject === "Toan" && exam.questions?.length && exam.answerGuide?.length;
}

function answerForQuestion(exam, questionNumber) {
  return answersForQuestion(exam, questionNumber)[0] || null;
}

function clearTimedExamTimer() {
  if (detailState.timerId) {
    window.clearInterval(detailState.timerId);
    detailState.timerId = null;
  }
}

function formatDuration(totalSeconds) {
  const safeSeconds = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(safeSeconds / 60);
  const seconds = safeSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function normalizeEnglishAnswer(value) {
  return String(value ?? "")
    .toLowerCase()
    .replace(/[’‘]/g, "'")
    .replace(/[“”]/g, '"')
    .replace(/\([^)]*\)/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

function expandedExpectedAnswers(expected) {
  const raw = String(expected ?? "");
  const withoutParentheses = raw.replace(/\s*\([^)]*\)\s*/g, " ");
  const variants = new Set([raw, withoutParentheses]);

  [raw, withoutParentheses].forEach((source) => {
    const tokens = source.split(/\s+/);
    const slashIndex = tokens.findIndex((token) => token.includes("/"));
    if (slashIndex === -1) return;
    tokenLoop:
    for (const part of tokens[slashIndex].split("/")) {
      if (!part) continue tokenLoop;
      const next = [...tokens];
      next[slashIndex] = part;
      variants.add(next.join(" "));
    }
  });

  return [...variants].map(normalizeEnglishAnswer).filter(Boolean);
}

function gradeEnglishAnswer(userAnswer, expectedAnswer) {
  const normalizedUser = normalizeEnglishAnswer(userAnswer);
  const expectedVariants = expandedExpectedAnswers(expectedAnswer);
  const userLetter = optionLetter(userAnswer);
  const expectedLetter = optionLetter(expectedAnswer);
  if (userLetter && expectedLetter && userLetter === expectedLetter) return true;
  return Boolean(normalizedUser && expectedVariants.includes(normalizedUser));
}

function optionLetter(value) {
  const match = String(value ?? "").trim().match(/^([A-D])(?:[\s.)]|$)/i);
  return match ? match[1].toUpperCase() : "";
}

function parseEnglishChoices(question) {
  const lines = String(question?.prompt || "").split(/\n+/);
  const choices = [];
  lines.forEach((line) => {
    const match = line.trim().match(/^(?:\d+\.\s*)?([A-D])\.\s*(.+)$/);
    if (match) choices.push(`${match[1]}. ${match[2]}`);
  });
  return choices;
}

function questionPromptWithoutChoices(question) {
  if (!parseEnglishChoices(question).length) return question.prompt;
  return String(question.prompt || "")
    .split(/\n+/)
    .filter((line) => !/^\s*(?:\d+\.\s*)?[A-D]\.\s+/.test(line))
    .join("\n")
    .trim();
}

function englishQuestionNumber(question) {
  const match = String(question?.number ?? "").match(/\d+/);
  return match ? Number(match[0]) : null;
}

function englishPassageRange(questionNumber) {
  if (questionNumber >= 17 && questionNumber <= 22) return { from: 17, to: 22, label: "Đoạn điền từ / cloze test" };
  if (questionNumber >= 23 && questionNumber <= 28) return { from: 23, to: 28, label: "Đoạn đọc hiểu / reading" };
  return null;
}

function splitEnglishTimedPrompt(question) {
  const prompt = questionPromptWithoutChoices(question);
  const questionNumber = englishQuestionNumber(question);
  const choices = parseEnglishChoices(question);
  const fallback = questionNumber
    ? `Chọn đáp án phù hợp cho câu ${questionNumber}.`
    : "Chọn đáp án phù hợp.";

  if (!questionNumber) return { context: "", prompt: prompt || fallback };

  const marker = new RegExp(`(?:^|\\n)\\s*${questionNumber}\\.\\s+`);
  const match = prompt.match(marker);
  if (match && match.index > 0) {
    return {
      context: prompt.slice(0, match.index).trim(),
      prompt: prompt.slice(match.index).trim(),
    };
  }

  if (choices.length && englishPassageRange(questionNumber) && prompt.length > 260) {
    return {
      context: prompt,
      prompt: `Chọn đáp án phù hợp cho chỗ trống (${questionNumber}).`,
    };
  }

  return { context: "", prompt: prompt || fallback };
}

function renderActivePassageCard(passage, label) {
  if (!passage) return "";
  return `
    <details class="active-passage-card" open>
      <summary>${escapeHtml(label || "Đoạn văn đang làm")}</summary>
      <div>${escapeHtml(passage)}</div>
    </details>
  `;
}

function renderTimedQuestionBody(question, index, exam) {
  const answer = answerForQuestion(exam, question.number);
  const splitPrompt = splitEnglishTimedPrompt(question);
  const prompt = splitPrompt.prompt || `Chọn đáp án phù hợp cho câu ${question.number || index + 1}.`;

  return `
    <div class="question-meta">
      <span>Câu ${escapeHtml(question.number || index + 1)}</span>
      <span>${escapeHtml(question.points ? `${question.points} điểm` : "Tiếng Anh")}</span>
    </div>
    <div class="exam-question-text">${escapeHtml(prompt)}</div>
    ${controlForEnglishQuestion(question, answer, exam)}
  `;
}

function renderTimedQuestionCard(question, index, exam) {
  return `
    <article class="detail-question-card timed-question-card">
      ${renderTimedQuestionBody(question, index, exam)}
    </article>
  `;
}

function renderPassageQuestionGroup(groupQuestions, startIndex, exam, range) {
  const passage = groupQuestions
    .map((question) => splitEnglishTimedPrompt(question).context)
    .find(Boolean);

  if (!passage) {
    return groupQuestions
      .map((question, offset) => renderTimedQuestionCard(question, startIndex + offset, exam))
      .join("");
  }

  const groupId = `passage-${range.from}-${range.to}`;
  return `
    <section class="passage-group-card">
      ${renderActivePassageCard(passage, range.label)}
      <div class="passage-question-tabs" role="tablist" aria-label="Câu hỏi ${range.from}-${range.to}">
        ${groupQuestions.map((question, offset) => `
          <button
            class="passage-tab-label ${offset === 0 ? "active" : ""}"
            type="button"
            role="tab"
            aria-selected="${offset === 0 ? "true" : "false"}"
            data-passage-tab="${escapeHtml(groupId)}"
            data-passage-index="${offset}"
          >
            ${escapeHtml(question.number || startIndex + offset + 1)}
          </button>
        `).join("")}
      </div>
      <div class="passage-tab-panels">
        ${groupQuestions.map((question, offset) => `
          <article
            class="passage-tab-panel detail-question-card timed-question-card"
            role="tabpanel"
            data-passage-panel="${escapeHtml(groupId)}"
            data-passage-index="${offset}"
            ${offset === 0 ? "" : "hidden"}
          >
            ${renderTimedQuestionBody(question, startIndex + offset, exam)}
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function renderEnglishTimedQuestionBlocks(exam) {
  const blocks = [];
  let index = 0;

  while (index < exam.questions.length) {
    const question = exam.questions[index];
    const questionNumber = englishQuestionNumber(question);
    const range = englishPassageRange(questionNumber);

    if (!range) {
      blocks.push(renderTimedQuestionCard(question, index, exam));
      index += 1;
      continue;
    }

    const groupStart = index;
    const groupQuestions = [];
    while (index < exam.questions.length) {
      const current = exam.questions[index];
      const currentNumber = englishQuestionNumber(current);
      const currentRange = englishPassageRange(currentNumber);
      if (!currentRange || currentRange.from !== range.from || currentRange.to !== range.to) break;
      groupQuestions.push(current);
      index += 1;
    }

    blocks.push(renderPassageQuestionGroup(groupQuestions, groupStart, exam, range));
  }

  return blocks.join("");
}

function compactAnswerText(value) {
  return String(value ?? "").replace(/\s+/g, " ").trim();
}

function textAnswerOptions(answer, exam) {
  const expected = compactAnswerText(answer?.answer);
  if (!expected) return [];
  const pool = exam.answerGuide
    .map((item) => compactAnswerText(item.answer))
    .filter((item) => (
      item &&
      item !== expected &&
      !optionLetter(item) &&
      !/^(true|false)$/i.test(item) &&
      item.length <= Math.max(expected.length + 80, 120)
    ));
  const seed = String(answer?.number || expected).split("").reduce((sum, char) => sum + char.charCodeAt(0), 0);
  const distractors = [];
  for (let offset = 0; offset < pool.length && distractors.length < 3; offset += 1) {
    const candidate = pool[(seed + offset) % pool.length];
    if (!distractors.includes(candidate)) distractors.push(candidate);
  }
  const options = [expected, ...distractors];
  return options
    .map((item, index) => ({ item, sort: (seed + index * 17) % 97 }))
    .sort((a, b) => a.sort - b.sort)
    .map(({ item }) => item);
}

function renderEnglishChoiceCheckboxes(name, questionNumber, choices) {
  return `
    <div class="exam-answer-control choice-control" role="group" aria-label="Đáp án câu ${escapeHtml(questionNumber)}">
      ${choices.map((choice, choiceIndex) => {
    const id = `${name}-${choiceIndex}`;
    return `
          <label class="choice-checkbox" for="${escapeHtml(id)}">
            <input
              id="${escapeHtml(id)}"
              type="checkbox"
              name="${escapeHtml(name)}"
              value="${escapeHtml(choice)}"
              data-answer-checkbox
            />
            <span>${escapeHtml(choice)}</span>
          </label>
        `;
  }).join("")}
    </div>
  `;
}

function controlForEnglishQuestion(question, answer, exam) {
  const name = `answer-${question.number}`;
  const expected = String(answer?.answer || "").trim();
  const choices = parseEnglishChoices(question);
  if (choices.length >= 2) {
    return renderEnglishChoiceCheckboxes(name, question.number, choices);
  }

  if (/^(true|false)$/i.test(expected)) {
    return renderEnglishChoiceCheckboxes(name, question.number, ["True", "False"]);
  }

  const textOptions = textAnswerOptions(answer, exam);
  return textOptions.length
    ? renderEnglishChoiceCheckboxes(name, question.number, textOptions)
    : `<p class="exam-answer-control text-control">Câu này chưa có phương án chọn tự động.</p>`;
}

function renderEnglishTimedExamIntro(exam) {
  if (!isEnglishGradableExam(exam)) return "";
  return `
    <section class="timed-exam-card">
      <div>
        <p class="eyebrow">Chế độ thi Tiếng Anh</p>
        <h3>Làm bài có tính giờ và chấm điểm tự động</h3>
        <p>
          Đồng hồ chạy theo thời lượng đề ${escapeHtml(exam.durationMinutes)} phút.
          Khi nộp bài, hệ thống chấm các câu có đáp án so sánh được và hiển thị điểm ngay.
        </p>
      </div>
      <button class="button primary" type="button" data-start-english-exam>
        Bắt đầu làm bài
      </button>
    </section>
  `;
}

function renderQuestionList(exam) {
  if (!exam.questions.length) {
    detailElements.questions.innerHTML = `
      <div class="detail-empty-state">
        <h3>Chưa có nội dung câu hỏi được nhập</h3>
        <p>
          Đề này hiện chỉ lưu nguồn công khai. Khi có bản text/PDF được phép sử dụng,
          hãy nhập từng câu vào <code>real-exam-detail-data.js</code> theo trường
          <code>questions</code>; trang sẽ tự hiển thị theo từng câu.
        </p>
        <p>
          Trạng thái này giúp tránh việc tự chép sai hoặc sử dụng đề thi thật khi chưa có quyền/nguồn xác minh.
        </p>
      </div>
    `;
    return;
  }

  detailElements.questions.innerHTML = `
    ${exam.questions
    .map((question, index) => {
      const relatedAnswers = answersForQuestion(exam, question.number);
      return `
        <article class="detail-question-card">
          <div class="question-meta">
            <span>Câu ${escapeHtml(question.number || index + 1)}</span>
            <span>${escapeHtml(question.points ? `${question.points} điểm` : exam.subjectLabel)}</span>
          </div>
          <div class="exam-question-text">${escapeHtml(question.prompt)}</div>
          ${question.choices?.length ? `
            <ol class="mock-choices">
              ${question.choices.map((choice) => `<li>${escapeHtml(choice)}</li>`).join("")}
            </ol>
          ` : ""}
          ${relatedAnswers.length ? `
            <details class="inline-answer">
              <summary>Đáp án / gợi ý cho câu này</summary>
              <div class="inline-answer-list">
                ${relatedAnswers.map((answer) => `
                  <section>
                    <h4>${escapeHtml(answer.number || "Đáp án")}</h4>
                    <p><b>Đáp án:</b> ${escapeHtml(answer.answer || answer.correctAnswer || "Chưa nhập")}</p>
                    ${answer.explanation ? `<p><b>Hướng dẫn:</b> ${escapeHtml(answer.explanation)}</p>` : ""}
                    ${renderReviewGuide(answer.reviewGuide)}
                  </section>
                `).join("")}
              </div>
            </details>
          ` : ""}
        </article>
      `;
    })
    .join("")}
  `;
}

function renderEnglishExamForm(exam) {
  const startedAt = detailState.timedMode?.startedAt || Date.now();
  const endsAt = startedAt + exam.durationMinutes * 60 * 1000;
  detailState.timedMode = {
    startedAt,
    endsAt,
    submitted: false,
  };

  renderTimedExamSidebar(exam, endsAt);
  detailElements.questions.innerHTML = `
    <form id="englishTimedExamForm" class="timed-exam-form">
      ${renderEnglishTimedQuestionBlocks(exam)}
    </form>
  `;

  clearTimedExamTimer();
  detailState.timerId = window.setInterval(() => {
    const remainingMs = endsAt - Date.now();
    const timer = document.querySelector("[data-exam-timer]");
    if (timer) timer.textContent = formatDuration(remainingMs / 1000);
    if (remainingMs <= 0) {
      submitEnglishTimedExam(exam, true);
    }
  }, 1000);
}

function submitEnglishTimedExam(exam, timedOut = false) {
  const form = detailElements.questions.querySelector("#englishTimedExamForm");
  if (!form || detailState.timedMode?.submitted) return;
  detailState.timedMode.submitted = true;
  clearTimedExamTimer();
  renderSources(exam);
  renderStructure(exam);

  const formData = new FormData(form);
  const results = exam.questions.map((question) => {
    const answer = answerForQuestion(exam, question.number);
    const expected = answer?.answer || "";
    const userAnswer = formData.get(`answer-${question.number}`) || "";
    const correct = gradeEnglishAnswer(userAnswer, expected);
    const points = Number(question.points || 0.25);
    return {
      number: question.number,
      prompt: question.prompt,
      userAnswer,
      expected,
      correct,
      points,
      earned: correct ? points : 0,
      explanation: answer?.explanation || "",
      reviewGuide: answer?.reviewGuide || null,
    };
  });

  const total = results.reduce((sum, item) => sum + item.points, 0);
  const earned = results.reduce((sum, item) => sum + item.earned, 0);
  const correctCount = results.filter((item) => item.correct).length;
  const score10 = total ? (earned / total) * 10 : 0;
  renderEnglishExamResult(exam, {
    timedOut,
    results,
    total,
    earned,
    correctCount,
    score10,
  });
}

function renderEnglishExamResult(exam, summary) {
  detailElements.questions.innerHTML = `
    <section class="timed-exam-card result">
      <div>
        <p class="eyebrow">Kết quả làm bài</p>
        <h3>${summary.score10.toFixed(2)} / 10 điểm</h3>
        <p>
          Đúng ${summary.correctCount}/${summary.results.length} câu,
          đạt ${summary.earned.toFixed(2)}/${summary.total.toFixed(2)} điểm gốc.
          ${summary.timedOut ? "Bài đã được tự nộp vì hết giờ." : "Bài đã được nộp và chấm tự động."}
        </p>
      </div>
      <button class="button primary" type="button" data-start-english-exam>Làm lại đề này</button>
    </section>

    <div class="timed-result-list">
      ${summary.results.map((item) => `
        <article class="detail-question-card timed-result-card ${item.correct ? "correct" : "incorrect"}">
          <div class="question-meta">
            <span>Câu ${escapeHtml(item.number)}</span>
            <span>${item.correct ? "Đúng" : "Sai"} - ${item.earned.toFixed(2)}/${item.points.toFixed(2)} điểm</span>
          </div>
          <div class="exam-question-text">${escapeHtml(item.prompt)}</div>
          <p><b>Bạn trả lời:</b> ${escapeHtml(item.userAnswer || "Chưa trả lời")}</p>
          <p><b>Đáp án:</b> ${escapeHtml(item.expected)}</p>
          ${item.explanation ? `<p><b>Ghi chú:</b> ${escapeHtml(item.explanation)}</p>` : ""}
          ${renderReviewGuide(item.reviewGuide)}
        </article>
      `).join("")}
    </div>
  `;
}

function renderMathExamForm(exam) {
  const startedAt = detailState.timedMode?.startedAt || Date.now();
  const endsAt = startedAt + exam.durationMinutes * 60 * 1000;
  detailState.timedMode = {
    startedAt,
    endsAt,
    submitted: false,
  };

  renderTimedExamSidebar(exam, endsAt, {
    formId: "mathTimedExamForm",
    heading: "Đang thi Toán",
    note: "Toán là bài tự luận nên hệ thống không chấm tự động tuyệt đối. Hãy nhập đáp số/lời giải ngắn, nộp bài để đối chiếu đáp án và tự chấm theo hướng dẫn.",
    submitText: "Nộp bài và xem đáp án",
  });

  detailElements.questions.innerHTML = `
    <form id="mathTimedExamForm" class="timed-exam-form math-exam-form">
      ${exam.questions.map((question, index) => `
        <article class="detail-question-card timed-question-card">
          <div class="question-meta">
            <span>Bài ${escapeHtml(question.number || index + 1)}</span>
            <span>${escapeHtml(question.points ? `${question.points} điểm` : "Toán")}</span>
          </div>
          <div class="exam-question-text">${escapeHtml(question.prompt)}</div>
          <label class="math-answer-box">
            Bài làm / đáp số của em
            <textarea name="answer-${escapeHtml(question.number)}" rows="4" placeholder="Nhập đáp số hoặc tóm tắt các bước giải chính..."></textarea>
          </label>
        </article>
      `).join("")}
    </form>
  `;

  clearTimedExamTimer();
  detailState.timerId = window.setInterval(() => {
    const remainingMs = endsAt - Date.now();
    const timer = document.querySelector("[data-exam-timer]");
    if (timer) timer.textContent = formatDuration(remainingMs / 1000);
    if (remainingMs <= 0) {
      submitMathTimedExam(exam, true);
    }
  }, 1000);
}

function submitMathTimedExam(exam, timedOut = false) {
  const form = detailElements.questions.querySelector("#mathTimedExamForm");
  if (!form || detailState.timedMode?.submitted) return;
  detailState.timedMode.submitted = true;
  clearTimedExamTimer();
  renderSources(exam);
  renderStructure(exam);

  const formData = new FormData(form);
  const results = exam.questions.map((question) => {
    const answer = answerForQuestion(exam, question.number);
    return {
      number: question.number,
      prompt: question.prompt,
      points: Number(question.points || 1),
      userAnswer: formData.get(`answer-${question.number}`) || "",
      expected: answer?.answer || answer?.correctAnswer || "Chưa nhập đáp án",
      explanation: answer?.explanation || "",
      reviewGuide: answer?.reviewGuide || null,
    };
  });

  renderMathExamResult(exam, {
    timedOut,
    results,
    total: results.reduce((sum, item) => sum + item.points, 0),
  });
}

function renderMathExamResult(exam, summary) {
  detailElements.questions.innerHTML = `
    <section class="timed-exam-card result">
      <div>
        <p class="eyebrow">Kết quả tự đối chiếu</p>
        <h3>${escapeHtml(exam.subjectLabel)} ${escapeHtml(exam.year)} - ${summary.total.toFixed(1)} điểm</h3>
        <p>
          ${summary.timedOut ? "Bài đã được tự nộp vì hết giờ." : "Bài đã được nộp."}
          Hãy so đáp số/lời giải của em với hướng dẫn bên dưới và tự đánh dấu mức đạt từng ý.
        </p>
      </div>
      <button class="button primary" type="button" data-start-math-exam>Làm lại đề này</button>
    </section>

    <div class="timed-result-list">
      ${summary.results.map((item) => `
        <article class="detail-question-card timed-result-card math-result-card">
          <div class="question-meta">
            <span>Bài ${escapeHtml(item.number)}</span>
            <span>Tự chấm / ${item.points.toFixed(2)} điểm</span>
          </div>
          <div class="exam-question-text">${escapeHtml(item.prompt)}</div>
          <div class="math-self-check">
            <p><b>Bài làm của em:</b> ${escapeHtml(item.userAnswer || "Chưa trả lời")}</p>
            <p><b>Đáp án/gợi ý:</b> ${escapeHtml(item.expected)}</p>
            ${item.explanation ? `<p><b>Hướng dẫn:</b> ${escapeHtml(item.explanation)}</p>` : ""}
            <div class="self-check-grid" aria-label="Tự chấm mức đạt">
              <label><input type="checkbox" /> Đúng đáp số</label>
              <label><input type="checkbox" /> Có lập luận/công thức</label>
              <label><input type="checkbox" /> Đủ điều kiện, đơn vị, kết luận</label>
            </div>
          </div>
          ${renderReviewGuide(item.reviewGuide)}
        </article>
      `).join("")}
    </div>
  `;
}

function renderAnswerList(exam) {
  const answers = exam.answerGuide.length ? exam.answerGuide : exam.questions;
  if (!answers.length) {
    detailElements.answers.innerHTML = `
      <div class="detail-empty-state">
        <h3>Chưa có đáp án/hướng dẫn chấm được nhập</h3>
        <p>
          Mở nguồn công khai bên trái để đối chiếu đáp án gốc. Khi có nội dung được phép sử dụng,
          nhập đáp án theo từng câu để trang hiển thị tại đây.
        </p>
      </div>
    `;
    return;
  }

  detailElements.answers.innerHTML = answers
    .map((answer, index) => `
      <article class="detail-question-card">
        <div class="question-meta">
          <span>Câu ${escapeHtml(answer.number || index + 1)}</span>
          <span>Đáp án</span>
        </div>
        <p><b>Đáp án:</b> ${escapeHtml(answer.answer || answer.correctAnswer || "Chưa nhập")}</p>
        ${answer.explanation ? `<p><b>Hướng dẫn:</b> ${escapeHtml(answer.explanation)}</p>` : ""}
        ${renderReviewGuide(answer.reviewGuide)}
      </article>
    `)
    .join("");
}

function renderSelectedExam(exam) {
  if (!exam) return;
  clearTimedExamTimer();
  detailState.timedMode = null;
  detailState.exam = exam;
  syncFilters(exam);
  renderExamHeader(exam);
  renderPrimaryAction(exam);
  renderSources(exam);
  renderStructure(exam);
  renderQuestionList(exam);
  renderAnswerList(exam);
}

function setActiveTab(tabName) {
  if (detailState.timedMode && !detailState.timedMode.submitted && tabName === "answers") {
    return;
  }
  detailState.activeTab = tabName;
  document.querySelectorAll("[data-detail-tab]").forEach((button) => {
    button.classList.toggle("active", button.dataset.detailTab === tabName);
  });
  detailElements.questions.hidden = tabName !== "questions";
  detailElements.answers.hidden = tabName !== "answers";
}

function bindEvents() {
  detailElements.navToggle?.addEventListener("click", () => {
    detailElements.navLinks.classList.toggle("open");
  });

  detailElements.yearFilter.addEventListener("change", () => {
    const exam = findSelectedExam();
    if (exam) renderSelectedExam(exam);
  });

  detailElements.subjectFilter.addEventListener("change", () => {
    const exam = findSelectedExam();
    if (exam) renderSelectedExam(exam);
  });

  document.querySelectorAll("[data-detail-tab]").forEach((button) => {
    button.addEventListener("click", () => setActiveTab(button.dataset.detailTab));
  });

  detailElements.questions.addEventListener("change", (event) => {
    const answerCheckbox = event.target.closest("[data-answer-checkbox]");
    if (!answerCheckbox || !answerCheckbox.checked) return;
    const group = answerCheckbox.closest(".choice-control");
    group?.querySelectorAll("[data-answer-checkbox]").forEach((checkbox) => {
      if (checkbox !== answerCheckbox) checkbox.checked = false;
    });
  });

  detailElements.questions.addEventListener("click", (event) => {
    const passageTab = event.target.closest("[data-passage-tab]");
    if (passageTab) {
      const groupId = passageTab.dataset.passageTab;
      const selectedIndex = passageTab.dataset.passageIndex;
      detailElements.questions.querySelectorAll(`[data-passage-tab="${groupId}"]`).forEach((tab) => {
        const selected = tab.dataset.passageIndex === selectedIndex;
        tab.classList.toggle("active", selected);
        tab.setAttribute("aria-selected", selected ? "true" : "false");
      });
      detailElements.questions.querySelectorAll(`[data-passage-panel="${groupId}"]`).forEach((panel) => {
        panel.hidden = panel.dataset.passageIndex !== selectedIndex;
      });
      return;
    }

    if (event.target.closest("[data-start-english-exam]")) {
      if (isEnglishGradableExam(detailState.exam)) renderEnglishExamForm(detailState.exam);
      return;
    }
    if (event.target.closest("[data-start-math-exam]")) {
      if (isMathPracticeExam(detailState.exam)) renderMathExamForm(detailState.exam);
      return;
    }
    if (event.target.closest("[data-cancel-english-exam]")) {
      clearTimedExamTimer();
      detailState.timedMode = null;
      renderSources(detailState.exam);
      renderStructure(detailState.exam);
      renderQuestionList(detailState.exam);
    }
  });

  detailElements.sources.addEventListener("click", (event) => {
    if (event.target.closest("[data-cancel-english-exam]")) {
      clearTimedExamTimer();
      detailState.timedMode = null;
      renderSources(detailState.exam);
      renderStructure(detailState.exam);
      renderQuestionList(detailState.exam);
    }
  });

  detailElements.primaryAction?.addEventListener("click", (event) => {
    if (event.target.closest("[data-start-english-exam]")) {
      setActiveTab("questions");
      if (isEnglishGradableExam(detailState.exam)) renderEnglishExamForm(detailState.exam);
      return;
    }
    if (event.target.closest("[data-start-math-exam]")) {
      setActiveTab("questions");
      if (isMathPracticeExam(detailState.exam)) renderMathExamForm(detailState.exam);
      return;
    }
    if (event.target.closest("[data-scroll-questions]")) {
      setActiveTab("questions");
      detailElements.questions.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    if (event.target.closest("[data-open-answers]")) {
      setActiveTab("answers");
      detailElements.answers.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });

  detailElements.questions.addEventListener("submit", (event) => {
    if (event.target?.id === "englishTimedExamForm") {
      event.preventDefault();
      submitEnglishTimedExam(detailState.exam);
    }
    if (event.target?.id === "mathTimedExamForm") {
      event.preventDefault();
      submitMathTimedExam(detailState.exam);
    }
  });
}

function init() {
  const data = window.REAL_EXAM_DETAILS;
  if (!data?.exams?.length) {
    detailElements.examHeader.innerHTML = `<article class="real-exam-empty">Chưa có dữ liệu đề thi thật.</article>`;
    return;
  }

  detailElements.examCount.textContent = data.exams.length;
  detailElements.yearCount.textContent = data.years.length;
  populateFilters(data);
  renderSelectedExam(selectInitialExam(data));
  bindEvents();
}

init();
