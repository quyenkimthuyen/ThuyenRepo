insert into public.words (word, ipa, vn_pronunciation, meaning_vi, example_en, example_vi, topic, level) values
  ('school', '/skuːl/', 'skuul', 'trường học', 'I go to school every day.', 'Tôi đi học mỗi ngày.', 'school', 'beginner'),
  ('beautiful', '/ˈbjuːtəfəl/', 'biu-tờ-phồ', 'đẹp', 'The garden is beautiful.', 'Khu vườn rất đẹp.', 'daily', 'elementary'),
  ('language', '/ˈlæŋɡwɪdʒ/', 'leang-quịch', 'ngôn ngữ', 'English is a useful language.', 'Tiếng Anh là một ngôn ngữ hữu ích.', 'learning', 'intermediate'),
  ('enough', '/ɪˈnʌf/', 'i-nâf', 'đủ', 'We have enough time.', 'Chúng ta có đủ thời gian.', 'daily', 'elementary'),
  ('green', '/ɡriːn/', 'griin', 'màu xanh lá', 'The leaf is green.', 'Chiếc lá màu xanh.', 'colors', 'beginner'),
  ('station', '/ˈsteɪʃən/', 'stây-shần', 'nhà ga', 'The train stops at the station.', 'Tàu dừng ở nhà ga.', 'travel', 'intermediate')
on conflict (word) do update set
  ipa = excluded.ipa,
  vn_pronunciation = excluded.vn_pronunciation,
  meaning_vi = excluded.meaning_vi,
  example_en = excluded.example_en,
  example_vi = excluded.example_vi,
  topic = excluded.topic,
  level = excluded.level;

insert into public.ipa_sounds (symbol, vietnamese_hint, examples, level) values
  ('/iː/', 'ii kéo dài', '[{"word":"see","hint":"sii"},{"word":"green","hint":"griin"},{"word":"eat","hint":"iit"}]', 'beginner'),
  ('/ɪ/', 'i ngắn, bật nhanh', '[{"word":"sit","hint":"sit"},{"word":"fish","hint":"fish"}]', 'beginner'),
  ('/æ/', 'ea mở miệng rộng', '[{"word":"cat","hint":"keat"},{"word":"language","hint":"leang-quịch"}]', 'beginner'),
  ('/uː/', 'uu kéo dài', '[{"word":"school","hint":"skuul"},{"word":"blue","hint":"bluu"}]', 'elementary'),
  ('/ə/', 'ơ nhẹ, không nhấn', '[{"word":"beautiful","hint":"biu-tờ-phồ"},{"word":"station","hint":"stây-shần"}]', 'elementary'),
  ('/ʃ/', 'sh như suỵt', '[{"word":"she","hint":"shii"},{"word":"station","hint":"stây-shần"}]', 'intermediate')
on conflict (symbol) do update set
  vietnamese_hint = excluded.vietnamese_hint,
  examples = excluded.examples,
  level = excluded.level;

insert into public.pronunciation_rules (pattern, ipa, vietnamese_hint, explanation, examples) values
  ('tion', '/ʃən/', 'shần', 'Thường đứng cuối danh từ và phát âm là /ʃən/, không đọc từng chữ t-i-o-n.', array['nation','station','education']),
  ('sh', '/ʃ/', 'sh', 'Đẩy hơi nhẹ qua răng, giống âm suỵt.', array['she','fish','shop']),
  ('ch', '/tʃ/', 'ch', 'Âm bật nhanh, gần với ch nhưng cần rõ hơi cuối.', array['chair','teacher','children']),
  ('ph', '/f/', 'ph/f', 'Trong nhiều từ gốc Hy Lạp, ph đọc như /f/.', array['phone','photo','physics']),
  ('th', '/θ/ or /ð/', 'th/dh', 'Đặt đầu lưỡi giữa răng. Âm có thể vô thanh hoặc hữu thanh.', array['think','this','three']),
  ('ng', '/ŋ/', 'ng', 'Âm ng ở cuối hoặc giữa từ, không thêm gờ nếu từ kết thúc bằng /ŋ/.', array['sing','English','language']),
  ('magic e', 'varies', 'nguyên âm dài', 'Chữ e câm cuối từ thường làm nguyên âm trước đó đọc theo tên chữ cái.', array['make','bike','home']),
  ('silent letters', 'varies', 'không đọc chữ câm', 'Một số chữ xuất hiện trong chính tả nhưng không có âm IPA tương ứng.', array['knife','listen','school'])
on conflict (pattern) do update set
  ipa = excluded.ipa,
  vietnamese_hint = excluded.vietnamese_hint,
  explanation = excluded.explanation,
  examples = excluded.examples;
