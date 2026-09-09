# -*- coding: utf-8 -*-
"""Generate 280 VanDungCao MCQs for high-school English sentence structures."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "questions"
WEB = ROOT / "web-html"
SOURCE = (
    "AI-generated luyện cấu trúc câu lớp 10-12 (collocation, cụm động từ, thành ngữ), "
    "cần giáo viên kiểm duyệt"
)

# Each item:
# s: structure, vi: Vietnamese gloss, kind: gap|mean
# prompt: sentence (use ______ for gaps; wrap the target in <u>...</u> for meaning)
# opts: 4 choices, ans: index of the key, form: canonical pattern, why: why the key is right
ITEMS: list[dict] = []


def add(s, vi, kind, prompt, opts, ans, form, why):
    assert len(opts) == 4, s
    assert 0 <= ans <= 3, s
    ITEMS.append(
        {
            "s": s,
            "vi": vi,
            "kind": kind,
            "prompt": prompt,
            "opts": opts,
            "ans": ans,
            "form": form,
            "why": why,
        }
    )


# --- 1-40 ---
add(
    "be committed to doing something",
    "cam kết, tận tụy làm gì",
    "gap",
    "Despite the modest salary, the young teachers remain committed ______ creating equal opportunities for rural students.",
    ["to", "for", "with", "in"],
    0,
    "be committed to + V-ing/N",
    "committed đi với giới từ to, sau to là V-ing hoặc danh từ.",
)
add(
    "come at the cost of something",
    "trả giá bằng cái gì",
    "gap",
    "Rapid urban expansion often comes ______ the cost of disappearing farmland and wetlands.",
    ["at", "with", "to", "on"],
    0,
    "come at the cost of + N",
    "Cụm cố định là come at the cost of, không dùng with/to/on.",
)
add(
    "deal a heavy blow",
    "giáng một đòn mạnh",
    "gap",
    "Prolonged drought has ______ a heavy blow to rice farmers in the Mekong Delta.",
    ["dealt", "given", "made", "put"],
    0,
    "deal a heavy blow (to sb/sth)",
    "Collocation chuẩn là deal a blow, không phải give/make/put a blow.",
)
add(
    "distinguish something from something",
    "phân biệt cái gì với cái gì",
    "gap",
    "Media literacy helps students distinguish reliable sources ______ sponsored content.",
    ["from", "with", "to", "of"],
    0,
    "distinguish A from B",
    "distinguish đi với from, không dùng with như confuse with.",
)
add(
    "gloss over",
    "phớt lờ; lờ đi",
    "gap",
    "The official statement glossed ______ several safety failures and only praised the outcome.",
    ["over", "on", "out", "away"],
    0,
    "gloss over + N",
    "gloss over nghĩa là lướt qua, che giấu phần bất lợi.",
)
add(
    "make all the difference",
    "tạo ra sự khác biệt lớn",
    "gap",
    "A mentor who checks in weekly can make ______ the difference to a first-year student.",
    ["all", "whole", "every", "total"],
    0,
    "make all the difference (to sb/sth)",
    "Thành ngữ cố định là make all the difference, không dùng whole/every.",
)
add(
    "play a pivotal role in something",
    "đóng vai trò then chốt trong cái gì",
    "gap",
    "Local volunteers played a pivotal role ______ restoring the flooded library.",
    ["in", "on", "at", "for"],
    0,
    "play a pivotal role in + N/V-ing",
    "play a role/part luôn đi với in.",
)
add(
    "take a back seat",
    "giữ vai trò thứ yếu",
    "mean",
    "When the specialists arrived, community leaders had to <u>take a back seat</u> in the rescue planning.",
    [
        "let others take the leading role",
        "sit at the rear of the vehicle",
        "refuse to participate at all",
        "demand a more important position",
    ],
    0,
    "take a back seat",
    "Nghĩa bóng: nhường vị trí quan trọng, không phải ngồi ghế sau.",
)
add(
    "take something with a pinch of salt",
    "không nên tin hoàn toàn",
    "mean",
    "Experienced readers take sensational exam rumours <u>with a pinch of salt</u>.",
    [
        "do not believe them completely",
        "memorise every detail immediately",
        "spread them to more classmates",
        "reject every piece of information",
    ],
    0,
    "take sth with a pinch of salt",
    "Thành ngữ nghĩa là đón nhận một cách dè dặt, không tin 100%.",
)
add(
    "go to great lengths to do something",
    "cố gắng hết sức để làm gì",
    "gap",
    "The organisers went to great lengths ______ that students with disabilities could sit the exam fairly.",
    ["to ensure", "ensuring", "for ensuring", "ensure"],
    0,
    "go to great lengths to V",
    "Sau go to great lengths dùng to-infinitive, không dùng V-ing.",
)
add(
    "tend to do something",
    "có xu hướng làm gì",
    "gap",
    "Under pressure, many candidates tend ______ the first option that looks familiar.",
    ["to choose", "choosing", "choose", "for choosing"],
    0,
    "tend to V",
    "tend to + V nguyên mẫu có to, không dùng V-ing.",
)
add(
    "at short notice",
    "trong thời gian ngắn, gấp",
    "gap",
    "A substitute invigilator had to be found ______ short notice after the teacher fell ill.",
    ["at", "in", "by", "with"],
    0,
    "at short notice",
    "Cụm cố định là at short notice (cũng gặp on short notice ở AmE, nhưng đáp án chuẩn đề VN là at).",
)
add(
    "immerse yourself in something",
    "đắm chìm, hòa mình vào",
    "gap",
    "To gain fluency, you should immerse yourself ______ authentic conversations rather than word lists alone.",
    ["in", "on", "into", "with"],
    0,
    "immerse yourself in + N",
    "immerse in (không dùng into/on).",
)
add(
    "when it comes to doing something",
    "khi nói đến việc gì",
    "gap",
    "When it comes ______ managing exam stress, sleep is more effective than last-minute cramming.",
    ["to", "with", "for", "about"],
    0,
    "when it comes to + N/V-ing",
    "to trong cụm này là giới từ nên theo sau là N hoặc V-ing.",
)
add(
    "bring about",
    "mang lại, gây ra",
    "gap",
    "Stricter plastic bans may bring ______ a measurable drop in ocean waste.",
    ["about", "up", "out", "over"],
    0,
    "bring about + N",
    "bring about = cause; bring up = nêu ra/nuôi; bring out = làm nổi bật.",
)
add(
    "cater to something",
    "phục vụ, đáp ứng nhu cầu",
    "gap",
    "The redesigned website caters ______ visually impaired users with high-contrast mode.",
    ["to", "with", "on", "about"],
    0,
    "cater to + N",
    "Cấu trúc trong danh mục là cater to; không dùng with/on/about.",
)
add(
    "desire to do something",
    "mong muốn làm gì đó",
    "gap",
    "Her desire ______ study marine biology grew after the coastal field trip.",
    ["to", "for", "of", "in"],
    0,
    "desire to V / desire for N",
    "Muốn dùng động từ thì desire to V; desire for đi với danh từ.",
)
add(
    "deter somebody from doing something",
    "ngăn cản ai làm gì đó",
    "gap",
    "High application fees should not deter talented students ______ applying for the scholarship.",
    ["from", "to", "of", "against"],
    0,
    "deter sb from V-ing",
    "deter/prevent/stop/discourage đều đi với from + V-ing.",
)
add(
    "get over",
    "vượt qua (bệnh, khó khăn, nỗi buồn)",
    "gap",
    "It took him an entire term to get ______ the disappointment of missing the gifted-school cutoff.",
    ["over", "off", "out", "across"],
    0,
    "get over + N",
    "get over = recover from; get off = xuống/xe; get out = ra ngoài.",
)
add(
    "get up",
    "thức dậy; đứng dậy",
    "gap",
    "Candidates who get ______ after midnight the night before a test rarely perform at their best.",
    ["up", "over", "out", "off"],
    0,
    "get up",
    "get up = thức dậy; ngữ cảnh giờ giấc trước kỳ thi chọn up.",
)
add(
    "immerse myself in something",
    "đắm mình, hòa mình vào",
    "gap",
    "During the exchange, I immersed myself ______ Japanese homestay routines to pick up natural expressions.",
    ["in", "on", "at", "into"],
    0,
    "immerse myself in + N",
    "Cùng cấu trúc immerse + đại từ phản thân + in.",
)
add(
    "inflict something on somebody",
    "gây ra, khiến ai phải chịu đựng",
    "gap",
    "The unexpected storm inflicted severe losses ______ small shrimp farms.",
    ["on", "to", "for", "at"],
    0,
    "inflict sth on sb/sth",
    "inflict đi với on, không dùng to như cause damage to.",
)
add(
    "raises concerns about",
    "dấy lên lo ngại về",
    "gap",
    "The new landfill raises concerns ______ groundwater contamination near the school.",
    ["about", "for", "on", "with"],
    0,
    "raise concerns about + N",
    "concerns đi với about khi nói lo ngại về vấn đề.",
)
add(
    "withdraw from something",
    "rút khỏi, rời khỏi",
    "gap",
    "The athlete had to withdraw ______ the final because of a stress fracture.",
    ["from", "of", "out", "off"],
    0,
    "withdraw from + N",
    "withdraw from a race/competition/agreement.",
)
add(
    "be stuck on",
    "bị kẹt, bị vướng vào",
    "gap",
    "The robotics team is stuck ______ one coding error that crashes the whole program.",
    ["on", "in", "at", "to"],
    0,
    "be stuck on + N",
    "be stuck on a problem = bị kẹt ở một chỗ; stuck in thường đi với traffic/place.",
)
add(
    "expect somebody to do something",
    "mong đợi ai đó làm gì",
    "gap",
    "Teachers should not expect 15-year-olds ______ handle adult workloads without guidance.",
    ["to", "for", "that", "in"],
    0,
    "expect sb to V",
    "expect + tân ngữ + to V, không dùng V-ing hay for.",
)
add(
    "meet up",
    "gặp nhau (theo kế hoạch)",
    "gap",
    "Let's meet ______ outside the exam hall at 6.30 so nobody gets lost.",
    ["up", "on", "in", "over"],
    0,
    "meet up (with sb)",
    "meet up = gặp theo hẹn; không thêm on/in sau meet trong nghĩa này.",
)
add(
    "bring somebody closer to something",
    "đưa ai đó gần hơn với cái gì",
    "gap",
    "Weekend volunteering brought her closer ______ a career in community health.",
    ["to", "with", "into", "for"],
    0,
    "bring sb closer to + N",
    "closer to + N; không dùng with.",
)
add(
    "make ends meet",
    "kiếm đủ sống",
    "mean",
    "Many student workers take night shifts just to <u>make ends meet</u>.",
    [
        "earn enough money for basic needs",
        "finish two tasks at the same time",
        "meet important people after work",
        "save a large amount for luxury goods",
    ],
    0,
    "make ends meet",
    "Thành ngữ = xoay xở đủ chi phí sinh hoạt, không liên quan 'gặp nhau'.",
)
add(
    "take the initiative to do something",
    "chủ động làm gì",
    "gap",
    "Instead of waiting to be told, Minh took the initiative ______ the lab after the experiment.",
    ["to tidy", "tidying", "for tidying", "tidy"],
    0,
    "take the initiative to V",
    "take the initiative to + V; có thể gặp in V-ing nhưng đáp án chuẩn theo danh mục là to V.",
)
add(
    "buckle up",
    "thắt dây an toàn",
    "gap",
    "All passengers are required to buckle ______ before the coach leaves the station.",
    ["up", "in", "on", "down"],
    0,
    "buckle up",
    "buckle up = thắt dây an toàn.",
)
add(
    "compel somebody to do something",
    "ép buộc, bắt buộc ai làm gì",
    "gap",
    "New evidence compelled the committee ______ the admissions policy.",
    ["to revise", "revising", "for revising", "revise"],
    0,
    "compel sb to V",
    "compel + sb + to V, giống force/oblige.",
)
add(
    "decline in something",
    "sự suy giảm về",
    "gap",
    "Researchers have recorded a sharp decline ______ teen reading for pleasure.",
    ["in", "of", "on", "at"],
    0,
    "a decline in + N",
    "decline in something; a decline of thường chỉ mức (a decline of 10%).",
)
add(
    "embark on",
    "bắt đầu, tiến hành",
    "gap",
    "After graduation she embarked ______ a long-term study of urban farming.",
    ["on", "in", "at", "to"],
    0,
    "embark on + N",
    "embark on a project/career/journey.",
)
add(
    "enable somebody to do something",
    "cho phép ai làm gì",
    "gap",
    "Need-based scholarships enable talented students ______ university without crushing debt.",
    ["to attend", "attending", "attend", "for attending"],
    0,
    "enable sb to V",
    "enable + sb + to V; khác với make sb V (không to).",
)
add(
    "glow up",
    "thay đổi tích cực về ngoại hình hoặc phong cách",
    "mean",
    "After a year of training and better sleep, he had a complete <u>glow up</u>.",
    [
        "a striking positive change in appearance and confidence",
        "a sudden rise in body temperature",
        "an expensive shopping spree",
        "a short period of fame online",
    ],
    0,
    "a glow-up / glow up",
    "Nghĩa slang học đường: lột xác theo hướng tích cực, không chỉ 'nổi tiếng'.",
)
add(
    "intend to do something",
    "có ý định làm gì",
    "gap",
    "The city does not intend ______ the historic market to build another mall.",
    ["to demolish", "demolishing", "demolish", "for demolishing"],
    0,
    "intend to V",
    "intend to V (intend + V-ing ít gặp hơn và không phải đáp án đề).",
)
add(
    "lose sight of something",
    "quên mất điều quan trọng",
    "gap",
    "In the race for rankings, some schools lose sight ______ students' mental health.",
    ["of", "from", "on", "about"],
    0,
    "lose sight of + N",
    "lose sight of = quên/mất phương hướng về điều quan trọng.",
)
add(
    "pressure on something",
    "áp lực lên cái gì",
    "gap",
    "Climate change is placing growing pressure ______ freshwater supplies.",
    ["on", "in", "at", "to"],
    0,
    "pressure on + N",
    "pressure on sb/sth; put/place pressure on.",
)
add(
    "align with",
    "phù hợp với, tương thích với",
    "gap",
    "School assessment should align ______ the national curriculum goals.",
    ["with", "to", "for", "on"],
    0,
    "align with + N",
    "align with = phù hợp/cùng hướng với.",
)

# --- 41-80 ---
add(
    "tie to",
    "gắn liền với",
    "gap",
    "His academic progress is closely tied ______ consistent sleep and revision habits.",
    ["to", "with", "on", "in"],
    0,
    "be tied to + N",
    "be tied to = gắn liền với; không dùng with trong cụm này.",
)
add(
    "play a key role",
    "đóng vai trò quan trọng",
    "gap",
    "Peer mentors play a key role ______ helping newcomers settle into boarding school.",
    ["in", "on", "at", "for"],
    0,
    "play a key role in",
    "Giống play a role in; tính từ key không đổi giới từ.",
)
add(
    "attempt to do something",
    "cố gắng làm gì",
    "gap",
    "Scientists are attempting ______ a cheaper dengue vaccine for the region.",
    ["to develop", "developing", "develop", "for developing"],
    0,
    "attempt to V",
    "attempt to V; attempt at + N/V-ing là cấu trúc khác.",
)
add(
    "be ingrained in something",
    "ăn sâu, hằn sâu vào",
    "gap",
    "Respect for teachers is deeply ingrained ______ many Vietnamese families.",
    ["in", "on", "at", "into"],
    0,
    "be ingrained in + N",
    "ingrained in a culture/habit/belief.",
)
add(
    "force somebody to do something",
    "buộc ai làm gì",
    "gap",
    "Rising rents forced several graduates ______ the inner city.",
    ["to leave", "leaving", "leave", "for leaving"],
    0,
    "force sb to V",
    "force + sb + to V, không dùng V-ing.",
)
add(
    "a sense of belonging",
    "cảm giác thuộc về",
    "gap",
    "After-school clubs help shy newcomers develop a sense of ______.",
    ["belonging", "belong", "belonged", "belongs"],
    0,
    "a sense of belonging",
    "Cụm danh từ cố định: a sense of belonging.",
)
add(
    "lose touch with somebody/something",
    "mất liên lạc, mất kết nối",
    "gap",
    "After moving abroad, she gradually lost touch ______ her primary-school friends.",
    ["with", "to", "from", "of"],
    0,
    "lose touch with + sb/sth",
    "lose touch with, không dùng from/of.",
)
add(
    "devote something to doing something",
    "cống hiến cái gì để làm gì",
    "gap",
    "He devoted every Sunday ______ tutoring children in the shelter.",
    ["to", "for", "in", "at"],
    0,
    "devote sth to + N/V-ing",
    "to là giới từ → V-ing (tutoring), không dùng for.",
)
add(
    "absorbed in something",
    "mải mê, say mê cái gì",
    "gap",
    "She was so absorbed ______ the mock test that she did not hear the fire drill.",
    ["in", "on", "at", "with"],
    0,
    "be absorbed in + N",
    "absorbed in; interested in khác interested, nhưng absorbed không đi với on.",
)
add(
    "be dependent on something",
    "phụ thuộc vào cái gì",
    "gap",
    "The island community is still heavily dependent ______ imported fuel.",
    ["on", "of", "from", "with"],
    0,
    "be dependent on + N",
    "dependent on = depend on; independent đi với of.",
)
add(
    "be responsible for doing something",
    "chịu trách nhiệm làm gì",
    "gap",
    "The class monitor is responsible ______ collecting the answer sheets.",
    ["for", "to", "of", "with"],
    0,
    "be responsible for + N/V-ing",
    "responsible for + V-ing; responsible to + người quản lý.",
)
add(
    "disagree with something",
    "không đồng ý với cái gì",
    "gap",
    "Many parents disagree ______ the proposal to shorten summer break.",
    ["with", "to", "about", "for"],
    0,
    "disagree with + sb/sth",
    "disagree with a person/idea; không dùng to.",
)
add(
    "fall for something",
    "bị lừa, mắc bẫy cái gì",
    "mean",
    "Several users <u>fell for</u> the fake scholarship email and shared their passwords.",
    [
        "were tricked by",
        "fell in love with",
        "applied successfully for",
        "reported immediately to",
    ],
    0,
    "fall for + N",
    "Trong ngữ cảnh lừa đảo, fall for = mắc bẫy, không phải 'phải lòng'.",
)
add(
    "figure out something",
    "tìm ra, hiểu ra cái gì",
    "gap",
    "It took the team two hours to figure ______ why the robot kept spinning.",
    ["out", "up", "off", "over"],
    0,
    "figure out + N/wh-clause",
    "figure out = understand/solve; figure up không dùng với nghĩa này.",
)
add(
    "let somebody down",
    "làm ai đó thất vọng",
    "gap",
    "He promised to bring the model, so missing the fair would let the whole group ______.",
    ["down", "off", "out", "away"],
    0,
    "let sb down",
    "let sb down = disappoint; let off = tha; let out = cho ra.",
)
add(
    "play a role in doing something",
    "đóng vai trò trong việc làm gì",
    "gap",
    "Parent workshops play a role ______ reducing dropout rates in mountainous areas.",
    ["in", "on", "at", "for"],
    0,
    "play a role in + V-ing",
    "in + V-ing (reducing), không dùng on/for.",
)
add(
    "pretend to do something",
    "giả vờ làm gì",
    "gap",
    "He pretended ______ the question although he had not revised that unit.",
    ["to understand", "understanding", "understand", "for understanding"],
    0,
    "pretend to V",
    "pretend to V, không dùng V-ing.",
)
add(
    "reflect on something",
    "suy ngẫm về cái gì",
    "gap",
    "After the mock exam, students were asked to reflect ______ their time-management mistakes.",
    ["on", "in", "to", "with"],
    0,
    "reflect on + N",
    "reflect on = think carefully about.",
)
add(
    "rely on something",
    "dựa vào, phụ thuộc vào",
    "gap",
    "Coastal towns cannot rely ______ last-minute sandbags to stop storm surges.",
    ["on", "in", "to", "at"],
    0,
    "rely on + N/V-ing",
    "rely on = depend on.",
)
add(
    "sign up for something",
    "đăng ký tham gia",
    "gap",
    "More than 200 students have signed up ______ the weekend coding camp.",
    ["for", "to", "in", "on"],
    0,
    "sign up for + N",
    "sign up for a course/club; sign up to + V là cấu trúc khác.",
)
add(
    "take a gap year",
    "nghỉ một năm",
    "gap",
    "She decided to take a ______ year to volunteer before starting university.",
    ["gap", "break", "rest", "leave"],
    0,
    "take a gap year",
    "Collocation chuẩn: take a gap year.",
)
add(
    "turn to somebody/something",
    "tìm đến ai/cái gì để được giúp",
    "gap",
    "When the experiment failed, the group turned ______ their physics teacher for advice.",
    ["to", "on", "in", "at"],
    0,
    "turn to sb/sth",
    "turn to = seek help; turn on = bật/tấn công.",
)
add(
    "worried about something",
    "lo lắng về cái gì",
    "gap",
    "Parents are increasingly worried ______ the amount of time teenagers spend online.",
    ["about", "for", "to", "on"],
    0,
    "worried about + N/V-ing",
    "worried about; worried for ít gặp và không phải đáp án chuẩn.",
)
add(
    "account for",
    "chiếm (tỷ lệ); giải thích cho",
    "gap",
    "Motorbikes still account ______ most private trips in the city during rush hour.",
    ["for", "to", "of", "in"],
    0,
    "account for + N/%",
    "account for = chiếm tỷ lệ hoặc explain.",
)
add(
    "appeal to somebody",
    "thu hút ai đó",
    "gap",
    "Project-based tasks appeal ______ students who dislike purely theoretical lessons.",
    ["to", "for", "with", "on"],
    0,
    "appeal to + sb",
    "appeal to sb = attract; appeal for = kêu gọi sự giúp đỡ.",
)
add(
    "apply for",
    "nộp đơn xin",
    "gap",
    "You must apply ______ the boarding scholarship before 15 May.",
    ["for", "to", "at", "on"],
    0,
    "apply for + N (job/scholarship)",
    "apply for a job/scholarship; apply to an institution.",
)
add(
    "at the cost of",
    "phải trả giá bằng",
    "gap",
    "He achieved a perfect score at the cost ______ his sleep and weekend hobbies.",
    ["of", "for", "to", "with"],
    0,
    "at the cost of + N",
    "at the cost of = at the expense of.",
)
add(
    "be concerned about",
    "lo ngại về, quan tâm đến",
    "gap",
    "Health experts are concerned ______ the rise of energy-drink use among teens.",
    ["about", "to", "on", "with"],
    0,
    "be concerned about + N",
    "concerned about a problem; concerned with = liên quan đến (nghĩa khác).",
)
add(
    "be linked to something",
    "có liên quan đến",
    "gap",
    "Poor ventilation has been linked ______ higher rates of classroom fatigue.",
    ["to", "for", "on", "at"],
    0,
    "be linked to + N",
    "be linked to/with; trong danh mục là linked to.",
)
add(
    "be to blame for something",
    "phải chịu trách nhiệm cho việc gì",
    "gap",
    "Outdated wiring was to blame ______ the laboratory fire, not the students.",
    ["for", "to", "on", "of"],
    0,
    "be to blame for + N/V-ing",
    "be to blame for; blame sb for sth.",
)
add(
    "come along",
    "đến, xuất hiện, đồng hành",
    "gap",
    "A much cheaper solar panel came ______ just as the school planned its rooftop project.",
    ["along", "across", "over", "out"],
    0,
    "come along",
    "come along = appear/progress; come across = bắt gặp.",
)
add(
    "concern about something",
    "lo lắng, lo ngại về điều gì",
    "gap",
    "There is growing concern ______ deepfake videos circulating before exams.",
    ["about", "to", "on", "with"],
    0,
    "concern about + N",
    "Danh từ concern + about a problem.",
)
add(
    "demand for something",
    "nhu cầu đối với cái gì",
    "gap",
    "Demand ______ affordable rental housing near universities has surged.",
    ["for", "of", "to", "on"],
    0,
    "demand for + N",
    "demand for sth; in demand = được cần nhiều.",
)
add(
    "different from",
    "khác với",
    "gap",
    "The 2026 paper is substantially different ______ last year's in the reading section.",
    ["from", "with", "of", "on"],
    0,
    "different from + N",
    "different from là dạng chuẩn trong đề VN.",
)
add(
    "eager to do something",
    "háo hức làm điều gì",
    "gap",
    "The juniors were eager ______ the visiting engineers about green roofs.",
    ["to question", "questioning", "question", "for questioning"],
    0,
    "eager to V",
    "eager to V; eager for + N.",
)
add(
    "give up",
    "từ bỏ",
    "gap",
    "After three failed trials, the team refused to give ______ redesigning the filter.",
    ["up", "out", "in", "off"],
    0,
    "give up + N/V-ing",
    "give up = quit; give in = yield; give out = phát/hết.",
)
add(
    "interact with",
    "tương tác với",
    "gap",
    "Young children learn faster when they interact ______ native speakers in real tasks.",
    ["with", "to", "for", "on"],
    0,
    "interact with + sb",
    "interact with, không dùng to.",
)
add(
    "live off the land",
    "sống dựa vào thiên nhiên, tự cung tự cấp",
    "mean",
    "The documentary follows a family that still <u>lives off the land</u> in the highlands.",
    [
        "survives by farming and gathering rather than buying food",
        "travels across the country without a map",
        "depends entirely on government subsidies",
        "refuses to work in any season",
    ],
    0,
    "live off the land",
    "Nghĩa là tự cung tự cấp từ đất đai/thiên nhiên.",
)
add(
    "made from",
    "được làm từ",
    "gap",
    "This classroom insulation is made ______ recycled plastic bottles.",
    ["from", "of", "with", "by"],
    0,
    "be made from + N",
    "made from khi nguyên liệu biến đổi (chai nhựa → tấm cách nhiệt); made of khi còn nhận ra chất liệu.",
)
add(
    "open to somebody",
    "mở cửa, sẵn sàng cho ai tiếp cận",
    "gap",
    "The evening science lab is open ______ all students, not only the gifted class.",
    ["to", "for", "with", "at"],
    0,
    "be open to + sb",
    "be open to someone = cho phép họ tham gia/tiếp cận.",
)
add(
    "protect somebody from something",
    "bảo vệ ai khỏi điều gì",
    "gap",
    "Shade trees protect cyclists ______ extreme heat on the way to school.",
    ["from", "of", "for", "off"],
    0,
    "protect sb from sth",
    "protect from/against; trong danh mục là from.",
)
add(
    "put something at risk",
    "đặt cái gì vào tình thế rủi ro",
    "gap",
    "Skipping breakfast before a three-hour paper can put concentration ______ risk.",
    ["at", "in", "on", "to"],
    0,
    "put sth at risk",
    "at risk; in danger là cụm khác.",
)
add(
    "roll up",
    "cuộn lại, kéo lên (tay áo)",
    "gap",
    "The mechanic rolled ______ his sleeves and crawled under the school bus.",
    ["up", "out", "over", "on"],
    0,
    "roll up (one's sleeves)",
    "roll up one's sleeves = xắn tay áo (cũng hàm ý sẵn sàng làm việc).",
)

# --- 81-120 ---
add(
    "sacrifice something for something",
    "hy sinh cái gì cho cái gì",
    "gap",
    "She sacrificed her weekend rest ______ extra practice with the debate team.",
    ["for", "to", "with", "on"],
    0,
    "sacrifice A for B",
    "sacrifice sth for sth; không dùng to trong nghĩa này.",
)
add(
    "struggle to do something",
    "chật vật để làm điều gì",
    "gap",
    "Many first-generation students struggle ______ academic English in year 10.",
    ["to master", "mastering", "master", "for mastering"],
    0,
    "struggle to V",
    "struggle to V = khó khăn để làm được; struggle with + N.",
)
add(
    "take over",
    "tiếp quản, chiếm quyền kiểm soát",
    "gap",
    "A younger engineer will take ______ the lab when the supervisor retires.",
    ["over", "on", "up", "off"],
    0,
    "take over (+ N)",
    "take over = tiếp quản; take on = nhận việc; take up = bắt đầu hobby.",
)
add(
    "trade something for something",
    "đổi cái gì lấy cái gì",
    "gap",
    "He traded his old tablet ______ a second-hand laptop suitable for coding.",
    ["for", "with", "to", "by"],
    0,
    "trade A for B",
    "trade A for B = đổi A lấy B.",
)
add(
    "with a view to doing something",
    "với mục đích làm gì",
    "gap",
    "The school planted a garden with a view ______ students' environmental awareness.",
    ["to raising", "to raise", "of raising", "for raise"],
    0,
    "with a view to + V-ing",
    "to là giới từ → V-ing, đây là bẫy vận dụng cao rất phổ biến.",
)
add(
    "in case of",
    "trong trường hợp",
    "gap",
    "In case ______ a power cut, the listening file has been copied onto two USBs.",
    ["of", "that", "if", "for"],
    0,
    "in case of + N",
    "in case of + danh từ; in case + mệnh đề là cấu trúc khác.",
)
add(
    "stay on track",
    "giữ đúng hướng, không sao nhãng",
    "gap",
    "A simple weekly checklist helps revision stay ______ track during Tet.",
    ["on", "in", "at", "to"],
    0,
    "stay on track",
    "on track = đúng lộ trình.",
)
add(
    "put off",
    "hoãn lại, trì hoãn",
    "gap",
    "Do not put ______ writing the outline until the night before the paper.",
    ["off", "out", "away", "down"],
    0,
    "put off + N/V-ing",
    "put off = postpone; put out = dập; put away = cất.",
)
add(
    "bring out something",
    "làm nổi bật; xuất bản",
    "gap",
    "Group discussion often brings ______ ideas that silent students would not write alone.",
    ["out", "up", "about", "in"],
    0,
    "bring out + N",
    "bring out = make sth appear/clear; bring up = nêu vấn đề.",
)
add(
    "clear out something",
    "dọn sạch, vứt bỏ đồ không cần",
    "gap",
    "Before moving dorms, they cleared ______ three bags of unused worksheets.",
    ["out", "up", "off", "away"],
    0,
    "clear out + N",
    "clear out = dọn hết; clear up = dọn/giải thích/trời quang.",
)
add(
    "keep out",
    "ngăn không cho vào",
    "gap",
    "A simple sign is not enough to keep stray dogs ______ of the canteen.",
    ["out", "off", "away", "down"],
    0,
    "keep out (of)",
    "keep out = prevent from entering.",
)
add(
    "take part in something",
    "tham gia vào việc gì",
    "gap",
    "Every grade 10 class must take part ______ the disaster-drill on Friday.",
    ["in", "on", "at", "to"],
    0,
    "take part in + N",
    "take part in = participate in.",
)
add(
    "exposure to something",
    "sự tiếp xúc với cái gì",
    "gap",
    "Long exposure ______ loud traffic can damage teenagers' hearing.",
    ["to", "with", "of", "for"],
    0,
    "exposure to + N",
    "exposure to a substance/experience.",
)
add(
    "fill out",
    "điền vào (mẫu đơn)",
    "gap",
    "Please fill ______ the medical form before the sports day.",
    ["out", "up", "in on", "over"],
    0,
    "fill out + a form",
    "fill out/in a form; fill up = làm đầy.",
)
add(
    "filter out",
    "lọc ra, loại bỏ",
    "gap",
    "A good search habit helps you filter ______ clickbait before citing a source.",
    ["out", "up", "off", "down"],
    0,
    "filter out + N",
    "filter out = loại bỏ thứ không muốn.",
)
add(
    "make use of",
    "tận dụng, sử dụng",
    "gap",
    "Candidates should make use ______ the extra five minutes to transfer answers.",
    ["of", "for", "with", "to"],
    0,
    "make use of + N",
    "make use of = use effectively.",
)
add(
    "mean to do something",
    "có ý định làm gì",
    "gap",
    "I meant ______ you the rubric, but the file was too large to send.",
    ["to send", "sending", "send", "for sending"],
    0,
    "mean to V",
    "mean to V = intend; mean V-ing = signify (nghĩa khác).",
)
add(
    "push out",
    "đẩy ra, loại bỏ",
    "gap",
    "Rising rents are pushing ______ long-term residents near the new metro line.",
    ["out", "off", "over", "away"],
    0,
    "push out + sb/sth",
    "push out = force to leave/displace.",
)
add(
    "run off",
    "bỏ chạy, chạy trốn",
    "gap",
    "The thief ran ______ with a tablet when the library door was left open.",
    ["off", "out", "over", "down"],
    0,
    "run off",
    "run off = flee; run out = hết; run over = cán qua.",
)
add(
    "show off",
    "khoe khoang, phô trương",
    "gap",
    "He kept showing ______ his new phone instead of helping with the experiment.",
    ["off", "up", "out", "in"],
    0,
    "show off",
    "show off = boast; show up = xuất hiện.",
)
add(
    "suffer from",
    "chịu đựng, mắc phải",
    "gap",
    "A growing number of teens suffer ______ sleep deprivation during exam season.",
    ["from", "of", "by", "with"],
    0,
    "suffer from + N",
    "suffer from an illness/problem.",
)
add(
    "take precautions",
    "thực hiện các biện pháp phòng ngừa",
    "gap",
    "Laboratories must take ______ against chemical spills during practice sessions.",
    ["precautions", "prevention", "prediction", "protection"],
    0,
    "take precautions (against)",
    "Collocation: take precautions, không take prevention.",
)
add(
    "try doing something",
    "thử làm việc gì",
    "gap",
    "If the formula is confusing, try ______ the diagram before rereading the paragraph.",
    ["drawing", "to drawing", "draw", "drew"],
    0,
    "try V-ing",
    "try V-ing = thử phương pháp; try to V = cố gắng (có thể thất bại).",
)
add(
    "catch up on",
    "làm bù, bắt kịp",
    "gap",
    "She stayed up to catch up ______ the biology notes she missed while ill.",
    ["on", "with", "to", "for"],
    0,
    "catch up on + N",
    "catch up on work/news; catch up with sb = đuổi kịp ai.",
)
add(
    "enjoy doing something",
    "thích làm gì",
    "gap",
    "Most of the class enjoys ______ field data more than memorising definitions.",
    ["collecting", "to collect", "collect", "collected"],
    0,
    "enjoy + V-ing",
    "enjoy/avoid/mind/finish + V-ing, không + to V.",
)
add(
    "fit in",
    "hòa nhập",
    "gap",
    "New boarders often need a term before they truly fit ______ with older students.",
    ["in", "on", "out", "up"],
    0,
    "fit in (with)",
    "fit in = belong socially; fit out = trang bị.",
)
add(
    "forget to do something",
    "quên làm gì",
    "gap",
    "Don't forget ______ your ID card, or you will not be allowed into the exam room.",
    ["to bring", "bringing", "bring", "brought"],
    0,
    "forget to V",
    "forget to V = quên việc cần làm; forget V-ing = quên kỷ niệm đã xảy ra.",
)
add(
    "lead to something",
    "dẫn đến điều gì",
    "gap",
    "Chronic sleep loss can lead ______ poorer memory on test day.",
    ["to", "into", "for", "on"],
    0,
    "lead to + N/V-ing",
    "lead to a result; không dùng into trong nghĩa 'gây ra'.",
)
add(
    "make up for",
    "bù đắp",
    "gap",
    "Extra tutoring cannot fully make up ______ months of skipped homework.",
    ["for", "to", "with", "on"],
    0,
    "make up for + N",
    "make up for = compensate for.",
)
add(
    "manage to do something",
    "xoay xở để làm được",
    "gap",
    "Against the odds, they managed ______ the robot working ten minutes before the demo.",
    ["to get", "getting", "get", "in getting"],
    0,
    "manage to V",
    "manage to V = succeed in doing; succeed in + V-ing là cấu trúc khác.",
)
add(
    "promise to do something",
    "hứa làm gì",
    "gap",
    "The principal promised ______ the damaged roof before the rainy season.",
    ["to repair", "repairing", "repair", "for repairing"],
    0,
    "promise to V",
    "promise to V, không dùng V-ing.",
)
add(
    "set off",
    "khởi hành",
    "gap",
    "The field-trip buses will set ______ at 5.15 a.m. from the main gate.",
    ["off", "out of", "up", "down"],
    0,
    "set off",
    "set off = start a journey; set up = thành lập; set down = đặt xuống.",
)
add(
    "be curious about something",
    "tò mò về cái gì",
    "gap",
    "Good scientists stay curious ______ results that do not match the hypothesis.",
    ["about", "for", "to", "on"],
    0,
    "be curious about + N",
    "curious about; curious to V = muốn làm để biết.",
)
add(
    "do laundry",
    "giặt giũ",
    "gap",
    "Boarding students are expected to ______ their own laundry every Sunday.",
    ["do", "make", "take", "have"],
    0,
    "do laundry",
    "do laundry/housework/homework; không dùng make laundry.",
)
add(
    "grow up",
    "lớn lên, trưởng thành",
    "gap",
    "She grew ______ in a floating village and later studied water engineering.",
    ["up", "out", "on", "over"],
    0,
    "grow up",
    "grow up = become an adult; grow out of = lớn quá cỡ.",
)
add(
    "in advance",
    "trước",
    "gap",
    "Permission slips must be submitted two days ______ advance.",
    ["in", "on", "at", "for"],
    0,
    "in advance",
    "in advance = beforehand.",
)
add(
    "keep up",
    "tiếp tục, duy trì",
    "gap",
    "It is hard to keep ______ regular exercise when revision timetables get dense.",
    ["up", "on", "out", "off"],
    0,
    "keep up (+ N)",
    "keep up = maintain; keep on = continue doing.",
)
add(
    "make a budget",
    "lập ngân sách",
    "gap",
    "Before buying a used laptop, ______ a budget that includes charger and repairs.",
    ["make", "do", "take", "set a"],
    0,
    "make a budget",
    "make a budget/plan/decision; do a budget không phải collocation chuẩn.",
)
add(
    "make for",
    "tạo nên điều gì; đi về phía",
    "gap",
    "Clear rubrics make ______ fairer marking across different teachers.",
    ["for", "up", "out", "over"],
    0,
    "make for + N",
    "make for = lead to/help create; make up = bịa/trang điểm/chiếm.",
)
add(
    "make up",
    "trang điểm; bịa chuyện; chiếm; làm hòa",
    "gap",
    "Do not make ______ data in the lab report; examiners can spot invented numbers.",
    ["up", "out", "over", "off"],
    0,
    "make up + N",
    "Trong ngữ cảnh này make up = invent/fabricate.",
)
add(
    "pick up",
    "nhận, học được, đón",
    "gap",
    "Living with a host family helped her pick ______ natural intonation quickly.",
    ["up", "out", "on", "off"],
    0,
    "pick up + N",
    "pick up a language/skill = học được tự nhiên; pick out = chọn.",
)
add(
    "put out",
    "dập lửa",
    "gap",
    "Students were trained to put ______ a small fire with a blanket, not water.",
    ["out", "off", "down", "away"],
    0,
    "put out + a fire",
    "put out a fire; put off = hoãn; put down = đặt xuống/viết.",
)
add(
    "set aside",
    "gạt sang một bên, tiết kiệm",
    "gap",
    "She sets ______ 30 minutes each evening for vocabulary, even during busy weeks.",
    ["aside", "away", "off", "out"],
    0,
    "set aside + N",
    "set aside time/money = dành riêng.",
)
add(
    "stick to something",
    "tuân thủ, làm theo cái gì",
    "gap",
    "If you stick ______ the outline, the 200-word paragraph will stay on topic.",
    ["to", "on", "with", "at"],
    0,
    "stick to + N",
    "stick to a plan/rule; stick with cũng gặp nhưng đáp án theo danh mục là to.",
)
add(
    "take place",
    "diễn ra",
    "gap",
    "The oral exam will take ______ in Room 204, not in the main hall.",
    ["place", "part", "part in", "the place"],
    0,
    "take place",
    "take place = happen; take part = participate (cần in).",
)

# --- 121-160 ---
add(
    "a sense of community",
    "ý thức cộng đồng",
    "gap",
    "Shared cooking nights in the dorm built a strong sense of ______ among the boarders.",
    ["community", "common", "commune", "communication"],
    0,
    "a sense of community",
    "Cụm cố định: a sense of community.",
)
add(
    "advise somebody to do something",
    "khuyên ai đó làm gì",
    "gap",
    "Counsellors advised the final-year students ______ a realistic list of schools.",
    ["to prepare", "preparing", "prepare", "for preparing"],
    0,
    "advise sb to V",
    "advise sb to V; advise + V-ing khi không có tân ngữ người.",
)
add(
    "call for",
    "kêu gọi, yêu cầu",
    "gap",
    "The drought called ______ an immediate change in irrigation practice.",
    ["for", "on", "out", "off"],
    0,
    "call for + N",
    "call for = require/demand; call off = hủy; call on = kêu gọi ai.",
)
add(
    "gain real-world experience",
    "có được kinh nghiệm thực tế",
    "gap",
    "Internships help students gain real-world ______ before choosing a major.",
    ["experience", "experiment", "expertise only", "experiences of theory"],
    0,
    "gain real-world experience",
    "Collocation: gain experience, không gain experiment.",
)
add(
    "get along with",
    "hòa thuận với ai",
    "gap",
    "She gets along ______ teammates who disagree with her, which makes group work smoother.",
    ["with", "to", "for", "on"],
    0,
    "get along with + sb",
    "get along with = have a good relationship.",
)
add(
    "get through to somebody",
    "liên lạc được với ai; làm ai hiểu",
    "gap",
    "The hotline was busy, so it took an hour to get through ______ an operator.",
    ["to", "with", "for", "at"],
    0,
    "get through to + sb",
    "get through to = make contact / make sb understand.",
)
add(
    "make the most of something",
    "tận dụng tối đa cái gì",
    "gap",
    "Make the most ______ the 10-minute break to stretch; do not scroll endlessly.",
    ["of", "from", "with", "for"],
    0,
    "make the most of + N",
    "make the most of = use as well as possible.",
)
add(
    "miss out on something",
    "bỏ lỡ cái gì",
    "gap",
    "Students who skip the workshop will miss out ______ practical exam strategies.",
    ["on", "of", "from", "for"],
    0,
    "miss out on + N",
    "miss out on an opportunity.",
)
add(
    "reach out to",
    "liên lạc, tiếp cận để được hỗ trợ",
    "gap",
    "If the workload feels unmanageable, reach out ______ the school counsellor early.",
    ["to", "for", "with", "at"],
    0,
    "reach out to + sb",
    "reach out to sb = contact for help.",
)
add(
    "speak up against",
    "lên tiếng phản đối",
    "gap",
    "Several students spoke up ______ the unfair ranking that ignored improvement.",
    ["against", "for", "to", "on"],
    0,
    "speak up against + N",
    "speak up against = protest; speak up for = bảo vệ.",
)
add(
    "stand up for",
    "bảo vệ, đấu tranh cho",
    "gap",
    "A good friend will stand up ______ you when rumours spread online.",
    ["for", "to", "against", "with"],
    0,
    "stand up for + sb/sth",
    "stand up for = defend; stand up to = đối mặt với kẻ mạnh.",
)
add(
    "stay away from",
    "tránh xa",
    "gap",
    "Candidates are told to stay away ______ unofficial answer keys sold on social media.",
    ["from", "of", "off", "to"],
    0,
    "stay away from + N",
    "stay away from = avoid.",
)
add(
    "stock up on something",
    "dự trữ cái gì",
    "gap",
    "Before the storm, families stocked up ______ bottled water and rice.",
    ["on", "with", "for", "in"],
    0,
    "stock up on + N",
    "stock up on supplies.",
)
add(
    "be careful with somebody/something",
    "cẩn thận với ai/cái gì",
    "gap",
    "Be careful ______ the concentrated acid; even a drop can burn skin.",
    ["with", "to", "for", "on"],
    0,
    "be careful with + sb/sth",
    "careful with an object/person; careful about a situation.",
)
add(
    "be open to",
    "cởi mở, sẵn sàng với",
    "gap",
    "Effective leaders are open ______ feedback, even when it is uncomfortable.",
    ["to", "for", "with", "on"],
    0,
    "be open to + N/V-ing",
    "open to ideas/suggestions; khác 'open for business'.",
)
add(
    "be passionate about (doing) something",
    "đam mê (làm) điều gì",
    "gap",
    "She is passionate ______ restoring mangrove forests in her hometown.",
    ["about", "for", "in", "to"],
    0,
    "be passionate about + N/V-ing",
    "passionate about, không dùng for như eager for.",
)
add(
    "connect with somebody",
    "kết nối với ai",
    "gap",
    "Stories from alumni help current students connect ______ possible future careers.",
    ["with", "to", "for", "on"],
    0,
    "connect with + sb",
    "connect with people; connect A to B là nối vật lý/ý.",
)
add(
    "fancy doing something",
    "thích làm gì",
    "gap",
    "Do you fancy ______ the science fair this Saturday, or would you rather rest?",
    ["visiting", "to visit", "visit", "visited"],
    0,
    "fancy + V-ing",
    "fancy + V-ing (BrE) = feel like doing.",
)
add(
    "get on with",
    "có mối quan hệ tốt với ai",
    "gap",
    "He gets on ______ almost everyone in the orchestra, which keeps rehearsals calm.",
    ["with", "to", "for", "at"],
    0,
    "get on with + sb",
    "get on with = get along with (BrE).",
)
add(
    "give back to the community",
    "đóng góp lại cho cộng đồng",
    "gap",
    "Scholarship holders are encouraged to give back ______ the community through tutoring.",
    ["to", "for", "into", "on"],
    0,
    "give back to the community",
    "give back to = đóng góp lại.",
)
add(
    "look for",
    "tìm kiếm",
    "gap",
    "The committee is looking ______ volunteers who can speak both Vietnamese and Khmer.",
    ["for", "after", "up", "into"],
    0,
    "look for + N",
    "look for = search; look after = chăm sóc; look up = tra cứu.",
)
add(
    "put up with",
    "chịu đựng",
    "gap",
    "I will not put up ______ teasing that targets a classmate's accent.",
    ["with", "to", "for", "on"],
    0,
    "put up with + N",
    "put up with = tolerate; put up = dựng/treo/cho ở.",
)
add(
    "run wild",
    "trở nên mất kiểm soát",
    "mean",
    "Without adult guidance, rumours about the answer key <u>ran wild</u> in the group chat.",
    [
        "spread in an uncontrolled way",
        "were proven completely accurate",
        "were deleted by the admin at once",
        "helped students revise more calmly",
    ],
    0,
    "run wild",
    "run wild = out of control.",
)
add(
    "speak up for",
    "lên tiếng bảo vệ, ủng hộ",
    "gap",
    "Older students should speak up ______ younger ones who are being excluded.",
    ["for", "against", "to", "on"],
    0,
    "speak up for + sb",
    "speak up for = defend; khác speak up against.",
)
add(
    "take down",
    "gỡ xuống; xóa bỏ thông tin",
    "gap",
    "The school took ______ the misleading poster as soon as parents complained.",
    ["down", "off", "out", "away"],
    0,
    "take down + N",
    "take down a poster/post; take off = cởi/cất cánh.",
)
add(
    "take in",
    "hấp thụ; hiểu cái gì",
    "gap",
    "The reading passage was too dense to take ______ in one silent sitting.",
    ["in", "on", "up", "over"],
    0,
    "take in + N",
    "take in information = understand/absorb.",
)
add(
    "take off",
    "cất cánh; cởi; thành công",
    "gap",
    "The plane could not take ______ until the thunderstorm had passed.",
    ["off", "out", "up", "away"],
    0,
    "take off",
    "Ngữ cảnh sân bay: take off = cất cánh.",
)
add(
    "take on",
    "thuê tuyển; đảm nhận",
    "gap",
    "She was afraid to take ______ the role of team leader at first.",
    ["on", "up", "over", "in"],
    0,
    "take on + N",
    "take on a role/job; take over = tiếp quản toàn bộ.",
)
add(
    "take out",
    "lấy/mang cái gì ra",
    "gap",
    "Please take ______ your ID and place it on the desk before the paper begins.",
    ["out", "off", "up", "on"],
    0,
    "take out + N",
    "take out = remove from a bag/place.",
)
add(
    "take up",
    "bắt đầu theo đuổi (sở thích, thói quen)",
    "gap",
    "To manage stress, he took ______ swimming instead of scrolling at midnight.",
    ["up", "on", "in", "over"],
    0,
    "take up + N",
    "take up a hobby; take on a responsibility.",
)
add(
    "commitment to doing something",
    "cam kết làm điều gì",
    "gap",
    "The principal restated the school's commitment ______ reducing plastic waste.",
    ["to", "for", "with", "in"],
    0,
    "commitment to + N/V-ing",
    "commitment to, giống committed to.",
)
add(
    "cut down on",
    "cắt giảm",
    "gap",
    "Doctors advised him to cut down ______ sugary drinks before training.",
    ["on", "of", "from", "off"],
    0,
    "cut down on + N",
    "cut down on = reduce consumption.",
)
add(
    "drop in on",
    "ghé thăm",
    "gap",
    "Feel free to drop in ______ your homeroom teacher if the timetable is confusing.",
    ["on", "at", "to", "for"],
    0,
    "drop in on + sb",
    "drop in on someone = visit briefly.",
)
add(
    "face up to",
    "đối mặt với",
    "gap",
    "He finally faced up ______ the fact that he needed extra maths support.",
    ["to", "with", "against", "on"],
    0,
    "face up to + N",
    "face up to a problem/truth.",
)
add(
    "get into the habit of doing something",
    "tạo thói quen làm gì",
    "gap",
    "Get into the habit ______ reviewing errors on the same day, not a week later.",
    ["of", "to", "for", "in"],
    0,
    "get into the habit of + V-ing",
    "habit of + V-ing, không to V.",
)
add(
    "hesitate to do something",
    "do dự làm điều gì",
    "gap",
    "Do not hesitate ______ the invigilator if the question paper is incomplete.",
    ["to tell", "telling", "tell", "for telling"],
    0,
    "hesitate to V",
    "hesitate to V; don't hesitate to V là mẫu đề nghị.",
)
add(
    "interested in",
    "quan tâm, hứng thú với",
    "gap",
    "Students interested ______ marine conservation can join Sunday beach clean-ups.",
    ["in", "on", "to", "for"],
    0,
    "interested in + N/V-ing",
    "interested in; interesting là tính từ cho vật.",
)
add(
    "keep something in check",
    "giữ cái gì trong tầm kiểm soát",
    "gap",
    "Regular exercise helps keep exam anxiety in ______.",
    ["check", "control room", "charge", "chance"],
    0,
    "keep sth in check",
    "in check = under control.",
)
add(
    "look forward to",
    "mong đợi",
    "gap",
    "The class is looking forward to ______ the overnight field trip next month.",
    ["going on", "go on", "gone on", "to go on"],
    0,
    "look forward to + N/V-ing",
    "to là giới từ → V-ing (going on), không dùng to V (to go on).",
)
add(
    "make a difference",
    "tạo ra sự khác biệt",
    "gap",
    "Even a 20-minute peer-tutoring session can make a real ______ to a struggling classmate.",
    ["difference", "different", "differ", "differential"],
    0,
    "make a difference (to)",
    "make a difference, không make a different.",
)

# --- 161-200 ---
add(
    "raise awareness",
    "nâng cao nhận thức",
    "gap",
    "The poster campaign aims to raise ______ of mental-health support at school.",
    ["awareness", "awake", "warning", "attention span"],
    0,
    "raise awareness (of/about)",
    "raise awareness, không raise attention (phải pay attention).",
)
add(
    "switch off",
    "tắt",
    "gap",
    "Please switch ______ your phones before the listening file starts.",
    ["off", "out", "over", "away"],
    0,
    "switch off + N",
    "switch off a device; switch over = chuyển kênh/hệ thống.",
)
add(
    "turn off",
    "tắt",
    "gap",
    "Remember to turn ______ the Bunsen burner when you leave the lab.",
    ["off", "down", "out", "away"],
    0,
    "turn off + N",
    "turn off = stop a machine; turn down = vặn nhỏ/từ chối.",
)
add(
    "bring in",
    "đưa vào; thuê; giới thiệu luật/ý tưởng",
    "gap",
    "The city brought ______ a new rule limiting motorbike parking near school gates.",
    ["in", "up", "about", "off"],
    0,
    "bring in + N",
    "bring in a law/policy; bring about = gây ra kết quả.",
)
add(
    "bring off something",
    "thành công khi làm điều khó",
    "mean",
    "Against the clock, the robotics club <u>brought off</u> a working prototype before the fair.",
    [
        "succeeded in doing something difficult",
        "cancelled the project completely",
        "copied another team's design",
        "postponed the demonstration",
    ],
    0,
    "bring off + N",
    "bring off = pull off a difficult task.",
)
add(
    "bring over something",
    "mang theo từ nơi này đến nơi khác",
    "gap",
    "Could you bring ______ the extra microscopes from the old campus tomorrow?",
    ["over", "off", "about", "in"],
    0,
    "bring over + N",
    "bring over = bring from another place.",
)
add(
    "bring up",
    "nuôi nấng; đề cập",
    "gap",
    "Please do not bring ______ private family problems in a public group chat.",
    ["up", "about", "out", "in"],
    0,
    "bring up + N",
    "Ngữ cảnh này bring up = mention a topic.",
)
add(
    "confide in somebody",
    "tâm sự với ai vì tin tưởng",
    "gap",
    "She needed someone she could confide ______ after the online bullying started.",
    ["in", "to", "with", "on"],
    0,
    "confide in + sb",
    "confide in sb; confide sth to sb là cấu trúc khác.",
)
add(
    "come up with something",
    "nghĩ ra ý tưởng/giải pháp",
    "gap",
    "The group came up ______ a low-cost way to filter well water.",
    ["with", "to", "for", "on"],
    0,
    "come up with + N",
    "come up with an idea; come up to = tiến lại.",
)
add(
    "hope to do something",
    "hi vọng làm điều gì",
    "gap",
    "They hope ______ enough money for solar panels by December.",
    ["to raise", "raising", "raise", "for raising"],
    0,
    "hope to V",
    "hope to V; hope for + N.",
)
add(
    "joint effort",
    "sự nỗ lực chung",
    "gap",
    "Cleaning the riverbank was a joint ______ among three neighbouring schools.",
    ["effort", "effect", "afford", "affair"],
    0,
    "a joint effort",
    "joint effort, không nhầm effect.",
)
add(
    "patient with",
    "kiên nhẫn với ai",
    "gap",
    "Tutors need to be patient ______ beginners who still mix up verb forms.",
    ["with", "to", "for", "at"],
    0,
    "patient with + sb",
    "patient with a person; impatient with.",
)
add(
    "open up",
    "mở lòng; khai trương",
    "gap",
    "After several meetings, he finally opened ______ about his fear of oral exams.",
    ["up", "out", "over", "off"],
    0,
    "open up",
    "open up = talk about feelings; hoặc open a business.",
)
add(
    "put up",
    "dựng/treo; cho ở nhờ; chịu đựng",
    "gap",
    "Volunteers put ______ tents on the playground for the overnight drill.",
    ["up", "on", "out", "off"],
    0,
    "put up + N",
    "Ngữ cảnh này put up = erect/build.",
)
add(
    "adapt to something",
    "thích nghi với điều gì",
    "gap",
    "New boarders need time to adapt ______ sharing a room with three classmates.",
    ["to", "with", "for", "in"],
    0,
    "adapt to + N/V-ing",
    "adapt to a situation.",
)
add(
    "adjust to something",
    "điều chỉnh để phù hợp",
    "gap",
    "It took weeks to adjust ______ the earlier timetable after the rule change.",
    ["to", "with", "for", "on"],
    0,
    "adjust to + N",
    "adjust to new conditions.",
)
add(
    "allow somebody to do something",
    "cho phép ai đó làm gì",
    "gap",
    "The invigilator will not allow anyone ______ the room after the first 15 minutes.",
    ["to enter", "entering", "enter", "entered"],
    0,
    "allow sb to V",
    "allow sb to V; let sb V (không to).",
)
add(
    "avoid doing something",
    "tránh làm gì đó",
    "gap",
    "Avoid ______ the same linking word in every sentence of your paragraph.",
    ["repeating", "to repeat", "repeat", "repeated"],
    0,
    "avoid + V-ing",
    "avoid + V-ing, không to V.",
)
add(
    "contribute to",
    "đóng góp vào",
    "gap",
    "Skipping breakfast can contribute ______ poorer concentration in period 1.",
    ["to", "for", "with", "on"],
    0,
    "contribute to + N/V-ing",
    "contribute to a result; to là giới từ.",
)
add(
    "gain an understanding of something",
    "có được sự hiểu biết về",
    "gap",
    "Field visits helped them gain an understanding ______ local water management.",
    ["of", "for", "to", "on"],
    0,
    "gain an understanding of + N",
    "understanding of a topic.",
)
add(
    "gain insights into something",
    "có được cái nhìn sâu sắc về",
    "gap",
    "Interviews with street vendors gave students insights ______ informal urban economies.",
    ["into", "on", "for", "to"],
    0,
    "gain insights into + N",
    "insight(s) into, không on/to.",
)
add(
    "invest in",
    "đầu tư vào",
    "gap",
    "The school invested ______ better lighting after several night-time accidents.",
    ["in", "on", "to", "for"],
    0,
    "invest in + N",
    "invest in equipment/people/education.",
)
add(
    "prepare for",
    "chuẩn bị cho",
    "gap",
    "Candidates should prepare ______ both multiple-choice grammar and guided writing.",
    ["for", "to", "on", "with"],
    0,
    "prepare for + N",
    "prepare for an exam; prepare to V = sẵn sàng làm.",
)
add(
    "step out of somebody’s comfort zone",
    "bước ra khỏi vùng an toàn",
    "gap",
    "Joining the debate club forced her to step out of her comfort ______.",
    ["zone", "area", "place", "room"],
    0,
    "step out of one's comfort zone",
    "Collocation cố định: comfort zone.",
)
add(
    "struggle with",
    "vật lộn với, gặp khó khăn với",
    "gap",
    "He still struggles ______ word forms even though his reading is strong.",
    ["with", "to", "for", "on"],
    0,
    "struggle with + N",
    "struggle with a subject; struggle to V = khó để làm được hành động.",
)
add(
    "take steps to do something",
    "thực hiện các bước để làm gì",
    "gap",
    "The city has taken steps ______ motorbike noise around hospitals.",
    ["to reduce", "reducing", "reduce", "for reduce"],
    0,
    "take steps to V",
    "take steps to V; take steps towards + N/V-ing cũng gặp nhưng đáp án là to V.",
)
add(
    "turn into",
    "biến thành, trở thành",
    "gap",
    "Without maintenance, the community garden may turn ______ a dump.",
    ["into", "to", "in", "out"],
    0,
    "turn into + N",
    "turn into = become; turn out = hóa ra.",
)
add(
    "bring something back",
    "mang trả lại; gợi lại",
    "gap",
    "The old photograph brought ______ memories of the first school camp.",
    ["back", "up", "out", "about"],
    0,
    "bring sth back",
    "bring back memories = gợi lại; bring back an object = trả/mang về.",
)
add(
    "depend on",
    "phụ thuộc vào, dựa vào",
    "gap",
    "Whether the trip happens will depend ______ the weather warning at 5 a.m.",
    ["on", "of", "to", "at"],
    0,
    "depend on + N",
    "depend on; dependent on; independent of.",
)
add(
    "focus on",
    "tập trung vào",
    "gap",
    "In the last 10 minutes, focus ______ transferring answers and checking -s/-ed.",
    ["on", "to", "at", "in"],
    0,
    "focus on + N/V-ing",
    "focus on, không focus to.",
)
add(
    "make an effort to do something",
    "nỗ lực làm gì",
    "gap",
    "She made a real effort ______ more clearly after the first oral test.",
    ["to speak", "speaking", "speak", "for speaking"],
    0,
    "make an effort to V",
    "make an effort to V.",
)
add(
    "result from",
    "là kết quả từ",
    "gap",
    "The blackout resulted ______ overloaded transformers, not from student error.",
    ["from", "in", "to", "on"],
    0,
    "result from + N",
    "result from = caused by; result in = cause.",
)
add(
    "switch to",
    "chuyển đổi sang cái gì",
    "gap",
    "Several canteens have switched ______ reusable containers to cut plastic waste.",
    ["to", "into", "for", "with"],
    0,
    "switch to + N",
    "switch to a new method; convert into = biến thành.",
)
add(
    "cope with",
    "đối phó, đương đầu với",
    "gap",
    "Mindfulness sessions help students cope ______ peak-season stress.",
    ["with", "to", "for", "on"],
    0,
    "cope with + N",
    "cope with a problem.",
)
add(
    "deal with",
    "giải quyết, xử lý",
    "gap",
    "Homeroom teachers must deal ______ late arrivals consistently, not case by case.",
    ["with", "to", "about", "on"],
    0,
    "deal with + N",
    "deal with a problem/person.",
)
add(
    "encourage somebody to do something",
    "khuyến khích ai đó làm gì",
    "gap",
    "Parents should encourage teenagers ______ questions in class rather than staying silent.",
    ["to ask", "asking", "ask", "for asking"],
    0,
    "encourage sb to V",
    "encourage sb to V; discourage sb from V-ing.",
)
add(
    "measure up (to somebody/something)",
    "đạt tiêu chuẩn, đáp ứng kỳ vọng",
    "gap",
    "The first draft did not measure up ______ the marking rubric.",
    ["to", "with", "for", "on"],
    0,
    "measure up to + N",
    "measure up to expectations/standards.",
)
add(
    "persuade somebody to do something",
    "thuyết phục ai đó làm gì",
    "gap",
    "They persuaded the principal ______ a quiet room for students with sensory needs.",
    ["to provide", "providing", "provide", "for providing"],
    0,
    "persuade sb to V",
    "persuade sb to V; prevent sb from V-ing.",
)

# --- 201-240 ---
add(
    "be accustomed to something",
    "quen với điều gì",
    "gap",
    "After two months, she became accustomed to ______ 8 km to school.",
    ["cycling", "cycle", "cycled", "to cycle"],
    0,
    "be accustomed to + N/V-ing",
    "to là giới từ nên sau accustomed to phải dùng V-ing (cycling), không dùng to cycle.",
)
add(
    "be confronted with something",
    "đối mặt với điều gì",
    "gap",
    "New graduates are often confronted ______ job ads that demand years of experience.",
    ["with", "to", "for", "on"],
    0,
    "be confronted with + N",
    "confronted with a problem/situation.",
)
add(
    "blend in with somebody",
    "hòa nhập với ai",
    "gap",
    "He tried to blend in ______ local students by joining the football club.",
    ["with", "to", "for", "on"],
    0,
    "blend in with + sb/sth",
    "blend in with a group/surroundings.",
)
add(
    "emerge from something",
    "nổi lên từ, xuất hiện từ",
    "gap",
    "A practical solution emerged ______ weeks of messy trial and error.",
    ["from", "of", "out", "off"],
    0,
    "emerge from + N",
    "emerge from a process/crisis.",
)
add(
    "expose somebody to something",
    "cho ai tiếp xúc với cái gì",
    "gap",
    "Exchange programmes expose students ______ accents they never hear in textbooks.",
    ["to", "with", "for", "on"],
    0,
    "expose sb to sth",
    "expose to; exposure to (danh từ).",
)
add(
    "fall into something",
    "rơi vào tình trạng, sa vào",
    "gap",
    "Without a revision plan, it is easy to fall ______ the habit of only doing familiar exercises.",
    ["into", "to", "on", "for"],
    0,
    "fall into + N",
    "fall into a habit/trap/category.",
)
add(
    "fearful of something",
    "sợ hãi điều gì",
    "gap",
    "Some parents are fearful ______ letting children commute alone after dark.",
    ["of", "to", "for", "with"],
    0,
    "fearful of + N/V-ing",
    "fearful of; afraid of.",
)
add(
    "give somebody insights into something",
    "cho ai cái nhìn sâu sắc về",
    "gap",
    "The documentary gave us insights ______ how informal recyclers actually work.",
    ["into", "on", "to", "for"],
    0,
    "give sb insights into + N",
    "insights into, giống gain insights into.",
)
add(
    "give up",
    "từ bỏ",
    "gap",
    "She did not give ______ hope after the first unsuccessful audition.",
    ["up", "out", "in", "off"],
    0,
    "give up + N",
    "give up hope/a habit; khác câu give up + V-ing ở mục 76 vì đây là give up + danh từ.",
)
add(
    "move out",
    "rời khỏi nơi đang ở",
    "gap",
    "When the lease ended, three students moved ______ of the cramped room.",
    ["out", "off", "away", "over"],
    0,
    "move out (of)",
    "move out = leave accommodation; move away = chuyển đi xa.",
)
add(
    "participate in something",
    "tham gia vào cái gì",
    "gap",
    "All clubs must participate ______ the community fair or lose funding.",
    ["in", "on", "at", "to"],
    0,
    "participate in + N",
    "participate in = take part in.",
)
add(
    "pick out",
    "lựa chọn",
    "gap",
    "From twenty sketches, the teacher picked ______ three ideas worth developing.",
    ["out", "up", "on", "off"],
    0,
    "pick out + N",
    "pick out = choose/select; pick up = nhặt/học được.",
)
add(
    "preferable to something",
    "đáng ưa chuộng hơn cái gì",
    "gap",
    "A short daily review is preferable ______ a seven-hour cram the night before.",
    ["to", "than", "from", "with"],
    0,
    "preferable to + N/V-ing",
    "preferable to, không than (than đi với more/er).",
)
add(
    "push something aside",
    "gạt cái gì sang một bên",
    "gap",
    "She pushed her self-doubt ______ and volunteered to present first.",
    ["aside", "away", "off", "out"],
    0,
    "push sth aside",
    "push aside = ignore temporarily / move to the side.",
)
add(
    "sleep rough",
    "ngủ ngoài trời, vô gia cư",
    "mean",
    "After losing his job, the young man had to <u>sleep rough</u> for several weeks.",
    [
        "sleep outdoors because he had no home",
        "sleep very deeply after hard work",
        "take cheap overnight coaches",
        "share a crowded dormitory room",
    ],
    0,
    "sleep rough",
    "sleep rough = be homeless and sleep outside.",
)
add(
    "take care of/look after",
    "chăm sóc, lo liệu",
    "gap",
    "Older siblings often look ______ younger ones while parents work late.",
    ["after", "for", "at", "into"],
    0,
    "look after / take care of",
    "look after = take care of; look for = tìm; look at = nhìn.",
)
add(
    "turn out",
    "hóa ra là",
    "gap",
    "The 'shortcut' formula turned ______ to be useless on the actual paper.",
    ["out", "up", "in", "over"],
    0,
    "turn out (to be)",
    "turn out = prove to be in the end.",
)
add(
    "worry about something",
    "lo lắng về điều gì",
    "gap",
    "Try not to worry ______ one bad mock score; use it as diagnostic data.",
    ["about", "for", "to", "on"],
    0,
    "worry about + N",
    "worry about; worried about.",
)
add(
    "be attributed to",
    "được cho là do, được quy cho",
    "gap",
    "The drop in dengue cases was attributed ______ better drainage after the campaign.",
    ["to", "for", "with", "on"],
    0,
    "be attributed to + N",
    "be attributed to a cause.",
)
add(
    "be based on something",
    "được dựa trên",
    "gap",
    "The documentary is based ______ true events in a coastal commune.",
    ["on", "in", "at", "to"],
    0,
    "be based on + N",
    "based on facts/a book.",
)
add(
    "be capable of doing something",
    "có khả năng làm gì",
    "gap",
    "With scaffolding, most students are capable ______ the extended-response task.",
    ["of completing", "to complete", "completing", "complete"],
    0,
    "be capable of + V-ing",
    "capable of V-ing, không capable to V.",
)
add(
    "be impressed by something",
    "bị ấn tượng bởi cái gì",
    "gap",
    "The judges were impressed ______ the clarity of her data tables.",
    ["by", "for", "to", "on"],
    0,
    "be impressed by + N",
    "impressed by/with; đáp án theo danh mục là by.",
)
add(
    "discourage somebody from doing something",
    "làm ai nản lòng không làm gì",
    "gap",
    "One low mark should not discourage you ______ applying again next round.",
    ["from", "to", "of", "for"],
    0,
    "discourage sb from V-ing",
    "discourage from; encourage to.",
)
add(
    "get credit for something",
    "được công nhận vì điều gì",
    "gap",
    "The quiet coder rarely got credit ______ the features that made the app stable.",
    ["for", "to", "of", "with"],
    0,
    "get credit for + N/V-ing",
    "get/take credit for a contribution.",
)
add(
    "insist on something",
    "khăng khăng",
    "gap",
    "The invigilator insisted ______ seeing every student's ID, no exceptions.",
    ["on", "in", "to", "for"],
    0,
    "insist on + N/V-ing",
    "insist on, không insist to.",
)
add(
    "keep an eye on",
    "theo dõi, để mắt đến",
    "gap",
    "Please keep an eye ______ the beaker while I fetch the gloves.",
    ["on", "in", "at", "to"],
    0,
    "keep an eye on + sb/sth",
    "keep an eye on = watch carefully.",
)
add(
    "make an impact on",
    "tạo ra tác động đến",
    "gap",
    "A well-run peer club can make a real impact ______ first-year retention.",
    ["on", "in", "to", "for"],
    0,
    "make an impact on + N",
    "impact on; effect on; influence on.",
)
add(
    "broaden somebody’s perspective",
    "mở rộng góc nhìn của ai",
    "gap",
    "Living with a host family broadened her ______ on what 'independence' means.",
    ["perspective", "prospect", "permission", "performance"],
    0,
    "broaden sb's perspective",
    "broaden/widen one's perspective/horizons.",
)
add(
    "build relationships",
    "xây dựng các mối quan hệ",
    "gap",
    "Group projects help students build ______ that last beyond a single term.",
    ["relationships", "relations only with marks", "relatives", "relativity"],
    0,
    "build relationships",
    "build relationships (with sb).",
)
add(
    "carry on",
    "tiếp tục",
    "gap",
    "Even after the microphone failed, the speaker carried ______ without notes.",
    ["on", "out", "over", "off"],
    0,
    "carry on",
    "carry on = continue; carry out = thực hiện.",
)
add(
    "catch on",
    "trở nên phổ biến",
    "gap",
    "Reusable bottle discounts quickly caught ______ among high-school canteens.",
    ["on", "up", "out", "in"],
    0,
    "catch on",
    "catch on = become popular; catch up = bắt kịp.",
)
add(
    "find out",
    "phát hiện ra, hiểu ra",
    "gap",
    "We need to find ______ who changed the shared lab password.",
    ["out", "up", "over", "off"],
    0,
    "find out + N/wh-clause",
    "find out = discover; find = tìm thấy vật.",
)
add(
    "get off the beaten track",
    "đi đến nơi hẻo lánh, ít người biết",
    "mean",
    "Their geography project required them to <u>get off the beaten track</u> and survey a little-known wetland.",
    [
        "go to a place that few tourists visit",
        "follow the most crowded tour route",
        "leave the train at the wrong station",
        "study only maps without fieldwork",
    ],
    0,
    "get off the beaten track",
    "off the beaten track = not the usual tourist path.",
)
add(
    "have an effect on something",
    "có ảnh hưởng đến cái gì",
    "gap",
    "Late-night gaming can have a serious effect ______ working memory the next morning.",
    ["on", "in", "to", "for"],
    0,
    "have an effect on + N",
    "effect on; affect + N (động từ, không cần on).",
)
add(
    "integrate something into something",
    "kết hợp cái gì vào cái gì",
    "gap",
    "The school wants to integrate coding ______ every science project, not only IT class.",
    ["into", "to", "for", "on"],
    0,
    "integrate A into B",
    "integrate into a system/course.",
)
add(
    "lift somebody out of something",
    "giúp ai thoát khỏi điều gì",
    "gap",
    "Targeted scholarships can lift able students ______ poverty without uprooting families.",
    ["out of", "off", "from out", "away"],
    0,
    "lift sb out of + N",
    "lift sb out of poverty/difficulty.",
)
add(
    "opt for something",
    "chọn cái gì",
    "gap",
    "After comparing campuses, she opted ______ the school with stronger lab facilities.",
    ["for", "to", "on", "at"],
    0,
    "opt for + N",
    "opt for an option; opt to V.",
)
add(
    "be willing to do something",
    "sẵn lòng làm gì",
    "gap",
    "A strong teammate is willing ______ credit when the idea was not originally theirs.",
    ["to share", "sharing", "share", "for sharing"],
    0,
    "be willing to V",
    "willing to V.",
)

# --- 241-280 ---
add(
    "benefit from",
    "hưởng lợi từ",
    "gap",
    "Shy students often benefit ______ smaller speaking groups before whole-class talks.",
    ["from", "of", "by", "with"],
    0,
    "benefit from + N/V-ing",
    "benefit from; be of benefit to.",
)
add(
    "drive somebody to do something",
    "thúc đẩy ai đó làm gì",
    "gap",
    "Compassion, not ranking, drove her ______ medicine in a remote clinic.",
    ["to study", "studying", "study", "for studying"],
    0,
    "drive sb to V",
    "drive sb to V = motivate strongly.",
)
add(
    "make decisions",
    "đưa ra quyết định",
    "gap",
    "Teenagers should be coached to make informed ______ rather than copy friends.",
    ["decisions", "decisive", "decide", "decision's"],
    0,
    "make decisions",
    "make a decision/decisions; take a decision cũng gặp (BrE) nhưng collocation học sinh là make.",
)
add(
    "be sentenced to",
    "bị kết án",
    "gap",
    "The poacher was sentenced ______ two years of community service in the reserve.",
    ["to", "for", "with", "on"],
    0,
    "be sentenced to + N",
    "be sentenced to a punishment; sentenced for a crime.",
)
add(
    "escape from",
    "thoát khỏi",
    "gap",
    "The narrative describes how villagers escaped ______ rising floodwater at dawn.",
    ["from", "of", "off", "out"],
    0,
    "escape from + N",
    "escape from a place/situation.",
)
add(
    "pay homage to",
    "bày tỏ lòng kính trọng, tưởng nhớ",
    "gap",
    "The mural pays homage ______ teachers who stayed during the epidemic.",
    ["to", "for", "with", "on"],
    0,
    "pay homage to + sb/sth",
    "pay homage to = show respect.",
)
add(
    "testament to something",
    "minh chứng cho",
    "gap",
    "The restored mangrove belt is a testament ______ years of community labour.",
    ["to", "for", "of", "on"],
    0,
    "a testament to + N",
    "be a testament to = prove/show clearly.",
)
add(
    "be mindful of something",
    "lưu tâm, để tâm tới",
    "gap",
    "Be mindful ______ classmates who need extra time to process spoken instructions.",
    ["of", "to", "for", "on"],
    0,
    "be mindful of + N",
    "mindful of = aware and careful.",
)
add(
    "play a vital role in something",
    "đóng vai trò thiết yếu trong cái gì",
    "gap",
    "School nurses play a vital role ______ detecting early signs of heatstroke.",
    ["in", "on", "at", "for"],
    0,
    "play a vital role in",
    "vital/key/pivotal/major role đều đi với in.",
)
add(
    "combine something with something",
    "kết hợp cái gì với cái gì",
    "gap",
    "The task combines statistical analysis ______ a short community interview.",
    ["with", "to", "for", "in"],
    0,
    "combine A with B",
    "combine A with B; combine into = hòa thành một.",
)
add(
    "gain qualifications",
    "đạt được bằng cấp/chứng chỉ",
    "gap",
    "Evening classes allowed her to gain extra ______ while working part-time.",
    ["qualifications", "qualities", "qualifiers", "quantities"],
    0,
    "gain qualifications",
    "gain/obtain qualifications ≠ qualities (phẩm chất).",
)
add(
    "be proud of something",
    "tự hào về điều gì",
    "gap",
    "The team was proud ______ finishing the prototype without copying others.",
    ["of", "for", "to", "with"],
    0,
    "be proud of + N/V-ing",
    "proud of; proud to V = tự hào được làm.",
)
add(
    "be attracted by something",
    "bị thu hút bởi cái gì",
    "gap",
    "Many visitors are attracted ______ the floating market's early-morning rhythm.",
    ["by", "for", "on", "at"],
    0,
    "be attracted by + N",
    "attracted by a feature/scene; attracted to a person/place cũng gặp nhưng đáp án theo danh mục là by.",
)
add(
    "play an important role in something",
    "đóng vai trò quan trọng trong việc gì",
    "gap",
    "Libraries play an important ______ in giving students quiet space to revise.",
    ["role", "roll", "rule", "rate"],
    0,
    "play an important role in",
    "Thiếu role là lỗi thường gặp; không nhầm roll/rule.",
)
add(
    "provide access to something",
    "mang đến sự tiếp cận với cái gì",
    "gap",
    "The grant will provide access ______ digital textbooks for low-income students.",
    ["to", "for", "with", "of"],
    0,
    "provide access to + N",
    "access to a resource; provide sb with sth là mẫu khác.",
)
add(
    "place pressure on somebody",
    "gây áp lực lên ai",
    "gap",
    "Constant ranking tables place unfair pressure ______ 15-year-olds.",
    ["on", "to", "in", "at"],
    0,
    "place/put pressure on + sb",
    "pressure on a person.",
)
add(
    "play a major role in doing something",
    "đóng vai trò chính trong việc gì",
    "gap",
    "Peer feedback played a major role ______ the quality of the final essays.",
    ["in improving", "to improve", "improve", "for improve"],
    0,
    "play a major role in + V-ing",
    "in + V-ing, không to V.",
)
add(
    "aspire to something",
    "khao khát, mong ước điều gì",
    "gap",
    "He aspires ______ a research career in climate science, not just a high test score.",
    ["to", "for", "at", "on"],
    0,
    "aspire to + N/V",
    "aspire to a career / aspire to be...",
)
add(
    "be part and parcel of something",
    "là một phần tất yếu của cái gì",
    "mean",
    "Late-night revision is not <u>part and parcel of</u> effective learning, despite what rumours say.",
    [
        "an essential and unavoidable component of",
        "a rare exception in",
        "a legal requirement for",
        "an optional extra after",
    ],
    0,
    "be part and parcel of + N",
    "part and parcel of = inseparable part.",
)
add(
    "conflict with something",
    "xung đột, mâu thuẫn với cái gì",
    "gap",
    "The extra training session conflicts ______ her chemistry practical.",
    ["with", "to", "against", "on"],
    0,
    "conflict with + N",
    "conflict with a schedule/value.",
)
add(
    "exclude somebody from something",
    "loại trừ ai khỏi cái gì",
    "gap",
    "No student should be excluded ______ the trip solely because of uniform cost.",
    ["from", "of", "off", "out"],
    0,
    "exclude sb from + N",
    "exclude from; include in.",
)
add(
    "pay attention to something",
    "chú ý vào điều gì",
    "gap",
    "Pay attention ______ the tense of the first verb before you transform the sentence.",
    ["to", "on", "for", "at"],
    0,
    "pay attention to + N",
    "pay attention to, không on (focus on).",
)
add(
    "sceptical of something",
    "hoài nghi về cái gì",
    "gap",
    "Good readers stay sceptical ______ miracle study apps that promise overnight fluency.",
    ["of", "to", "for", "on"],
    0,
    "sceptical of + N",
    "sceptical of/about; đáp án theo danh mục là of.",
)
add(
    "take something for granted",
    "cho rằng điều gì là hiển nhiên",
    "mean",
    "After moving to the city, she stopped <u>taking clean tap water for granted</u>.",
    [
        "assuming it would always be there without appreciating it",
        "refusing to drink it under any circumstances",
        "paying extra to have it delivered daily",
        "testing it in the school laboratory each week",
    ],
    0,
    "take sth for granted",
    "take for granted = coi là đương nhiên.",
)
add(
    "watch out for",
    "cẩn thận, đề phòng",
    "gap",
    "Watch out ______ questions that look like present simple but hide a present-perfect signal.",
    ["for", "to", "on", "at"],
    0,
    "watch out for + N",
    "watch out for = be careful of.",
)
add(
    "a pipe dream",
    "giấc mơ viển vông",
    "mean",
    "Promising every student a perfect score without extra hours is <u>a pipe dream</u>.",
    [
        "an unrealistic hope that is unlikely to happen",
        "a carefully costed official plan",
        "a short-term timetable for revision",
        "a proven method used by all top schools",
    ],
    0,
    "a pipe dream",
    "pipe dream = unrealistic dream.",
)
add(
    "make a contribution to",
    "đóng góp vào",
    "gap",
    "Even small weekend clean-ups make a contribution ______ a healthier canal.",
    ["to", "for", "in", "on"],
    0,
    "make a contribution to + N",
    "contribution to, giống contribute to.",
)
add(
    "pose a risk",
    "gây ra rủi ro",
    "gap",
    "Unlicensed food stalls outside the gate may pose a ______ to students' health.",
    ["risk", "risky", "dangerously", "harmful"],
    0,
    "pose a risk (to)",
    "pose a risk/threat; không pose a risky.",
)
add(
    "cancel out",
    "triệt tiêu / làm mất tác dụng",
    "gap",
    "Eating a heavy fried meal can cancel ______ the benefit of an hour's jogging.",
    ["out", "off", "over", "away"],
    0,
    "cancel out + N",
    "cancel out = neutralize the effect.",
)
add(
    "prevent something from doing something",
    "ngăn cái gì làm gì",
    "gap",
    "A simple lock prevented the gate ______ swinging open during the storm.",
    ["from", "to", "of", "for"],
    0,
    "prevent sth/sb from V-ing",
    "prevent from V-ing; không prevent to V.",
)
add(
    "refer to",
    "đề cập đến, tham khảo",
    "gap",
    "Please refer ______ the rubric on page 2 before you start writing.",
    ["to", "at", "for", "on"],
    0,
    "refer to + N",
    "refer to a source/person.",
)
add(
    "enter into",
    "tham gia / ký kết (thỏa thuận)",
    "gap",
    "The two schools entered ______ an agreement to share laboratory equipment.",
    ["into", "in", "to", "on"],
    0,
    "enter into + an agreement/contract",
    "enter into an agreement; enter a room (không into) là nghĩa khác.",
)
add(
    "take priority over",
    "được ưu tiên hơn",
    "gap",
    "Safety drills take priority ______ extra coaching in the last week of term.",
    ["over", "on", "to", "from"],
    0,
    "take priority over + N",
    "take/have priority over sth.",
)
add(
    "pledge to",
    "cam kết / thề hứa làm gì",
    "gap",
    "The canteen pledged ______ single-use plastic bottles by the next school year.",
    ["to stop selling", "stopping selling", "stop selling", "for stopping"],
    0,
    "pledge to V",
    "pledge to V; pledge + N (pledge support).",
)
add(
    "convert something into something",
    "chuyển đổi cái gì thành cái gì",
    "gap",
    "The old canteen was converted ______ a quiet study hall after renovation.",
    ["into", "to", "for", "as"],
    0,
    "convert A into B",
    "convert into = change from one form/use to another.",
)
add(
    "at stake",
    "bị đe dọa; đang đặt cược/rủi ro",
    "mean",
    "With scholarships <u>at stake</u>, candidates cannot afford careless word-form errors.",
    [
        "in danger of being lost if things go wrong",
        "already guaranteed for every student",
        "unrelated to the final result",
        "postponed until the next academic year",
    ],
    0,
    "at stake",
    "at stake = being risked; the outcome matters.",
)


def rotate_choices(opts: list[str], ans: int, index: int) -> tuple[list[str], str]:
    """Spread keys across A/B/C/D so the set is not all-option-A."""
    shift = index % 4
    rotated = opts[shift:] + opts[:shift]
    new_ans = (ans - shift) % 4
    return rotated, rotated[new_ans]


def build_question(index: int, item: dict) -> dict:
    n = index + 1
    choices, answer = rotate_choices(item["opts"], item["ans"], index)
    if item["kind"] == "mean":
        header = "Choose the option closest in meaning to the underlined part."
    else:
        header = "Choose the best answer to complete the sentence."
    de_bai = f"{header} {item['prompt']}"
    loi_giai = (
        f"Cấu trúc trọng tâm: {item['s']} ({item['vi']}). "
        f"Dạng chuẩn: {item['form']}. "
        f"{item['why']} "
        f"Đáp án đúng là «{answer}». "
        f"Các lựa chọn còn lại sai giới từ, sai dạng V-ing/to V, hoặc đổi nghĩa của cụm."
    )
    form_l = item["form"].lower()
    if item["kind"] == "mean":
        meo = (
            "Thành ngữ phải hiểu theo nghĩa cả cụm và ngữ cảnh câu, không dịch word-by-word. "
            "Loại đáp án theo nghĩa đen."
        )
    elif any(
        token in form_l
        for token in (
            "to + v-ing",
            "to + n/v-ing",
            "view to",
            "accustomed to",
            "forward to",
            "committed to",
            "from v-ing",
            "of + v-ing",
            "habit of",
        )
    ):
        meo = (
            "Nếu to/from/of là giới từ (committed to, look forward to, prevent from, capable of…) "
            "thì sau đó dùng V-ing hoặc danh từ, không dùng to V."
        )
    elif "to v" in form_l:
        meo = (
            "Sau tend/intend/enable/force/expect/manage/promise… dùng to V. "
            "Loại ngay đáp án V-ing nếu động từ này không nhận V-ing."
        )
    else:
        meo = (
            "Học nguyên collocation (động từ + giới từ/particle). "
            "Gạch chân giới từ trước chỗ trống rồi loại đáp án không cùng cụm."
        )
    return {
        "id": f"english-cautruc-{n:03d}",
        "monHoc": "TiengAnh",
        "chuyenDe": "CauTrucCau",
        "mucDo": "VanDungCao",
        "namXuatHien": None,
        "nguon": SOURCE,
        "deBai": de_bai,
        "luaChon": choices,
        "dapAn": answer,
        "loiGiai": loi_giai,
        "meoLamBai": meo,
        "tags": [
            "TPHCM",
            "GDPT2018",
            "CauTrucCau",
            "VanDungCao",
            "Collocation",
            "Lop10-12",
            "DeMoPhong",
        ],
        "examPriority": "Cao",
        "examPart": "Câu 5-16/35-40",
        "realExamPattern": "Cấu trúc câu, collocation, cụm động từ và thành ngữ (ôn lớp 10-12)",
        "examYears": [],
        "estimatedTimeSeconds": 90,
        "structure": item["s"],
    }


def validate(rows: list[dict], items: list[dict]) -> None:
    assert len(items) == 280, f"Expected 280 source items, got {len(items)}"
    assert len(rows) == 280, f"Expected 280 questions, got {len(rows)}"
    ids = [r["id"] for r in rows]
    assert len(set(ids)) == 280, "Duplicate IDs"
    prompts = [r["deBai"] for r in rows]
    assert len(set(prompts)) == 280, "Duplicate stems"
    for r in rows:
        assert r["dapAn"] in r["luaChon"], r["id"]
        assert len(r["luaChon"]) == 4, r["id"]
        assert len(set(r["luaChon"])) == 4, r["id"]
        text = r["deBai"] + r["loiGiai"] + r["meoLamBai"]
        assert "đ" in r["loiGiai"] or "ă" in r["loiGiai"] or "ư" in r["loiGiai"], r["id"]
        for field in (
            "id",
            "monHoc",
            "chuyenDe",
            "mucDo",
            "nguon",
            "deBai",
            "dapAn",
            "loiGiai",
            "meoLamBai",
            "tags",
            "estimatedTimeSeconds",
        ):
            assert field in r and r[field] not in ("", None, []), (r["id"], field)
        _ = text
    positions = [r["luaChon"].index(r["dapAn"]) for r in rows]
    assert len(set(positions)) == 4, "Answer keys are not spread across A/B/C/D"


def append_jsonl(path: Path, rows: list[dict]) -> None:
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    # Drop previously generated CauTrucCau lines so the script is idempotent.
    kept = []
    for line in existing.splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get("chuyenDe") == "CauTrucCau" or str(obj.get("id", "")).startswith(
            "english-cautruc-"
        ):
            continue
        kept.append(line)
    new_lines = [json.dumps(row, ensure_ascii=False) for row in rows]
    path.write_text("\n".join(kept + new_lines) + "\n", encoding="utf-8")


def splice_questions_data(rows: list[dict]) -> None:
    """Insert new items before the closing ]; without reformatting the old bank."""
    js_path = WEB / "questions-data.js"
    text = js_path.read_text(encoding="utf-8-sig")
    if not text.lstrip("\ufeff").startswith("window.QUESTION_BANK = "):
        raise SystemExit("Unexpected questions-data.js prefix")
    body = text.rstrip()
    if body.endswith(";"):
        body = body[:-1].rstrip()
    if not body.endswith("]"):
        raise SystemExit("questions-data.js does not end with ]")
    body = body[:-1].rstrip()
    for marker in ('"id": "english-cautruc-001"', '"id":  "english-cautruc-001"'):
        pos = body.find(marker)
        if pos != -1:
            start = body.rfind("{", 0, pos)
            comma = body.rfind(",", 0, start)
            if comma == -1:
                raise SystemExit("Could not find comma before existing CauTrucCau block")
            body = body[:comma].rstrip()
            break
    blob = json.dumps(rows, ensure_ascii=False, indent=4)
    inner = blob.strip()[1:-1].strip()
    js_path.write_text(body + ",\n" + inner + "\n];\n", encoding="utf-8-sig")


def write_sidecar(rows: list[dict]) -> None:
    out = DATA / "english-cautruc.jsonl"
    out.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    rows = [build_question(i, item) for i, item in enumerate(ITEMS)]
    validate(rows, ITEMS)
    write_sidecar(rows)
    append_jsonl(DATA / "english.jsonl", rows)
    splice_questions_data(rows)
    print(f"Wrote {len(rows)} CauTrucCau questions.")


if __name__ == "__main__":
    main()
