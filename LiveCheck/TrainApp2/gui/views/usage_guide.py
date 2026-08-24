"""Hướng dẫn vận hành — khớp sidebar / workflow thực tế của desk."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from gui.navigation import ALL_ITEMS
from gui.page_chrome import render_page_header

_DOCS = Path(__file__).resolve().parents[2] / "docs"
_MINING_DOC = _DOCS / "mining_search_space.md"
_GRID_DOC = _DOCS / "grid_search.md"


def _desk_ctx() -> dict:
  """Desk-specific labels from protocol (EUR E21 / GBP G23 / …)."""
  from mt5_bridge.history_sync import MT5_CACHE_PATH
  from mt5_bridge.protocol import (
    BRIDGE_DIR,
    BRIDGE_SIM_DIR,
    DEFAULT_MAGIC,
    DEFAULT_SIM_MAGIC,
    INSTANCE_ID,
    MAX_BRIDGE_MODELS,
  )
  from gui.desk_ui import pair_label, tf_label

  try:
    from gui.trade_model import desk_pair_code
    pair = desk_pair_code()
  except Exception:
    pair = "EUR"

  ea_live = f"ForgeBridge{INSTANCE_ID}"
  ea_sim = f"ForgeBridge{INSTANCE_ID}Sim"
  cache_rel = f"data/{MT5_CACHE_PATH.name}"

  return {
    "instance": INSTANCE_ID,
    "pair": pair,
    "pair_label": pair_label(),
    "tf": tf_label(),
    "ea_live": ea_live,
    "ea_sim": ea_sim,
    "bridge_live": BRIDGE_DIR.name,
    "bridge_sim": BRIDGE_SIM_DIR.name,
    "magic": DEFAULT_MAGIC,
    "magic_sim": DEFAULT_SIM_MAGIC,
    "max_models": MAX_BRIDGE_MODELS,
    "cache": cache_rel,
  }


def _render_doc_expander(title: str, path: Path, fallback: str) -> None:
  with st.expander(title, expanded=False):
    if path.exists():
      st.markdown(path.read_text(encoding="utf-8"))
    else:
      st.warning(f"Không tìm thấy `{path.name}`. {fallback}")


def render():
  render_page_header(ALL_ITEMS["guide"], show_workspace=False)
  d = _desk_ctx()

  st.caption(
    f"Desk **{d['instance']}** · {d['pair_label']} {d['tf']} · "
    f"EA `{d['ea_live']}` · "
    f"bridge `{d['bridge_live']}` · magic `{d['magic']}`"
  )

  # ── Mục lục nhanh ──────────────────────────────────────────────
  st.markdown(
    """
**Cách đọc:** mục **0** (đánh giá) → **2** (5 bước) → **3** (khái niệm) khi vận hành;
mục **7–8** khi vướng; **Thuật ngữ** ở cuối trang.
"""
  )

  # ── 0. Đánh giá nhanh (honesty for the user) ───────────────────
  st.markdown("## 0. Đánh giá nhanh")
  st.info(
    "**Khớp thực tế app:** sidebar 7 trang · workflow Tổng quan "
    "(KB → Grid → Model → Compare → Live) · Active ≠ Bridge · Archive · "
    "Paper Monitor đã gỡ · remine theo Bridge roster.\n\n"
    "**Còn lệch / hạn chế** (chi tiết mục 7): Bridge chưa lọc Candidates/Live-ok; "
    "module tên `paper_*` vẫn tồn tại cho sim fills; "
    "một app = một pair/timeframe."
  )

  # ── 1. Sidebar map ─────────────────────────────────────────────
  st.markdown("## 1. Bản đồ sidebar — đúng đúng trang")
  st.markdown(
    f"""
Sidebar hiện tại (**không** còn Paper Monitor / Phân tích riêng):

| Trang | Việc chính |
|-------|------------|
| **Tổng quan** | Data refresh · tiến độ workflow · KPI |
| **Học & tối ưu** | ① Cài đặt → ② Huấn luyện KB → ③ Grid Search |
| **Trade Models** | Active (phân tích) · **Tổng hợp** (so sánh / Archive / đổi tên) · Sức khỏe · Rủi ro · Nhật ký · Chiến lược |
| **Compare Trade** | So nhiều model trên lịch sử (**không EA**; sim fills) |
| **Live Trade** | Desk theo dõi Live hàng ngày (KPI / trạng thái) |
| **MT5 Bridge** | Roster 1–{d['max_models']} model · **một EA Live** · test lịch sử from/to · remine · Parity · Loss guard |
| **Hướng dẫn** | Trang này |

Thứ tự đọc khuyến nghị: mục **2** → **3** → chạy workflow → quay lại **7–8** khi vướng.
"""
  )

  # ── 2. Workflow ────────────────────────────────────────────────
  st.markdown("## 2. Quy trình 5 bước (khớp Tổng quan)")
  st.markdown(
    f"""
Panel workflow trên **Tổng quan** và thứ tự vận hành:

| Bước | Trang | Việc |
|------|-------|------|
| ① | Học & tối ưu → Huấn luyện | Học KB đủ giai đoạn / vòng theo Cài đặt |
| ② | Học & tối ưu → Grid Search | Chạy combo (train × KB × epoch × mining preset) |
| ③ | Trade Models | **Tạo** model từ combo → xem Health / Tổng hợp |
| ④ | Compare Trade | So model trên lịch sử trước khi Live |
| ⑤ | MT5 Bridge | Chọn **roster** → Start **Live** → theo dõi Parity / Live Trade |

**Nguyên tắc**

| Mục đích | Dùng gì |
|----------|---------|
| Đánh giá strategy | Grid + Health OOS + spread/slip · **KB OFF** làm baseline |
| Cải thiện kinh nghiệm | Học KB giai đoạn A → OOS giai đoạn B (không leakage) |
| Vận hành | Bridge roster + remine tuần · **không** Grid lại mỗi tuần |
| Cất nghiên cứu | **Archive** (giữ report) thay vì Xóa cứng |

Chỉ Live **micro lot** khi Parity / Health khớp kỳ vọng. Test lịch sử & Compare **không** thay lệnh MT5.
"""
  )

  # ── 3. Concepts ────────────────────────────────────────────────
  st.markdown("## 3. Khái niệm dễ nhầm")
  st.markdown(
    f"""
### Active ≠ Bridge ≠ Compare ≠ Test lịch sử

| | **Active** | **Bridge roster** | **Compare** | **Test lịch sử** |
|---|---|---|---|---|
| Ở đâu | Dropdown Trade Models | Tab MT5 Bridge · Trade Models | Trang Compare Trade | Tab MT5 Bridge · Test lịch sử (chỉ from/to) |
| Việc | Phân tích / Health / Journal | Remine + quyết định Live | So lịch sử, không EA | Ghi from/to → EA → bar/fill hiện trên **Live** |
| Điều khiển lệnh MT5? | Không | **Live:** có (cần EA) | Không | Không (không tiền thật) |
| Khớp lệnh nội bộ | — | Fill EA → `trades.json` | `PaperBook` sim fills | Fill EA sim / paper path |

**Active không ghi đè Bridge.** Đổi Active chỉ đổi tab phân tích.

### Archive vs Xóa cứng

- **Archive** — cất kệ nghiên cứu, giữ report/schedule/KB pin, ẩn Active/Bridge, **gỡ `model_ids`**. Restore **không** tự add Bridge.
- **Xóa cứng** — mất store + artifact. Chỉ khi chắc không cần.
- **Id ma** — id còn trong Bridge config nhưng model đã Archive/xóa → **Dọn roster** / **Dọn Bridge**.

### “Paper” trong code ≠ Paper Monitor

Desk **Paper Monitor** đã gỡ (bookmark cũ → Bridge).  
Module `paper_fill` / `PaperBook` / port chart legacy = **sim fills** cho Compare/test lịch sử — đúng kỹ thuật, dễ nhầm tên.

### Remine vs cập nhật model

| Việc | Tự động? | Điều kiện |
|------|----------|-----------|
| Remine strategy mỗi tuần | Có | Bridge **Live** Start · theo **từng id trong roster** |
| Đồng bộ lịch sử MT5 | Có | Tổng quan / Bridge + EA |
| Học KB / Grid / tạo model | Không | Thủ công khi muốn đổi “bộ não” |
| Archive / đổi roster | Không | Thủ công |
"""
  )

  # ── 4. Trade Models ────────────────────────────────────────────
  st.markdown("## 4. Trade Models")
  st.markdown(
    f"""
**Active** (dropdown trên cùng) = model đang xem cho tab Thông tin / Sức khỏe / Rủi ro / Nhật ký / Chiến lược.

**Tổng hợp**

- Bảng so sánh KPI · badge Live-ok / High-DD / Grid-only / Stale / Archived
- Mặc định ẩn High-DD + chưa OOS + Archived (Bridge luôn hiện nếu còn trên roster)
- Click dòng → **Đổi tên** · **Archive** · **Xóa cứng** (xác nhận) · **Export .tmpkg**
- Export ghi `Trade/live/packages_inbox/*.tmpkg` (cần schedule từ tab **Sức khỏe**)
- Trade import: `http://127.0.0.1:8601/?nav=Models` — tab Live chỉ chạy roster đã import
- Cảnh báo id ma + nút Dọn Bridge

**Sức khỏe** — report OOS, KB ON/OFF, mining space vs baseline.

Desk **{d['pair']}**: sort Tổng hợp mặc định khác nhau (EUR ưu tiên Total R; GBP ưu tiên WR → DD → R).
"""
  )

  # ── 5. Runtime pages ───────────────────────────────────────────
  st.markdown("## 5. Compare · Live Trade · MT5 Bridge")
  st.markdown(
    f"""
### Compare Trade
So 1–N model trên cache {d['tf']} (`{d['cache']}`). Không EA. Kết quả = sim fills — **không** mở lệnh tài khoản.

### Live Trade
Dashboard theo dõi ngày khi Live đang chạy (KPI / trạng thái). Không thay Bridge Start/Stop.

### MT5 Bridge — một EA Live

1. Tab **Trade Models**: chọn 1–{d['max_models']} model (không gồm Archived) · Risk % chung · Loss guard.
2. **Desk** → **Start** service (process riêng — đổi tab GUI không dừng).
3. MT5: attach `{d['ea_live']}` · Live · Files/`{d['bridge_live']}`.
4. Mỗi {d['tf']}: EA `bar.json` → App decide → `decision.json` → BUY/SELL/FLAT → `fill.json` → `trades.json`.
5. Remine Live cùng đường Health OOS (KB pin, `conditions_fp`). Xem **Parity tuần này**.
6. Tab **Test lịch sử**: chỉ nhập from/to. App ghi `sim_control.json` vào `{d['bridge_live']}`. EA CopyRates, **cùng** `decide_for_bar` + loss guard như Live, **fill giấy** tại open nến (không OrderSend). Chart / lệnh / thống kê xem **Desk** / **Biểu đồ** (cùng folder). Tick Live tạm dừng đến khi Stop.
7. Một hàng tab: **Trade Models** · **Desk** · **Biểu đồ** · **Sức khỏe** · **Kỹ thuật** · **Test lịch sử**.

Cần tài khoản **hedging** nếu multi-model. Magic `{d['magic']}`.

| | Live | Test lịch sử (Simulate) |
|---|---|---|
| Pipeline | EA nến đóng → App `decide_for_bar` → `OpenFromDecision` | **Cùng** (một EA, một worker, một folder) |
| Giá | Tick / nến đang chạy | CopyRates lịch sử (OHLC quá khứ) |
| Lệnh | `OrderSend` tài khoản MT5 | Fill giấy — **không** vào MT5 |
| Loss guard / roster / magic | Bật | Bật (cùng journal) |
| Journal / chart | `{d['bridge_live']}/trades.json` + biểu đồ Live | Cùng chỗ (Live không biết đang replay) |
| Khi dùng | Desk + Sức khỏe / Parity | Test pipeline Live trên nến đã đóng |
"""
  )

  # ── 6. Deep dive ───────────────────────────────────────────────
  st.markdown("## 6. Học sâu: Train · KB · Epoch · Mining · Grid")
  st.markdown(
    f"""
### Walk-forward
```
|---- train 3/6/9 tuần ----|-- OOS tuần --|
Tuần sau: cửa sổ trượt tới trước. OOS không nằm trong train. Features chỉ quá khứ.
```
**KB OFF** = đánh giá trung thực nhất trước khi tin Live.

### Train · KB · Epoch (ba tầng)

| | Train 3/6/9 tuần | KB | Epoch |
|---|---|---|---|
| Là gì | Mine strategy mỗi tuần WF | Bộ nhớ dài hạn | Một vòng học full giai đoạn |
| Tần suất | Mỗi tuần OOS | Dùng khi KB ON | Thủ công 3–5–8 lần |
| Mục đích | Khớp regime gần | Mine thông minh hơn | Cải thiện KB |

### Mining search space
Cách miner được phép tìm edge (RR, exit, anti-chase…) — **khác** KB và train weeks.  
Mặc định app: preset **`elite_or_quality`** (thường **ít lệnh hơn**, WR/DD tốt hơn).  
Đổi ở Cài đặt chỉ ảnh hưởng Grid; Live/Sim theo space **đã lưu trên Trade Model** trong Bridge roster.

### Grid Search
Số combo ≈ `train × KB profile × epoch × mining_preset` (OOS/spread/slip cố định).  
`grid_objective` chỉ xếp hạng, không nhân combo. Đổi Cài đặt → Grid chỉ chạy combo **mới**.

### Chi phí & hold-out
Spread/slip mặc định desk (EUR thường 1.0/0.3; GBP thường 1.5/0.3) — luôn bật khi đánh giá.  
Hold-out: giữ tháng cuối chỉ test, không re-optimize WF chính.

### Mục tiêu checklist
Checklist “đủ điều kiện” chỉ còn: **WR>60% · RR>2 · profitable** (1 năm gần nhất).  
Tần suất lệnh/tuần **đã bỏ** khỏi checklist (preset elite cố ý ít lệnh). Vẫn xem **Tpw** trên Tổng hợp / report để biết mật độ — không coi đỏ/xanh tần suất là gate Live.
"""
  )

  _render_doc_expander(
    "Mining search space — tài liệu đầy đủ",
    _MINING_DOC,
    "Mở `docs/mining_search_space.md` trong repo.",
  )
  _render_doc_expander(
    "Grid Search — tham số & combo",
    _GRID_DOC,
    "Mở `docs/grid_search.md` trong repo.",
  )

  with st.expander("Chạy app / CLI (ngắn)"):
    st.markdown(
      f"""
```powershell
# Windows — lifecycle
.\\scripts\\run_app_windows.ps1 Start|Restart|Status|Stop
.\\scripts\\deploy_xm_forgebridge.ps1 -Desk e21 -Mode Live -Attach
```

```bash
python run_gui.py
python run_backtest.py --no-kb --oos-from 2024-01-01 --oos-to 2024-12-31 --spread 1.0 --slippage 0.3
python run_learning.py --kb-profile era_2022_2023 --from-date 2022-01-01 --until-date 2023-12-31 --epochs 3
python scripts/mt5_bridge_service.py
```

Cache: `{d['cache']}` · Bridge: `mt5/{d['bridge_live']}` · EA: `{d['ea_live']}.mq5`
"""
    )

  with st.expander("Sơ đồ Train · KB · Epoch"):
    st.code(
      """
graph TD
  E[Epoch offline] --> KB[KB Profile]
  KB --> WF[Mỗi tuần OOS]
  WF --> T[Train 3/6/9 tuần]
  T --> M[Mine]
  KB -.->|KB ON| M
  M --> TR[Trade 1 tuần]
""",
      language="text",
    )

  with st.expander("Sơ đồ quy trình desk"):
    st.code(
      """
graph TD
  S[Cài đặt] --> KB[Huấn luyện KB]
  KB --> G[Grid Search]
  G --> M[Tạo Trade Model]
  M --> C[Compare Trade]
  M --> A[Trade Models Active / Tổng hợp]
  M --> B[Bridge roster]
  B --> L[Live + Parity]
  B --> Hist[Test lịch sử cùng EA]
  C -.->|không EA| L
""",
      language="text",
    )

  # ── 7. Limitations ─────────────────────────────────────────────
  st.markdown("## 7. Hạn chế & còn thiếu")
  st.markdown(
    f"""
### Đã khớp tài liệu gần đây
- Paper Monitor gỡ khỏi nav; Active không sync Bridge; Archive prune roster; id ma có nút dọn.

### Hạn chế sản phẩm (còn đúng)
| Hạng mục | Chi tiết |
|----------|----------|
| Một desk = một pair/TF | App này: **{d['pair_label']} {d['tf']}** — không multi-pair trong một process |
| Intrabar | Thứ tự chạm SL/TP trong bar có thể khác live |
| RoR | Ước lượng, không Monte Carlo đầy đủ |
| Nguồn giá | Chỉ ForgeBridge/XM MT5 (không feed ngoài) |
| Bridge phụ thuộc EA+service | Cùng lúc; Wine/SSL login có thể fail trên Linux Docker |
| Multi-model | Cần tài khoản **hedging**; risk ≈ N × Risk% nếu mở đồng thời |
| Sim fills ≠ Live | Test lịch sử / Compare FILLED không phải lệnh MT5 (broker không nhận giá quá khứ) |

### Còn thiếu / dễ gây hiểu nhầm (backlog)
| Hạng mục | Hiện trạng |
|----------|------------|
| Candidates / Live-ok gate trên Bridge | Multiselect vẫn = mọi model **live** (kể cả High-DD / Grid-only) — chưa lọc Candidates |
| Đổi tên module `paper_*` | Giữ tên legacy trong code; UI/docs gọi **sim fills** |
| Auto thêm Bridge khi Restore | Cố ý không — phải chọn roster tay |
| Báo cáo “Best 3m” cũ | Remine theo model trong roster, không hardcode Best 3m |
"""
  )

  # ── 8. FAQ ─────────────────────────────────────────────────────
  st.markdown("## 8. FAQ")
  st.markdown(
    f"""
**Q: 60% WR có Live được không?**  
A: Sau Health OOS + spread + **Parity** khớp kỳ vọng; KB OFF vẫn profitable; Compare trước nếu cần. Micro lot.

**Q: Active đổi rồi Live có đổi không?**  
A: Không. Chỉ đổi roster trên **MT5 Bridge** (Stop trước nếu đang chạy).

**Q: App tự optimize mỗi tuần?**  
A: Remine strategy theo roster khi Live chạy. **Không** tự Grid / tạo model.

**Q: Archive khác Xóa?**  
A: Archive giữ artifact + gỡ Bridge. Xóa cứng mất report. Restore không auto-add Bridge.

**Q: Id ma?**  
A: Id trong config nhưng model đã Archive/xóa → Dọn roster.

**Q: Compare có tín hiệu = MT5 vào lệnh?**  
A: Chỉ khi Live + EA chạy đúng bar đóng. Sim fills ≠ Live.

**Q: Còn `PaperBook` nghĩa là còn Paper Monitor?**  
A: Không — helper sim fills. Nav Paper Monitor đã gỡ.

**Q: MT4?**  
A: Không. Chỉ MT5 `{d['ea_live']}.mq5`.

**Q: Loss guard?**  
A: Dừng service nếu lệnh **auto** thua liên tiếp đạt ngưỡng ngày/tuần. Mặc định ≈ ⌊\\|Max DD\\|⌋+1. Start lại xóa cờ.

**Q: Đổi mining preset ở Cài đặt có đổi Live?**  
A: Không. Grid → model mới → thêm Bridge roster.

**Q: Log App↔EA?**  
A: MT5 Bridge → Nhật ký giao tiếp, hoặc `mt5/{d['bridge_live']}/comm_log.jsonl`.
"""
  )

  # ── Glossary last (reference) ──────────────────────────────────
  st.divider()
  from gui.glossary import render_glossary_guide
  render_glossary_guide()
