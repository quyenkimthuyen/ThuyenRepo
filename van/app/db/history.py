"""Lưu lịch sử chấm bài vào SQLite."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from app.config import DB_PATH


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS grade_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            question_type TEXT NOT NULL,
            total REAL NOT NULL,
            max_score REAL NOT NULL,
            payload TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mock_exam_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            exam_id TEXT NOT NULL,
            province_id TEXT,
            total REAL NOT NULL,
            max_score REAL NOT NULL,
            payload TEXT NOT NULL
        )
        """
    )
    conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    try:
        yield conn
    finally:
        conn.close()


def save_grade(*, question_type: str, result: dict[str, Any]) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO grade_history (created_at, question_type, total, max_score, payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                question_type,
                float(result.get("total", 0)),
                float(result.get("max_score", 0)),
                json.dumps(result, ensure_ascii=False),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_history(limit: int = 50) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, question_type, total, max_score, payload
            FROM grade_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    items = []
    for row in rows:
        payload = json.loads(row["payload"])
        items.append(
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "question_type": row["question_type"],
                "total": row["total"],
                "max_score": row["max_score"],
                "summary": (payload.get("weaknesses") or [""])[0][:120],
            }
        )
    return items


def get_stats() -> dict[str, Any]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT question_type,
                   COUNT(*) AS cnt,
                   AVG(total) AS avg_total,
                   AVG(max_score) AS avg_max
            FROM grade_history
            GROUP BY question_type
            """
        ).fetchall()
    by_type = {}
    total = 0
    for row in rows:
        cnt = int(row["cnt"])
        total += cnt
        avg_pct = (float(row["avg_total"]) / float(row["avg_max"]) * 100) if row["avg_max"] else 0
        by_type[row["question_type"]] = {
            "count": cnt,
            "avg_score": round(float(row["avg_total"]), 2),
            "avg_percent": round(avg_pct, 1),
        }
    return {"total_attempts": total, "by_type": by_type}


def save_mock_exam(result: dict[str, Any]) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO mock_exam_history (created_at, exam_id, province_id, total, max_score, payload)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                result.get("exam_id", ""),
                result.get("province_id", ""),
                float(result.get("total", 0)),
                float(result.get("max_score", 10)),
                json.dumps(result, ensure_ascii=False),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_mock_exams(limit: int = 20) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, exam_id, province_id, total, max_score
            FROM mock_exam_history ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
