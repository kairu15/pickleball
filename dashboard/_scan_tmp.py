"""Throwaway analysis helper (deleted before handoff)."""
import collections
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NAME_RE = re.compile(r"(?:views|cms_views)\.([A-Za-z_][A-Za-z0-9_]*)")


def scan():
    hits = collections.defaultdict(set)
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules", "staticfiles", "media", ".venv", "venv")]
        for f in files:
            if not f.endswith((".py", ".html", ".txt", ".md", ".json")):
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, ROOT)
            try:
                t = io.open(p, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            for m in NAME_RE.finditer(t):
                hits[m.group(1)].add(rel)
    return hits


def defs(path):
    lines = io.open(os.path.join(ROOT, path), encoding="utf-8").read().split("\n")
    out = []
    for i, l in enumerate(lines, 1):
        if re.match(r"^(def |class |[A-Za-z_]+ = |from |import )", l):
            out.append((i, l.rstrip()))
    return lines, out


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "names"
    if mode == "names":
        h = scan()
        print("TOTAL UNIQUE NAMES:", len(h))
        for k in sorted(h):
            print("%-55s %s" % (k, ",".join(sorted(h[k]))))
    elif mode == "defs":
        for p in sys.argv[2:]:
            lines, out = defs(p)
            print("===== %s (%d lines)" % (p, len(lines)))
            for i, l in out:
                print("%5d %s" % (i, l[:120]))
    elif mode == "summary":
        for p in sys.argv[2:]:
            lines = io.open(os.path.join(ROOT, p), encoding="utf-8").read().split("\n")
            print("===== %s (%d lines)" % (p, len(lines)))
            cur = None
            buf = []
            for i, l in enumerate(lines, 1):
                if re.match(r"^def ", l):
                    if cur:
                        print("  %s -> %s" % (cur, " / ".join(buf[:4])))
                    cur, buf = l[4:].split("(")[0], []
                elif cur is not None:
                    s = l.strip()
                    if s and not s.startswith(('"""', "'''")):
                        buf.append(s[:100])
            if cur:
                print("  %s -> %s" % (cur, " / ".join(buf[:4])))
