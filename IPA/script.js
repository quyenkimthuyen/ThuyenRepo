/**
 * IPA Phonics Mindmap - Core Javascript
 * Tác giả: Antigravity coding subagent
 * Dựa trên sách "Ráp vần tiếng Anh, phiên âm quốc tế" - NXB Đồng Nai
 */

// --- 1. DỮ LIỆU QUY TẮC RÁP VẦN & PHIÊN ÂM (PHONICS DATA) ---
const ipaData = {
  id: "root",
  label: "Ráp Vần Tiếng Anh",
  type: "root",
  children: [
    {
      id: "vowel-single",
      label: "Nguyên âm đơn",
      type: "category",
      color: "var(--color-vowel-single)",
      children: [
        {
          id: "v-a",
          label: "a",
          type: "letter",
          category: "vowel-single",
          children: [
            {
              id: "r-a-1",
              label: "/æ/",
              type: "rule",
              ipa: "/æ/",
              desc: "Âm A bẹt (ngắn, miệng mở rộng sang 2 bên)",
              rule: "Phát âm là /æ/ trong từ một âm tiết kết thúc bằng một hoặc nhiều phụ âm (âm tiết khép kín).",
              examples: [
                { word: "cat", ipa: "kæt", meaning: "con mèo" },
                { word: "map", ipa: "mæp", meaning: "bản đồ" },
                { word: "hand", ipa: "hænd", meaning: "bàn tay" },
                { word: "flag", ipa: "flæg", meaning: "lá cờ" }
              ]
            },
            {
              id: "r-a-2",
              label: "/eɪ/",
              type: "rule",
              ipa: "/eɪ/",
              desc: "Nguyên âm đôi A-I (đọc như 'ây')",
              rule: "Phát âm là /eɪ/ khi đứng trước cụm [phụ âm + e] ở cuối từ (cấu trúc a_e), hoặc khi đi với phụ âm tạo âm mở.",
              examples: [
                { word: "cake", ipa: "keɪk", meaning: "bánh ngọt" },
                { word: "late", ipa: "leɪt", meaning: "muộn" },
                { word: "name", ipa: "neɪm", meaning: "tên" },
                { word: "game", ipa: "ɡeɪm", meaning: "trò chơi" }
              ]
            },
            {
              id: "r-a-3",
              label: "/ɑː/",
              type: "rule",
              ipa: "/ɑː/",
              desc: "Âm A dài (mở rộng miệng, hơi phát ra từ cổ họng)",
              rule: "Phát âm là /ɑː/ khi đi trước âm 'r' (tổ hợp ar), hoặc trong một số từ đặc biệt như father.",
              examples: [
                { word: "car", ipa: "kɑː(r)", meaning: "xe hơi" },
                { word: "park", ipa: "pɑːk", meaning: "công viên" },
                { word: "star", ipa: "stɑː(r)", meaning: "ngôi sao" },
                { word: "father", ipa: "ˈfɑːðə(r)", meaning: "cha/bố" }
              ]
            },
            {
              id: "r-a-4",
              label: "/ɔː/",
              type: "rule",
              ipa: "/ɔː/",
              desc: "Âm O dài (tròn môi)",
              rule: "Phát âm là /ɔː/ khi đi trước 'll', 'lk' (như all, alk) hoặc đứng sau âm 'w'.",
              examples: [
                { word: "tall", ipa: "tɔːl", meaning: "cao" },
                { word: "call", ipa: "kɔːl", meaning: "gọi điện" },
                { word: "walk", ipa: "wɔːk", meaning: "đi bộ" },
                { word: "water", ipa: "ˈwɔːtə(r)", meaning: "nước" }
              ]
            },
            {
              id: "r-a-5",
              label: "/ə/",
              type: "rule",
              ipa: "/ə/",
              desc: "Âm Ơ ngắn (âm yếu, không nhấn trọng âm)",
              rule: "Phát âm là /ə/ khi nằm trong âm tiết không được nhấn trọng âm của từ nhiều âm tiết.",
              examples: [
                { word: "about", ipa: "əˈbaʊt", meaning: "về/khoảng" },
                { word: "banana", ipa: "bəˈnɑːnə", meaning: "quả chuối" },
                { word: "sofa", ipa: "ˈsəʊfə", meaning: "ghế sô-fa" },
                { word: "agree", ipa: "əˈɡriː", meaning: "đồng ý" }
              ]
            },
            {
              id: "r-a-6",
              label: "/eə/",
              type: "rule",
              ipa: "/eə/",
              desc: "Âm đôi E-Ơ (đọc lướt từ e sang ơ)",
              rule: "Phát âm là /eə/ khi chữ a đứng trước đuôi 're' (cấu trúc a_re) hoặc đi với r tạo âm đôi.",
              examples: [
                { word: "care", ipa: "keə(r)", meaning: "chăm sóc" },
                { word: "share", ipa: "ʃeə(r)", meaning: "chia sẻ" },
                { word: "rare", ipa: "reə(r)", meaning: "hiếm" },
                { word: "dare", ipa: "deə(r)", meaning: "dám" }
              ]
            },
            {
              id: "r-a-7",
              label: "/ɪ/",
              type: "rule",
              ipa: "/ɪ/",
              desc: "Âm I ngắn (âm yếu ở hậu tố)",
              rule: "Phát âm là /ɪ/ trong hậu tố không nhấn trọng âm '-age' ở các từ có hai âm tiết trở lên.",
              examples: [
                { word: "village", ipa: "ˈvɪlɪdʒ", meaning: "ngôi làng" },
                { word: "message", ipa: "ˈmesɪdʒ", meaning: "tin nhắn" },
                { word: "cabbage", ipa: "ˈkæbɪdʒ", meaning: "bắp cải" },
                { word: "image", ipa: "ˈɪmɪdʒ", meaning: "hình ảnh" }
              ]
            },
            {
              id: "r-a-8",
              label: "/ɒ/",
              type: "rule",
              ipa: "/ɒ/",
              desc: "Âm O ngắn tròn môi",
              rule: "Thường phát âm là /ɒ/ (giọng Anh-Anh) khi đi sau âm /w/ hoặc /kw/ (như w, wh, qu).",
              examples: [
                { word: "was", ipa: "wɒz", meaning: "thì/là (quá khứ)" },
                { word: "wash", ipa: "wɒʃ", meaning: "rửa/giặt" },
                { word: "what", ipa: "wɒt", meaning: "cái gì" },
                { word: "watch", ipa: "wɒtʃ", meaning: "đồng hồ/xem" }
              ]
            }
          ]
        },
        {
          id: "v-e",
          label: "e",
          type: "letter",
          category: "vowel-single",
          children: [
            {
              id: "r-e-1",
              label: "/e/",
              type: "rule",
              ipa: "/e/",
              desc: "Âm E ngắn",
              rule: "Phát âm là /e/ trong âm tiết khép kín (kết thúc bằng phụ âm).",
              examples: [
                { word: "bed", ipa: "bed", meaning: "cái giường" },
                { word: "pen", ipa: "pen", meaning: "bút bi" },
                { word: "red", ipa: "red", meaning: "màu đỏ" },
                { word: "desk", ipa: "desk", meaning: "bàn học" }
              ]
            },
            {
              id: "r-e-2",
              label: "/iː/",
              type: "rule",
              ipa: "/iː/",
              desc: "Âm I dài (cười nhẹ khi đọc)",
              rule: "Phát âm là /iː/ khi nằm trong các đại từ một âm tiết kết thúc bằng nguyên âm e (âm tiết mở).",
              examples: [
                { word: "he", ipa: "hiː", meaning: "anh ấy" },
                { word: "she", ipa: "ʃiː", meaning: "cô ấy" },
                { word: "me", ipa: "miː", meaning: "tôi" },
                { word: "we", ipa: "wiː", meaning: "chúng ta" }
              ]
            },
            {
              id: "r-e-3",
              label: "/ɪ/",
              type: "rule",
              ipa: "/ɪ/",
              desc: "Âm I ngắn",
              rule: "Thường phát âm là /ɪ/ ở các tiền tố như be-, de-, re- khi không mang trọng âm.",
              examples: [
                { word: "begin", ipa: "bɪˈɡɪn", meaning: "bắt đầu" },
                { word: "decide", ipa: "dɪˈsaɪd", meaning: "quyết định" },
                { word: "return", ipa: "rɪˈtɜːn", meaning: "trở về" }
              ]
            }
          ]
        },
        {
          id: "v-i",
          label: "i",
          type: "letter",
          category: "vowel-single",
          children: [
            {
              id: "r-i-1",
              label: "/ɪ/",
              type: "rule",
              ipa: "/ɪ/",
              desc: "Âm I ngắn",
              rule: "Phát âm là /ɪ/ trong từ một âm tiết có cấu trúc khép kín kết thúc bằng phụ âm.",
              examples: [
                { word: "pin", ipa: "pɪn", meaning: "cái ghim" },
                { word: "sit", ipa: "sɪt", meaning: "ngồi" },
                { word: "big", ipa: "bɪɡ", meaning: "to lớn" },
                { word: "wind", ipa: "wɪnd", meaning: "gió" }
              ]
            },
            {
              id: "r-i-2",
              label: "/aɪ/",
              type: "rule",
              ipa: "/aɪ/",
              desc: "Âm đôi A-I (đọc như 'ai')",
              rule: "Phát âm là /aɪ/ khi đi trước cụm [phụ âm + e] (i_e) hoặc đi trước các cụm phụ âm đuôi -nd, -gh.",
              examples: [
                { word: "bite", ipa: "baɪt", meaning: "cắn" },
                { word: "kind", ipa: "kaɪnd", meaning: "tử tế/loại" },
                { word: "high", ipa: "haɪ", meaning: "cao" },
                { word: "light", ipa: "laɪt", meaning: "ánh sáng" }
              ]
            },
            {
              id: "r-i-3",
              label: "/ɜː/",
              type: "rule",
              ipa: "/ɜː/",
              desc: "Âm Ơ dài cong lưỡi",
              rule: "Phát âm là /ɜː/ khi đi liền trước âm r (tổ hợp ir) trong từ đơn tiết.",
              examples: [
                { word: "girl", ipa: "ɡɜːl", meaning: "cô gái" },
                { word: "bird", ipa: "bɜːd", meaning: "con chim" },
                { word: "shirt", ipa: "ʃɜːt", meaning: "áo sơ mi" }
              ]
            }
          ]
        },
        {
          id: "v-o",
          label: "o",
          type: "letter",
          category: "vowel-single",
          children: [
            {
              id: "r-o-1",
              label: "/ɒ/",
              type: "rule",
              ipa: "/ɒ/",
              desc: "Âm O ngắn (miệng mở tròn hơi dẹt)",
              rule: "Phát âm là /ɒ/ (UK) hoặc /ɑː/ (US) trong âm tiết khép kín kết thúc bằng phụ âm.",
              examples: [
                { word: "hot", ipa: "hɒt", meaning: "nóng" },
                { word: "dog", ipa: "dɒɡ", meaning: "con chó" },
                { word: "box", ipa: "bɒks", meaning: "cái hộp" },
                { word: "stop", ipa: "stɒp", meaning: "dừng lại" }
              ]
            },
            {
              id: "r-o-2",
              label: "/əʊ/",
              type: "rule",
              ipa: "/əʊ/",
              desc: "Âm đôi Ơ-U (đọc như 'âu')",
              rule: "Phát âm là /əʊ/ (hoặc /oʊ/ trong tiếng Mỹ) khi ở âm tiết mở, trước [phụ âm + e] (o_e), hoặc trước cụm -ld.",
              examples: [
                { word: "go", ipa: "ɡəʊ", meaning: "đi" },
                { word: "home", ipa: "həʊm", meaning: "nhà" },
                { word: "cold", ipa: "kəʊld", meaning: "lạnh" },
                { word: "stone", ipa: "stəʊn", meaning: "hòn đá" }
              ]
            },
            {
              id: "r-o-3",
              label: "/ʌ/",
              type: "rule",
              ipa: "/ʌ/",
              desc: "Âm Á ngắn",
              rule: "Một số từ thông dụng phát âm O thành /ʌ/ thay vì O ngắn.",
              examples: [
                { word: "son", ipa: "sʌn", meaning: "con trai" },
                { word: "come", ipa: "kʌm", meaning: "đến" },
                { word: "love", ipa: "lʌv", meaning: "yêu" },
                { word: "glove", ipa: "ɡlʌv", meaning: "găng tay" }
              ]
            },
            {
              id: "r-o-4",
              label: "/uː/",
              type: "rule",
              ipa: "/uː/",
              desc: "Âm U dài (chu môi kéo dài)",
              rule: "Một số từ ngắn đặc biệt phát âm là /uː/.",
              examples: [
                { word: "do", ipa: "duː", meaning: "làm" },
                { word: "to", ipa: "tuː", meaning: "đến/hướng tới" },
                { word: "move", ipa: "muːv", meaning: "di chuyển" },
                { word: "lose", ipa: "luːz", meaning: "mất/thua" }
              ]
            },
            {
              id: "r-o-5",
              label: "/ɜː/",
              type: "rule",
              ipa: "/ɜː/",
              desc: "Âm Ơ dài cong lưỡi",
              rule: "Phát âm là /ɜː/ khi đi sau w và đứng trước r (tổ hợp wor).",
              examples: [
                { word: "work", ipa: "wɜːk", meaning: "làm việc" },
                { word: "word", ipa: "wɜːd", meaning: "từ ngữ" },
                { word: "world", ipa: "wɜːld", meaning: "thế giới" }
              ]
            }
          ]
        },
        {
          id: "v-u",
          label: "u",
          type: "letter",
          category: "vowel-single",
          children: [
            {
              id: "r-u-1",
              label: "/ʌ/",
              type: "rule",
              ipa: "/ʌ/",
              desc: "Âm Á ngắn",
              rule: "Phát âm là /ʌ/ trong âm tiết khép kín kết thúc bằng phụ âm.",
              examples: [
                { word: "cup", ipa: "kʌp", meaning: "cái tách/chén" },
                { word: "cut", ipa: "kʌt", meaning: "cắt" },
                { word: "sun", ipa: "sʌn", meaning: "mặt trời" },
                { word: "run", ipa: "rʌn", meaning: "chạy" }
              ]
            },
            {
              id: "r-u-2",
              label: "/juː/",
              type: "rule",
              ipa: "/juː/",
              desc: "Âm I-U (đọc giống 'du-uy' hay 'diu')",
              rule: "Phát âm là /juː/ trong âm tiết mở hoặc đứng trước cụm [phụ âm + e] (u_e).",
              examples: [
                { word: "use", ipa: "juːz", meaning: "sử dụng" },
                { word: "cute", ipa: "kjuːt", meaning: "dễ thương" },
                { word: "music", ipa: "ˈmjuːzɪk", meaning: "âm nhạc" },
                { word: "unit", ipa: "ˈjuːnɪt", meaning: "đơn vị" }
              ]
            },
            {
              id: "r-u-3",
              label: "/uː/",
              type: "rule",
              ipa: "/uː/",
              desc: "Âm U dài chu môi",
              rule: "Phát âm là /uː/ khi đứng sau các âm /r/, /l/, /dʒ/ (chữ j, ch) trong cấu trúc u_e.",
              examples: [
                { word: "rule", ipa: "ruːl", meaning: "quy luật" },
                { word: "blue", ipa: "bluː", meaning: "màu xanh dương" },
                { word: "June", ipa: "dʒuːn", meaning: "tháng 6" },
                { word: "flute", ipa: "fluːt", meaning: "cây sáo" }
              ]
            },
            {
              id: "r-u-4",
              label: "/ʊ/",
              type: "rule",
              ipa: "/ʊ/",
              desc: "Âm U ngắn (hơi giống âm ư-u phát âm ngắn)",
              rule: "Một số từ kết thúc bằng l hoặc sh phát âm U thành /ʊ/.",
              examples: [
                { word: "put", ipa: "pʊt", meaning: "đặt/để" },
                { word: "push", ipa: "pʊʃ", meaning: "đẩy" },
                { word: "pull", ipa: "pʊl", meaning: "kéo" },
                { word: "full", ipa: "fʊl", meaning: "đầy" }
              ]
            },
            {
              id: "r-u-5",
              label: "/ɜː/",
              type: "rule",
              ipa: "/ɜː/",
              desc: "Âm Ơ dài cong lưỡi",
              rule: "Phát âm là /ɜː/ khi đi liền trước âm r (tổ hợp ur) trong từ đơn tiết.",
              examples: [
                { word: "burn", ipa: "bɜːn", meaning: "đốt cháy" },
                { word: "turn", ipa: "tɜːn", meaning: "xoay/lượt" },
                { word: "nurse", ipa: "nɜːs", meaning: "y tá" }
              ]
            }
          ]
        },
        {
          id: "v-y",
          label: "y",
          type: "letter",
          category: "vowel-single",
          children: [
            {
              id: "r-y-1",
              label: "/aɪ/",
              type: "rule",
              ipa: "/aɪ/",
              desc: "Âm đôi A-I",
              rule: "Phát âm là /aɪ/ khi đứng cuối từ một âm tiết (thay thế cho nguyên âm i).",
              examples: [
                { word: "my", ipa: "maɪ", meaning: "của tôi" },
                { word: "fly", ipa: "flaɪ", meaning: "bay/con ruồi" },
                { word: "cry", ipa: "kraɪ", meaning: "khóc" },
                { word: "by", ipa: "baɪ", meaning: "bởi/cạnh bên" }
              ]
            },
            {
              id: "r-y-2",
              label: "/i/",
              type: "rule",
              ipa: "/i/",
              desc: "Âm I ngắn (yếu)",
              rule: "Phát âm là /i/ hoặc /ɪ/ ở cuối từ có hai âm tiết trở lên và không được nhấn trọng âm.",
              examples: [
                { word: "baby", ipa: "ˈbeɪbi", meaning: "em bé" },
                { word: "happy", ipa: "ˈhæpi", meaning: "hạnh phúc" },
                { word: "very", ipa: "ˈveri", meaning: "rất" },
                { word: "lady", ipa: "ˈleɪdi", meaning: "quý cô" }
              ]
            },
            {
              id: "r-y-3",
              label: "/j/",
              type: "rule",
              ipa: "/j/",
              desc: "Phụ âm Dờ-I (đọc nhanh thành d/gi nhẹ)",
              rule: "Đóng vai trò là phụ âm /j/ khi đứng đầu từ trước một nguyên âm khác.",
              examples: [
                { word: "yes", ipa: "jes", meaning: "vâng/phải" },
                { word: "yellow", ipa: "ˈjeləʊ", meaning: "màu vàng" },
                { word: "young", ipa: "jʌŋ", meaning: "trẻ tuổi" }
              ]
            }
          ]
        }
      ]
    },
    {
      id: "vowel-digraph",
      label: "Nguyên âm ghép",
      type: "category",
      color: "var(--color-vowel-digraph)",
      children: [
        {
          id: "vd-ai",
          label: "ai / ay",
          type: "letter",
          category: "vowel-digraph",
          children: [
            {
              id: "r-ai-1",
              label: "/eɪ/",
              type: "rule",
              ipa: "/eɪ/",
              desc: "Âm đôi A-I (đọc như 'ây')",
              rule: "Hầu hết các tổ hợp AI hoặc AY đều phát âm là /eɪ/.",
              examples: [
                { word: "rain", ipa: "reɪn", meaning: "mưa" },
                { word: "wait", ipa: "weɪt", meaning: "chờ đợi" },
                { word: "day", ipa: "deɪn", meaning: "ngày" },
                { word: "play", ipa: "pleɪ", meaning: "chơi" }
              ]
            }
          ]
        },
        {
          id: "vd-ea",
          label: "ea",
          type: "letter",
          category: "vowel-digraph",
          children: [
            {
              id: "r-ea-1",
              label: "/iː/",
              type: "rule",
              ipa: "/iː/",
              desc: "Âm I dài căng",
              rule: "Đây là cách phát âm phổ biến nhất của tổ hợp EA.",
              examples: [
                { word: "meat", ipa: "miːt", meaning: "thịt" },
                { word: "seat", ipa: "siːt", meaning: "chỗ ngồi" },
                { word: "eat", ipa: "iːt", meaning: "ăn" },
                { word: "tea", ipa: "tiː", meaning: "trà" }
              ]
            },
            {
              id: "r-ea-2",
              label: "/e/",
              type: "rule",
              ipa: "/e/",
              desc: "Âm E ngắn",
              rule: "Tổ hợp EA phát âm thành /e/ trong một số từ thông dụng chỉ vật dụng, thức ăn hoặc trạng thái.",
              examples: [
                { word: "head", ipa: "hed", meaning: "cái đầu" },
                { word: "bread", ipa: "bred", meaning: "bánh mì" },
                { word: "heavy", ipa: "ˈhevi", meaning: "nặng" },
                { word: "dead", ipa: "ded", meaning: "chết" }
              ]
            },
            {
              id: "r-ea-3",
              label: "/ɪə/",
              type: "rule",
              ipa: "/ɪə/",
              desc: "Âm đôi I-Ơ",
              rule: "Phát âm là /ɪə/ khi tổ hợp ea đi liền trước r ở đuôi từ (ear).",
              examples: [
                { word: "near", ipa: "nɪə(r)", meaning: "gần" },
                { word: "hear", ipa: "hɪə(r)", meaning: "nghe" },
                { word: "clear", ipa: "klɪə(r)", meaning: "rõ ràng" }
              ]
            },
            {
              id: "r-ea-4",
              label: "/eə/",
              type: "rule",
              ipa: "/eə/",
              desc: "Âm đôi E-Ơ",
              rule: "Ngoại lệ phát âm thành /eə/ ở một số ít từ đi với r đặc biệt.",
              examples: [
                { word: "bear", ipa: "beə(r)", meaning: "con gấu" },
                { word: "pear", ipa: "peə(r)", meaning: "quả lê" },
                { word: "wear", ipa: "weə(r)", meaning: "mặc (áo)" }
              ]
            }
          ]
        },
        {
          id: "vd-ee",
          label: "ee",
          type: "letter",
          category: "vowel-digraph",
          children: [
            {
              id: "r-ee-1",
              label: "/iː/",
              type: "rule",
              ipa: "/iː/",
              desc: "Âm I dài căng",
              rule: "Tổ hợp hai chữ EE viết liền luôn luôn phát âm là /iː/.",
              examples: [
                { word: "meet", ipa: "miːt", meaning: "gặp gỡ" },
                { word: "green", ipa: "ɡriːn", meaning: "màu xanh lá" },
                { word: "tree", ipa: "triː", meaning: "cái cây" },
                { word: "feel", ipa: "fiːl", meaning: "cảm thấy" }
              ]
            }
          ]
        },
        {
          id: "vd-ei",
          label: "ei / ey",
          type: "letter",
          category: "vowel-digraph",
          children: [
            {
              id: "r-ei-1",
              label: "/eɪ/",
              type: "rule",
              ipa: "/eɪ/",
              desc: "Âm đôi A-I (đọc như 'ây')",
              rule: "Phát âm thành /eɪ/ trong phần lớn các từ chứa tổ hợp này.",
              examples: [
                { word: "vein", ipa: "veɪn", meaning: "tĩnh mạch" },
                { word: "grey", ipa: "ɡreɪ", meaning: "màu xám" },
                { word: "obey", ipa: "əˈbeɪ", meaning: "vâng lời" }
              ]
            },
            {
              id: "r-ei-2",
              label: "/iː/",
              type: "rule",
              ipa: "/iː/",
              desc: "Âm I dài căng",
              rule: "Phát âm thành /iː/ khi đứng sau chữ C (như ceive) hoặc một số ngoại lệ.",
              examples: [
                { word: "ceiling", ipa: "ˈsiːlɪŋ", meaning: "trần nhà" },
                { word: "receive", ipa: "rɪˈsiːv", meaning: "nhận được" },
                { word: "key", ipa: "kiː", meaning: "chìa khóa" }
              ]
            }
          ]
        },
        {
          id: "vd-oa",
          label: "oa",
          type: "letter",
          category: "vowel-digraph",
          children: [
            {
              id: "r-oa-1",
              label: "/əʊ/",
              type: "rule",
              ipa: "/əʊ/",
              desc: "Âm đôi Ơ-U (đọc như 'âu')",
              rule: "Tổ hợp OA hầu hết phát âm là /əʊ/ (UK) hoặc /oʊ/ (US) trong từ một âm tiết.",
              examples: [
                { word: "boat", ipa: "bəʊt", meaning: "con thuyền" },
                { word: "coat", ipa: "kəʊt", meaning: "áo khoác" },
                { word: "road", ipa: "rəʊd", meaning: "con đường" },
                { word: "soap", ipa: "səʊp", meaning: "xà phòng" }
              ]
            }
          ]
        },
        {
          id: "vd-oi",
          label: "oi / oy",
          type: "letter",
          category: "vowel-digraph",
          children: [
            {
              id: "r-oi-1",
              label: "/ɔɪ/",
              type: "rule",
              ipa: "/ɔɪ/",
              desc: "Âm đôi O-I (đọc như 'oi')",
              rule: "Tổ hợp OI (ở giữa từ) hoặc OY (ở cuối từ) luôn phát âm là /ɔɪ/.",
              examples: [
                { word: "coin", ipa: "kɔɪn", meaning: "đồng xu" },
                { word: "oil", ipa: "ɔɪl", meaning: "dầu ăn" },
                { word: "boy", ipa: "bɔɪ", meaning: "cậu bé" },
                { word: "toy", ipa: "tɔɪ", meaning: "đồ chơi" }
              ]
            }
          ]
        },
        {
          id: "vd-oo",
          label: "oo",
          type: "letter",
          category: "vowel-digraph",
          children: [
            {
              id: "r-oo-1",
              label: "/uː/",
              type: "rule",
              ipa: "/uː/",
              desc: "Âm U dài căng tròn môi",
              rule: "Đây là cách phát âm phổ biến nhất của tổ hợp OO.",
              examples: [
                { word: "moon", ipa: "muːn", meaning: "mặt trăng" },
                { word: "food", ipa: "fuːd", meaning: "thức ăn" },
                { word: "cool", ipa: "kuːl", meaning: "mát mẻ" },
                { word: "spoon", ipa: "spuːn", meaning: "cái thìa" }
              ]
            },
            {
              id: "r-oo-2",
              label: "/ʊ/",
              type: "rule",
              ipa: "/ʊ/",
              desc: "Âm U ngắn nhẹ",
              rule: "Thường phát âm ngắn lại thành /ʊ/ khi đứng liền trước phụ âm d, k, t.",
              examples: [
                { word: "book", ipa: "bʊk", meaning: "sách" },
                { word: "foot", ipa: "fʊt", meaning: "bàn chân" },
                { word: "good", ipa: "ɡʊd", meaning: "tốt" },
                { word: "look", ipa: "lʊk", meaning: "nhìn" }
              ]
            },
            {
              id: "r-oo-3",
              label: "/ʌ/",
              type: "rule",
              ipa: "/ʌ/",
              desc: "Âm Á ngắn",
              rule: "Một số ít ngoại lệ đặc biệt phát âm thành /ʌ/.",
              examples: [
                { word: "blood", ipa: "blʌd", meaning: "máu" },
                { word: "flood", ipa: "flʌd", meaning: "lũ lụt" }
              ]
            }
          ]
        },
        {
          id: "vd-ou",
          label: "ou",
          type: "letter",
          category: "vowel-digraph",
          children: [
            {
              id: "r-ou-1",
              label: "/aʊ/",
              type: "rule",
              ipa: "/aʊ/",
              desc: "Âm đôi A-U (đọc như 'ao')",
              rule: "Cách phát âm phổ biến nhất của tổ hợp OU.",
              examples: [
                { word: "out", ipa: "aʊt", meaning: "ra ngoài" },
                { word: "house", ipa: "haʊs", meaning: "ngôi nhà" },
                { word: "mouth", ipa: "maʊθ", meaning: "cái miệng" },
                { word: "cloud", ipa: "klaʊd", meaning: "đám mây" }
              ]
            },
            {
              id: "r-ou-2",
              label: "/uː/",
              type: "rule",
              ipa: "/uː/",
              desc: "Âm U dài chu môi",
              rule: "Tổ hợp OU được đọc thành /uː/ chủ yếu trong các từ mượn gốc Pháp.",
              examples: [
                { word: "soup", ipa: "suːp", meaning: "súp/canh" },
                { word: "group", ipa: "ɡruːp", meaning: "nhóm" },
                { word: "wound", ipa: "wuːnd", meaning: "vết thương" }
              ]
            },
            {
              id: "r-ou-3",
              label: "/ʌ/",
              type: "rule",
              ipa: "/ʌ/",
              desc: "Âm Á ngắn",
              rule: "Tổ hợp OU được phát âm ngắn thành /ʌ/ trong một số từ thông dụng ghép hoặc trạng thái.",
              examples: [
                { word: "double", ipa: "ˈdʌbl", meaning: "gấp đôi" },
                { word: "cousin", ipa: "ˈkʌzn", meaning: "anh chị em họ" },
                { word: "tough", ipa: "tʌf", meaning: "dai/khó khăn" }
              ]
            },
            {
              id: "r-ou-4",
              label: "/ɔː/",
              type: "rule",
              ipa: "/ɔː/",
              desc: "Âm O dài căng",
              rule: "Phát âm thành /ɔː/ khi đi trong nhóm đuôi -ought của các động từ chia quá khứ.",
              examples: [
                { word: "thought", ipa: "θɔːt", meaning: "suy nghĩ (V2)" },
                { word: "bought", ipa: "bɔːt", meaning: "mua (V2)" },
                { word: "fought", ipa: "fɔːt", meaning: "chiến đấu (V2)" }
              ]
            }
          ]
        },
        {
          id: "vd-ow",
          label: "ow",
          type: "letter",
          category: "vowel-digraph",
          children: [
            {
              id: "r-ow-1",
              label: "/aʊ/",
              type: "rule",
              ipa: "/aʊ/",
              desc: "Âm đôi A-U (đọc như 'ao')",
              rule: "Phát âm là /aʊ/ khi đứng ở cuối từ ngắn hoặc trước các phụ âm n, l.",
              examples: [
                { word: "cow", ipa: "kaʊ", meaning: "con bò sữa" },
                { word: "now", ipa: "naʊ", meaning: "bây giờ" },
                { word: "town", ipa: "taʊn", meaning: "thị trấn" },
                { word: "flower", ipa: "ˈflaʊə(r)", meaning: "bông hoa" }
              ]
            },
            {
              id: "r-ow-2",
              label: "/əʊ/",
              type: "rule",
              ipa: "/əʊ/",
              desc: "Âm đôi Ơ-U (đọc như 'âu')",
              rule: "Tổ hợp OW thường được phát âm thành /əʊ/ khi ở cuối các từ chứa nhiều âm tiết hoặc động từ chỉ sự hành động chậm rãi.",
              examples: [
                { word: "blow", ipa: "bləʊ", meaning: "thổi" },
                { word: "snow", ipa: "snəʊ", meaning: "tuyết rơi" },
                { word: "grow", ipa: "ɡrəʊ", meaning: "lớn lên/trồng" },
                { word: "show", ipa: "ʃəʊ", meaning: "trình diễn" }
              ]
            }
          ]
        }
      ]
    },
    {
      id: "consonant-digraph",
      label: "Phụ âm ghép",
      type: "category",
      color: "var(--color-consonant-digraph)",
      children: [
        {
          id: "cd-ch",
          label: "ch",
          type: "letter",
          category: "consonant-digraph",
          children: [
            {
              id: "r-ch-1",
              label: "/tʃ/",
              type: "rule",
              ipa: "/tʃ/",
              desc: "Âm Chờ bật hơi nặng",
              rule: "Cách đọc nguyên bản phổ thông nhất của CH trong tiếng Anh.",
              examples: [
                { word: "chair", ipa: "tʃeə(r)", meaning: "cái ghế" },
                { word: "cheap", ipa: "tʃiːp", meaning: "rẻ tiền" },
                { word: "much", ipa: "mʌtʃ", meaning: "nhiều" },
                { word: "church", ipa: "tʃɜːtʃ", meaning: "nhà thờ" }
              ]
            },
            {
              id: "r-ch-2",
              label: "/k/",
              type: "rule",
              ipa: "/k/",
              desc: "Âm Cờ/Khờ cổ họng",
              rule: "Tổ hợp CH đọc thành /k/ trong các từ mượn có nguồn gốc Hy Lạp (thường liên quan khoa học, y tế, lịch sử).",
              examples: [
                { word: "school", ipa: "skuːl", meaning: "trường học" },
                { word: "chemist", ipa: "ˈkemɪst", meaning: "nhà hóa học" },
                { word: "character", ipa: "ˈkærəktə(r)", meaning: "nhân vật" },
                { word: "echo", ipa: "ˈekəʊ", meaning: "tiếng vang" }
              ]
            },
            {
              id: "r-ch-3",
              label: "/ʃ/",
              type: "rule",
              ipa: "/ʃ/",
              desc: "Âm Sờ nặng thổi gió",
              rule: "CH đọc thành /ʃ/ trong các từ mượn trực tiếp từ tiếng Pháp hiện đại.",
              examples: [
                { word: "chef", ipa: "ʃef", meaning: "đầu bếp trưởng" },
                { word: "machine", ipa: "məˈʃiːn", meaning: "máy móc" },
                { word: "champagne", ipa: "ʃæmˈpeɪn", meaning: "rượu sâm-panh" }
              ]
            }
          ]
        },
        {
          id: "cd-sh",
          label: "sh",
          type: "letter",
          category: "consonant-digraph",
          children: [
            {
              id: "r-sh-1",
              label: "/ʃ/",
              type: "rule",
              ipa: "/ʃ/",
              desc: "Âm Sờ nặng bật hơi rộng môi",
              rule: "Tổ hợp SH luôn luôn phát âm là /ʃ/.",
              examples: [
                { word: "ship", ipa: "ʃɪp", meaning: "tàu thủy" },
                { word: "shoe", ipa: "ʃuː", meaning: "chiếc giày" },
                { word: "fish", ipa: "fɪʃ", meaning: "con cá" },
                { word: "wash", ipa: "wɒʃ", meaning: "rửa/giặt" }
              ]
            }
          ]
        },
        {
          id: "cd-th",
          label: "th",
          type: "letter",
          category: "consonant-digraph",
          children: [
            {
              id: "r-th-1",
              label: "/θ/",
              type: "rule",
              ipa: "/θ/",
              desc: "Âm Th thổi hơi vô thanh (kẹp lưỡi giữa hai hàm răng)",
              rule: "Phát âm vô thanh /θ/ (không rung cổ họng), thường gặp ở các từ loại như danh từ, tính từ, động từ nội tại.",
              examples: [
                { word: "think", ipa: "θɪŋk", meaning: "suy nghĩ" },
                { word: "thin", ipa: "θɪn", meaning: "mỏng/gầy" },
                { word: "thank", ipa: "θæŋk", meaning: "cảm ơn" },
                { word: "bath", ipa: "bɑːθ", meaning: "bồn tắm" }
              ]
            },
            {
              id: "r-th-2",
              label: "/ð/",
              type: "rule",
              ipa: "/ð/",
              desc: "Âm Th rung hữu thanh (kẹp lưỡi giữa răng, rung thanh quản)",
              rule: "Phát âm hữu thanh /ð/ (rung dây thanh), thường gặp ở các đại từ chỉ định, liên từ và giới từ (như this, that, they, with).",
              examples: [
                { word: "this", ipa: "ðɪs", meaning: "đây/cái này" },
                { word: "that", ipa: "ðæt", meaning: "kia/cái kia" },
                { word: "they", ipa: "ðeɪ", meaning: "họ/chúng nó" },
                { word: "mother", ipa: "ˈmʌðə(r)", meaning: "mẹ" }
              ]
            }
          ]
        },
        {
          id: "cd-ph",
          label: "ph",
          type: "letter",
          category: "consonant-digraph",
          children: [
            {
              id: "r-ph-1",
              label: "/f/",
              type: "rule",
              ipa: "/f/",
              desc: "Âm Phờ nhẹ răng dưới chạm môi trên",
              rule: "Tổ hợp PH luôn luôn phát âm giống âm /f/.",
              examples: [
                { word: "phone", ipa: "fəʊn", meaning: "điện thoại" },
                { word: "photo", ipa: "ˈfəʊtəʊ", meaning: "bức ảnh" },
                { word: "dolphin", ipa: "ˈdɒlfɪn", meaning: "cá heo" },
                { word: "alphabet", ipa: "ˈælfəbet", meaning: "bảng chữ cái" }
              ]
            }
          ]
        },
        {
          id: "cd-gh",
          label: "gh",
          type: "letter",
          category: "consonant-digraph",
          children: [
            {
              id: "r-gh-1",
              label: "/f/",
              type: "rule",
              ipa: "/f/",
              desc: "Âm Phờ nhẹ răng dưới chạm môi trên",
              rule: "Phát âm thành /f/ khi đứng ở cuối từ trong một số từ đặc thù.",
              examples: [
                { word: "laugh", ipa: "lɑːf", meaning: "cười lớn" },
                { word: "cough", ipa: "kɒf", meaning: "ho" },
                { word: "tough", ipa: "tʌf", meaning: "dai/cứng cáp" },
                { word: "rough", ipa: "rʌf", meaning: "gồ ghề/nhám" }
              ]
            },
            {
              id: "r-gh-2",
              label: "câm",
              type: "rule",
              ipa: "",
              desc: "Âm câm (hoàn toàn không phát âm)",
              rule: "Tổ hợp GH hoàn toàn không phát âm (âm câm) khi đi sau các nguyên âm dài như i (igh) hoặc đứng trước chữ t.",
              examples: [
                { word: "high", ipa: "haɪ", meaning: "cao" },
                { word: "night", ipa: "naɪt", meaning: "ban đêm" },
                { word: "light", ipa: "laɪt", meaning: "ánh sáng" },
                { word: "daughter", ipa: "ˈdɔːtə(r)", meaning: "con gái" }
              ]
            }
          ]
        },
        {
          id: "cd-ng",
          label: "ng",
          type: "letter",
          category: "consonant-digraph",
          children: [
            {
              id: "r-ng-1",
              label: "/ŋ/",
              type: "rule",
              ipa: "/ŋ/",
              desc: "Âm Ngờ mũi (không phát âm G cứng)",
              rule: "Tổ hợp NG đứng ở cuối từ đọc thành âm mũi /ŋ/.",
              examples: [
                { word: "sing", ipa: "sɪŋ", meaning: "hát" },
                { word: "king", ipa: "kɪŋ", meaning: "vua" },
                { word: "ring", ipa: "rɪŋ", meaning: "chiếc nhẫn" },
                { word: "song", ipa: "sɒŋ", meaning: "bài hát" }
              ]
            }
          ]
        },
        {
          id: "cd-wh",
          label: "wh",
          type: "letter",
          category: "consonant-digraph",
          children: [
            {
              id: "r-wh-1",
              label: "/w/",
              type: "rule",
              ipa: "/w/",
              desc: "Âm Quờ môi chu nhẹ",
              rule: "Phát âm là /w/ ở hầu hết các từ thông dụng (chữ H câm).",
              examples: [
                { word: "what", ipa: "wɒt", meaning: "cái gì" },
                { word: "when", ipa: "wen", meaning: "khi nào" },
                { word: "where", ipa: "weə(r)", meaning: "ở đâu" },
                { word: "why", ipa: "waɪ", meaning: "tại sao" }
              ]
            },
            {
              id: "r-wh-2",
              label: "/h/",
              type: "rule",
              ipa: "/h/",
              desc: "Âm Hờ hơi bay nhẹ (chữ W câm)",
              rule: "Phát âm là /h/ khi tổ hợp WH đi liền trước nguyên âm O (W bị câm).",
              examples: [
                { word: "who", ipa: "huː", meaning: "ai" },
                { word: "whom", ipa: "huːm", meaning: "ai (tân ngữ)" },
                { word: "whose", ipa: "huːz", meaning: "của ai" },
                { word: "whole", ipa: "həʊl", meaning: "toàn bộ" }
              ]
            }
          ]
        }
      ]
    }
  ]
};

// --- 2. HỆ THỐNG VẼ MINDMAP ĐỘNG (SVG MINDMAP CONTROLLER) ---
class SVGMindmap {
  constructor(svgElementId, data) {
    this.svg = document.getElementById(svgElementId);
    this.zoomGroup = document.getElementById("zoom-group");
    this.linksGroup = document.getElementById("links-group");
    this.nodesGroup = document.getElementById("nodes-group");
    this.rawTreeData = data;

    // Quản lý Zoom & Pan
    this.transform = { x: 0, y: 0, k: 1 };
    this.isDragging = false;
    this.dragStart = { x: 0, y: 0 };

    // Cấu trúc phẳng của Mindmap phục vụ vẽ và tìm kiếm
    this.nodes = [];
    this.links = [];
    this.nodeMap = new Map();

    // Cấu hình Kích thước Layout
    this.vGap = 42; // Khoảng cách dòng giữa các nút ngang cấp
    this.hGap = 160; // Khoảng cách cột giữa các cấp (level)

    this.init();
  }

  init() {
    this.setupZoomPan();
    this.processData();
    this.render();
    this.centerView();
  }

  // Chuyển đổi dữ liệu phân cấp thành dạng phẳng và tính toán trạng thái
  processData() {
    this.nodes = [];
    this.links = [];
    this.nodeMap.clear();

    const traverse = (node, parentNode = null, level = 0) => {
      // Thiết lập các thuộc tính vẽ cơ bản cho từng nút
      const flatNode = {
        id: node.id,
        label: node.label,
        type: node.type,
        category: node.category || (parentNode ? parentNode.category : null),
        parent: parentNode ? parentNode.id : null,
        level: level,
        color: node.color || (parentNode ? parentNode.color : "var(--primary)"),
        childrenIds: node.children ? node.children.map(c => c.id) : [],
        collapsed: node.collapsed !== undefined ? node.collapsed : (level >= 2), // Mặc định thu gọn các âm nhỏ level 3
        ipa: node.ipa || "",
        desc: node.desc || "",
        rule: node.rule || "",
        examples: node.examples || [],
        x: 0,
        y: 0
      };

      this.nodes.push(flatNode);
      this.nodeMap.set(node.id, flatNode);

      if (node.children) {
        node.children.forEach(child => {
          traverse(child, flatNode, level + 1);
        });
      }
    };

    traverse(this.rawTreeData);
    this.updateLinks();
  }

  updateLinks() {
    this.links = [];
    this.nodes.forEach(node => {
      if (node.parent) {
        const parentNode = this.nodeMap.get(node.parent);
        // Chỉ vẽ link nếu nút cha hiện tại không bị collapse và cả hai đều hiển thị
        if (parentNode && !parentNode.collapsed && this.isNodeVisible(node.id)) {
          this.links.push({
            source: node.parent,
            target: node.id
          });
        }
      }
    });
  }

  isNodeVisible(nodeId) {
    const node = this.nodeMap.get(nodeId);
    if (!node) return false;
    if (node.id === "root") return true;

    let current = node;
    while (current.parent) {
      const parentNode = this.nodeMap.get(current.parent);
      if (parentNode.collapsed) return false;
      current = parentNode;
    }
    return true;
  }

  // Thuật toán tính toán vị trí Node đối xứng không đè lên nhau (Dynamic Subtree Spacing)
  calculateLayout() {
    const root = this.nodeMap.get("root");
    root.x = 0;
    root.y = 0;

    // Tính toán chiều cao của mỗi nhánh dựa trên các node con đang mở rộng
    const measureNode = (node) => {
      if (!this.isNodeVisible(node.id)) {
        return 0;
      }
      if (node.collapsed || node.childrenIds.length === 0) {
        if (node.level === 3) return 38; // Chiều cao rule leaf node
        if (node.level === 2) return 48; // Chiều cao letter node
        return 58; // Chiều cao category node
      }
      let childrenHeight = 0;
      let visibleCount = 0;
      node.childrenIds.forEach(childId => {
        const child = this.nodeMap.get(childId);
        if (this.isNodeVisible(childId)) {
          childrenHeight += measureNode(child);
          visibleCount++;
        }
      });
      const gap = node.level === 2 ? 12 : (node.level === 1 ? 22 : 32);
      const totalHeight = childrenHeight + (visibleCount - 1) * gap;
      return totalHeight;
    };

    // Đặt vị trí các node con đệ quy bao quanh vị trí yCenter của cha
    const positionSubtree = (node, x, yCenter, directionX) => {
      node.x = x;
      node.y = yCenter;

      if (node.collapsed || node.childrenIds.length === 0) return;

      const visibleChildren = node.childrenIds
        .map(id => this.nodeMap.get(id))
        .filter(child => this.isNodeVisible(child.id));

      if (visibleChildren.length === 0) return;

      // Đo đạc và đặt vị trí các con
      const childrenHeights = visibleChildren.map(child => measureNode(child));
      const gap = node.level === 2 ? 12 : (node.level === 1 ? 22 : 32);
      
      const totalHeight = childrenHeights.reduce((sum, h) => sum + h, 0) + (visibleChildren.length - 1) * gap;
      let yStart = yCenter - totalHeight / 2;

      visibleChildren.forEach((child, index) => {
        const childHeight = childrenHeights[index];
        const childYCenter = yStart + childHeight / 2;
        
        // Điều chỉnh khoảng cách ngang (horizontal spacing) cho thoáng đãng
        let childHGap = this.hGap;
        if (node.level === 1) childHGap = this.hGap * 1.25;
        else if (node.level === 2) childHGap = this.hGap * 1.35;

        const nextX = x + directionX * childHGap;
        positionSubtree(child, nextX, childYCenter, directionX);
        yStart += childHeight + gap;
      });
    };

    // Phân chia hai phía của Mindmap (Trái / Phải) xoay quanh gốc (0,0)
    // Phía bên trái (Left side): vowel-single
    const leftCategoryIds = ["vowel-single"];
    const leftCategories = leftCategoryIds
      .map(id => this.nodeMap.get(id))
      .filter(node => node && this.isNodeVisible(node.id));

    if (leftCategories.length > 0) {
      const leftHeights = leftCategories.map(cat => measureNode(cat));
      const leftGap = 40;
      const leftTotalHeight = leftHeights.reduce((sum, h) => sum + h, 0) + (leftCategories.length - 1) * leftGap;
      let yStart = 0 - leftTotalHeight / 2;

      leftCategories.forEach((cat, index) => {
        const catHeight = leftHeights[index];
        const catYCenter = yStart + catHeight / 2;
        positionSubtree(cat, -this.hGap, catYCenter, -1);
        yStart += catHeight + leftGap;
      });
    }

    // Phía bên phải (Right side): vowel-digraph và consonant-digraph
    const rightCategoryIds = ["vowel-digraph", "consonant-digraph"];
    const rightCategories = rightCategoryIds
      .map(id => this.nodeMap.get(id))
      .filter(node => node && this.isNodeVisible(node.id));

    if (rightCategories.length > 0) {
      const rightHeights = rightCategories.map(cat => measureNode(cat));
      const rightGap = 40;
      const rightTotalHeight = rightHeights.reduce((sum, h) => sum + h, 0) + (rightCategories.length - 1) * rightGap;
      let yStart = 0 - rightTotalHeight / 2;

      rightCategories.forEach((cat, index) => {
        const catHeight = rightHeights[index];
        const catYCenter = yStart + catHeight / 2;
        positionSubtree(cat, this.hGap, catYCenter, 1);
        yStart += catHeight + rightGap;
      });
    }
  }

  render() {
    this.calculateLayout();
    this.updateLinks();

    // 1. RENDER LINKS (Đường dẫn dạng Bezier mượt mà)
    this.linksGroup.innerHTML = "";
    this.links.forEach(link => {
      const sourceNode = this.nodeMap.get(link.source);
      const targetNode = this.nodeMap.get(link.target);
      if (!sourceNode || !targetNode) return;

      const pathData = this.calculateBezierPath(sourceNode, targetNode);
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", pathData);
      path.setAttribute("class", `link link-from-${sourceNode.id} link-to-${targetNode.id}`);
      path.setAttribute("id", `link-${sourceNode.id}-${targetNode.id}`);

      // Đặt màu nhạt theo màu của nhánh cha
      path.style.stroke = targetNode.color;
      this.linksGroup.appendChild(path);
    });

    // 2. RENDER NODES
    this.nodesGroup.innerHTML = "";
    this.nodes.forEach(node => {
      if (!this.isNodeVisible(node.id)) return;

      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.setAttribute("class", `node level-${node.level} ${node.category || ''}`);
      g.setAttribute("id", `node-${node.id}`);
      g.setAttribute("transform", `translate(${node.x}, ${node.y})`);

      // Hình tròn bao quanh
      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("class", "node-circle");

      // Bán kính thay đổi dựa trên cấp độ của nút
      let radius = 7;
      if (node.level === 0) radius = 16;
      else if (node.level === 1) radius = 11;
      else if (node.level === 2) radius = 9;

      circle.setAttribute("r", radius);
      circle.style.stroke = node.color;
      g.appendChild(circle);

      // Nếu có con và bị thu gọn, hiển thị dấu cộng nhỏ ở tâm
      if (node.childrenIds.length > 0 && node.collapsed) {
        g.classList.add("collapsed");
      }

      // Văn bản hiển thị
      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("class", "node-text");
      text.textContent = node.label;

      // Căn lề chữ dựa trên nhánh ở bên trái hay bên phải
      if (node.level === 0) {
        text.setAttribute("text-anchor", "middle");
        text.setAttribute("y", "-24");
      } else {
        const isLeft = node.x < 0;
        text.setAttribute("text-anchor", isLeft ? "end" : "start");
        text.setAttribute("x", isLeft ? "-15" : "15");
        text.setAttribute("y", "4");
      }

      g.appendChild(text);

      // Sự kiện nhấp chuột tương tác
      g.addEventListener("click", (e) => {
        e.stopPropagation();
        this.handleNodeClick(node);
      });

      this.nodesGroup.appendChild(g);
    });
  }

  // Tính toán đường cong Bezier nối hai nút
  calculateBezierPath(source, target) {
    const x0 = source.x;
    const y0 = source.y;
    const x1 = target.x;
    const y1 = target.y;

    // Điều khiển điểm uốn để đường vẽ uốn lượn ngang đều hai bên
    const cpX = (x0 + x1) / 2;
    return `M ${x0} ${y0} C ${cpX} ${y0}, ${cpX} ${y1}, ${x1} ${y1}`;
  }

  handleNodeClick(node) {
    // 1. Highlight nút đang chọn
    document.querySelectorAll(".node").forEach(el => el.classList.remove("active"));
    const nodeEl = document.getElementById(`node-${node.id}`);
    if (nodeEl) nodeEl.classList.add("active");

    // Highlight đường đi nối từ node này về gốc (path trace)
    this.highlightPathToRoot(node.id);

    // 2. Xử lý đóng/mở nhánh nếu có con
    if (node.childrenIds.length > 0) {
      // Chuyển đổi trạng thái đóng mở
      node.collapsed = !node.collapsed;
      this.render();
      // Giữ focus cho nút vừa bấm sau khi vẽ lại
      const freshNodeEl = document.getElementById(`node-${node.id}`);
      if (freshNodeEl) freshNodeEl.classList.add("active");
    }

    // 3. Mở ngăn kéo chi tiết (Details Drawer)
    openDetailsDrawer(node);
  }

  highlightPathToRoot(nodeId) {
    // Khôi phục tất cả link và node về trạng thái thường
    document.querySelectorAll(".link").forEach(el => {
      el.classList.remove("highlighted", "dimmed");
    });
    document.querySelectorAll(".node").forEach(el => {
      el.classList.remove("dimmed");
    });

    if (nodeId === "root") return;

    // Nếu chọn một node cụ thể, ta làm mờ toàn bộ các node khác và chỉ làm nổi bật đường đi
    document.querySelectorAll(".link").forEach(el => el.classList.add("dimmed"));
    document.querySelectorAll(".node").forEach(el => {
      if (el.id !== "node-root") el.classList.add("dimmed");
    });

    let currentId = nodeId;
    const activeNodeEl = document.getElementById(`node-${currentId}`);
    if (activeNodeEl) activeNodeEl.classList.remove("dimmed");

    while (currentId) {
      const node = this.nodeMap.get(currentId);
      if (!node || !node.parent) break;

      const parentId = node.parent;
      const linkEl = document.getElementById(`link-${parentId}-${currentId}`);
      const parentNodeEl = document.getElementById(`node-${parentId}`);

      if (linkEl) {
        linkEl.classList.remove("dimmed");
        linkEl.classList.add("highlighted");
      }
      if (parentNodeEl) {
        parentNodeEl.classList.remove("dimmed");
      }
      currentId = parentId;
    }
  }

  // --- Zoom & Pan Logic ---
  setupZoomPan() {
    // Nhấp vào màn hình trống để đặt lại các nổi bật đường vẽ
    this.svg.addEventListener("click", () => {
      document.querySelectorAll(".node").forEach(el => el.classList.remove("active", "dimmed"));
      document.querySelectorAll(".link").forEach(el => el.classList.remove("highlighted", "dimmed"));
      closeDrawer();
    });

    // Kéo thả di chuyển (Pan)
    this.svg.addEventListener("mousedown", (e) => {
      if (e.button !== 0) return; // Chỉ cho phép chuột trái
      this.isDragging = true;
      this.svg.style.cursor = "grabbing";
      this.dragStart.x = e.clientX - this.transform.x;
      this.dragStart.y = e.clientY - this.transform.y;
    });

    window.addEventListener("mousemove", (e) => {
      if (!this.isDragging) return;
      this.transform.x = e.clientX - this.dragStart.x;
      this.transform.y = e.clientY - this.dragStart.y;
      this.applyTransform();
    });

    window.addEventListener("mouseup", () => {
      if (this.isDragging) {
        this.isDragging = false;
        this.svg.style.cursor = "grab";
      }
    });

    // Cuộn chuột phóng to/thu nhỏ (Zoom)
    this.svg.addEventListener("wheel", (e) => {
      e.preventDefault();
      const zoomFactor = 1.1;
      const mouseX = e.clientX - this.svg.getBoundingClientRect().left;
      const mouseY = e.clientY - this.svg.getBoundingClientRect().top;

      const prevK = this.transform.k;
      if (e.deltaY < 0) {
        this.transform.k = Math.min(this.transform.k * zoomFactor, 3.0); // max zoom 3x
      } else {
        this.transform.k = Math.max(this.transform.k / zoomFactor, 0.4); // min zoom 0.4x
      }

      // Zoom căn chỉnh theo vị trí con trỏ chuột
      this.transform.x = mouseX - (mouseX - this.transform.x) * (this.transform.k / prevK);
      this.transform.y = mouseY - (mouseY - this.transform.y) * (this.transform.k / prevK);

      this.applyTransform();
    }, { passive: false });

    // Hỗ trợ cảm ứng vuốt trên mobile
    let touchStartDist = 0;
    let touchStartScale = 1;

    this.svg.addEventListener("touchstart", (e) => {
      if (e.touches.length === 1) {
        this.isDragging = true;
        this.dragStart.x = e.touches[0].clientX - this.transform.x;
        this.dragStart.y = e.touches[0].clientY - this.transform.y;
      } else if (e.touches.length === 2) {
        this.isDragging = false;
        touchStartDist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
        touchStartScale = this.transform.k;
      }
    });

    this.svg.addEventListener("touchmove", (e) => {
      if (this.isDragging && e.touches.length === 1) {
        this.transform.x = e.touches[0].clientX - this.dragStart.x;
        this.transform.y = e.touches[0].clientY - this.dragStart.y;
        this.applyTransform();
      } else if (e.touches.length === 2) {
        const dist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
        const factor = dist / touchStartDist;
        this.transform.k = Math.max(0.4, Math.min(touchStartScale * factor, 3.0));
        this.applyTransform();
      }
    });

    this.svg.addEventListener("touchend", () => {
      this.isDragging = false;
    });
  }

  applyTransform() {
    this.zoomGroup.setAttribute(
      "transform",
      `translate(${this.transform.x}, ${this.transform.y}) scale(${this.transform.k})`
    );
  }

  centerView() {
    // Đặt sơ đồ tư duy vào chính giữa khung hiển thị
    const rect = this.svg.getBoundingClientRect();
    this.transform.x = rect.width / 2;
    this.transform.y = rect.height / 2;
    this.transform.k = 0.8;
    this.applyTransform();
  }

  zoomIn() {
    this.transform.k = Math.min(this.transform.k * 1.2, 3.0);
    this.applyTransform();
  }

  zoomOut() {
    this.transform.k = Math.max(this.transform.k / 1.2, 0.4);
    this.applyTransform();
  }

  expandAll() {
    this.nodes.forEach(n => {
      if (n.childrenIds.length > 0) n.collapsed = false;
    });
    this.render();
  }

  collapseAll() {
    this.nodes.forEach(n => {
      if (n.childrenIds.length > 0 && n.level >= 1) n.collapsed = true;
    });
    this.render();
    this.centerView();
  }

  // Tô sáng nút tìm kiếm
  searchNodes(query) {
    if (!query) {
      this.nodes.forEach(n => n.collapsed = n.level >= 2);
      this.render();
      document.querySelectorAll(".node").forEach(el => el.classList.remove("highlighted"));
      return;
    }

    const q = query.toLowerCase().trim();
    let matchedId = null;

    this.nodes.forEach(node => {
      const matchLabel = node.label.toLowerCase().includes(q);
      const matchIpa = node.ipa.toLowerCase().includes(q);
      const matchRule = node.rule.toLowerCase().includes(q);
      const matchExample = node.examples.some(ex => ex.word.toLowerCase().includes(q));

      if (matchLabel || matchIpa || matchRule || matchExample) {
        node.collapsed = false; // Mở rộng node để đảm bảo nó hiển thị

        // Mở rộng tất cả cha của nó
        let parent = this.nodeMap.get(node.parent);
        while (parent) {
          parent.collapsed = false;
          parent = this.nodeMap.get(parent.parent);
        }

        if (!matchedId || node.label.toLowerCase() === q) {
          matchedId = node.id;
        }
      }
    });

    this.render();

    // Tô sáng các node khớp
    this.nodes.forEach(node => {
      const nodeEl = document.getElementById(`node-${node.id}`);
      if (!nodeEl) return;

      const matchLabel = node.label.toLowerCase().includes(q);
      const matchIpa = node.ipa && node.ipa.toLowerCase().includes(q);
      const matchExample = node.examples.some(ex => ex.word.toLowerCase().includes(q));

      if (matchLabel || matchIpa || matchExample) {
        nodeEl.classList.add("highlighted");
      } else {
        nodeEl.classList.remove("highlighted");
      }
    });

    // Cuộn tới node khớp đầu tiên
    if (matchedId) {
      const target = this.nodeMap.get(matchedId);
      const rect = this.svg.getBoundingClientRect();
      this.transform.x = rect.width / 2 - target.x * this.transform.k;
      this.transform.y = rect.height / 2 - target.y * this.transform.k;
      this.applyTransform();
    }
  }

  // Lọc nhanh hiển thị
  filterCategory(category) {
    if (category === "all") {
      this.expandAll();
      return;
    }

    // Collapse hết tất cả
    this.nodes.forEach(n => {
      if (n.level >= 1) n.collapsed = true;
    });

    // Mở đúng nhánh được lọc
    const matchedCategoryNode = this.nodes.find(n => n.id === category);
    if (matchedCategoryNode) {
      matchedCategoryNode.collapsed = false;
      matchedCategoryNode.childrenIds.forEach(id => {
        const child = this.nodeMap.get(id);
        if (child) child.collapsed = false;
      });
    }

    this.render();
    this.centerView();
  }
}

// --- 3. ĐIỀU KHIỂN CHI TIẾT PHÁT ÂM (DETAILS DRAWER CONTROLLER) ---
const drawer = document.getElementById("details-drawer");
const drawerBackdrop = document.getElementById("drawer-backdrop");
const drawerCategory = document.getElementById("drawer-category");
const drawerTitle = document.getElementById("drawer-title");
const drawerIntro = document.getElementById("drawer-intro");
const drawerAllRulesList = document.getElementById("drawer-all-rules-list");
const drawerDetailView = document.getElementById("drawer-detail-view");

const detailIpaSymbol = document.getElementById("detail-ipa-symbol");
const detailIpaDesc = document.getElementById("detail-ipa-desc");
const detailRuleText = document.getElementById("detail-rule-text");
const detailExamplesList = document.getElementById("detail-examples-list");
const practiceWordSelect = document.getElementById("practice-word-select");

function openDetailsDrawer(node) {
  drawer.classList.add("open");
  drawerBackdrop.classList.add("active");
  drawer.setAttribute("aria-hidden", "false");

  // Thiết lập badge danh mục
  const catNames = {
    "vowel-single": "Nguyên âm đơn",
    "vowel-digraph": "Nguyên âm ghép",
    "consonant-digraph": "Phụ âm ghép"
  };
  drawerCategory.textContent = catNames[node.category] || "Gốc sơ đồ";

  if (node.level === 2) {
    // 1. Trạng thái Click vào chữ cái lớn (như A, E, CH...)
    drawerTitle.textContent = `Tổ hợp: ${node.label}`;
    drawerIntro.hidden = false;
    drawerDetailView.hidden = true;

    // Hiển thị danh sách nhanh tất cả quy tắc của chữ này
    drawerAllRulesList.innerHTML = "";
    node.childrenIds.forEach(id => {
      const ruleNode = mapInstance.nodeMap.get(id);
      if (!ruleNode) return;

      const item = document.createElement("div");
      item.className = "all-rules-item";
      item.innerHTML = `
        <span class="rule-ipa-badge">${ruleNode.ipa || 'câm'}</span>
        <div class="rule-summary-text">
          <strong>${ruleNode.desc}</strong>
          <span>${ruleNode.rule.substring(0, 52)}...</span>
        </div>
      `;
      item.addEventListener("click", () => {
        // Chuyển sang hiển thị chi tiết âm này
        showRuleDetail(ruleNode);
      });
      drawerAllRulesList.appendChild(item);
    });

  } else if (node.level === 3) {
    // 2. Trạng thái Click trực tiếp vào âm cụ thể (như /æ/, /tʃ/...)
    const parentNode = mapInstance.nodeMap.get(node.parent);
    drawerTitle.textContent = `Tổ hợp: ${parentNode ? parentNode.label : ''}`;
    showRuleDetail(node);
  } else {
    // Click vào root hoặc category
    drawerTitle.textContent = node.label;
    drawerIntro.hidden = false;
    drawerDetailView.hidden = true;
    drawerAllRulesList.innerHTML = `<p style="font-size:13px; color:var(--text-secondary)">Hãy chọn một chữ cái hoặc âm để tra cứu chi tiết.</p>`;
  }
}

function showRuleDetail(ruleNode) {
  drawerIntro.hidden = true;
  drawerDetailView.hidden = false;

  // Điền dữ liệu quy tắc
  detailIpaSymbol.textContent = ruleNode.ipa || "âm câm";
  detailIpaDesc.textContent = ruleNode.desc;
  detailRuleText.textContent = ruleNode.rule;

  // Nút nghe phát âm của chính ký tự âm đó
  const speakIpaBtn = document.getElementById("speak-ipa-btn");
  speakIpaBtn.onclick = () => speakText(ruleNode.ipa || ruleNode.label);

  // Hiển thị các từ vựng ví dụ
  detailExamplesList.innerHTML = "";
  practiceWordSelect.innerHTML = "";

  ruleNode.examples.forEach((ex, idx) => {
    // Tạo ví dụ card
    const card = document.createElement("div");
    card.className = "example-card";
    card.innerHTML = `
      <div class="example-left">
        <span class="example-word">${ex.word}</span>
        <span class="example-phonetic">/${ex.ipa}/</span>
        <span class="example-meaning">${ex.meaning}</span>
      </div>
      <button class="speak-btn round-btn small-btn" title="Nghe từ này">🔊</button>
    `;

    // Nút nghe phát âm từ ví dụ
    card.querySelector(".speak-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      speakText(ex.word);
    });

    detailExamplesList.appendChild(card);

    // Thêm vào dropdown luyện tập ghi âm
    const opt = document.createElement("option");
    opt.value = ex.word;
    opt.textContent = `${ex.word} /${ex.ipa}/ - ${ex.meaning}`;
    practiceWordSelect.appendChild(opt);
  });

  // Reset ghi âm khi đổi âm
  resetRecordingState();
}

function closeDrawer() {
  drawer.classList.remove("open");
  drawerBackdrop.classList.remove("active");
  drawer.setAttribute("aria-hidden", "true");
}

document.getElementById("close-drawer").addEventListener("click", closeDrawer);
drawerBackdrop.addEventListener("click", closeDrawer);


// --- 4. TRÌNH PHÁT ÂM VÀ THU ÂM SO SÁNH (SPEECH ENGINE) ---

// Giọng đọc Text-to-Speech (TTS)
let englishVoice = null;
function loadVoices() {
  if (!('speechSynthesis' in window)) return;

  const voices = window.speechSynthesis.getVoices();
  // Ưu tiên chọn giọng đọc tiếng Anh chuẩn tự nhiên
  englishVoice = voices.find(v => v.lang.startsWith("en-US") && v.name.includes("Google")) ||
    voices.find(v => v.lang.startsWith("en")) ||
    voices[0];
}

if ('speechSynthesis' in window) {
  window.speechSynthesis.onvoiceschanged = loadVoices;
  loadVoices();
}

function speakText(text) {
  if (!('speechSynthesis' in window)) {
    alert("Trình duyệt của bạn không hỗ trợ tính năng phát thanh.");
    return;
  }

  // Tạm dừng phát thanh hiện tại nếu có
  window.speechSynthesis.cancel();

  // Loại bỏ các dấu ngoặc / khi đọc âm đơn lẻ
  const cleanText = text.replace(/\//g, "");

  const utterance = new SpeechSynthesisUtterance(cleanText);
  utterance.voice = englishVoice;
  utterance.lang = "en-US";
  utterance.rate = 0.85; // Đọc chậm một chút để dễ nghe vần
  window.speechSynthesis.speak(utterance);
}

// Logic Ghi âm Mic so sánh (MediaRecorder)
let mediaRecorder = null;
let audioChunks = [];
let recordedAudioUrl = null;

const recordBtn = document.getElementById("record-btn");
const recordBtnText = document.getElementById("record-btn-text");
const playRecordingBtn = document.getElementById("play-recording-btn");
const audioFeedbackMsg = document.getElementById("audio-feedback-msg");

recordBtn.addEventListener("mousedown", startRecording);
recordBtn.addEventListener("mouseup", stopRecording);
recordBtn.addEventListener("mouseleave", stopRecording);

// Hỗ trợ cảm ứng điện thoại di động
recordBtn.addEventListener("touchstart", (e) => {
  e.preventDefault();
  startRecording();
});
recordBtn.addEventListener("touchend", (e) => {
  e.preventDefault();
  stopRecording();
});

async function startRecording() {
  if (mediaRecorder && mediaRecorder.state === "recording") return;

  audioChunks = [];
  audioFeedbackMsg.textContent = "";
  audioFeedbackMsg.className = "audio-feedback";

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = () => {
      const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
      recordedAudioUrl = URL.createObjectURL(audioBlob);
      playRecordingBtn.disabled = false;

      audioFeedbackMsg.textContent = "Đã thu âm! Bấm nghe lại bên cạnh để so sánh.";
      audioFeedbackMsg.classList.add("success");
    };

    mediaRecorder.start();
    recordBtn.classList.add("recording");
    recordBtnText.textContent = "Đang thu âm...";
  } catch (err) {
    console.error("Lỗi truy cập micro:", err);
    audioFeedbackMsg.textContent = "Không tìm thấy Micro hoặc bạn đã từ chối quyền.";
    audioFeedbackMsg.classList.add("error");
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
    // Tắt các luồng mic để tiết kiệm pin/bảo mật
    mediaRecorder.stream.getTracks().forEach(track => track.stop());
    recordBtn.classList.remove("recording");
    recordBtnText.textContent = "Giữ để nói";
  }
}

playRecordingBtn.addEventListener("click", () => {
  if (!recordedAudioUrl) return;

  // Phát lại âm thu âm của học viên
  const audio = new Audio(recordedAudioUrl);
  audio.play();

  audioFeedbackMsg.textContent = "Đang phát lại giọng của bạn...";
  audioFeedbackMsg.className = "audio-feedback info";

  audio.onended = () => {
    audioFeedbackMsg.textContent = "Học viên có thể bấm nghe lại để so sánh.";
    audioFeedbackMsg.className = "audio-feedback success";

    // Đọc từ mẫu ngay sau đó để so sánh trực diện
    setTimeout(() => {
      const selectedWord = practiceWordSelect.value;
      if (selectedWord) speakText(selectedWord);
    }, 500);
  };
});

function resetRecordingState() {
  recordedAudioUrl = null;
  playRecordingBtn.disabled = true;
  audioFeedbackMsg.textContent = "";
  audioFeedbackMsg.className = "audio-feedback";
}


// --- 5. BÀI TẬP LUYỆN TẬP TRẮC NGHIỆM (QUIZ CONTROLLER) ---
let quizQuestions = [];
let currentQuestionIndex = 0;
let quizScore = 0;

function generateQuiz() {
  // Tạo danh sách câu hỏi ngẫu nhiên từ kho từ ví dụ
  const allLeafNodes = mapInstance.nodes.filter(n => n.level === 3 && n.ipa);
  const quizPool = [];

  allLeafNodes.forEach(ruleNode => {
    const parentNode = mapInstance.nodeMap.get(ruleNode.parent);
    if (!parentNode) return;

    ruleNode.examples.forEach(ex => {
      // Xác định ký tự gạch chân
      const letterPattern = parentNode.label; // e.g. "CH", "EA", "A"

      quizPool.push({
        word: ex.word,
        highlight: letterPattern,
        correctIpa: ruleNode.ipa,
        meaning: ex.meaning,
        desc: ruleNode.desc,
        rule: ruleNode.rule
      });
    });
  });

  // Trộn câu hỏi và lấy 10 câu
  shuffleArray(quizPool);
  quizQuestions = quizPool.slice(0, 10);

  currentQuestionIndex = 0;
  quizScore = 0;

  document.getElementById("quiz-score").textContent = quizScore;
  document.getElementById("quiz-total-num").textContent = quizQuestions.length;
  document.getElementById("quiz-stats-screen").hidden = true;
  document.querySelector(".quiz-card").hidden = false;

  showQuestion();
}

function showQuestion() {
  if (currentQuestionIndex >= quizQuestions.length) {
    showQuizStats();
    return;
  }

  const question = quizQuestions[currentQuestionIndex];
  document.getElementById("quiz-current-num").textContent = currentQuestionIndex + 1;
  document.getElementById("quiz-feedback-box").hidden = true;

  // Tạo hiển thị từ gạch chân
  const displayWord = question.word;
  // Tìm kiếm xem cụm từ nằm ở đâu
  const idx = displayWord.toLowerCase().indexOf(question.highlight.toLowerCase());

  if (idx !== -1) {
    document.getElementById("quiz-word-before").textContent = displayWord.substring(0, idx);
    document.getElementById("quiz-word-highlight").textContent = displayWord.substring(idx, idx + question.highlight.length);
    document.getElementById("quiz-word-after").textContent = displayWord.substring(idx + question.highlight.length);
  } else {
    document.getElementById("quiz-word-before").textContent = displayWord;
    document.getElementById("quiz-word-highlight").textContent = "";
    document.getElementById("quiz-word-after").textContent = "";
  }

  document.getElementById("quiz-word-meaning").textContent = `Nghĩa: ${question.meaning}`;

  // Nút nghe từ mẫu trong câu hỏi
  document.getElementById("quiz-listen-btn").onclick = () => speakText(question.word);

  // Tạo 4 phương án đáp án (1 đúng, 3 sai ngẫu nhiên)
  const allIpaList = [...new Set(mapInstance.nodes.filter(n => n.level === 3 && n.ipa).map(n => n.ipa))];
  const incorrectOptions = allIpaList.filter(ipa => ipa !== question.correctIpa);
  shuffleArray(incorrectOptions);

  const options = [
    question.correctIpa,
    incorrectOptions[0] || "/e/",
    incorrectOptions[1] || "/ɪ/",
    incorrectOptions[2] || "/ʌ/"
  ];
  shuffleArray(options);

  // Hiển thị nút lựa chọn
  const optionsGrid = document.getElementById("quiz-options-grid");
  optionsGrid.innerHTML = "";
  options.forEach(opt => {
    const btn = document.createElement("button");
    btn.className = "option-btn";
    btn.textContent = opt || "âm câm";
    btn.addEventListener("click", () => selectOption(btn, opt, question.correctIpa));
    optionsGrid.appendChild(btn);
  });
}

function selectOption(selectedBtn, selectedIpa, correctIpa) {
  // Khóa tất cả các nút bấm
  const buttons = document.querySelectorAll(".option-btn");
  buttons.forEach(btn => btn.disabled = true);

  const isCorrect = selectedIpa === correctIpa;
  const question = quizQuestions[currentQuestionIndex];

  if (isCorrect) {
    selectedBtn.classList.add("correct");
    quizScore += 10;
    document.getElementById("quiz-score").textContent = quizScore;

    document.getElementById("quiz-feedback-text").textContent = "Chính xác! 🎉";
    document.getElementById("quiz-feedback-text").className = "feedback-text correct";
  } else {
    selectedBtn.classList.add("wrong");
    // Tô sáng đáp án đúng
    buttons.forEach(btn => {
      if (btn.textContent === correctIpa) btn.classList.add("correct");
    });

    document.getElementById("quiz-feedback-text").textContent = "Chưa đúng rồi! ❌";
    document.getElementById("quiz-feedback-text").className = "feedback-text wrong";
  }

  // Đọc từ để học viên nhớ phát âm
  speakText(question.word);

  // Hiển thị giải thích quy tắc ráp vần
  document.getElementById("quiz-feedback-explanation").innerHTML = `
    Ký tự gạch chân <strong>${question.highlight}</strong> trong từ <strong>${question.word}</strong> phát âm là <strong>${correctIpa || 'âm câm'}</strong>.<br>
    <em>Quy tắc:</em> ${question.rule} (${question.desc})
  `;
  document.getElementById("quiz-feedback-box").hidden = false;
}

// Bấm chuyển câu hỏi tiếp theo
document.getElementById("next-question-btn").addEventListener("click", () => {
  currentQuestionIndex++;
  showQuestion();
});

function showQuizStats() {
  document.querySelector(".quiz-card").hidden = true;
  const statsScreen = document.getElementById("quiz-stats-screen");
  statsScreen.hidden = false;

  const correctCount = quizScore / 10;
  document.getElementById("final-score").textContent = correctCount;
  document.getElementById("final-total").textContent = quizQuestions.length;

  const emoji = document.querySelector(".quiz-result-emoji");
  if (correctCount >= 8) emoji.textContent = "🏆";
  else if (correctCount >= 5) emoji.textContent = "🥈";
  else emoji.textContent = "✏️";
}

document.getElementById("restart-quiz-btn").addEventListener("click", generateQuiz);

// --- 6. KHỞI TẠO BẢN ĐỒ VÀ ĐIỀU KHIỂN CHUNG ---
let mapInstance = null;

window.addEventListener("DOMContentLoaded", () => {
  // 1. Khởi tạo đối tượng Mindmap
  mapInstance = new SVGMindmap("mindmap-svg", ipaData);

  // Đếm các số liệu hiển thị trên sidebar
  const singleVowels = ipaData.children[0].children.length;
  const doubleVowels = ipaData.children[1].children.length;
  const digraphConsonants = ipaData.children[2].children.length;

  let totalRules = 0;
  let totalExamples = 0;

  const countMetrics = (node) => {
    if (node.type === "rule") {
      totalRules++;
      totalExamples += node.examples.length;
    }
    if (node.children) node.children.forEach(countMetrics);
  };
  countMetrics(ipaData);

  document.getElementById("stat-nodes").textContent = singleVowels + doubleVowels + digraphConsonants;
  document.getElementById("stat-rules").textContent = totalRules;
  document.getElementById("stat-examples").textContent = `${totalExamples}+`;

  // 2. Lắng nghe các sự kiện điều khiển Zoom/Collapse
  document.getElementById("zoom-in").addEventListener("click", () => mapInstance.zoomIn());
  document.getElementById("zoom-out").addEventListener("click", () => mapInstance.zoomOut());
  document.getElementById("zoom-reset").addEventListener("click", () => mapInstance.centerView());
  document.getElementById("collapse-all").addEventListener("click", () => mapInstance.collapseAll());
  document.getElementById("expand-all").addEventListener("click", () => mapInstance.expandAll());

  // 3. Sự kiện Tìm kiếm từ khóa
  const searchInput = document.getElementById("node-search");
  const clearSearchBtn = document.getElementById("clear-search");

  searchInput.addEventListener("input", (e) => {
    const val = e.target.value;
    clearSearchBtn.hidden = !val;
    mapInstance.searchNodes(val);
  });

  clearSearchBtn.addEventListener("click", () => {
    searchInput.value = "";
    clearSearchBtn.hidden = true;
    mapInstance.searchNodes("");
  });

  // 4. Lọc danh mục bằng Chips
  const filterChips = document.querySelectorAll(".filter-chip");
  filterChips.forEach(chip => {
    chip.addEventListener("click", () => {
      filterChips.forEach(c => c.classList.remove("active"));
      chip.classList.add("active");

      const filterValue = chip.dataset.filter;
      mapInstance.filterCategory(filterValue);
    });
  });

  // 5. Chuyển đổi giữa chế độ Bản đồ và Trắc nghiệm
  const tabMap = document.getElementById("tab-map");
  const tabQuiz = document.getElementById("tab-quiz");
  const mapViewPanel = document.getElementById("map-view");
  const quizViewPanel = document.getElementById("quiz-view");

  tabMap.addEventListener("click", () => {
    tabMap.classList.add("active");
    tabMap.setAttribute("aria-selected", "true");
    tabQuiz.classList.remove("active");
    tabQuiz.setAttribute("aria-selected", "false");

    mapViewPanel.classList.add("active");
    quizViewPanel.classList.remove("active");

    // Tự động căn chỉnh lại sơ đồ khi quay lại tab
    setTimeout(() => mapInstance.centerView(), 100);
  });

  tabQuiz.addEventListener("click", () => {
    tabQuiz.classList.add("active");
    tabQuiz.setAttribute("aria-selected", "true");
    tabMap.classList.remove("active");
    tabMap.setAttribute("aria-selected", "false");

    quizViewPanel.classList.add("active");
    mapViewPanel.classList.remove("active");
    closeDrawer();

    // Sinh câu hỏi và bắt đầu quiz mới
    generateQuiz();
  });

  // 6. Chuyển đổi giao diện Dark/Light mode
  const themeToggle = document.getElementById("theme-toggle");

  // Tự động load theme lưu trước đó nếu có
  if (localStorage.getItem("theme") === "dark") {
    document.body.classList.add("dark-mode");
  }

  themeToggle.addEventListener("click", () => {
    document.body.classList.toggle("dark-mode");
    if (document.body.classList.contains("dark-mode")) {
      localStorage.setItem("theme", "dark");
    } else {
      localStorage.setItem("theme", "light");
    }
    // Vẽ lại sơ đồ để cập nhật các màu stroke chữ
    mapInstance.render();
  });
});

// --- CÁC HÀM TIỆN ÍCH TRỢ GIÚP (HELPERS) ---
function shuffleArray(array) {
  for (let i = array.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [array[i], array[j]] = [array[j], array[i]];
  }
}
