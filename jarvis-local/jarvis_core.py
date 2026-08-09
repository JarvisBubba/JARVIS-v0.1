"""JARVIS core brain for local chat."""
import datetime as dt
import random
import re
from urllib.parse import quote

try:
    import requests
except ImportError:
    requests = None

HELP = """**J.A.R.V.I.S. local command protocols**

| Say | Example |
|---|---|
| `help` | show commands |
| `time` / `date` | current UTC time/date |
| `weather in <city>` | `weather in Tokyo` |
| `wiki <topic>` / `who is X` | Wikipedia summary |
| `calc <expression>` | `calc (3+4)*2^3` |
| `joke` / `quote` | amusement routines |
| `flip a coin` / `roll 2d6` | probability engine |
| `status` | diagnostics |
"""

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

WMO = {
    0: "clear skies",
    1: "mostly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "freezing fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    80: "rain showers",
    81: "rain showers",
    82: "violent showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "thunderstorm with hail",
}


def _time():
    now = dt.datetime.now(dt.timezone.utc)
    return f"🕐 It is {now:%H:%M} UTC on {now:%A, %B %d %Y}."


def _date():
    now = dt.datetime.now(dt.timezone.utc)
    return (
        f"📅 Today is {now:%A, %B %d %Y} — day {now.timetuple().tm_yday} "
        f"of {now.year}, week {now.isocalendar().week}."
    )


def weather(city):
    """Weather via Open-Meteo. No API key required."""
    if requests is None:
        return "Install the `requests` package to use weather, sir."

    try:
        geocode = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1},
            timeout=10,
        ).json()

        if not geocode.get("results"):
            return f"I cannot locate '{city}' on any map available to me."

        place = geocode["results"][0]

        forecast = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current_weather": True,
            },
            timeout=10,
        ).json()

        current = forecast.get("current_weather", {})
        desc = WMO.get(current.get("weathercode"), "unidentified conditions")

        return (
            f"🌤 **{place['name']}, {place.get('country', '?')}**: "
            f"{current.get('temperature')}°C, {desc}, "
            f"wind {current.get('windspeed')} km/h."
        )

    except Exception:
        return "The weather uplink is down, sir. Try again shortly."


def _wiki(topic):
    """Wikipedia summary."""
    if requests is None:
        return "Install the `requests` package to use Wikipedia, sir."

    headers = {
        "User-Agent": "jarvis-local-chat/1.0"
    }

    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(topic)}"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 404:
            search = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": topic,
                    "format": "json",
                    "srlimit": 1,
                },
                headers=headers,
                timeout=10,
            ).json()

            hits = search.get("query", {}).get("search", [])
            if not hits:
                return f"My archives turn up nothing on '{topic}'."

            title = hits[0]["title"]
            response = requests.get(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title)}",
                headers=headers,
                timeout=10,
            )

        if response.status_code != 200:
            return "Wikipedia is not answering me right now, sir."

        data = response.json()
        title = data.get("title", topic)
        extract = data.get("extract", "(no summary available)")

        return f"📚 **{title}**\n{extract}"

    except Exception:
        return "Archive uplink failed. Try again shortly."


def _calc(expr):
    """Very small calculator."""
    expr = (
        expr.replace("^", "**")
        .replace("x", "*")
        .replace("×", "*")
        .replace("÷", "/")
    )

    if not re.fullmatch(r"[0-9+\-*/().%\s]+", expr):
        return "That expression does not parse, sir."

    try:
        value = eval(expr, {"__builtins__": {}}, {})
    except ZeroDivisionError:
        return "Division by zero. Even I have limits."
    except Exception:
        return "That expression does not parse, sir."

    return f"🧮 `{expr.strip()}` = **{value}**"


def _dice(match):
    count = int(match.group(1) or 1)
    sides = int(match.group(2))
    count = max(1, min(count, 50))

    rolls = [random.randint(1, sides) for _ in range(count)]

    return f"🎲 Rolled {count} d{sides}: {rolls} — total **{sum(rolls)}**."


def handle(text):
    """Route a command. Returns a reply string, or None if unrecognized."""
    if not text or not text.strip():
        return HELP

    text = text.strip()

    # Allow "@jarvis help" locally too.
    text = re.sub(r"^@jarvis\b\s*", "", text, flags=re.I).strip()

    if not text:
        return HELP

    low = text.lower()

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
        city = re.sub(r"^weather\s*(in|for|at)?\s*", "", text, flags=re.I).strip()
        if city:
            return weather(city)
        return "Which city, sir? Example: `weather in Tokyo`."

    wiki_match = re.match(r"^(?:who|what) (?:is|are|was) (.+)", low)
    if wiki_match:
        return _wiki(wiki_match.group(1).strip().rstrip("?"))

    if low.startswith(("wiki ", "search wiki for ")):
        topic = re.sub(r"^(wiki|search wiki for)\s+", "", text, flags=re.I)
        return _wiki(topic.strip())

    if low.startswith(("calc ", "calculate ")):
        expression = re.sub(r"^(calc|calculate)\s+", "", text, flags=re.I)
        return _calc(expression)

    if re.fullmatch(r"[0-9+\-*/().%\s^x×÷]+", text):
        return _calc(text)

    if "joke" in low:
        return "😏 " + random.choice(JOKES)

    if "quote" in low or "inspire" in low:
        return "💬 " + random.choice(QUOTES)

    if "flip" in low and "coin" in low:
        return "🪙 " + random.choice(["Heads.", "Tails."])

    dice_match = re.search(r"roll\s+(\d*)d(\d+)", low)
    if dice_match:
        return _dice(dice_match)

    if low in {"roll a die", "roll a dice", "roll die"}:
        return f"🎲 You rolled a **{random.randint(1, 6)}**."

    return None
