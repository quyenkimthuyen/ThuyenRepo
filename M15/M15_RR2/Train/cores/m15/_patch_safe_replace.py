from pathlib import Path

p = Path(r"C:\Work\ThuyenRepo\EdgeMinerM15\mt5_bridge\protocol.py")
text = p.read_text(encoding="utf-8")
start = text.find("def safe_replace(")
end = text.find("\ndef read_json(")
if start < 0 or end < 0:
  raise SystemExit(f"markers not found {start=} {end=}")

new = '''def safe_replace(src: Path, dst: Path, attempts: int = 10, delay: float = 0.05) -> None:
  """Replace dst with src; resilient to Windows WinError 5 (file in use)."""
  import os
  import shutil

  dst.parent.mkdir(parents=True, exist_ok=True)
  last_err: OSError | None = None
  for attempt in range(attempts):
    try:
      os.replace(str(src), str(dst))
      return
    except OSError as err:
      last_err = err
      if attempt < attempts - 1:
        time.sleep(delay * (attempt + 1))
  try:
    shutil.copyfile(str(src), str(dst))
    Path(src).unlink(missing_ok=True)
    return
  except OSError as err:
    last_err = err
  try:
    with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
      shutil.copyfileobj(fsrc, fdst)
      fdst.flush()
    Path(src).unlink(missing_ok=True)
    return
  except OSError as err:
    last_err = err
  try:
    Path(src).unlink(missing_ok=True)
  except OSError:
    pass
  if last_err is not None:
    raise last_err
  raise OSError(f"safe_replace failed: {src} -> {dst}")


def atomic_write_json(path: Path, data: Any) -> None:
  import os

  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_name(f"{path.stem}.{os.getpid()}.{time.time_ns()}.tmp")
  with open(tmp, "w", encoding="utf-8", newline="\\n") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\\n")
  try:
    safe_replace(tmp, path)
  except Exception:
    try:
      with open(path, "w", encoding="utf-8", newline="\\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\\n")
      if tmp.exists():
        tmp.unlink(missing_ok=True)
    except Exception:
      if tmp.exists():
        try:
          tmp.unlink(missing_ok=True)
        except OSError:
          pass
      raise


'''
# Fix accidental double-escaping of newlines in the written source
new = new.replace("newline=\\\\n", "newline=\"\\n\"").replace('f.write("\\\\n")', 'f.write("\\n")')
# Actually I used \\n in the triple string incorrectly. Rewrite cleanly.
new = r'''def safe_replace(src: Path, dst: Path, attempts: int = 10, delay: float = 0.05) -> None:
  """Replace dst with src; resilient to Windows WinError 5 (file in use)."""
  import os
  import shutil

  dst.parent.mkdir(parents=True, exist_ok=True)
  last_err: OSError | None = None
  for attempt in range(attempts):
    try:
      os.replace(str(src), str(dst))
      return
    except OSError as err:
      last_err = err
      if attempt < attempts - 1:
        time.sleep(delay * (attempt + 1))
  try:
    shutil.copyfile(str(src), str(dst))
    Path(src).unlink(missing_ok=True)
    return
  except OSError as err:
    last_err = err
  try:
    with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
      shutil.copyfileobj(fsrc, fdst)
      fdst.flush()
    Path(src).unlink(missing_ok=True)
    return
  except OSError as err:
    last_err = err
  try:
    Path(src).unlink(missing_ok=True)
  except OSError:
    pass
  if last_err is not None:
    raise last_err
  raise OSError(f"safe_replace failed: {src} -> {dst}")


def atomic_write_json(path: Path, data: Any) -> None:
  import os

  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_name(f"{path.stem}.{os.getpid()}.{time.time_ns()}.tmp")
  with open(tmp, "w", encoding="utf-8", newline="\n") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
  try:
    safe_replace(tmp, path)
  except Exception:
    try:
      with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
      if tmp.exists():
        tmp.unlink(missing_ok=True)
    except Exception:
      if tmp.exists():
        try:
          tmp.unlink(missing_ok=True)
        except OSError:
          pass
      raise


'''
p.write_text(text[:start] + new + text[end:], encoding="utf-8")
compile(p.read_text(encoding="utf-8"), str(p), "exec")
print("protocol OK")
