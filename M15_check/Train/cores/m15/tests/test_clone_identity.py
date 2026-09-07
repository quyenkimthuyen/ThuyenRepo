"""Clone folder identity — copied Train trees must not share M15 ports/bridges."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from clone_identity import (  # noqa: E402
  clone_port_offset,
  clone_slug,
  overlay_desk_identity,
)


def test_canonical_folders_have_empty_slug():
  assert clone_slug("M15") == ""
  assert clone_slug("LiveCheck2") == ""
  assert clone_port_offset("") == 0


def test_copy_folder_gets_stable_unique_offset():
  assert clone_slug("M15_check") == "check"
  assert clone_slug("M15_bk") == "bk"
  off_check = clone_port_offset("check")
  off_bk = clone_port_offset("bk")
  assert off_check != 0
  assert off_bk != 0
  assert off_check != off_bk
  assert off_check % 100 == 0
  assert abs(off_check) != 20


def test_overlay_unique_ports_and_bridge(tmp_path):
  train = tmp_path / "M15_check" / "Train"
  train.mkdir(parents=True)
  cfg = overlay_desk_identity(
    {
      "id": "e21",
      "port": 8911,
      "chart_port": 9975,
      "bridge_subdir": "bridge_lc2_e21",
      "bridge_sim_subdir": "bridge_lc2_e21_sim",
      "instance_id": "LC2E21",
      "magic": 20281021,
      "sim_magic": 20282021,
    },
    train_root=train,
  )
  assert cfg["clone_slug"] == "check"
  assert cfg["port"] != 8911
  assert cfg["chart_port"] != 9975
  assert cfg["bridge_subdir"] == "bridge_lc2_e21_check"
  assert cfg["instance_id"] == "LC2E21CHECK"
  assert cfg["magic"] != 20281021
  assert cfg["sim_chart_port"] != 10086


def test_overlay_does_not_double_suffix(tmp_path):
  train = tmp_path / "M15_check" / "Train"
  train.mkdir(parents=True)
  once = overlay_desk_identity(
    {"bridge_subdir": "bridge_lc2_e21", "instance_id": "LC2E21", "port": 8911},
    train_root=train,
  )
  twice = overlay_desk_identity(once, train_root=train)
  assert twice["bridge_subdir"] == once["bridge_subdir"]
  assert twice["instance_id"] == once["instance_id"]
  assert twice["port"] == once["port"]


def test_this_copy_load_desk_differs_from_m15_template():
  from desk_context import load_desk

  cfg = load_desk("e21")
  assert cfg["clone_slug"] == "check"
  assert cfg["port"] != 8911
  assert cfg["bridge_subdir"] == "bridge_lc2_e21_check"
  assert cfg["instance_id"] == "LC2E21CHECK"
  dumped = json.dumps(cfg)
  assert "M15_check" in str(cfg["runtime_root"]).replace("\\", "/")
  assert cfg["port"] != 8911
  assert str(cfg["port"]) in dumped
