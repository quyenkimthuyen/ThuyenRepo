# Question Seed Data

Bộ dữ liệu gồm 2.100 câu theo ma trận ôn thi tuyển sinh lớp 10 TP.HCM, cộng thêm 280 câu Cấu trúc câu (lớp 10-12) trong ngân hàng luyện tập Tiếng Anh:

- `math.jsonl`: 600 câu Toán.
- `literature.jsonl`: 600 câu Ngữ văn.
- `english.jsonl`: 1.180 câu Tiếng Anh (900 câu ma trận TS10 + 280 câu Cấu trúc câu lớp 10-12).
- `english-cautruc.jsonl`: bản tách 280 câu chuyên đề `CauTrucCau` (mức vận dụng cao).

Mỗi dòng là một JSON object hợp lệ theo `question.schema.json`. Các câu này là dữ liệu seed/mẫu để phát triển sản phẩm, cần giáo viên kiểm duyệt trước khi sử dụng trong môi trường thương mại.

## Định Hướng Theo Đề Thật

- Toán ưu tiên `HinhHocPhang`, `ToanThucTe`, `PhuongTrinhBacHai`, `XacSuatThongKe`, đồng thời giữ đủ câu nền cho parabol, đồ thị, hình học thực tế và đường tròn.
- Ngữ văn ưu tiên đọc hiểu ngữ liệu ngoài SGK, thông điệp, viết đoạn/bài nghị luận xã hội, dẫn chứng, sửa lỗi diễn đạt và nghị luận văn học.
- Tiếng Anh ưu tiên `WordForms`, `SentenceTransformation`, `ReadingComprehension`, `ClozeTest`, nhưng vẫn giữ đủ ngữ âm, trọng âm, ngữ pháp và giao tiếp để dựng đề 40 câu.
- Các trường mở rộng như `examPart`, `realExamPattern`, `examPriority`, `examYears` giúp UI và diagnostic biết câu hỏi đang phục vụ phần nào của đề thật.

## Mức Độ

- `NhanBiet`: nhận diện kiến thức, công thức, thông tin trực tiếp.
- `ThongHieu`: giải thích, áp dụng công thức cơ bản, hiểu ý nghĩa.
- `VanDung`: giải bài có ngữ cảnh, kết hợp 2-3 bước.
- `VanDungCao`: câu phân loại, lập luận hoặc tổng hợp nhiều kỹ năng.

## Quy Ước Nguồn

`nguon` mặc định là `AI-generated theo ma trận TP.HCM`. Không trộn với đề chính thức nếu chưa có quyền sử dụng.
