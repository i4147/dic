"""
Translate English words → Persian (fa), resilient to blocked endpoints.
Backends tried in order until one succeeds:
  1) translate.googleapis.com   (raw HTTP, no library)
  2) MyMemory free API           (different infra, works from IR)
  3) Bing via 'translators' pkg  (optional 3rd fallback)

Features:
- tenacity retries with exponential backoff per backend
- Cycles through backends on failure (a word isn't abandoned until all fail)
- Ctrl+C safe, resume from existing JSON, atomic flush every 50 pairs
- Optional HTTPS_PROXY via env var (requests honours it automatically)

Usage: python translate.py [en.txt]
Output: en-fa.json
"""

import sys, os, re, json, time
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
)
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry as U3Retry

INPUT_FILE = sys.argv[1] if len(sys.argv) > 1 else "en.txt"
OUTPUT_FILE = "en-fa.json"
SAVE_EVERY = 50
TIMEOUT = 30
DELAY = 1.5
MAX_ATTEMPTS = 4
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
PERSIAN_RE = re.compile(r"[\u0600-\u06FF]")
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA})
SESSION.mount(
    "https://",
    HTTPAdapter(
        max_retries=U3Retry(
            total=2,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
    ),
)


class BadTranslation(Exception):
    """Echoed original, empty, non-Persian, or rate-limit sentinel."""


def _validate(word, out):
    if not out:
        raise BadTranslation(f"empty output for {word!r}")
    out = out.strip()
    if out.lower() == word.strip().lower():
        raise BadTranslation(f"echoed original for {word!r}")
    if "MYMEMORY WARNING" in out.upper() or "QUERY LENGTH LIMIT" in out.upper():
        raise BadTranslation(f"rate limit sentinel for {word!r}")
    if not PERSIAN_RE.search(out):
        raise BadTranslation(f"no Persian chars in output for {word!r}: {out!r}")
    return out


@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    stop=stop_after_attempt(MAX_ATTEMPTS),
    reraise=True,
)
def backend_gtx(word):
    r = SESSION.get(
        "https://translate.googleapis.com/translate_a/single",
        params={"client": "gtx", "sl": "en", "tl": "fa", "dt": "t", "q": word},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    out = "".join(chunk[0] for chunk in data[0] if chunk and chunk[0])
    return _validate(word, out)


@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    stop=stop_after_attempt(MAX_ATTEMPTS),
    reraise=True,
)
def backend_mymemory(word):
    r = SESSION.get(
        "https://api.mymemory.translated.net/get",
        params={"q": word, "langpair": "en|fa"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("responseStatus") not in (200, "200"):
        raise BadTranslation(f"MyMemory status {data.get('responseStatus')}")
    return _validate(word, data.get("responseData", {}).get("translatedText", ""))


def backend_bing(word):
    try:
        import translators as ts
    except ImportError:
        raise BadTranslation("translators package not installed")
    out = ts.translate_text(word, translator="bing", from_language="en", to_language="fa")
    return _validate(word, out)


BACKENDS = [
    ("gtx", backend_gtx),
    ("mymemory", backend_mymemory),
    ("bing", backend_bing),
]


def translate_word(word):
    """Try each backend in turn; return (text, backend_name)."""
    last_err = None
    for name, fn in BACKENDS:
        try:
            return fn(word), name
        except RetryError as e:
            last_err = f"{name}: {e.last_attempt.exception() if e.last_attempt else e}"
        except Exception as e:
            last_err = f"{name}: {e}"
    raise BadTranslation(last_err or "all backends failed")


def load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        os.replace(path, path + ".corrupt")
        print(f"⚠️  corrupt JSON backed up to {path}.corrupt")
        return {}


def save_json_atomic(data, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def main():
    if not os.path.exists(INPUT_FILE):
        sys.exit(f"❌ input file not found: {INPUT_FILE}")
    seen, words = set(), []
    with open(INPUT_FILE, encoding="utf-8-sig") as f:
        for line in f:
            w = line.strip()
            if w and w not in seen:
                seen.add(w)
                words.append(w)
    translations = load_json(OUTPUT_FILE)
    pending = [w for w in words if w not in translations]
    print(f"📄 {len(words)} unique words | 💾 already done: {len(translations)} | ⏳ pending: {len(pending)}\n")
    if not pending:
        print("✅ nothing to do.")
        return
    flush = ok = fail = 0
    stats = {name: 0 for name, _ in BACKENDS}
    try:
        for i, word in enumerate(pending, 1):
            try:
                fa, via = translate_word(word)
                translations[word] = fa
                ok += 1
                flush += 1
                stats[via] += 1
                print(f"[{i}/{len(pending)}] {word} → {fa}   ({via})")
            except Exception as e:
                fail += 1
                print(f"[{i}/{len(pending)}] ❌ {word!r}: {e}")
            if flush >= SAVE_EVERY:
                save_json_atomic(translations, OUTPUT_FILE)
                print(f"--- 💾 flush: {len(translations)} pairs ---")
                flush = 0
            time.sleep(DELAY)
    except KeyboardInterrupt:
        print("\n\n⛔ interrupted.")
    finally:
        save_json_atomic(translations, OUTPUT_FILE)
        print(f"\n💾 saved {len(translations)} pairs → {OUTPUT_FILE}")
        print(f"   this run: ✔ {ok}  ✘ {fail}   backends: {stats}")
        if fail:
            print("   re-run the same command to retry failed words.")


if __name__ == "__main__":
    main()
