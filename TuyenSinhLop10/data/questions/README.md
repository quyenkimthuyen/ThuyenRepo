# Question Seed Data

Bộ dữ liệu này gồm 2.100 câu hỏi AI-generated theo ma trận ôn thi tuyển sinh lớp 10 TP.HCM, đã tái phân bổ theo blueprint rút từ đề thật TP.HCM 2022-2026:

- `math.jsonl`: 600 câu Toán.
- `literature.jsonl`: 600 câu Ngữ văn.
- `english.jsonl`: 900 câu Tiếng Anh.

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
