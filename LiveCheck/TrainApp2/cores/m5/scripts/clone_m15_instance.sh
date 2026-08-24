#!/usr/bin/env bash
# Clone EdgeMinerM15 into an isolated sibling instance.
#
# Spec: <Version><Offset>  e.g. B4
#   Full spec → naming (repo / INSTANCE_ID / EA / bridge folder)
#   Offset    → ports = M15 defaults + offset*10  (slot; avoids B4/B5 overlap)
#
# Magic uses a reserved block (not base+offset) to avoid H1/sim collisions:
#   live = 20261000 + offset,  sim = 20262000 + offset
#
# Example:
#   ./scripts/clone_m15_instance.sh B4
#   ./scripts/clone_m15_instance.sh B4 --dry-run
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: clone_m15_instance.sh <Version><Offset> [--dry-run] [--force] [--parent DIR]

  Spec examples:  B4   Beta2   X10
    Version+Offset together name the repo (B4 → EdgeMinerM15B4)
    Offset = slot ≥ 1; ports = M15 default + offset*10

  Options:
    --dry-run     Print identity matrix only; do not copy
    --force       Replace existing target directory
    --parent DIR  Parent for the new repo (default: sibling of this repo)

Derived (example B4):
  repo            EdgeMinerM15B4
  INSTANCE_ID     M15B4
  bridge          bridge_m15b4 / bridge_sim_m15b4
  EA              ForgeBridgeM5E31B4 / ForgeBridgeM5E31B4Sim
  app/bridge/paper/sim/compare ports   8541 / 8805 / 8806 / 8916 / 9026
  magic live/sim  20261004 / 20262004

Offset must be unique across clones (same offset ⇒ same ports).
Stride *10 avoids paper(N) colliding with bridge(N+1).
EOF
}

SPEC=""
DRY_RUN=0
FORCE=0
PARENT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --parent)
      PARENT="${2:?--parent requires a directory}"
      shift 2
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      if [[ -n "$SPEC" ]]; then
        echo "Unexpected argument: $1" >&2
        usage >&2
        exit 2
      fi
      SPEC="$1"
      shift
      ;;
  esac
done

if [[ -z "$SPEC" ]]; then
  usage >&2
  exit 2
fi

if [[ ! "$SPEC" =~ ^([A-Za-z]+)([1-9][0-9]*)$ ]]; then
  echo "Invalid spec '$SPEC'. Expected <Version><Offset> e.g. B3" >&2
  exit 2
fi

VERSION="${BASH_REMATCH[1]}"
OFFSET="${BASH_REMATCH[2]}"
VERSION_UPPER="${VERSION^^}"
VERSION_LOWER="${VERSION,,}"
SPEC_UPPER="${VERSION_UPPER}${OFFSET}"
SPEC_LOWER="${VERSION_LOWER}${OFFSET}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if [[ -z "$PARENT" ]]; then
  PARENT="$(cd "$SRC_ROOT/.." && pwd)"
fi
PARENT="$(cd "$PARENT" && pwd)"

# Full spec in names so B4 and B5 are different folders/IDs.
REPO_NAME="EdgeMinerM15${SPEC_UPPER}"
DST_ROOT="$PARENT/$REPO_NAME"
INSTANCE_ID="M15${SPEC_UPPER}"
BRIDGE_LIVE="bridge_m15${SPEC_LOWER}"
BRIDGE_SIM="bridge_sim_m15${SPEC_LOWER}"
EA_LIVE="ForgeBridge${INSTANCE_ID}"
EA_SIM="${EA_LIVE}Sim"

# Slot stride 10: consecutive offsets never share a port.
PORT_SLOT=$((OFFSET * 10))
APP_PORT=$((8501 + PORT_SLOT))
BRIDGE_PORT=$((8765 + PORT_SLOT))
PAPER_PORT=$((8766 + PORT_SLOT))
SIM_PORT=$((8876 + PORT_SLOT))
# Compare sits +110 above Sim base so it never equals next clone's Sim
# (Sim_N+1 = 8876+(N+1)*10 = 8886+N*10 — old Compare formula collided).
COMPARE_PORT=$((8986 + PORT_SLOT))
MAGIC_LIVE=$((20261000 + OFFSET))
MAGIC_SIM=$((20262000 + OFFSET))

# Known ports already taken by stock M15 / H1.
RESERVED_PORTS=(8501 8502 8765 8766 8876 8886 8986 8865 8866 8877)
RESERVED_MAGICS=(20260724 20260725 20260726 20260727)

print_matrix() {
  cat <<EOF
Clone plan for spec ${SPEC_UPPER}
  source          $SRC_ROOT
  target          $DST_ROOT
  INSTANCE_ID     $INSTANCE_ID
  bridge live/sim $BRIDGE_LIVE / $BRIDGE_SIM
  EA live/sim     $EA_LIVE / $EA_SIM
  app port        $APP_PORT   (= 8501 + ${OFFSET}*10)
  bridge monitor  $BRIDGE_PORT   (= 8765 + ${OFFSET}*10)
  paper monitor   $PAPER_PORT   (= 8766 + ${OFFSET}*10)
  sim monitor     $SIM_PORT   (= 8876 + ${OFFSET}*10)
  compare monitor $COMPARE_PORT   (= 8986 + ${OFFSET}*10)
  magic live/sim  $MAGIC_LIVE / $MAGIC_SIM
EOF
}

port_in_reserved() {
  local p="$1" r
  for r in "${RESERVED_PORTS[@]}"; do
    [[ "$p" == "$r" ]] && return 0
  done
  return 1
}

magic_in_reserved() {
  local m="$1" r
  for r in "${RESERVED_MAGICS[@]}"; do
    [[ "$m" == "$r" ]] && return 0
  done
  return 1
}

check_conflicts() {
  local bad=0 p
  for p in "$APP_PORT" "$BRIDGE_PORT" "$PAPER_PORT" "$SIM_PORT" "$COMPARE_PORT"; do
    if port_in_reserved "$p"; then
      echo "Conflict: port $p is reserved (M15/H1). Choose another offset." >&2
      bad=1
    fi
  done
  if magic_in_reserved "$MAGIC_LIVE" || magic_in_reserved "$MAGIC_SIM"; then
    echo "Conflict: magic collides with M15/H1 reserved block." >&2
    bad=1
  fi
  if [[ "$SRC_ROOT" == "$DST_ROOT" ]]; then
    echo "Conflict: target equals source." >&2
    bad=1
  fi
  if [[ -e "$DST_ROOT" && "$FORCE" -ne 1 && "$DRY_RUN" -ne 1 ]]; then
    echo "Target exists: $DST_ROOT (pass --force to replace)." >&2
    bad=1
  fi
  # Sibling clones: same offset ⇒ same ports.
  local sibling
  for sibling in "$PARENT"/EdgeMinerM15*; do
    [[ -d "$sibling" ]] || continue
    [[ "$(cd "$sibling" && pwd)" == "$SRC_ROOT" ]] && continue
    [[ "$(cd "$sibling" && pwd)" == "$DST_ROOT" ]] && continue
    local sib_proto="$sibling/mt5_bridge/protocol.py"
    local sib_mon="$sibling/mt5_bridge/live_monitor_server.py"
    local sib_paper="$sibling/paper_live_monitor_server.py"
    [[ -f "$sib_proto" && -f "$sib_mon" ]] || continue
    local sib_magic sib_app_hint
    sib_magic="$(grep -E '^DEFAULT_MAGIC = ' "$sib_proto" | head -1 | awk '{print $3}' || true)"
    if [[ "$sib_magic" == "$MAGIC_LIVE" ]]; then
      echo "Conflict: $sibling already uses magic $MAGIC_LIVE (same offset?)." >&2
      bad=1
    fi
    local sib_bridge_port
    sib_bridge_port="$(grep -E '^DEFAULT_MONITOR_PORT = ' "$sib_mon" | head -1 | awk '{print $3}' || true)"
    if [[ "$sib_bridge_port" == "$BRIDGE_PORT" ]]; then
      echo "Conflict: $sibling already uses bridge monitor $BRIDGE_PORT." >&2
      bad=1
    fi
    local sib_sim_port
    sib_sim_port="$(grep -E '^SIM_MONITOR_PORT = ' "$sib_mon" | head -1 | awk '{print $3}' || true)"
    if [[ "$sib_sim_port" == "$SIM_PORT" ]]; then
      echo "Conflict: $sibling already uses sim monitor $SIM_PORT." >&2
      bad=1
    fi
    local sib_compare_port
    sib_compare_port="$(grep -E '^COMPARE_MONITOR_PORT = ' "$sib_mon" | head -1 | awk '{print $3}' || true)"
    if [[ -n "$sib_compare_port" && "$sib_compare_port" == "$COMPARE_PORT" ]]; then
      echo "Conflict: $sibling already uses compare monitor $COMPARE_PORT." >&2
      bad=1
    fi
    if [[ -f "$sib_paper" ]]; then
      local sib_paper_port
      sib_paper_port="$(grep -E '^DEFAULT_PAPER_MONITOR_PORT = ' "$sib_paper" | head -1 | awk '{print $3}' || true)"
      if [[ "$sib_paper_port" == "$PAPER_PORT" ]]; then
        echo "Conflict: $sibling already uses paper monitor $PAPER_PORT." >&2
        bad=1
      fi
    fi
  done
  return "$bad"
}

print_matrix
if ! check_conflicts; then
  exit 1
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "(dry-run) no files written."
  exit 0
fi

# Avoid "getcwd failed" if shell cwd sits inside a tree we replace.
cd "$SRC_ROOT"

if [[ -e "$DST_ROOT" && "$FORCE" -eq 1 ]]; then
  echo "Removing existing $DST_ROOT ..."
  rm -rf "$DST_ROOT"
fi

echo "Copying $SRC_ROOT → $DST_ROOT ..."
mkdir -p "$DST_ROOT"
if command -v rsync >/dev/null 2>&1; then
  rsync -a \
    --exclude '.venv/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '.pytest_cache/' \
    --exclude 'results/*.pid' \
    --exclude 'results/*.log' \
    --exclude 'results/jobs/long_task_state.json' \
    --exclude 'mt5/bridge/*.json' \
    --exclude 'mt5/bridge/*.csv' \
    --exclude 'mt5/bridge_sim/*.json' \
    --exclude 'mt5/bridge_sim/*.csv' \
    --exclude 'C:\\Work\\*' \
    "$SRC_ROOT/" "$DST_ROOT/"
else
  # Trailing /. copies contents into DST (plain cp -a SRC DST nests SRC basename).
  cp -a "$SRC_ROOT"/. "$DST_ROOT"/
  rm -rf "$DST_ROOT/.venv"
  find "$DST_ROOT" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
  find "$DST_ROOT" -type d -name '.pytest_cache' -prune -exec rm -rf {} + 2>/dev/null || true
  rm -f "$DST_ROOT"/results/*.pid "$DST_ROOT"/results/*.log 2>/dev/null || true
  rm -f "$DST_ROOT"/results/jobs/long_task_state.json 2>/dev/null || true
fi

# Prefer a working interpreter (skip Windows Store python3 stubs).
run_python() {
  local cand
  for cand in \
    /c/Python314/python.exe \
    /c/Python313/python.exe \
    /c/Python312/python.exe \
    python3 \
    py \
    python
  do
    case "$cand" in
      py)
        if command -v py >/dev/null 2>&1 && py -3 -c "import sys" >/dev/null 2>&1; then
          py -3 "$@"
          return $?
        fi
        ;;
      *)
        if command -v "$cand" >/dev/null 2>&1 || [[ -x "$cand" ]]; then
          if "$cand" -c "import sys" >/dev/null 2>&1; then
            "$cand" "$@"
            return $?
          fi
        fi
        ;;
    esac
  done
  echo "No working Python found; cannot specialize clone." >&2
  exit 1
}
echo "Python probe OK"

# Rename bridge folders
if [[ -d "$DST_ROOT/mt5/bridge" ]]; then
  mv "$DST_ROOT/mt5/bridge" "$DST_ROOT/mt5/$BRIDGE_LIVE"
fi
if [[ -d "$DST_ROOT/mt5/bridge_sim" ]]; then
  mv "$DST_ROOT/mt5/bridge_sim" "$DST_ROOT/mt5/$BRIDGE_SIM"
fi
mkdir -p "$DST_ROOT/mt5/$BRIDGE_LIVE" "$DST_ROOT/mt5/$BRIDGE_SIM"

# Rename EA sources
if [[ -f "$DST_ROOT/mt5/Experts/ForgeBridgeM5E31.mq5" ]]; then
  mv "$DST_ROOT/mt5/Experts/ForgeBridgeM5E31.mq5" "$DST_ROOT/mt5/Experts/${EA_LIVE}.mq5"
fi
if [[ -f "$DST_ROOT/mt5/Experts/ForgeBridgeM5E31Sim.mq5" ]]; then
  mv "$DST_ROOT/mt5/Experts/ForgeBridgeM5E31Sim.mq5" "$DST_ROOT/mt5/Experts/${EA_SIM}.mq5"
fi

export CLONE_SRC_ROOT="$SRC_ROOT"
export CLONE_DST_ROOT="$DST_ROOT"
export CLONE_INSTANCE_ID="$INSTANCE_ID"
export CLONE_BRIDGE_LIVE="$BRIDGE_LIVE"
export CLONE_BRIDGE_SIM="$BRIDGE_SIM"
export CLONE_EA_LIVE="$EA_LIVE"
export CLONE_EA_SIM="$EA_SIM"
export CLONE_REPO_NAME="$REPO_NAME"
export CLONE_APP_PORT="$APP_PORT"
export CLONE_BRIDGE_PORT="$BRIDGE_PORT"
export CLONE_PAPER_PORT="$PAPER_PORT"
export CLONE_SIM_PORT="$SIM_PORT"
export CLONE_COMPARE_PORT="$COMPARE_PORT"
export CLONE_MAGIC_LIVE="$MAGIC_LIVE"
export CLONE_MAGIC_SIM="$MAGIC_SIM"
export CLONE_SPEC="${SPEC_UPPER}"
export CLONE_VERSION="$VERSION_UPPER"
export CLONE_OFFSET="$OFFSET"

run_python - <<'PY'
from __future__ import annotations

import os
import re
from pathlib import Path

root = Path(os.environ["CLONE_DST_ROOT"])
instance_id = os.environ["CLONE_INSTANCE_ID"]
bridge_live = os.environ["CLONE_BRIDGE_LIVE"]
bridge_sim = os.environ["CLONE_BRIDGE_SIM"]
ea_live = os.environ["CLONE_EA_LIVE"]
ea_sim = os.environ["CLONE_EA_SIM"]
repo_name = os.environ["CLONE_REPO_NAME"]
app_port = int(os.environ["CLONE_APP_PORT"])
bridge_port = int(os.environ["CLONE_BRIDGE_PORT"])
paper_port = int(os.environ["CLONE_PAPER_PORT"])
sim_port = int(os.environ["CLONE_SIM_PORT"])
compare_port = int(os.environ["CLONE_COMPARE_PORT"])
magic_live = int(os.environ["CLONE_MAGIC_LIVE"])
magic_sim = int(os.environ["CLONE_MAGIC_SIM"])
spec = os.environ["CLONE_SPEC"]
version = os.environ["CLONE_VERSION"]
offset = os.environ["CLONE_OFFSET"]


def replace_file(path: Path, patterns: list[tuple[str, str]], *, count: int = 0) -> None:
  if not path.exists():
    print(f"  skip missing {path.relative_to(root)}")
    return
  text = path.read_text(encoding="utf-8")
  original = text
  for pat, repl in patterns:
    text, n = re.subn(pat, repl, text, count=count, flags=re.MULTILINE)
    if n == 0 and pat.startswith("^"):
      # allow non-anchored retry already in list; just continue
      pass
  if text == original:
    print(f"  warn: no changes in {path.relative_to(root)}")
  else:
    path.write_text(text, encoding="utf-8")
    print(f"  patched {path.relative_to(root)}")


# protocol.py
replace_file(
  root / "mt5_bridge" / "protocol.py",
  [
    (r'^BRIDGE_DIR = ROOT / "mt5" / "bridge_m5e31"', f'BRIDGE_DIR = ROOT / "mt5" / "{bridge_live}"'),
    (r'^BRIDGE_SIM_DIR = ROOT / "mt5" / "bridge_sim_m5e31"', f'BRIDGE_SIM_DIR = ROOT / "mt5" / "{bridge_sim}"'),
    (r"^DEFAULT_MAGIC = \d+", f"DEFAULT_MAGIC = {magic_live}"),
    (r"^DEFAULT_SIM_MAGIC = \d+", f"DEFAULT_SIM_MAGIC = {magic_sim}"),
    (r'^INSTANCE_ID = "M5E31"', f'INSTANCE_ID = "{instance_id}"'),
  ],
)

# live monitor ports — match any current value (source may already be non-default)
replace_file(
  root / "mt5_bridge" / "live_monitor_server.py",
  [
    (r"^DEFAULT_MONITOR_PORT = \d+", f"DEFAULT_MONITOR_PORT = {bridge_port}"),
    (r"^SIM_MONITOR_PORT = \d+", f"SIM_MONITOR_PORT = {sim_port}"),
    (r"^COMPARE_MONITOR_PORT = \d+", f"COMPARE_MONITOR_PORT = {compare_port}"),
  ],
)

replace_file(
  root / "paper_live_monitor_server.py",
  [
    (r"^DEFAULT_PAPER_MONITOR_PORT = \d+", f"DEFAULT_PAPER_MONITOR_PORT = {paper_port}"),
  ],
)

replace_file(
  root / "scripts" / "run_app_linux.sh",
  [
    (r"^PORT=\d+", f"PORT={app_port}"),
    (r"default: \d+", f"default: {app_port}"),
  ],
)

replace_file(
  root / "scripts" / "run_app_windows.ps1",
  [
    (r"\[int\]\$Port = \d+", f"[int]$Port = {app_port}"),
  ],
)

replace_file(
  root / "scripts" / "paper_monitor_service.py",
  [
    (r"http://127\.0\.0\.1:\d+", f"http://127.0.0.1:{paper_port}"),
  ],
)

# deploy script — placeholder rename to avoid ForgeBridgeM5E31 prefix clobbering Sim
deploy = root / "scripts" / "deploy_xm_forgebridge.ps1"
if deploy.exists():
  text = deploy.read_text(encoding="utf-8")
  text = text.replace("ForgeBridgeM5E31Sim", "@@EA_SIM@@")
  text = text.replace("ForgeBridgeM5E31", "@@EA_LIVE@@")
  text = text.replace("@@EA_SIM@@", ea_sim)
  text = text.replace("@@EA_LIVE@@", ea_live)
  # Use str.replace (not re.sub): "\b" in replacement is a backspace escape for re.
  text = text.replace(
    '$ProjectBridge = Join-Path $RepoRoot "mt5\\bridge"',
    f'$ProjectBridge = Join-Path $RepoRoot "mt5\\{bridge_live}"',
  )
  text = text.replace(
    '$ProjectBridgeSim = Join-Path $RepoRoot "mt5\\bridge_sim"',
    f'$ProjectBridgeSim = Join-Path $RepoRoot "mt5\\{bridge_sim}"',
  )
  text = text.replace('$BridgeSubdirLive = "bridge_m5e31"', f'$BridgeSubdirLive = "{bridge_live}"')
  text = text.replace('$BridgeSubdirSim = "bridge_sim_m5e31"', f'$BridgeSubdirSim = "{bridge_sim}"')
  text = re.sub(r'\$EaNameLive = "[^"]+"', f'$EaNameLive = "{ea_live}"', text)
  text = re.sub(r'\$EaNameSim = "[^"]+"', f'$EaNameSim = "{ea_sim}"', text)
  text = text.replace('$EaFolder = "EdgeMinerM5E31"', f'$EaFolder = "{repo_name}"')
  text = re.sub(r"\$EaMagicLive = \d+", f"$EaMagicLive = {magic_live}", text)
  text = re.sub(r"\$EaMagicSim = \d+", f"$EaMagicSim = {magic_sim}", text)
  text = re.sub(r"--monitor-port \d+", f"--monitor-port {bridge_port}", text)
  # Keep ALL ForgeBridge* charts protected (stock + every sibling clone).
  # Listing only this clone's EA lets deploy steal B4 when attaching B5 (and vice versa).
  broad_family = r"name=ForgeBridge[A-Za-z0-9]*\b"
  broad_expert = r"(?s)<expert>\s*name=ForgeBridge[A-Za-z0-9]*\b.*?</expert>\s*"
  # Use lambdas: replacement strings must not contain \s/\b (re.sub escape rules).
  text, n_fam = re.subn(
    r"function Get-ForgeFamilyPattern \{.*?return '[^']+'.*?\}",
    lambda _m: f"function Get-ForgeFamilyPattern {{\n  return '{broad_family}'\n}}",
    text,
    count=1,
    flags=re.DOTALL,
  )
  text, n_exp = re.subn(
    r"\$forgeExpertPattern = '[^']*'",
    lambda _m: f"$forgeExpertPattern = '{broad_expert}'",
    text,
  )
  if n_fam == 0:
    print("  warn: Get-ForgeFamilyPattern not rewritten")
  if n_exp == 0:
    print("  warn: forgeExpertPattern not rewritten")
  deploy.write_text(text, encoding="utf-8")
  print("  patched scripts/deploy_xm_forgebridge.ps1")
else:
  print("  skip missing scripts/deploy_xm_forgebridge.ps1")

# EA sources — use placeholders so ForgeBridgeM5E31 is not a prefix of the new Sim name.
for ea_path, subdir, magic, label in (
  (root / "mt5" / "Experts" / f"{ea_live}.mq5", bridge_live, magic_live, "live"),
  (root / "mt5" / "Experts" / f"{ea_sim}.mq5", bridge_sim, magic_sim, "sim"),
):
  if not ea_path.exists():
    print(f"  missing EA {ea_path.name}")
    continue
  text = ea_path.read_text(encoding="utf-8")
  text = text.replace("ForgeBridgeM5E31Sim", "@@EA_SIM@@")
  text = text.replace("ForgeBridgeM5E31", "@@EA_LIVE@@")
  text = text.replace("@@EA_SIM@@", ea_sim)
  text = text.replace("@@EA_LIVE@@", ea_live)
  text = re.sub(
    r'const string INSTANCE_ID = "M5E31";',
    f'const string INSTANCE_ID = "{instance_id}";',
    text,
  )
  if label == "live":
    text = re.sub(
      r'input string InpBridgeSubdir\s*=\s*"bridge";',
      f'input string InpBridgeSubdir   = "{subdir}";',
      text,
    )
    text = re.sub(
      r"input ulong\s+InpMagic\s*=\s*20260724;",
      f"input ulong  InpMagic          = {magic};",
      text,
    )
    text = re.sub(
      rf"{re.escape(ea_live)}\.mq5 — EdgeMiner M15 \(magic 20260724, bridge\)",
      f"{ea_live}.mq5 — EdgeMiner {instance_id} (magic {magic}, {subdir})",
      text,
    )
  else:
    text = re.sub(
      r'input string InpBridgeSubdir\s*=\s*"bridge_sim";',
      f'input string InpBridgeSubdir   = "{subdir}";',
      text,
    )
    text = re.sub(
      r"input ulong\s+InpMagic\s*=\s*20260726;",
      f"input ulong  InpMagic          = {magic};",
      text,
    )
    text = re.sub(
      rf"{re.escape(ea_sim)}\.mq5 — EdgeMiner M15 SIM \(magic 20260726, bridge_sim\)",
      f"{ea_sim}.mq5 — EdgeMiner {instance_id} SIM (magic {magic}, {subdir})",
      text,
    )
  ea_path.write_text(text, encoding="utf-8")
  print(f"  patched mt5/Experts/{ea_path.name}")

# README identity banner
readme = root / "README.md"
if readme.exists():
  text = readme.read_text(encoding="utf-8")
  banner = (
    f"> **Clone `{spec}`** từ EdgeMinerM15 — instance `{instance_id}` · "
    f"app/bridge/paper/sim/compare `{app_port}/{bridge_port}/{paper_port}/{sim_port}/{compare_port}` · "
    f"folder `{bridge_live}` · magic `{magic_live}`.\n\n"
  )
  text = re.sub(
    r"M15 dùng app/Bridge/Paper `8501/8765/8766`, folder `bridge`, Magic `20260724`\.",
    f"{instance_id} dùng app/Bridge/Paper/Sim/Compare "
    f"`{app_port}/{bridge_port}/{paper_port}/{sim_port}/{compare_port}`, "
    f"folder `{bridge_live}`, Magic `{magic_live}`.",
    text,
    count=1,
  )
  text = re.sub(
    r"App mặc định mở tại `http://127\.0\.0\.1:8501`\.",
    f"App mặc định mở tại `http://127.0.0.1:{app_port}`.",
    text,
    count=1,
  )
  if not text.startswith(banner) and f"Clone `{spec}`" not in text[:400]:
    text = banner + text
  readme.write_text(text, encoding="utf-8")
  print("  patched README.md")

# Write identity manifest
manifest = root / "CLONE_IDENTITY.md"
manifest.write_text(
  f"""# Clone identity `{spec}`

| Field | Value |
|-------|-------|
| Spec | `{spec}` (version `{version}`, offset `{offset}`) |
| Repo | `{repo_name}` |
| INSTANCE_ID | `{instance_id}` |
| Bridge live / sim | `{bridge_live}` / `{bridge_sim}` |
| EA live / sim | `{ea_live}` / `{ea_sim}` |
| App port | `{app_port}` (= 8501 + {offset}*10) |
| Bridge monitor | `{bridge_port}` (= 8765 + {offset}*10) |
| Paper monitor | `{paper_port}` (= 8766 + {offset}*10) |
| Sim monitor | `{sim_port}` (= 8876 + {offset}*10) |
| Compare monitor | `{compare_port}` (= 8986 + {offset}*10) |
| Magic live / sim | `{magic_live}` / `{magic_sim}` |

## Run

```bash
cd {repo_name}
python -m venv .venv && .venv/bin/pip install -r requirements.txt
./scripts/run_app_linux.sh Start
```

Offset must stay unique vs other clones (ports derive only from offset).
""",
  encoding="utf-8",
)
print("  wrote CLONE_IDENTITY.md")

# Fix absolute paths copied from source so clones never point at EdgeMinerM15.
import json
src_root = Path(os.environ["CLONE_SRC_ROOT"]).resolve()

def _rewrite_str(value: str) -> str:
  if not isinstance(value, str):
    return value
  if repo_name in value:
    return value
  src_s = str(src_root)
  if value == src_s:
    return str(root)
  if value.startswith(src_s + "/"):
    return str(root / Path(value).relative_to(src_root))
  if "EdgeMinerM15B" in value:
    return value
  norm = value.replace("\\", "/")
  needle = "C:/Work/ThuyenRepo/EdgeMinerM15/"
  if norm.startswith(needle):
    return str(root / norm[len(needle):])
  return value

def _rewrite_obj(obj):
  if isinstance(obj, dict):
    return {k: _rewrite_obj(v) for k, v in obj.items()}
  if isinstance(obj, list):
    return [_rewrite_obj(v) for v in obj]
  if isinstance(obj, str):
    return _rewrite_str(obj)
  return obj

for rel in (
  "results/mt5_bridge_config.json",
  "results/mt5_bridge_sim_state.json",
  "results/paper_monitor_config.json",
  "results/trade_models.json",
  "results/active_workspace.json",
):
  path = root / rel
  if not path.exists():
    continue
  data = json.loads(path.read_text(encoding="utf-8-sig"))
  data = _rewrite_obj(data)
  if path.name == "mt5_bridge_config.json":
    data["bridge_dir"] = str(root / "mt5" / bridge_live)
  if path.name == "mt5_bridge_sim_state.json":
    data["bridge_dir"] = str(root / "mt5" / bridge_sim)
  path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  print(f"  rewritten paths in {rel}")
PY

# Soften dual-runtime test expectations for this clone (local identity).
if [[ -f "$DST_ROOT/tests/test_dual_runtime_contract.py" ]]; then
  run_python - <<'PY'
from pathlib import Path
import os, re
p = Path(os.environ["CLONE_DST_ROOT"]) / "tests" / "test_dual_runtime_contract.py"
text = p.read_text(encoding="utf-8")
magic = os.environ["CLONE_MAGIC_LIVE"]
magic_sim = os.environ["CLONE_MAGIC_SIM"]
instance = os.environ["CLONE_INSTANCE_ID"]
bridge = os.environ["CLONE_BRIDGE_LIVE"]
bridge_sim = os.environ["CLONE_BRIDGE_SIM"]
ea = os.environ["CLONE_EA_LIVE"]
ea_sim = os.environ["CLONE_EA_SIM"]
bport = os.environ["CLONE_BRIDGE_PORT"]
sport = os.environ["CLONE_SIM_PORT"]
# Local M15 assertions → clone identity; keep H1 checks.
text = text.replace("assert M15_MAGIC == 20260724", f"assert M15_MAGIC == {magic}")
text = text.replace('assert \'const string INSTANCE_ID = "M5E31"\' in m15', f'assert \'const string INSTANCE_ID = "{instance}"\' in m15')
text = text.replace('assert \'const string INSTANCE_ID = "M5E31"\' in m15_sim', f'assert \'const string INSTANCE_ID = "{instance}"\' in m15_sim')
text = text.replace('assert \'InpBridgeSubdir   = "bridge"\' in m15', f'assert \'InpBridgeSubdir   = "{bridge}"\' in m15')
text = text.replace("assert \"InpMagic          = 20260724\" in m15", f'assert "InpMagic          = {magic}" in m15')
text = text.replace('assert \'InpBridgeSubdir   = "bridge_sim"\' in m15_sim', f'assert \'InpBridgeSubdir   = "{bridge_sim}"\' in m15_sim')
text = text.replace("assert \"InpMagic          = 20260726\" in m15_sim", f'assert "InpMagic          = {magic_sim}" in m15_sim')
text = text.replace('(M15_ROOT, "ForgeBridgeM5E31", "ForgeBridgeM5E31Sim")', f'(M15_ROOT, "{ea}", "{ea_sim}")')
text = re.sub(
  r'm15 = \(M15_ROOT / "mt5" / "Experts" / "ForgeBridgeM5E31\.mq5"\)',
  f'm15 = (M15_ROOT / "mt5" / "Experts" / "{ea}.mq5")',
  text,
)
text = re.sub(
  r'm15_sim = \(M15_ROOT / "mt5" / "Experts" / "ForgeBridgeM5E31Sim\.mq5"\)',
  f'm15_sim = (M15_ROOT / "mt5" / "Experts" / "{ea_sim}.mq5")',
  text,
)
# Point M15_ROOT constant name still means "this repo" — OK.
# Monitor port uniqueness still holds if clone ≠ H1.
p.write_text(text, encoding="utf-8")
print("  patched tests/test_dual_runtime_contract.py")
PY
fi

chmod +x "$DST_ROOT/scripts/"*.sh 2>/dev/null || true

echo
echo "Done. Next:"
echo "  cd $DST_ROOT"
echo "  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
echo "  ./scripts/run_app_linux.sh Start"
echo "  # MT5: deploy EA $EA_LIVE, mount folder $BRIDGE_LIVE, magic $MAGIC_LIVE"
echo "See $DST_ROOT/CLONE_IDENTITY.md"
