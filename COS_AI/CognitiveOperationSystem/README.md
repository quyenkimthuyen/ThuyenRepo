# Nhìn lại suy nghĩ (Cognitive OS)

Ứng dụng web ghi nhận và sắp xếp suy nghĩ theo framework **EEIBVIA** (7 bước): Event → Emotion → Interpretation → Belief → Value → Identity → Action.

Dữ liệu lưu trên **localStorage** (chỉ trên thiết bị của bạn).

---

## Mở app

**Cách 1 — Live Server (VS Code / Cursor)**

1. Mở thư mục project trong editor.
2. Mở `index.html` → chạy **Live Server** (port mặc định thường là `5500`).
3. Trình duyệt: `http://127.0.0.1:5500`

**Cách 2 — Python**

```bash
cd /path/to/CognitiveOperationSystem
python3 -m http.server 5500
```

Mở `http://localhost:5500`

---

## Hai chế độ phản hồi

| Chế độ | Khi nào dùng | Cần gì |
|--------|--------------|--------|
| **Rule engine (offline)** | Mặc định, không cần mạng | Chỉ mở `index.html` |
| **Cursor AI** | Test hội thoại tự nhiên hơn | Proxy local + `CURSOR_API_KEY` |

Cấu hình trên **Trang chủ** → khung **Chế độ phản hồi**.

- **Rule engine**: match từ khóa + câu hỏi mẫu (không gọi AI).
- **Cursor AI**: câu hỏi do AI sinh qua proxy; ghi nhận node vẫn dùng rule engine; nếu AI lỗi → tự fallback rule engine.

> API key **không** lưu trong browser. Key chỉ đặt trên máy dev qua biến môi trường khi chạy proxy.

---

## Thiết lập Cursor AI (lần đầu)

### Bước 1 — Lấy API key

1. Vào [Cursor Dashboard → Integrations](https://cursor.com/dashboard/integrations) (hoặc Cloud Agents → API Keys).
2. Tạo **User API key** (dạng `cursor_...`).
3. Billing theo usage trên tài khoản Cursor của bạn.

> Tài khoản **ChatGPT Plus** hoặc gói Cursor IDE **không thay thế** API key này.

### Bước 2 — Cài và chạy proxy

Mở **terminal riêng** (giữ chạy trong lúc dùng AI):

```bash
cd server
npm install --registry https://registry.npmjs.org
export CURSOR_API_KEY="cursor_YOUR_KEY_HERE"
npm start
```

Kết quả mong đợi:

```text
[reflect-server] http://localhost:3001
[reflect-server] CURSOR_API_KEY: set
```

**Tùy chọn:**

```bash
export AI_SERVER_PORT=3001          # đổi port proxy
export CURSOR_MODEL=composer-2.5    # đổi model
npm run dev                         # tự reload khi sửa server
```

### Bước 3 — Bật AI trong app

1. Mở app (`http://localhost:5500` hoặc Live Server).
2. Trang chủ → **Chế độ phản hồi** → chọn **Cursor AI**.
3. Proxy URL: `http://localhost:3001` (mặc định).
4. Bấm **Kiểm tra kết nối**:
   - Pill **Proxy sẵn sàng** = OK
   - **Thiếu CURSOR_API_KEY** = chưa `export` key trước `npm start`
   - **Không kết nối được** = proxy chưa chạy hoặc sai URL/port
5. **Bắt đầu suy ngẫm** — badge **Cursor AI** hiện ở phiên suy ngẫm.

### Bước 4 — Dùng hàng ngày (tóm tắt)

```text
Terminal 1:  cd server && export CURSOR_API_KEY="..." && npm start
Terminal 2:  (hoặc Live Server) mở app
App:         Home → Cursor AI → Kiểm tra kết nối → Bắt đầu suy ngẫm
```

---

## Chế độ Thử nghiệm (Test Mode)

Tab **Thử nghiệm** — kịch bản mẫu để tham khảo và mô phỏng.

| Nút | Việc làm |
|-----|----------|
| **Điền vào Home** | Copy suy nghĩ ban đầu vào ô Home |
| **Mô phỏng** | Chạy hội thoại tự động (có delay) |
| **Mô phỏng nhanh** | Chạy ngay, không delay |
| **Khôi phục dữ liệu cũ** | Sau mô phỏng, trả lại data trước khi chạy |

> Mô phỏng **luôn dùng rule engine** (`forceRule`), không gọi Cursor — để kết quả ổn định khi test.

Thêm kịch bản: chỉnh file `test-scenarios.js` (push object vào mảng `TEST_SCENARIOS`).

---

## Cấu trúc file quan trọng

```text
index.html              # UI chính
app.js                  # Điều phối màn hình
reflection-engine.js    # Rule engine + tích hợp AI
ai-client.js            # Gọi proxy từ browser
data.js                 # LocalStorage (settings: reflectionMode, cursorProxyUrl)
cognitive-library.js    # EEIBVIA, từ khóa, mâu thuẫn
test-scenarios.js       # Kịch bản test
test-mode.js            # Engine mô phỏng

server/
  reflect-server.mjs    # Proxy Cursor AI
  package.json          # @cursor/sdk, express
```

### Settings lưu trong browser

```json
{
  "reflectionMode": "rule",
  "cursorProxyUrl": "http://localhost:3001"
}
```

- `reflectionMode`: `"rule"` | `"cursor"`
- Đổi mode trên UI → tự lưu localStorage.

---

## API proxy (tham khảo)

**Health check**

```bash
curl http://localhost:3001/api/health
```

Response mẫu:

```json
{ "ok": true, "hasKey": true, "model": "composer-2.5" }
```

**Reflect** (app gọi nội bộ)

```http
POST /api/reflect
Content-Type: application/json

{
  "message": "Tôi cảm thấy lo lắng...",
  "session": { "initialThought": "...", "flowStep": "Emotion", "messages": [] },
  "locale": "vi",
  "phase": "continue"
}
```

---

## Xử lý sự cố

| Triệu chứng | Nguyên nhân thường gặp | Cách xử lý |
|-------------|------------------------|------------|
| Không kết nối được proxy | Server chưa chạy | `cd server && npm start` |
| Thiếu CURSOR_API_KEY | Chưa export key | `export CURSOR_API_KEY="cursor_..."` rồi chạy lại `npm start` |
| `npm install` lỗi 404 | Registry npm nội bộ | `npm install --registry https://registry.npmjs.org` |
| AI chậm / timeout | Agent Cursor nặng | Dùng rule engine hoặc thử lại; kiểm tra mạng |
| Toast “đã dùng rule engine” | Proxy lỗi tạm thời | Xem log terminal proxy; kiểm tra key và quota |
| CORS lỗi | App và proxy khác origin lạ | Proxy đã bật CORS; dùng `localhost` nhất quán |
| Test Mode không giống AI | By design | Test Mode cố ý dùng rule engine |

**Xem log proxy:** terminal đang chạy `npm start`.

**Xóa dữ liệu app:** Trang chủ → **Xóa dữ liệu và bắt đầu lại** (giữ ngôn ngữ và cài đặt AI).

---

## Ngôn ngữ

Góc trên nav: **VI** / **EN**. Cài đặt lưu trong `settings.locale`.

---

## Lưu ý bảo mật

- Không commit `CURSOR_API_KEY` vào git.
- Không deploy proxy ra internet công khai mà không bảo vệ (auth, HTTPS).
- Dùng cho **dev / test cá nhân**; production nên có backend riêng và quản lý key an toàn.

---

## Phát triển tiếp (gợi ý)

- Thay `reflect-server.mjs` bằng deploy backend khi có nhiều user.
- Mở rộng `test-scenarios.js` cho domain khác (công việc, tài chính, sức khỏe).
- Tích hợp AI cho Insight / Contradiction (hiện chủ yếu ở phiên Suy ngẫm).

---

## Cursor rules (chất lượng khi cập nhật)

Thư mục `.cursor/rules/` — Cursor IDE tự đọc khi bạn sửa project:

| File | Áp dụng |
|------|---------|
| `cognitive-os-quality.mdc` | Luôn — checklist QA, kiến trúc, lệnh test nhanh |
| `cognitive-os-i18n.mdc` | Khi sửa `i18n.js`, `index.html`, `app.js` |
| `cognitive-os-ai-server.mdc` | Khi sửa proxy / AI / reflection engine |

Mở project trong **Cursor** → agent sẽ tuân rules này mỗi lần bạn nhờ cập nhật code.

---

*Tài liệu cập nhật: tháng 6/2026 — sau khi thêm chế độ Cursor AI + Test Mode.*
