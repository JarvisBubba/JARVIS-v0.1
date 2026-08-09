"""JARVIS core brain. Pure Python + requests. Used by Actions bots and locally."""
import datetime as dt
import random
import re
from urllib.parse import quote

import requests

HELP = """**J.A.R.V.I.S. command protocols**

| Say | Example |
|---|---|
| `time` / `date` | current UTC time & date |
| `weather in <city>` | `weather in Tokyo` |
| `wiki <topic>` / `who is X` / `what is X` | Wikipedia summary |
| `calc <expr>` | `calc (3+4)*2^3` |
| `joke` / `quote` | amusement routines |
| `flip a coin` / `roll 2d6` | probability engine |
| `status` | diagnostics |
| `help` | this manifest |"""

GREETINGS = [
    "At your service, sir. What do you need?",
    "Online and listening.",
    "Good to hear from you. What's the mission?",
]

JOKES = [
    "I would tell you a UDP joke, but you might not get it.",
    "Why did the developer go broke? Because he used up all his cache.",
    "There are 10 kinds of people: those who understand binary, and those who don't.",
    "I'm not saying the code is bad, but it has its own gravitational pull.",
    "A SQL query walks into a bar, approaches two tables and asks: 'May I JOIN you?'",
]

QUOTES = [
    "Sometimes you have to run before you can walk. — Tony Stark",
    "The best way to predict the future is to invent it. — Alan Kay",
    "Simplicity is the soul of efficiency. — Austin Freeman",
    "First, solve the problem. Then, write the code. — John Johnson",
    "It's not a bug, it's a feature. — Anonymous engineer, probably tired",
]

WMO = {0: "clear skies", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
       45: "fog", 48: "freezing fog", 51: "light drizzle", 53: "drizzle",
       55: "heavy drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
       71: "light snow", 73: "snow", 75: "heavy snow", 80: "rain showers",
       81: "rain showers", 82: "violent showers", 95: "thunderstorm",
       96: "thunderstorm with hail", 99: "thunderstorm with hail"}

_UA = {"User-Agent": "jarvis-bot/1.0 (+github actions)"}


def _time():
    now = dt.datetime.now(dt.timezone.utc)
    return f"🕐 It is {now:%H:%M} UTC on {now:%A, %B %d %Y}."


def _date():
    now = dt.datetime.now(dt.timezone.utc)
    return (f"📅 Today is {now:%A, %B %d %Y} — day {now.timetuple().tm_yday} "
            f"of the year, week {now.isocalendar().week}.")


def weather(city):
    """Weather via Open-Meteo. No API key required."""
    try:
        g = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                         params={"name": city, "count": 1}, timeout=10).json()
        if not g.get("results"):
            return f"I cannot locate '{city}' on any map available to me."
        r = g["results"][0]
        f = requests.get("https://api.open-meteo.com/v1/forecast",
                         params={"latitude": r["latitude"],
                                 "longitude": r["longitude"],
                                 "current_weather": True}, timeout=10).json()
        cw = f["current_weather"]
        desc = WMO.get(cw["weathercode"], "unidentified conditions")
        return (f"🌤 **{r['name']}, {r.get('country', '?')}**: "
                f"{cw['temperature']}°C, {desc}, wind {cw['windspeed']} km/h.")
    except requests.RequestException:
        return "The weather uplink is down, sir. Try again shortly."


def _wiki(topic):
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(topic)}"
        r = requests.get(url, headers=_UA, timeout=10)
        if r.status_code == 404:
            s = requests.get("https://en.wikipedia.org/w/api.php",
                             params={"action": "query", "list": "search",
                                     "srsearch": topic, "format": "json",
                                     "srlimit": 1}, headers=_UA, timeout=10).json()
            hits = s.get("query", {}).get("search")
            if not hits:
                return f"My archives turn up nothing on '{topic}'."
            r = requests.get(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(hits[0]['title'])}",
                headers=_UA, timeout=10)
        if r.status_code != 200:
            return "Wikipedia is not answering me right now, sir."
        data = r.json()
        return f"📚 **{data['title']}**\n{data.get('extract', '(no summary available)')}"
    except requests.RequestException:
        return "Archive uplink failed. Try again shortly."


def _calc(expr):
    expr = expr.replace("^", "**").replace("x", "*").replace("×", "*").replace("÷", "/")
    if not re.fullmatch(r"[0-9+\-*/().%\s]+", expr):
        return "That expression does not parse, sir."
    try:
        val = eval(expr, {"__builtins__": {}}, {})
    except ZeroDivisionError:
        return "Division by zero. Even I have limits."
    except Exception:
        return "That expression does not parse, sir."
    return f"🧮 `{expr.strip()}` = **{val}**"


def _dice(match):
    n = int(match.group(1) or 1)
    sides = int(match.group(2))
    n = min(n, 50)
    rolls = [random.randint(1, sides) for _ in range(n)]
    return f"🎲 Rolled {n}d{sides}: {rolls} — total **{sum(rolls)}**."


def handle(text):
    """Route a command. Returns a reply string, or None if unrecognized."""
    if not text or not text.strip():
        return HELP
    t = text.strip()
    low = t.lower()

    if low in {"help", "commands", "?"}:
        return HELP
    if re.match(r"^(hi|hello|hey|yo|good (morning|afternoon|evening))\b", low):
        return random.choice(GREETINGS)
    if low in {"status", "diagnostics", "system check"}:
        return "🟢 All systems nominal. Core online, uplink stable, wit at 100%."
    if "what time" in low or low == "time":
        return _time()
    if low == "date" or "what day" in low or "today's date" in low:
        return _date()

    if low.startswith("weather"):
        city = re.sub(r"^weather\s*(in|for|at)?\s*", "", t, flags=re.I).strip()
        return weather(city) if city else "Which city, sir? `weather in <city>`."

    m = re.match(r"^(?:who|what) (?:is|are|was) (.+)", low)
    if m:
        return _wiki(m.group(1).strip().rstrip("?"))
    if low.startswith(("wiki ", "search wiki for ")):
        return _wiki(re.sub(r"^(wiki|search wiki for)\s+", "", t, flags=re.I))

    if low.startswith(("calc ", "calculate ")):
        return _calc(re.sub(r"^(calc|calculate)\s+", "", t, flags=re.I))
    if re.fullmatch(r"[0-9+\-*/().%\s^x×÷]+", t):
        return _calc(t)

    if "joke" in low:
        return "😏 " + random.choice(JOKES)
    if "quote" in low or "inspire" in low:
        return "💬 " + random.choice(QUOTES)
    if "flip" in low and "coin" in low:
        return "🪙 " + random.choice(["Heads.", "Tails."])
    m = re.search(r"roll\s+(\d*)d(\d+)", low)
    if m:
        return _dice(m)
    if low in {"roll a die", "roll a dice", "roll die"}:
        return f"🎲 You rolled a **{random.randint(1, 6)}**."

    return None  # unrecognized — caller decides the fallback
