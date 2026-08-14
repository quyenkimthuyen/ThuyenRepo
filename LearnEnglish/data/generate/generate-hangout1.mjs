import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const CREATED_AT = 1779703568473;

const rawData = {
  "hangout1-welcome": [
    { word: "one", ipa_us: "/wʌn/", meaning_vi: "số 1", example: "I have one red apple.", image_keyword: "number one count child" },
    { word: "two", ipa_us: "/tuː/", meaning_vi: "số 2", example: "She has two blue pens.", image_keyword: "number two blue pens" },
    { word: "three", ipa_us: "/θriː/", meaning_vi: "số 3", example: "There are three cats on the mat.", image_keyword: "three cats mat" },
    { word: "four", ipa_us: "/fɔːr/", meaning_vi: "số 4", example: "I see four yellow birds.", image_keyword: "four yellow birds" },
    { word: "five", ipa_us: "/faɪv/", meaning_vi: "số 5", example: "He bought five crayons today.", image_keyword: "five crayons colors" },
    { word: "six", ipa_us: "/sɪks/", meaning_vi: "số 6", example: "We need six chairs for the class.", image_keyword: "six wooden chairs" },
    { word: "seven", ipa_us: "/ˈsev.ən/", meaning_vi: "số 7", example: "A week has seven days.", image_keyword: "seven days calendar" },
    { word: "eight", ipa_us: "/eɪt/", meaning_vi: "số 8", example: "She drew eight stars in her notebook.", image_keyword: "eight stars drawing" },
    { word: "nine", ipa_us: "/naɪn/", meaning_vi: "số 9", example: "My brother is nine years old.", image_keyword: "nine birthday cake" },
    { word: "ten", ipa_us: "/ten/", meaning_vi: "số 10", example: "I can count to ten in English.", image_keyword: "ten fingers counting" },
    { word: "red", ipa_us: "/red/", meaning_vi: "màu đỏ", example: "She wears a red hat.", image_keyword: "red hat clothing" },
    { word: "blue", ipa_us: "/bluː/", meaning_vi: "màu xanh dương", example: "The sky is bright blue today.", image_keyword: "blue sky sunny" },
    { word: "green", ipa_us: "/ɡriːn/", meaning_vi: "màu xanh lá cây", example: "The grass is green in spring.", image_keyword: "green grass field" },
    { word: "yellow", ipa_us: "/ˈjel.oʊ/", meaning_vi: "màu vàng", example: "The sun is big and yellow.", image_keyword: "yellow bright sun" },
    { word: "pink", ipa_us: "/pɪŋk/", meaning_vi: "màu hồng", example: "She has a pink eraser in her bag.", image_keyword: "pink eraser school" },
    { word: "orange", ipa_us: "/ˈɔːr.ɪndʒ/", meaning_vi: "màu cam", example: "He picked an orange marker.", image_keyword: "orange marker color" },
    { word: "purple", ipa_us: "/ˈpɝː.pəl/", meaning_vi: "màu tím", example: "I like my purple backpack.", image_keyword: "purple backpack school" },
    { word: "black", ipa_us: "/blæk/", meaning_vi: "màu đen", example: "The little cat is black.", image_keyword: "black cat pet" },
    { word: "white", ipa_us: "/waɪt/", meaning_vi: "màu trắng", example: "I have a white paper sheet.", image_keyword: "white paper paper" },
    { word: "brown", ipa_us: "/braʊn/", meaning_vi: "màu nâu", example: "The bear is big and brown.", image_keyword: "brown teddy bear" }
  ],
  "hangout1-unit1-school-things": [
    { word: "backpack", ipa_us: "/ˈbæk.pæk/", meaning_vi: "ba lô", example: "I put my books in my backpack.", image_keyword: "school backpack bag" },
    { word: "pencil", ipa_us: "/ˈpen.səl/", meaning_vi: "bút chì", example: "She writes her name with a pencil.", image_keyword: "yellow writing pencil" },
    { word: "pen", ipa_us: "/pen/", meaning_vi: "bút mực", example: "He uses a blue pen to write.", image_keyword: "blue ink pen" },
    { word: "eraser", ipa_us: "/ɪˈreɪ.sɚ/", meaning_vi: "cục tẩy", example: "I erased the mistake with my eraser.", image_keyword: "rubber eraser school" },
    { word: "lunchbox", ipa_us: "/ˈlʌntʃ.bɑːks/", meaning_vi: "hộp cơm trưa", example: "My mom packed fruit in my lunchbox.", image_keyword: "kids school lunchbox" },
    { word: "textbook", ipa_us: "/ˈtekst.bʊk/", meaning_vi: "sách giáo khoa", example: "Open your English textbook to page five.", image_keyword: "english textbook open" },
    { word: "crayon", ipa_us: "/ˈkreɪ.ɑːn/", meaning_vi: "bút màu sáp", example: "Color the picture with a red crayon.", image_keyword: "wax crayon coloring" },
    { word: "pencil case", ipa_us: "/ˈpen.səl keɪs/", meaning_vi: "hộp bút", example: "My pencils are inside my pencil case.", image_keyword: "zipper pencil case" },
    { word: "pencil sharpener", ipa_us: "/ˈpen.səl ˈʃɑːr.pən.ɚ/", meaning_vi: "gọt bút chì", example: "Use the pencil sharpener to sharpen your pencil.", image_keyword: "small pencil sharpener" },
    { word: "glue stick", ipa_us: "/ˈɡluː stɪk/", meaning_vi: "hồ dán dạng thỏi", example: "Apply the glue stick to paste the picture.", image_keyword: "paper glue stick" },
    { word: "ruler", ipa_us: "/ˈruː.lɚ/", meaning_vi: "thước kẻ", example: "Measure the line with a ruler.", image_keyword: "plastic measuring ruler" },
    { word: "paintbrush", ipa_us: "/ˈpeɪnt.brʌʃ/", meaning_vi: "cọ vẽ", example: "She dipped her paintbrush into blue paint.", image_keyword: "art watercolor paintbrush" },
    { word: "marker", ipa_us: "/ˈmɑːr.kɚ/", meaning_vi: "bút dạ", example: "Draw a big circle using a black marker.", image_keyword: "drawing felt marker" },
    { word: "notebook", ipa_us: "/ˈnoʊt.bʊk/", meaning_vi: "quyển vở", example: "Write the new words in your notebook.", image_keyword: "spiral lined notebook" },
    { word: "tape", ipa_us: "/teɪp/", meaning_vi: "băng dính", example: "Use tape to stick the poster on the wall.", image_keyword: "clear adhesive tape" },
    { word: "stapler", ipa_us: "/ˈsteɪ.plɚ/", meaning_vi: "cái dập ghim", example: "The teacher stapled the papers with a stapler.", image_keyword: "office paper stapler" }
  ],
  "hangout1-unit2-my-toys": [
    { word: "elephant", ipa_us: "/ˈel.ə.fənt/", meaning_vi: "con voi (đồ chơi)", example: "He plays with a soft toy elephant.", image_keyword: "plush toy elephant" },
    { word: "cards", ipa_us: "/kɑːrdz/", meaning_vi: "thẻ bài / bộ bài", example: "They are playing matching games with cards.", image_keyword: "playing cards game" },
    { word: "jump rope", ipa_us: "/ˈdʒʌmp roʊp/", meaning_vi: "dây nhảy", example: "She skips quickly with her new jump rope.", image_keyword: "fitness jump rope" },
    { word: "video game", ipa_us: "/ˈvɪd.i.oʊ ɡeɪm/", meaning_vi: "trò chơi điện tử", example: "He likes playing a fun video game.", image_keyword: "arcade video game" },
    { word: "doll", ipa_us: "/dɑːl/", meaning_vi: "búp bê", example: "The little girl has a pretty doll.", image_keyword: "cute toy doll" },
    { word: "puzzle", ipa_us: "/ˈpʌz.əl/", meaning_vi: "trò chơi xếp hình", example: "We completed the picture puzzle together.", image_keyword: "jigsaw puzzle pieces" },
    { word: "blocks", ipa_us: "/blɑːks/", meaning_vi: "khối đồ chơi / xếp hình", example: "He built a tall tower with wooden blocks.", image_keyword: "wooden building blocks" },
    { word: "airplane", ipa_us: "/ˈer.pleɪn/", meaning_vi: "máy bay đồ chơi", example: "The red toy airplane zooms through the room.", image_keyword: "toy model airplane" },
    { word: "soccer ball", ipa_us: "/ˈsɑː.kɚ bɑːl/", meaning_vi: "quả bóng đá", example: "He kicked the soccer ball into the goal.", image_keyword: "black white soccer ball" },
    { word: "baseball glove", ipa_us: "/ˈbeɪs.bɑːl ɡlʌv/", meaning_vi: "găng tay bóng chày", example: "Put on your baseball glove to catch the ball.", image_keyword: "leather baseball glove" },
    { word: "board game", ipa_us: "/ˈbɔːrd ɡeɪm/", meaning_vi: "trò chơi cờ", example: "Our family plays a fun board game.", image_keyword: "tabletop board game" },
    { word: "rollerblades", ipa_us: "/ˈroʊ.lɚ.bleɪdz/", meaning_vi: "giày trượt patin", example: "She rides fast on her new rollerblades.", image_keyword: "inline rollerblades skates" },
    { word: "bike", ipa_us: "/baɪk/", meaning_vi: "xe đạp", example: "I ride my bike to the park.", image_keyword: "kids bicycle bike" },
    { word: "skateboard", ipa_us: "/ˈskeɪt.bɔːrd/", meaning_vi: "ván trượt", example: "He loves practicing tricks on his skateboard.", image_keyword: "wooden skateboard wheels" },
    { word: "kite", ipa_us: "/kaɪt/", meaning_vi: "con diều", example: "The colorful kite flies high in the wind.", image_keyword: "flying colorful kite" },
    { word: "hula hoop", ipa_us: "/ˈhuː.lə huːp/", meaning_vi: "vòng lắc hula", example: "She can spin the hula hoop around her waist.", image_keyword: "plastic hula hoop" }
  ],
  "hangout1-unit3-my-classroom": [
    { word: "desk", ipa_us: "/desk/", meaning_vi: "bàn học", example: "Sit at your desk and open your notebook.", image_keyword: "school student desk" },
    { word: "chair", ipa_us: "/tʃer/", meaning_vi: "cái ghế", example: "Pull up a chair to join the reading circle.", image_keyword: "wooden classroom chair" },
    { word: "bookcase", ipa_us: "/ˈbʊk.keɪs/", meaning_vi: "tủ sách", example: "The storybooks are stacked neatly on the bookcase.", image_keyword: "wooden bookcase shelves" },
    { word: "cupboard", ipa_us: "/ˈkʌb.ɚd/", meaning_vi: "tủ đựng đồ", example: "We keep our art paper inside the cupboard.", image_keyword: "storage cabinet cupboard" },
    { word: "computer", ipa_us: "/kəmˈpjuː.t̬ɚ/", meaning_vi: "máy tính", example: "We watch learning videos on the computer.", image_keyword: "desktop computer monitor" },
    { word: "whiteboard", ipa_us: "/ˈwaɪt.bɔːrd/", meaning_vi: "bảng trắng", example: "The teacher writes today's date on the whiteboard.", image_keyword: "classroom dry whiteboard" },
    { word: "easel", ipa_us: "/ˈiː.zəl/", meaning_vi: "giá vẽ", example: "The painting paper is clipped onto the easel.", image_keyword: "artist painting easel" },
    { word: "poster", ipa_us: "/ˈpoʊ.stɚ/", meaning_vi: "tấm phích / áp phích", example: "There is a map poster on the classroom wall.", image_keyword: "educational wall poster" },
    { word: "drawing", ipa_us: "/ˈdrɑː.ɪŋ/", meaning_vi: "bức vẽ", example: "Her drawing shows a cheerful sunny morning.", image_keyword: "child colorful drawing" },
    { word: "calendar", ipa_us: "/ˈkæl.ən.dɚ/", meaning_vi: "lịch", example: "Check the calendar to see what day it is today.", image_keyword: "wall month calendar" },
    { word: "wastebasket", ipa_us: "/ˈweɪstˌbæs.kət/", meaning_vi: "thùng rác nhỏ", example: "Throw paper scraps into the wastebasket.", image_keyword: "office trash wastebasket" },
    { word: "mat", ipa_us: "/mæt/", meaning_vi: "thảm trải sàn", example: "The kids sit on the mat during story hour.", image_keyword: "colorful floor mat" },
    { word: "shelf", ipa_us: "/ʃelf/", meaning_vi: "giá / kệ", example: "Place your painted bowl on the shelf.", image_keyword: "single wall shelf" },
    { word: "clock", ipa_us: "/klɑːk/", meaning_vi: "đồng hồ treo tường", example: "The clock on the wall ticks loudly.", image_keyword: "round wall clock" },
    { word: "drawer", ipa_us: "/drɔːr/", meaning_vi: "ngăn kéo", example: "Open the wooden drawer to store your crayons.", image_keyword: "desk open drawer" },
    { word: "map", ipa_us: "/mæp/", meaning_vi: "bản đồ", example: "We located our country on the world map.", image_keyword: "geography world map" }
  ],
  "hangout1-unit4-family-and-friends": [
    { word: "mother", ipa_us: "/ˈmʌð.ɚ/", meaning_vi: "mẹ", example: "My mother cooks delicious food for us.", image_keyword: "mother mom smiling" },
    { word: "father", ipa_us: "/ˈfɑː.ðɚ/", meaning_vi: "bố", example: "My father reads me a bedtime story.", image_keyword: "father dad reading" },
    { word: "sister", ipa_us: "/ˈsɪs.tɚ/", meaning_vi: "chị / em gái", example: "My sister plays with her doll in the room.", image_keyword: "young sister smiling" },
    { word: "brother", ipa_us: "/ˈbrʌð.ɚ/", meaning_vi: "anh / em trai", example: "My brother plays soccer with his schoolmates.", image_keyword: "young brother boy" },
    { word: "parents", ipa_us: "/ˈper.ənts/", meaning_vi: "bố mẹ", example: "My parents love taking us to the beach.", image_keyword: "happy parents couple" },
    { word: "children", ipa_us: "/ˈtʃɪl.drən/", meaning_vi: "trẻ em", example: "The children laugh merrily in the park.", image_keyword: "happy playing children" },
    { word: "family", ipa_us: "/ˈfæm.əl.i/", meaning_vi: "gia đình", example: "I love spending weekends with my family.", image_keyword: "happy family group" },
    { word: "friend", ipa_us: "/frend/", meaning_vi: "bạn bè", example: "Mai is my helpful friend at school.", image_keyword: "best friends hug" },
    { word: "neighbor", ipa_us: "/ˈneɪ.bɚ/", meaning_vi: "hàng xóm", example: "Our neighbor greeted us with a cheerful wave.", image_keyword: "friendly neighbor wave" },
    { word: "grandmother", ipa_us: "/ˈɡrænˌmʌð.ɚ/", meaning_vi: "bà", example: "My grandmother knitted a warm sweater.", image_keyword: "kind grandmother grandma" },
    { word: "grandfather", ipa_us: "/ˈɡrænˌfɑː.ðɚ/", meaning_vi: "ông", example: "My grandfather tends to his flower garden.", image_keyword: "kind grandfather grandpa" },
    { word: "uncle", ipa_us: "/ˈʌŋ.kəl/", meaning_vi: "chú / bác / cậu", example: "My uncle bought me a nice puzzle.", image_keyword: "friendly uncle smiling" },
    { word: "aunt", ipa_us: "/ænt/", meaning_vi: "cô / dì / thím", example: "My aunt bakes tasty fruit pies.", image_keyword: "kind aunt smiling" },
    { word: "grandparents", ipa_us: "/ˈɡrænˌper.ənts/", meaning_vi: "ông bà", example: "We visit our grandparents every summer.", image_keyword: "loving grandparents elderly" },
    { word: "teacher", ipa_us: "/ˈtiː.tʃɚ/", meaning_vi: "giáo viên", example: "Our teacher guides us patiently.", image_keyword: "school teacher classroom" },
    { word: "cousin", ipa_us: "/ˈkʌz.ən/", meaning_vi: "anh chị em họ", example: "My cousin and I played board games.", image_keyword: "young cousins playing" }
  ],
  "hangout1-unit5-actions-and-animals": [
    { word: "drink", ipa_us: "/drɪŋk/", meaning_vi: "uống", example: "Drink fresh water after running outside.", image_keyword: "child drinking water" },
    { word: "eat", ipa_us: "/iːt/", meaning_vi: "ăn", example: "Rabbits eat crunchy orange carrots.", image_keyword: "eating healthy food" },
    { word: "run", ipa_us: "/rʌn/", meaning_vi: "chạy", example: "Dogs like to run fast across the field.", image_keyword: "running kids park" },
    { word: "walk", ipa_us: "/wɑːk/", meaning_vi: "đi bộ", example: "We walk together to the library.", image_keyword: "walking sidewalk street" },
    { word: "swim", ipa_us: "/swɪm/", meaning_vi: "bơi", example: "Fish swim gracefully in the cool pond.", image_keyword: "swimming pool fish" },
    { word: "fly", ipa_us: "/flaɪ/", meaning_vi: "bay", example: "Birds fly high up in the blue sky.", image_keyword: "flying bird sky" },
    { word: "jump", ipa_us: "/dʒʌmp/", meaning_vi: "nhảy", example: "Frogs can jump across small rocks.", image_keyword: "jumping high joy" },
    { word: "sleep", ipa_us: "/sliːp/", meaning_vi: "ngủ", example: "Kittens sleep softly on the carpet.", image_keyword: "sleeping cute kitten" },
    { word: "cow", ipa_us: "/kaʊ/", meaning_vi: "con bò sữa", example: "The spotted cow gives fresh milk.", image_keyword: "farm dairy cow" },
    { word: "horse", ipa_us: "/hɔːrs/", meaning_vi: "con ngựa", example: "The brown horse runs swiftly.", image_keyword: "galloping brown horse" },
    { word: "sheep", ipa_us: "/ʃiːp/", meaning_vi: "con cừu", example: "The sheep has warm white fleece.", image_keyword: "fluffy white sheep" },
    { word: "rabbit", ipa_us: "/ˈræb.ɪt/", meaning_vi: "con thỏ", example: "The small rabbit twitches its nose.", image_keyword: "white fluffy rabbit" },
    { word: "mouse", ipa_us: "/maʊs/", meaning_vi: "con chuột", example: "A quiet mouse peeked behind the door.", image_keyword: "little brown mouse" },
    { word: "bird", ipa_us: "/bɝːd/", meaning_vi: "con chim", example: "The blue bird perches on the tree branch.", image_keyword: "singing blue bird" },
    { word: "fish", ipa_us: "/fɪʃ/", meaning_vi: "con cá", example: "The little fish blows tiny bubbles.", image_keyword: "colorful tropical fish" },
    { word: "snake", ipa_us: "/sneɪk/", meaning_vi: "con rắn", example: "The long snake hides among green leaves.", image_keyword: "green garden snake" }
  ],
  "hangout1-unit6-feelings": [
    { word: "happy", ipa_us: "/ˈhæp.i/", meaning_vi: "vui vẻ", example: "We feel happy when we sing together.", image_keyword: "happy smiling child" },
    { word: "sad", ipa_us: "/sæd/", meaning_vi: "buồn", example: "He was sad when his balloon popped.", image_keyword: "sad disappointed boy" },
    { word: "angry", ipa_us: "/ˈæŋ.ɡri/", meaning_vi: "tức giận", example: "Take a deep breath when you feel angry.", image_keyword: "angry upset face" },
    { word: "tired", ipa_us: "/ˈtaɪɚd/", meaning_vi: "mệt mỏi", example: "She went to bed early because she was tired.", image_keyword: "sleepy tired kid" },
    { word: "hot", ipa_us: "/hɑːt/", meaning_vi: "nóng", example: "The summer sun makes us feel hot.", image_keyword: "hot sunny weather" },
    { word: "cold", ipa_us: "/koʊld/", meaning_vi: "lạnh", example: "Put on a jacket when you are cold.", image_keyword: "cold winter snow" },
    { word: "hungry", ipa_us: "/ˈhʌŋ.ɡri/", meaning_vi: "đói", example: "I am hungry for a healthy sandwich.", image_keyword: "hungry tummy food" },
    { word: "thirsty", ipa_us: "/ˈθɝː.sti/", meaning_vi: "khát nước", example: "He is thirsty and wants orange juice.", image_keyword: "thirsty drink glass" },
    { word: "excited", ipa_us: "/ɪkˈsaɪ.t̬ɪd/", meaning_vi: "hào hứng", example: "The children are excited about the zoo visit.", image_keyword: "excited cheering kids" },
    { word: "bored", ipa_us: "/bɔːrd/", meaning_vi: "chán nản", example: "She played music when she felt bored.", image_keyword: "bored dull expression" },
    { word: "relaxed", ipa_us: "/rɪˈlækst/", meaning_vi: "thư thái", example: "Reading a gentle story makes him feel relaxed.", image_keyword: "relaxed peaceful child" },
    { word: "upset", ipa_us: "/ʌpˈset/", meaning_vi: "thất vọng / buồn phiền", example: "She was upset about dropping her ice cream.", image_keyword: "upset crying girl" },
    { word: "worried", ipa_us: "/ˈwɝː.id/", meaning_vi: "lo lắng", example: "He was worried about his lost keys.", image_keyword: "worried anxious face" },
    { word: "surprised", ipa_us: "/sɚˈpraɪzd/", meaning_vi: "ngạc nhiên", example: "She was surprised by the cute puppy.", image_keyword: "surprised open mouth" },
    { word: "sick", ipa_us: "/sɪk/", meaning_vi: "ốm / bệnh", example: "Drink warm tea when you are sick.", image_keyword: "sick fever bed" },
    { word: "scared", ipa_us: "/skerd/", meaning_vi: "sợ hãi", example: "The dark shadows made him feel scared.", image_keyword: "scared fearful eyes" }
  ],
  "hangout1-unit7-daily-activities": [
    { word: "eat breakfast", ipa_us: "/iːt ˈbrek.fəst/", meaning_vi: "ăn sáng", example: "I eat breakfast before heading to school.", image_keyword: "family eating breakfast" },
    { word: "exercise", ipa_us: "/ˈek.sɚ.saɪz/", meaning_vi: "tập thể dục", example: "They exercise every morning in the yard.", image_keyword: "morning workout exercise" },
    { word: "watch TV", ipa_us: "/wɑːtʃ ˌtiːˈviː/", meaning_vi: "xem tivi", example: "We watch TV cartoons on Saturday.", image_keyword: "kids watching television" },
    { word: "listen to music", ipa_us: "/ˈlɪs.ən tuː ˈmjuː.zɪk/", meaning_vi: "nghe nhạc", example: "She likes to listen to music while painting.", image_keyword: "headphones listening music" },
    { word: "read", ipa_us: "/riːd/", meaning_vi: "đọc sách", example: "I read short stories in my room.", image_keyword: "child reading book" },
    { word: "use the computer", ipa_us: "/juːz ðə kəmˈpjuː.t̬ɚ/", meaning_vi: "sử dụng máy tính", example: "He uses the computer to practice English.", image_keyword: "student at computer" },
    { word: "study", ipa_us: "/ˈstʌd.i/", meaning_vi: "học bài", example: "They study together in the library.", image_keyword: "students studying desk" },
    { word: "play soccer", ipa_us: "/pleɪ ˈsɑː.kɚ/", meaning_vi: "chơi bóng đá", example: "Boys and girls play soccer after class.", image_keyword: "children playing soccer" },
    { word: "bedroom", ipa_us: "/ˈbed.ruːm/", meaning_vi: "phòng ngủ", example: "His bedroom has a bright yellow desk.", image_keyword: "cozy kids bedroom" },
    { word: "living room", ipa_us: "/ˈlɪv.ɪŋ ruːm/", meaning_vi: "phòng khách", example: "We rest on the sofa in the living room.", image_keyword: "modern home living room" },
    { word: "dining room", ipa_us: "/ˈdaɪ.nɪŋ ruːm/", meaning_vi: "phòng ăn", example: "The family gathers in the dining room.", image_keyword: "home dining room table" },
    { word: "kitchen", ipa_us: "/ˈkɪtʃ.ən/", meaning_vi: "phòng bếp", example: "Fresh cookies are baking in the kitchen.", image_keyword: "clean home kitchen" },
    { word: "backyard", ipa_us: "/ˌbækˈjɑːrd/", meaning_vi: "sân sau", example: "They play tag in the grassy backyard.", image_keyword: "green grass backyard" },
    { word: "garage", ipa_us: "/ɡəˈrɑːʒ/", meaning_vi: "nhà để xe", example: "Dad parked his bicycle in the garage.", image_keyword: "home car garage" },
    { word: "bathroom", ipa_us: "/ˈbæθ.ruːm/", meaning_vi: "phòng tắm", example: "Brush your teeth in the bathroom.", image_keyword: "clean white bathroom" },
    { word: "hall", ipa_us: "/hɑːl/", meaning_vi: "hành lang", example: "Leave your coat in the entrance hall.", image_keyword: "house entrance hall" }
  ],
  "hangout1-unit8-my-face-and-body": [
    { word: "ear", ipa_us: "/ɪr/", meaning_vi: "tai", example: "Listen carefully with your ears.", image_keyword: "human ear hearing" },
    { word: "eye", ipa_us: "/aɪ/", meaning_vi: "mắt", example: "Close your eyes and make a wish.", image_keyword: "human brown eye" },
    { word: "nose", ipa_us: "/noʊz/", meaning_vi: "mũi", example: "I can smell flowers with my nose.", image_keyword: "human nose smelling" },
    { word: "mouth", ipa_us: "/maʊθ/", meaning_vi: "miệng", example: "Smile brightly with your mouth.", image_keyword: "smiling mouth teeth" },
    { word: "hair", ipa_us: "/her/", meaning_vi: "tóc", example: "Combing your hair keeps it neat.", image_keyword: "long clean hair" },
    { word: "tooth", ipa_us: "/tuːθ/", meaning_vi: "răng", example: "Keep every tooth clean and healthy.", image_keyword: "single white tooth" },
    { word: "head", ipa_us: "/hed/", meaning_vi: "đầu", example: "Put a yellow cap on your head.", image_keyword: "child head smile" },
    { word: "face", ipa_us: "/feɪs/", meaning_vi: "khuôn mặt", example: "A warm smile brightens your face.", image_keyword: "happy human face" },
    { word: "arm", ipa_us: "/ɑːrm/", meaning_vi: "cánh tay", example: "Stretch your arm up high.", image_keyword: "raised human arm" },
    { word: "leg", ipa_us: "/leɡ/", meaning_vi: "chân", example: "Hop forward on your right leg.", image_keyword: "walking human leg" },
    { word: "hand", ipa_us: "/hænd/", meaning_vi: "bàn tay", example: "Hold your mom's hand while crossing.", image_keyword: "open human hand" },
    { word: "foot", ipa_us: "/fʊt/", meaning_vi: "bàn chân", example: "Wiggle your toes on your left foot.", image_keyword: "bare human foot" },
    { word: "curly hair", ipa_us: "/ˈkɝː.li her/", meaning_vi: "tóc xoăn", example: "She has bouncy black curly hair.", image_keyword: "girl curly hair" },
    { word: "straight hair", ipa_us: "/streɪt her/", meaning_vi: "tóc thẳng", example: "Her straight hair shines in the sunlight.", image_keyword: "girl straight hair" },
    { word: "short hair", ipa_us: "/ʃɔːrt her/", meaning_vi: "tóc ngắn", example: "He prefers having short hair in summer.", image_keyword: "boy short hair" },
    { word: "long hair", ipa_us: "/lɑːŋ her/", meaning_vi: "tóc dài", example: "She tied her long hair into a ponytail.", image_keyword: "girl long hair ponytail" }
  ],
  "hangout1-unit9-peoples-jobs": [
    { word: "actor", ipa_us: "/ˈæk.tɚ/", meaning_vi: "diễn viên", example: "The talented actor starred in a children's play.", image_keyword: "theater stage actor" },
    { word: "businessman", ipa_us: "/ˈbɪz.nɪs.mæn/", meaning_vi: "doanh nhân", example: "The businessman wears a dark suit.", image_keyword: "businessman suit briefcase" },
    { word: "cook", ipa_us: "/kʊk/", meaning_vi: "đầu bếp", example: "The cook makes tasty pasta.", image_keyword: "chef cook kitchen" },
    { word: "doctor", ipa_us: "/ˈdɑːk.tɚ/", meaning_vi: "bác sĩ", example: "The caring doctor examined the young patient.", image_keyword: "hospital medical doctor" },
    { word: "farmer", ipa_us: "/ˈfɑːr.mɚ/", meaning_vi: "nông dân", example: "The farmer drives a red tractor.", image_keyword: "farm agriculture farmer" },
    { word: "pilot", ipa_us: "/ˈpaɪ.lət/", meaning_vi: "phi công", example: "The skilled pilot flies large airplanes.", image_keyword: "airplane cockpit pilot" },
    { word: "police officer", ipa_us: "/pəˈliːs ˌɑː.fɪ.sɚ/", meaning_vi: "cảnh sát", example: "The police officer helped the lost boy.", image_keyword: "police officer uniform" },
    { word: "florist", ipa_us: "/ˈflɔːr.ɪst/", meaning_vi: "thợ cắm hoa / người bán hoa", example: "The florist arranged a bouquet of roses.", image_keyword: "flower shop florist" },
    { word: "airport", ipa_us: "/ˈer.pɔːrt/", meaning_vi: "sân bay", example: "We arrived at the airport early.", image_keyword: "airport terminal plane" },
    { word: "farm", ipa_us: "/fɑːrm/", meaning_vi: "trang trại", example: "We saw sheep grazing on the farm.", image_keyword: "rural countryside farm" },
    { word: "hospital", ipa_us: "/ˈhɑː.spɪ.t̬əl/", meaning_vi: "bệnh viện", example: "The city hospital is clean and modern.", image_keyword: "hospital building exterior" },
    { word: "office", ipa_us: "/ˈɑː.fɪs/", meaning_vi: "văn phòng", example: "He answers phone calls in his office.", image_keyword: "modern corporate office" },
    { word: "police station", ipa_us: "/pəˈliːs ˌsteɪ.ʃən/", meaning_vi: "đồn cảnh sát", example: "The police station is next to the post office.", image_keyword: "city police station" },
    { word: "restaurant", ipa_us: "/ˈres.tə.rɑːnt/", meaning_vi: "nhà hàng", example: "Our family ate at a cozy restaurant.", image_keyword: "dining room restaurant" }
  ]
};

function formatAudioUs(word) {
  const clean = word.toLowerCase().replace(/[^a-z0-9]/g, '');
  return `https://api.dictionaryapi.dev/media/pronunciations/en/${clean}-us.mp3`;
}

let counter = 1;
const result = {};

for (const [topicKey, items] of Object.entries(rawData)) {
  result[topicKey] = items.map((item) => {
    const id = `ho1-${String(counter++).padStart(4, '0')}`;
    return {
      id,
      word: item.word,
      ipa_us: item.ipa_us,
      meaning_vi: item.meaning_vi,
      example: item.example,
      status: "new",
      reviewLevel: 0,
      reviewCount: 0,
      createdAt: CREATED_AT,
      audio_us: formatAudioUs(item.word),
      topic: topicKey,
      cefr_level: "A1",
      difficulty: 1,
      image_keyword: item.image_keyword,
      audio_vi: `audio/vi/${id}.mp3`
    };
  });
}

const outputPath = path.join(__dirname, '..', 'all-topics-hangout1.json');
fs.writeFileSync(outputPath, JSON.stringify(result, null, 2), 'utf8');
console.log(`Generated ${counter - 1} words across ${Object.keys(result).length} topics to ${outputPath}`);

// Also merge Hang Out 1 topics into all-topics-toeic.json so that default TOEIC source also includes Hangout 1 topics!
const toeicPath = path.join(__dirname, '..', 'all-topics-toeic.json');
try {
  const toeicData = JSON.parse(fs.readFileSync(toeicPath, 'utf8'));
  for (const [topicKey, words] of Object.entries(result)) {
    toeicData[topicKey] = words;
  }
  fs.writeFileSync(toeicPath, JSON.stringify(toeicData, null, 2), 'utf8');
  console.log(`Successfully merged Hang Out 1 topics into ${toeicPath}`);
} catch (err) {
  console.error(`Failed to update toeic dataset: ${err.message}`);
}
