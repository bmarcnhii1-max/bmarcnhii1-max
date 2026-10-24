"""Daily joke card: fetch EN programmer joke, translate to RU, render dark SVG."""
import html
import json
import textwrap
import urllib.parse
import urllib.request

UA = {"User-Agent": "bmarcnhii1-max-profile/1.0"}


def http_get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", errors="replace")


def fetch_joke():
    # Official Joke API, programming only, safe mode
    st, body = http_get(
        "https://official-joke-api.appspot.com/jokes/programming/random"
    )
    if st != 200:
        raise RuntimeError(f"joke api HTTP {st}")
    data = json.loads(body)
    item = data[0] if isinstance(data, list) else data
    setup = (item.get("setup") or "").strip()
    punch = (item.get("punchline") or "").strip()
    if not setup or not punch:
        raise RuntimeError("empty joke")
    return setup, punch


def translate(text):
    # Primary: unofficial Google endpoint, no key. Fallback: MyMemory.
    try:
        q = urllib.parse.quote(text)
        url = (
            "https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl=en&tl=ru&dt=t&q={q}"
        )
        st, body = http_get(url)
        if st == 200:
            data = json.loads(body)
            out = "".join(seg[0] for seg in data[0] if seg[0])
            if out.strip():
                return out.strip()
    except Exception:
        pass
    try:
        q = urllib.parse.quote(text)
        url = f"https://api.mymemory.translated.net/get?q={q}&langpair=en|ru"
        st, body = http_get(url)
        if st == 200:
            out = json.loads(body).get("responseData", {}).get("translatedText", "")
            if out.strip() and "QUERY LENGTH LIMIT" not in out:
                return out.strip()
    except Exception:
        pass
    return text


def esc(s):
    return html.escape(s, quote=False)


def render(setup, punch):
    lines = textwrap.wrap(setup, 52) + [""] + textwrap.wrap(punch, 52)
    lines = lines[:8]
    h = 34 + len(lines) * 24 + 30
    parts = []
    for i, line in enumerate(lines):
        y = 58 + i * 24
        parts.append(
            f'<text x="24" y="{y}" font-family="monospace" font-size="14" '
            f'fill="#c9d1d9">{esc(line)}</text>'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="{h}">
<rect width="600" height="{h}" rx="8" fill="#0d1117" stroke="#30363d"/>
<text x="24" y="30" font-family="monospace" font-size="13" fill="#30d158">шутка дня &#8226; en&#8594;ru, машинный перевод</text>
{"".join(parts)}
</svg>
"""


def main():
    try:
        setup, punch = fetch_joke()
        setup_ru = translate(setup)
        punch_ru = translate(punch)
    except Exception as e:
        setup_ru, punch_ru = "Шутка не подъехала", f"апишка упала: {e}"[:90]
    with open("joke.svg", "w", encoding="utf-8") as f:
        f.write(render(setup_ru, punch_ru))
    print("joke.svg written")


if __name__ == "__main__":
    main()
