"""Clone of the github-readme-stats card, but Total Commits counts EVERY commit
in the owned repos (you + Claude + others), not just your email.

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

# github-readme-stats "dark" theme.
BG = "#0d1117"
BORDER = "#30363d"
TITLE = "#fff"
TEXT = "#9f9f9f"
VALUE = "#fff"
GREEN = "#79ff97"


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


def count_repo(name, tmp):
    dest = os.path.join(tmp, name)
    r = sh(["git", "clone", "--bare", "--filter=tree:0", "-q",
            repo_url(name), dest], timeout=300)
    if r.returncode != 0:
        return None
    total = sh(["git", "-C", dest, "rev-list", "--count", "HEAD"])
    try:
        return int((total.stdout or "0").strip())
    except ValueError:
        return None


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


def render(commits, stars, prs, issues):
    w, h = 495, 200
    rows = [
        ("★", "Total Stars Earned:", stars),
        ("⟳", "Total Commits:", commits),
        ("⎇", "Total PRs:", prs),
        ("⚠", "Total Issues:", issues),
        ("❐", "Contributed to:", 0),
    ]
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
         f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="4.5" fill="{BG}" stroke="{BORDER}"/>',
         f'<text x="25" y="35" font-family="Segoe UI, Ubuntu, sans-serif" font-size="18" font-weight="600" fill="{TITLE}">'
         f"{esc(OWNER)}'s GitHub Stats</text>"]
    y = 76
    for icon, label, value in rows:
        p.append(f'<text x="25" y="{y}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="14" fill="{GREEN}">{icon}</text>')
        p.append(f'<text x="48" y="{y}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="14" fill="{TEXT}">{esc(label)}</text>')
        p.append(f'<text x="300" y="{y}" text-anchor="end" font-family="Segoe UI, Ubuntu, sans-serif" font-size="14" fill="{VALUE}">{esc(value)}</text>')
        y += 25
    # Rank circle, like the original.
    cx, cy, rr = 410, 115, 57
    frac = max(0.05, min(1.0, commits / 500))
    p.append(f'<circle cx="{cx}" cy="{cy}" r="{rr}" fill="none" stroke="#333" stroke-width="7"/>')
    p.append(f'<circle cx="{cx}" cy="{cy}" r="{rr}" fill="none" stroke="{GREEN}" stroke-width="7" '
             f'stroke-linecap="round" stroke-dasharray="{2 * 3.1416 * rr:.1f}" '
             f'stroke-dashoffset="{2 * 3.1416 * rr * (1 - frac):.1f}" transform="rotate(-90 {cx} {cy})"/>')
    p.append(f'<text x="{cx}" y="{cy + 13}" text-anchor="middle" font-family="Segoe UI, Ubuntu, sans-serif" '
             f'font-size="34" font-weight="600" fill="{VALUE}">{esc(rank_letter(commits))}</text>')
    p.append('</svg>\n')
    return "".join(p)


def main():
    entries = repos()
    commits = 0
    stars = 0
    with tempfile.TemporaryDirectory(prefix="repstats") as tmp:
        for e in entries:
            n = e.get("name", "")
            c = count_repo(n, tmp)
            if c is None:
                print(f"skip {n}: n/a")
                continue
            commits += c
            stars += int(e.get("stargazerCount", 0) or 0)
            print(f"ok   {n}: {c}")
    prs = search_count(f"type:pr+author:{OWNER}")
    issues = search_count(f"type:issue+author:{OWNER}")
    with open(os.path.join(ROOT, "stats.svg"), "w", encoding="utf-8") as f:
        f.write(render(commits, stars, prs, issues))
    print(f"stats.svg written: commits={commits} stars={stars} prs={prs} issues={issues}")


if __name__ == "__main__":
    main()
