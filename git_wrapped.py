#!/usr/bin/env python3
"""git-wrapped: a "year in review" page for any git repository.

Usage:
    python git_wrapped.py [REPO_PATH] [--year YEAR] [--author NAME] [-o OUT.html]

Reads `git log`, writes one self-contained HTML file. No dependencies.
"""
import argparse
import html
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, timedelta

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def read_commits(repo, year, author):
    cmd = ["git", "-C", repo, "log", "--no-merges", "--date=iso-strict",
           "--pretty=format:@@%H|%an|%ad|%s", "--numstat"]
    if year:
        cmd += [f"--since={year}-01-01", f"--until={year}-12-31 23:59:59"]
    if author:
        cmd += [f"--author={author}"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        sys.exit(f"git log failed: {getattr(e, 'stderr', e)}")
    commits, cur = [], None
    for line in out.splitlines():
        if line.startswith("@@"):
            h, name, when, subj = line[2:].split("|", 3)
            cur = {"hash": h, "author": name, "when": datetime.fromisoformat(when),
                   "subject": subj, "files": Counter(), "add": 0, "del": 0}
            commits.append(cur)
        elif line.strip() and cur:
            a, d, path = line.split("\t", 2)
            if a.isdigit() and d.isdigit():
                cur["add"] += int(a)
                cur["del"] += int(d)
                cur["files"][path] += 1
    return commits


def longest_streak(days):
    best = run = 0
    prev = None
    for d in sorted(days):
        run = run + 1 if prev and d - prev == timedelta(days=1) else 1
        best = max(best, run)
        prev = d
    return best


def personality(hours, weekdays):
    night = sum(hours[h] for h in (22, 23, 0, 1, 2, 3, 4))
    morning = sum(hours[h] for h in range(5, 10))
    weekend = weekdays[5] + weekdays[6]
    total = max(sum(hours), 1)
    if night / total > 0.35:
        return "Night Owl", "Most of your commits land after dark."
    if morning / total > 0.35:
        return "Early Bird", "You ship before most people have had coffee."
    if weekend / total > 0.35:
        return "Weekend Warrior", "Side-project energy. Saturdays are your sprint."
    return "Nine-to-Fiver", "Steady, sensible, sustainable."


def build(commits, name, year):
    days = Counter(c["when"].date() for c in commits)
    hours, weekdays = [0] * 24, [0] * 7
    files, authors = Counter(), Counter()
    for c in commits:
        hours[c["when"].hour] += 1
        weekdays[c["when"].weekday()] += 1
        files.update(c["files"])
        authors[c["author"]] += 1
    add = sum(c["add"] for c in commits)
    dele = sum(c["del"] for c in commits)
    busiest = days.most_common(1)[0]
    title, blurb = personality(hours, weekdays)
    biggest = max(commits, key=lambda c: c["add"] + c["del"])

    # heatmap: weeks as columns, Mon-Sun as rows
    first = min(days)
    start = first - timedelta(days=first.weekday())
    last = max(days)
    cells, d, peak = [], start, max(days.values())
    week = 0
    while d <= last:
        n = days.get(d, 0)
        lvl = 0 if n == 0 else min(4, 1 + int(3 * n / peak))
        x, y = week * 14, d.weekday() * 14
        cells.append(f'<rect x="{x}" y="{y}" width="11" height="11" rx="2" '
                     f'class="l{lvl}"><title>{d} : {n}</title></rect>')
        d += timedelta(days=1)
        if d.weekday() == 0:
            week += 1
    heat_w = (week + 1) * 14

    def bars(vals, labels, w=22):
        m = max(vals) or 1
        out = []
        for i, v in enumerate(vals):
            h = int(90 * v / m)
            out.append(f'<div class="bar"><span class="n">{v or ""}</span>'
                       f'<i style="height:{h}px"></i><b>{labels[i]}</b></div>')
        return "".join(out)

    top_files = "".join(
        f"<li><code>{html.escape(f)}</code><span>{n}</span></li>"
        for f, n in files.most_common(5))
    esc = html.escape
    label = f"{year}" if year else f"{first.year}-{last.year}"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(name)} Wrapped {label}</title><style>
:root{{--bg:#0d1117;--card:#161b22;--fg:#e6edf3;--mut:#8b949e;--a:#2ea043}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);
font:16px/1.5 system-ui,sans-serif;padding:24px}}
main{{max-width:900px;margin:auto;display:grid;gap:16px}}
.hero{{background:linear-gradient(135deg,#1f6feb,#8957e5 60%,#db61a2);
border-radius:20px;padding:40px 28px}}
.hero h1{{margin:0;font-size:clamp(2rem,6vw,3.4rem)}}.hero p{{margin:.4rem 0 0;opacity:.9}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px}}
.card{{background:var(--card);border-radius:16px;padding:20px}}
.big{{font-size:2.4rem;font-weight:800;line-height:1.1}}.mut{{color:var(--mut)}}
h2{{margin:0 0 10px;font-size:1rem;color:var(--mut);font-weight:600}}
.bars{{display:flex;gap:4px;align-items:flex-end;height:130px}}
.bar{{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;font-size:10px}}
.bar i{{display:block;width:100%;background:var(--a);border-radius:3px 3px 0 0;min-height:2px}}
.bar .n{{color:var(--mut)}}.bar b{{font-weight:400;color:var(--mut);margin-top:3px}}
.l0{{fill:#21262d}}.l1{{fill:#0e4429}}.l2{{fill:#006d32}}.l3{{fill:#26a641}}.l4{{fill:#39d353}}
svg{{max-width:100%;height:auto}}.scroll{{overflow-x:auto}}
ul{{list-style:none;margin:0;padding:0}}li{{display:flex;justify-content:space-between;
padding:6px 0;border-bottom:1px solid #21262d;gap:12px}}code{{word-break:break-all}}
footer{{text-align:center;color:var(--mut);font-size:13px}}
</style></head><body><main>
<section class="hero"><h1>{esc(name)}<br>Wrapped {label}</h1>
<p>You are a <b>{title}</b>. {blurb}</p></section>
<div class="grid">
<div class="card"><h2>Commits</h2><div class="big">{len(commits):,}</div></div>
<div class="card"><h2>Active days</h2><div class="big">{len(days)}</div></div>
<div class="card"><h2>Longest streak</h2><div class="big">{longest_streak(days)} days</div></div>
<div class="card"><h2>Lines added / removed</h2><div class="big">+{add:,}<br><span class="mut">-{dele:,}</span></div></div>
</div>
<div class="card"><h2>Busiest day</h2><div class="big">{busiest[0]:%b %d, %Y}</div>
<span class="mut">{busiest[1]} commits</span></div>
<div class="card"><h2>Commit activity</h2><div class="scroll">
<svg width="{heat_w}" height="98" viewBox="0 0 {heat_w} 98">{"".join(cells)}</svg></div></div>
<div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(300px,1fr))">
<div class="card"><h2>By hour of day</h2><div class="bars">{bars(hours, [str(h) if h % 3 == 0 else "" for h in range(24)])}</div></div>
<div class="card"><h2>By day of week</h2><div class="bars">{bars(weekdays, DAYS)}</div></div></div>
<div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(300px,1fr))">
<div class="card"><h2>Most touched files</h2><ul>{top_files or "<li>none</li>"}</ul></div>
<div class="card"><h2>Biggest commit</h2><p>{esc(biggest["subject"])}</p>
<span class="mut">+{biggest["add"]:,} / -{biggest["del"]:,} on {biggest["when"]:%b %d, %Y}</span>
<h2 style="margin-top:16px">Contributors</h2><ul>{"".join(f"<li>{esc(a)}<span>{n}</span></li>" for a, n in authors.most_common(5))}</ul></div></div>
<footer>Generated by git-wrapped</footer></main></body></html>"""


def main():
    p = argparse.ArgumentParser(description="Spotify-Wrapped style report for a git repo.")
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--year", type=int, help="limit to one year (default: all time)")
    p.add_argument("--author", help="filter by author name or email")
    p.add_argument("-o", "--out", default="wrapped.html")
    a = p.parse_args()
    commits = read_commits(a.repo, a.year, a.author)
    if not commits:
        sys.exit("No commits found for those filters.")
    name = a.repo.rstrip("/").split("/")[-1] if a.repo != "." else \
        subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                       text=True).stdout.strip().split("/")[-1]
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(build(commits, name or "repo", a.year))
    print(f"Wrote {a.out} ({len(commits)} commits)")


if __name__ == "__main__":
    main()
