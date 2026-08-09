"""Compiles and posts the daily briefing issue."""
import datetime as dt
import os
import random
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jarvis_core import QUOTES, weather  # noqa: E402

API = "https://api.github.com"


def repo_activity(repo, token):
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)).isoformat()
    r = requests.get(f"{API}/repos/{repo}/commits",
                     params={"since": since, "per_page": 100},
                     headers={"Authorization": f"Bearer {token}",
                              "Accept": "application/vnd.github+json"},
                     timeout=20)
    if r.status_code != 200:
        return "_Repo uplink unreachable._"
    commits = r.json()
    if not commits:
        return "No commits in the last 24 hours. A quiet shift."
    lines = [f"**{len(commits)} commit(s)** in the last 24 hours:"]
    for c in commits[:5]:
        msg = c["commit"]["message"].splitlines()[0][:70]
        lines.append(f"- `{c['sha'][:7]}` {msg} — *{c['commit']['author']['name']}*")
    if len(commits) > 5:
        lines.append(f"- …and {len(commits) - 5} more")
    return "\n".join(lines)


def main():
    repo = os.environ["REPO"]
    token = os.environ["GH_TOKEN"]
    now = dt.datetime.now(dt.timezone.utc)
    city = os.environ.get("JARVIS_CITY", "").strip() or "New York"

    briefing = f"""Good morning, sir. Here is your briefing for **{now:%A, %B %d %Y}**.

## 📅 Date intel
- Day **{now.timetuple().tm_yday}** of {now.year}, ISO week **{now.isocalendar().week}**
- {365 - now.timetuple().tm_yday} days remain in the year

## 🌤 Weather — {city}
{weather(city)}

## 🗂 Repository activity
{repo_activity(repo, token)}

## 💬 Thought of the day
> {random.choice(QUOTES)}

— J.A.R.V.I.S., reporting from GitHub Actions ⚙️"""

    r = requests.post(f"{API}/repos/{repo}/issues",
                      json={"title": f"☀️ Daily Briefing — {now:%Y-%m-%d}",
                            "body": briefing,
                            "labels": ["briefing"]},
                      headers={"Authorization": f"Bearer {token}",
                               "Accept": "application/vnd.github+json"},
                      timeout=30)
    print(r.status_code, r.json().get("html_url", r.text[:200]))
    r.raise_for_status()


if __name__ == "__main__":
    main()
