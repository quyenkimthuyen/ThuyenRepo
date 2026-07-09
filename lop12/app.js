const EXAMS = {
  math: {
    title: "Toán",
    code: "0108",
    duration: 90,
    source: "data/toan/2026/Giai-de-mon-Toan-Bo-GD-2026-ma-de-108.pdf",
    note:
      "Đề Toán 2026 mã 0108 nhập theo file PDF trong data/toan/2026; hình và bảng được dựng lại để hiển thị trong app.",
    sections: [
      {
        title: "Phần I - Trắc nghiệm nhiều phương án lựa chọn",
        type: "single",
        points: 0.25,
        questions: [
          q("m1", "Cho hình lập phương ABCD.A'B'C'D' như hình minh họa. Vectơ nào sau đây bằng vectơ AD?", "D", ["AB", "CD", "AA'", "B'C'"], "Hình học không gian", pdfQuestionImage("m1", "Câu 1 mã đề 0108 cắt từ PDF")),
          q("m2", "Cho cấp số nhân (u_n) có số hạng đầu u1 và công bội q với u1 khác 0, q>1. Số hạng u3 là", "B", ["u3 = u1.q^3", "u3 = u1.q^2", "u3 = u1 + 3q", "u3 = u1 + 2q"], "Dãy số", pdfQuestionImage("m2", "Câu 2 mã đề 0108 cắt từ PDF")),
          q("m3", "Nghiệm của phương trình log_3(3x)=2 là", "B", ["x=8/3", "x=3", "x=2", "x=2/3"], "Logarit", pdfQuestionImage("m3", "Câu 3 mã đề 0108 cắt từ PDF")),
          q("m4", "Hàm số F(x)=5x^3 là một nguyên hàm của hàm số nào sau đây?", "B", ["f(x)=5x^4", "f(x)=15x^2", "f(x)=5x^2", "f(x)=x^4/5"], "Nguyên hàm", pdfQuestionImage("m4", "Câu 4 mã đề 0108 cắt từ PDF")),
          q("m5", "Cho hàm số y=(ax+b)/(cx+d), c khác 0, ad-bc khác 0, có bảng biến thiên như hình. Đường tiệm cận đứng của đồ thị hàm số đã cho có phương trình là", "A", ["x=1", "y=1", "y=-2", "x=-2"], "Hàm số", pdfQuestionImage("m5", "Câu 5 mã đề 0108 cắt từ PDF")),
          q("m6", "Cho các hàm số y=f(x) và y=g(x) có đạo hàm trên R thỏa mãn f'(x)=2x và g'(x)=x^2. Đạo hàm của hàm số y=f(x)+g(x) là", "C", ["2+x^2", "2+2x", "2x+x^2", "4x"], "Đạo hàm", pdfQuestionImage("m6", "Câu 6 mã đề 0108 cắt từ PDF")),
          q("m7", "Khảo sát thời gian học trực tuyến trong một ngày của 42 học sinh, người ta thu được mẫu số liệu ghép nhóm như bảng. Trung vị của mẫu số liệu trên thuộc nhóm nào sau đây?", "A", ["[30;40)", "[50;60)", "[40;50)", "[20;30)"], "Thống kê", pdfQuestionImage(["m7a", "m7b"], "Câu 7 mã đề 0108 cắt từ PDF")),
          q("m8", "Trong không gian Oxyz, cho hai điểm A(2;3;1) và B(4;1;1). Vectơ AB có tọa độ là", "D", ["(-2;2;0)", "(6;4;2)", "(3;2;1)", "(2;-2;0)"], "Oxyz", pdfQuestionImage("m8", "Câu 8 mã đề 0108 cắt từ PDF")),
          q("m9", "Cho hai biến cố độc lập A và B có xác suất thỏa mãn P(A)=0,3 và P(B)=0,6. Giá trị của P(AB) bằng", "D", ["0,5", "0,9", "0,3", "0,18"], "Xác suất", pdfQuestionImage("m9", "Câu 9 mã đề 0108 cắt từ PDF")),
          q("m10", "Cho cấp số cộng (u_n) có u1=-2 và công sai d=3. Giá trị của u2 bằng", "D", ["-6", "-1", "-5", "1"], "Dãy số", pdfQuestionImage("m10", "Câu 10 mã đề 0108 cắt từ PDF")),
          q("m11", "Cho ∫f(x)dx = sin x + C. Phát biểu nào sau đây là đúng?", "C", ["∫[2+f(x)]dx = 2x+cos x+C", "∫[2+f(x)]dx = 2x-sin x+C", "∫[2+f(x)]dx = 2x+sin x+C", "∫[2+f(x)]dx = 2x-cos x+C"], "Nguyên hàm", pdfQuestionImage("m11", "Câu 11 mã đề 0108 cắt từ PDF")),
          q("m12", "Cặp số nào sau đây là nghiệm của hệ bất phương trình { x+y-2<0; x-y+2>0 }?", "A", ["(1;0)", "(-3;0)", "(0;3)", "(1;2)"], "Bất phương trình", pdfQuestionImage("m12", "Câu 12 mã đề 0108 cắt từ PDF"))
        ]
      },
      {
        title: "Phần II - Trắc nghiệm đúng/sai",
        type: "truefalse",
        points: "tiered",
        questions: [
          tf("m13", "Trong không gian Oxyz, mỗi đơn vị dài ứng với 10 m. Vành đai bảo vệ là đường tròn tâm O bán kính 6 trong mặt phẳng Oxy. Một máy bay bay theo đoạn thẳng từ M(2;11;3) đến N(14;2;3).", "DSSD", [
            "Vectơ MN=(12;-9;0).",
            "Phương trình tham số của đường thẳng MN là x=2+4t, y=11-3t, z=0.",
            "Trong quá trình bay từ M đến N, khoảng cách ngắn nhất từ máy bay đến vành đai bảo vệ là 100 mét.",
            "Khoảng cách từ máy bay đến vành đai bảo vệ là ngắn nhất khi máy bay ở vị trí (6;8;3)."
          ], "Oxyz - mô hình thực tế", pdfQuestionImage(["m13a", "m13b"], "Phần II câu 1 mã đề 0108 cắt từ PDF")),
          tf("m14", "Một ứng dụng trí tuệ nhân tạo được dùng để sàng lọc nguy cơ mắc bệnh trên 10000 người. Có 1000 người nhận cảnh báo, trong đó 600 người có bệnh và 400 người không có bệnh. Có 9000 người không nhận cảnh báo, trong đó 200 người có bệnh và 8800 người không có bệnh.", "DDSD", [
            "Xác suất để người đó không nhận được cảnh báo từ ứng dụng bằng 0,9.",
            "Xác suất để người đó không có bệnh, biết rằng người đó không nhận được cảnh báo từ ứng dụng, lớn hơn 0,97.",
            "Xác suất để người đó không có bệnh bằng 0,9.",
            "Xác suất để người đó không nhận được cảnh báo từ ứng dụng, biết rằng người đó không có bệnh, lớn hơn 0,95."
          ], "Xác suất có điều kiện", pdfQuestionImage("m14", "Phần II câu 2 mã đề 0108 cắt từ PDF")),
          tf("m15", "Một hệ thống pin năng lượng mặt trời có năng lượng lưu trữ F(t), F(0)=0. Tốc độ lưu trữ là f(t)=F'(t)=-0,15t^2+1,8t với 0<=t<=12.", "DDSS", [
            "F(t)=-0,05t^3+0,9t^2 với 0<=t<=12.",
            "Năng lượng điện lưu trữ được từ thời điểm t=a đến t=b là tích phân từ a đến b của f(t)dt.",
            "Năng lượng điện lưu trữ được từ t=1 đến t=5 nhỏ hơn 15,3 kWh.",
            "Năng lượng điện lưu trữ được từ t=1 đến t=9 gấp hai lần năng lượng điện lưu trữ được từ t=1 đến t=5."
          ], "Tích phân - ứng dụng", pdfQuestionImage("m15", "Phần II câu 3 mã đề 0108 cắt từ PDF")),
          tf("m16", "Cho hàm số f(x)=1/3 x^3 - 2x^2 + 3x + 8. Xét các mệnh đề sau.", "DDDS", [
            "Đạo hàm của hàm số đã cho là f'(x)=x^2-4x+3.",
            "Phương trình f'(x)=0 có tập nghiệm là S={1;3}.",
            "Hàm số đã cho nghịch biến trên khoảng (1;3).",
            "Giá trị cực tiểu của hàm số đã cho bằng 28/3."
          ], "Hàm số", pdfQuestionImage("m16", "Phần II câu 4 mã đề 0108 cắt từ PDF"))
        ]
      },
      {
        title: "Phần III - Trả lời ngắn",
        type: "short",
        points: 0.5,
        questions: [
          short(
            "m17",
            "Trong một trò chơi, Bình cần điền tất cả 15 số thuộc tập {1;2;3;4;5;6;7;8;9;11;12;13;16;17;21} vào 15 ô vuông như hình sao cho mỗi ô đúng một số, mỗi số dùng một lần, và hiệu hai số ở hai ô bất kì khác nhau trên cùng hàng hoặc cùng cột không chia hết cho 5. Gọi H là số cách điền khác nhau. Tính H/10.",
            "3456",
            "Tổ hợp - chia lớp đồng dư",
            pdfQuestionImage(["m17a", "m17b"], "Phần III câu 1 mã đề 0108 cắt từ PDF"),
            "Chia các số theo số dư mod 5 có số lượng 5,4,3,2,1. Số cách là H=5!.4!.3!.2!.1!=34560, nên H/10=3456."
          ),
          short(
            "m18",
            "Một khung hình trang trí là đa giác đều 12 cạnh A1A2...A12. Có 12 bóng đèn gồm 4 bóng đỏ và 8 bóng xanh, công suất đôi một khác nhau. Lắp ngẫu nhiên 12 bóng vào 12 đỉnh. Gọi P là xác suất để mỗi hình vuông có bốn đỉnh là các đỉnh của đa giác đều đều có ít nhất một bóng đỏ. Tính 4565P.",
            "2656",
            "Xác suất - tổ hợp",
            pdfQuestionImage("m18", "Phần III câu 2 mã đề 0108 cắt từ PDF"),
            "Ba hình vuông độc lập chia 12 đỉnh thành 3 nhóm 4 đỉnh. Số vị trí đỏ thuận lợi là 288, tổng là C(12,4)=495 nên P=32/55. Do đó 4565P=2656."
          ),
          short(
            "m19",
            "Một nông trại cung cấp rau quả cho siêu thị A theo bảng. Biết đơn giá mỗi kg không đổi. Tính tổng số tiền thu được ở ngày thứ Bảy từ ba loại rau quả, đơn vị nghìn đồng.",
            "1350",
            "Hệ phương trình - bảng số liệu",
            pdfQuestionImage("m19", "Phần III câu 3 mã đề 0108 cắt từ PDF"),
            "Gọi đơn giá rau muống, bí xanh, cà chua là x,y,z. Từ ba ngày đầu giải được x=10, y=15, z=20. Thứ Bảy: 50.10+30.15+20.20=1350."
          ),
          short(
            "m20",
            "Cho hình lập phương ABCD.MNPQ có cạnh bằng 14. Gọi E là trung điểm của AB. Tính khoảng cách từ điểm P đến mặt phẳng (MED), làm tròn đến hàng phần mười.",
            "17,1",
            "Hình học không gian - Oxyz",
            pdfQuestionImage("m20", "Phần III câu 4 mã đề 0108 cắt từ PDF"),
            "Đặt A(0;0;0), B(14;0;0), D(0;14;0), M(0;0;14), E(7;0;0), P(14;14;14). Mặt phẳng (MED): 2x+y+z-14=0. Khoảng cách bằng 7sqrt(6)≈17,1."
          ),
          short(
            "m21",
            "Một công ty nông sản có công suất chế biến không quá 180 tấn nguyên liệu mỗi tháng. Nếu chế biến x tấn nguyên liệu (1<=x<=180), chi phí C(x)=0,002x^3+30x+20 và doanh thu R(x)=90x, đơn vị triệu đồng. Lợi nhuận lớn nhất công ty đạt được trong một tháng là bao nhiêu triệu đồng?",
            "3980",
            "Tối ưu hàm số",
            pdfQuestionImage("m21", "Phần III câu 5 mã đề 0108 cắt từ PDF"),
            "P(x)=R(x)-C(x)=-0,002x^3+60x-20. P'(x)=-0,006x^2+60=0 cho x=100. P(100)=3980 triệu đồng."
          ),
          short(
            "m22",
            "Một hạt cườm được tạo từ khối tròn xoay sinh bởi nửa trên elip x^2/1,5^2 + y^2/1^2 = 1 quay quanh trục Ox, sau đó khoan dọc theo trục xoay một lỗ trụ bán kính 0,1 cm. Tính thể tích phần còn lại, đơn vị cm3, làm tròn đến hàng phần trăm.",
            "6,19",
            "Khối tròn xoay - tích phân",
            pdfQuestionImage("m22", "Phần III câu 6 mã đề 0108 cắt từ PDF"),
            "Sau khi khoan bán kính 0,1, cận theo hoành độ là ±1,5sqrt(0,99). Tích phân thể tích vành khăn cho V≈6,189 cm3, làm tròn được 6,19."
          )
        ]
      }
    ]
  },
  physics: {
    title: "Vật lí",
    code: "0214",
    duration: 50,
    source:
      "https://xaydungchinhsach.chinhphu.vn/thi-tot-nghiep-thpt-2026-de-thi-mon-vat-li-va-goi-y-dap-an-119260612135353486.htm",
    note:
      "Mô phỏng theo đề Vật lí 2026: nhận biết/thông hiểu ở đầu đề, tăng vận dụng ở phần sau.",
    sections: [
      {
        title: "Phần I - Trắc nghiệm nhiều phương án lựa chọn",
        type: "single",
        points: 0.25,
        questions: buildChoiceSet("p", [
          ["Đơn vị của cường độ dòng điện trong hệ SI là", "A", ["ampe", "vôn", "ôm", "oát"], "Điện học"],
          ["Một vật dao động điều hòa, đại lượng luôn không âm là", "C", ["li độ", "vận tốc", "cơ năng", "gia tốc"], "Dao động"],
          ["Trong chân không, sóng điện từ truyền với tốc độ xấp xỉ", "B", ["3.10^6 m/s", "3.10^8 m/s", "340 m/s", "1,5.10^8 m/s"], "Sóng điện từ"],
          ["Hạt nhân nguyên tử được cấu tạo chủ yếu từ", "D", ["electron và proton", "electron và neutron", "photon", "proton và neutron"], "Hạt nhân"],
          ["Khi nhiệt độ khí lí tưởng tăng ở thể tích không đổi, áp suất", "A", ["tăng", "giảm", "không đổi", "bằng 0"], "Khí lí tưởng"],
          ["Công thức tính cảm kháng của cuộn cảm là", "D", ["ZL=1/(wL)", "ZL=R", "ZL=wC", "ZL=wL"], "Dòng điện xoay chiều"],
          ["Từ thông qua một khung dây phụ thuộc trực tiếp vào", "B", ["điện trở khung", "cảm ứng từ", "khối lượng khung", "nhiệt độ phòng"], "Từ trường"],
          ["Ánh sáng đơn sắc khi truyền từ không khí vào nước thì tần số", "A", ["không đổi", "tăng", "giảm", "bằng 0"], "Sóng ánh sáng"],
          ["Động năng của vật khối lượng m chuyển động tốc độ v là", "B", ["mv", "mv^2/2", "2mv", "mgh"], "Cơ học"],
          ["Pin quang điện hoạt động dựa trên hiện tượng", "A", ["quang điện", "nhiệt điện", "siêu dẫn", "phóng xạ"], "Lượng tử ánh sáng"],
          ["Trong mạch RLC nối tiếp cộng hưởng, tổng trở bằng", "A", ["R", "ZL", "ZC", "R+ZL+ZC"], "Mạch xoay chiều"],
          ["Độ hụt khối của hạt nhân liên hệ với năng lượng liên kết qua", "A", ["E=mc^2", "E=hf", "F=ma", "A=Fs"], "Hạt nhân"],
          ["Áp suất chất khí trong lốp xe thường tăng khi xe chạy lâu vì", "C", ["thể tích giảm mạnh", "khối lượng khí giảm", "nhiệt độ khí tăng", "trọng lượng xe giảm"], "Nhiệt học"],
          ["Suất điện động cảm ứng xuất hiện khi", "D", ["khung đứng yên trong từ trường đều", "không có từ thông", "điện trở bằng 0", "từ thông qua mạch biến thiên"], "Cảm ứng điện từ"],
          ["Một nguồn âm có mức cường độ âm tăng 10 dB thì cường độ âm tăng", "A", ["10 lần", "2 lần", "100 lần", "không đổi"], "Âm học"],
          ["Tia nào sau đây có bản chất là sóng điện từ?", "D", ["tia alpha", "tia beta trừ", "chùm proton", "tia gamma"], "Bức xạ"],
          ["Nhiệt lượng khí nhận vào khi nội năng tăng và khí sinh công thỏa", "B", ["Q=A-DeltaU", "Q=DeltaU+A", "Q=DeltaU-A", "Q=0"], "Nhiệt động lực học"],
          ["Trong thí nghiệm giao thoa ánh sáng, khoảng vân tăng khi", "A", ["tăng khoảng cách màn", "giảm bước sóng", "giảm khoảng cách màn", "tăng khoảng cách hai khe"], "Giao thoa"]
        ])
      },
      {
        title: "Phần II - Trắc nghiệm đúng/sai",
        type: "truefalse",
        points: "tiered",
        questions: [
          tf("p19", "Một lượng khí lí tưởng được giữ ở thể tích không đổi.", "DSDS", [
            "Áp suất tỉ lệ thuận với nhiệt độ tuyệt đối.",
            "Áp suất tỉ lệ nghịch với nhiệt độ tuyệt đối.",
            "Khi nhiệt độ tăng gấp đôi thì áp suất tăng gấp đôi.",
            "Khi nhiệt độ tăng thì khối lượng khí tăng."
          ], "Khí lí tưởng"),
          tf("p20", "Mạch điện xoay chiều RLC nối tiếp đang ở trạng thái cộng hưởng.", "SDDS", [
            "Cảm kháng khác dung kháng.",
            "Dòng điện cùng pha với điện áp hai đầu mạch.",
            "Tổng trở của mạch đạt giá trị nhỏ nhất.",
            "Công suất tiêu thụ bằng 0."
          ], "Mạch xoay chiều"),
          tf("p21", "Xét hiện tượng cảm ứng điện từ trong một vòng dây kín.", "DDSS", [
            "Từ thông biến thiên có thể tạo dòng điện cảm ứng.",
            "Chiều dòng điện cảm ứng tuân theo định luật Len-xơ.",
            "Từ thông không đổi vẫn luôn tạo dòng cảm ứng.",
            "Dòng cảm ứng luôn cùng chiều với nguyên nhân sinh ra nó."
          ], "Cảm ứng điện từ"),
          tf("p22", "Trong vật lí hạt nhân, phản ứng phân hạch và nhiệt hạch đều liên quan năng lượng liên kết.", "DSDD", [
            "Phân hạch có thể giải phóng năng lượng.",
            "Nhiệt hạch chỉ xảy ra ở nhiệt độ rất thấp.",
            "Độ hụt khối liên quan đến năng lượng tỏa ra.",
            "Năng lượng hạt nhân có thể tính theo E=mc^2."
          ], "Hạt nhân")
        ]
      },
      {
        title: "Phần III - Trả lời ngắn",
        type: "short",
        points: 0.25,
        questions: [
          short("p23", "Một vật khối lượng m=2 kg chuyển động thẳng với tốc độ v=3 m/s như hình. Tính động năng của vật theo đơn vị J.", "9", "Cơ học", diagramMotion(), "Wđ=1/2.m.v^2=1/2.2.3^2=9 J."),
          short("p24", "Một điện trở R=10 ohm mắc vào mạch có dòng điện I=2 A chạy qua. Tính công suất tỏa nhiệt trên điện trở theo đơn vị W.", "40", "Điện học", diagramCircuit("R=10 ohm", "I=2 A"), "P=I^2R=2^2.10=40 W."),
          short("p25", "Một sóng cơ có bước sóng lambda=0,5 m và tần số f=20 Hz. Tính tốc độ truyền sóng theo đơn vị m/s.", "10", "Sóng", diagramWave("lambda=0,5 m", "f=20 Hz"), "v=lambda.f=0,5.20=10 m/s."),
          short("p26", "Một lượng khí nhận nhiệt lượng Q=500 J và sinh công A=120 J ra môi trường như hình. Tính độ tăng nội năng Delta U của khí theo đơn vị J.", "380", "Nhiệt", diagramGas(), "Theo quy ước Q=Delta U + A khí sinh ra, Delta U=Q-A=500-120=380 J."),
          short("p27", "Một photon có tần số f=5.10^14 Hz. Lấy h=6,625.10^-34 J.s. Tính năng lượng photon theo đơn vị 10^-19 J, làm tròn đến hàng phần trăm.", "3,31", "Lượng tử", diagramPhoton(), "E=hf=6,625.10^-34.5.10^14=3,3125.10^-19 J, nhập 3,31."),
          short("p28", "Một mạch xoay chiều nối tiếp có R=6 ohm, cảm kháng ZL=8 ohm và dung kháng ZC=0 ohm. Tính tổng trở Z của mạch theo đơn vị ohm.", "10", "Xoay chiều", diagramImpedance(), "Z=sqrt(R^2+(ZL-ZC)^2)=sqrt(6^2+8^2)=10 ohm.")
        ]
      },
      {
        title: "Luyện thêm - Trả lời ngắn nâng cao",
        type: "short",
        points: 0.25,
        questions: [
          short(
            "p29",
            "Một mạch RLC nối tiếp có R=30 ohm, ZL=80 ohm, ZC=40 ohm. Đặt vào hai đầu mạch điện áp hiệu dụng U=100 V. Tính cường độ dòng điện hiệu dụng I trong mạch theo đơn vị A.",
            "2",
            "Điện xoay chiều - RLC",
            diagramImpedance(),
            "Z=sqrt(30^2+(80-40)^2)=50 ohm. I=U/Z=100/50=2 A."
          ),
          short(
            "p30",
            "Áp suất khí trong một lốp xe là 2,4 bar ở 27 độ C. Coi thể tích lốp không đổi. Khi nhiệt độ khí tăng lên 57 độ C, áp suất khí trong lốp là bao nhiêu bar?",
            "2,64",
            "Khí lí tưởng - đẳng tích",
            diagramGas(),
            "Đổi nhiệt độ: T1=300 K, T2=330 K. Vì V không đổi, p2=p1.T2/T1=2,4.330/300=2,64 bar."
          ),
          short(
            "p31",
            "Một photon có bước sóng lambda=0,50 micromet. Dùng hệ thức gần đúng E(eV)=1240/lambda(nm). Tính năng lượng photon theo đơn vị eV.",
            "2,48",
            "Lượng tử ánh sáng",
            diagramPhoton(),
            "0,50 micromet = 500 nm. E=1240/500=2,48 eV."
          ),
          short(
            "p32",
            "Một mẫu phóng xạ ban đầu có khối lượng 40 g. Sau 3 chu kì bán rã, khối lượng chất phóng xạ còn lại là bao nhiêu g?",
            "5",
            "Phóng xạ - chu kì bán rã",
            diagramGrowth(),
            "Sau 3 chu kì bán rã, m=40/2^3=5 g."
          )
        ]
      }
    ]
  },
  informatics: {
    title: "Tin học",
    code: "0525",
    duration: 50,
    source:
      "https://dolthpt.vn/tot-nghiep-thpt/pdf-de-chinh-thuc-tot-nghiep-thpt-mon-tin-hoc-nam-2026-ma-de-0525-co-dap-an",
    note:
      "Cập nhật theo đề chính thức tốt nghiệp THPT môn Tin học năm 2026 mã đề 0525 từ DOL. Phần đúng/sai dùng 2 câu chung và nhánh Tin học ứng dụng để giữ cấu trúc 10 điểm trong app.",
    sections: [
      {
        title: "Phần I - Trắc nghiệm nhiều phương án lựa chọn",
        type: "single",
        points: 0.25,
        questions: buildChoiceSet("i", [
          ["Cho đoạn mã HTML và CSS có hai quy tắc .tieude: quy tắc đầu đặt màu vàng, in đậm; quy tắc sau đặt màu đỏ, in nghiêng. Khi thực hiện, dòng chữ 'Tin học' hiển thị theo định dạng nào?", "C", ["Màu vàng, in đậm và nghiêng.", "Màu vàng, in đậm và không nghiêng.", "Màu đỏ, in đậm và nghiêng.", "Màu đỏ, in nghiêng và không đậm."], "Web"],
          ["Hệ thống camera thông minh của bãi gửi xe có khả năng nhận dạng biển số xe. Chức năng xử lí dữ liệu hình ảnh này thuộc lĩnh vực nào của AI?", "C", ["Xử lí tiếng nói.", "Điều khiển rô-bốt.", "Thị giác máy tính.", "Xử lí ngôn ngữ tự nhiên."], "AI"],
          ["Phương án nào liệt kê đơn vị đo dung lượng bộ nhớ theo thứ tự giảm dần?", "A", ["Terabyte, Megabyte, Kilobyte.", "Terabyte, Kilobyte, Megabyte.", "Megabyte, Terabyte, Kilobyte.", "Megabyte, Kilobyte, Terabyte."], "Dữ liệu"],
          ["Phát biểu nào nêu đúng chức năng chính của Switch?", "D", ["Định danh các máy tính có trong mạng thông qua địa chỉ IPv4.", "Định tuyến cho gói dữ liệu khi truyền đi giữa các mạng.", "Phân giải tên miền thành địa chỉ IP dưới dạng nhị phân.", "Chuyển dữ liệu đến đúng thiết bị nhận thông qua địa chỉ MAC."], "Mạng"],
          ["Cho CSS: p {font-size: 25px; padding: 30px; margin: 20px;}. Các giá trị font-size, margin, padding lần lượt là", "D", ["30px, 20px, 25px.", "25px, 30px, 20px.", "20px, 30px, 25px.", "25px, 20px, 30px."], "Web"],
          ["Nhiệm vụ nào thể hiện đặc trưng tạo nội dung mới của trí tuệ nhân tạo tạo sinh?", "A", ["Tạo ra đoạn mã chương trình từ mô tả yêu cầu bằng ngôn ngữ tự nhiên.", "Chẩn đoán bệnh dựa trên việc phân loại hình ảnh chụp X-quang.", "Nhận diện và đếm số lượng phương tiện giao thông trong một bức ảnh.", "Dự báo lượng mưa dựa trên dữ liệu khí tượng của mười năm trước đó."], "AI"],
          ["Phương án nào chỉ ra ưu điểm của giao tiếp trên không gian mạng?", "C", ["Luôn quan sát được thái độ của người nói.", "Không phụ thuộc vào thiết bị công nghệ.", "Tạo cơ hội mở rộng các mối quan hệ xã hội.", "Đảm bảo tin cậy và bảo mật thông tin tuyệt đối."], "Văn hóa số"],
          ["Lựa chọn ngôn ngữ lập trình Python hoặc C++ để tìm hiểu đoạn chương trình sau. Sau khi thực hiện, giá trị nào được hiển thị trên màn hình?", "B", ["4.", "21.", "20.", "3."], "Lập trình", tin2026Image("q8")],
          ["Cách ứng xử nào thể hiện tính nhân văn khi thấy một người bạn thường xuyên chia sẻ thông tin chưa được kiểm chứng lên mạng xã hội?", "D", ["Công khai phê phán về hành động của bạn.", "Lập nhóm riêng với các bạn khác để bàn luận.", "Hủy kết bạn để tránh nhìn thấy thông tin đó.", "Nhắn tin riêng phân tích và khuyên nhủ bạn."], "Văn hóa số"],
          ["Bảng dữ liệu phim có các cột Mã phim, Tên phim, Loại phim, Thời lượng, Ngày khởi chiếu, Giá vé. Cần khai thác dữ liệu trong trường hợp nào?", "B", ["Điều chỉnh lại giá vé của các bộ phim khoa học viễn tưởng.", "Đưa ra tên các bộ phim được chiếu từ ngày 20/11/2025.", "Xóa khỏi bảng các bộ phim có thời lượng ít hơn 60 phút.", "Bổ sung thêm các bộ phim được phát hành mới nhất."], "Cơ sở dữ liệu"],
          ["Cặp thẻ HTML nào được dùng để tạo các mục của danh sách?", "D", ["<td> </td>", "<ol> </ol>", "<ul> </ul>", "<li> </li>"], "Web"],
          ["Lựa chọn ngôn ngữ lập trình Python hoặc C++ để tìm hiểu đoạn chương trình sau. Sau khi thực hiện, biến T có giá trị nào?", "C", ["-5.", "-11.", "6.", "2."], "Lập trình", tin2026Image("q12")],
          ["Ứng dụng nào là một Chatbot có sử dụng trí tuệ nhân tạo?", "D", ["WinRAR.", "Notepad.", "Geogebra.", "Copilot."], "AI"],
          ["Đoạn mã CSS nào định dạng đoạn văn bản cỡ chữ 20 pixel với đường viền bao quanh là các dấu chấm liền nhau màu đen?", "C", ["p{font-size: 20px; border-style: solid;}", "p{font-size: 20pt; border-style: dotted;}", "p{font-size: 20px; border-style: dotted;}", "p{font-size: 20pt; border-style: solid;}"], "Web"],
          ["Việc chia sẻ thư mục trong mạng LAN cần các thao tác: (1) chọn thư mục, (2) thiết lập quyền sửa, (3) chọn người dùng được chia sẻ, (4) mở ứng dụng quản lí tệp. Thứ tự đúng là", "A", ["(4), (1), (3), (2).", "(4), (3), (1), (2).", "(1), (4), (2), (3).", "(1), (3), (2), (4)."], "Mạng"],
          ["Lựa chọn ngôn ngữ lập trình Python hoặc C++ để tìm hiểu đoạn chương trình sau. Với a và b là hai số nguyên dương khác nhau, n thỏa mãn tính chất nào?", "B", ["Nhỏ nhất và chia hết cho cả a và b.", "Nhỏ nhất và chia hết cho a hoặc b.", "Lớn nhất và là ước số của a hoặc b.", "Lớn nhất và là ước số của cả a và b."], "Lập trình", tin2026Image("q16")],
          ["Thành phần nào thuộc hệ cơ sở dữ liệu?", "A", ["Hệ quản trị cơ sở dữ liệu.", "Tập hợp các trang tính.", "Máy chủ dữ liệu của tổ chức.", "Không gian lưu trữ đám mây."], "Cơ sở dữ liệu"],
          ["Một siêu liên kết <a href=\"#binhluan\">Bình luận</a>. Đoạn HTML nào để điều hướng đến vùng nhập dữ liệu 10 dòng 8 cột trong cùng trang?", "C", ["<textarea name=\"binhluan\" rows=\"10\" cols=\"8\"></textarea>", "<textarea id=\"binhluan\" rows=\"8\" cols=\"10\"></textarea>", "<textarea id=\"binhluan\" rows=\"10\" cols=\"8\"></textarea>", "<textarea name=\"binhluan\" rows=\"8\" cols=\"10\"></textarea>"], "Web"],
          ["Trong buổi học trực tuyến, một bạn liên tục ngắt lời cô giáo để đặt câu hỏi. Lớp trưởng nên xử lí thế nào để mọi người đều được tôn trọng?", "C", ["Nhắn tin kêu gọi các thành viên khác phê phán hành động đó.", "Bật micro và phê bình bạn đó vì đã liên tục ngắt lời cô giáo.", "Nhắn tin riêng giải thích và khuyên bạn không nên ngắt lời cô giáo.", "Khuyến khích bạn đó tiếp tục phát biểu để thể hiện tư duy phản biện."], "Văn hóa số"],
          ["Nhận định nào phản ánh đúng một rủi ro về an toàn thông tin do ảnh hưởng của trí tuệ nhân tạo?", "D", ["Trí tuệ nhân tạo khiến tốc độ truyền dữ liệu qua Internet bị chậm lại.", "Chi phí đầu tư hạ tầng mạng Internet tăng cao do yêu cầu xử lí dữ liệu lớn.", "Dung lượng bộ nhớ trên các thiết bị lưu trữ của người dùng giảm đáng kể.", "Trí tuệ nhân tạo có thể bị lợi dụng để tạo ra các nội dung giả mạo."], "An toàn thông tin"],
          ["Người quản trị cơ sở dữ liệu cần thực hiện được công việc nào?", "C", ["Phát triển phần mềm ứng dụng cơ sở dữ liệu.", "Đảm bảo an toàn và bảo mật mạng máy tính.", "Cài đặt, cập nhật hệ quản trị cơ sở dữ liệu.", "Kiểm thử và đảm bảo chất lượng phần mềm."], "Cơ sở dữ liệu"],
          ["Kiến thức và chủ đề nào không nằm trong yêu cầu đối với người làm nghề lập trình?", "C", ["Cấu trúc dữ liệu và giải thuật.", "Ngôn ngữ lập trình bậc cao.", "Phần mềm thiết kế đồ họa.", "Ngôn ngữ truy vấn SQL."], "Nghề nghiệp"],
          ["Nghề nào thuộc nhóm nghề dịch vụ trong ngành Công nghệ thông tin?", "D", ["Quản trị và bảo trì hệ thống.", "Quản trị mạng máy tính.", "Bảo mật hệ thống thông tin.", "Sửa chữa và bảo trì máy tính."], "Nghề nghiệp"],
          ["Phương án nào nêu đúng một công việc chính của người làm nghề quản trị mạng máy tính?", "D", ["Kiểm tra và tháo lắp linh kiện phần cứng.", "Quản lí và duy trì hệ thống thông tin.", "Khắc phục lỗi và sửa chữa máy tính.", "Cài đặt và điều chỉnh hiệu năng mạng."], "Nghề nghiệp"]
        ])
      },
      {
        title: "Phần II - Trắc nghiệm đúng/sai",
        type: "truefalse",
        points: "tiered",
        questions: [
          tf("i25", "Người quản trị trang web Đoàn thanh niên tạo biểu mẫu HTML để học sinh đăng kí hoạt động văn nghệ, thể thao.", "DSDS", [
            "Biểu mẫu này có hai ô nhập dữ liệu và một nút gửi dữ liệu.",
            "Giá trị của thuộc tính value của hai ô nhập dữ liệu không được để trống.",
            "Nếu nhập dữ liệu và nhấn nút Đăng kí thì dữ liệu được gửi đến trang dangki.php.",
            "Để chỉ được chọn một trong hai hoạt động Văn nghệ hoặc Thể thao, hai nút radio có thể dùng hai giá trị name khác nhau."
          ], "Web"),
          tf("i26", "Một nhóm giảng viên tập huấn năng lực số, hằng ngày gửi báo cáo qua email và đăng bài lên website https://dha.edu.vn.", "SDDS", [
            "https trong địa chỉ website là giao thức truyền tải thư điện tử.",
            "Tên miền website đóng vai trò là địa chỉ thay thế cho địa chỉ IP của máy chủ web.",
            "Nếu máy chủ thư điện tử thay đổi địa chỉ IP, trưởng nhóm vẫn có thể gửi báo cáo đến email đã được cung cấp.",
            "Học viên cần dùng điện thoại thông minh kết nối trực tiếp vào Switch để xem tài liệu trên website."
          ], "Mạng"),
          tf("i27", "Một chủ nông trại dùng phần mềm quản lí dữ liệu vườn cây với các bảng VUON_CAY, LOAI_CAY và THONG_KE.", "DSDS", [
            "Để tạo cấu trúc bảng LOAI_CAY, cần tạo bảng mới, đặt tên bảng, tạo trường/kiểu dữ liệu và thiết lập khóa chính.",
            "Trong bảng LOAI_CAY, không thể thiết lập trường maLC có kiểu số nguyên và tự động tăng.",
            "Để đảm bảo nhất quán, khi nhập maVC của bảng THONG_KE cần nhập giá trị đã có trong VUON_CAY.",
            "Truy vấn tên loại cây, tên vườn và sản lượng năm 2025 lớn hơn 3000 kg có thể liên kết VUON_CAY và LOAI_CAY trực tiếp qua maLC."
          ], "Cơ sở dữ liệu"),
          tf("i28", "Một trường đại học phát động cuộc thi thiết kế website bằng phần mềm tạo trang web với các trang Trang chủ, Giới thiệu, Tuyển dụng.", "DSDS", [
            "Nếu đưa logo từng khoa vào trang Giới thiệu thì có thể liên kết từng logo đến trang chi tiết của khoa tương ứng.",
            "Thanh điều hướng chỉ có ở Trang chủ để người dùng dễ di chuyển giữa các trang trong website.",
            "Có thể thiết kế biểu mẫu bằng công cụ trực tuyến phù hợp rồi chèn liên kết biểu mẫu vào trang Tuyển dụng.",
            "Để xem nội dung website sau khi xuất bản, máy tính người dùng cần sử dụng phần mềm tạo trang web."
          ], "Tin học ứng dụng")
        ]
      }
    ]
  }
};

const EXAMS_BY_YEAR = {
  2026: EXAMS,
  2025: {
    math: {
      title: "Toán",
      code: "0124",
      duration: 90,
      source: "https://www.mathvn.com/2025/07/loi-giai-chi-tiet-e-thi-toan-tot-nghiep.html#xem-l-i-gi-i-chi-ti-t",
      note:
        "Đề Toán 2025 mã 0124 nhập theo ảnh đề và lời giải chi tiết từ MathVN.",
      sections: [
        {
          title: "Phần I - Trắc nghiệm nhiều phương án lựa chọn",
          type: "single",
          points: 0.25,
          questions: [
            q("y25m1", "Xem nội dung Câu 1 trong ảnh cắt từ đề Toán 2025 mã 0124.", "B", ["Phương án A", "Phương án B", "Phương án C", "Phương án D"], "Thể tích khối chóp", math2025QuestionImage("y25m1")),
            q("y25m2", "Xem nội dung Câu 2 trong ảnh cắt từ đề Toán 2025 mã 0124.", "B", ["Phương án A", "Phương án B", "Phương án C", "Phương án D"], "Hình học không gian", math2025QuestionImage("y25m2")),
            q("y25m3", "Xem nội dung Câu 3 trong ảnh cắt từ đề Toán 2025 mã 0124.", "D", ["Phương án A", "Phương án B", "Phương án C", "Phương án D"], "Nguyên hàm", math2025QuestionImage("y25m3")),
            q("y25m4", "Xem nội dung Câu 4 trong ảnh cắt từ đề Toán 2025 mã 0124.", "B", ["Phương án A", "Phương án B", "Phương án C", "Phương án D"], "Mũ", math2025QuestionImage("y25m4")),
            q("y25m5", "Xem nội dung Câu 5 trong ảnh cắt từ đề Toán 2025 mã 0124.", "B", ["Phương án A", "Phương án B", "Phương án C", "Phương án D"], "Oxyz", math2025QuestionImage("y25m5")),
            q("y25m6", "Xem nội dung Câu 6 trong ảnh cắt từ đề Toán 2025 mã 0124.", "A", ["Phương án A", "Phương án B", "Phương án C", "Phương án D"], "Hàm phân thức", math2025QuestionImage("y25m6")),
            q("y25m7", "Xem nội dung Câu 7 trong ảnh cắt từ đề Toán 2025 mã 0124.", "D", ["Phương án A", "Phương án B", "Phương án C", "Phương án D"], "Oxyz", math2025QuestionImage("y25m7")),
            q("y25m8", "Xem nội dung Câu 8 trong ảnh cắt từ đề Toán 2025 mã 0124.", "B", ["Phương án A", "Phương án B", "Phương án C", "Phương án D"], "Vectơ không gian", math2025QuestionImage("y25m8")),
            q("y25m9", "Xem nội dung Câu 9 trong ảnh cắt từ đề Toán 2025 mã 0124.", "D", ["Phương án A", "Phương án B", "Phương án C", "Phương án D"], "Thống kê", math2025QuestionImage("y25m9")),
            q("y25m10", "Xem nội dung Câu 10 trong ảnh cắt từ đề Toán 2025 mã 0124.", "A", ["Phương án A", "Phương án B", "Phương án C", "Phương án D"], "Lượng giác", math2025QuestionImage("y25m10")),
            q("y25m11", "Xem nội dung Câu 11 trong ảnh cắt từ đề Toán 2025 mã 0124.", "D", ["Phương án A", "Phương án B", "Phương án C", "Phương án D"], "Tích phân", math2025QuestionImage("y25m11")),
            q("y25m12", "Xem nội dung Câu 12 trong ảnh cắt từ đề Toán 2025 mã 0124.", "C", ["Phương án A", "Phương án B", "Phương án C", "Phương án D"], "Cấp số cộng", math2025QuestionImage("y25m12"))
          ]
        },
        {
          title: "Phần II - Trắc nghiệm đúng/sai",
          type: "truefalse",
          points: "tiered",
          questions: [
            tf("y25m13", "Xem nội dung Phần II - Câu 1 trong ảnh cắt từ đề Toán 2025 mã 0124.", "DSSS", [
              "Mệnh đề a trong ảnh.",
              "Mệnh đề b trong ảnh.",
              "Mệnh đề c trong ảnh.",
              "Mệnh đề d trong ảnh."
            ], "Xác suất có điều kiện", math2025QuestionImage("y25m13")),
            tf("y25m14", "Xem nội dung Phần II - Câu 2 trong ảnh cắt từ đề Toán 2025 mã 0124.", "DDSS", [
              "Mệnh đề a trong ảnh.",
              "Mệnh đề b trong ảnh.",
              "Mệnh đề c trong ảnh.",
              "Mệnh đề d trong ảnh."
            ], "Hàm mũ - mô hình thực tế", math2025QuestionImage("y25m14")),
            tf("y25m15", "Xem nội dung Phần II - Câu 3 trong ảnh cắt từ đề Toán 2025 mã 0124.", "DSDS", [
              "Mệnh đề a trong ảnh.",
              "Mệnh đề b trong ảnh.",
              "Mệnh đề c trong ảnh.",
              "Mệnh đề d trong ảnh."
            ], "Chuyển động trong Oxyz", math2025QuestionImage("y25m15")),
            tf("y25m16", "Xem nội dung Phần II - Câu 4 trong ảnh cắt từ đề Toán 2025 mã 0124.", "DSDD", [
              "Mệnh đề a trong ảnh.",
              "Mệnh đề b trong ảnh.",
              "Mệnh đề c trong ảnh.",
              "Mệnh đề d trong ảnh."
            ], "Hàm số", math2025QuestionImage("y25m16"))
          ]
        },
        {
          title: "Phần III - Trả lời ngắn",
          type: "short",
          points: 0.5,
          questions: [
            short("y25m17", "Xem nội dung Phần III - Câu 1 trong ảnh cắt từ đề Toán 2025 mã 0124.", "5040", "Tổ hợp - xác suất", math2025QuestionImage("y25m17")),
            short("y25m18", "Xem nội dung Phần III - Câu 2 trong ảnh cắt từ đề Toán 2025 mã 0124.", "2,55", "Khoảng cách trong không gian", math2025QuestionImage("y25m18")),
            short("y25m19", "Xem nội dung Phần III - Câu 3 trong ảnh cắt từ đề Toán 2025 mã 0124.", "3150", "Quy hoạch tuyến tính", math2025QuestionImage("y25m19")),
            short("y25m20", "Xem nội dung Phần III - Câu 4 trong ảnh cắt từ đề Toán 2025 mã 0124.", "3528", "Tổ hợp", math2025QuestionImage("y25m20")),
            short("y25m21", "Xem nội dung Phần III - Câu 5 trong ảnh cắt từ đề Toán 2025 mã 0124.", "1347", "Hàm số - tối ưu", math2025QuestionImage("y25m21")),
            short("y25m22", "Xem nội dung Phần III - Câu 6 trong ảnh cắt từ đề Toán 2025 mã 0124.", "94,7", "Thể tích khối tròn xoay", math2025QuestionImage("y25m22"))
          ]
        }
      ]
    },
    physics: {
      title: "Vật lí",
      code: "0201",
      duration: 50,
      source: "https://nct.edu.vn/dap-an-va-de-thi-tot-nghiep-thpt-mon-vat-ly-2025-cap-nhat-lien-tuc/",
      note:
        "Mô phỏng theo đề Vật lí 2025 mã 0201 với cấu trúc 18 câu chọn đáp án, 4 câu đúng/sai, 6 câu trả lời ngắn.",
      sections: [
        {
          title: "Phần I - Trắc nghiệm nhiều phương án lựa chọn",
          type: "single",
          points: 0.25,
          questions: buildChoiceSet("y25p", [
            ["Đơn vị của hiệu điện thế là", "B", ["ampe", "vôn", "ôm", "tesla"], "Điện học"],
            ["Đại lượng đặc trưng cho mức quán tính của vật là", "D", ["vận tốc", "gia tốc", "lực", "khối lượng"], "Cơ học"],
            ["Tần số của sóng được đo bằng", "B", ["m", "Hz", "J", "N"], "Sóng"],
            ["Hạt tải điện trong kim loại chủ yếu là", "D", ["proton", "ion dương", "neutron", "electron tự do"], "Điện học"],
            ["Nhiệt độ tuyệt đối có đơn vị", "A", ["kelvin", "celsius", "jun", "niuton"], "Nhiệt học"],
            ["Cảm ứng từ có đơn vị", "B", ["weber", "tesla", "henry", "culong"], "Từ trường"],
            ["Trong chân không, ánh sáng truyền với tốc độ xấp xỉ", "B", ["3.10^6 m/s", "3.10^8 m/s", "340 m/s", "30 m/s"], "Sóng điện từ"],
            ["Công thức động năng là", "C", ["mgh", "mv", "mv^2/2", "F.s"], "Cơ học"],
            ["Trong mạch RLC cộng hưởng, cảm kháng và dung kháng", "D", ["đều bằng 0", "luôn khác nhau", "không xác định", "bằng nhau"], "Xoay chiều"],
            ["Photon có năng lượng tỉ lệ với", "B", ["bước sóng", "tần số", "khối lượng nghỉ", "điện trở"], "Lượng tử"],
            ["Định luật Len-xơ cho biết", "A", ["chiều dòng điện cảm ứng", "độ lớn điện trở", "khối lượng riêng", "nhiệt dung"], "Cảm ứng điện từ"],
            ["Áp suất khí lí tưởng ở thể tích không đổi tỉ lệ với", "B", ["thể tích", "nhiệt độ tuyệt đối", "khối lượng mol", "diện tích"], "Khí lí tưởng"],
            ["Sự phóng xạ là quá trình", "D", ["đốt cháy hóa học", "truyền nhiệt", "nén khí", "hạt nhân tự biến đổi"], "Hạt nhân"],
            ["Độ to của âm liên quan trực tiếp đến", "B", ["màu sắc", "mức cường độ âm", "khối lượng nguồn", "nhiệt độ"], "Âm học"],
            ["Máy biến áp hoạt động dựa trên", "B", ["quang điện", "cảm ứng điện từ", "phân hạch", "nhiệt điện"], "Điện từ"],
            ["Công thức liên hệ năng lượng nghỉ và khối lượng là", "B", ["E=hf", "E=mc^2", "F=ma", "P=UI"], "Hạt nhân"],
            ["Khi sóng truyền đi, đại lượng truyền theo sóng là", "D", ["vật chất", "khối lượng", "điện tích nghỉ", "năng lượng"], "Sóng"],
            ["Trong giao thoa ánh sáng, khoảng vân phụ thuộc vào", "B", ["màu nền", "bước sóng", "khối lượng khe", "nhiệt độ phòng"], "Giao thoa"]
          ])
        },
        {
          title: "Phần II - Trắc nghiệm đúng/sai",
          type: "truefalse",
          points: "tiered",
          questions: [
            tf("y25p19", "Một vật dao động điều hòa quanh vị trí cân bằng.", "DDDD", [
              "Li độ biến thiên tuần hoàn.",
              "Vận tốc biến thiên tuần hoàn.",
              "Cơ năng bảo toàn nếu bỏ qua ma sát.",
              "Gia tốc hướng về vị trí cân bằng."
            ], "Dao động"),
            tf("y25p20", "Xét mạch điện xoay chiều RLC nối tiếp.", "DSDD", [
              "Tổng trở phụ thuộc R, ZL và ZC.",
              "Cộng hưởng xảy ra khi ZL khác ZC.",
              "Công suất tiêu thụ phụ thuộc hệ số công suất.",
              "Dòng điện hiệu dụng được đo bằng ampe kế xoay chiều."
            ], "Xoay chiều"),
            tf("y25p21", "Về sóng điện từ và ánh sáng.", "SDSD", [
              "Sóng điện từ cần môi trường vật chất để truyền trong chân không.",
              "Ánh sáng nhìn thấy là sóng điện từ.",
              "Tần số ánh sáng thay đổi khi truyền qua các môi trường.",
              "Bước sóng trong môi trường phụ thuộc chiết suất."
            ], "Sóng điện từ"),
            tf("y25p22", "Về vật lí hạt nhân.", "DDSD", [
              "Phóng xạ là quá trình tự phát.",
              "Độ hụt khối liên quan đến năng lượng liên kết.",
              "Hạt nhân càng nặng luôn càng bền vững tuyệt đối.",
              "Phân hạch có thể giải phóng năng lượng."
            ], "Hạt nhân")
          ]
        },
        {
          title: "Phần III - Trả lời ngắn",
          type: "short",
          points: 0.25,
          questions: [
            short("y25p23", "Một đại lượng vật lí trong thí nghiệm được đo là 3,25 m sau khi làm tròn đến hàng phần trăm. Hãy nhập giá trị theo đơn vị m.", "3,25", "Đo lường", diagramMotion(), "Đề yêu cầu nhập theo đơn vị m, đáp án là 3,25."),
            short("y25p24", "Một photon có năng lượng tính được là 3,29.10^-19 J. Hãy nhập phần hệ số trước 10^-19 J.", "3,29", "Lượng tử", diagramPhoton(), "Nếu E=3,29.10^-19 J thì hệ số cần nhập là 3,29."),
            short("y25p25", "Một khoảng cách trong thí nghiệm giao thoa đo được là 1,48 mm. Hãy nhập giá trị theo đơn vị mm.", "1,48", "Giao thoa", diagramWave("i=1,48 mm", "Dữ kiện mô phỏng"), "Đề yêu cầu đơn vị mm, đáp án là 1,48."),
            short("y25p26", "Một đại lượng điện áp hãm trong thí nghiệm quang điện có giá trị 0,15 V. Hãy nhập giá trị theo đơn vị V.", "0,15", "Quang điện", diagramPhoton(), "Đề yêu cầu nhập theo V, đáp án là 0,15."),
            short("y25p27", "Một hệ số hiệu suất sau khi đổi đơn vị được 0,31. Hãy nhập hệ số không kèm đơn vị.", "0,31", "Hiệu suất", diagramImpedance(), "Hệ số không có đơn vị, đáp án là 0,31."),
            short("y25p28", "Một thiết bị có tần số dao động f=8000 Hz. Hãy nhập tần số theo đơn vị Hz.", "8000", "Dao động", diagramWave("lambda", "f=8000 Hz"), "Đề yêu cầu đơn vị Hz, đáp án là 8000.")
          ]
        }
      ]
    },
    informatics: {
      title: "Tin học",
      code: "THAM-KHAO-2025",
      duration: 50,
      source: "https://thpthoaiduca.hanoi.edu.vn/mon-tin-hoc/de-thi-tham-khao-ky-thi-tot-nghiep-thpt-tu-nam-2025-mon-tin-hoc/ctmb/23796/23430",
      note:
        "Cập nhật theo đề tham khảo kỳ thi tốt nghiệp THPT từ năm 2025 môn Tin học. Câu hỏi nhập dạng text; chỉ giữ ảnh cho câu có bảng mã Python/C++.",
      sections: [
        {
          title: "Phần I - Trắc nghiệm nhiều phương án lựa chọn",
          type: "single",
          points: 0.25,
          questions: buildChoiceSet("y25i", [
            ["Khả năng nào sau đây không là đặc trưng của AI?", "D", ["Học.", "Hiểu ngôn ngữ.", "Suy luận.", "Luyện thể hình."], "AI"],
            ["Thiết bị nào sau đây thường được tích hợp trợ lý ảo?", "B", ["Máy rút tiền tự động ATM.", "Điện thoại thông minh.", "Chuông báo cháy.", "Máy quét mã vạch."], "AI"],
            ["Trường hợp nào sau đây không thể hiện rõ ứng dụng của AI trong giáo dục?", "C", ["Mô phỏng các thí nghiệm vật lí trên máy tính bằng đa phương tiện.", "Lập kế hoạch học tập cho từng học sinh dựa trên dữ liệu về người học.", "Sao lưu dữ liệu của máy tính cá nhân ra thiết bị nhớ ngoài.", "Sử dụng chat GPT để tìm kiếm lời giải cho một bài toán."], "AI"],
            ["Sự phát triển của AI không dẫn đến nguy cơ nào sau đây?", "A", ["Tất cả các lập trình viên sẽ bị mất việc do AI có khả năng lập trình.", "Người dùng bị lừa đảo qua mạng do kẻ xấu lợi dụng nội dung giả mạo của AI.", "Quyền riêng tư bị xâm phạm do AI có khả năng thu thập dữ liệu cá nhân.", "Các hệ thống mạng bị đe dọa do AI có khả năng khai thác các lỗ hổng bảo mật."], "AI"],
            ["Thiết bị nào sau đây có chức năng chính là để kết nối không dây trong một mạng cục bộ?", "D", ["Router.", "Switch.", "Hub.", "Access Point."], "Mạng"],
            ["LAN là loại mạng nào sau đây?", "A", ["Mạng cục bộ.", "Mạng diện rộng.", "Mạng toàn cầu.", "Mạng thành phố."], "Mạng"],
            ["Một phòng máy tính của nhà trường được kết nối mạng LAN giữa 01 máy giáo viên (GV) và các máy học sinh (HS). Phòng máy được cấp thêm một máy in có cổng giao tiếp với máy tính qua cổng USB. Các công việc cần làm: (1) Kết nối và cài đặt máy in trên máy GV; (2) Tìm và cài đặt máy in trên mạng cho các máy HS; (3) Chia sẻ quyền truy cập máy in qua mạng từ máy GV. Phương án nào nêu đúng thứ tự thực hiện?", "B", ["1 → 2 → 3.", "1 → 3 → 2.", "3 → 1 → 2.", "3 → 2 → 1."], "Mạng"],
            ["Phương án nào sau đây nêu đúng chức năng chính của Modem?", "B", ["Kết nối có dây hoặc không dây các thiết bị trong mạng diện rộng.", "Chuyển đổi tín hiệu hai chiều giữa các thiết bị truy cập Internet và ISP.", "Truy cập vào tài nguyên mạng mà không cần sử dụng dây cáp.", "Chuyển tiếp dữ liệu giữa các thiết bị trong cùng một mạng LAN."], "Mạng"],
            ["Thuộc tính nào sau đây của thẻ <img> trong HTML xác định văn bản thay thế cho hình ảnh nếu hình ảnh không thể hiển thị khi duyệt web?", "C", ["alter", "text", "alt", "error"], "Web"],
            ["Trong CSS, thuộc tính nào sau đây được sử dụng để thiết lập màu nền cho một phần tử HTML?", "A", ["background-color", "color-background", "background", "background-clr"], "Web"],
            ["Phương án nào sau đây nêu đúng cú pháp khai báo CSS ngoài (ngoại tuyến) trong một đoạn mã HTML?", "A", ['<link href="tentep.css" rel="stylesheet">', '<style link="tentep.css" rel="stylesheet">', '<css link="tentep.css" rel="stylesheet">', '<link src="tentep.css" rel="stylesheet">'], "Web"],
            ["Đoạn mã HTML nào sau đây tạo liên kết đến Cổng thông tin điện tử của Chính phủ có địa chỉ https://www.chinhphu.vn?", "A", ['<a href="https://www.chinhphu.vn">Chính phủ</a>', '<a name="https://www.chinhphu.vn">Chính phủ</a>', '<a url="https://www.chinhphu.vn">Chính phủ</a>', '<a "https://www.chinhphu.vn">Chính phủ</a>'], "Web"],
            ["Xét dòng lệnh sau trong một đoạn mã HTML để tạo bảng: <tr> <td> Họ tên </td> <td> Tuổi </td> </tr>. Phương án nào nêu đúng ý nghĩa của dòng lệnh trên?", "A", ["Tạo 1 hàng có 2 cột trong bảng.", "Tạo 1 cột có 2 hàng trong bảng.", "Tạo 2 hàng, mỗi hàng có 1 cột.", "Tạo tiêu đề cho 2 cột của bảng."], "Web"],
            ["Cho bộ chọn được khai báo trong thẻ <style> thuộc phần <head> của một trang web như sau: .mark{color: red; font-weight: bold; font-size: 13px;}. Phương án nào nêu đúng phạm vi áp dụng của bộ chọn trên?", "B", ["Tất cả các phần tử trong trang web.", 'Các phần tử có giá trị thuộc tính class là "mark".', 'Chỉ các phần tử có định danh (id) là "mark".', 'Chỉ các phần tử có tên là "mark".'], "Web"],
            ["Phương án nào sau đây chỉ ra đúng cặp thẻ HTML để hiển thị một danh sách học sinh trong lớp được đánh số thứ tự từ 10?", "B", ['<ul type="10">...</ul>', '<ol start="10">...</ol>', '<ol type="10">...</ol>', '<ul start="10">...</ul>'], "Web"],
            ["Đoạn mã HTML nào sau đây phù hợp để tạo một phần tử cho phép nhập mật khẩu trong một biểu mẫu đăng nhập?", "B", ['<input type="text" name="password">', '<input type="password" name="password">', '<textarea name="password"></textarea>', '<textarea type="password"></textarea>'], "Web"],
            ["Khi thực hiện đoạn mã HTML sau, văn bản \"Hôm nay có bão\" hiển thị theo định dạng nào?\n<head><style>\nh1{color: blue; font-size: 13px}\nh1{color: green; font-size: 14px}\n</style></head>\n<body><h1>Hôm nay có bão</h1></body>", "C", ["Chữ màu xanh dương, kích thước 14px.", "Chữ màu xanh dương, kích thước 13px.", "Chữ màu xanh lá, kích thước 14px.", "Chữ màu xanh lá, kích thước 13px."], "Web"],
            ["Chọn một trong hai ngôn ngữ Python hoặc C++ để xem xét đoạn chương trình sau. Phương án nào dưới đây nêu đúng giá trị của S sau khi thực hiện đoạn chương trình trên?", "C", ["30.", "29.", "14.", "13."], "Lập trình", tin2025CodeImage("q18")],
            ["Hành vi nào sau đây thể hiện tính nhân văn trong giao tiếp trên không gian mạng?", "B", ["Sử dụng ngôn từ một cách tùy thích khi tham gia bình luận trực tuyến.", "Tôn trọng quyền riêng tư của người khác khi chia sẻ thông tin cá nhân.", "Chia sẻ thông tin chưa được kiểm chứng để nhằm thu hút lượt tương tác.", "Sử dụng không gian mạng để chỉ trích người khác một cách gay gắt."], "Văn hóa số"],
            ["Hành vi nào sau đây bị xem là vi phạm pháp luật trên không gian mạng?", "A", ["Làm tắc nghẽn hệ thống mạng của nhà trường.", "Không trả lời tin nhắn ngay lập tức.", "Tải phần mềm nguồn mở để sử dụng.", "Gửi email cho bạn bè mà không ghi tiêu đề."], "An toàn thông tin"],
            ["Việc tự ý đăng tải hình ảnh của người khác lên mạng xã hội vi phạm quyền về vấn đề nào dưới đây?", "B", ["Tự do ngôn luận.", "Bảo mật thông tin cá nhân.", "Sử dụng hình ảnh công khai.", "Phản hồi của người tiêu dùng."], "An toàn thông tin"],
            ["Công việc nào dưới đây thuộc nhóm nghề sửa chữa và bảo trì máy tính?", "B", ["Thiết kế và xây dựng hệ điều hành.", "Cài đặt hoặc gỡ bỏ hệ điều hành.", "Phát triển phần mềm di động.", "Xây dựng các ứng dụng mạng."], "Nghề nghiệp"],
            ["Công việc nào dưới đây thuộc nghề quản trị mạng?", "A", ["Bảo đảm hệ thống mạng hoạt động an toàn.", "Thiết kế và xây dựng các ứng dụng di động.", "Thiết kế cơ sở dữ liệu phân tán trên mạng.", "Phát triển phần mềm trò chơi trực tuyến."], "Nghề nghiệp"],
            ["Lí do nào sau đây là lí do chủ yếu nhất của sự gia tăng nhu cầu tuyển dụng vị trí sửa chữa và bảo trì máy tính?", "A", ["Máy tính ngày càng được sử dụng rộng rãi trong xã hội hiện đại.", "Nhu cầu trang bị máy tính có cấu hình cao để chạy các ứng dụng AI.", "Nhiều trường đại học đào tạo về lĩnh vực kĩ thuật máy tính và mạng.", "Phần mềm độc hại ngày càng dễ phát tán trên không gian mạng."], "Nghề nghiệp"]
          ])
        },
        {
          title: "Phần II - Trắc nghiệm đúng/sai",
          type: "truefalse",
          points: "tiered",
          questions: [
            tf("y25i25", "Một trường học có 3 phòng máy tính cần được lắp đặt mạng LAN cho từng phòng. Nhà trường đã đăng ký sử dụng Internet với nhà cung cấp dịch vụ (ISP) và được họ lắp đặt một Modem có tích hợp cả chức năng của Router và Access Point. Một số bạn học sinh đưa ra các ý kiến sau:", "DDSS", [
              "Để thiết lập mạng LAN cho mỗi phòng máy nên sử dụng thiết bị Switch.",
              "Chức năng Router được tích hợp trong Modem để đảm bảo việc định tuyến tối ưu giữa các mạng LAN của các phòng máy.",
              "Để chia sẻ một thư mục Bài thực hành trên một máy tính với quyền được sửa cho các máy tính khác trong phòng máy, cần phải cấp duy nhất quyền read.",
              "Nếu Modem không tích hợp chức năng của Router thì cần bổ sung thiết bị Router và thứ tự kết nối các thiết bị như sau: Máy tính → Switch → Modem → Router."
            ], "Mạng"),
            tf("y25i26", "Để hỗ trợ việc quản lí thông tin nhân sự tại một công ty, một cơ sở dữ liệu quan hệ được xây dựng với 3 bảng: NHANVIEN (MaNV, HoTen, GioiTinh, NgaySinh); DUAN (MaDA, TenDA, BatDau, KetThuc); THAMGIA (MaDA, MaNV, ViTri). Một nhân viên có thể tham gia nhiều dự án và một dự án có thể có nhiều nhân viên. Khi tìm hiểu về cơ sở dữ liệu trên, một số bạn học sinh đưa ra các nhận xét sau:", "DDSD", [
              "HoTen là một trường tương ứng với một cột của bảng NHANVIEN.",
              "Bộ hai thuộc tính MaDA và MaNV là khóa chính của bảng THAMGIA.",
              "Công ty sử dụng một máy chủ để lưu dữ liệu, do vậy phải chọn hệ cơ sở dữ liệu phân tán để quản lí cơ sở dữ liệu.",
              "Câu lệnh SQL sau liệt kê họ tên các nhân viên và vị trí của họ trong dự án có mã dự án là 1: SELECT NHANVIEN.HoTen, THAMGIA.ViTri FROM NHANVIEN INNER JOIN THAMGIA ON NHANVIEN.MaNV = THAMGIA.MaNV WHERE MaDA = 1"
            ], "Cơ sở dữ liệu"),
            tf("y25i27", "Một học sinh thực hiện tạo website cho một tổ chức từ thiện gồm 3 trang web: Giới thiệu về tổ chức, Thông tin dự án, Sự kiện. Bạn học sinh đó có một số nhận xét sau đây:", "DSDS", [
              "Có thể tạo 3 trang web đã nêu từ các mẫu (theme) có sẵn của phần mềm tạo trang web.",
              "Tổ chức chia sẻ website bằng cách duy nhất là: gửi các tệp *.html của trang web qua email.",
              "Trong trang Sự kiện, để hiển thị nhiều hình ảnh trong cùng một khối, có thể sử dụng chức năng Bộ sưu tập (hoặc thanh trượt/băng chuyền hình ảnh) của phần mềm tạo trang web.",
              "Khi cần đăng lại một video về hoạt động từ thiện trên YouTube, cách làm tốt nhất là tải video đó về máy tính, sau đó chèn video vào trang web bằng chức năng Thêm hình ảnh/video của phần mềm."
            ], "Tin học ứng dụng"),
            tf("y25i28", "Cho cơ sở dữ liệu của một hiệu thuốc với 3 bảng: BENHNHAN (MaBN, TenBN, DiaChi); HOADON (MaHD, MaBN, NgayBan); THUOCBAN (MaHD, TenThuoc, SoLuong, DonGia, ThanhTien). Một số bạn học sinh có ý kiến về việc sử dụng các phần mềm khai thác cơ sở dữ liệu trên như sau:", "DDSD", [
              "Phần mềm bảng tính Excel giúp biểu thị được số lượng từng tên thuốc đã bán ở dạng biểu đồ một cách thuận lợi.",
              "Nếu bảng THUOCBAN được lưu trên một bảng tính Excel thì sử dụng hàm SUM để biết được tổng số tiền đã bán của tất cả các hóa đơn.",
              "Phần mềm quản trị cơ sở dữ liệu có thể tính được tổng số tiền bán hàng theo từng ngày dựa trên chỉ một bảng THUOCBAN.",
              "Trong phần mềm quản trị cơ sở dữ liệu, để trích xuất được các tên thuốc mua bởi bệnh nhân có MaBN xác định thì phải thực hiện thao tác truy vấn có liên kết cả 3 bảng trên thông qua các trường khóa."
            ], "Tin học ứng dụng")
          ]
        }
      ]
    }
  },
  2024: createExams2024(),
  2023: createExams2023()
};

const STUDY_GUIDES = {
  math: {
    title: "Toán",
    overview:
      "Đề Toán tốt nghiệp THPT theo chương trình mới có 22 câu nhưng độ phủ kiến thức rộng, câu hỏi dài hơn và phần đúng/sai có tính phân hóa mạnh. Học sinh cần học theo chuyên đề, nắm công thức lõi, biết nhận diện dạng bài và luyện quy trình kiểm tra từng mệnh đề thay vì chỉ học mẹo bấm máy.",
    examMap: [
      "Phần I gồm 12 câu chọn đáp án, mỗi câu 0,25 điểm: ưu tiên tốc độ, kiến thức nền và dạng quen thuộc.",
      "Phần II gồm 4 câu đúng/sai, mỗi câu 4 ý, tối đa 1 điểm: đây là phần quyết định khoảng điểm 7-9 vì cần hiểu bản chất và kiểm tra điều kiện.",
      "Phần III gồm 6 câu trả lời ngắn, mỗi câu 0,5 điểm: thường gắn với tính toán, mô hình thực tế, tổ hợp, tọa độ hoặc tối ưu.",
      "Chiến lược thời gian: 25-30 phút cho phần I, 35-40 phút cho phần II, 15-20 phút cho phần III, còn lại để soát điều kiện và nhập đáp án."
    ],
    topics: [
      ["Hàm số và đạo hàm", "Khảo sát tính đơn điệu, cực trị, giá trị lớn nhất nhỏ nhất, tiệm cận, tương giao, tiếp tuyến, bảng biến thiên, bài toán tham số. Cần thành thạo xét dấu f'(x), đọc đồ thị f(x), f'(x), hiểu khi nào hàm đồng biến/nghịch biến trên khoảng."],
      ["Mũ và logarit", "Điều kiện xác định, biến đổi logarit, phương trình và bất phương trình mũ-log, hàm số mũ-log, bài toán lãi kép, tăng trưởng dân số, suy giảm theo thời gian. Lỗi thường gặp là quên điều kiện x>0 hoặc đổi chiều bất phương trình sai."],
      ["Nguyên hàm, tích phân và ứng dụng", "Bảng nguyên hàm cơ bản, đổi biến đơn giản, tích phân từng phần ở mức nhận biết, diện tích hình phẳng, thể tích vật thể tròn xoay, bài toán vận tốc - quãng đường. Cần phân biệt nguyên hàm với tích phân xác định và biết dựng cận theo đề."],
      ["Hình học không gian cổ điển", "Góc, khoảng cách, thể tích khối chóp/lăng trụ, khối nón/trụ/cầu, thiết diện cơ bản. Khi gặp đề dài, phải xác định đáy, chiều cao, đường vuông góc và tam giác phụ trước khi tính."],
      ["Tọa độ Oxyz", "Vector, tích vô hướng, mặt phẳng, đường thẳng, mặt cầu, khoảng cách điểm - mặt phẳng, góc giữa đường thẳng và mặt phẳng, vị trí tương đối. Đây là nhóm dễ luyện theo công thức nhưng hay sai dấu và sai hệ số."],
      ["Xác suất và quy tắc đếm", "Quy tắc cộng/nhân, hoán vị, chỉnh hợp, tổ hợp, xác suất cổ điển, biến cố đối, xác suất có điều kiện ở mức cơ bản. Cần biết khi nào dùng C(n,k), A(n,k), khi nào phải chia trường hợp."],
      ["Thống kê", "Số trung bình, trung vị, tứ phân vị, khoảng biến thiên, khoảng tứ phân vị, phương sai, độ lệch chuẩn, ý nghĩa của việc cộng/nhân dữ liệu. Câu đúng/sai hay hỏi nhận xét bản chất, không chỉ tính số."],
      ["Dãy số và bài toán tài chính", "Cấp số cộng, cấp số nhân, tổng n số hạng, lãi đơn, lãi kép, gửi góp định kỳ, mô hình tăng trưởng. Cần đọc kỹ đơn vị tháng/năm và thời điểm gửi/rút tiền."],
      ["Bài toán thực tế và tối ưu", "Chuyển ngôn ngữ đời sống thành biến số, lập hàm mục tiêu, điều kiện ràng buộc, tìm cực trị trên miền cho phép. Đây thường là phần vận dụng/vận dụng cao, nên luyện quy trình hơn là học thuộc đáp án."]
    ],
    formulas: [
      ["Đạo hàm cơ bản", "(x^n)'=n.x^(n-1); (u^n)'=n.u^(n-1).u'; (sin u)'=u'cos u; (cos u)'=-u'sin u; (e^u)'=u'e^u; (ln u)'=u'/u."],
      ["Xét đơn điệu - cực trị", "f'(x)>0 thì đồng biến; f'(x)<0 thì nghịch biến; f' đổi dấu + sang - là cực đại, - sang + là cực tiểu."],
      ["Logarit", "log_a(xy)=log_a x+log_a y; log_a(x/y)=log_a x-log_a y; log_a(x^n)=nlog_a x; a^(log_a x)=x; điều kiện: a>0, a khác 1, x>0."],
      ["Cấp số", "CSC: u_n=u_1+(n-1)d, S_n=n(u_1+u_n)/2. CSN: u_n=u_1.q^(n-1), S_n=u_1(q^n-1)/(q-1) nếu q khác 1."],
      ["Tổ hợp", "P_n=n!; A(n,k)=n!/(n-k)!; C(n,k)=n!/[k!(n-k)!]; C(n,k)=C(n,n-k)."],
      ["Xác suất", "P(A)=n(A)/n(Omega); P(A đối)=1-P(A); nếu A,B độc lập thì P(AB)=P(A)P(B)."],
      ["Thể tích", "Chóp: V=1/3.Sđáy.h; lăng trụ: V=Sđáy.h; nón: V=1/3.pi.r^2.h; trụ: V=pi.r^2.h; cầu: V=4/3.pi.R^3."],
      ["Oxyz", "Mặt cầu: (x-a)^2+(y-b)^2+(z-c)^2=R^2. Mặt phẳng: Ax+By+Cz+D=0. Khoảng cách từ M(x0,y0,z0) đến mp: |Ax0+By0+Cz0+D|/sqrt(A^2+B^2+C^2)."],
      ["Tích vô hướng", "u.v=|u||v|cos(alpha)=x1x2+y1y2+z1z2; u vuông góc v khi u.v=0."]
    ],
    skills: [
      "Luôn bắt đầu bằng nhận diện chuyên đề: hàm số, logarit, tích phân, Oxyz, xác suất hay thực tế. Nhận diện đúng giúp chọn công thức nhanh.",
      "Phần I làm theo nguyên tắc: câu quen làm ngay, câu dài đánh dấu quay lại, không để một câu 0,25 điểm lấy quá 3 phút.",
      "Phần đúng/sai phải tách 4 mệnh đề thành 4 bài nhỏ. Mỗi mệnh đề cần kiểm tra điều kiện, công thức, dấu bằng, khoảng xét và đơn vị.",
      "Khi gặp tham số, nên thử đọc theo hướng điều kiện nghiệm, số giao điểm, dấu đạo hàm hoặc vị trí tương đối thay vì biến đổi tùy tiện.",
      "Với Oxyz, viết rõ vector pháp tuyến/chỉ phương, tọa độ điểm, phương trình đang dùng. Sai một dấu là hỏng cả câu.",
      "Phần trả lời ngắn cần nhập đúng định dạng: số nguyên, số thập phân, dấu phẩy/dấu chấm, làm tròn theo yêu cầu đề.",
      "Sau khi tính ra kết quả, soát bằng ước lượng: thể tích có hợp lý không, xác suất có nằm trong [0,1] không, khoảng cách có âm không."
    ],
    plan: [
      "Giai đoạn nền tảng: học lại công thức và dạng nhận biết của hàm số, logarit, tích phân, Oxyz, xác suất. Mỗi ngày làm 40-50 câu ngắn để tăng phản xạ.",
      "Giai đoạn chuyên đề: mỗi buổi chọn một chuyên đề, làm đủ 3 mức nhận biết, thông hiểu, vận dụng. Sau buổi học phải ghi lại 3 lỗi sai phổ biến nhất.",
      "Giai đoạn đúng/sai: luyện riêng dạng đúng/sai theo từng chương. Mục tiêu không phải làm nhanh trước, mà là biết vì sao từng mệnh đề đúng hoặc sai.",
      "Giai đoạn trả lời ngắn: luyện bài tính toán có đáp số, rèn làm tròn, kiểm tra điều kiện và nhập đáp án. Đây là phần dễ mất điểm vì sai nhỏ.",
      "Giai đoạn nước rút: 2 ngày một đề 90 phút, ngày còn lại sửa đề. Sửa đề phải phân loại lỗi: thiếu kiến thức, sai kỹ thuật, đọc nhầm, bấm máy sai."
    ],
    traps: [
      "Quên điều kiện xác định của logarit, căn thức, phân thức trước khi giải.",
      "Xét dấu đạo hàm sai tại nghiệm kép hoặc điểm không xác định.",
      "Nhầm cực trị của hàm số với giá trị lớn nhất/nhỏ nhất trên đoạn.",
      "Đọc đồ thị f'(x) nhưng lại kết luận như đang đọc đồ thị f(x).",
      "Nhầm công thức thể tích khối chóp, khối nón với lăng trụ, hình trụ.",
      "Sai vector pháp tuyến/chỉ phương trong Oxyz, đặc biệt khi lập mặt phẳng.",
      "Dùng tổ hợp khi bài toán có thứ tự, hoặc dùng chỉnh hợp khi bài toán không xét thứ tự.",
      "Bấm máy ra kết quả đúng nhưng làm tròn sai yêu cầu.",
      "Trong câu đúng/sai, thấy 3 ý đúng rồi đoán ý còn lại mà không kiểm tra.",
      "Đọc thiếu các từ: 'không', 'duy nhất', 'nguyên', 'dương', 'lớn nhất', 'nhỏ nhất', 'xấp xỉ'."
    ],
    targets: [
      ["Mục tiêu 5-6 điểm", "Nắm chắc công thức cơ bản, làm ổn phần I, chọn câu dễ trong phần II và không bỏ trống phần III."],
      ["Mục tiêu 7-8 điểm", "Phần I sai tối đa 1-2 câu, phần đúng/sai đạt trung bình từ 0,5 điểm/câu trở lên, phần trả lời ngắn làm được ít nhất 3-4 câu."],
      ["Mục tiêu 8,5+ điểm", "Làm chủ đúng/sai và bài thực tế, biết soát điều kiện, hạn chế sai kỹ thuật, luyện đề có bấm giờ và sửa lỗi rất kỹ."]
    ],
    deepDives: [
      ["Hàm số", "Khi luyện, luôn đi theo chuỗi: tập xác định -> đạo hàm -> nghiệm f' -> bảng xét dấu -> kết luận. Với tham số, xác định điều kiện để f' có nghiệm, nghiệm nằm trong khoảng hoặc dấu f' thỏa yêu cầu."],
      ["Oxyz", "Mỗi bài nên vẽ sơ đồ quan hệ: điểm thuộc đường/mặt nào, vector nào vuông góc, vector nào song song. Đừng vội thế số khi chưa xác định đúng pháp tuyến hoặc chỉ phương."],
      ["Xác suất", "Nếu bài có cụm 'ít nhất', 'không quá', 'có đúng', hãy cân nhắc dùng biến cố đối hoặc chia trường hợp. Viết rõ không gian mẫu để tránh đếm thiếu."],
      ["Bài thực tế", "Đặt biến có ý nghĩa, ghi đơn vị, lập hàm theo biến, tìm miền điều kiện rồi mới tối ưu. Học sinh thường sai vì bỏ qua điều kiện thực tế của biến."]
    ]
  },
  physics: {
    title: "Vật lí",
    overview:
      "Đề Vật lí 2025-2026 không chỉ kiểm tra nhớ công thức mà kiểm tra khả năng hiểu hiện tượng, đọc dữ kiện thực tế, đổi đơn vị và đánh giá từng mệnh đề đúng/sai. Học sinh muốn đạt điểm cao cần học theo mạch bản chất -> công thức -> điều kiện áp dụng -> bài toán thực tế.",
    examMap: [
      "Phần I thường gồm 18 câu chọn đáp án, mỗi câu 0,25 điểm: bao phủ lý thuyết nhận biết, thông hiểu và một số câu tính nhanh.",
      "Phần II gồm 4 câu đúng/sai, mỗi câu 4 ý, tối đa 1 điểm: phần này phân hóa mạnh vì một câu có thể trộn lý thuyết, công thức, đồ thị và nhận xét đơn vị.",
      "Phần III gồm 6 câu trả lời ngắn, mỗi câu 0,25 điểm: thường là tính toán trực tiếp hoặc vận dụng ngắn, yêu cầu nhập số chính xác và làm tròn đúng.",
      "Chiến lược thời gian: 18-22 phút cho phần I, 18-20 phút cho phần II, 8-10 phút cho phần III, còn lại để đổi đơn vị và soát dấu/kết quả."
    ],
    topics: [
      ["Dao động điều hòa", "Phương trình x=Acos(omega t+phi), vận tốc, gia tốc, chu kì, tần số, pha, năng lượng. Cần hiểu quan hệ vuông pha giữa x và v, gia tốc luôn hướng về vị trí cân bằng, cơ năng bảo toàn khi bỏ qua ma sát."],
      ["Sóng cơ và âm học", "Bước sóng, tốc độ truyền sóng, độ lệch pha, giao thoa sóng, sóng dừng, cường độ âm, mức cường độ âm. Đề hay hỏi bản chất truyền năng lượng chứ không truyền vật chất."],
      ["Dòng điện xoay chiều", "Giá trị hiệu dụng, mạch RLC nối tiếp, cảm kháng, dung kháng, tổng trở, độ lệch pha, cộng hưởng, công suất, hệ số công suất. Đây là chuyên đề trọng điểm để phân loại học sinh khá giỏi."],
      ["Điện từ học và cảm ứng điện từ", "Từ thông, suất điện động cảm ứng, chiều dòng điện cảm ứng theo Len-xơ, lực từ, thanh dẫn chuyển động trong từ trường, máy biến áp. Cần gắn công thức với chiều biến thiên của từ thông."],
      ["Nhiệt học và khí lí tưởng", "Nội năng, nhiệt lượng, công, nguyên lí I nhiệt động lực học, phương trình trạng thái khí lí tưởng, các đẳng quá trình. Cần tuyệt đối đổi nhiệt độ sang K khi dùng công thức khí."],
      ["Quang học và lượng tử ánh sáng", "Giao thoa ánh sáng, khoảng vân, photon, năng lượng lượng tử, hiện tượng quang điện, giới hạn quang điện. Cần phân biệt tần số không đổi khi ánh sáng truyền qua môi trường với bước sóng thay đổi."],
      ["Vật lí hạt nhân", "Cấu tạo hạt nhân, đồng vị, độ hụt khối, năng lượng liên kết, năng lượng liên kết riêng, phóng xạ, chu kì bán rã, phân hạch, nhiệt hạch. Câu đúng/sai hay hỏi tính bền vững và bản chất phản ứng."],
      ["Bài toán thực tế", "Lốp xe nóng lên, thiết bị điện, truyền tải điện, máy biến áp, cảm biến, pin quang điện, bức xạ, năng lượng hạt nhân. Học sinh cần biết nhận diện mô hình vật lí ẩn sau tình huống đời sống."]
    ],
    formulas: [
      ["Dao động", "omega=2pi/T=2pi.f; v=-omega A sin(omega t+phi); a=-omega^2 x; vmax=omega A; amax=omega^2 A; W=1/2.k.A^2=1/2.m.omega^2.A^2."],
      ["Sóng cơ", "v=lambda.f=lambda/T; độ lệch pha Delta phi=2pi.d/lambda; giao thoa cực đại khi d2-d1=k.lambda, cực tiểu khi d2-d1=(k+1/2)lambda."],
      ["Âm học", "I=P/S; L=10log(I/I0) dB; mức âm tăng 10 dB thì cường độ âm tăng 10 lần."],
      ["Điện xoay chiều", "ZL=omega L; ZC=1/(omega C); Z=sqrt(R^2+(ZL-ZC)^2); I=U/Z; tan phi=(ZL-ZC)/R; P=UIcos(phi)=I^2R."],
      ["Cộng hưởng RLC", "Cộng hưởng khi ZL=ZC, omega^2LC=1, Zmin=R, Imax=U/R, u và i cùng pha."],
      ["Cảm ứng điện từ", "Phi=BScos(alpha); |e|=|Delta Phi/Delta t|; với thanh dẫn chuyển động: e=Blv nếu v vuông góc B và l."],
      ["Khí lí tưởng", "pV=nRT; p1V1/T1=p2V2/T2; đẳng tích: p/T không đổi; đẳng áp: V/T không đổi; đẳng nhiệt: pV không đổi."],
      ["Nhiệt động lực học", "Delta U=Q+A nhận nếu quy ước A là công ngoại lực thực hiện lên khí; trong nhiều bài phổ thông dùng Q=Delta U+A khi A là công khí sinh ra."],
      ["Quang - lượng tử", "i=lambda D/a; epsilon=hf=hc/lambda; điều kiện quang điện: hf >= A; eUh=1/2.mvmax^2."],
      ["Hạt nhân", "Delta m=Zmp+(A-Z)mn-mhạt nhân; Wlk=Delta m.c^2; N=N0/2^(t/T); A phóng xạ=lambda N."]
    ],
    skills: [
      "Mỗi bài tính phải bắt đầu bằng bảng dữ kiện: đại lượng, giá trị, đơn vị. Đề Vật lí mất điểm rất nhiều ở đổi cm -> m, ms -> s, độ C -> K.",
      "Câu lý thuyết nên tự hỏi: nguyên nhân vật lí là gì, đại lượng nào bảo toàn, đại lượng nào biến thiên, công thức đang áp dụng trong điều kiện nào.",
      "Với câu đúng/sai, không đánh giá cả câu theo cảm giác. Hãy kiểm tra từng ý theo 4 bước: khái niệm, công thức, điều kiện, đơn vị.",
      "Với điện xoay chiều, luôn xác định mạch có R, L, C nào; đang hỏi U, I, Z, P hay pha. Không dùng công thức cộng hưởng nếu chưa có ZL=ZC.",
      "Với khí lí tưởng, đổi sang Kelvin trước rồi mới xét đẳng quá trình. Nhớ 27 độ C là 300 K, không phải 27 K.",
      "Với cảm ứng điện từ, vẽ chiều B, chiều chuyển động, chiều biến thiên từ thông trước khi kết luận chiều dòng cảm ứng.",
      "Phần trả lời ngắn nên ước lượng kết quả: công suất không âm, hiệu suất không vượt 100%, xác suất/ tỉ lệ không vượt miền hợp lí."
    ],
    plan: [
      "Giai đoạn nền tảng: học lại khái niệm và công thức cốt lõi của từng chương. Mỗi công thức phải kèm điều kiện áp dụng và đơn vị chuẩn.",
      "Giai đoạn chuyên đề: luyện riêng dao động-sóng, điện xoay chiều, nhiệt học, cảm ứng điện từ, lượng tử, hạt nhân. Sau mỗi buổi ghi lại lỗi sai theo nhóm: công thức, đơn vị, đọc đề, bấm máy.",
      "Giai đoạn đúng/sai: mỗi ngày luyện 5-8 câu đúng/sai. Mục tiêu là giải thích được từng ý sai vì sai khái niệm, sai điều kiện hay sai hệ quả.",
      "Giai đoạn trả lời ngắn: luyện các bài tính một bước và hai bước, đặc biệt phần đổi đơn vị, làm tròn và nhập đáp số.",
      "Giai đoạn nước rút: làm đề 50 phút, sửa đề 60 phút. Khi sửa, không chỉ ghi đáp án đúng mà phải ghi 'dấu hiệu nhận dạng dạng bài'."
    ],
    traps: [
      "Dùng độ C thay vì K trong phương trình khí lí tưởng.",
      "Nhầm tần số f với chu kì T, nhầm omega với f.",
      "Quên bình phương trong động năng, gia tốc cực đại hoặc năng lượng dao động.",
      "Nhầm ZL=omega L với ZC=1/(omega C), hoặc áp dụng cộng hưởng khi mạch chưa cộng hưởng.",
      "Lấy U cực đại thay cho U hiệu dụng, hoặc ngược lại.",
      "Nhầm bước sóng thay đổi với tần số thay đổi khi ánh sáng đi qua môi trường.",
      "Sai chiều dòng điện cảm ứng vì chưa xét chiều chống lại sự biến thiên từ thông.",
      "Nhầm năng lượng liên kết với năng lượng liên kết riêng.",
      "Quên đổi eV sang J hoặc MeV sang J khi tính năng lượng hạt nhân.",
      "Trong câu đúng/sai, bỏ qua từ 'luôn', 'chỉ khi', 'tỉ lệ thuận', 'tỉ lệ nghịch'."
    ],
    targets: [
      ["Mục tiêu 5-6 điểm", "Nắm chắc lý thuyết nhận biết, công thức cơ bản, đổi đơn vị SI và làm được các câu phần I quen thuộc."],
      ["Mục tiêu 7-8 điểm", "Làm tốt phần I, phần đúng/sai đạt trung bình từ 0,5 điểm/câu, xử lí được điện xoay chiều, khí lí tưởng, cảm ứng điện từ và hạt nhân mức thông hiểu."],
      ["Mục tiêu 8,5+ điểm", "Làm chủ câu đúng/sai, biết phân tích bài thực tế, hạn chế sai đơn vị, làm nhanh trả lời ngắn và giải thích được bản chất của từng hiện tượng."]
    ],
    deepDives: [
      ["Điện xoay chiều", "Dạy học sinh lập bảng R, ZL, ZC, Z trước khi tính. Khi đề hỏi công suất, phải nghĩ đến P=I^2R hoặc P=UIcos(phi). Khi đề hỏi cộng hưởng, kiểm tra ZL=ZC trước tiên."],
      ["Khí lí tưởng", "Quy trình nên là: đổi T sang K -> xác định đẳng quá trình hoặc dùng pV/T -> xét tỉ lệ tăng giảm. Các bài lốp xe thường gắn với đẳng tích gần đúng nên p tỉ lệ T."],
      ["Cảm ứng điện từ", "Không học thuộc máy móc chiều dòng điện. Hãy xác định từ thông tăng hay giảm, dòng cảm ứng sinh từ trường chống lại sự biến thiên đó, rồi mới suy ra chiều bằng quy tắc nắm tay phải."],
      ["Hạt nhân", "Tách rõ 3 câu hỏi: phản ứng có bảo toàn số khối/điện tích không, năng lượng tỏa hay thu dựa vào khối lượng trước-sau, và hạt nhân nào bền hơn dựa vào năng lượng liên kết riêng."],
      ["Câu đúng/sai", "Một mệnh đề vật lí đúng phải đúng cả về khái niệm, công thức, điều kiện và đơn vị. Chỉ cần sai một trong bốn lớp này thì mệnh đề sai."]
    ]
  },
  informatics: {
    title: "Tin học",
    overview:
      "Đề Tin học 2025-2026 là dạng đề đọc hiểu hệ thống: câu hỏi thường đặt trong bối cảnh website, bệnh viện, vận tải, cơ sở dữ liệu, AI hoặc an toàn thông tin. Muốn đạt điểm cao, học sinh cần nắm khái niệm cốt lõi, đọc được mã Python ngắn, hiểu mô hình dữ liệu và biết phân tích quyền truy cập, luồng dữ liệu, rủi ro bảo mật.",
    examMap: [
      "Phần I thường có 24 câu trắc nghiệm 4 lựa chọn: kiểm tra nền tảng Python, thuật toán, cơ sở dữ liệu, web, mạng, an toàn thông tin, AI và tin học ứng dụng.",
      "Phần II là các câu đúng/sai theo tình huống, mỗi câu có 4 ý: thường yêu cầu phân tích hệ thống thực tế, không chỉ nhớ định nghĩa.",
      "Tin học có nhiều câu dài hơn Toán/Lý về mặt ngữ cảnh. Cần đọc theo vai trò: người dùng nào, dữ liệu nào, thao tác nào, rủi ro nào.",
      "Chiến lược thời gian: 25-30 phút cho 24 câu phần I, 15-18 phút cho đúng/sai, 3-5 phút cuối soát các câu đọc code, SQL và bảo mật."
    ],
    topics: [
      ["Python cơ bản", "Biến, kiểu dữ liệu int/float/str/bool, list, tuple, dict, set, phép toán số học, phép so sánh, logic and/or/not. Cần đọc được kết quả biểu thức, chỉ số mảng và phép chia //, %, **."],
      ["Rẽ nhánh, vòng lặp và hàm", "if/elif/else, for, while, range, break/continue, hàm có tham số và giá trị trả về. Đề hay cho đoạn mã ngắn và hỏi kết quả sau vài vòng lặp."],
      ["Cấu trúc dữ liệu", "List dùng cho dãy có thứ tự, dict lưu cặp khóa-giá trị, set lưu tập không trùng, tuple thường không thay đổi. Cần biết thao tác thêm, truy cập, duyệt, kiểm tra phần tử."],
      ["Thuật toán", "Tìm kiếm tuần tự, tìm kiếm nhị phân, sắp xếp, mô phỏng thuật toán, độ phức tạp O(1), O(log n), O(n), O(n^2). Cần biết điều kiện dữ liệu đã sắp xếp khi dùng tìm kiếm nhị phân."],
      ["Cơ sở dữ liệu quan hệ", "Bảng, bản ghi, trường, kiểu dữ liệu, khóa chính, khóa ngoại, quan hệ một-một, một-nhiều, nhiều-nhiều. Cần hiểu vì sao cần chuẩn hóa dữ liệu và tránh trùng lặp."],
      ["SQL cơ bản", "SELECT, FROM, WHERE, ORDER BY, GROUP BY ở mức nhận biết, điều kiện AND/OR, lọc theo chuỗi/số/ngày. Đề thường hỏi câu lệnh nào lấy đúng dữ liệu theo yêu cầu."],
      ["Web và hệ thống thông tin", "HTML tạo cấu trúc, CSS trình bày, JavaScript tạo tương tác, form nhập dữ liệu, client-server, request-response, HTTP/HTTPS, cookie/session."],
      ["Mạng máy tính", "IP, tên miền, DNS, LAN, Internet, router, server, client, giao thức truyền dữ liệu. Cần phân biệt địa chỉ IP, URL, tên miền và vai trò máy chủ."],
      ["An toàn thông tin", "Mật khẩu mạnh, xác thực nhiều yếu tố, phân quyền, mã hóa, HTTPS, sao lưu, mã độc, lừa đảo, bảo vệ dữ liệu cá nhân. Đây là nhóm câu rất hay xuất hiện trong tình huống thực tế."],
      ["AI và dữ liệu", "Dữ liệu huấn luyện, dữ liệu kiểm thử, mô hình, dự đoán, phân loại, sai lệch dữ liệu, đánh giá mô hình, quyền riêng tư dữ liệu. Cần tránh suy nghĩ AI luôn đúng tuyệt đối."],
      ["Tin học ứng dụng", "Bảng tính, hàm SUM/AVERAGE/COUNTIF/IF, lọc và sắp xếp dữ liệu, biểu mẫu, khai thác dữ liệu trong quản lý học sinh, bệnh viện, vận tải, bán hàng."],
      ["Phân tích hệ thống", "Xác định tác nhân, dữ liệu đầu vào/đầu ra, quy trình nghiệp vụ, luồng dữ liệu, quyền người dùng và rủi ro. Đây là năng lực quan trọng trong đề mới."]
    ],
    formulas: [
      ["Python list", "len(a), a[i], a.append(x), a.pop(), x in a, for x in a. Chỉ số bắt đầu từ 0, phần tử cuối có thể truy cập bằng a[-1]."],
      ["Python dict", "d[key], d.get(key), d[key]=value, key in d, for key in d. Dict phù hợp khi cần tra cứu theo mã học sinh, mã bệnh nhân, mã hàng."],
      ["Điều kiện", "if dieu_kien: ... elif ... else ...; toán tử logic: and đúng khi cả hai đúng, or đúng khi ít nhất một đúng, not đảo giá trị."],
      ["Vòng lặp", "for i in range(n) chạy i từ 0 đến n-1; while chạy khi điều kiện còn đúng; cần có cập nhật biến để tránh lặp vô hạn."],
      ["Tìm kiếm tuần tự", "Duyệt từng phần tử, dùng được cả khi dữ liệu chưa sắp xếp, độ phức tạp O(n)."],
      ["Tìm kiếm nhị phân", "Chỉ áp dụng khi dữ liệu đã sắp xếp; so sánh với phần tử giữa rồi bỏ một nửa phạm vi, độ phức tạp O(log n)."],
      ["SQL SELECT", "SELECT cot1, cot2 FROM bang WHERE dieu_kien ORDER BY cot; WHERE lọc bản ghi, ORDER BY sắp xếp, SELECT chọn cột cần lấy."],
      ["Khóa dữ liệu", "Khóa chính định danh duy nhất một bản ghi; khóa ngoại tham chiếu khóa chính của bảng khác để tạo liên kết."],
      ["Web", "HTML = cấu trúc; CSS = trình bày; JavaScript = tương tác; HTTPS = HTTP có mã hóa khi truyền dữ liệu."],
      ["An toàn", "Mật khẩu mạnh + xác thực nhiều yếu tố + phân quyền đúng + sao lưu định kỳ + HTTPS là nền tảng bảo vệ hệ thống."]
    ],
    skills: [
      "Đọc tình huống theo 5 câu hỏi: hệ thống làm gì, dữ liệu nào được lưu, ai được thao tác, điều kiện lọc là gì, rủi ro bảo mật nằm ở đâu.",
      "Với Python, lập bảng chạy tay gồm i, biến chính, điều kiện, giá trị sau mỗi vòng lặp. Không đoán kết quả code bằng cảm giác.",
      "Với thuật toán, hỏi trước: dữ liệu có sắp xếp chưa, cần tìm một phần tử hay xử lý toàn bộ dãy, có cần tối ưu thời gian không.",
      "Với SQL, xác định bảng, cột, điều kiện WHERE, thứ tự sắp xếp rồi mới chọn đáp án. Nhầm SELECT với WHERE là lỗi rất phổ biến.",
      "Với CSDL, vẽ nhanh quan hệ bảng nếu đề có nhiều thực thể như học sinh-lớp, bệnh nhân-lịch khám, xe-tuyến-tài xế.",
      "Với web, phân biệt dữ liệu xử lý ở client và server. Dữ liệu nhạy cảm phải được kiểm tra quyền ở server, không chỉ ẩn trên giao diện.",
      "Với an toàn thông tin, ưu tiên nguyên tắc tối thiểu quyền: người dùng chỉ được xem/sửa dữ liệu đúng vai trò.",
      "Với AI, kiểm tra dữ liệu huấn luyện có đại diện không, có sai lệch không, có cần đánh giá bằng dữ liệu kiểm thử không."
    ],
    plan: [
      "Giai đoạn nền tảng: ôn Python, kiểu dữ liệu, rẽ nhánh, vòng lặp, hàm. Mỗi ngày đọc 10 đoạn code ngắn và tự chạy tay.",
      "Giai đoạn thuật toán: luyện tìm kiếm, sắp xếp, mô phỏng vòng lặp, độ phức tạp. Mỗi dạng cần biết điều kiện áp dụng và dấu hiệu nhận dạng.",
      "Giai đoạn dữ liệu: học CSDL quan hệ, khóa chính/khóa ngoại, SQL SELECT/WHERE/ORDER BY, bài toán quản lý học sinh, bệnh viện, vận tải.",
      "Giai đoạn hệ thống: ôn web, mạng, client-server, HTTP/HTTPS, cookie/session, phân quyền và an toàn thông tin.",
      "Giai đoạn AI và tình huống: luyện câu đọc hiểu về mô hình AI, dữ liệu huấn luyện, dữ liệu kiểm thử, sai lệch dữ liệu và quyền riêng tư.",
      "Giai đoạn nước rút: làm đề 50 phút, sửa đề bằng cách ghi rõ lỗi: sai Python, sai thuật toán, sai SQL, sai bảo mật hay đọc thiếu dữ kiện."
    ],
    traps: [
      "Nhầm HTML với CSS: HTML tạo cấu trúc, CSS trình bày giao diện, JavaScript tạo tương tác.",
      "Quên chỉ số Python bắt đầu từ 0, dẫn đến sai kết quả khi truy cập list.",
      "Nhầm / với // và %, đặc biệt trong câu đọc hiểu biểu thức Python.",
      "Vòng while thiếu cập nhật biến làm lặp vô hạn nhưng học sinh vẫn chọn như vòng lặp kết thúc bình thường.",
      "Dùng tìm kiếm nhị phân cho dữ liệu chưa sắp xếp.",
      "Nhầm khóa chính với khóa ngoại, hoặc nghĩ khóa chính được trùng lặp.",
      "Nhầm SELECT là lọc điều kiện, trong khi WHERE mới là phần lọc bản ghi.",
      "Cho rằng ẩn nút trên giao diện là đủ bảo mật, trong khi server vẫn phải kiểm tra quyền.",
      "Cho rằng AI luôn đúng tuyệt đối hoặc không cần dữ liệu kiểm thử.",
      "Bỏ qua dữ liệu cá nhân trong tình huống bệnh viện, trường học, tài khoản người dùng.",
      "Đọc thiếu các từ: 'chỉ', 'tất cả', 'ít nhất', 'không được', 'đã sắp xếp', 'duy nhất'."
    ],
    targets: [
      ["Mục tiêu 5-6 điểm", "Nắm chắc khái niệm cơ bản, Python đơn giản, thuật toán nhận biết, SQL SELECT/WHERE và các nguyên tắc bảo mật phổ thông."],
      ["Mục tiêu 7-8 điểm", "Đọc được code có vòng lặp, phân biệt cấu trúc dữ liệu, hiểu khóa chính/khóa ngoại, xử lý câu đúng/sai về hệ thống thực tế."],
      ["Mục tiêu 8,5+ điểm", "Phân tích tốt tình huống dài, nhận diện rủi ro bảo mật, hiểu bản chất AI/dữ liệu, chạy tay thuật toán chính xác và hạn chế lỗi đọc nhầm."]
    ],
    deepDives: [
      ["Đọc code Python", "Không đọc từ trên xuống một lần rồi đoán. Hãy lập bảng biến, chạy từng vòng lặp, ghi giá trị sau mỗi lần cập nhật. Với list, luôn kiểm tra chỉ số bắt đầu từ 0 và độ dài len(a)."],
      ["Thuật toán", "Khi đề hỏi thuật toán phù hợp, hãy nhìn trạng thái dữ liệu. Dữ liệu chưa sắp xếp thì tìm kiếm tuần tự an toàn hơn; dữ liệu đã sắp xếp và cần tìm nhanh thì nghĩ đến tìm kiếm nhị phân."],
      ["Cơ sở dữ liệu", "Tách đề thành thực thể và quan hệ. Ví dụ bệnh nhân-lịch khám-bác sĩ là nhiều bảng liên kết bằng khóa. Khóa chính định danh duy nhất, khóa ngoại tạo liên hệ giữa bảng."],
      ["SQL", "Quy trình đọc SQL: SELECT lấy cột nào, FROM từ bảng nào, WHERE lọc điều kiện gì, ORDER BY sắp xếp theo cột nào. Nếu đề hỏi 'danh sách học sinh lớp 12A1', điều kiện thường nằm ở WHERE."],
      ["Web và bảo mật", "Form gửi dữ liệu từ client lên server. Dữ liệu nhạy cảm như mật khẩu, hồ sơ bệnh án, điểm số cần HTTPS, phân quyền, kiểm tra phía server và không lưu mật khẩu dạng văn bản gốc."],
      ["AI và dữ liệu", "AI chỉ học từ dữ liệu được cung cấp. Nếu dữ liệu thiếu đại diện hoặc sai lệch, mô hình dự đoán có thể sai. Kết quả AI cần được đánh giá, không xem là chân lý tuyệt đối."]
    ]
  }
};

const SUBJECT_CATALOG = {
  math: { title: "Toán" },
  physics: { title: "Vật lí" },
  informatics: { title: "Tin học" }
};

const INFORMATICS_EXAM_YEARS = new Set(["2025", "2026"]);

const state = {
  year: "2026",
  subjectId: "math",
  mode: "practice",
  examStarted: false,
  answers: {},
  submitted: false,
  intervalId: null,
  endsAt: null
};

const subjectList = document.querySelector("#subjectList");
const subjectPanel = document.querySelector("#subjectPanel");
const yearList = document.querySelector("#yearList");
const practiceModeBtn = document.querySelector("#practiceModeBtn");
const studyModeBtn = document.querySelector("#studyModeBtn");
const examCode = document.querySelector("#examCode");
const timer = document.querySelector("#timer");
const timerNote = document.querySelector("#timerNote");
const sourceTitle = document.querySelector("#sourceTitle");
const sourceText = document.querySelector("#sourceText");
const sourceLink = document.querySelector("#sourceLink");
const subjectMeta = document.querySelector("#subjectMeta");
const subjectTitle = document.querySelector("#subjectTitle");
const questionNav = document.querySelector("#questionNav");
const examForm = document.querySelector("#examForm");
const studyGuide = document.querySelector("#studyGuide");
const resultBox = document.querySelector("#resultBox");
const submitBtn = document.querySelector("#submitBtn");
const resetBtn = document.querySelector("#resetBtn");

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function q(id, prompt, answer, options, topic, figure = "") {
  return { id, prompt, answer, options, topic, figure };
}

function tf(id, prompt, answer, statements, topic, figure = "") {
  return { id, prompt, answer, statements, topic, figure };
}

function short(id, prompt, answer, topic, figure = "", solution = "") {
  return { id, prompt, answer, topic, figure, solution };
}

function pdfQuestionImage(names, alt) {
  const imageNames = Array.isArray(names) ? names : [names];
  return imageNames
    .map((name) => `<img class="pdf-crop" src="data/toan/2026/crops/${name}.png?v=20260709-0914" alt="${alt}" loading="lazy" />`)
    .join("");
}

function pdfSolutionImage(names, alt) {
  const imageNames = Array.isArray(names) ? names : [names];
  return imageNames
    .map((name) => `<img class="pdf-crop solution-crop" src="data/toan/2026/solutions/${name}.png" alt="${alt}" loading="lazy" />`)
    .join("");
}

function math2025QuestionImage(name) {
  return `<img class="pdf-crop" src="data/toan/2025/crops/${name}.jpg?v=20260709-0945" alt="Đề Toán 2025 mã 0124 ${name} cắt từ MathVN" loading="lazy" />`;
}

function math2025SolutionImage(name) {
  return `<img class="pdf-crop solution-crop" src="data/toan/2025/solutions/${name}.jpg" alt="Lời giải Toán 2025 mã 0124 ${name} cắt từ MathVN" loading="lazy" />`;
}

function tin2026Image(name) {
  return `<img class="pdf-crop" src="data/tin/2026/images/${name}.png?v=20260709-1125" alt="Đoạn chương trình đề Tin học 2026 mã 0525 ${name}" loading="lazy" />`;
}

function tin2025CodeImage(name) {
  return `<img class="pdf-crop" src="data/tin/2025/images/${name}.png?v=20260709-1350" alt="Đoạn chương trình đề Tin học 2025 ${name}" loading="lazy" />`;
}

function tin2025QuestionImage(name) {
  return `<img class="pdf-crop" src="data/tin/2025/crops/${name}.png?v=20260709-1245" alt="Đề Tin học 2025 ${name} cắt từ PDF" loading="lazy" />`;
}

function math2024QuestionImage(name) {
  return `<img class="pdf-crop" src="data/toan/2024/crops/${name}.png?v=20260709-0902" alt="Đề Toán 2024 mã 123 ${name} cắt từ PDF" loading="lazy" />`;
}

function math2024SolutionImage(name) {
  return `<img class="pdf-crop solution-crop" src="data/toan/2024/solutions/${name}.png?v=20260709-0902" alt="Lời giải Toán 2024 mã 123 ${name} cắt từ PDF" loading="lazy" />`;
}

function math2023QuestionImage(name) {
  return `<img class="pdf-crop" src="data/toan/2023/crops/${name}.png?v=20260709-0955" alt="Đề Toán 2023 mã 102 ${name} cắt từ PDF" loading="lazy" />`;
}

function math2023SolutionImage(name) {
  return `<img class="pdf-crop solution-crop" src="data/toan/2023/solutions/${name}.png" alt="Lời giải Toán 2023 mã 102 ${name} cắt từ PDF" loading="lazy" />`;
}

function getPdfSolutionFigure(questionId) {
  if (questionId.startsWith("y23m")) {
    return math2023SolutionImage(questionId);
  }

  if (questionId.startsWith("y24m")) {
    return math2024SolutionImage(questionId);
  }

  if (questionId.startsWith("y25m")) {
    return math2025SolutionImage(questionId);
  }

  const solutions = {
    m1: ["m1"],
    m2: ["m2"],
    m3: ["m3a", "m3b"],
    m4: ["m4"],
    m5: ["m5"],
    m6: ["m6"],
    m7: ["m7"],
    m8: ["m8"],
    m9: ["m9"],
    m10: ["m10a", "m10b"],
    m11: ["m11"],
    m12: ["m12"],
    m13: ["m13a", "m13b"],
    m14: ["m14a", "m14b"],
    m15: ["m15a", "m15b"],
    m16: ["m16a", "m16b"],
    m17: ["m17a", "m17b"],
    m18: ["m18a", "m18b"],
    m19: ["m19"],
    m20: ["m20a", "m20b"],
    m21: ["m21a", "m21b"],
    m22: ["m22a", "m22b"]
  };
  const names = solutions[questionId];
  return names ? pdfSolutionImage(names, `Lời giải chi tiết ${questionId} cắt từ PDF`) : "";
}

function buildChoiceSet(prefix, rows) {
  return rows.map((row, index) =>
    q(`${prefix}${index + 1}`, row[0], row[1], row[2], row[3], row[4] || "")
  );
}

function buildImageChoiceSet(prefix, answers, label, imageBuilder) {
  return answers.map((answer, index) => {
    const id = `${prefix}${index + 1}`;
    return q(
      id,
      `Xem nội dung Câu ${index + 1} trong ảnh cắt từ ${label}.`,
      answer,
      ["Phương án A", "Phương án B", "Phương án C", "Phương án D"],
      label,
      imageBuilder(id)
    );
  });
}

function diagramRightTriangle(a, b, start, end) {
  return `
    <svg viewBox="0 0 360 180" role="img" aria-label="Tam giác vuông minh họa đường bay">
      <line x1="50" y1="135" x2="260" y2="135" stroke="#2457d6" stroke-width="4" />
      <line x1="260" y1="135" x2="260" y2="35" stroke="#2457d6" stroke-width="4" />
      <line x1="50" y1="135" x2="260" y2="35" stroke="#c92a2a" stroke-width="4" stroke-dasharray="8 6" />
      <path d="M240 135 L240 115 L260 115" fill="none" stroke="#667085" stroke-width="2" />
      <text x="40" y="155">${start}</text>
      <text x="268" y="32">${end}</text>
      <text x="140" y="154">${a}</text>
      <text x="270" y="92">${b}</text>
      <text x="135" y="76">AB?</text>
    </svg>
  `;
}

function diagramSeats(count) {
  return `
    <svg viewBox="0 0 360 150" role="img" aria-label="Sơ đồ bốn phần tạo mã">
      ${Array.from({ length: count })
        .map((_, index) => {
          const x = 38 + index * 80;
          const labels = ["8 cách", "6 cách", "4 cách", "6 cách"];
          return `<rect x="${x}" y="45" width="62" height="44" rx="10" fill="#eef4ff" stroke="#2457d6" />
            <text x="${x + 31}" y="72" text-anchor="middle">${labels[index]}</text>`;
        })
        .join("")}
      <text x="180" y="125" text-anchor="middle">Quy tắc nhân: 8 x 6 x 4 x 6</text>
    </svg>
  `;
}

function diagramPlanePoint() {
  return `
    <svg viewBox="0 0 360 190" role="img" aria-label="Minh họa khoảng cách trong Oxyz">
      <line x1="70" y1="145" x2="300" y2="145" stroke="#667085" />
      <line x1="70" y1="145" x2="70" y2="35" stroke="#667085" />
      <line x1="70" y1="145" x2="130" y2="95" stroke="#667085" />
      <circle cx="85" cy="128" r="5" fill="#2457d6" />
      <circle cx="245" cy="58" r="5" fill="#c92a2a" />
      <line x1="85" y1="128" x2="245" y2="58" stroke="#2457d6" stroke-width="3" stroke-dasharray="7 5" />
      <text x="55" y="165">A(1;2;0)</text>
      <text x="220" y="45">B(4;6;3,15)</text>
      <text x="158" y="82">AB?</text>
      <text x="305" y="149">x</text>
      <text x="58" y="30">z</text>
      <text x="135" y="92">y</text>
    </svg>
  `;
}

function diagramParabola() {
  return `
    <svg viewBox="0 0 360 190" role="img" aria-label="Đồ thị parabol mô phỏng truy cập">
      <line x1="40" y1="155" x2="320" y2="155" stroke="#667085" />
      <line x1="55" y1="165" x2="55" y2="25" stroke="#667085" />
      <path d="M65 148 C120 38, 230 38, 300 148" fill="none" stroke="#2457d6" stroke-width="4" />
      <line x1="180" y1="45" x2="180" y2="155" stroke="#c92a2a" stroke-dasharray="6 6" />
      <text x="190" y="55">đỉnh</text>
      <text x="290" y="172">x ngày</text>
      <text x="20" y="34">P(x)</text>
    </svg>
  `;
}

function diagramBoxNet() {
  return `
    <svg viewBox="0 0 360 190" role="img" aria-label="Tấm bìa cắt góc làm hộp">
      <rect x="75" y="35" width="210" height="120" rx="6" fill="#eef4ff" stroke="#2457d6" stroke-width="3" />
      <rect x="75" y="35" width="32" height="32" fill="#fff8e6" stroke="#b7791f" />
      <rect x="253" y="35" width="32" height="32" fill="#fff8e6" stroke="#b7791f" />
      <rect x="75" y="123" width="32" height="32" fill="#fff8e6" stroke="#b7791f" />
      <rect x="253" y="123" width="32" height="32" fill="#fff8e6" stroke="#b7791f" />
      <text x="180" y="102" text-anchor="middle">V(x) lớn nhất?</text>
      <text x="88" y="57">x</text>
      <text x="267" y="57">x</text>
    </svg>
  `;
}

function diagramBoxVolume() {
  return `
    <svg viewBox="0 0 360 190" role="img" aria-label="Hộp quà không nắp có đáy 15 cm x 17 cm và chiều cao 5 cm">
      <polygon points="110,80 235,80 270,55 145,55" fill="#eef4ff" stroke="#2457d6" stroke-width="3" />
      <polygon points="110,80 235,80 235,145 110,145" fill="#eef4ff" stroke="#2457d6" stroke-width="3" />
      <polygon points="235,80 270,55 270,120 235,145" fill="#dbe7ff" stroke="#2457d6" stroke-width="3" />
      <line x1="110" y1="145" x2="235" y2="145" stroke="#c92a2a" stroke-width="3" />
      <line x1="235" y1="145" x2="270" y2="120" stroke="#c92a2a" stroke-width="3" />
      <line x1="270" y1="55" x2="270" y2="120" stroke="#c92a2a" stroke-width="3" />
      <text x="156" y="166">17 cm</text>
      <text x="255" y="142">15 cm</text>
      <text x="278" y="92">5 cm</text>
    </svg>
  `;
}

function diagramPyramid() {
  return `
    <svg viewBox="0 0 360 190" role="img" aria-label="Khối chóp có đáy và chiều cao">
      <polygon points="95,145 235,145 280,105 140,105" fill="#eef4ff" stroke="#2457d6" stroke-width="3" />
      <line x1="185" y1="38" x2="95" y2="145" stroke="#2457d6" stroke-width="3" />
      <line x1="185" y1="38" x2="235" y2="145" stroke="#2457d6" stroke-width="3" />
      <line x1="185" y1="38" x2="280" y2="105" stroke="#2457d6" stroke-width="3" />
      <line x1="185" y1="38" x2="140" y2="105" stroke="#2457d6" stroke-width="3" stroke-dasharray="6 5" />
      <line x1="185" y1="38" x2="185" y2="126" stroke="#c92a2a" stroke-width="3" />
      <path d="M174 126 L185 116 L196 126" fill="none" stroke="#667085" stroke-width="2" />
      <text x="194" y="84">h=5</text>
      <text x="145" y="164">S đáy = 18</text>
    </svg>
  `;
}

function diagramGrowth() {
  return `
    <svg viewBox="0 0 360 180" role="img" aria-label="Biểu đồ tăng trưởng cấp số nhân">
      <line x1="45" y1="145" x2="320" y2="145" stroke="#667085" />
      <line x1="55" y1="155" x2="55" y2="25" stroke="#667085" />
      <path d="M60 135 C115 128, 165 112, 210 82 C245 58, 275 43, 310 35" fill="none" stroke="#2457d6" stroke-width="4" />
      <line x1="55" y1="70" x2="320" y2="70" stroke="#c92a2a" stroke-dasharray="6 6" />
      <text x="230" y="64">ngưỡng</text>
      <text x="286" y="164">năm</text>
    </svg>
  `;
}

function diagramSignChart() {
  return `
    <svg viewBox="0 0 360 170" role="img" aria-label="Bảng xét dấu đạo hàm">
      <line x1="42" y1="55" x2="318" y2="55" stroke="#667085" />
      <line x1="42" y1="105" x2="318" y2="105" stroke="#667085" />
      <line x1="95" y1="30" x2="95" y2="135" stroke="#667085" />
      <line x1="170" y1="55" x2="170" y2="135" stroke="#667085" />
      <line x1="245" y1="55" x2="245" y2="135" stroke="#667085" />
      <text x="62" y="88">x</text>
      <text x="52" y="128">f'(x)</text>
      <text x="112" y="88">-∞</text>
      <text x="160" y="88">-1</text>
      <text x="238" y="88">2</text>
      <text x="286" y="88">+∞</text>
      <text x="128" y="128">+</text>
      <text x="203" y="128">-</text>
      <text x="278" y="128">+</text>
      <circle cx="170" cy="124" r="4" fill="#c92a2a" />
      <circle cx="245" cy="124" r="4" fill="#c92a2a" />
    </svg>
  `;
}

function diagramCubeVector() {
  return `
    <svg viewBox="0 0 360 210" role="img" aria-label="Hình lập phương minh họa vectơ">
      <polygon points="85,155 205,155 255,105 135,105" fill="#eef4ff" stroke="#2457d6" stroke-width="3" />
      <polygon points="85,65 205,65 255,15 135,15" fill="none" stroke="#2457d6" stroke-width="3" />
      <line x1="85" y1="155" x2="85" y2="65" stroke="#2457d6" stroke-width="3" />
      <line x1="205" y1="155" x2="205" y2="65" stroke="#2457d6" stroke-width="3" />
      <line x1="255" y1="105" x2="255" y2="15" stroke="#2457d6" stroke-width="3" />
      <line x1="135" y1="105" x2="135" y2="15" stroke="#2457d6" stroke-width="3" />
      <line x1="85" y1="155" x2="205" y2="155" stroke="#c92a2a" stroke-width="4" marker-end="url(#cubeArrow)" />
      <line x1="135" y1="15" x2="255" y2="15" stroke="#c92a2a" stroke-width="4" marker-end="url(#cubeArrow)" />
      <defs><marker id="cubeArrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#c92a2a" /></marker></defs>
      <text x="72" y="174">A</text><text x="208" y="174">B</text><text x="258" y="112">C</text><text x="118" y="112">D</text>
      <text x="63" y="62">A'</text><text x="205" y="62">B'</text><text x="258" y="17">C'</text><text x="115" y="17">D'</text>
    </svg>
  `;
}

function diagramCubeVectorAD() {
  return `
    <svg viewBox="0 0 360 210" role="img" aria-label="Hình lập phương minh họa vectơ AD và B'C'">
      <polygon points="85,155 205,155 255,105 135,105" fill="#eef4ff" stroke="#2457d6" stroke-width="3" />
      <polygon points="85,65 205,65 255,15 135,15" fill="none" stroke="#2457d6" stroke-width="3" />
      <line x1="85" y1="155" x2="85" y2="65" stroke="#2457d6" stroke-width="3" />
      <line x1="205" y1="155" x2="205" y2="65" stroke="#2457d6" stroke-width="3" />
      <line x1="255" y1="105" x2="255" y2="15" stroke="#2457d6" stroke-width="3" />
      <line x1="135" y1="105" x2="135" y2="15" stroke="#2457d6" stroke-width="3" />
      <line x1="85" y1="155" x2="135" y2="105" stroke="#c92a2a" stroke-width="4" marker-end="url(#cubeADArrow)" />
      <line x1="205" y1="65" x2="255" y2="15" stroke="#c92a2a" stroke-width="4" marker-end="url(#cubeADArrow)" />
      <defs><marker id="cubeADArrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#c92a2a" /></marker></defs>
      <text x="72" y="174">A</text><text x="208" y="174">B</text><text x="258" y="112">C</text><text x="118" y="112">D</text>
      <text x="63" y="62">A'</text><text x="205" y="62">B'</text><text x="258" y="17">C'</text><text x="115" y="17">D'</text>
    </svg>
  `;
}

function diagramRationalTable() {
  return `
    <svg viewBox="0 0 360 180" role="img" aria-label="Bảng biến thiên hàm phân thức có tiệm cận ngang y bằng âm 2">
      <line x1="40" y1="50" x2="320" y2="50" stroke="#667085" />
      <line x1="40" y1="100" x2="320" y2="100" stroke="#667085" />
      <line x1="95" y1="25" x2="95" y2="145" stroke="#667085" />
      <line x1="205" y1="50" x2="205" y2="145" stroke="#c92a2a" stroke-dasharray="6 5" />
      <text x="62" y="82">x</text>
      <text x="54" y="132">y</text>
      <text x="112" y="82">-∞</text>
      <text x="198" y="82">1</text>
      <text x="285" y="82">+∞</text>
      <text x="116" y="130">-2</text>
      <text x="268" y="130">-2</text>
      <path d="M120 118 C150 92, 175 72, 196 58" fill="none" stroke="#2457d6" stroke-width="3" />
      <path d="M214 142 C240 118, 270 100, 304 88" fill="none" stroke="#2457d6" stroke-width="3" />
      <text x="134" y="165">Tiệm cận ngang: y=-2</text>
    </svg>
  `;
}

function diagramRationalTableVertical0108() {
  return `
    <svg viewBox="0 0 360 180" role="img" aria-label="Bảng biến thiên hàm phân thức có tiệm cận đứng x bằng 1">
      <line x1="40" y1="50" x2="320" y2="50" stroke="#667085" />
      <line x1="40" y1="100" x2="320" y2="100" stroke="#667085" />
      <line x1="95" y1="25" x2="95" y2="145" stroke="#667085" />
      <line x1="205" y1="50" x2="205" y2="145" stroke="#c92a2a" stroke-dasharray="6 5" />
      <text x="62" y="82">x</text><text x="54" y="132">y</text>
      <text x="112" y="82">-∞</text><text x="198" y="82">1</text><text x="285" y="82">+∞</text>
      <text x="116" y="130">-2</text><text x="170" y="66">+∞</text><text x="214" y="142">-∞</text><text x="268" y="130">-2</text>
      <path d="M120 118 C150 92, 175 72, 196 58" fill="none" stroke="#2457d6" stroke-width="3" />
      <path d="M214 142 C240 118, 270 100, 304 88" fill="none" stroke="#2457d6" stroke-width="3" />
      <text x="134" y="165">Tiệm cận đứng: x=1</text>
    </svg>
  `;
}

function diagramOnlineStudyTable() {
  return `
    <table class="figure-table" aria-label="Bảng thời gian học trực tuyến">
      <tr><th>Nhóm thời gian (phút)</th><th>[10;20)</th><th>[20;30)</th><th>[30;40)</th><th>[40;50)</th><th>[50;60)</th><th>[60;70)</th></tr>
      <tr><th>Số học sinh</th><td>4</td><td>8</td><td>14</td><td>8</td><td>5</td><td>3</td></tr>
    </table>
  `;
}

function diagramOnlineStudyTable0108() {
  return `
    <table class="figure-table" aria-label="Bảng thời gian học trực tuyến mã đề 0108">
      <tr><th>Nhóm thời gian (phút)</th><th>[10;20)</th><th>[20;30)</th><th>[30;40)</th><th>[40;50)</th><th>[50;60)</th><th>[60;70)</th></tr>
      <tr><th>Số học sinh</th><td>5</td><td>7</td><td>15</td><td>6</td><td>5</td><td>4</td></tr>
    </table>
  `;
}

function diagramAiScreeningTable() {
  return `
    <table class="figure-table" aria-label="Bảng kết quả sàng lọc AI">
      <tr><th></th><th>Có bệnh</th><th>Không có bệnh</th><th>Tổng</th></tr>
      <tr><th>Nhận cảnh báo</th><td>700</td><td>300</td><td>1000</td></tr>
      <tr><th>Không nhận cảnh báo</th><td>100</td><td>8900</td><td>9000</td></tr>
      <tr><th>Tổng</th><td>800</td><td>9200</td><td>10000</td></tr>
    </table>
  `;
}

function diagramAiScreeningTable0108() {
  return `
    <table class="figure-table" aria-label="Bảng kết quả sàng lọc AI mã đề 0108">
      <tr><th></th><th>Có bệnh</th><th>Không có bệnh</th><th>Tổng</th></tr>
      <tr><th>Nhận cảnh báo</th><td>600</td><td>400</td><td>1000</td></tr>
      <tr><th>Không nhận cảnh báo</th><td>200</td><td>8800</td><td>9000</td></tr>
      <tr><th>Tổng</th><td>800</td><td>9200</td><td>10000</td></tr>
    </table>
  `;
}

function diagramCubicVariation() {
  return `
    <svg viewBox="0 0 360 180" role="img" aria-label="Bảng biến thiên hàm bậc ba">
      <line x1="40" y1="55" x2="320" y2="55" stroke="#667085" />
      <line x1="40" y1="100" x2="320" y2="100" stroke="#667085" />
      <line x1="90" y1="30" x2="90" y2="145" stroke="#667085" />
      <line x1="165" y1="55" x2="165" y2="145" stroke="#667085" />
      <line x1="245" y1="55" x2="245" y2="145" stroke="#667085" />
      <text x="60" y="85">x</text><text x="50" y="130">f'</text>
      <text x="112" y="85">-∞</text><text x="158" y="85">1</text><text x="238" y="85">9</text><text x="288" y="85">+∞</text>
      <text x="128" y="130">+</text><text x="202" y="130">-</text><text x="278" y="130">+</text>
      <text x="136" y="42">cực đại 37/3</text>
      <text x="235" y="165">cực tiểu -73</text>
    </svg>
  `;
}

function diagramCubicVariation0108() {
  return `
    <svg viewBox="0 0 360 180" role="img" aria-label="Bảng biến thiên hàm bậc ba mã đề 0108">
      <line x1="40" y1="55" x2="320" y2="55" stroke="#667085" />
      <line x1="40" y1="100" x2="320" y2="100" stroke="#667085" />
      <line x1="90" y1="30" x2="90" y2="145" stroke="#667085" />
      <line x1="165" y1="55" x2="165" y2="145" stroke="#667085" />
      <line x1="245" y1="55" x2="245" y2="145" stroke="#667085" />
      <text x="60" y="85">x</text><text x="50" y="130">f'</text>
      <text x="112" y="85">-∞</text><text x="158" y="85">1</text><text x="238" y="85">3</text><text x="288" y="85">+∞</text>
      <text x="128" y="130">+</text><text x="202" y="130">-</text><text x="278" y="130">+</text>
      <text x="136" y="42">cực đại 28/3</text>
      <text x="240" y="165">cực tiểu 8</text>
    </svg>
  `;
}

function diagramSolarStorage() {
  return `
    <svg viewBox="0 0 360 180" role="img" aria-label="Tốc độ lưu trữ điện năng theo thời gian">
      <line x1="45" y1="145" x2="320" y2="145" stroke="#667085" />
      <line x1="55" y1="155" x2="55" y2="25" stroke="#667085" />
      <path d="M55 145 C105 40, 205 40, 300 145" fill="none" stroke="#2457d6" stroke-width="4" />
      <line x1="75" y1="145" x2="75" y2="118" stroke="#c92a2a" stroke-dasharray="5 5" />
      <line x1="140" y1="145" x2="140" y2="55" stroke="#c92a2a" stroke-dasharray="5 5" />
      <line x1="235" y1="145" x2="235" y2="72" stroke="#c92a2a" stroke-dasharray="5 5" />
      <text x="285" y="164">t</text><text x="20" y="35">f(t)</text>
      <text x="69" y="163">1</text><text x="134" y="163">4</text><text x="229" y="163">7</text>
    </svg>
  `;
}

function diagramSolarStorage0108() {
  return `
    <svg viewBox="0 0 360 180" role="img" aria-label="Tốc độ lưu trữ điện năng mã đề 0108">
      <line x1="45" y1="145" x2="320" y2="145" stroke="#667085" />
      <line x1="55" y1="155" x2="55" y2="25" stroke="#667085" />
      <path d="M55 145 C105 42, 205 42, 300 145" fill="none" stroke="#2457d6" stroke-width="4" />
      <line x1="75" y1="145" x2="75" y2="118" stroke="#c92a2a" stroke-dasharray="5 5" />
      <line x1="156" y1="145" x2="156" y2="50" stroke="#c92a2a" stroke-dasharray="5 5" />
      <line x1="238" y1="145" x2="238" y2="74" stroke="#c92a2a" stroke-dasharray="5 5" />
      <text x="285" y="164">t</text><text x="20" y="35">f(t)</text>
      <text x="69" y="163">1</text><text x="150" y="163">5</text><text x="232" y="163">9</text>
    </svg>
  `;
}

function diagramDroneRing() {
  return `
    <svg viewBox="0 0 360 210" role="img" aria-label="Máy bay bay qua vành đai bảo vệ trong Oxyz">
      <ellipse cx="170" cy="125" rx="92" ry="42" fill="none" stroke="#2457d6" stroke-width="4" />
      <circle cx="170" cy="125" r="5" fill="#c92a2a" />
      <line x1="80" y1="55" x2="270" y2="145" stroke="#c92a2a" stroke-width="4" marker-end="url(#droneArrow)" />
      <circle cx="80" cy="55" r="6" fill="#2457d6" />
      <circle cx="270" cy="145" r="6" fill="#2457d6" />
      <circle cx="140" cy="85" r="6" fill="#087443" />
      <defs><marker id="droneArrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#c92a2a" /></marker></defs>
      <text x="66" y="47">M</text><text x="278" y="150">N</text><text x="145" y="78">(8;6;4)</text>
      <text x="150" y="131">O</text><text x="225" y="105">R=7</text>
    </svg>
  `;
}

function diagramDroneRing0108() {
  return `
    <svg viewBox="0 0 360 210" role="img" aria-label="Máy bay bay qua vành đai bảo vệ mã đề 0108">
      <ellipse cx="170" cy="125" rx="82" ry="38" fill="none" stroke="#2457d6" stroke-width="4" />
      <circle cx="170" cy="125" r="5" fill="#c92a2a" />
      <line x1="76" y1="58" x2="282" y2="138" stroke="#c92a2a" stroke-width="4" marker-end="url(#droneArrow0108)" />
      <circle cx="76" cy="58" r="6" fill="#2457d6" />
      <circle cx="282" cy="138" r="6" fill="#2457d6" />
      <circle cx="145" cy="85" r="6" fill="#087443" />
      <defs><marker id="droneArrow0108" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#c92a2a" /></marker></defs>
      <text x="62" y="50">M(2;11;3)</text><text x="246" y="156">N(14;2;3)</text><text x="150" y="78">(6;8;3)</text>
      <text x="150" y="131">O</text><text x="218" y="106">R=6</text>
    </svg>
  `;
}

function diagramCubeDistance() {
  return `
    <svg viewBox="0 0 360 220" role="img" aria-label="Hình lập phương ABCD.MNPQ và mặt phẳng MED">
      <polygon points="85,165 205,165 255,115 135,115" fill="#eef4ff" stroke="#2457d6" stroke-width="3" />
      <polygon points="85,75 205,75 255,25 135,25" fill="none" stroke="#2457d6" stroke-width="3" />
      <line x1="85" y1="165" x2="85" y2="75" stroke="#2457d6" stroke-width="3" />
      <line x1="205" y1="165" x2="205" y2="75" stroke="#2457d6" stroke-width="3" />
      <line x1="255" y1="115" x2="255" y2="25" stroke="#2457d6" stroke-width="3" />
      <line x1="135" y1="115" x2="135" y2="25" stroke="#2457d6" stroke-width="3" />
      <polygon points="145,165 85,75 135,115" fill="#fff8e6" stroke="#c92a2a" stroke-width="3" opacity="0.85" />
      <circle cx="255" cy="25" r="6" fill="#087443" />
      <text x="72" y="184">A</text><text x="207" y="184">B</text><text x="120" y="122">D</text><text x="67" y="72">M</text><text x="260" y="25">P</text><text x="139" y="182">E</text>
    </svg>
  `;
}

function diagramCubeDistance0108() {
  return `
    <svg viewBox="0 0 360 220" role="img" aria-label="Hình lập phương cạnh 14 và mặt phẳng MED">
      <polygon points="85,165 205,165 255,115 135,115" fill="#eef4ff" stroke="#2457d6" stroke-width="3" />
      <polygon points="85,75 205,75 255,25 135,25" fill="none" stroke="#2457d6" stroke-width="3" />
      <line x1="85" y1="165" x2="85" y2="75" stroke="#2457d6" stroke-width="3" />
      <line x1="205" y1="165" x2="205" y2="75" stroke="#2457d6" stroke-width="3" />
      <line x1="255" y1="115" x2="255" y2="25" stroke="#2457d6" stroke-width="3" />
      <line x1="135" y1="115" x2="135" y2="25" stroke="#2457d6" stroke-width="3" />
      <polygon points="145,165 85,75 135,115" fill="#fff8e6" stroke="#c92a2a" stroke-width="3" opacity="0.85" />
      <circle cx="255" cy="25" r="6" fill="#087443" />
      <text x="72" y="184">A</text><text x="207" y="184">B</text><text x="120" y="122">D</text><text x="67" y="72">M</text><text x="260" y="25">P</text><text x="139" y="182">E</text>
      <text x="150" y="205">cạnh = 14</text>
    </svg>
  `;
}

function diagramResidueGrid() {
  return `
    <svg viewBox="0 0 360 220" role="img" aria-label="Sơ đồ 15 ô chia theo số dư modulo 5">
      ${Array.from({ length: 5 }).map((_, row) =>
        Array.from({ length: 5 - row }).map((__, col) => {
          const x = 72 + col * 44 + row * 22;
          const y = 35 + row * 34;
          return `<rect x="${x}" y="${y}" width="34" height="26" rx="6" fill="#eef4ff" stroke="#2457d6" />
            <text x="${x + 17}" y="${y + 18}" text-anchor="middle">□</text>`;
        }).join("")
      ).join("")}
      <text x="180" y="202" text-anchor="middle">Mỗi hàng/cột không trùng số dư khi chia cho 5</text>
    </svg>
  `;
}

function diagramBeadVolume0108() {
  return `
    <svg viewBox="0 0 360 190" role="img" aria-label="Hạt cườm có lỗ khoan bán kính 0,1 cm">
      <ellipse cx="180" cy="95" rx="110" ry="62" fill="#eef4ff" stroke="#2457d6" stroke-width="3" />
      <rect x="70" y="88" width="220" height="14" fill="#fff8e6" stroke="#b7791f" stroke-width="3" />
      <line x1="55" y1="95" x2="305" y2="95" stroke="#c92a2a" stroke-dasharray="6 5" />
      <text x="133" y="74">elip quay quanh Ox</text>
      <text x="142" y="127">lỗ khoan r=0,1 cm</text>
    </svg>
  `;
}

function diagramBeadVolume() {
  return `
    <svg viewBox="0 0 360 190" role="img" aria-label="Hạt cườm tạo bởi khối tròn xoay và lỗ khoan">
      <ellipse cx="180" cy="95" rx="110" ry="62" fill="#eef4ff" stroke="#2457d6" stroke-width="3" />
      <rect x="70" y="82" width="220" height="26" fill="#fff8e6" stroke="#b7791f" stroke-width="3" />
      <line x1="55" y1="95" x2="305" y2="95" stroke="#c92a2a" stroke-dasharray="6 5" />
      <text x="133" y="74">elip quay quanh Ox</text>
      <text x="142" y="127">lỗ khoan r=0,2 cm</text>
    </svg>
  `;
}

function diagramDodecagonSquares() {
  return `
    <svg viewBox="0 0 360 220" role="img" aria-label="Đa giác đều 12 cạnh và ba hình vuông nội tiếp">
      <polygon points="180,25 220,36 249,65 260,105 249,145 220,174 180,185 140,174 111,145 100,105 111,65 140,36" fill="#eef4ff" stroke="#2457d6" stroke-width="3" />
      <polygon points="180,25 249,65 180,185 111,145" fill="none" stroke="#c92a2a" stroke-width="3" />
      <polygon points="220,36 260,105 140,174 100,105" fill="none" stroke="#087443" stroke-width="3" />
      <polygon points="249,145 220,174 111,65 140,36" fill="none" stroke="#b7791f" stroke-width="3" />
      <text x="110" y="205">3 hình vuông từ 12 đỉnh</text>
    </svg>
  `;
}

function diagramFarmTable() {
  return `
    <table class="figure-table" aria-label="Bảng bán hàng nông trại">
      <tr><th>Ngày</th><th>Rau muống (kg)</th><th>Bí xanh (kg)</th><th>Cà chua (kg)</th><th>Tiền (nghìn đồng)</th></tr>
      <tr><td>Thứ Tư</td><td>19</td><td>14</td><td>10</td><td>600</td></tr>
      <tr><td>Thứ Năm</td><td>20</td><td>12</td><td>8</td><td>540</td></tr>
      <tr><td>Thứ Sáu</td><td>25</td><td>12</td><td>7</td><td>570</td></tr>
      <tr><td>Thứ Bảy</td><td>50</td><td>25</td><td>20</td><td>?</td></tr>
    </table>
  `;
}

function diagramFarmTable0108() {
  return `
    <table class="figure-table" aria-label="Bảng bán hàng nông trại mã đề 0108">
      <tr><th>Ngày</th><th>Rau muống (kg)</th><th>Bí xanh (kg)</th><th>Cà chua (kg)</th><th>Tiền (nghìn đồng)</th></tr>
      <tr><td>Thứ Tư</td><td>19</td><td>15</td><td>10</td><td>615</td></tr>
      <tr><td>Thứ Năm</td><td>20</td><td>12</td><td>8</td><td>540</td></tr>
      <tr><td>Thứ Sáu</td><td>25</td><td>12</td><td>7</td><td>570</td></tr>
      <tr><td>Thứ Bảy</td><td>50</td><td>30</td><td>20</td><td>?</td></tr>
    </table>
  `;
}

function diagramProfitCurve() {
  return `
    <svg viewBox="0 0 360 190" role="img" aria-label="Đồ thị lợi nhuận đạt cực đại tại 100 tấn">
      <line x1="45" y1="150" x2="320" y2="150" stroke="#667085" />
      <line x1="55" y1="160" x2="55" y2="25" stroke="#667085" />
      <path d="M60 148 C110 88, 155 38, 205 62 C250 84, 285 132, 310 168" fill="none" stroke="#2457d6" stroke-width="4" />
      <line x1="180" y1="55" x2="180" y2="150" stroke="#c92a2a" stroke-dasharray="6 5" />
      <text x="190" y="62">x=100</text>
      <text x="196" y="36">Pmax=1990</text>
      <text x="292" y="168">x</text><text x="22" y="35">P</text>
    </svg>
  `;
}

function diagramProfitCurve0108() {
  return `
    <svg viewBox="0 0 360 190" role="img" aria-label="Đồ thị lợi nhuận mã đề 0108 đạt cực đại 3980">
      <line x1="45" y1="150" x2="320" y2="150" stroke="#667085" />
      <line x1="55" y1="160" x2="55" y2="25" stroke="#667085" />
      <path d="M60 148 C110 88, 155 38, 205 62 C250 84, 285 132, 310 168" fill="none" stroke="#2457d6" stroke-width="4" />
      <line x1="180" y1="55" x2="180" y2="150" stroke="#c92a2a" stroke-dasharray="6 5" />
      <text x="190" y="62">x=100</text>
      <text x="196" y="36">Pmax=3980</text>
      <text x="292" y="168">x</text><text x="22" y="35">P</text>
    </svg>
  `;
}

function diagramMotion() {
  return `
    <svg viewBox="0 0 360 160" role="img" aria-label="Vật chuyển động thẳng">
      <line x1="45" y1="115" x2="310" y2="115" stroke="#667085" stroke-width="2" />
      <rect x="90" y="75" width="58" height="38" rx="8" fill="#eef4ff" stroke="#2457d6" stroke-width="3" />
      <line x1="155" y1="94" x2="245" y2="94" stroke="#c92a2a" stroke-width="4" marker-end="url(#arrowMotion)" />
      <defs>
        <marker id="arrowMotion" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
          <path d="M0,0 L0,6 L9,3 z" fill="#c92a2a" />
        </marker>
      </defs>
      <text x="94" y="66">m=2 kg</text>
      <text x="185" y="84">v=3 m/s</text>
    </svg>
  `;
}

function diagramCircuit(labelR, labelI) {
  return `
    <svg viewBox="0 0 360 170" role="img" aria-label="Mạch điện điện trở">
      <path d="M70 85 H130 M230 85 H290 M70 85 V130 H290 V85" fill="none" stroke="#2457d6" stroke-width="4" />
      <rect x="130" y="62" width="100" height="46" rx="8" fill="#fff8e6" stroke="#b7791f" stroke-width="3" />
      <circle cx="70" cy="85" r="5" fill="#2457d6" />
      <circle cx="290" cy="85" r="5" fill="#2457d6" />
      <text x="153" y="91">${labelR}</text>
      <text x="135" y="150">${labelI}</text>
    </svg>
  `;
}

function diagramWave(labelLambda, labelFrequency) {
  return `
    <svg viewBox="0 0 360 170" role="img" aria-label="Sóng hình sin">
      <line x1="35" y1="90" x2="325" y2="90" stroke="#667085" />
      <path d="M40 90 C70 35, 100 35, 130 90 S190 145, 220 90 S280 35, 315 90" fill="none" stroke="#2457d6" stroke-width="4" />
      <line x1="45" y1="130" x2="130" y2="130" stroke="#c92a2a" stroke-width="3" />
      <line x1="45" y1="122" x2="45" y2="138" stroke="#c92a2a" />
      <line x1="130" y1="122" x2="130" y2="138" stroke="#c92a2a" />
      <text x="64" y="153">${labelLambda}</text>
      <text x="210" y="45">${labelFrequency}</text>
    </svg>
  `;
}

function diagramGas() {
  return `
    <svg viewBox="0 0 360 170" role="img" aria-label="Khí nhận nhiệt và sinh công">
      <rect x="95" y="45" width="150" height="85" rx="12" fill="#eef4ff" stroke="#2457d6" stroke-width="3" />
      <line x1="55" y1="88" x2="92" y2="88" stroke="#c92a2a" stroke-width="4" marker-end="url(#arrowGasQ)" />
      <line x1="248" y1="88" x2="305" y2="88" stroke="#087443" stroke-width="4" marker-end="url(#arrowGasA)" />
      <defs>
        <marker id="arrowGasQ" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#c92a2a" /></marker>
        <marker id="arrowGasA" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#087443" /></marker>
      </defs>
      <text x="36" y="76">Q=500 J</text>
      <text x="260" y="76">A=120 J</text>
      <text x="130" y="94">Delta U?</text>
    </svg>
  `;
}

function diagramPhoton() {
  return `
    <svg viewBox="0 0 360 160" role="img" aria-label="Photon và năng lượng">
      <path d="M45 80 C75 30, 105 130, 135 80 S195 30, 225 80 S285 130, 315 80" fill="none" stroke="#2457d6" stroke-width="4" />
      <circle cx="275" cy="80" r="12" fill="#fff8e6" stroke="#b7791f" stroke-width="3" />
      <text x="75" y="40">f=5.10^14 Hz</text>
      <text x="218" y="125">E=hf</text>
    </svg>
  `;
}

function diagramImpedance() {
  return `
    <svg viewBox="0 0 360 180" role="img" aria-label="Tam giác tổng trở">
      <line x1="75" y1="130" x2="235" y2="130" stroke="#2457d6" stroke-width="4" />
      <line x1="235" y1="130" x2="235" y2="55" stroke="#2457d6" stroke-width="4" />
      <line x1="75" y1="130" x2="235" y2="55" stroke="#c92a2a" stroke-width="4" stroke-dasharray="8 6" />
      <path d="M218 130 L218 113 L235 113" fill="none" stroke="#667085" stroke-width="2" />
      <text x="140" y="150">R=6 ohm</text>
      <text x="245" y="96">ZL-ZC=8 ohm</text>
      <text x="145" y="82">Z?</text>
    </svg>
  `;
}

function diagramQuarticExtrema() {
  return `
    <svg viewBox="0 0 360 190" role="img" aria-label="Đồ thị hàm bậc bốn có ba điểm cực trị">
      <line x1="35" y1="145" x2="325" y2="145" stroke="#667085" />
      <line x1="180" y1="170" x2="180" y2="25" stroke="#667085" />
      <path d="M55 36 C92 156, 128 166, 156 92 C170 56, 190 56, 204 92 C232 166, 268 156, 305 36" fill="none" stroke="#2457d6" stroke-width="4" />
      <circle cx="118" cy="136" r="5" fill="#c92a2a" />
      <circle cx="180" cy="68" r="5" fill="#c92a2a" />
      <circle cx="242" cy="136" r="5" fill="#c92a2a" />
      <text x="195" y="35">y=x^4-2x^2</text>
      <text x="270" y="164">x</text>
      <text x="190" y="42">y</text>
    </svg>
  `;
}

function diagramRationalAsymptote() {
  return `
    <svg viewBox="0 0 360 190" role="img" aria-label="Đồ thị phân thức có tiệm cận">
      <line x1="35" y1="145" x2="325" y2="145" stroke="#667085" />
      <line x1="85" y1="170" x2="85" y2="25" stroke="#667085" />
      <line x1="180" y1="25" x2="180" y2="170" stroke="#c92a2a" stroke-dasharray="6 6" />
      <line x1="35" y1="75" x2="325" y2="75" stroke="#c92a2a" stroke-dasharray="6 6" />
      <path d="M55 155 C95 138, 132 115, 165 30" fill="none" stroke="#2457d6" stroke-width="4" />
      <path d="M195 165 C225 112, 265 88, 315 80" fill="none" stroke="#2457d6" stroke-width="4" />
      <text x="187" y="165">x=1 hoặc x=2</text>
      <text x="270" y="68">tiệm cận ngang</text>
    </svg>
  `;
}

function diagramCylinder() {
  return `
    <svg viewBox="0 0 360 190" role="img" aria-label="Khối trụ bán kính và chiều cao">
      <ellipse cx="180" cy="50" rx="75" ry="22" fill="#eef4ff" stroke="#2457d6" stroke-width="3" />
      <path d="M105 50 V140 C105 152, 255 152, 255 140 V50" fill="#eef4ff" stroke="#2457d6" stroke-width="3" />
      <ellipse cx="180" cy="140" rx="75" ry="22" fill="none" stroke="#2457d6" stroke-width="3" />
      <line x1="180" y1="140" x2="255" y2="140" stroke="#c92a2a" stroke-width="3" />
      <line x1="270" y1="50" x2="270" y2="140" stroke="#c92a2a" stroke-width="3" />
      <text x="204" y="132">r=2</text>
      <text x="278" y="99">h=5</text>
    </svg>
  `;
}

function diagramSphere() {
  return `
    <svg viewBox="0 0 360 190" role="img" aria-label="Mặt cầu tâm I bán kính R">
      <circle cx="180" cy="95" r="72" fill="#eef4ff" stroke="#2457d6" stroke-width="3" />
      <ellipse cx="180" cy="95" rx="72" ry="22" fill="none" stroke="#2457d6" stroke-dasharray="6 5" />
      <circle cx="180" cy="95" r="5" fill="#c92a2a" />
      <line x1="180" y1="95" x2="252" y2="95" stroke="#c92a2a" stroke-width="3" />
      <text x="154" y="88">I(1;0;-2)</text>
      <text x="208" y="88">R=3</text>
    </svg>
  `;
}

function diagramHexagon() {
  return `
    <svg viewBox="0 0 360 190" role="img" aria-label="Lục giác đều chọn ba đỉnh tạo tam giác">
      <polygon points="180,28 255,70 255,150 180,192 105,150 105,70" fill="#eef4ff" stroke="#2457d6" stroke-width="3" transform="translate(0 -15)" />
      <polygon points="180,13 255,55 105,135" fill="#fff8e6" stroke="#c92a2a" stroke-width="3" />
      <text x="148" y="168">Chọn 3 trong 6 đỉnh</text>
    </svg>
  `;
}

function diagramPlaneDistance() {
  return `
    <svg viewBox="0 0 360 190" role="img" aria-label="Khoảng cách từ O đến mặt phẳng">
      <polygon points="90,135 235,95 295,138 145,172" fill="#eef4ff" stroke="#2457d6" stroke-width="3" />
      <circle cx="80" cy="55" r="5" fill="#c92a2a" />
      <line x1="80" y1="55" x2="165" y2="142" stroke="#c92a2a" stroke-width="3" stroke-dasharray="7 5" />
      <path d="M150 127 L166 126 L166 142" fill="none" stroke="#667085" stroke-width="2" />
      <text x="66" y="47">O</text>
      <text x="188" y="134">(P)</text>
      <text x="98" y="102">d?</text>
    </svg>
  `;
}

function createExams2024() {
  return {
    math: {
      title: "Toán",
      code: "123",
      duration: 90,
      source: "data/toan/2024/Lời giải chi tiết đề Toán 2024 (final).pdf",
      note:
        "Đề Toán tốt nghiệp THPT 2024 mã 123 nhập theo PDF lời giải chi tiết trong data/toan/2024.",
      sections: [
        {
          title: "Đề 2024 - Trắc nghiệm một lựa chọn",
          type: "single",
          points: 0.2,
          questions: buildImageChoiceSet("y24m", [
            "D", "D", "D", "A", "D", "B", "D", "A", "B", "C",
            "B", "C", "B", "B", "C", "A", "A", "B", "C", "B",
            "B", "C", "A", "A", "A", "B", "C", "C", "B", "A",
            "C", "C", "C", "A", "B", "A", "A", "C", "C", "B",
            "C", "A", "C", "A", "C", "C", "B", "B", "A", "A"
          ], "Toán 2024 mã 123", math2024QuestionImage)
        }
      ]
    },
    physics: {
      title: "Vật lí",
      code: "201",
      duration: 50,
      source:
        "https://laodong.vn/giao-duc/de-thi-dap-an-mon-vat-ly-tot-nghiep-thpt-ma-de-201-207-209-1358774.ldo",
      note:
        "Mô phỏng rút gọn theo cấu trúc Vật lí tốt nghiệp THPT 2024: 40 câu trắc nghiệm một lựa chọn trong bài thi Khoa học tự nhiên.",
      sections: [
        {
          title: "Đề 2024 - Trắc nghiệm một lựa chọn",
          type: "single",
          points: 0.4,
          questions: buildChoiceSet("y24p", [
            ["Đơn vị của tần số là", "A", ["Hz", "m/s", "N", "J"], "Dao động"],
            ["Trong dao động điều hòa, gia tốc luôn", "C", ["cùng chiều li độ", "bằng 0", "hướng về vị trí cân bằng", "không đổi"], "Dao động"],
            ["Công thức liên hệ giữa bước sóng, tốc độ và tần số là", "B", ["v=lambda/T", "v=lambda f", "f=lambda v", "lambda=vf"], "Sóng"],
            ["Mức cường độ âm được đo bằng", "D", ["W", "W/m2", "Hz", "dB"], "Âm học"],
            ["Tụ điện trong mạch xoay chiều có dung kháng", "A", ["ZC=1/(omega C)", "ZC=omega C", "ZC=omega L", "ZC=R"], "Xoay chiều"],
            ["Điều kiện cộng hưởng trong mạch RLC nối tiếp là", "B", ["ZL>ZC", "ZL=ZC", "R=0", "ZC=0"], "Xoay chiều"],
            ["Từ thông qua diện tích S trong từ trường đều là", "C", ["BS", "B/S", "BScos alpha", "BStan alpha"], "Cảm ứng điện từ"],
            ["Suất điện động cảm ứng xuất hiện khi", "D", ["điện trở không đổi", "dòng điện không đổi", "nhiệt độ tăng", "từ thông biến thiên"], "Cảm ứng điện từ"],
            ["Trong chân không, ánh sáng truyền với tốc độ xấp xỉ", "B", ["3.10^6 m/s", "3.10^8 m/s", "340 m/s", "3.10^5 m/s"], "Sóng điện từ"],
            ["Năng lượng photon được tính bằng", "A", ["epsilon=hf", "epsilon=mv", "epsilon=UIt", "epsilon=mgh"], "Lượng tử"],
            ["Hiện tượng quang điện ngoài chứng tỏ ánh sáng có", "C", ["tính sóng", "tính nhiệt", "tính hạt", "tính cơ"], "Lượng tử"],
            ["Hạt nhân nguyên tử gồm", "D", ["electron và proton", "electron và neutron", "photon", "proton và neutron"], "Hạt nhân"],
            ["Công thức liên hệ khối lượng và năng lượng là", "A", ["E=mc^2", "E=hf", "F=ma", "P=UI"], "Hạt nhân"],
            ["Dòng điện trong kim loại là dòng chuyển dời có hướng của", "B", ["ion dương", "electron tự do", "proton", "photon"], "Điện học"],
            ["Công suất điện tiêu thụ của đoạn mạch là", "C", ["P=U/I", "P=I/U", "P=UI", "P=R/U"], "Điện học"],
            ["Một máy biến áp lí tưởng có U2/U1 bằng", "D", ["N1/N2", "I2/I1", "P2/P1", "N2/N1"], "Điện từ"],
            ["Trong thí nghiệm giao thoa ánh sáng, khoảng vân i bằng", "A", ["lambda D/a", "aD/lambda", "lambda a/D", "D/(lambda a)"], "Giao thoa"],
            ["Tia nào sau đây là sóng điện từ?", "C", ["tia alpha", "tia beta", "tia gamma", "chùm proton"], "Bức xạ"],
            ["Chu kì bán rã là thời gian để số hạt nhân chưa phân rã còn", "B", ["1/4", "1/2", "1/3", "0"], "Phóng xạ"],
            ["Khi nhiệt độ khí lí tưởng tăng ở thể tích không đổi, áp suất", "A", ["tăng", "giảm", "không đổi", "bằng 0"], "Khí lí tưởng"],
            ["Động năng của vật khối lượng m, tốc độ v là", "D", ["mv", "2mv", "mgh", "mv^2/2"], "Cơ học"],
            ["Đơn vị của cảm ứng từ là", "C", ["Wb", "H", "T", "F"], "Từ trường"],
            ["Sóng cơ truyền được trong môi trường", "B", ["chân không", "vật chất", "không cần môi trường", "ánh sáng"], "Sóng"],
            ["Cường độ dòng điện hiệu dụng được đo bằng", "A", ["ampe kế xoay chiều", "vôn kế", "nhiệt kế", "áp kế"], "Xoay chiều"],
            ["Độ hụt khối của hạt nhân liên quan trực tiếp đến", "D", ["điện trở", "nhiệt độ", "áp suất", "năng lượng liên kết"], "Hạt nhân"]
          ])
        }
      ]
    }
  };
}

function createExams2023() {
  return {
    math: {
      title: "Toán",
      code: "102",
      duration: 90,
      source: "data/toan/2023/GiaiChiTiet102-THPT2023.pdf",
      note:
        "Đề Toán tốt nghiệp THPT 2023 mã 102 nhập theo PDF lời giải chi tiết trong data/toan/2023.",
      sections: [
        {
          title: "Đề 2023 - Trắc nghiệm một lựa chọn",
          type: "single",
          points: 0.2,
          questions: buildImageChoiceSet("y23m", [
            "A", "C", "C", "A", "B", "B", "C", "A", "D", "B",
            "D", "A", "B", "D", "D", "D", "B", "C", "B", "A",
            "A", "B", "C", "A", "A", "B", "C", "A", "C", "B",
            "C", "B", "C", "A", "A", "A", "C", "C", "B", "A",
            "B", "C", "B", "C", "C", "B", "B", "C", "C", "A"
          ], "Toán 2023 mã 102", math2023QuestionImage)
        }
      ]
    },
    physics: {
      title: "Vật lí",
      code: "201",
      duration: 50,
      source:
        "https://doctailieu.com/dap-an-ly-thpt-quoc-gia-2023-ma-de-201-va-loi-giai-chi-tiet",
      note:
        "Mô phỏng rút gọn theo cấu trúc Vật lí tốt nghiệp THPT 2023: 40 câu trắc nghiệm một lựa chọn trong bài thi Khoa học tự nhiên.",
      sections: [
        {
          title: "Đề 2023 - Trắc nghiệm một lựa chọn",
          type: "single",
          points: 0.4,
          questions: buildChoiceSet("y23p", [
            ["Trong dao động điều hòa, li độ x và gia tốc a liên hệ bởi", "A", ["a=-omega^2x", "a=omega x", "a=omega^2x", "a=-omega x"], "Dao động"],
            ["Đơn vị của bước sóng là", "A", ["m", "Hz", "s", "dB"], "Sóng"],
            ["Sóng âm truyền được trong", "B", ["chân không", "không khí", "ánh sáng", "điện trường tĩnh"], "Âm học"],
            ["Cường độ dòng điện được đo bằng", "B", ["vôn kế", "ampe kế", "nhiệt kế", "áp kế"], "Điện học"],
            ["Cảm kháng của cuộn cảm là", "A", ["ZL=omega L", "ZL=1/(omega L)", "ZL=omega C", "ZL=R"], "Xoay chiều"],
            ["Dung kháng của tụ điện là", "A", ["ZC=1/(omega C)", "ZC=omega C", "ZC=omega L", "ZC=R"], "Xoay chiều"],
            ["Trong mạch RLC cộng hưởng, cường độ dòng điện", "D", ["nhỏ nhất", "bằng 0", "không xác định", "lớn nhất"], "Xoay chiều"],
            ["Từ thông qua khung dây phụ thuộc vào", "B", ["điện trở", "góc giữa B và pháp tuyến mặt khung", "khối lượng dây", "nhiệt độ"], "Cảm ứng điện từ"],
            ["Đơn vị của từ thông là", "C", ["T", "H", "Wb", "F"], "Từ trường"],
            ["Sóng điện từ trong chân không truyền với tốc độ", "D", ["340 m/s", "3.10^5 m/s", "3.10^6 m/s", "3.10^8 m/s"], "Sóng điện từ"],
            ["Khoảng vân trong giao thoa ánh sáng tăng khi", "D", ["giảm D", "giảm lambda", "tăng a", "tăng D"], "Giao thoa"],
            ["Năng lượng photon tỉ lệ thuận với", "C", ["bước sóng", "chu kì", "tần số", "vận tốc nguồn"], "Lượng tử"],
            ["Hiện tượng quang điện xảy ra khi photon có năng lượng", "C", ["nhỏ hơn công thoát", "bằng 0", "không nhỏ hơn công thoát", "bất kỳ"], "Lượng tử"],
            ["Hạt nhân có số khối A gồm", "A", ["A nuclon", "A electron", "A photon", "A proton luôn"], "Hạt nhân"],
            ["Chu kì bán rã càng nhỏ thì chất phóng xạ phân rã", "B", ["chậm hơn", "nhanh hơn", "không đổi", "không xảy ra"], "Phóng xạ"],
            ["Động năng của vật chuyển động là", "A", ["mv^2/2", "mgh", "kx^2", "qU"], "Cơ học"],
            ["Công suất tiêu thụ trên điện trở R là", "D", ["IR", "UR", "I/R", "I^2R"], "Điện học"],
            ["Máy biến áp dùng để biến đổi", "A", ["điện áp xoay chiều", "điện áp một chiều không đổi", "khối lượng", "nhiệt độ"], "Điện từ"],
            ["Trong thang sóng điện từ, tia gamma có bước sóng", "C", ["rất lớn", "bằng sóng radio", "rất ngắn", "bằng 0"], "Bức xạ"],
            ["Khí lí tưởng đẳng nhiệt thỏa mãn", "D", ["p/V hằng số", "V/T hằng số", "p/T hằng số", "pV hằng số"], "Khí lí tưởng"],
            ["Nội năng của khí lí tưởng phụ thuộc chủ yếu vào", "A", ["nhiệt độ", "hình dạng bình", "màu bình", "độ cao"], "Nhiệt học"],
            ["Lực từ tác dụng lên dây dẫn mang dòng điện phụ thuộc vào", "C", ["màu dây", "nhiệt độ phòng", "cường độ dòng điện", "áp suất"], "Từ trường"],
            ["Hiệu suất của máy luôn", "C", ["lớn hơn 1", "bằng 2", "không vượt quá 1", "âm"], "Năng lượng"],
            ["Tia hồng ngoại có bản chất là", "D", ["dòng electron", "dòng proton", "sóng cơ", "sóng điện từ"], "Bức xạ"],
            ["Trong dao động điều hòa, cơ năng tỉ lệ với", "A", ["A^2", "A", "1/A", "T"], "Dao động"]
          ])
        }
      ]
    }
  };
}

function getExam() {
  return EXAMS_BY_YEAR[state.year]?.[state.subjectId];
}

function hasExamData(subjectId = state.subjectId, year = state.year) {
  const exam = EXAMS_BY_YEAR[year]?.[subjectId];
  return Boolean(exam && Array.isArray(exam.sections) && exam.sections.length > 0);
}

function getExamsForYear() {
  return EXAMS_BY_YEAR[state.year];
}

function getStorageKey() {
  return `lop12-exam-${state.year}-${state.subjectId}`;
}

function loadSavedAnswers() {
  const raw = localStorage.getItem(getStorageKey());
  if (!raw) {
    state.answers = {};
    return;
  }

  try {
    state.answers = JSON.parse(raw);
  } catch (error) {
    console.warn("Không đọc được bài làm đã lưu, app sẽ tạo bài mới.", error);
    localStorage.removeItem(getStorageKey());
    state.answers = {};
  }
}

function saveAnswers() {
  localStorage.setItem(getStorageKey(), JSON.stringify(state.answers));
}

function clearCurrentAnswers() {
  state.answers = {};
  localStorage.removeItem(getStorageKey());
}

function normalizeAnswer(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "")
    .replace(".", ",");
}

function gradeTrueFalse(userAnswer, correctAnswer) {
  const correctCount = correctAnswer
    .split("")
    .filter((value, index) => value === (userAnswer || "")[index]).length;

  if (correctCount === 4) return 1;
  if (correctCount === 3) return 0.5;
  if (correctCount === 2) return 0.25;
  if (correctCount === 1) return 0.1;
  return 0;
}

function gradeExam() {
  const exam = getExam();
  let score = 0;
  let maxScore = 0;
  const details = {};

  exam.sections.forEach((section) => {
    section.questions.forEach((question) => {
      let earned = 0;
      let max = section.points === "tiered" ? 1 : section.points;
      const answer = state.answers[question.id];

      if (section.type === "single") {
        earned = answer === question.answer ? section.points : 0;
      }

      if (section.type === "short") {
        earned =
          normalizeAnswer(answer) === normalizeAnswer(question.answer)
            ? section.points
            : 0;
      }

      if (section.type === "truefalse") {
        earned = gradeTrueFalse(answer, question.answer);
      }

      score += earned;
      maxScore += max;
      details[question.id] = { earned, max };
    });
  });

  return {
    score: Math.round(score * 100) / 100,
    maxScore,
    details
  };
}

function startTimer() {
  const exam = getExam();
  clearInterval(state.intervalId);
  state.endsAt = Date.now() + exam.duration * 60 * 1000;
  updateTimer();
  state.intervalId = setInterval(updateTimer, 1000);
}

function updateTimer() {
  const remaining = Math.max(0, state.endsAt - Date.now());
  const minutes = Math.floor(remaining / 60000);
  const seconds = Math.floor((remaining % 60000) / 1000);

  timer.textContent = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  timerNote.textContent = remaining === 0 ? "Hết giờ" : "Thời gian còn lại";

  if (remaining === 0 && !state.submitted) {
    clearInterval(state.intervalId);
    submitExam();
  }
}

function renderSubjects() {
  const yearExams = getExamsForYear();

  subjectList.innerHTML = Object.entries(SUBJECT_CATALOG)
    .map(([id, subject]) => {
      const exam = yearExams[id];
      const active = id === state.subjectId ? " active" : "";
      const unavailable = !exam;

      if (unavailable) {
        const unavailableText =
          id === "informatics"
            ? `Không có đề thi năm ${state.year}`
            : `Chưa có dữ liệu năm ${state.year}`;
        return `
          <button class="subject-card subject-card-unavailable${active}" type="button" data-subject="${id}">
            <strong>${subject.title}</strong>
            <span>${unavailableText}</span>
          </button>
        `;
      }

      const actionText = state.mode === "practice" ? "Bấm để bắt đầu thi" : "Xem nội dung ôn tập";
      return `
        <button class="subject-card${active}" type="button" data-subject="${id}">
          <strong>${exam.title}</strong>
          <span>Mã đề ${exam.code} - ${exam.duration} phút<br />${actionText}</span>
        </button>
      `;
    })
    .join("");

  subjectList.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => selectSubject(button.dataset.subject));
  });
}

function renderYears() {
  yearList.innerHTML = Object.keys(EXAMS_BY_YEAR)
    .sort((a, b) => Number(b) - Number(a))
    .map((year) => {
      const active = year === state.year ? " active" : "";
      return `<button class="year-card${active}" type="button" data-year="${year}">${year}</button>`;
    })
    .join("");

  yearList.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => selectYear(button.dataset.year));
  });
}

function renderModeButtons() {
  practiceModeBtn.classList.toggle("active", state.mode === "practice");
  studyModeBtn.classList.toggle("active", state.mode === "study");
}

function renderMissingExam() {
  clearInterval(state.intervalId);
  const subject = SUBJECT_CATALOG[state.subjectId]?.title || "Môn thi";
  const informaticsUnavailable =
    state.subjectId === "informatics" && !INFORMATICS_EXAM_YEARS.has(state.year);

  examCode.textContent = `${state.year} - ${subject}`;
  sourceTitle.textContent = `Nguồn tham khảo ${state.year}`;
  sourceText.textContent = informaticsUnavailable
    ? "Môn Tin học chỉ có đề thi tốt nghiệp THPT cho năm 2025 và 2026."
    : "Chưa có bộ đề cho môn và năm đã chọn.";
  sourceLink.href = "#";
  subjectMeta.textContent = `Năm ${state.year} - ${subject}`;
  subjectTitle.textContent = informaticsUnavailable
    ? `Không có đề thi Tin học năm ${state.year}`
    : `Không có đề thi ${subject} năm ${state.year}`;
  subjectPanel.classList.remove("hidden");
  questionNav.classList.add("hidden");
  questionNav.innerHTML = "";
  studyGuide.classList.add("hidden");
  examForm.classList.remove("hidden");
  submitBtn.classList.add("hidden");
  resetBtn.classList.add("hidden");
  timer.textContent = "--:--";
  timerNote.textContent = "Không có đề";
  resultBox.classList.add("hidden");

  examForm.innerHTML = `
    <div class="result-box">
      <h3>Không có đề thi ${subject} năm ${state.year}</h3>
      <p>${
        informaticsUnavailable
          ? "Môn Tin học hiện chỉ có đề thi cho năm 2025 và 2026. Hãy chọn một trong hai năm đó để làm bài."
          : "Hãy chọn năm hoặc môn khác, hoặc chuyển sang chế độ ôn tập nếu có nội dung hướng dẫn."
      }</p>
    </div>
  `;
}

function renderExam() {
  renderModeButtons();

  if (state.mode === "study" && STUDY_GUIDES[state.subjectId]) {
    renderStudyGuide();
    return;
  }

  const exam = getExam();
  if (!exam || !Array.isArray(exam.sections)) {
    renderMissingExam();
    return;
  }

  const flatQuestions = exam.sections.flatMap((section) => section.questions);

  examCode.textContent = `${state.year} - Mã đề ${exam.code}`;
  sourceTitle.textContent = `Nguồn tham khảo ${state.year}`;
  sourceText.textContent = exam.note;
  sourceLink.href = exam.source;
  subjectMeta.textContent = `Năm ${state.year} - Mã đề ${exam.code} - ${exam.duration} phút`;
  subjectTitle.textContent =
    state.mode === "study"
      ? `Ôn kiến thức môn ${exam.title}`
      : `Đề luyện thi môn ${exam.title}`;
  resultBox.classList.add("hidden");

  if (!state.examStarted) {
    clearInterval(state.intervalId);
    timer.textContent = "--:--";
    timerNote.textContent = "Chưa bắt đầu";
    examCode.textContent = `${state.year} - Chọn môn`;
    subjectMeta.textContent = `Năm ${state.year} - Chế độ làm đề`;
    subjectTitle.textContent = "Chọn môn thi ở bước 3 để bắt đầu";
    subjectPanel.classList.remove("hidden");
    questionNav.classList.add("hidden");
    questionNav.innerHTML = "";
    studyGuide.classList.add("hidden");
    examForm.classList.remove("hidden");
    examForm.innerHTML = `
      <div class="result-box">
        <h3>Sẵn sàng làm đề</h3>
        <p>Hãy chọn chế độ, chọn năm, rồi bấm môn thi ở sidebar bên trái để bắt đầu tính giờ và làm bài.</p>
      </div>
    `;
    submitBtn.classList.add("hidden");
    resetBtn.classList.add("hidden");
    return;
  }

  studyGuide.classList.add("hidden");
  examForm.classList.remove("hidden");
  subjectPanel.classList.add("hidden");
  questionNav.classList.remove("hidden");
  submitBtn.classList.remove("hidden");
  resetBtn.classList.remove("hidden");

  if (flatQuestions.length === 0) {
    clearInterval(state.intervalId);
    timer.textContent = "--:--";
    timerNote.textContent = "Không có đề";
    subjectPanel.classList.remove("hidden");
    questionNav.classList.add("hidden");
    questionNav.innerHTML = "";
    examForm.innerHTML = `
      <div class="result-box">
        <h3>Chưa có nội dung đề cho môn này.</h3>
        <p>${exam.note}</p>
      </div>
    `;
    submitBtn.classList.add("hidden");
    return;
  }

  renderNavOnly();

  examForm.innerHTML = exam.sections
    .map((section) => {
      const questions = section.questions
        .map((question, index) => renderQuestion(section, question, index))
        .join("");
      return `<div class="section-title">${section.title}</div>${questions}`;
    })
    .join("");

  bindQuestionEvents();
  submitBtn.disabled = false;
}

function renderStudyGuide() {
  const guide = STUDY_GUIDES[state.subjectId];

  clearInterval(state.intervalId);
  timer.textContent = "Ôn tập";
  timerNote.textContent = "Không giới hạn thời gian";
  subjectPanel.classList.remove("hidden");
  questionNav.classList.add("hidden");
  examForm.classList.add("hidden");
  submitBtn.classList.add("hidden");
  resetBtn.classList.add("hidden");
  studyGuide.classList.remove("hidden");

  if (!guide) {
    studyGuide.innerHTML = `
      <section class="study-hero">
        <h3>Chưa có dữ liệu ôn tập</h3>
        <p>Hãy chọn lại môn hoặc refresh trang để tải dữ liệu mới nhất.</p>
      </section>
    `;
    return;
  }

  studyGuide.innerHTML = `
    <section class="study-hero">
      <p class="eyebrow">Tổng quan ôn thi</p>
      <h3>${guide.title}: học gì để làm tốt đề 2025-2026?</h3>
      <p>${guide.overview}</p>
    </section>

    <div class="study-grid">
      ${guide.examMap ? `
        <section class="study-card full">
          <h3>Bản đồ cấu trúc đề</h3>
          <ul>
            ${guide.examMap.map((item) => `<li>${item}</li>`).join("")}
          </ul>
        </section>
      ` : ""}

      <section class="study-card full">
        <h3>Chuyên đề trọng tâm</h3>
        <div class="topic-list">
          ${guide.topics
            .map(
              ([topic, detail]) => `
                <div class="topic-item">
                  <strong>${topic}</strong>
                  <span>${detail}</span>
                </div>
              `
            )
            .join("")}
        </div>
      </section>

      <section class="study-card">
        <h3>Công thức và mẫu cần nhớ</h3>
        <div class="formula-list">
          ${guide.formulas
            .map(
              ([name, formula]) => `
                <div class="formula-item">
                  <strong>${name}</strong>
                  <br />
                  <code>${formula}</code>
                </div>
              `
            )
            .join("")}
        </div>
      </section>

      <section class="study-card">
        <h3>Kỹ năng làm bài</h3>
        <ul>
          ${guide.skills.map((item) => `<li>${item}</li>`).join("")}
        </ul>
      </section>

      <section class="study-card">
        <h3>Lộ trình ôn gợi ý</h3>
        <ol>
          ${guide.plan.map((item) => `<li>${item}</li>`).join("")}
        </ol>
      </section>

      <section class="study-card">
        <h3>Lỗi hay mất điểm</h3>
        <ul>
          ${guide.traps.map((item) => `<li>${item}</li>`).join("")}
        </ul>
      </section>

      ${guide.targets ? `
        <section class="study-card full">
          <h3>Mục tiêu theo mức điểm</h3>
          <div class="topic-list">
            ${guide.targets
              .map(
                ([target, detail]) => `
                  <div class="topic-item">
                    <strong>${target}</strong>
                    <span>${detail}</span>
                  </div>
                `
              )
              .join("")}
          </div>
        </section>
      ` : ""}

      ${guide.deepDives ? `
        <section class="study-card full">
          <h3>Hướng dẫn chuyên sâu theo dạng bài</h3>
          <div class="topic-list">
            ${guide.deepDives
              .map(
                ([topic, detail]) => `
                  <div class="topic-item">
                    <strong>${topic}</strong>
                    <span>${detail}</span>
                  </div>
                `
              )
              .join("")}
          </div>
        </section>
      ` : ""}
    </div>
  `;
}

function renderQuestion(section, question, index) {
  const value = state.answers[question.id] || "";
  const number = index + 1;
  const pointText = section.points === "tiered" ? "tối đa 1 điểm" : `${section.points} điểm`;

  if (section.type === "single") {
    return `
      <article class="question-card" id="${question.id}" data-question-id="${question.id}">
        ${questionHeader(number, question, pointText)}
        ${renderFigure(question)}
        ${renderPrompt(question)}
        <div class="options">
          ${["A", "B", "C", "D"]
            .map((letter, optionIndex) => `
              <label class="option">
                <input type="radio" name="${question.id}" value="${letter}" ${value === letter ? "checked" : ""} />
                <strong>${letter}.</strong> ${escapeHtml(question.options[optionIndex])}
              </label>
            `)
            .join("")}
        </div>
        ${renderAnswerGuide(section.type, question)}
      </article>
    `;
  }

  if (section.type === "short") {
    return `
      <article class="question-card" id="${question.id}" data-question-id="${question.id}">
        ${questionHeader(number, question, pointText)}
        ${renderFigure(question)}
        ${renderPrompt(question)}
        <input class="short-input" name="${question.id}" value="${value}" placeholder="Nhập đáp án" />
        ${renderAnswerGuide(section.type, question)}
      </article>
    `;
  }

  return `
    <article class="question-card" id="${question.id}" data-question-id="${question.id}">
      ${questionHeader(number, question, pointText)}
      ${renderFigure(question)}
      ${renderPrompt(question)}
      <div class="truefalse-grid">
        ${question.statements
          .map((statement, statementIndex) => {
            const current = value[statementIndex] || "";
            return `
              <div class="tf-row">
                <span>${String.fromCharCode(97 + statementIndex)}) ${escapeHtml(statement)}</span>
                <div class="tf-controls">
                  <label><input type="radio" name="${question.id}-${statementIndex}" value="D" ${current === "D" ? "checked" : ""} /> Đúng</label>
                  <label><input type="radio" name="${question.id}-${statementIndex}" value="S" ${current === "S" ? "checked" : ""} /> Sai</label>
                </div>
              </div>
            `;
          })
          .join("")}
      </div>
      ${renderAnswerGuide(section.type, question)}
    </article>
  `;
}

function renderFigure(question) {
  if (!question.figure) return "";
  return `<div class="question-figure">${question.figure}</div>`;
}

function renderPrompt(question) {
  if (question.figure.includes("data/toan/2026/crops/")) return "";
  if (question.figure.includes("data/tin/2025/crops/")) return "";
  if (/^Xem nội dung\b/i.test(question.prompt)) return "";
  return `<p class="prompt">${escapeHtml(question.prompt).replace(/\n/g, "<br />")}</p>`;
}

function renderAnswerGuide(type, question) {
  if (!state.submitted) return "";

  const solutionFigure = getPdfSolutionFigure(question.id);

  return `
    <details class="answer-hint">
      <summary>Xem đáp án / lời giải chi tiết</summary>
      <p><strong>Đáp án:</strong> ${formatCorrectAnswer(type, question)}</p>
      ${question.solution ? `<p>${escapeHtml(question.solution)}</p>` : ""}
      ${solutionFigure ? `<div class="solution-figure">${solutionFigure}</div>` : ""}
    </details>
  `;
}

function questionHeader(number, question, pointText) {
  return `
    <div class="question-head">
      <h3>Câu ${number}</h3>
      <span class="tag">${question.topic} - ${pointText}</span>
    </div>
  `;
}

function bindQuestionEvents() {
  examForm.querySelectorAll("input").forEach((input) => {
    input.addEventListener("input", handleAnswerInput);
    input.addEventListener("change", handleAnswerInput);
  });
}

function handleAnswerInput(event) {
  if (state.submitted) return;

  const input = event.target;

  if (input.name.includes("-")) {
    const [questionId, indexText] = input.name.split("-");
    const index = Number(indexText);
    const current = (state.answers[questionId] || "____").split("");
    current[index] = input.value;
    state.answers[questionId] = current.join("");
  } else {
    state.answers[input.name] = input.value;
  }

  saveAnswers();
  renderNavOnly();
}

function renderNavOnly() {
  const exam = getExam();
  const flatQuestions = exam.sections.flatMap((section) => section.questions);
  const answeredCount = flatQuestions.filter((question) => Boolean(state.answers[question.id])).length;

  questionNav.innerHTML = flatQuestions
    .map((question, index) => {
      const answered = state.answers[question.id] ? " answered" : "";
      return `<a class="nav-pill${answered}" href="#${question.id}" title="Đi tới câu ${index + 1}">${index + 1}</a>`;
    })
    .join("");

  questionNav.innerHTML = `
    <h3>Điều hướng câu hỏi</h3>
    <p>Đã làm ${answeredCount}/${flatQuestions.length} câu</p>
    <div class="nav-list">${questionNav.innerHTML}</div>
    <button class="nav-exit" type="button" id="exitPracticeBtn">Thoát chế độ thi / Chọn đề</button>
  `;

  questionNav.querySelector("#exitPracticeBtn").addEventListener("click", () => {
    state.examStarted = false;
    state.submitted = false;
    clearInterval(state.intervalId);
    renderExam();
  });
}

function submitExam() {
  state.submitted = true;
  clearInterval(state.intervalId);
  const result = gradeExam();

  resultBox.innerHTML = `
    <h3>Kết quả: ${result.score.toFixed(2)} / ${result.maxScore.toFixed(2)} điểm</h3>
    <p>Bài đã được chấm tự động. Các câu đúng được viền xanh, câu chưa đạt đủ điểm được viền đỏ.</p>
  `;
  resultBox.classList.remove("hidden");
  submitBtn.disabled = true;
  showFeedback(result.details);
}

function showFeedback(details) {
  const exam = getExam();

  exam.sections.forEach((section) => {
    section.questions.forEach((question) => {
      const card = examForm.querySelector(`[data-question-id="${question.id}"]`);
      const detail = details[question.id];
      const isFull = detail.earned === detail.max;
      const userAnswer = state.answers[question.id] || "Chưa trả lời";

      card.classList.add(isFull ? "correct" : "incorrect");
      card.insertAdjacentHTML(
        "beforeend",
        `<div class="feedback">
          <strong>Đáp án:</strong> ${formatCorrectAnswer(section.type, question)}
          <br />
          <strong>Bạn chọn:</strong> ${escapeHtml(userAnswer)}
          <br />
          <strong>Điểm câu này:</strong> ${detail.earned} / ${detail.max}
        </div>`
      );
      card.insertAdjacentHTML("beforeend", renderAnswerGuide(section.type, question));
    });
  });

  examForm.querySelectorAll("input").forEach((input) => {
    input.disabled = true;
  });
}

function formatCorrectAnswer(type, question) {
  if (type === "truefalse") {
    return question.answer
      .split("")
      .map((value, index) => `${String.fromCharCode(97 + index)}) ${value === "D" ? "Đúng" : "Sai"}`)
      .join("; ");
  }
  if (type === "single" && question.options) {
    const index = question.answer.charCodeAt(0) - 65;
    const optionText = question.options[index];
    if (optionText !== undefined) {
      return `${question.answer}. ${escapeHtml(optionText)}`;
    }
  }
  return escapeHtml(question.answer);
}

function selectSubject(subjectId) {
  state.subjectId = subjectId;
  state.submitted = false;
  state.examStarted = state.mode === "practice" && hasExamData(subjectId);
  if (state.examStarted) {
    clearCurrentAnswers();
  } else {
    state.answers = {};
  }
  renderSubjects();
  renderExam();
  if (state.examStarted) {
    startTimer();
  }
}

function selectYear(year) {
  state.year = year;
  state.submitted = false;
  state.examStarted = false;
  state.answers = {};

  if (!hasExamData(state.subjectId, year) && state.subjectId !== "informatics") {
    const fallback = Object.keys(getExamsForYear())[0];
    if (fallback) {
      state.subjectId = fallback;
    }
  }

  renderYears();
  renderSubjects();
  renderExam();
}

function selectMode(mode) {
  state.mode = mode;
  state.submitted = false;
  state.examStarted = false;
  state.answers = {};
  renderExam();
}

function resetExam() {
  if (!confirm("Bạn muốn xóa bài làm hiện tại và làm lại từ đầu?")) return;
  state.answers = {};
  state.submitted = false;
  localStorage.removeItem(getStorageKey());
  renderExam();
  if (state.examStarted) {
    startTimer();
  }
}

practiceModeBtn.addEventListener("click", () => selectMode("practice"));
studyModeBtn.addEventListener("click", () => selectMode("study"));
submitBtn.addEventListener("click", submitExam);
resetBtn.addEventListener("click", resetExam);

renderYears();
renderSubjects();
state.answers = {};
renderExam();
