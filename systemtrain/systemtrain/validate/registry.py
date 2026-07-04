from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from systemtrain.strategy.dsl import StrategyGene
from systemtrain.validate.oos_gate import OOSVerdict


class StrategyRegistry:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS strategies (
                    id TEXT PRIMARY KEY,
                    rank_order INTEGER,
                    created_at TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    gene_json TEXT NOT NULL,
                    train_metrics_json TEXT,
                    oos_metrics_json TEXT,
                    wf_summary_json TEXT,
                    monte_carlo_json TEXT,
                    verdict_passed INTEGER,
                    verdict_reasons TEXT,
                    rank_score REAL
                )
                """
            )
            # migrate older DB without rank columns
            cols = {row[1] for row in conn.execute("PRAGMA table_info(strategies)")}
            if "rank_order" not in cols:
                conn.execute("ALTER TABLE strategies ADD COLUMN rank_order INTEGER")
            if "rank_score" not in cols:
                conn.execute("ALTER TABLE strategies ADD COLUMN rank_score REAL")

    def save(
        self,
        gene: StrategyGene,
        symbol: str,
        timeframe: str,
        train_metrics: dict[str, Any],
        oos_metrics: dict[str, Any],
        wf_summary: dict[str, Any],
        monte_carlo: dict[str, Any],
        verdict: OOSVerdict,
        rank_order: int = 0,
        rank_score: float = 0.0,
    ) -> str:
        strategy_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO strategies (
                    id, rank_order, created_at, symbol, timeframe, gene_json,
                    train_metrics_json, oos_metrics_json, wf_summary_json,
                    monte_carlo_json, verdict_passed, verdict_reasons, rank_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    strategy_id,
                    rank_order,
                    now,
                    symbol,
                    timeframe,
                    json.dumps(gene.to_dict()),
                    json.dumps(train_metrics),
                    json.dumps(oos_metrics),
                    json.dumps(wf_summary, default=str),
                    json.dumps(monte_carlo),
                    1 if verdict.passed else 0,
                    json.dumps(verdict.reasons),
                    rank_score,
                ),
            )
        return strategy_id

    def replace_top_strategies(self, records: list[dict[str, Any]]) -> None:
        """Keep only the provided strategies (max 3), wipe previous entries."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM strategies")
        for i, rec in enumerate(records, 1):
            self.save(
                gene=rec["gene"],
                symbol=rec["symbol"],
                timeframe=rec["timeframe"],
                train_metrics=rec["train_metrics"],
                oos_metrics=rec["oos_metrics"],
                wf_summary=rec.get("wf_summary", {}),
                monte_carlo=rec.get("monte_carlo", {}),
                verdict=rec["verdict"],
                rank_order=i,
                rank_score=rec.get("rank_score", 0.0),
            )

    def list_strategies(self, passed_only: bool = False) -> list[dict[str, Any]]:
        query = "SELECT * FROM strategies"
        if passed_only:
            query += " WHERE verdict_passed = 1"
        query += " ORDER BY rank_order ASC, created_at DESC"
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query).fetchall()
        return [dict(row) for row in rows]

    def export_report(self, output_dir: str | Path) -> Path:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        strategies = self.list_strategies()
        report_path = output_dir / "registry_report.json"
        with report_path.open("w") as f:
            json.dump(strategies, f, indent=2, default=str)
        return report_path
