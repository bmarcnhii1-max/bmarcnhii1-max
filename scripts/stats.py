"""Full commit stats across all owned repos (you + Claude + others).

Counts every commit in the default branch via a blobless partial clone,
so Claude-authored commits count too (GitHub's own stats only see your email).
Private repos need STATS_PAT (a classic PAT with repo scope); without it they
are skipped gracefully.
"""
import html
import json
import os
import subprocess
import tempfile

OWNER = "bmarcnhii1-max"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def repo_url(name):
    token = os.environ.get("STATS_PAT") or os.environ.get("GH_TOKEN", "")
    auth = f"x-access-token:{token}@" if token else ""
    return f"https://{auth}github.com/{OWNER}/{name}.git"


def repos():
    r = sh(["gh", "repo", "list", OWNER, "--json", "name", "--limit", "100"])
    try:
        return [x["name"] for x in json.loads(r.stdout or "[]")]
    except Exception:
        return []


def classify(email, name):
    e = (email or "").lower()
    n = (name or "").lower()
    if "anthropic.com" in e or n == "claude":
        return "claude"
    if "bmarcnhii1" in e or "alumno.uned.es" in e:
        return "you"
    return "other"


def count_repo(name, tmp):
    dest = os.path.join(tmp, name)
    r = sh(["git", "clone", "--bare", "--filter=tree:0", "-q",
            repo_url(name), dest], timeout=300)
    if r.returncode != 0:
        return None
    total = sh(["git", "-C", dest, "rev-list", "--count", "HEAD"])
    try:
        total_n = int((total.stdout or "0").strip())
    except ValueError:
        return None
    parts = {"you": 0, "claude": 0, "other": 0}
    log = sh(["git", "-C", dest, "log", "--format=%ae%x00%an%x00"])
    for line in (log.stdout or "").splitlines():
        fields = line.strip("\x00").split("\x00")
        if len(fields) < 2:
            continue
        parts[classify(fields[0].strip(), fields[1].strip())] += 1
    return {"name": name, "total": total_n, **parts}


def esc(s):
    return html.escape(s, quote=False)


def render(rows):
    rows = sorted(rows, key=lambda r: (r is not None, (r or {}).get("total", 0)))
    rows = [r for r in rows if r is not None]
    known = [r for r in rows if r["total"] is not None]
    top = max([r["total"] for r in known] + [1])
    tot = sum(r["total"] for r in known)
    you = sum(r["you"] for r in known)
    claude = sum(r["claude"] for r in known)

    rh, y0 = 34, 52
    h = y0 + len(rows) * rh + 40
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="{h}">']
    out.append(f'<rect width="600" height="{h}" rx="8" fill="#0d1117" stroke="#30363d"/>')
    out.append('<text x="24" y="30" font-family="monospace" font-size="13" fill="#30d158">'
               f'полные коммиты · всего {tot} (ты {you} · claude {claude})</text>')
    y = y0
    for r in rows:
        if r["total"] is None:
            line = (f'<text x="24" y="{y}" font-family="monospace" font-size="13" fill="#8b949e">'
                    f'{esc(r["name"]):24} private / n-a</text>')
            out.append(line)
            y += rh
            continue
        w = max(4, int(200 * r["total"] / top))
        wy = max(2, int(w * r["you"] / max(r["total"], 1)))
        wc = max(0, int(w * r["claude"] / max(r["total"], 1)))
        bar = (f'<rect x="250" y="{y - 11}" width="{w}" height="10" rx="5" fill="#21262d"/>'
               f'<rect x="250" y="{y - 11}" width="{wy}" height="10" rx="5" fill="#30d158"/>'
               f'<rect x="{250 + wy}" y="{y - 11}" width="{wc}" height="10" rx="5" fill="#a371f7"/>')
        label = (f'<text x="24" y="{y}" font-family="monospace" font-size="13" fill="#c9d1d9">'
                 f'{esc(r["name"]):24} {r["total"]}</text>')
        out.append(label + bar)
        y += rh
    out.append(f'<text x="24" y="{y + 8}" font-family="monospace" font-size="11" fill="#8b949e">'
               '■ ты  ■ claude  ■ прочие · считает все email, не только твой</text>')
    out.append('</svg>\n')
    return "".join(out)


def main():
    names = repos()
    results = []
    with tempfile.TemporaryDirectory(prefix="repstats") as tmp:
        for n in names:
            info = count_repo(n, tmp)
            results.append(info if info else {"name": n, "total": None})
            print(("ok  " if info else "skip") + f" {n}: "
                  + (str(info["total"]) if info else "n/a"))
    with open(os.path.join(ROOT, "stats.svg"), "w", encoding="utf-8") as f:
        f.write(render(results))
    print("stats.svg written")


if __name__ == "__main__":
    main()
