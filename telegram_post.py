#!/usr/bin/env python3
"""
Posts newly-added data.json titles to Telegram automatically.

WHEN TO RUN:
    Every time you add new titles to data.json, run this right after
    generate.py:

        python generate.py
        python telegram_post.py

    It keeps track of what's already been posted in posted_telegram.json
    (created automatically next to this file), so re-running it only
    posts titles that are new since last time. Nothing gets posted twice.

ONE-TIME SETUP (edit the value below before first run):
    TELEGRAM_BOT_TOKEN -> from @BotFather on Telegram (BotFather -> /newbot,
                           or /mybots if you already made one)

    Your bot must be added as an ADMIN (with "Post Messages" permission)
    in BOTH channels:
        @hindiDubbedAnimes4u
        @HDMoviesDL4u

IMAGES:
    No TMDB anymore. The banner image is scraped straight from the post
    page on https://www.animedubhindi.link (search by title -> open the
    first result -> grab its featured image). If that site has nothing
    for a title, it falls back to center-cropping the poster to 16:9.

NOTE ON THE DOWNLOAD BUTTON COLOR:
    Telegram's Bot API does not let a bot set a custom color for inline
    buttons - the button look (including color) is rendered by each
    user's Telegram app/theme, not something send from the bot side.
    So "blue" isn't something this script can force; it'll match
    whatever theme the viewer is using. Everything else below (bold
    text, quote blocks) IS something we control, and is applied.

REQUIRES:
    pip install pillow --break-system-packages
    (only needed for the rare poster-crop fallback)
"""

import html
import json
import re
import time
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data.json"
POSTED_FILE = ROOT / "posted_telegram.json"

# ---------------------------------------------------------------------
# FILL THIS IN
TELEGRAM_BOT_TOKEN = "8885570507:AAG3mHJvmWX4y15YhKXH2hcCHestD8qhqiA"
# ---------------------------------------------------------------------

DOWNLOAD_LINK = "https://t.me/c/3917444779/9"  # same button link for every post
JOIN_CHANNEL = "@HindiAnimestuff"  # shown as "Join : ..." in every caption - edit if needed

CHANNELS = {
    "anime": "@hindiDubbedAnimes4u",
    "movies": "@HDMoviesDL4u",
    "series": "@HDMoviesDL4u",
}

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def load_posted():
    if POSTED_FILE.exists():
        return set(json.loads(POSTED_FILE.read_text(encoding="utf-8")))
    return set()


def save_posted(posted_ids):
    POSTED_FILE.write_text(json.dumps(sorted(posted_ids), indent=2), encoding="utf-8")


def http_get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="ignore")


def animedubhindi_banner(title):
    """
    Search animedubhindi.link for the title and grab the post's banner
    image (their blogger-hosted images are already ~16:9). Returns a
    URL or None.
    """
    try:
        search_url = "https://www.animedubhindi.link/?s=" + urllib.parse.quote(title)
        search_html = http_get(search_url)

        # Grab the first search-result post link. Try the common WP
        # "entry-title" pattern first, then fall back to any bookmark link.
        m = re.search(r'entry-title["\'][^>]*>\s*<a[^>]+href="([^"]+)"', search_html)
        if not m:
            m = re.search(
                r'<a[^>]+href="(https://www\.animedubhindi\.link/[^"]+)"[^>]*rel="bookmark"',
                search_html,
            )
        if not m:
            print(f"  animedubhindi: no search result for '{title}'")
            return None
        post_url = m.group(1)

        post_html = http_get(post_url)

        # Prefer the og:image meta tag (set to the post's featured/banner image).
        m2 = re.search(
            r'<meta[^>]+property=["\']og:image["\'][^>]+content="([^"]+)"',
            post_html,
        )
        if m2:
            return m2.group(1)

        # Fallback: first blogger-hosted image found in the post body.
        m3 = re.search(r'(https://blogger\.googleusercontent\.com/img/[^"\'\s]+)', post_html)
        if m3:
            return m3.group(1)

        print(f"  animedubhindi: no image found on {post_url}")
        return None
    except Exception as e:
        print(f"  animedubhindi lookup failed for '{title}': {e}")
        return None


def crop_poster_to_16x9(poster_url):
    """Last-resort fallback: if animedubhindi.link has nothing, center-crop the poster to 16:9."""
    try:
        from PIL import Image
        from io import BytesIO
        with urllib.request.urlopen(poster_url, timeout=15) as r:
            im = Image.open(BytesIO(r.read())).convert("RGB")
        w, h = im.size
        target_h = int(w * 9 / 16)
        if target_h <= h:
            top = (h - target_h) // 2
            im = im.crop((0, top, w, top + target_h))
        else:
            target_w = int(h * 16 / 9)
            left = (w - target_w) // 2
            im = im.crop((left, 0, left + target_w, h))
        out_path = ROOT / "_tg_crop_tmp.jpg"
        im.save(out_path, "JPEG", quality=88)
        return out_path
    except Exception as e:
        print(f"  Poster crop fallback failed: {e}")
        return None


def build_caption(item):
    """
    Builds the HTML-formatted caption (parse_mode=HTML). Everything is
    bold; the title and the join line sit inside a quote block, matching
    the requested post layout.
    """
    title = html.escape(item["title"])
    season = html.escape(str(item.get("season") or "N/A"))
    rating = html.escape(str(item.get("rating", "N/A")))
    genres = html.escape(" | ".join(item.get("genres", [])))
    quality = html.escape(item.get("quality_tag", ""))
    languages = html.escape(" | ".join(item.get("languages", [])))
    subtitle = html.escape(item.get("subtitle", ""))
    join_channel = html.escape(JOIN_CHANNEL)

    lines = ["\u2022 Series Information", ""]
    lines.append(f"Title: <blockquote>{title}</blockquote>")
    lines.append(f"Season: {season}")
    lines.append(f"MAL Rating: {rating}/10")
    lines.append(f"Genres: {genres}")
    lines.append(f"Quality: {quality}")
    lines.append(f"Audio Tracks : {languages}")
    lines.append(f"Subtitle: {subtitle}")
    if item.get("category") != "movies":
        lines.append(f"Total Episode: {item.get('episodes') or 'N/A'}")
    lines.append("")
    lines.append(f"Join : <blockquote>{join_channel}</blockquote>")

    body = "\n".join(lines)
    return f"<b>{body}</b>"


def send_photo(chat_id, photo, caption, local_file=False):
    button = {"inline_keyboard": [[{"text": "Download Now \U0001F343", "url": DOWNLOAD_LINK}]]}

    if local_file:
        boundary = "----tgboundary"
        fields = {
            "chat_id": chat_id,
            "caption": caption,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(button),
        }
        body = b""
        for k, v in fields.items():
            body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n").encode("utf-8")
        body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"thumb.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n").encode("utf-8")
        body += Path(photo).read_bytes()
        body += f"\r\n--{boundary}--\r\n".encode("utf-8")
        req = urllib.request.Request(
            f"{TELEGRAM_API}/sendPhoto", data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
    else:
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "photo": photo,
            "caption": caption,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(button),
        }).encode("utf-8")
        req = urllib.request.Request(f"{TELEGRAM_API}/sendPhoto", data=data)

    with urllib.request.urlopen(req, timeout=30) as r:
        result = json.load(r)
    if not result.get("ok"):
        raise RuntimeError(result)


def main():
    if "PASTE_YOUR" in TELEGRAM_BOT_TOKEN:
        print("Fill in TELEGRAM_BOT_TOKEN at the top of telegram_post.py first.")
        return

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    items = data.get("items", [])
    posted = load_posted()
    new_items = [i for i in items if i["id"] not in posted]

    if not new_items:
        print("Nothing new to post.")
        return

    print(f"Posting {len(new_items)} new title(s) to Telegram...")
    for item in new_items:
        chat_id = CHANNELS.get(item.get("category"))
        if not chat_id:
            print(f"  Skipping {item['id']} - unknown category '{item.get('category')}'")
            continue

        caption = build_caption(item)
        banner = animedubhindi_banner(item["title"])

        try:
            if banner:
                send_photo(chat_id, banner, caption)
            else:
                cropped = crop_poster_to_16x9(item["poster"])
                if cropped:
                    send_photo(chat_id, str(cropped), caption, local_file=True)
                    cropped.unlink(missing_ok=True)
                else:
                    send_photo(chat_id, item["poster"], caption)  # last resort
            print(f"  Posted: {item['title']} -> {chat_id}")
            posted.add(item["id"])
            save_posted(posted)  # save progress after every single post
            time.sleep(2)  # stay well under Telegram's rate limits
        except Exception as e:
            print(f"  FAILED to post {item['id']}: {e}")

    print("Done.")


if __name__ == "__main__":
    main()
