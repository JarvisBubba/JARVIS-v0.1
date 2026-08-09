#!/usr/bin/env python3
"""JARVIS local voice console.  Run: python jarvis.py  (add --text for keyboard)."""
import argparse, datetime as dt, json, os, re, sys, webbrowser

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot"))
from jarvis_core import handle  # noqa: E402

try: import pyttsx3
except ImportError: pyttsx3 = None
try: import speech_recognition as sr
except ImportError: sr = None

REMINDERS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reminders.json")
SITES = {"youtube": "https://youtube.com", "google": "https://google.com",
         "github": "https://github.com", "twitter": "https://x.com"}


class Jarvis:
    def __init__(self, text_mode=False):
        self.text_mode = text_mode or sr is None
        self.engine = None
        if pyttsx3:
            try:
                self.engine = pyttsx3.init()
                self.engine.setProperty("rate", 185)
            except Exception:
                pass
        self.rec = sr.Recognizer() if sr else None

    def say(self, text):
        print(f"JARVIS ▸ {text}")
        if self.engine:
            try:
                self.engine.say(text); self.engine.runAndWait()
            except Exception:
                pass

    def hear(self):
        if self.text_mode:
            try: return input("YOU    ▸ ").strip()
            except (EOFError, KeyboardInterrupt): sys.exit(0)
        try:
            with sr.Microphone() as src:
                print("… listening")
                audio = self.rec.listen(src, timeout=6, phrase_time_limit=12)
            text = self.rec.recognize_google(audio)
            print(f"YOU    ▸ {text}")
            return text
        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            return ""
        except Exception:
            self.say("Speech service unavailable, sir. Switching to text mode.")
            self.text_mode = True
            return ""

    # ---- local-only actions ----
    def _load_rems(self):
        try:
            with open(REMINDERS) as f: return json.load(f)
        except Exception: return []

    def check_reminders(self):
        now = dt.datetime.now()
        keep, due = [], [r for r in self._load_rems()
                         if dt.datetime.fromisoformat(r["due"]) <= now]
        for r in self._load_rems():
            if dt.datetime.fromisoformat(r["due"]) > now: keep.append(r)
        for r in due: self.say(f"Reminder, sir: {r['text']}")
        if due:
            with open(REMINDERS, "w") as f: json.dump(keep, f)

    def respond(self, text):
        low = text.lower().strip()
        if low.startswith("jarvis"): low = low[6:].strip(); text = text.strip()[6:].strip()
        if not low: return
        if low in {"exit", "quit", "goodbye", "shutdown"}:
            self.say("Powering down. Try not to break anything without me."); sys.exit(0)

        m = re.match(r"open (\w+)", low)
        if m and m.group(1) in SITES:
            webbrowser.open(SITES[m.group(1)]); self.say(f"Opening {m.group(1)}."); return
        m = re.match(r"search (?:for )?(.+)", low)
        if m:
            webbrowser.open("https://www.google.com/search?q=" + m.group(1))
            self.say("Searching now."); return
        m = re.match(r"remind me to (.+?) at (\d{1,2}):(\d{2})", low)
        if m:
            due = dt.datetime.now().replace(hour=int(m.group(2)), minute=int(m.group(3)),
                                            second=0, microsecond=0)
            if due <= dt.datetime.now(): due += dt.timedelta(days=1)
            rems = self._load_rems(); rems.append({"text": m.group(1), "due": due.isoformat()})
            with open(REMINDERS, "w") as f: json.dump(rems, f)
            self.say(f"Noted. I will remind you at {due:%H:%M}."); return
        if low in {"reminders", "show reminders"}:
            rems = self._load_rems()
            self.say(", ".join(f"{r['text']} at {r['due'][11:16]}" for r in rems)
                     if rems else "No reminders pending."); return

        answer = handle(text)
        self.say(answer if answer else "I don't have a protocol for that, sir. Say 'help'.")


def main():
    ap = argparse.ArgumentParser(description="JARVIS local console")
    ap.add_argument("--text", action="store_true", help="keyboard mode (no mic)")
    args = ap.parse_args()
    j = Jarvis(args.text)
    j.say("Jarvis online. How may I help, sir?")
    while True:
        j.check_reminders()
        j.respond(j.hear())


if __name__ == "__main__":
    main()
