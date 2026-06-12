# Rule Engine — Cách app map câu trả lời (không dùng AI)

App **không gọi LLM**. Mọi phân loại, gợi ý và phát hiện mâu thuẫn đều dựa trên **keyword matching** và **luồng rule cố định** trong code.

Tài liệu này mô tả *rule là gì*, *chạy ở đâu*, và *cách mở rộng*.

---

## 1. Thuật toán cốt lõi: `matchFromLibrary`

**File:** `reflection-engine.js` → `ReflectionEngine.matchFromLibrary(text, library)`

```
1. Chuẩn hóa text: lowercase + trim
2. Với mỗi item trong library { label, keywords[] }:
   - Duyệt từng vị trí keyword xuất hiện trong text
   - Bỏ qua nếu bị phủ định gần đó (isKeywordNegated): không/chưa/chẳng/đừng…
   - score += độ dài keyword; keyword ngắn (≤3 ký tự) được bonus nếu có ranh giới từ
3. Sắp xếp score giảm dần → trả về danh sách khớp
```

**Ví dụ:** Câu *"Tôi lo lắng và căng thẳng"*  
→ khớp `Lo lắng` (lo lắng, băn khoăn…) và `Áp lực` (căng thẳng, stress…)  
→ engine lấy **tối đa 2–3 item** score cao nhất tùy loại.

**Ví dụ phủ định:** *"Tôi không lo lắng nữa"* → keyword `lo lắng` bị bỏ qua vì có `không` ngay trước.

**Fallback:** Nếu không khớp library nhưng câu có dấu hiệu heuristic (`looksLikeBelief`, `looksLikeValue`…) hoặc đang ở đúng bước EEIBVIA → ghi nhận bằng `summarizeUserPhrase()` (rút gọn câu user làm nhãn).

**Giới hạn:** Chỉ nhận diện được từ/cụm đã có trong `keywords` hoặc heuristic đã định nghĩa. Không hiểu ngữ nghĩa ngoài từ điển.

---

## 2. Khung 7 bước EEIBVIA

**File:** `cognitive-library.js` → `REFLECTION_FLOW`

| Bước (code)   | Nhãn UI        | Vai trò |
|---------------|----------------|---------|
| Event         | Việc xảy ra    | Tình huống kích hoạt (câu mở đầu) |
| Emotion       | Cảm xúc        | Cảm xúc gắn với sự việc |
| Interpretation| Cách hiểu      | Cách diễn giải / lo điều gì xảy ra |
| Belief        | Niềm tin       | Niềm tin ẩn dưới cách hiểu |
| Value         | Giá trị        | Điều quan trọng với người dùng |
| Identity      | Vai trò bản thân| “Tôi là ai” trong tình huống |
| Action        | Hành động      | Việc đã / sẽ làm |

**Luồng hội thoại:** Mỗi lần user gửi tin → `processMessage()` xử lý theo `session.flowStep` hiện tại → `getNextFlowStep()` chuyển sang bước kế (mỗi tin user = tiến 1 bước).

**File xử lý:** `reflection-engine.js` → `processMessage`, `continueSession`, `createSession`

---

## 3. Thư viện keyword (`cognitive-library.js`)

Mỗi mục có dạng:

```js
{ label: 'Nhãn hiển thị', keywords: ['từ', 'cụm từ', ...] }
```

### 3.1. Trích xuất từ câu trả lời

| Library | Số mục (ước) | Dùng khi | Giới hạn lấy |
|---------|--------------|----------|--------------|
| `EMOTIONS` | ~65 | Bước Emotion hoặc text có keyword cảm xúc | 3 |
| `VALUES` | ~60 | Bước Value | 3 |
| `BELIEFS` | ~120 | Bước Belief | 3 |
| `COGNITIVE_BIASES` | ~33 | Phân tích session (Góc khám phá) | 2 |
| `ACTION_PATTERNS` | ~22 | Bước Action hoặc `looksLikeAction` | 2 |
| `IDENTITY_PATTERNS` | ~16 | Bước Identity hoặc `looksLikeIdentity` | 2 |

**Hành động** (`cognitive-library.js` → `ACTION_PATTERNS`, dùng qua `extractActions`):

| Label | Keywords ví dụ |
|-------|----------------|
| Làm việc nhiều giờ | 14 giờ, làm việc nhiều, overtime |
| La mắng / kỷ luật con | la mắng, phạt, mắng |
| Bắt con học | bắt học, ép học |
| Tránh né / im lặng | im lặng, tránh, không nói |
| Tìm kiếm giải pháp | tìm cách, giải quyết |
| Nhờ giúp đỡ | nhờ, nhờ team, tư vấn |
| Nghỉ ngơi | nghỉ, thư giãn |
| Dành thời gian cho gia đình | dành thời gian, ở bên |
| So sánh với người khác | so sánh, nhà hàng xóm |
| Tự trách móc | tự trách, trách mình |
| Từ chối / đặt ranh giới | từ chối, nói không |
| Lên kế hoạch | lên kế hoạch, sẽ thử |
| … | Xem đầy đủ trong `cognitive-library.js` |

### 3.2. Rule bổ sung trong `processMessage`

Ngoài keyword library, có **heuristic** (pattern đơn giản):

| Bước | Điều kiện ghi nhận thêm |
|------|-------------------------|
| Interpretation | `looksLikeInterpretation`: chứa *sẽ, có thể, lo rằng, nghĩ rằng…* |
| Belief | `looksLikeBelief` hoặc bước Belief → `summarizeUserPhrase` |
| Value | `looksLikeValue` hoặc bước Value → `summarizeUserPhrase` |
| Identity | `looksLikeIdentity` hoặc bước Identity → `summarizeUserPhrase` |
| Action | `looksLikeAction`, bước Action, hoặc khớp `ACTION_PATTERNS` |
| Emotion | Không match library → lấy 50 ký tự đầu làm nhãn tạm |
| Event | Tin đầu hoặc bước Event → cắt 80 ký tự làm nhãn sự kiện |

---

## 4. Sinh câu hỏi & gợi ý trả lời

### 4.1. Câu hỏi người dẫn

**File:** `i18n.js` (`I18N_REFLECTION_QUESTIONS`) + `reflection-engine.js` → `generateQuestion`

| Bước | Rule chọn câu hỏi |
|------|-------------------|
| Emotion + có event | Template: *"Khi nghĩ về {event}, cảm xúc nào…"* |
| Interpretation + có emotion | Template: *"Khi cảm thấy {emotion}, bạn lo…"* |
| Belief + có interpretation | Cố định: *"Điều gì khiến bạn tin như vậy?"* |
| Value | Đôi khi dùng `contextQuestion` (hoàn cảnh / áp lực ngoài) |
| Identity | Đôi khi dùng `powerQuestion` (ai có thể thay đổi) |
| Khác | Random 1 trong pool `REFLECTION_QUESTIONS[bước]` |

**Mở đầu phiên:** `getOpeningQuestion(initialThought)` — nếu initial thought có emotion keyword → template có snippet; không thì câu mặc định.

**Kết thúc phiên:** Khi ở bước Action và đủ ≥6 tin user → `buildSessionEndMessage`: tóm tắt + reframe + bước nhỏ.

### 4.2. Gợi ý chip (UI)

| Nguồn | File | Mô tả |
|-------|------|--------|
| `REFLECTION_SUGGESTIONS` | `cognitive-library.js` + `i18n.js` | Mẫu câu dài theo từng bước (tối đa 5) |
| `I18N_SHORT_CHIPS` | `i18n.js` | Chip ngắn (Buồn, Lo, Tức…) ở bước Emotion |

---

## 5. Bản đồ suy nghĩ (Cognitive Forest)

**File:** `cognitive-library.js` → `FOREST_TREES`

Gán nhánh **family | work | finance | learning | health | self** bằng cách:  
`label + sourceText` của node → nếu chứa keyword của cây nào → thuộc cây đó; không khớp → `self`.

| Cây | Keywords ví dụ |
|-----|----------------|
| Gia đình | gia đình, con, vợ, chồng, cha, mẹ… |
| Công việc | công việc, sếp, dự án, công ty… |
| Tài chính | tiền, nợ, lương, đầu tư… |
| Học tập | học, thi, điểm, trường… |
| Sức khỏe | sức khỏe, mệt, ngủ, stress… |
| Bản thân | tôi, mình, tự tin… (mặc định) |

**Trạng thái ghi nhận** (`cognitive-tree.js`):

| Occurrences | Status UI |
|-------------|-----------|
| 1 | Mới ghi nhận |
| 2 | Lặp lại nhiều lần |
| ≥3 | Đã vững chắc |

Cùng `type + label` → `upsertNode` tăng occurrences thay vì tạo node mới.

---

## 6. Mâu thuẫn (Contradiction Engine)

**File:** `contradiction-engine.js` + `CONTRADICTION_PATTERNS` trong `cognitive-library.js`

Chạy 4 nhóm rule:

### 6.1. Pattern cố định (`CONTRADICTION_PATTERNS`)

Khớp khi **đồng thời** có node Value/Belief/Action chứa keyword:

| Ví dụ | Value/Belief keywords | Action keywords |
|-------|----------------------|-----------------|
| Gia đình vs overtime | gia đình, ưu tiên | 14 giờ, làm việc nhiều |
| Sức khỏe vs stress | sức khỏe | không ngủ, stress |
| Cân bằng vs làm nhiều | cân bằng | làm cuối tuần, không nghỉ |
| Tự do vs kiểm soát con | tự do | bắt con, phải nghe |
| Phát triển vs không học | phát triển | không học, bỏ học |
| Con nghe lời vs tự do | belief + value keywords |
| Tiền vs gia đình | tiền mang lại hạnh phúc + gia đình |

### 6.2. Niềm tin đối lập (`detectOpposingBeliefs`)

Cặp cứng trong code, ví dụ:

- tiền mang lại hạnh phúc ↔ hạnh phúc không cần tiền  
- con phải nghe lời ↔ con cần tự lập  
- phải hoàn hảo ↔ sai lầm là bình thường  
- làm việc chăm chỉ ↔ nghỉ ngơi  
- kiểm soát ↔ tự do  

### 6.3. Khoảng cách giá trị–hành động (`detectValueActionGap`)

Chỉ xét Value có status ≠ draft:

| Value keywords | Action keywords | Thông điệp |
|----------------|-----------------|------------|
| gia đình, yêu thương | làm việc nhiều, 14 giờ | ít thời gian cho gia đình |
| sức khỏe | stress, không ngủ, mệt | nhịp sống gây căng thẳng |
| phát triển | bắt con học, ép học | áp lực hơn khuyến khích |

### 6.4. Quan hệ `conflicts` trong DataStore

Nếu có relation type `conflicts` giữa 2 node → báo mâu thuẫn severity `high`.

---

## 7. Góc khám phá (Insight Engine)

**File:** `insight-engine.js`

| Output | Rule |
|--------|------|
| Khám phá hôm nay | Node tạo/cập nhật trong ngày |
| Top beliefs/values | Sắp xếp `occurrences` giảm dần |
| Thiên kiến | `matchFromLibrary` trên 5 session gần nhất → `COGNITIVE_BIASES` |
| Mâu thuẫn | `ContradictionEngine.analyze()` |
| Gợi ý suy ngẫm tiếp | `EXPLORATION_PROMPT_RULES` (xem §8) |

---

## 8. Gợi ý suy ngẫm tiếp

**File:** `cognitive-library.js` → `EXPLORATION_PROMPT_RULES`  
**Nội dung câu:** `i18n.js` → `I18N_EXPLORATION_PROMPTS`

Mỗi rule: `{ id, priority, matches(insights), vars? }`

| id | Kích hoạt khi |
|----|----------------|
| family_work | Mâu thuẫn có keyword gia đình + công việc/overtime |
| health_burnout | Sức khỏe + stress/mệt |
| work_life_balance | Cân bằng / work-life |
| development_pressure | Phát triển + ép học / áp lực |
| control_freedom | Tự do + kiểm soát |
| belief_obedience | Nghe lời |
| money_family | Tiền + hạnh phúc |
| bias_* | Có thiên kiến tương ứng (Catastrophizing, Should…) |
| general_belief | Fallback: có top belief |

Lấy tối đa **4** gợi ý, `priority` nhỏ = ưu tiên cao.

---

## 9. An toàn (Safety Engine)

**File:** `safety-engine.js`

Keyword khủng hoảng (VI + EN): *tự tử, muốn chết, tự làm hại, chán sống, self-harm, suicide…*  
Bạo lực gia đình: *đánh con, bạo lực gia đình, bị bạo hành…* → hiện tài nguyên hỗ trợ.  
→ chặn gửi tin, hiện modal đường dây nóng **111**, **18001929**.

---

## 10. Chế độ Thử nghiệm

**File:** `test-scenarios.js` — kịch bản mẫu có `dialogue[]` theo từng bước EEIBVIA.  
**File:** `test-mode.js` — chạy `continueSession` lần lượt; hỗ trợ sửa hội thoại rồi mô phỏng lại.

Không có rule riêng: dùng chung `ReflectionEngine` như phiên thật.

---

## 11. Sửa tin nhắn trong Suy ngẫm

**File:** `reflection-engine.js` → `editUserMessage`, `replaySessionFromUserIndex`

1. Cập nhật nội dung tin user  
2. **Giữ** toàn bộ tin phía sau  
3. Chạy lại `processMessage` cho mọi tin user (cập nhật ghi nhận)  
4. Cập nhật **câu người dẫn từ chỗ sửa trở đi** theo kết quả mới  

---

## 12. Cách thêm / sửa rule

| Muốn thêm… | Sửa file |
|------------|----------|
| Cảm xúc, giá trị, niềm tin | `cognitive-library.js` → `EMOTIONS` / `VALUES` / `BELIEFS` |
| Hành động, vai trò | `cognitive-library.js` → `ACTION_PATTERNS` / `IDENTITY_PATTERNS` |
| Thiên kiến | `COGNITIVE_BIASES` + `I18N_BIAS_DESCRIPTIONS` trong `i18n.js` |
| Mâu thuẫn mới | `CONTRADICTION_PATTERNS` hoặc `detectValueActionGap` / `detectOpposingBeliefs` |
| Gợi ý khám phá | `EXPLORATION_PROMPT_RULES` + `I18N_EXPLORATION_PROMPTS` (cùng `id`) |
| Câu hỏi / gợi ý UI | `i18n.js` (`I18N_REFLECTION_QUESTIONS`, `I18N_REFLECTION_SUGGESTIONS`) |
| Kịch bản thử | `test-scenarios.js` |

**Checklist sau khi sửa:**

1. Keyword **lowercase**, dùng `includes` — tránh chỉ match đầu câu  
2. i18n **vi + en** nếu là chuỗi hiển thị  
3. `node --check <file>.js`  
4. Thử mô phỏng kịch bản hoặc sửa hội thoại trong Thử nghiệm  

---

## 13. Hạn chế hiện tại (cố ý)

- Không hiểu câu đồng nghĩa ngoài từ điển keyword  
- Phủ định chỉ xử lý đơn giản (`không/chưa/đừng` ngay trước keyword); câu phủ định phức tạp hoặc đùa vẫn có thể khớp sai  
- Mỗi tin chỉ lấy **2–3** ghi nhận nổi bật nhất  
- Mở rộng tương lai: thay `processMessage()` bằng API LLM, giữ interface `{ extracted, nextQuestion, flowStep }` (ghi chú trong `reflection-engine.js`)

---

## 14. Sơ đồ luồng tổng quát

```
User nhập text
    │
    ▼
SafetyEngine (khủng hoảng?)
    │
    ▼
ReflectionEngine.processMessage
    ├─ matchFromLibrary → EMOTIONS / VALUES / BELIEFS / …
    ├─ heuristics → Interpretation, Belief
    ├─ CognitiveTree.upsertNode → Bản đồ suy nghĩ
    └─ generateQuestion → Câu hỏi tiếp theo
    │
    ▼
InsightEngine.analyze (khi cần)
    ├─ ContradictionEngine
    ├─ bias từ session gần đây
    └─ EXPLORATION_PROMPT_RULES → Gợi ý suy ngẫm tiếp
```

---

*Cập nhật theo codebase Cognitive OS — vanilla JS, LocalStorage.*
