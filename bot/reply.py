"""Reads the triggering issue comment from env, posts JARVIS's reply."""
import os
import re
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jarvis_core import HELP, handle  # noqa: E402

API = "https://api.github.com"


def llm_answer(query):
    """Optional free-form fallback when OPENAI_API_KEY secret is set."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": "gpt-4o-mini",
                  "messages": [
                      {"role": "system",
                       "content": "You are JARVIS: a concise, dry-witted assistant. "
                                  "Answer in under 150 words, light markdown ok."},
                      {"role": "user", "content": query}],
                  "max_tokens": 500},
            timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def main():
    if os.environ.get("COMMENT_AUTHOR", "").endswith("[bot]"):
        return  # never talk to other bots

    body = os.environ.get("COMMENT_BODY", "")
    m = re.search(r"@jarvis\b\s*(.*)", body, re.I | re.S)
    query = (m.group(1) if m else body).strip()

    answer = handle(query) if query else HELP
    if answer is None:
        answer = llm_answer(query)
    if answer is None:
        answer = ("I don't have a protocol for that yet, sir. "
                  "Try `@jarvis help` to see what I can do.")

    payload = f"> {query}\n\n{answer}" if query else answer
    r = requests.post(
        f"{API}/repos/{os.environ['REPO']}/issues/{os.environ['ISSUE_NUMBER']}/comments",
        json={"body": payload},
        headers={"Authorization": f"Bearer {os.environ['GH_TOKEN']}",
                 "Accept": "application/vnd.github+json"},
        timeout=30)
    print(r.status_code)
    r.raise_for_status()


if __name__ == "__main__":
    main()
