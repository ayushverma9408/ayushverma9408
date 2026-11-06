#!/usr/bin/env python3
"""Generate self-hosted SVG cards for the AYUSH profile README."""
import json
import os
import urllib.request
import html
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

USER = "ayushverma9408"
TOKEN = os.environ["GITHUB_TOKEN"]
OUT = Path("profile")
OUT.mkdir(exist_ok=True)

def request_json(url, data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
        "User-Agent": "ayush-profile-dashboard"
    })
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

def esc(value):
    return html.escape(str(value))

def card(title, subtitle, body, width=495, height=190):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#111827"/><stop offset="1" stop-color="#171b2e"/></linearGradient><linearGradient id="accent"><stop stop-color="#7aa2f7"/><stop offset="1" stop-color="#bb9af7"/></linearGradient></defs>
<rect width="100%" height="100%" rx="13" fill="url(#bg)" stroke="#2b3448"/>
<text x="24" y="34" fill="#e5e9f0" font-family="Segoe UI,Arial" font-size="15" font-weight="700">{esc(title)}</text>
<text x="24" y="53" fill="#8b9bb4" font-family="Segoe UI,Arial" font-size="9">{esc(subtitle)}</text>
{body}
<text x="24" y="{height-13}" fill="#59677e" font-family="Segoe UI,Arial" font-size="8">AYUSH OS  ·  AUTO-UPDATED BY GITHUB ACTIONS</text>
</svg>'''

def text(x, y, value, size=12, color="#c0caf5", weight="400"):
    return f'<text x="{x}" y="{y}" fill="{color}" font-family="Segoe UI,Arial" font-size="{size}" font-weight="{weight}">{esc(value)}</text>'

profile = request_json(f"https://api.github.com/users/{USER}")
repos = []
page = 1
while page <= 5:
    batch = request_json(f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}&type=owner&sort=updated")
    repos.extend(batch)
    if len(batch) < 100:
        break
    page += 1
repos = [r for r in repos if not r.get("fork", False)]
stars = sum(r.get("stargazers_count", 0) for r in repos)
forks = sum(r.get("forks_count", 0) for r in repos)
language_bytes = {}
for repo in repos:
    if repo.get("language"):
        language_bytes[repo["language"]] = language_bytes.get(repo["language"], 0) + 1
languages = sorted(language_bytes.items(), key=lambda x: x[1], reverse=True)[:6]

today = date.today()
from_day = today - timedelta(days=364)
query = """query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}"""
data = request_json("https://api.github.com/graphql", {
    "query": query,
    "variables": {
        "login": USER,
        "from": datetime.combine(from_day, datetime.min.time(), timezone.utc).isoformat(),
        "to": datetime.combine(today, datetime.max.time(), timezone.utc).isoformat()
    }
})
user_data = data.get("data", {}).get("user") or {}
calendar = user_data.get("contributionsCollection", {}).get("contributionCalendar", {})
days = [d for week in calendar.get("weeks", []) for d in week.get("contributionDays", [])]
total_contributions = calendar.get("totalContributions", 0)
counts = [d.get("contributionCount", 0) for d in days]
current_streak = 0
for count in reversed(counts):
    if count > 0:
        current_streak += 1
    elif current_streak or count == 0:
        break
longest = run = 0
for count in counts:
    run = run + 1 if count > 0 else 0
    longest = max(longest, run)

# Public profile statistics.
stats_body = ""
metrics = [
    ("PUBLIC REPOS", len(repos)),
    ("TOTAL STARS", stars),
    ("TOTAL FORKS", forks),
    ("FOLLOWERS", profile.get("followers", 0))
]
for i, (label, value) in enumerate(metrics):
    x = 28 + i * 118
    stats_body += text(x, 105, f"{value:,}", 25, "#7aa2f7", "700")
    stats_body += text(x, 125, label, 8, "#8b9bb4", "600")
    if i < 3:
        stats_body += f'<line x1="{x+102}" y1="77" x2="{x+102}" y2="145" stroke="#30394e"/>'
(OUT / "github-stats.svg").write_text(card("GitHub Statistics", "PUBLIC REPOSITORY SNAPSHOT", stats_body), encoding="utf-8")

# Language card based on public repository primary-language metadata.
lang_body = ""
total_lang = sum(v for _, v in languages) or 1
palette = ["#7aa2f7", "#bb9af7", "#9ece6a", "#e0af68", "#f7768e", "#73daca"]
x = 26
for i, (name, count) in enumerate(languages):
    pct = count / total_lang * 100
    lang_body += f'<rect x="{x}" y="78" width="{pct*4.35:.1f}" height="10" rx="4" fill="{palette[i % len(palette)]}"/>'
    lang_body += text(x, 112 + (i//3)*35, f"{name}  ·  {pct:.0f}%", 10, palette[i % len(palette)], "600")
    x += pct * 4.35
    if x > 450:
        break
(OUT / "languages.svg").write_text(card("Language Distribution", "PRIMARY LANGUAGES ACROSS PUBLIC, NON-FORK REPOSITORIES", lang_body), encoding="utf-8")

# Contribution activity card with current/longest streak.
activity_body = ""
for i, (label, value) in enumerate([
    ("TOTAL CONTRIBUTIONS", total_contributions),
    ("CURRENT STREAK", current_streak),
    ("LONGEST STREAK", longest)
]):
    x = 38 + i * 157
    activity_body += text(x, 111, f"{value:,}", 27, "#7aa2f7" if i != 1 else "#bb9af7", "700")
    activity_body += text(x, 132, label, 8, "#8b9bb4", "600")
    if i < 2:
        activity_body += f'<line x1="{x+126}" y1="78" x2="{x+126}" y2="148" stroke="#30394e"/>'
activity_body += text(38, 160, f"Contribution calendar · {from_day.isoformat()} to {today.isoformat()}", 8, "#73daca")
(OUT / "contributions.svg").write_text(card("GitHub Contribution Activity", "LAST 365 DAYS · PUBLIC PROFILE CONTRIBUTIONS", activity_body), encoding="utf-8")

# Compact recent weekly activity visualization.
weekly = []
for week in calendar.get("weeks", [])[-26:]:
    weekly.append(sum(d.get("contributionCount", 0) for d in week.get("contributionDays", [])))
max_week = max(weekly, default=1) or 1
bars = ""
for i, value in enumerate(weekly):
    h = max(3, value / max_week * 65)
    x = 26 + i * 17
    bars += f'<rect x="{x}" y="{145-h:.1f}" width="10" height="{h:.1f}" rx="3" fill="#7aa2f7" opacity="{0.45 + 0.55*value/max_week:.2f}"/>'
bars += text(26, 165, "WEEKLY CONTRIBUTION TREND · LAST 26 WEEKS", 8, "#8b9bb4")
bars += text(26, 105, f"{total_contributions:,} contributions in the last year", 11, "#bb9af7", "600")
(OUT / "live-coding.svg").write_text(card("Live Coding Activity", "GITHUB CONTRIBUTION CALENDAR · REFRESHED DAILY", bars, height=190), encoding="utf-8")


# Full-width GitHub activity graph, rendered locally as a repository-owned SVG.
weekly_all = [
    sum(day.get("contributionCount", 0) for day in week.get("contributionDays", []))
    for week in calendar.get("weeks", [])
]
graph_width, graph_height = 1000, 300
left, right, top, bottom = 62, 24, 70, 48
plot_w, plot_h = graph_width - left - right, graph_height - top - bottom
peak = max(weekly_all, default=1) or 1
coords = []
for i, value in enumerate(weekly_all):
    px = left + (i / max(1, len(weekly_all)-1)) * plot_w
    py = top + plot_h - (value / peak) * plot_h
    coords.append((px, py))
line_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
area_points = f"{left},{top+plot_h} " + line_points + f" {left+plot_w},{top+plot_h}"
grid = ""
for tick in range(5):
    y = top + plot_h - (tick / 4) * plot_h
    val = round(peak * tick / 4)
    grid += f'<line x1="{left}" y1="{y:.1f}" x2="{left+plot_w}" y2="{y:.1f}" stroke="#293449" stroke-dasharray="4 6"/>'
    grid += f'<text x="{left-12}" y="{y+4:.1f}" text-anchor="end" fill="#8290a8" font-size="10">{val}</text>'
month_labels = ""
all_dates = [day.get("date") for day in days]
for i, day_date in enumerate(all_dates):
    if day_date and day_date.endswith("-01"):
        x = left + (i / max(1, len(all_dates)-1)) * plot_w
        month = date.fromisoformat(day_date).strftime("%b")
        month_labels += f'<text x="{x:.1f}" y="{top+plot_h+24}" fill="#8290a8" font-size="10">{month}</text>'
graph_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{graph_width}" height="{graph_height}" viewBox="0 0 {graph_width} {graph_height}">
<defs>
  <linearGradient id="graphBg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#111827"/><stop offset="1" stop-color="#171b2e"/></linearGradient>
  <linearGradient id="graphArea" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#7aa2f7" stop-opacity=".38"/><stop offset="1" stop-color="#7aa2f7" stop-opacity="0"/></linearGradient>
</defs>
<rect width="100%" height="100%" rx="16" fill="url(#graphBg)" stroke="#2b3448"/>
<text x="28" y="34" fill="#e5e9f0" font-family="Segoe UI,Arial" font-size="17" font-weight="700">GitHub Activity — Live Graph</text>
<text x="28" y="53" fill="#8b9bb4" font-family="Segoe UI,Arial" font-size="10">WEEKLY CONTRIBUTIONS · LAST 12 MONTHS · {total_contributions:,} TOTAL CONTRIBUTIONS</text>
{grid}
<polygon points="{area_points}" fill="url(#graphArea)"/>
<polyline points="{line_points}" fill="none" stroke="#7aa2f7" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
{''.join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="#bb9af7" stroke="#111827" stroke-width="1.5"/>' for x,y in coords)}
{month_labels}
<text x="28" y="{graph_height-12}" fill="#59677e" font-family="Segoe UI,Arial" font-size="9">AYUSH OS · SELF-HOSTED SVG · UPDATED DAILY BY GITHUB ACTIONS</text>
</svg>'''
(OUT / "activity-graph.svg").write_text(graph_svg, encoding="utf-8")

print("Generated:", ", ".join(p.name for p in OUT.glob("*.svg")))
