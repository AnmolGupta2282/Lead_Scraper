"""
Finds social media links (and a contact email) from a business website.
Used by app.py. Needs:  pip install requests
"""

import html as htmllib
import re
from urllib.parse import urlparse

import requests

SOCIAL_FIELDS = ["facebook", "instagram", "tiktok", "linkedin", "youtube", "twitter", "email"]

HOSTS = {
    "facebook": {"facebook.com", "fb.com"},
    "instagram": {"instagram.com"},
    "tiktok": {"tiktok.com"},
    "linkedin": {"linkedin.com"},
    "youtube": {"youtube.com", "youtu.be"},
    "twitter": {"twitter.com", "x.com"},
}

# first path segments that are share buttons, posts or system pages, not profiles
BAD_FIRST = {
    "sharer", "sharer.php", "share", "share.php", "sharearticle", "intent", "plugins",
    "dialog", "tr", "login", "login.php", "watch", "embed", "hashtag", "explore", "p",
    "reel", "reels", "home", "i", "privacy", "policies", "help", "legal", "tag", "tags",
    "stories", "feed", "pages_reaction_units", "v2.0", "v3.0",
}
TWO_SEGMENT = {"company", "in", "channel", "c", "user", "pages", "school", "showcase"}

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9",
}

URL_RE = re.compile(r"https?://[^\s\"'<>\\)]+", re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
BAD_EMAIL_PARTS = ("example", "sentry", "wixpress", "domain.", "email.com", "yourname", "@2x")
BAD_EMAIL_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js")


def _host(netloc: str) -> str:
    h = netloc.lower().split(":")[0]
    for prefix in ("www.", "m.", "web.", "mobile."):
        if h.startswith(prefix):
            h = h[len(prefix):]
    return h


def _clean(platform: str, url: str):
    """Return a normalised profile URL for `platform`, or None if not a profile."""
    try:
        u = urlparse(url.rstrip("/.,;"))
    except Exception:
        return None
    host = _host(u.netloc)
    if host not in HOSTS[platform]:
        return None
    segs = [s for s in u.path.split("/") if s]
    if not segs:
        return None
    first = segs[0].lower()
    if first in BAD_FIRST:
        return None
    if first == "profile.php" and u.query:
        return f"https://{host}/profile.php?{u.query}"
    keep = segs[:2] if first in TWO_SEGMENT and len(segs) > 1 else segs[:1]
    return f"https://{host}/" + "/".join(keep)


def _pick_email(text: str) -> str:
    mailtos = re.findall(r"mailto:([^\"'?<>\s]+)", text, re.I)
    candidates = mailtos + EMAIL_RE.findall(text)
    for e in candidates:
        e = e.strip().lower()
        if not EMAIL_RE.fullmatch(e):
            continue
        if e.endswith(BAD_EMAIL_EXT) or any(b in e for b in BAD_EMAIL_PARTS):
            continue
        return e
    return ""


def find_social_links(website: str, timeout: int = 8) -> dict:
    """Return {facebook, instagram, tiktok, linkedin, youtube, twitter, email}."""
    result = {f: "" for f in SOCIAL_FIELDS}
    if not website:
        return result

    # The "website" on Google Maps is sometimes just a social page itself
    for platform in HOSTS:
        cleaned = _clean(platform, website)
        if cleaned:
            result[platform] = cleaned
            return result

    try:
        r = requests.get(website, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if "html" not in r.headers.get("Content-Type", "").lower():
            return result
        text = r.text[:1_500_000]
    except Exception:
        return result

    text = htmllib.unescape(text).replace("\\/", "/")

    for url in URL_RE.findall(text):
        for platform in HOSTS:
            if result[platform]:
                continue
            cleaned = _clean(platform, url)
            if cleaned:
                result[platform] = cleaned

    result["email"] = _pick_email(text)
    return result
