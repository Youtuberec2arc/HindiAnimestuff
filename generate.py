#!/usr/bin/env python3
"""
Static movie/anime/series download-page site generator (OTT-style UI).

USAGE:
    python3 generate.py

INPUT:
    data.json          -> define all content here (title, poster,
                           genres, quality, download links, trending, etc.)
    assets/            -> style.css, app.js, logo.svg, poster images

OUTPUT:
    output/            -> ready-to-host static site
        index.html, anime.html, movies.html, series.html, trending.html
        favourites.html, browse-az.html, browse-genres.html,
        how-to-download.html, report.html
        pages/<id>.html        (each title's own detail page)
        pages_az/<a-z>.html    (A-Z anime list, one page per letter)
        genres/<slug>.html     (one page per genre, across all categories)
        assets/                (copied from ./assets + generated data.js)

Design notes
------------
- Category/genre/A-Z GRID pages are pre-rendered server-side (build time),
  not client JS — so nothing needs a raw data dump to work.
- Genre chips on listing pages are still JS-built (client-side filter on
  the current page's cards) for instant filtering. In addition, dedicated
  genre/<slug>.html pages are now pre-rendered at build time so every
  genre is browsable from the menu and gets its own shareable URL.
- Search & Favourites need to work across the WHOLE catalog from any
  page, so a small assets/data.js (window.SITE_ITEMS) is generated with
  just the fields needed for that (id, title, poster, type, category) —
  this is unavoidable for client-side search/favourites on a static site.
- Trending page: shows any item explicitly flagged "trending": true in
  data.json, automatically topped up with the highest-rated remaining
  titles so the page is never empty/sparse even if nothing was flagged.
"""

import json
import re
import shutil
import string
import hashlib
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data.json"
TEMPLATES_DIR = ROOT / "templates"
ASSETS_DIR = ROOT / "assets"
OUTPUT_DIR = ROOT / "output"

CATEGORY_LABELS = {
    "anime": "Anime",
    "movies": "Movies",
    "series": "Series",
}

LETTERS = list(string.ascii_uppercase)

TRENDING_TARGET_COUNT = 24
HERO_CAROUSEL_MAX = 5
TELEGRAM_REQUEST_URL = "https://t.me/+CChGHZIm5J9kODVl"
TELEGRAM_JOIN_URL = "https://t.me/+ZY6u10TE0PdjZmM1"
REPORT_PROBLEM_URL = "https://t.me/+xo_0Z-JlYIU5NDg1"

# Future ad networks (Adsterra / Monetag) — set enabled=True and fill slot HTML in templates
AD_CONFIG = {
    "enabled": False,
    "networks": ["adsterra", "monetag"],
    "slots": ["home_banner", "download_page", "file_page", "detail_footer"],
}

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_env():
    return Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))


def clean_output():
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)
    (OUTPUT_DIR / "pages").mkdir()
    (OUTPUT_DIR / "pages_az").mkdir()
    (OUTPUT_DIR / "genres").mkdir()
    (OUTPUT_DIR / "download").mkdir()


def copy_assets():
    dest = OUTPUT_DIR / "assets"
    shutil.copytree(ASSETS_DIR, dest)


def copy_root_static_files():
    """URLchecker.html + links.json power the download-redirect flow and
    must live at the SITE ROOT (not inside assets/), so they're copied
    straight into output/ on every build instead of being hand-managed."""
    for name in ("URLchecker.html", "links.json", "manifest.json"):
        src = ROOT / name
        if src.exists():
            shutil.copy2(src, OUTPUT_DIR / name)


def write_data_js(items):
    """Small embedded catalog for client-side search & favourites only."""
    slim = [
        {
            "id": i["id"],
            "title": i["title"],
            "poster": i["poster"],
            "type": i.get("type", ""),
            "category": i.get("category", ""),
            "season": i.get("season", ""),
            "rating": i.get("rating", ""),
            "episode_tag": i.get("episode_tag", ""),
        }
        for i in items
    ]
    js = "window.SITE_ITEMS = " + json.dumps(slim, ensure_ascii=False) + ";\n"
    (OUTPUT_DIR / "assets" / "data.js").write_text(js, encoding="utf-8")


def write_download_data_js(items):
    """Map of sid -> ep -> quality -> {url, name} for the file download page.
    Full worker URLs live only in this JS file and are used on user click —
    not rendered as visible hrefs on the page."""
    from urllib.parse import urlparse, parse_qs, unquote

    download_map = {}
    for item in items:
        el = item.get("episode_links")
        if not el:
            continue
        sid = item["id"]
        download_map[sid] = {}
        for ep_num, quals in el.items():
            download_map[sid][ep_num] = {}
            for q, url in quals.items():
                if not url:
                    continue
                name = ""
                try:
                    qs = parse_qs(urlparse(url).query)
                    name = unquote(qs.get("name", [""])[0])
                except Exception:
                    name = f"{item['title']} E{ep_num} {q}.mkv"
                download_map[sid][ep_num][q] = {"url": url, "name": name}
    js = "window.DOWNLOAD_MAP = " + json.dumps(download_map, ensure_ascii=False) + ";\n"
    (OUTPUT_DIR / "assets" / "download-data.js").write_text(js, encoding="utf-8")



NOTIFICATIONS_SEEN_FILE = ROOT / "notifications_seen.json"


def load_notifications_seen():
    if NOTIFICATIONS_SEEN_FILE.exists():
        try:
            return json.loads(NOTIFICATIONS_SEEN_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_notifications_seen(seen_map):
    NOTIFICATIONS_SEEN_FILE.write_text(json.dumps(seen_map, indent=2, ensure_ascii=False), encoding="utf-8")


def write_notifications_js(items):
    """Latest content notifications for the floating mail box (7-day window).
    Add optional data.json key "notifications": [{type, title, ts}] to override/extend.

    Each auto-detected title's timestamp is looked up in
    notifications_seen.json (persisted next to generate.py, not wiped by
    clean_output()) instead of being stamped with "now" on every single
    build. That file remembers the first time each title was actually
    seen, so: (a) the "new content" list is now genuinely meaningful
    instead of claiming everything is brand new on every run, and
    (b) this output file stays byte-identical across rebuilds when
    nothing changed, instead of forcing a re-upload every time.
    """
    from datetime import datetime, timezone
    seen_map = load_notifications_seen()
    now_iso = datetime.now(timezone.utc).isoformat()

    notes = []
    # Prefer explicit list from data.json if present
    data = load_data()
    for n in data.get("notifications") or []:
        notes.append({
            "type": n.get("type", "Update"),
            "title": n.get("title", ""),
            "ts": n.get("ts") or now_iso,
            "date": n.get("date") or "",
        })
    # Auto: items with episode_links count as New Anime / New Episode
    for i in items:
        if not i.get("episode_links"):
            continue
        title = i.get("title", "") + ((" — " + i["season"]) if i.get("season") else "")
        if title not in seen_map:
            seen_map[title] = now_iso
        notes.append({
            "type": "New Anime" if i.get("category") == "anime" else "New Series",
            "title": title,
            "ts": seen_map[title],
            "date": "Recently added",
        })
    save_notifications_seen(seen_map)
    # Dedupe by title, keep first 30
    seen = set()
    unique = []
    for n in notes:
        k = n["title"]
        if k in seen:
            continue
        seen.add(k)
        unique.append(n)
    unique = unique[:30]
    js = "window.SITE_NOTIFICATIONS = " + json.dumps(unique, ensure_ascii=False) + ";\n"
    (OUTPUT_DIR / "assets" / "notifications-data.js").write_text(js, encoding="utf-8")
    # Also embed into notifications.js load path via data file name used in base — 
    # we write notifications-data.js and load it before notifications.js

def base_title_key(item):
    """Normalize title for grouping seasons of the same show."""
    t = item.get("title", "")
    t = re.sub(r"\s*Season\s*\d+.*$", "", t, flags=re.I).strip()
    t = re.sub(r"\s*S\d+.*$", "", t, flags=re.I).strip()
    return t.lower()


def related_seasons_for(item, items):
    key = base_title_key(item)
    seasons = [i for i in items if base_title_key(i) == key and i.get("episode_links")]
    seasons.sort(key=lambda i: i.get("season") or "")
    return seasons


def related_by_genre(item, items, limit=6):
    genres = set(item.get("genres") or [])
    if not genres:
        return []
    scored = []
    for i in items:
        if i["id"] == item["id"]:
            continue
        overlap = len(genres & set(i.get("genres") or []))
        if overlap:
            scored.append((overlap, _safe_float(i.get("rating")), i))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [x[2] for x in scored[:limit]]


def _safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def slugify(text):
    text = text.strip().lower()
    text = re.sub(r"&", " and ", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def collect_genres(items):
    """Unique {name, slug} list of every genre across the whole catalog, A-Z."""
    seen = {}
    for i in items:
        for g in i.get("genres", []):
            g = g.strip()
            if not g:
                continue
            slug = slugify(g)
            if slug not in seen:
                seen[slug] = g
    return [{"name": seen[s], "slug": s} for s in sorted(seen, key=lambda s: seen[s].lower())]


def brand_parts(site_name):
    words = site_name.split(" ")
    if len(words) >= 2:
        return " ".join(words[:-1]) + " ", words[-1]
    if len(site_name) > 4:
        return site_name[:-4], site_name[-4:]
    return site_name, ""


def compute_build_version():
    """A short hash of everything that actually affects the CSS/JS a
    browser needs to re-fetch (assets + templates). Used as the ?v=...
    cache-busting query string.

    This used to be int(time.time()) -- a fresh number on literally every
    single run -- which meant every one of the 500+ generated pages had
    different HTML byte-for-byte on every build, even when nothing about
    the site had actually changed. Firebase Hosting diffs by content hash,
    so that forced a full re-upload of the whole site every time. Hashing
    the real inputs instead means unchanged pages stay byte-identical
    across builds, so only what actually changed gets uploaded.
    """
    h = hashlib.sha256()
    for f in sorted(ASSETS_DIR.rglob("*")):
        if f.is_file():
            h.update(str(f.relative_to(ASSETS_DIR)).encode("utf-8"))
            h.update(f.read_bytes())
    for f in sorted(TEMPLATES_DIR.rglob("*.html")):
        h.update(str(f.relative_to(TEMPLATES_DIR)).encode("utf-8"))
        h.update(f.read_bytes())
    return h.hexdigest()[:10]


def render_all():
    data = load_data()
    site_name = data.get("site_name", "MovieSite")
    items = data.get("items", [])
    head, tail = brand_parts(site_name)

    env = build_env()
    clean_output()
    copy_assets()
    copy_root_static_files()
    write_data_js(items)
    write_download_data_js(items)
    write_notifications_js(items)

    all_genres = collect_genres(items)

    common_ctx = {
        "site_name": site_name,
        "brand_head": head,
        "brand_tail": tail,
        "all_genres": all_genres,
        "build_version": compute_build_version(),
        "telegram_join_url": TELEGRAM_JOIN_URL,
        "report_problem_url": REPORT_PROBLEM_URL,
        "ad_config": AD_CONFIG,
    }

    # ---- Homepage: ANIME ONLY (no Hollywood/Bollywood movies/series) ----
    anime_items = [i for i in items if i.get("category") == "anime"]

    trending_flagged = [i for i in anime_items if i.get("trending")]
    if trending_flagged:
        hero_items = trending_flagged[:HERO_CAROUSEL_MAX]
    elif anime_items:
        hero_items = [max(anime_items, key=lambda i: _safe_float(i.get("rating")))]
    else:
        hero_items = []

    # Top 10 rated Anime Movies (type == "Movie" within the anime category)
    top_anime_movies = sorted(
        (i for i in anime_items if i.get("type") == "Movie"),
        key=lambda i: _safe_float(i.get("rating")),
        reverse=True,
    )[:10]

    tpl = env.get_template("index.html")
    html = tpl.render(**common_ctx, items=anime_items, active="home",
                       hero_items=hero_items, top_anime_movies=top_anime_movies,
                       root_prefix="", asset_prefix="")
    (OUTPUT_DIR / "index.html").write_text(html, encoding="utf-8")

    # ---- Category pages: anime.html / movies.html / series.html ----
    for cat, label in CATEGORY_LABELS.items():
        cat_items = [i for i in items if i.get("category") == cat]
        tpl = env.get_template("category.html")
        html = tpl.render(**common_ctx, items=cat_items, active=cat,
                           category_label=label,
                           root_prefix="", asset_prefix="")
        (OUTPUT_DIR / f"{cat}.html").write_text(html, encoding="utf-8")

    # ---- Trending page: ANIME ONLY, highest-rated first (auto-updates
    #      whenever ratings/new anime change — no manual flag needed) ----
    trending_items = sorted(anime_items, key=lambda i: _safe_float(i.get("rating")), reverse=True)[:TRENDING_TARGET_COUNT]
    tpl = env.get_template("category.html")
    html = tpl.render(**common_ctx, items=trending_items, active="trending",
                       category_label="Trending", root_prefix="", asset_prefix="")
    (OUTPUT_DIR / "trending.html").write_text(html, encoding="utf-8")

    # ---- Favourites shell (client-rendered) ----
    tpl = env.get_template("favourites.html")
    html = tpl.render(**common_ctx, active="favourites", root_prefix="", asset_prefix="")
    (OUTPUT_DIR / "favourites.html").write_text(html, encoding="utf-8")

    # ---- How to Download / Report pages (dedicated templates) ----
    tpl = env.get_template("how_to_download.html")
    html = tpl.render(**common_ctx, active="howto", root_prefix="", asset_prefix="")
    (OUTPUT_DIR / "how-to-download.html").write_text(html, encoding="utf-8")

    tpl = env.get_template("report.html")
    html = tpl.render(**common_ctx, active="report", root_prefix="", asset_prefix="",
                       telegram_url=TELEGRAM_REQUEST_URL)
    (OUTPUT_DIR / "report.html").write_text(html, encoding="utf-8")

    # ---- A-Z hub page ----
    tpl = env.get_template("browse_az.html")
    html = tpl.render(**common_ctx, active="az", root_prefix="", asset_prefix="",
                       letters=LETTERS)
    (OUTPUT_DIR / "browse-az.html").write_text(html, encoding="utf-8")

    # ---- A-Z per-letter pages (anime category, one level deep) ----
    anime_items = [i for i in items if i.get("category") == "anime"]
    tpl = env.get_template("letter.html")
    for letter in LETTERS:
        letter_items = sorted(
            [i for i in anime_items if i["title"].strip().upper().startswith(letter)],
            key=lambda i: i["title"].lower(),
        )
        html = tpl.render(**common_ctx, items=letter_items, active="az",
                           letter=letter, all_letters=LETTERS,
                           root_prefix="../", asset_prefix="../")
        (OUTPUT_DIR / "pages_az" / f"{letter.lower()}.html").write_text(html, encoding="utf-8")

    # ---- Genres hub page ----
    tpl = env.get_template("browse_genres.html")
    html = tpl.render(**common_ctx, active="genres", root_prefix="", asset_prefix="")
    (OUTPUT_DIR / "browse-genres.html").write_text(html, encoding="utf-8")

    # ---- Per-genre pages: genres/<slug>.html (across ALL categories) ----
    tpl = env.get_template("genre.html")
    for g in all_genres:
        genre_items = sorted(
            [i for i in items if g["name"] in i.get("genres", [])],
            key=lambda i: _safe_float(i.get("rating")),
            reverse=True,
        )
        html = tpl.render(**common_ctx, items=genre_items, active="genres",
                           genre=g, root_prefix="../", asset_prefix="../")
        (OUTPUT_DIR / "genres" / f"{g['slug']}.html").write_text(html, encoding="utf-8")

    # ---- Detail pages: pages/<id>.html ----
    tpl = env.get_template("detail.html")
    for item in items:
        # Anime titles use the new single-Download-button + ID system.
        # (Movies/Series i.e. Hollywood/Bollywood keep the old 3-button system.)
        if item.get("category") == "anime" and item.get("episode_links"):
            quality_set = set()
            for eps in item["episode_links"].values():
                quality_set.update(eps.keys())
            item["available_qualities"] = [q for q in ["480p", "720p", "1080p"] if q in quality_set]
        html = tpl.render(**common_ctx, item=item, active=item.get("category"),
                           root_prefix="../", asset_prefix="../")
        (OUTPUT_DIR / "pages" / f"{item['id']}.html").write_text(html, encoding="utf-8")

    # ---- Download pages (episode list + qualities) for anime with episode_links ----
    tpl_dl = env.get_template("download_series.html")
    dl_count = 0
    for item in items:
        if not item.get("episode_links"):
            continue
        episode_order = sorted(
            item["episode_links"].keys(),
            key=lambda x: int(re.sub(r"\D", "", x) or 0),
        )
        related_seasons = related_seasons_for(item, items)
        related_items = related_by_genre(item, items, limit=6)
        html = tpl_dl.render(
            **common_ctx,
            item=item,
            episode_order=episode_order,
            related_seasons=related_seasons,
            related_items=related_items,
            active=item.get("category"),
            root_prefix="../",
            asset_prefix="../",
        )
        (OUTPUT_DIR / "download" / f"{item['id']}.html").write_text(html, encoding="utf-8")
        dl_count += 1

    # ---- Single file-download intermediate page (dynamic via query + download-data.js) ----
    tpl_file = env.get_template("download_file.html")
    html = tpl_file.render(
        **common_ctx,
        active="",
        root_prefix="../",
        asset_prefix="../",
    )
    (OUTPUT_DIR / "download" / "file.html").write_text(html, encoding="utf-8")

    total_pages = 9 + len(items) + len(LETTERS) + len(all_genres) + dl_count + 1
    print(f"Done. {len(items)} titles, {dl_count} download pages, {len(all_genres)} genres, {total_pages} pages -> {OUTPUT_DIR}")
    print("Open output/index.html in a browser to preview.")


if __name__ == "__main__":
    render_all()
