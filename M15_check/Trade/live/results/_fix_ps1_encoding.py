from pathlib import Path

p = Path(r"C:\Work\ThuyenRepo\Final_app\split_app\live\scripts\run_app_windows.ps1")
t = p.read_text(encoding="utf-8")
repl = {
  "\u2014": "-",
  "\u2013": "-",
  "\u2018": "'",
  "\u2019": "'",
  "\u201c": '"',
  "\u201d": '"',
}
for a, b in repl.items():
  t = t.replace(a, b)
p.write_text(t, encoding="utf-8")
print("ok", any(ord(c) > 127 for c in t))
