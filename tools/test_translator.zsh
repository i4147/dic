python - <<'PY'
import requests
for url in ("https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=fa&dt=t&q=hello",
            "https://api.mymemory.translated.net/get?q=hello&langpair=en|fa"):
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        print("OK ", r.status_code, url.split('/')[2])
    except Exception as e:
        print("XX ", url.split('/')[2], "→", e)
PY