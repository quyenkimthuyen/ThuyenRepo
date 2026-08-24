"""BUG-06: cancel/stop must not drop _thread while worker is still alive."""
from __future__ import annotations

import threading
import time

import gui.grid_search_background as grid_bg
import gui.long_task_background as long_bg


def test_stop_grid_search_keeps_thread_if_still_alive(monkeypatch):
  started = threading.Event()
  release = threading.Event()

  def _slow():
    started.set()
    release.wait(timeout=5)

  t = threading.Thread(target=_slow, name="grid-test-worker", daemon=True)
  monkeypatch.setattr(grid_bg, "_thread", t)
  t.start()
  assert started.wait(timeout=2)

  # Simulate join timeout: join returns but thread still alive.
  monkeypatch.setattr(t, "join", lambda timeout=None: None)
  grid_bg.stop_grid_search(wait=True)

  assert grid_bg._thread is t
  assert t.is_alive()
  release.set()
  t.join(timeout=2)


def test_cancel_task_keeps_thread_if_still_alive(monkeypatch):
  started = threading.Event()
  release = threading.Event()

  def _slow():
    started.set()
    release.wait(timeout=5)

  t = threading.Thread(target=_slow, name="long-test-worker", daemon=True)
  monkeypatch.setattr(long_bg, "_thread", t)
  t.start()
  assert started.wait(timeout=2)

  monkeypatch.setattr(t, "join", lambda timeout=None: None)
  long_bg.cancel_task(wait=True)

  assert long_bg._thread is t
  assert t.is_alive()
  release.set()
  t.join(timeout=2)


def test_stop_grid_search_clears_thread_when_dead(monkeypatch):
  t = threading.Thread(target=lambda: None, daemon=True)
  t.start()
  t.join(timeout=2)
  monkeypatch.setattr(grid_bg, "_thread", t)
  grid_bg.stop_grid_search(wait=True)
  assert grid_bg._thread is None


def test_stop_sim_worker_keeps_thread_if_still_alive(monkeypatch):
  """R-03: sim stop must not orphan an alive worker reference."""
  import mt5_bridge.background as bridge_bg

  started = threading.Event()
  release = threading.Event()

  def _slow():
    started.set()
    release.wait(timeout=5)

  t = threading.Thread(target=_slow, name="sim-test-worker", daemon=True)
  monkeypatch.setattr(bridge_bg, "_sim_thread", t)
  monkeypatch.setattr(bridge_bg, "_sim_bridge_thread", None)
  monkeypatch.setattr(bridge_bg, "_read_sim_pid", lambda: None)
  monkeypatch.setattr(bridge_bg, "_clear_sim_pid", lambda: None)
  monkeypatch.setattr(bridge_bg, "_pid_alive", lambda _pid: False)

  def _noop_stop_control(_dir=None):
    return None

  monkeypatch.setattr(
    "mt5_bridge.ea_simulator.stop_history_feed_control",
    _noop_stop_control,
    raising=False,
  )
  monkeypatch.setattr(
    "mt5_bridge.ea_simulator.write_sim_state",
    lambda *_a, **_k: None,
    raising=False,
  )

  t.start()
  assert started.wait(timeout=2)
  monkeypatch.setattr(t, "join", lambda timeout=None: None)
  bridge_bg.stop_sim_worker()

  assert bridge_bg._sim_thread is t
  assert t.is_alive()
  release.set()
  t.join(timeout=2)


def test_is_thread_running_true_while_stop_flag_set(monkeypatch):
  """R-05: stop flag must not hide an alive live worker."""
  import mt5_bridge.background as bridge_bg

  started = threading.Event()
  release = threading.Event()

  def _slow():
    started.set()
    release.wait(timeout=5)

  t = threading.Thread(target=_slow, name="live-test-worker", daemon=True)
  monkeypatch.setattr(bridge_bg, "_thread", t)
  bridge_bg._stop.set()
  t.start()
  assert started.wait(timeout=2)
  assert bridge_bg.is_thread_running() is True
  release.set()
  t.join(timeout=2)


def test_start_thread_worker_waits_for_stopping_thread(monkeypatch):
  """R-05: must not spawn a second worker while the first is still dying."""
  import mt5_bridge.background as bridge_bg

  started = threading.Event()
  release = threading.Event()

  def _slow():
    started.set()
    release.wait(timeout=5)

  t = threading.Thread(target=_slow, name="live-dying-worker", daemon=True)
  monkeypatch.setattr(bridge_bg, "_thread", t)
  bridge_bg._stop.set()
  t.start()
  assert started.wait(timeout=2)
  # join times out → start must refuse
  monkeypatch.setattr(t, "join", lambda timeout=None: None)
  monkeypatch.setattr(bridge_bg, "is_process_running", lambda: False)
  assert bridge_bg.start_thread_worker() is False
  assert bridge_bg._thread is t
  release.set()
  t.join(timeout=2)
