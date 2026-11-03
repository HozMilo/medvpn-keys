"""Читает публичный канал Telegram и сохраняет свежие ключи в keys.json.

Формат совпадает с ответом сервера /current: {link, keys, updated, checked}.
Если канал не открылся или ключей нет, старый файл не трогаем.
"""
import html
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

CHANNEL = os.environ.get("CHANNEL", "freekvn")
OUT = os.environ.get("OUT", "keys.json")
URL = f"https://t.me/s/{CHANNEL}"

KEY_RE = re.compile(r"(?:vless|vmess|trojan|ss|hysteria2|hy2|tuic)://[^\s<>\"']+", re.I)
SUB_RE = re.compile(r"https://sb\.[^\s<>\"']+", re.I)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept-Language": "ru,en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def post_text(chunk: str) -> str:
    """Текст поста + адреса ссылок, без HTML."""
    hrefs = " ".join(html.unescape(h) for h in re.findall(r'href="([^"]+)"', chunk))
    m = re.search(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', chunk, re.S)
    body = m.group(1) if m else ""
    body = re.sub(r"<br\s*/?>", "\n", body)
    body = re.sub(r"<[^>]+>", "", body)
    return html.unescape(body) + "\n" + hrefs


def parse(page: str):
    posts = [post_text(c) for c in page.split("tgme_widget_message_wrap")[1:]]
    # посты на странице идут от старых к новым
    last_sub_idx, link = None, None
    for i, t in enumerate(posts):
        subs = SUB_RE.findall(t)
        if subs:
            last_sub_idx, link = i, subs[-1].rstrip(".,)")
    start = last_sub_idx if last_sub_idx is not None else max(0, len(posts) - 3)
    keys = []
    for t in posts[start:]:
        for k in KEY_RE.findall(t):
            k = k.rstrip(".,)")
            if k not in keys:
                keys.append(k)
    return link, keys


def main() -> int:
    try:
        link, keys = parse(fetch(URL))
    except Exception as e:  # сеть, разметка
        print("ошибка чтения канала:", e)
        return 0
    old = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
    link = link or old.get("link")
    if not link and not keys:
        print("в канале не нашлось ни подписки, ни ключей — файл не меняю")
        return 0
    if link == old.get("link") and keys == old.get("keys"):
        print("ключи не изменились")
        return 0
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data = {"link": link, "keys": keys, "updated": now, "checked": now}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"обновлено: link={'есть' if link else 'нет'}, ключей={len(keys)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
