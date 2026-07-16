# EUR/USD H1 — Self-Learning Trading System v4

## Hai chế độ chạy

### 1. Backtest một lần (v3)
```bash
python run_backtest.py
```
Walk-forward thông thường, không tích lũy kinh nghiệm.

### 2. Self-Learning — **khuyến nghị** (v4)
```bash
python run_learning.py              # 5 epoch
python run_learning.py --epochs 10  # 10 epoch
python run_learning.py --reset      # bắt đầu lại từ đầu
```

## Cách hoạt động

```
Epoch 1: Mine chiến lược → Walk-forward OOS → Ghi nhận rule thắng/thua
         ↓
Epoch 2: Khởi đầu từ genomes tốt + đột biến → Rules có weight cao hơn
         ML train thêm trên experience tích lũy
         ↓
Epoch N: Hệ thống ngày càng tinh chỉnh
```

**3 lớp học:**
| Lớp | Cơ chế | Lưu tại |
|-----|--------|---------|
| Rule Memory | Rule nào giúp thắng → weight tăng | `learning/knowledge.json` |
| Genome Evolution | Chiến lược tốt → đột biến/lai ghép | `genomes[]` |
| ML Experience | Feature → outcome tích lũy | `ml_experience[]` |

## Files

```
run_learning.py      # App chính — multi-epoch self-learning
knowledge_base.py    # Bộ nhớ lâu dài
evolution.py         # Đột biến / lai ghép genomes
meta_learner.py      # Optimize có nhớ
run_backtest.py      # Backtest đơn (v3)
```

## Lưu ý

- Mỗi epoch chạy full walk-forward (~2-7 phút/epoch)
- Knowledge **persist** giữa các lần chạy — chạy lại `run_learning.py` sẽ tiếp tục học
- Epoch sau thường tốt hơn epoch 1 vì có genomes + rule stats
