EdgeMiner Live debug logs (for support / AI diagnosis).
Traders normally ignore this folder.
Retention: 14 days. Env LIVE_DEBUG_RETENTION_DAYS to change.
Each line = JSON event (decision, fill, ea_sync, error, start/stop…).
Lifecycle: bridge_start / worker_spawn / worker_start / worker_exit / worker_kill / bridge_start_done / bridge_stop.
Start path payload includes preflight_mode (reuse|fast|full|skip|none), preflight_sec, duration_sec, books.
