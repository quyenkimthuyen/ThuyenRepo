from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.research.analyze import analyze_period
from backend.research.label_scan import auto_label_period, label_status
from backend.research.optimize import optimize_period
from backend.core.folds import get_fold


def test_fold_config_valid():
    fold = get_fold("fold_a")
    assert fold["label_period"] == "train_2022"
    assert fold["optimize_period"] == "bt_2023"
    assert fold["final_test_period"] == "bt_2024"


def test_label_status_train_2022():
    status = label_status("train_2022")
    assert status["label_period"] == "train_2022"
    assert "target" in status


def test_auto_label_adds_setups():
    before = label_status("train_2022")["count"]
    result = auto_label_period("train_2022", max_add=5)
    assert result["added"] <= 5
    after = label_status("train_2022")["count"]
    assert after >= before


def test_analyze_period_structure():
    auto_label_period("train_2022", max_add=3)
    report = analyze_period("train_2022")
    assert report["status"] == "ok"
    assert "alignment" in report
    assert "recommendations" in report
    assert "by_setup" in report


def test_optimize_bt_2023():
    result = optimize_period("bt_2023", method="greedy", save_best=False)
    assert result["status"] == "ok"
    assert result["optimize_period"] == "bt_2023"
    assert "best_params" in result


def test_backtest_final_only_api(client: TestClient):
    r = client.post("/api/backtest", params={"period": "bt_2023"})
    assert r.status_code == 400
    r2 = client.post("/api/backtest/explore", params={"period": "bt_2023"})
    assert r2.status_code == 200


def test_fold_label_status_api(client: TestClient):
    r = client.post("/api/fold/fold_a/label_status")
    assert r.status_code == 200
    assert r.json()["label_period"] == "train_2022"


def test_html_report(client: TestClient):
    r = client.get("/api/backtest/report", params={"period": "bt_2024"})
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "Backtest" in r.text
