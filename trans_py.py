import sys, os, re, json, time
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry as U3Retry

INPUT_FILE = sys.argv[1] if len(sys.argv) > 1 else "en.txt"
OUTPUT_FILE = "en-fa.json"
MAX_CHARS = 2500
MAX_WORDS = 100
SAVE_EVERY = 50
TIMEOUT = 30
DELAY = 1.5
MAX_ATTEMPTS = 4
PERSIAN_RE = re.compile(r"[\u0600-\u06FF]")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
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
    pass


def _persian(t):
    return bool(PERSIAN_RE.search(t or ""))


def _validate_single(word, out):
    if not out:
        raise BadTranslation(f"empty for {word!r}")
    out = out.strip()
    if out.lower() == word.strip().lower():
        raise BadTranslation(f"echoed for {word!r}")
    if not _persian(out):
        raise BadTranslation(f"non-Persian for {word!r}: {out!r}")
    return out


@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    stop=stop_after_attempt(MAX_ATTEMPTS),
    reraise=True,
)
def translate_gtx(text):
    r = SESSION.get(
        "https://translate.googleapis.com/translate_a/single",
        params={"client": "gtx", "sl": "en", "tl": "fa", "dt": "t", "q": text},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    if not data or not data[0]:
        raise BadTranslation("empty gtx response")
    out = "".join(chunk[0] for chunk in data[0] if chunk and chunk[0])
    if not out:
        raise BadTranslation("empty joined translation")
    return out


def translate_chunk(chunk):
    """Return {word: fa} for successful translations; log failures."""
    out = {}
    joined = "\n".join(chunk)
    try:
        translated = translate_gtx(joined)
    except Exception as e:
        print(f"  ✗ batch failed ({e}) — per-word fallback")
        for w in chunk:
            try:
                out[w] = translate_gtx(w)
            except Exception as e2:
                print(f"    ✗ {w!r}: {e2}")
            time.sleep(DELAY)
        return out
    parts = translated.strip().split("\n")
    if len(parts) == len(chunk):
        for w, p in zip(chunk, parts):
            try:
                out[w] = _validate_single(w, p)
            except BadTranslation as e:
                print(f"  ↻ {w!r}: {e} — solo retry")
                try:
                    out[w] = translate_gtx(w)
                except Exception as e2:
                    print(f"    ✗ {w!r}: {e2}")
                time.sleep(DELAY)
    else:
        print(f"  ⚠️  line-count mismatch ({len(parts)} vs {len(chunk)}) — per-word fallback")
        for w in chunk:
            try:
                out[w] = translate_gtx(w)
            except Exception as e:
                print(f"    ✗ {w!r}: {e}")
            time.sleep(DELAY)
    return out


def make_chunks(words, max_chars=MAX_CHARS, max_words=MAX_WORDS):
    """Group whole words into ~max_chars chunks; never split a word."""
    chunk, chars = [], 0
    for w in words:
        wsize = len(w) + 1
        if chunk and (chars + wsize > max_chars or len(chunk) >= max_words):
            yield chunk
            chunk, chars = [w], len(w)
        else:
            chunk.append(w)
            chars += wsize
    if chunk:
        yield chunk


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
        sys.exit(f"❌ not found: {INPUT_FILE}")
    seen, words = set(), []
    with open(INPUT_FILE, encoding="utf-8-sig") as f:
        for line in f:
            w = line.strip()
            if w and w not in seen:
                seen.add(w)
                words.append(w)
    translations = load_json(OUTPUT_FILE)
    pending = [w for w in words if w not in translations]
    print(f"📄 {len(words)} unique | 💾 done: {len(translations)} | ⏳ pending: {len(pending)}")
    if not pending:
        print("✅ nothing to do.")
        return
    chunks = list(make_chunks(pending))
    print(f"📦 {len(chunks)} chunks (~{MAX_CHARS} chars each)\n")
    flush = ok = fail = 0
    try:
        for ci, chunk in enumerate(chunks, 1):
            print(f"[chunk {ci}/{len(chunks)}] {len(chunk)} words")
            results = translate_chunk(chunk)
            for w, fa in results.items():
                translations[w] = fa
                ok += 1
                flush += 1
                print(f"  ✓ {w} → {fa}")
            fail += len(chunk) - len(results)
            if flush >= SAVE_EVERY:
                save_json_atomic(translations, OUTPUT_FILE)
                print(f"--- 💾 flushed {len(translations)} pairs ---")
                flush = 0
            time.sleep(DELAY)
    except KeyboardInterrupt:
        print("\n\n⛔ interrupted by user.")
    finally:
        save_json_atomic(translations, OUTPUT_FILE)
        print(f"\n💾 saved {len(translations)} pairs → {OUTPUT_FILE}")
        print(f"   this run: ✔ {ok}  ✘ {fail}")
        if fail:
            print("   re-run the same command to retry the failed words.")


if __name__ == "__main__":
    main()
