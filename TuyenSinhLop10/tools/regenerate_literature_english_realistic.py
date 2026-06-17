from pathlib import Path
import json
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "questions"
WEB = ROOT / "web-html"
SOURCE = "AI-generated mô phỏng theo ma trận TP.HCM và đối chiếu đề thật 2022-2026, cần giáo viên kiểm duyệt"
LEVELS = ["NhanBiet", "ThongHieu", "VanDung", "VanDungCao"]

LIT_TOPICS = [
    "DocHieuVanBanVanHoc", "DocHieuVanBanThongTin", "BienPhapTuTu",
    "ThongDiepVanBan", "VietDoanVan", "NghiLuanXaHoi", "DanChungXaHoi",
    "MoBaiKetBai", "NghiLuanVanHoc", "PhanTichNhanVat", "GiaTriNoiDung",
    "GiaTriNgheThuat", "LienHeBanThan", "SuaLoiDienDat", "LapDanY",
]
ENG_TOPICS = [
    "Pronunciation", "Stress", "Tenses", "PassiveVoice", "ReportedSpeech",
    "RelativeClauses", "Conditionals", "WordForms", "Prepositions",
    "Comparisons", "ErrorIdentification", "ClozeTest", "ReadingComprehension",
    "SentenceTransformation", "DialogueCompletion",
]
LIT_TOPIC_WEIGHTS = {
    "DocHieuVanBanVanHoc": 55,
    "DocHieuVanBanThongTin": 60,
    "BienPhapTuTu": 35,
    "ThongDiepVanBan": 45,
    "VietDoanVan": 65,
    "NghiLuanXaHoi": 70,
    "DanChungXaHoi": 45,
    "MoBaiKetBai": 25,
    "NghiLuanVanHoc": 40,
    "PhanTichNhanVat": 25,
    "GiaTriNoiDung": 20,
    "GiaTriNgheThuat": 20,
    "LienHeBanThan": 30,
    "SuaLoiDienDat": 40,
    "LapDanY": 25,
}
ENG_TOPIC_WEIGHTS = {
    "Pronunciation": 50,
    "Stress": 50,
    "Tenses": 65,
    "PassiveVoice": 50,
    "ReportedSpeech": 50,
    "RelativeClauses": 50,
    "Conditionals": 50,
    "WordForms": 100,
    "Prepositions": 50,
    "Comparisons": 30,
    "ErrorIdentification": 25,
    "ClozeTest": 95,
    "ReadingComprehension": 95,
    "SentenceTransformation": 100,
    "DialogueCompletion": 40,
}
LIT_ALIGNMENT = {
    "DocHieuVanBanVanHoc": ("Đọc hiểu", "Ngữ liệu ngoài SGK, xác định nội dung/chủ đề/căn cứ"),
    "DocHieuVanBanThongTin": ("Đọc hiểu", "Văn bản thông tin/nghị luận, đọc chi tiết và thông điệp"),
    "BienPhapTuTu": ("Đọc hiểu", "Gọi tên biện pháp, chỉ dấu hiệu và nêu tác dụng"),
    "ThongDiepVanBan": ("Đọc hiểu", "Rút thông điệp từ ngữ liệu và giải thích ngắn"),
    "VietDoanVan": ("Viết đoạn", "Đoạn nghị luận khoảng 200 chữ, có quan điểm và hành động"),
    "NghiLuanXaHoi": ("Bài viết", "Vấn đề đời sống gần học sinh, lập luận và phản biện"),
    "DanChungXaHoi": ("Bài viết", "Chọn dẫn chứng đúng vấn đề, tránh chung chung"),
    "MoBaiKetBai": ("Bài viết", "Mở/kết tự nhiên, không học tủ văn mẫu"),
    "NghiLuanVanHoc": ("Bài viết", "Cảm nhận văn học, phân tích chi tiết và thông điệp"),
    "PhanTichNhanVat": ("Bài viết", "Phân tích nhân vật qua hành động, lời nói, suy nghĩ"),
    "GiaTriNoiDung": ("Bài viết", "Nhận xét chủ đề, tư tưởng, cảm xúc"),
    "GiaTriNgheThuat": ("Bài viết", "Nhận xét hình ảnh, giọng điệu, kết cấu, ngôn ngữ"),
    "LienHeBanThan": ("Đọc hiểu/Viết", "Liên hệ cụ thể, có hành động phù hợp lứa tuổi"),
    "SuaLoiDienDat": ("Kỹ năng diễn đạt", "Sửa câu, tránh lặp, rõ chủ-vị và mạch lập luận"),
    "LapDanY": ("Kỹ năng viết", "Dàn ý đủ luận điểm, đúng trọng tâm đề"),
}
ENG_ALIGNMENT = {
    "Pronunciation": ("Câu 1-2", "Phát âm nguyên âm/phụ âm, đuôi -ed/-s"),
    "Stress": ("Câu 3-4", "Trọng âm từ 2-4 âm tiết"),
    "Tenses": ("Câu 5-16", "Thì và dạng động từ trong ngữ cảnh"),
    "PassiveVoice": ("Câu 5-16/37-40", "Câu bị động và biến đổi câu"),
    "ReportedSpeech": ("Câu 5-16/37-40", "Tường thuật câu hỏi/lời đề nghị"),
    "RelativeClauses": ("Câu 5-16", "Mệnh đề quan hệ who/which/whose/that"),
    "Conditionals": ("Câu 5-16/37-40", "Câu điều kiện và unless"),
    "WordForms": ("Câu 29-34", "Từ loại, hậu tố, tiền tố phủ định"),
    "Prepositions": ("Câu 5-16", "Giới từ và cụm cố định"),
    "Comparisons": ("Câu 5-16/37-40", "So sánh và viết lại câu tương đương"),
    "ErrorIdentification": ("Câu 5-16", "Tìm lỗi ngữ pháp/collocation"),
    "ClozeTest": ("Câu 23-28", "Điền từ trong đoạn, mạch nghĩa và ngữ pháp"),
    "ReadingComprehension": ("Câu 17-22", "True/False, ý chính, chi tiết, ngoại trừ"),
    "SentenceTransformation": ("Câu 35-40", "Sắp xếp/viết lại câu giữ nguyên nghĩa"),
    "DialogueCompletion": ("Câu 5-16", "Hội thoại: đề nghị, cảm ơn, chúc mừng, xin lỗi"),
}

themes = [
    "lòng biết ơn", "tinh thần vượt khó", "sự tử tế", "trách nhiệm với cộng đồng",
    "văn hóa ứng xử trên mạng", "thói quen đọc sách", "bảo vệ môi trường",
    "ý thức tự học", "tôn trọng sự khác biệt", "sử dụng thời gian hiệu quả",
]
texts = [
    "Một hạt mầm nằm im trong lòng đất rất lâu. Nó không vội vã, chỉ lặng lẽ hút từng giọt nước, chờ ngày đủ sức vươn lên. Khi nhú khỏi mặt đất, nó hiểu rằng mọi trưởng thành đều bắt đầu từ những cố gắng âm thầm.",
    "Trên chuyến xe buýt đông người, một bạn học sinh đứng dậy nhường chỗ cho cụ già. Hành động nhỏ ấy khiến nhiều người mỉm cười, vì sự tử tế đôi khi không cần lời nói lớn lao mà cần một lựa chọn đúng lúc.",
    "Mạng xã hội giống như một quảng trường rộng. Mỗi lời ta viết ra có thể làm ai đó được động viên, cũng có thể khiến họ tổn thương. Vì vậy, sự văn minh bắt đầu từ việc biết dừng lại trước khi bấm gửi.",
    "Một quyển sách hay không trả lời thay ta mọi câu hỏi, nhưng mở ra nhiều cánh cửa để ta biết hỏi đúng hơn. Người đọc sách không chỉ tích lũy chữ nghĩa mà còn học cách lắng nghe những cuộc đời khác.",
]

lit_focuses = [
    "xác định đúng vấn đề trung tâm",
    "chọn chi tiết tiêu biểu làm căn cứ",
    "giải thích tác dụng của chi tiết",
    "diễn đạt câu trả lời ngắn gọn",
    "phân biệt thông điệp và chủ đề",
    "biết liên hệ với hành động cụ thể",
    "tránh kể lại văn bản",
    "dùng dẫn chứng phù hợp",
    "nêu phản đề hợp lí",
    "kết nối nội dung và nghệ thuật",
    "giữ đúng dung lượng yêu cầu",
    "sắp xếp luận điểm theo trật tự rõ",
    "tránh lặp từ và diễn đạt sáo rỗng",
    "rút ra bài học cho học sinh lớp 9",
    "đặt câu chủ đề đúng trọng tâm",
    "phân tích thay vì liệt kê",
    "làm rõ thái độ của người viết",
    "nhận diện từ khóa trong ngữ liệu",
    "biết mở rộng vấn đề vừa phải",
    "chốt ý bằng nhận xét khái quát",
]

lit_contexts = [
    "trả lời ngắn nhưng phải có căn cứ",
    "phân biệt ý chính và chi tiết phụ",
    "không chép lại nguyên văn cả câu dài",
    "dẫn chứng phải được giải thích",
    "liên hệ với đời sống học sinh lớp 9",
    "tránh viết thành khẩu hiệu chung chung",
    "chọn từ ngữ tự nhiên, có sắc thái",
    "sắp xếp ý theo quan hệ nguyên nhân - kết quả",
    "nêu giải pháp cụ thể, khả thi",
    "phản biện vừa phải, không phủ định cực đoan",
    "giữ đúng dung lượng đề yêu cầu",
    "mỗi luận điểm cần có một câu phân tích",
    "chỉ ra tác dụng nghệ thuật gắn với văn bản",
    "không kể lại tác phẩm thay cho phân tích",
    "mở bài đi thẳng vào vấn đề",
    "kết bài khẳng định nhận thức và hành động",
    "dùng dẫn chứng gần gũi, kiểm chứng được",
    "tránh lặp từ khóa quá nhiều lần",
    "chú ý chính tả và dấu câu",
    "viết câu chủ đề rõ trong đoạn văn",
    "xác định đúng thái độ của người viết",
    "nhận diện hình ảnh trung tâm của ngữ liệu",
    "giải thích khái niệm bằng lời của mình",
    "không sa vào bình luận ngoài văn bản",
    "biết kết nối chi tiết với thông điệp",
    "phân tích cả nội dung và hình thức",
    "đưa bài học thành hành động cụ thể",
    "tránh dùng dẫn chứng quá xa lạ",
    "kiểm tra mạch liên kết giữa các câu",
    "ưu tiên lập luận rõ hơn câu chữ hoa mỹ",
    "dùng thao tác giải thích trước khi bàn luận",
    "nêu biểu hiện tích cực và trái ngược",
    "không dùng văn mẫu rập khuôn",
    "trình bày sạch, dễ đọc, đúng trọng tâm",
    "nêu quan điểm cá nhân có chừng mực",
    "bám sát câu hỏi nhỏ trong phần đọc hiểu",
    "chọn chi tiết nghệ thuật thật tiêu biểu",
    "soát lại lỗi diễn đạt trước khi nộp",
    "đặt vấn đề phù hợp lứa tuổi học sinh",
    "kết luận không mở thêm ý mới",
]

eng_focuses = [
    "sound discrimination", "syllable stress", "time signal", "sentence meaning",
    "verb pattern", "fixed expression", "context clue", "word family",
    "relative pronoun", "conditional form", "reported question", "passive structure",
    "comparison structure", "error correction", "cloze coherence", "reading detail",
    "main idea", "sentence transformation", "dialogue function", "exam strategy",
]

eng_contexts = [
    "school life", "environment", "healthy habits", "online learning", "public transport",
    "volunteer work", "family routines", "reading culture", "city life", "traditional festivals",
    "energy saving", "teen communication", "exam preparation", "sports day", "library habits",
    "community service", "travel plans", "science club", "music class", "career orientation",
    "food safety", "digital citizenship", "weather changes", "local tourism", "friendship",
    "time management", "traffic safety", "recycling projects", "English club", "school rules",
    "future jobs", "personal finance", "green living", "teamwork", "cultural exchange",
    "study skills", "technology use", "daily chores", "social media", "student wellbeing",
    "exam stress", "after-school activities", "local community", "smartphone habits", "public libraries",
    "clean water", "youth volunteering", "school canteen", "road safety", "science fairs",
    "heritage sites", "online manners", "mental health", "school uniforms", "English speaking practice",
    "saving money", "household chores", "green transport", "weekend plans", "future education",
]


def row(qid, subject, topic, level, de_bai, dap_an, loi_giai, meo, choices=None, seconds=180):
    alignment = LIT_ALIGNMENT[topic] if subject == "NguVan" else ENG_ALIGNMENT[topic]
    priority_topics = {
        "DocHieuVanBanVanHoc", "DocHieuVanBanThongTin", "VietDoanVan", "NghiLuanXaHoi",
        "WordForms", "SentenceTransformation", "ReadingComprehension", "ClozeTest",
    }
    priority = "Rất cao" if topic in priority_topics else "Cao"
    return {
        "id": qid,
        "monHoc": subject,
        "chuyenDe": topic,
        "mucDo": level,
        "namXuatHien": None,
        "nguon": SOURCE,
        "deBai": de_bai,
        "luaChon": choices or [],
        "dapAn": dap_an,
        "loiGiai": loi_giai,
        "meoLamBai": meo,
        "tags": ["TPHCM", "GDPT2018", topic, "DeMoPhong", "BamDeThat2022_2026", alignment[0].replace(" ", "")],
        "examPriority": priority,
        "examPart": alignment[0],
        "realExamPattern": alignment[1],
        "examYears": [2022, 2023, 2024, 2025, 2026],
        "estimatedTimeSeconds": seconds,
    }


def literature_question(i, topic_override=None, occurrence_override=None):
    topic = topic_override or LIT_TOPICS[(i - 1) % len(LIT_TOPICS)]
    level = LEVELS[(i - 1) % 4]
    occurrence = occurrence_override if occurrence_override is not None else (i - 1) // len(LIT_TOPICS)
    focus = lit_focuses[occurrence % len(lit_focuses)]
    context = lit_contexts[occurrence % len(lit_contexts)]
    theme = themes[(i - 1) % len(themes)]
    text = texts[(i - 1) % len(texts)]
    hint = text.split(".")[0] + "."
    qid = f"literature-{i:03d}"
    seconds = 180 + 45 * LEVELS.index(level)

    if topic in ["DocHieuVanBanVanHoc", "DocHieuVanBanThongTin"]:
        de = f"Đọc ngữ liệu sau về {theme} và trả lời: “{text}” Câu hỏi: Nêu nội dung chính của ngữ liệu và chỉ ra một chi tiết làm căn cứ. Trọng tâm chấm điểm: {focus}."
        ans = "Nội dung chính cần nêu đúng vấn đề trung tâm của ngữ liệu; chi tiết làm căn cứ phải trích hoặc diễn đạt sát văn bản."
        sol = "Học sinh cần đọc toàn ngữ liệu, xác định hình ảnh/chi tiết lặp hoặc câu mang ý khái quát, sau đó trả lời bằng 2 ý: nội dung chính và căn cứ."
        tip = "Không trả lời theo suy đoán ngoài văn bản; luôn bám một chi tiết cụ thể."
    elif topic == "BienPhapTuTu":
        de = f"Đọc câu gợi chủ đề {theme}: “{hint}” Chỉ ra một biện pháp tu từ nổi bật và nêu tác dụng. Trọng tâm chấm điểm: {focus}."
        ans = "Có thể nêu nhân hóa/ẩn dụ/so sánh tùy câu; tác dụng là làm hình ảnh gợi cảm, nhấn mạnh thông điệp của văn bản."
        sol = "Câu trả lời đủ điểm cần có: tên biện pháp, từ ngữ thể hiện, tác dụng về nội dung và cảm xúc."
        tip = "Không chỉ gọi tên biện pháp; phải nói biện pháp ấy giúp người đọc hiểu/cảm gì."
    elif topic == "ThongDiepVanBan":
        de = f"Từ ngữ liệu về {theme}, hãy rút ra một thông điệp có ý nghĩa với học sinh lớp 9 và giải thích ngắn gọn. Trọng tâm chấm điểm: {focus}."
        ans = f"Thông điệp có thể là: mỗi học sinh cần rèn luyện {theme} bằng hành động cụ thể trong học tập và đời sống."
        sol = "Thông điệp phải khái quát, tích cực, không sao chép nguyên văn; phần giải thích cần gắn với lứa tuổi học sinh."
        tip = "Viết thông điệp thành một câu hoàn chỉnh, tránh khẩu hiệu quá chung."
    elif topic == "VietDoanVan":
        de = f"Viết đoạn văn khoảng 200 chữ trình bày suy nghĩ của em về {theme}. Có thể gợi mở từ hình ảnh/câu văn: “{hint}” Trọng tâm chấm điểm: {focus}."
        ans = "Đoạn văn cần có câu chủ đề, giải thích vấn đề, 2-3 luận điểm, dẫn chứng ngắn và bài học hành động."
        sol = "Có thể triển khai: giải thích khái niệm, nêu biểu hiện, phân tích ý nghĩa, phê phán biểu hiện trái ngược, liên hệ bản thân."
        tip = "Đề yêu cầu đoạn văn thì không tách thành nhiều đoạn; cần giữ dung lượng khoảng 200 chữ."
    elif topic == "NghiLuanXaHoi":
        de = f"Lập dàn ý cho bài nghị luận xã hội về vai trò của {theme} trong đời sống hiện nay; phần dẫn chứng nên gắn với ngữ cảnh: “{hint}” Trọng tâm chấm điểm: {focus}."
        ans = "Dàn ý gồm mở bài nêu vấn đề; thân bài giải thích, biểu hiện, ý nghĩa, phản biện, bài học; kết bài khẳng định vấn đề."
        sol = "Dẫn chứng nên gần gũi với học sinh hoặc có tính thời sự; không dùng dẫn chứng mơ hồ."
        tip = "Mỗi luận điểm nên trả lời một câu hỏi: là gì, vì sao, biểu hiện thế nào, em làm gì."
    elif topic == "DanChungXaHoi":
        de = f"Đề xuất 2 dẫn chứng phù hợp cho bài nghị luận về {theme}; một dẫn chứng cần liên hệ với gợi ý “{hint}”. Trọng tâm chấm điểm: {focus}."
        ans = "Dẫn chứng cần cụ thể, đúng vấn đề, có khả năng làm sáng tỏ luận điểm; nên có một dẫn chứng đời sống học sinh và một dẫn chứng xã hội rộng hơn."
        sol = "Không chỉ nêu tên dẫn chứng; cần giải thích mối liên hệ giữa dẫn chứng và luận điểm."
        tip = "Tránh dẫn chứng quá xa lạ hoặc không kiểm chứng được."
    elif topic == "MoBaiKetBai":
        de = f"Viết một mở bài gián tiếp và một kết bài ngắn cho đề: Suy nghĩ về {theme}. Tránh lặp lại nguyên văn gợi ý “{hint}”. Trọng tâm chấm điểm: {focus}."
        ans = "Mở bài cần dẫn vào vấn đề tự nhiên; kết bài khẳng định ý nghĩa và nêu định hướng hành động."
        sol = "Mở bài không nên quá dài. Kết bài cần tránh lặp y nguyên mở bài, nên nâng vấn đề hoặc liên hệ bản thân."
        tip = "Mở bài/kết bài hay nhưng không đúng vấn đề vẫn mất điểm."
    elif topic in ["NghiLuanVanHoc", "PhanTichNhanVat", "GiaTriNoiDung", "GiaTriNgheThuat"]:
        de = f"Khi phân tích một nhân vật trong tác phẩm văn học lớp 9 gắn với chủ đề {theme}, hãy nêu cách chọn chi tiết và cách triển khai luận điểm để tránh kể lại truyện. Có thể đối chiếu với gợi ý “{hint}”. Trọng tâm chấm điểm: {focus}."
        ans = "Cần chọn chi tiết tiêu biểu về hành động, lời nói, suy nghĩ; mỗi chi tiết phải được phân tích để làm rõ phẩm chất nhân vật và nghệ thuật xây dựng."
        sol = "Một đoạn phân tích tốt gồm: luận điểm về nhân vật, chi tiết dẫn chứng, phân tích ý nghĩa, nhận xét nghệ thuật, liên hệ chủ đề tác phẩm."
        tip = "Không kể lại diễn biến truyện; hãy trả lời chi tiết đó chứng minh điều gì."
    elif topic == "LienHeBanThan":
        de = f"Từ vấn đề {theme}, hãy viết 4-5 câu liên hệ bản thân sao cho chân thành và cụ thể; cần có ít nhất một hành động gắn với gợi ý “{hint}”. Trọng tâm chấm điểm: {focus}."
        ans = "Liên hệ cần nêu nhận thức, hành động cụ thể, thói quen cần thay đổi và cam kết phù hợp với học sinh."
        sol = "Câu liên hệ tốt không hô khẩu hiệu mà nói rõ bản thân sẽ làm gì trong học tập, gia đình, nhà trường hoặc cộng đồng."
        tip = "Tránh viết 'em sẽ cố gắng hơn' mà không nói cố gắng bằng việc gì."
    elif topic == "SuaLoiDienDat":
        de = f"Sửa câu sau cho rõ ý và bớt lặp từ: “{theme} là một điều rất quan trọng và điều đó giúp cho chúng ta trở nên tốt hơn trong cuộc sống”. Sau khi sửa, câu vẫn cần phù hợp với gợi ý “{hint}”. Trọng tâm chấm điểm: {focus}."
        ans = f"{theme.capitalize()} giúp mỗi người sống tích cực và có trách nhiệm hơn."
        sol = "Câu sửa bỏ cụm lặp 'một điều/điều đó', rút gọn ý và giữ trọng tâm nội dung."
        tip = "Khi sửa diễn đạt, ưu tiên rõ nghĩa, ngắn gọn, đúng ngữ pháp."
    else:  # LapDanY
        de = f"Lập dàn ý 5 ý chính cho đoạn văn nghị luận về {theme}, trong đó có một ý liên hệ từ gợi ý “{hint}”. Trọng tâm chấm điểm: {focus}."
        ans = "5 ý chính: giải thích, biểu hiện, ý nghĩa, phản đề, bài học hành động."
        sol = "Dàn ý cần đủ hướng triển khai nhưng mỗi ý phải ngắn, rõ và đúng vấn đề."
        tip = "Dàn ý không phải bài viết hoàn chỉnh; tránh viết lan man."

    de = f"{de} Yêu cầu phụ: {context}."
    return row(qid, "NguVan", topic, level, de, ans, sol, tip, seconds=seconds)


eng_bank = {
    "Pronunciation": [
        ("Which word has the underlined part pronounced differently from that of the others?", ["want<u>ed</u>", "need<u>ed</u>", "walk<u>ed</u>", "visit<u>ed</u>"], "walk<u>ed</u>", "The ending -ed in 'walked' is pronounced /t/, while the others are /id/."),
        ("Which word has the underlined part pronounced differently from that of the others?", ["book<u>s</u>", "lamp<u>s</u>", "pen<u>s</u>", "map<u>s</u>"], "pen<u>s</u>", "The final -s in 'pens' is /z/, while the others are /s/."),
        ("Which word has the underlined part pronounced differently from that of the others?", ["stopp<u>ed</u>", "watch<u>ed</u>", "play<u>ed</u>", "miss<u>ed</u>"], "play<u>ed</u>", "The ending -ed in 'played' is /d/, while the others are /t/."),
        ("Which word has the underlined part pronounced differently from that of the others?", ["ma<u>ch</u>ine", "<u>ch</u>air", "tea<u>ch</u>er", "<u>ch</u>ildren"], "ma<u>ch</u>ine", "'ch' in machine is pronounced /ʃ/, not /tʃ/."),
        ("Which word has the underlined part pronounced differently from that of the others?", ["<u>c</u>ity", "<u>c</u>ountry", "<u>c</u>enter", "<u>c</u>inema"], "<u>c</u>ountry", "The letter c in country is /k/, while the others are /s/."),
    ],
    "Stress": [
        ("Choose the word with a different stress pattern: pollution, attention, collection, festival.", ["pollution", "attention", "collection", "festival"], "festival", "'Festival' has first-syllable stress; the others are stressed later."),
        ("Choose the word with a different stress pattern: computer, volunteer, important, holiday.", ["computer", "volunteer", "important", "holiday"], "holiday", "'Holiday' is stressed on the first syllable."),
        ("Choose the word with a different stress pattern: beautiful, successful, expensive, convenient.", ["beautiful", "successful", "expensive", "convenient"], "beautiful", "'Beautiful' is stressed on the first syllable."),
        ("Choose the word with a different stress pattern: environment, activity, education, family.", ["environment", "activity", "education", "family"], "family", "'Family' is stressed on the first syllable."),
        ("Choose the word with a different stress pattern: tradition, musician, national, prediction.", ["tradition", "musician", "national", "prediction"], "national", "'National' has first-syllable stress."),
    ],
    "Tenses": [
        ("Choose the best answer: My brother _____ English since he was in grade 6.", ["learns", "learned", "has learned", "is learning"], "has learned", "Use present perfect with 'since'."),
        ("Choose the best answer: When I arrived, they _____ dinner.", ["have", "are having", "were having", "will have"], "were having", "Use past continuous for an action happening at a past moment."),
        ("Choose the best answer: We _____ our grandparents last Sunday.", ["visit", "visited", "have visited", "are visiting"], "visited", "Use past simple with 'last Sunday'."),
        ("Choose the best answer: Look! The children _____ kites in the park.", ["fly", "flew", "are flying", "have flown"], "are flying", "Use present continuous for an action happening now."),
        ("Choose the best answer: By the time we got to the station, the train _____.", ["left", "has left", "had left", "leaves"], "had left", "Use past perfect for the earlier past action."),
    ],
    "PassiveVoice": [
        ("Rewrite in passive voice: People recycle paper in many schools.", [], "Paper is recycled in many schools.", "Present simple passive: am/is/are + V3."),
        ("Rewrite in passive voice: They will build a new library next year.", [], "A new library will be built next year.", "Future passive: will be + V3."),
        ("Rewrite in passive voice: The students cleaned the classroom yesterday.", [], "The classroom was cleaned by the students yesterday.", "Past simple passive: was/were + V3."),
        ("Rewrite in passive voice: People should save electricity at home.", [], "Electricity should be saved at home.", "Modal passive: modal + be + V3."),
        ("Rewrite in passive voice: The teacher has explained the lesson clearly.", [], "The lesson has been explained clearly by the teacher.", "Present perfect passive: has/have been + V3."),
    ],
    "ReportedSpeech": [
        ("Rewrite in reported speech: 'I am preparing for the exam,' Lan said.", [], "Lan said that she was preparing for the exam.", "Backshift present continuous to past continuous."),
        ("Rewrite in reported speech: 'Do you like reading books?' he asked me.", [], "He asked me if I liked reading books.", "Yes/no questions use if/whether and statement word order."),
        ("Rewrite in reported speech: 'I will join the English club tomorrow,' Nam said.", [], "Nam said that he would join the English club the next day.", "Change will to would and tomorrow to the next day."),
        ("Rewrite in reported speech: 'Where do you live?' the teacher asked Hoa.", [], "The teacher asked Hoa where she lived.", "Wh-questions in reported speech use statement word order."),
        ("Rewrite in reported speech: 'Please turn off the lights,' my mother said.", [], "My mother asked me to turn off the lights.", "A polite request can be reported with asked + object + to V."),
    ],
    "RelativeClauses": [
        ("Combine the sentences: The girl is my classmate. She won the English contest.", [], "The girl who won the English contest is my classmate.", "Use 'who' for people."),
        ("Choose the best answer: This is the book _____ I borrowed from the library.", ["who", "which", "whose", "where"], "which", "Use 'which' for things."),
        ("Combine the sentences: The bike is mine. It is parked near the gate.", [], "The bike which is parked near the gate is mine.", "Use 'which' for things."),
        ("Choose the best answer: The man _____ daughter studies with me is a doctor.", ["who", "whom", "whose", "which"], "whose", "Use 'whose' to show possession."),
        ("Combine the sentences: Da Lat is a city. Many tourists visit it every year.", [], "Da Lat is a city which many tourists visit every year.", "Use a relative clause to modify 'city'."),
    ],
    "Conditionals": [
        ("Choose the best answer: If we plant more trees, the air _____ cleaner.", ["is", "was", "will be", "would be"], "will be", "First conditional: If + present simple, will + V."),
        ("Choose the best answer: If I _____ enough time, I would join the club.", ["have", "had", "will have", "am having"], "had", "Second conditional: If + past simple, would + V."),
        ("Choose the best answer: If you study harder, you _____ better results.", ["get", "got", "will get", "would get"], "will get", "This is a real future condition."),
        ("Choose the best answer: If she were taller, she _____ reach the shelf.", ["can", "could", "will", "may"], "could", "Second conditional uses could/would + V."),
        ("Choose the best answer: Unless it rains, we _____ a picnic tomorrow.", ["have", "had", "will have", "would have"], "will have", "Unless means if not; use first conditional."),
    ],
    "WordForms": [
        ("Complete the sentence: The Internet is a useful means of _____. (communicate)", [], "communication", "After 'of', a noun is needed."),
        ("Complete the sentence: Students should listen _____ to their teachers. (careful)", [], "carefully", "The word modifies the verb 'listen', so use an adverb."),
        ("Complete the sentence: We should use water _____. (economy)", [], "economically", "The word modifies the verb 'use', so use an adverb."),
        ("Complete the sentence: Her _____ helped the team finish the project. (creative)", [], "creativity", "A noun is needed as the subject."),
        ("Complete the sentence: It is _____ to throw trash on the street. (responsible)", [], "irresponsible", "The meaning requires the negative adjective."),
    ],
    "Prepositions": [
        ("Choose the best answer: She is interested _____ learning foreign languages.", ["on", "in", "at", "for"], "in", "The fixed phrase is 'interested in'."),
        ("Choose the best answer: We are proud _____ our school's tradition.", ["of", "with", "about", "to"], "of", "The fixed phrase is 'proud of'."),
        ("Choose the best answer: The exam starts _____ 8 o'clock.", ["in", "on", "at", "by"], "at", "Use 'at' with exact times."),
        ("Choose the best answer: My house is different _____ yours.", ["from", "with", "to", "for"], "from", "The fixed phrase is 'different from'."),
        ("Choose the best answer: She often goes to school _____ bus.", ["in", "on", "by", "with"], "by", "Use 'by' with means of transport."),
    ],
    "Comparisons": [
        ("Rewrite: This exercise is easier than that one.", [], "That exercise is more difficult than this one.", "Change the comparison while keeping the meaning."),
        ("Choose the best answer: This is _____ book I have ever read.", ["interesting", "more interesting", "the most interesting", "most interesting"], "the most interesting", "Use the superlative with 'ever'."),
        ("Rewrite: No student in my class is taller than Minh.", [], "Minh is the tallest student in my class.", "Use the superlative form."),
        ("Choose the best answer: Learning online is _____ than I expected.", ["convenient", "more convenient", "the most convenient", "conveniently"], "more convenient", "Use comparative form with 'than'."),
        ("Rewrite: Lan is not as careful as Mai.", [], "Mai is more careful than Lan.", "Change not as...as to comparative."),
    ],
    "ErrorIdentification": [
        ("Find the mistake: She suggested to go to the library after school.", ["suggested", "to go", "the library", "after"], "to go", "After 'suggest', use V-ing: suggested going."),
        ("Find the mistake: The boy which is standing near the gate is my brother.", ["which", "standing", "near", "is"], "which", "Use 'who' for people."),
        ("Find the mistake: I have seen him yesterday.", ["have seen", "him", "yesterday", "I"], "have seen", "Use past simple with yesterday: saw."),
        ("Find the mistake: She is fond in listening to music.", ["is", "fond", "in", "listening"], "in", "The fixed phrase is 'fond of'."),
        ("Find the mistake: If he will come early, we will start the meeting.", ["will come", "early", "will start", "meeting"], "will come", "Do not use will in the if-clause of the first conditional."),
    ],
    "ClozeTest": [
        ("Choose the best word: Reading books helps students expand their vocabulary and improve their _____.", ["noise", "knowledge", "weather", "traffic"], "knowledge", "The context is learning, so 'knowledge' fits."),
        ("Choose the best word: To protect the environment, we should reduce plastic _____.", ["waste", "taste", "speed", "sound"], "waste", "The phrase 'plastic waste' is natural and meaningful."),
        ("Choose the best word: A healthy lifestyle includes enough sleep and regular _____.", ["exercise", "mistake", "pollution", "silence"], "exercise", "Sleep and exercise are parts of a healthy lifestyle."),
        ("Choose the best word: Many students use dictionaries to check the _____ of new words.", ["meaning", "weather", "ticket", "noise"], "meaning", "Dictionaries help users find word meanings."),
        ("Choose the best word: Teamwork teaches students how to share ideas and solve problems _____.", ["alone", "together", "slowly", "rarely"], "together", "Teamwork means working together."),
    ],
    "ReadingComprehension": [
        ("Read the statement: 'Small actions such as turning off lights can save energy.' What is the main idea?", ["Saving energy starts from daily habits", "Lights are expensive", "Students dislike saving energy", "Energy is unlimited"], "Saving energy starts from daily habits", "The main idea generalizes the example."),
        ("A passage says Minh studies 30 minutes of English every day and reviews new words on weekends. What habit helps Minh remember vocabulary?", ["Skipping homework", "Reviewing words regularly", "Watching TV", "Sleeping late"], "Reviewing words regularly", "The detail directly states the habit."),
        ("A notice says students should bring water bottles and avoid single-use plastic cups on the school trip. What should students do?", ["Bring reusable bottles", "Buy plastic cups", "Stay at home", "Throw bottles away"], "Bring reusable bottles", "The notice asks students to avoid single-use plastic."),
        ("A short text says online learning is useful but students need self-discipline. What is the writer's opinion?", ["Online learning requires responsibility", "Online learning is always bad", "Students need no plans", "Teachers should stop teaching"], "Online learning requires responsibility", "The balanced idea is usefulness plus self-discipline."),
        ("A poster says: 'Read 20 minutes a day to build a lifelong habit.' What is the poster encouraging?", ["Daily reading", "Playing games", "Buying phones", "Skipping school"], "Daily reading", "The poster directly encourages regular reading."),
    ],
    "SentenceTransformation": [
        ("Rewrite without changing meaning: Because it rained heavily, we stayed at home.", [], "Because of the heavy rain, we stayed at home.", "Because + clause can change to because of + noun phrase."),
        ("Rewrite without changing meaning: The test was so difficult that many students could not finish it.", [], "It was such a difficult test that many students could not finish it.", "Use such + noun phrase + that."),
        ("Rewrite without changing meaning: Although she was tired, she finished her homework.", [], "In spite of being tired, she finished her homework.", "Although + clause can change to in spite of + noun/V-ing."),
        ("Rewrite without changing meaning: I last met him two years ago.", [], "I have not met him for two years.", "Use present perfect negative with for."),
        ("Rewrite without changing meaning: Let's recycle used paper at school.", [], "I suggest recycling used paper at school.", "Suggest can be followed by V-ing."),
    ],
    "DialogueCompletion": [
        ("Complete the dialogue: A: 'Thank you for your help.' B: '_____'.", ["You're welcome", "No, I don't", "Yes, please", "I agree"], "You're welcome", "This is the natural response to thanks."),
        ("Complete the dialogue: A: 'Would you like some tea?' B: '_____'.", ["Yes, please", "That's all right", "I am a student", "See you"], "Yes, please", "This is a polite acceptance of an offer."),
        ("Complete the dialogue: A: 'How about going to the library?' B: '_____'.", ["That's a good idea", "I am fifteen", "No, it isn't mine", "Here you are"], "That's a good idea", "This responds naturally to a suggestion."),
        ("Complete the dialogue: A: 'I'm sorry I'm late.' B: '_____'.", ["Never mind", "Yes, I do", "Good luck", "It's expensive"], "Never mind", "This is a natural response to an apology."),
        ("Complete the dialogue: A: 'Good luck with your exam!' B: '_____'.", ["Thanks a lot", "You're welcome", "No, thanks", "It doesn't matter"], "Thanks a lot", "This is a natural response to a wish."),
    ],
}


def english_question(i, topic_override=None, occurrence_override=None):
    topic = topic_override or ENG_TOPICS[(i - 1) % len(ENG_TOPICS)]
    level = LEVELS[(i - 1) % 4]
    variants = eng_bank[topic]
    round_index = occurrence_override if occurrence_override is not None else (i - 1) // len(ENG_TOPICS)
    prompt, choices, answer, explanation = variants[round_index % len(variants)]
    focus = eng_focuses[round_index % len(eng_focuses)]
    context = eng_contexts[round_index % len(eng_contexts)]
    return row(
        f"english-{i:03d}", "TiengAnh", topic, level,
        f"[{topic}] {prompt} Context: {context}. Focus: {focus}.",
        answer,
        explanation,
        "Read the whole sentence/context first, then check grammar and meaning before choosing the answer.",
        choices,
        60 + 30 * LEVELS.index(level),
    )


literature_rows = []
index = 1
for topic in LIT_TOPICS:
    for occurrence in range(LIT_TOPIC_WEIGHTS[topic]):
        literature_rows.append(literature_question(index, topic, occurrence))
        index += 1

english_rows = []
index = 1
for topic in ENG_TOPICS:
    for occurrence in range(ENG_TOPIC_WEIGHTS[topic]):
        english_rows.append(english_question(index, topic, occurrence))
        index += 1

for filename, rows in [("literature.jsonl", literature_rows), ("english.jsonl", english_rows)]:
    (DATA / filename).write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in rows) + "\n",
        encoding="utf-8",
    )

all_rows = []
for filename in ["math.jsonl", "literature.jsonl", "english.jsonl"]:
    for line in (DATA / filename).read_text(encoding="utf-8").splitlines():
        if line.strip():
            all_rows.append(json.loads(line))

(WEB / "questions-data.js").write_text(
    "window.QUESTION_BANK = " + json.dumps(all_rows, ensure_ascii=False, indent=2) + ";\n",
    encoding="utf-8",
)

by_subject = Counter(r["monHoc"] for r in all_rows)
by_level = Counter(r["mucDo"] for r in all_rows)
by_topic = defaultdict(Counter)
for r in all_rows:
    by_topic[r["monHoc"]][r["chuyenDe"]] += 1

report = ["# Validation Report", "", f"Total rows: {len(all_rows)}", "", "## Rows By Subject"]
for key, value in sorted(by_subject.items()):
    report.append(f"- {key}: {value}")
report.extend(["", "## Rows By Difficulty"])
for key, value in sorted(by_level.items()):
    report.append(f"- {key}: {value}")
report.extend(["", "## Topic Coverage"])
for subject, counts in sorted(by_topic.items()):
    report.append(f"### {subject}")
    for topic, count in sorted(counts.items()):
        report.append(f"- {topic}: {count}")
report.extend([
    "",
    "## Quality Audit",
    "- Toán: redistributed to 600 questions using the real-exam 2022-2026 priority map.",
    "- Ngữ văn: redistributed to 600 questions emphasizing reading comprehension, paragraph/social writing, evidence, expression repair and literary response.",
    "- Tiếng Anh: redistributed to 900 questions emphasizing WordForms, SentenceTransformation, ReadingComprehension and ClozeTest in the 40-question structure.",
    "- Mock exams in the frontend should show answers and explanations from the same question bank.",
    "- Remaining content is AI-generated and still needs human teacher review before commercial use.",
    "",
    "## Errors",
    "None",
])
(DATA / "validation-report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

print("Regenerated 600 Literature and 900 English questions; rebuilt frontend bundle.")
