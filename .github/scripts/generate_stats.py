#!/usr/bin/env python3
"""Generates live profile cards (stats + languages) from the GitHub API.

Runs inside the "Update profile stats" workflow. Uses only the Python
standard library. Output SVG files are written to ./dist and published to
the `profile-stats` branch, which the README loads.
"""
import json
import math
import os
import urllib.request
from datetime import datetime, timezone
from html import escape

USER = os.environ.get("GH_USER", "OscarGonzalezwr1")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.environ.get("OUT_DIR", "dist")

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
BG, BORDER, TEXT, MUTED, ACCENT = "#0d1117", "#30363d", "#e6edf3", "#8b949e", "#3fb950"

LANG_COLORS = {
    "PHP": "#4F5D95", "JavaScript": "#f1e05a", "TypeScript": "#3178c6",
    "CSS": "#663399", "HTML": "#e34c26", "Python": "#3572A5", "Java": "#b07219",
    "C#": "#178600", "C++": "#f34b7d", "C": "#555555", "Hack": "#878787",
    "Blade": "#f7523f", "Shell": "#89e051", "TSQL": "#e38c00", "PLpgSQL": "#336790",
    "Vue": "#41b883", "Kotlin": "#A97BFF", "Go": "#00ADD8", "Dart": "#00B4AB",
}
FALLBACK = ["#3fb950", "#58a6ff", "#d29922", "#f778ba", "#a5d6ff", "#ff7b72"]


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def contributions_last_year():
    if not TOKEN:
        return None
    q = {"query": 'query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{totalContributions}}}}',
         "variables": {"u": USER}}
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps(q).encode(), method="POST")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    except Exception as e:  # keep the cards working even if GraphQL is unavailable
        print("contributions unavailable:", e)
        return None


ICONS = {
    "repo": '<path d="M3 6.5A1.5 1.5 0 0 1 4.5 5h4l2 2h9A1.5 1.5 0 0 1 21 8.5v9a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 17.5z"/>',
    "star": '<path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z"/>',
    "user": '<circle cx="12" cy="8" r="3.5"/><path d="M5 20c0-3.9 3.1-6.5 7-6.5s7 2.6 7 6.5"/>',
    "pulse": '<path d="M3 12h4l2.5-6 5 12 2.5-6H21"/>',
    "code": '<path d="M8.5 7L3.5 12l5 5M15.5 7l5 5-5 5"/>',
}


def stat_card(icon, value, label):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="240" height="120" viewBox="0 0 240 120" role="img" aria-label="{escape(label)}: {value}">
  <rect x="1" y="1" width="238" height="118" rx="14" fill="{BG}" stroke="{BORDER}" stroke-width="1.5"/>
  <g transform="translate(108 14)" fill="none" stroke="{MUTED}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{ICONS[icon]}</g>
  <text x="120" y="76" text-anchor="middle" font-family="{FONT}" font-size="32" font-weight="700" fill="{TEXT}">{value}</text>
  <text x="120" y="102" text-anchor="middle" font-family="{FONT}" font-size="15" fill="{MUTED}">{escape(label)}</text>
</svg>
'''


def languages_card(langs, repo_count):
    total = sum(langs.values()) or 1
    items = sorted(langs.items(), key=lambda kv: kv[1], reverse=True)
    top = items[:6]
    rest = sum(v for _, v in items[6:])
    if rest:
        top.append(("Other", rest))
    W, H = 480, 260
    cx, cy, r, sw = 120, 128, 72, 26
    circ = 2 * math.pi * r
    parts, offset = [], 0.0
    for i, (name, val) in enumerate(top):
        color = LANG_COLORS.get(name, FALLBACK[i % len(FALLBACK)])
        length = circ * val / total
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="{sw}" '
                     f'stroke-dasharray="{length:.3f} {circ - length:.3f}" stroke-dashoffset="{-offset:.3f}" '
                     f'transform="rotate(-90 {cx} {cy})"/>')
        offset += length
    if not top:
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{BORDER}" stroke-width="{sw}"/>')
    rows = []
    row_h = 30
    y0 = cy - (len(top) - 1) * row_h / 2
    for i, (name, val) in enumerate(top):
        color = LANG_COLORS.get(name, FALLBACK[i % len(FALLBACK)])
        y = y0 + i * row_h
        pct = 100 * val / total
        rows.append(f'<circle cx="262" cy="{y:.1f}" r="7" fill="{color}"/>'
                    f'<text x="278" y="{y + 5:.1f}" font-family="{FONT}" font-size="16" fill="{TEXT}">{escape(name)}</text>'
                    f'<text x="452" y="{y + 5:.1f}" text-anchor="end" font-family="{FONT}" font-size="16" font-weight="600" fill="{TEXT}">{pct:.1f}%</text>')
    plural = "repository" if repo_count == 1 else "repositories"
    updated = datetime.now(timezone.utc).strftime("%b %d, %Y")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Most used languages">
  <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="{BG}" stroke="{BORDER}" stroke-width="1.5"/>
  {''.join(parts)}
  <text x="{cx}" y="{cy + 5}" text-anchor="middle" font-family="{FONT}" font-size="14" fill="{MUTED}">{len(langs)} {"language" if len(langs) == 1 else "languages"}</text>
  {''.join(rows)}
  <text x="24" y="{H - 16}" font-family="{FONT}" font-size="12" fill="{MUTED}">Based on {repo_count} public {plural} · updated {updated}</text>
</svg>
'''


def main():
    os.makedirs(OUT, exist_ok=True)
    user = api(f"/users/{USER}")
    repos, page = [], 1
    while True:
        batch = api(f"/users/{USER}/repos?per_page=100&page={page}&type=owner")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    own = [r for r in repos if not r["fork"]]
    projects = [r for r in own if r["name"].lower() != USER.lower()]  # skip the profile README repo
    stars = sum(r["stargazers_count"] for r in own)

    langs = {}
    for r in projects:
        for name, size in api(f"/repos/{USER}/{r['name']}/languages").items():
            langs[name] = langs.get(name, 0) + size

    contrib = contributions_last_year()
    cards = {
        "stat-repos.svg": stat_card("repo", user["public_repos"], "Total Repos"),
        "stat-stars.svg": stat_card("star", stars, "Total Stars"),
        "stat-followers.svg": stat_card("user", user["followers"], "Followers"),
        "stat-activity.svg": (stat_card("pulse", contrib, "Contributions (1y)") if contrib is not None
                              else stat_card("code", len(langs), "Languages Used")),
        "languages.svg": languages_card(langs, len(projects)),
    }
    for name, svg in cards.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(svg)
        print("wrote", name)


if __name__ == "__main__":
    main()
