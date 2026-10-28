#!/usr/bin/env python3
"""
Fast English → Persian (Farsi) batch translator via Google Translate gtx.

Speed-ups vs the original:
  • Concurrent chunk workers (ThreadPoolExecutor)
  • Shared token-bucket rate limiter instead of fixed 1.5 s sleeps
  • Larger default chunks, fewer round-trips
  • Adaptive backoff only on real errors / 429
  • Atomic resume + periodic flush preserved
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from urllib3.util.retry import Retry as U3Retry

# ── config (override via env) ───────────────────────────────────────────────
INPUT_FILE = sys.argv[1] if len(sys.argv) > 1 else "en.txt"
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "en-fa.json")

MAX_CHARS = int(os.environ.get("MAX_CHARS", "3000"))
MAX_WORDS = int(os.environ.get("MAX_WORDS", "150"))
SAVE_EVERY = int(os.environ.get("SAVE_EVERY", "80"))
TIMEOUT = float(os.environ.get("TIMEOUT", "25"))
MAX_ATTEMPTS = int(os.environ.get("MAX_ATTEMPTS", "3"))
WORKERS = int(os.environ.get("WORKERS", "8"))  # parallel chunks
RATE_PER_SEC = float(os.environ.get("RATE", "4.0"))
MIN_INTERVAL = 1.0 / RATE_PER_SEC

PERSIAN_RE = re.compile(r"[\u0600-\u06FF]")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"

# ── shared session (thread-safe for our use) ────────────────────────────────
_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": UA})
_SESSION.mount(
    "https://",
    HTTPAdapter(
        pool_connections=WORKERS + 2,
        pool_maxsize=WORKERS + 2,
        max_retries=U3Retry(
            total=2,
            backoff_factor=0.8,
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False,
        ),
    ),
)


# ── rate limiter (token bucket, thread-safe) ────────────────────────────────
class RateLimiter:
    def __init__(self, rate: float) -> None:
        self.rate = max(rate, 0.1)
        self._tokens = self.rate
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last
            self._tokens = min(self.rate, self._tokens + elapsed * self.rate)
            self._last = now
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return
            wait = (1.0 - self._tokens) / self.rate
            self._tokens = 0.0
            self._last = now + wait
        time.sleep(wait)


_LIMITER = RateLimiter(RATE_PER_SEC)
_print_lock = threading.Lock()


def log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


class BadTranslation(Exception):
    pass


def _persian(t: str | None) -> bool:
    return bool(PERSIAN_RE.search(t or ""))


def _validate_single(word: str, out: str) -> str:
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
    wait=wait_exponential(multiplier=1.5, min=1, max=20),
    stop=stop_after_attempt(MAX_ATTEMPTS),
    reraise=True,
)
def translate_gtx(text: str) -> str:
    _LIMITER.acquire()
    r = _SESSION.get(
        "https://translate.googleapis.com/translate_a/single",
        params={"client": "gtx", "sl": "en", "tl": "fa", "dt": "t", "q": text},
        timeout=TIMEOUT,
    )
    if r.status_code == 429:
        raise BadTranslation("rate-limited (429)")
    r.raise_for_status()
    data = r.json()
    if not data or not data[0]:
        raise BadTranslation("empty gtx response")
    out = "".join(chunk[0] for chunk in data[0] if chunk and chunk[0])
    if not out:
        raise BadTranslation("empty joined translation")
    return out


def translate_chunk(chunk: list[str]) -> dict[str, str]:
    """Return {word: fa} for successful translations."""
    out: dict[str, str] = {}
    joined = "\n".join(chunk)
    try:
        translated = translate_gtx(joined)
    except Exception as e:
        log(f"  ✗ batch failed ({e}) — per-word fallback")
        for w in chunk:
            try:
                out[w] = _validate_single(w, translate_gtx(w))
            except Exception as e2:
                log(f"    ✗ {w!r}: {e2}")
        return out

    parts = translated.strip().split("\n")
    if len(parts) == len(chunk):
        for w, p in zip(chunk, parts):
            try:
                out[w] = _validate_single(w, p)
            except BadTranslation as e:
                log(f"  ↻ {w!r}: {e} — solo retry")
                try:
                    out[w] = _validate_single(w, translate_gtx(w))
                except Exception as e2:
                    log(f"    ✗ {w!r}: {e2}")
    else:
        log(f"  ⚠️  line-count mismatch ({len(parts)} vs {len(chunk)}) — per-word fallback")
        for w in chunk:
            try:
                out[w] = _validate_single(w, translate_gtx(w))
            except Exception as e:
                log(f"    ✗ {w!r}: {e}")
    return out


def make_chunks(
    words: list[str],
    max_chars: int = MAX_CHARS,
    max_words: int = MAX_WORDS,
):
    chunk: list[str] = []
    chars = 0
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


def load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        os.replace(path, path + ".corrupt")
        log(f"⚠️  corrupt JSON backed up to {path}.corrupt")
        return {}


def save_json_atomic(data: dict, path: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def main() -> None:
    if not os.path.exists(INPUT_FILE):
        sys.exit(f"❌ not found: {INPUT_FILE}")

    seen: set[str] = set()
    words: list[str] = []
    with open(INPUT_FILE, encoding="utf-8-sig") as f:
        for line in f:
            w = line.strip()
            if w and w not in seen:
                seen.add(w)
                words.append(w)

    translations = load_json(OUTPUT_FILE)
    pending = [w for w in words if w not in translations]
    log(f"📄 {len(words)} unique | 💾 done: {len(translations)} | ⏳ pending: {len(pending)}")
    if not pending:
        log("✅ nothing to do.")
        return

    chunks = list(make_chunks(pending))
    log(f"📦 {len(chunks)} chunks | workers={WORKERS} | rate≈{RATE_PER_SEC}/s | max_chars={MAX_CHARS}\n")

    lock = threading.Lock()
    ok = fail = 0
    flush_count = 0
    t0 = time.monotonic()

    def process(ci: int, chunk: list[str]) -> tuple[int, dict[str, str], int]:
        log(f"[chunk {ci}/{len(chunks)}] {len(chunk)} words")
        results = translate_chunk(chunk)
        return ci, results, len(chunk) - len(results)

    try:
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futs = {pool.submit(process, ci, chunk): ci for ci, chunk in enumerate(chunks, 1)}
            for fut in as_completed(futs):
                try:
                    ci, results, nfail = fut.result()
                except Exception as e:
                    log(f"  ✗ worker error: {e}")
                    continue
                with lock:
                    for w, fa in results.items():
                        translations[w] = fa
                        ok += 1
                        flush_count += 1
                        log(f"  ✓ {w} → {fa}")
                    fail += nfail
                    if flush_count >= SAVE_EVERY:
                        save_json_atomic(translations, OUTPUT_FILE)
                        log(f"--- 💾 flushed {len(translations)} pairs ---")
                        flush_count = 0
    except KeyboardInterrupt:
        log("\n\n⛔ interrupted by user.")
    finally:
        save_json_atomic(translations, OUTPUT_FILE)
        elapsed = time.monotonic() - t0
        rate = ok / elapsed if elapsed > 0 else 0
        log(f"\n💾 saved {len(translations)} pairs → {OUTPUT_FILE}")
        log(f"   this run: ✔ {ok}  ✘ {fail}  ⏱ {elapsed:.1f}s  ({rate:.1f} words/s)")
        if fail:
            log("   re-run the same command to retry the failed words.")


if __name__ == "__main__":
    main()
