"""
Discord Loker Digital Notifier
-------------------------------
Ambil loker dari beberapa API job board + (opsional) RSS, saring sesuai
niche "digital" (game/esport, remote, IT/dev, programmer, designer,
trader, content creator, marketer, dll), lalu kirim yang BARU sebagai
embed ke Discord webhook.

Jalankan manual:
  DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/xxx" python job_notifier.py

Di GitHub Actions:
  URL webhook disimpan sebagai secret DISCORD_WEBHOOK_URL.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import (
    API_SOURCES,
    DEFAULT_COLOR,
    KEYWORDS,
    MAX_EMBEDS_PER_MESSAGE,
    MAX_SEEN_HISTORY,
    RSS_FEEDS,
    SEEN_FILE,
    SOURCE_COLORS,
)

# ---------------------------------------------------------------------------
# Logging setup — timestamp + level + message
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("job_notifier")

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
USER_AGENT = "discord-loker-digital-bot/2.0 (+github-actions)"


# ---------------------------------------------------------------------------
# HTTP Session — auto retry on transient errors
# ---------------------------------------------------------------------------
def _build_session():
    """Buat requests.Session dengan retry strategy bawaan."""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.5,              # 0s, 1.5s, 3s
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session


http = _build_session()


# ---------------------------------------------------------------------------
# Util
# ---------------------------------------------------------------------------
def get_nested(item, dot_path):
    """Ambil field dari dict, mendukung dot-path ('company.name') dan
    otomatis gabung jadi string kalau hasilnya berupa list (misal kategori)."""
    if not dot_path:
        return None
    value = item
    for part in dot_path.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    if isinstance(value, list):
        return " ".join(str(v) for v in value if v)
    return value


def matches_keywords(text):
    """Cek apakah text mengandung salah satu keyword (case-insensitive)."""
    text_lower = (text or "").lower()
    return any(kw.lower() in text_lower for kw in KEYWORDS)


def load_seen():
    """Load histori job ID yang sudah pernah dikirim."""
    path = Path(SEEN_FILE)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            log.info("Loaded %d seen IDs dari %s", len(data), SEEN_FILE)
            return set(data)
        except (json.JSONDecodeError, ValueError) as e:
            log.warning("%s rusak/tidak valid (%s), mulai dari kosong.", SEEN_FILE, e)
    return set()


def save_seen(seen_ids):
    """Simpan histori, trim ke MAX_SEEN_HISTORY terbaru."""
    trimmed = list(seen_ids)[-MAX_SEEN_HISTORY:]
    Path(SEEN_FILE).write_text(json.dumps(trimmed, indent=2), encoding="utf-8")
    log.info("Saved %d seen IDs ke %s", len(trimmed), SEEN_FILE)


# ---------------------------------------------------------------------------
# Fetch sources
# ---------------------------------------------------------------------------
def fetch_api_source(source):
    """Fetch loker dari satu API source, return list of job dicts."""
    name = source["name"]
    try:
        resp = http.get(source["url"], timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.ConnectionError as e:
        log.error("❌ %s: koneksi gagal — %s", name, e)
        return []
    except requests.exceptions.Timeout:
        log.error("❌ %s: timeout setelah 20 detik", name)
        return []
    except requests.exceptions.HTTPError as e:
        log.error("❌ %s: HTTP error %s", name, e)
        return []
    except Exception as e:
        log.error("❌ %s: error tidak terduga — %s", name, e)
        return []

    items = data.get(source["items_path"], []) if isinstance(data, dict) else data
    if not isinstance(items, list):
        log.warning("⚠️  %s: format response tidak sesuai (bukan list)", name)
        return []

    jobs = []
    for item in items:
        title = get_nested(item, source["title_key"])
        url = get_nested(item, source["url_key"])
        company = get_nested(item, source["company_key"]) or "-"
        category = get_nested(item, source.get("category_key")) or ""

        if not title or not url:
            continue
        if not matches_keywords(f"{title} {category}"):
            continue

        jobs.append(
            {
                "id": url,
                "title": str(title).strip(),
                "company": str(company).strip(),
                "url": url,
                "source": name,
            }
        )

    log.info("✅ %s: %d loker cocok niche (dari %d total)", name, len(jobs), len(items))
    return jobs


def fetch_rss_source(source):
    """Fetch loker dari satu RSS feed source."""
    name = source["name"]
    try:
        feed = feedparser.parse(source["url"])
        if feed.bozo:
            log.warning("⚠️  %s: RSS parse warning — %s", name, feed.bozo_exception)
    except Exception as e:
        log.error("❌ %s: gagal fetch RSS — %s", name, e)
        return []

    jobs = []
    for entry in feed.entries:
        title = entry.get("title", "")
        link = entry.get("link", "")
        if not title or not link:
            continue
        if not matches_keywords(title):
            continue
        jobs.append(
            {
                "id": link,
                "title": title.strip(),
                "company": source.get("label", name),
                "url": link,
                "source": name,
            }
        )

    log.info("✅ %s: %d loker cocok niche", name, len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Discord
# ---------------------------------------------------------------------------
def build_embed(job):
    """Buat satu embed dict untuk Discord webhook."""
    return {
        "title": job["title"][:250],
        "url": job["url"],
        "description": f"🏢  **{job['company']}**",
        "color": SOURCE_COLORS.get(job["source"], DEFAULT_COLOR),
        "footer": {"text": f"📌 Sumber: {job['source']}"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def send_to_discord(jobs):
    """Kirim loker ke Discord webhook, 10 embed per pesan (batas Discord)."""
    if not jobs:
        log.info("📭 Tidak ada loker baru yang cocok kriteria.")
        return 0

    total_sent = 0

    for i in range(0, len(jobs), MAX_EMBEDS_PER_MESSAGE):
        batch = jobs[i : i + MAX_EMBEDS_PER_MESSAGE]
        payload = {"embeds": [build_embed(j) for j in batch]}

        try:
            resp = http.post(WEBHOOK_URL, json=payload, timeout=20)

            # Handle Discord rate limiting
            if resp.status_code == 429:
                retry_after = resp.json().get("retry_after", 5)
                log.warning("⏳ Discord rate limited, tunggu %.1f detik...", retry_after)
                time.sleep(retry_after + 0.5)
                resp = http.post(WEBHOOK_URL, json=payload, timeout=20)

            if resp.status_code >= 300:
                log.error(
                    "❌ Gagal kirim batch %d ke Discord: %d %s",
                    (i // MAX_EMBEDS_PER_MESSAGE) + 1,
                    resp.status_code,
                    resp.text[:200],
                )
            else:
                total_sent += len(batch)
                log.info(
                    "📨 Batch %d: %d loker terkirim ke Discord",
                    (i // MAX_EMBEDS_PER_MESSAGE) + 1,
                    len(batch),
                )

        except requests.exceptions.RequestException as e:
            log.error("❌ Gagal kirim ke Discord: %s", e)

        time.sleep(1.5)  # jaga-jaga rate limit webhook Discord

    return total_sent


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    log.info("=" * 50)
    log.info("🚀 Discord Loker Digital Notifier — mulai")
    log.info("=" * 50)

    if not WEBHOOK_URL:
        log.critical(
            "DISCORD_WEBHOOK_URL belum di-set! "
            "Set environment variable ini (atau GitHub Actions secret) "
            "sebelum menjalankan script."
        )
        raise SystemExit(1)

    if not WEBHOOK_URL.startswith("https://discord.com/api/webhooks/"):
        log.warning(
            "⚠️  DISCORD_WEBHOOK_URL tidak terlihat seperti URL webhook Discord yang valid."
        )

    # --- Fetch ---
    seen = load_seen()
    all_jobs = []

    log.info("📡 Fetching dari %d API source...", len(API_SOURCES))
    for source in API_SOURCES:
        all_jobs.extend(fetch_api_source(source))

    if RSS_FEEDS:
        log.info("📡 Fetching dari %d RSS feed...", len(RSS_FEEDS))
        for source in RSS_FEEDS:
            all_jobs.extend(fetch_rss_source(source))

    # --- Deduplicate ---
    deduped = {}
    for job in all_jobs:
        deduped.setdefault(job["id"], job)
    all_jobs = list(deduped.values())

    new_jobs = [job for job in all_jobs if job["id"] not in seen]

    log.info("-" * 50)
    log.info("📊 Total ditemukan  : %d loker cocok niche", len(all_jobs))
    log.info("📊 Sudah dikirim    : %d (skip)", len(all_jobs) - len(new_jobs))
    log.info("📊 Baru (akan kirim): %d", len(new_jobs))
    log.info("-" * 50)

    # --- Send ---
    sent_count = send_to_discord(new_jobs)

    # --- Save ---
    seen.update(job["id"] for job in new_jobs)
    save_seen(seen)

    # --- Summary ---
    log.info("=" * 50)
    log.info("✅ Selesai — %d loker baru terkirim ke Discord", sent_count)
    log.info("=" * 50)


if __name__ == "__main__":
    main()
