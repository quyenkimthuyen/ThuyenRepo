# Web HTML App

Đây là bản prototype web frontend tĩnh hoàn toàn bằng HTML/CSS/JavaScript cho ứng dụng ôn thi tuyển sinh lớp 10 TP.HCM. App không cần backend, không cần database runtime và không cần framework.

## File Chính

- `index.html`: giao diện chính.
- `styles.css`: thiết kế responsive xanh dương, trắng, cam nhấn.
- `questions-data.js`: đóng gói 2.100 câu hỏi ngay trong frontend.
- `app.js`: lọc câu hỏi, luyện tập, thi thử mô phỏng và phân tích phiên học.

## Cách Chạy

Có thể mở trực tiếp:

```text
C:\Work\ThuyenRepo\TuyenSinhLop10\Toan\web-html\index.html
```

Hoặc chạy bằng server tĩnh để mô phỏng môi trường deploy:

Từ thư mục `C:\Work\ThuyenRepo\TuyenSinhLop10\Toan`:

```powershell
python -m http.server 8000
```

Sau đó mở:

```text
http://localhost:8000/web-html/
```

Vì dữ liệu đã nằm trong `questions-data.js`, app vẫn chạy khi mở bằng `file://`.

## Deploy Static Hosting

Có thể deploy nguyên thư mục `web-html/` lên Netlify, Vercel Static, GitHub Pages hoặc bất kỳ hosting tĩnh nào. Entry point là `index.html`.

## Phạm Vi Prototype

- Dashboard học tập.
- Lọc câu hỏi theo môn, chuyên đề, mức độ.
- Luyện câu hỏi và xem đáp án/lời giải/mẹo.
- Thi thử mô phỏng theo cấu trúc TP.HCM.
- Phân tích nhanh trong phiên hiện tại.

## Bước Tiếp Theo

- Thêm lưu tiến độ bằng localStorage nếu vẫn muốn frontend-only.
- Chuyển prototype sang Next.js/NestJS nếu cần sản phẩm production.
