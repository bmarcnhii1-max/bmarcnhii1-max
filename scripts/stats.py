"""Profile stats: readme-stats-styled card (all authors) + 30-day activity sparkline.

- Total Commits counts EVERY commit in owned repos (you + Claude + others).
- Lines of Code counts tracked text files (binaries excluded).
- Private repos need STATS_PAT (classic PAT, repo scope); otherwise skipped.
"""
import datetime
import html
import json
import os
import subprocess
import tempfile

OWNER = "bmarcnhii1-max"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

BG = "#0d1117"
BORDER = "#30363d"
TITLE = "#fff"
TEXT = "#9f9f9f"
VALUE = "#fff"
GREEN = "#79ff97"
DIM = "#21262d"

BIN_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".apk", ".msix", ".cer",
           ".pfx", ".dll", ".exe", ".pdb", ".so", ".dylib", ".ttf", ".otf",
           ".woff", ".woff2", ".mp3", ".mp4", ".zip", ".jar", ".aar",
           ".keystore", ".jks", ".bin", ".dat", ".sqlite", ".db", ".pdf"}


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def repo_url(name):
    token = os.environ.get("STATS_PAT") or os.environ.get("GH_TOKEN", "")
    auth = f"x-access-token:{token}@" if token else ""
    return f"https://{auth}github.com/{OWNER}/{name}.git"


def repos():
    r = sh(["gh", "repo", "list", OWNER, "--json", "name,stargazerCount",
            "--limit", "100"])
    try:
        return json.loads(r.stdout or "[]")
    except Exception:
        return []


def search_count(q):
    r = sh(["gh", "api", f"search/issues?q={q}", "--jq", ".total_count"])
    try:
        return int((r.stdout or "0").strip())
    except ValueError:
        return 0


def analyze(name, tmp):
    dest = os.path.join(tmp, name)
    r = sh(["git", "clone", "-q", repo_url(name), dest], timeout=600)
    if r.returncode != 0:
        return None
    total = sh(["git", "-C", dest, "rev-list", "--count", "HEAD"])
    try:
        total_n = int((total.stdout or "0").strip())
    except ValueError:
        return None
    days = sh(["git", "-C", dest, "log", "--since=30 days ago",
               "--format=%ad", "--date=short"])
    per_day = {}
    for line in (days.stdout or "").splitlines():
        d = line.strip()
        if d:
            per_day[d] = per_day.get(d, 0) + 1
    files = sh(["git", "-C", dest, "ls-files"])
    loc = 0
    for f in (files.stdout or "").splitlines():
        f = f.strip()
        if not f or os.path.splitext(f)[1].lower() in BIN_EXT:
            continue
        p = os.path.join(dest, f)
        try:
            with open(p, "rb") as fh:
                loc += sum(1 for _ in fh)
        except OSError:
            pass
    return {"name": name, "total": total_n, "days": per_day, "loc": loc}


def rank_letter(total):
    if total >= 500:
        return "S"
    if total >= 200:
        return "A+"
    if total >= 100:
        return "A"
    if total >= 50:
        return "B+"
    if total >= 20:
        return "B"
    return "C+"


def esc(s):
    return html.escape(str(s), quote=False)


def render_combined(commits, stars, prs, issues, loc, day_counts):
    import datetime as dt
    w = 600
    rows = [
        ("★", "Total Stars Earned:", stars),
        ("⟳", "Total Commits:", commits),
        ("⎇", "Total PRs:", prs),
        ("⚠", "Total Issues:", issues),
        ("❐", "Contributed to:", 0),
        ("≣", "Lines of Code:", f"{loc:,}"),
    ]
    # Stats block.
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="405" viewBox="0 0 {w} 405">',
         f'<defs><linearGradient id="bar" x1="0" y1="1" x2="0" y2="0">'
         f'<stop offset="0" stop-color="#1a7f37"/><stop offset="1" stop-color="{GREEN}"/>'
         f'</linearGradient></defs>',
         f'<rect x="0.5" y="0.5" width="{w - 1}" height="404" rx="8" fill="{BG}" stroke="{BORDER}"/>',
         f'<text x="24" y="35" font-family="Segoe UI, Ubuntu, sans-serif" font-size="18" font-weight="600" fill="{TITLE}">'
         f"{esc(OWNER)}'s GitHub Stats</text>"]
    y = 76
    for icon, label, value in rows:
        p.append(f'<text x="24" y="{y}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="14" fill="{GREEN}">{icon}</text>')
        p.append(f'<text x="48" y="{y}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="14" fill="{TEXT}">{esc(label)}</text>')
        p.append(f'<text x="320" y="{y}" text-anchor="end" font-family="Segoe UI, Ubuntu, sans-serif" font-size="14" fill="{VALUE}">{esc(value)}</text>')
        y += 25
    cx, cy, rr = 505, 122, 57
    frac = max(0.05, min(1.0, commits / 500))
    c = 2 * 3.1416 * rr
    p.append(f'<circle cx="{cx}" cy="{cy}" r="{rr}" fill="none" stroke="#333" stroke-width="7"/>')
    p.append(f'<circle cx="{cx}" cy="{cy}" r="{rr}" fill="none" stroke="{GREEN}" stroke-width="7" '
             f'stroke-linecap="round" stroke-dasharray="{c:.1f}" '
             f'stroke-dashoffset="{c * (1 - frac):.1f}" transform="rotate(-90 {cx} {cy})"/>')
    p.append(f'<text x="{cx}" y="{cy + 13}" text-anchor="middle" font-family="Segoe UI, Ubuntu, sans-serif" '
             f'font-size="34" font-weight="600" fill="{VALUE}">{esc(rank_letter(commits))}</text>')
    # Seam between the blocks.
    p.append(f'<line x1="24" y1="232" x2="{w - 24}" y2="232" stroke="#21262d" stroke-width="1"/>')
    # Activity block.
    today = dt.date.today()
    days = [today - dt.timedelta(days=i) for i in range(29, -1, -1)]
    vals = [day_counts.get(d.isoformat(), 0) for d in days]
    peak = max(vals + [1])
    p.append('<text x="24" y="258" font-family="monospace" font-size="13" fill="#30d158">'
             f'активность · 30 дней · {sum(vals)} коммитов</text>')
    bw, slot, y0, hm = 11, (w - 48) / 30, 272, 100
    for i, v in enumerate(vals):
        bh = max(3 if v else 2, int(hm * v / peak))
        x = 24 + i * slot
        yy = y0 + hm - bh
        if v:
            p.append(f'<rect x="{x:.1f}" y="{yy}" width="{bw}" height="{bh}" rx="3" fill="url(#bar)">'
                     f'<title>{days[i].isoformat()}: {v}</title></rect>')
        else:
            p.append(f'<rect x="{x:.1f}" y="{yy}" width="{bw}" height="{bh}" rx="3" fill="{DIM}" opacity="0.6"/>')
    p.append('</svg>\n')
    return "".join(p)


def main():
    entries = repos()
    commits = stars = loc = 0
    day_counts = {}
    with tempfile.TemporaryDirectory(prefix="repstats") as tmp:
        for e in entries:
            n = e.get("name", "")
            info = analyze(n, tmp)
            if info is None:
                print(f"skip {n}: n/a")
                continue
            commits += info["total"]
            loc += info["loc"]
            stars += int(e.get("stargazerCount", 0) or 0)
            for d, c in info["days"].items():
                day_counts[d] = day_counts.get(d, 0) + c
            print(f"ok   {n}: {info['total']} commits, {info['loc']} loc")
    prs = search_count(f"type:pr+author:{OWNER}")
    issues = search_count(f"type:issue+author:{OWNER}")
    with open(os.path.join(ROOT, "stats.svg"), "w", encoding="utf-8") as f:
        f.write(render_combined(commits, stars, prs, issues, loc, day_counts))
    print(f"done: commits={commits} loc={loc} stars={stars}")


if __name__ == "__main__":
    main()
