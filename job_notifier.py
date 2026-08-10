"""
Discord Loker Digital Notifier — Rich Embed Edition
-----------------------------------------------------
Ambil loker dari beberapa API job board + (opsional) RSS, saring sesuai
niche "digital" (game/esport, remote, IT/dev, programmer, designer,
trader, content creator, marketer, dll), lalu kirim yang BARU sebagai
embed KAYA (thumbnail logo, gaji, lokasi, tags) ke Discord webhook.

Jalankan manual:
  DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/xxx" python job_notifier.py

Di GitHub Actions:
  URL webhook disimpan sebagai secret DISCORD_WEBHOOK_URL.
"""

import json
import logging
import os
import re
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
    DEFAULT_SALARY_ESTIMATE,
    KEYWORDS,
    MAX_EMBEDS_PER_MESSAGE,
    MAX_SEEN_HISTORY,
    RSS_FEEDS,
    SALARY_ESTIMATES,
    SEEN_FILE,
    SOURCE_COLORS,
)

# ---------------------------------------------------------------------------
# Logging setup
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

# Screenshot service (gratis, tanpa API key) untuk preview halaman job
SCREENSHOT_URL = "https://image.thum.io/get/width/1280/crop/640/noanimate/"
# Fallback logo untuk author icon
FALLBACK_LOGO = "https://ui-avatars.com/api/?background=5865F2&color=fff&bold=true&size=64&name="


# ---------------------------------------------------------------------------
# HTTP Session — auto retry on transient errors
# ---------------------------------------------------------------------------
def _build_session():
    """Buat requests.Session dengan retry strategy bawaan."""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.5,
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
# Salary helpers
# ---------------------------------------------------------------------------
def _format_salary_range(min_sal, max_sal, currency="USD", period="annual"):
    """Format min/max salary jadi string yang readable."""
    currency = (currency or "USD").upper()
    symbol = {"USD": "$", "EUR": "€", "GBP": "£", "IDR": "Rp"}.get(currency, currency + " ")

    def _fmt(val):
        if val >= 1000:
            return f"{symbol}{val / 1000:.0f}k"
        return f"{symbol}{val:.0f}"

    period_label = {"annual": "/thn", "yearly": "/thn", "monthly": "/bln",
                    "hourly": "/jam"}.get(period, "")

    if min_sal and max_sal:
        return f"{_fmt(min_sal)} – {_fmt(max_sal)}{period_label}"
    elif min_sal:
        return f"{_fmt(min_sal)}+{period_label}"
    elif max_sal:
        return f"s.d. {_fmt(max_sal)}{period_label}"
    return None


def _estimate_salary(title, category=""):
    """Estimasi kisaran gaji berdasarkan judul/kategori job."""
    text = f"{title} {category}".lower()
    for keyword, estimate in SALARY_ESTIMATES.items():
        if keyword.lower() in text:
            return f"~{estimate} /thn (estimasi)"
    return f"~{DEFAULT_SALARY_ESTIMATE} /thn (estimasi)"


def get_salary_display(job_data, source_config, title, category=""):
    """Ambil info gaji dari data API, format, atau estimasi kalau tidak ada."""
    # 1. Cek salary string langsung (Remotive style)
    salary_str = get_nested(job_data, source_config.get("salary_key"))
    if salary_str and str(salary_str).strip():
        return str(salary_str).strip()

    # 2. Cek min/max salary (Himalayas style)
    min_key = source_config.get("salary_min_key")
    max_key = source_config.get("salary_max_key")
    if min_key or max_key:
        min_sal = get_nested(job_data, min_key)
        max_sal = get_nested(job_data, max_key)
        if min_sal or max_sal:
            currency = get_nested(job_data, source_config.get("salary_currency_key"))
            period = get_nested(job_data, source_config.get("salary_period_key"))
            formatted = _format_salary_range(
                float(min_sal) if min_sal else 0,
                float(max_sal) if max_sal else 0,
                currency, period
            )
            if formatted:
                return formatted

    # 3. Fallback: estimasi berdasarkan judul/kategori
    return _estimate_salary(title, category)


# ---------------------------------------------------------------------------
# Fetch sources
# ---------------------------------------------------------------------------
def _get_company_logo(item, source, company_name):
    """Ambil logo URL, fallback ke avatar generator kalau kosong."""
    logo = get_nested(item, source.get("logo_key"))
    if logo and str(logo).strip() and str(logo).startswith("http"):
        return str(logo).strip()
    # Fallback: generate avatar dari nama company
    name_encoded = (company_name or "Co").replace(" ", "+")
    return FALLBACK_LOGO + name_encoded


def _get_screenshot_url(job_url):
    """Generate screenshot URL dari halaman job menggunakan thum.io."""
    if not job_url:
        return None
    return SCREENSHOT_URL + job_url


def _format_job_type(raw_type):
    """Format job type jadi label yang rapi."""
    if not raw_type:
        return "🏢 Full-time"
    raw = str(raw_type).lower().replace("_", " ").replace("-", " ")
    mapping = {
        "full time": "🏢 Full-time",
        "fulltime": "🏢 Full-time",
        "part time": "⏰ Part-time",
        "parttime": "⏰ Part-time",
        "contract": "📋 Contract",
        "freelance": "💼 Freelance",
        "internship": "🎓 Internship",
        "temporary": "⏳ Temporary",
    }
    return mapping.get(raw, f"💼 {raw_type}")


def _format_tags(item, source, max_tags=4):
    """Ambil tags dan format sebagai badge-style string."""
    tags_raw = get_nested(item, source.get("tags_key"))
    if not tags_raw:
        return None
    if isinstance(tags_raw, str):
        tags = [t.strip() for t in tags_raw.replace("-", " ").split() if t.strip()]
    else:
        tags = tags_raw if isinstance(tags_raw, list) else []
    # Clean up tags
    clean_tags = []
    for tag in tags[:max_tags]:
        tag_str = str(tag).strip().replace("-", " ").title()
        if len(tag_str) > 20:
            tag_str = tag_str[:18] + "…"
        clean_tags.append(f"`{tag_str}`")
    return " ".join(clean_tags) if clean_tags else None


def _format_location(item, source):
    """Ambil dan format lokasi."""
    loc = get_nested(item, source.get("location_key"))
    if not loc:
        return "🌍 Remote (Worldwide)"
    if isinstance(loc, list):
        loc = ", ".join(str(l) for l in loc[:3])
        if len(loc) > 50:
            loc = loc[:47] + "…"
    return f"📍 {loc}"


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

        salary = get_salary_display(item, source, str(title), str(category))
        logo = _get_company_logo(item, source, str(company))
        location = _format_location(item, source)
        job_type = _format_job_type(get_nested(item, source.get("job_type_key")))
        tags = _format_tags(item, source)

        jobs.append(
            {
                "id": url,
                "title": str(title).strip(),
                "company": str(company).strip(),
                "url": url,
                "source": name,
                "salary": salary,
                "logo": logo,
                "location": location,
                "job_type": job_type,
                "tags": tags,
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

        label = source.get("label", name)
        salary_est = _estimate_salary(title)

        jobs.append(
            {
                "id": link,
                "title": title.strip(),
                "company": label,
                "url": link,
                "source": name,
                "salary": salary_est,
                "logo": FALLBACK_LOGO + label.replace(" ", "+"),
                "location": "🌍 Remote",
                "job_type": "💼 Lihat detail",
                "tags": None,
            }
        )

    log.info("✅ %s: %d loker cocok niche", name, len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Discord — Article-Style Embed Builder
# ---------------------------------------------------------------------------
def build_embed(job):
    """Buat embed style artikel: screenshot job page sebagai gambar besar,
    company logo sebagai author icon, info lengkap di description."""
    color = SOURCE_COLORS.get(job["source"], DEFAULT_COLOR)

    # Build description dengan info lengkap
    desc_lines = [
        f"💰  **{job['salary']}**",
        f"{job['location']}  •  {job['job_type']}",
    ]

    if job.get("tags"):
        desc_lines.append(f"🏷️  {job['tags']}")

    description = "\n".join(desc_lines)

    # Screenshot halaman job sebagai gambar besar (style artikel)
    screenshot = _get_screenshot_url(job["url"])

    embed = {
        "title": f"💼 {job['title'][:245]}",
        "url": job["url"],
        "description": description,
        "color": color,
        # Company info sebagai author (icon kecil + nama)
        "author": {
            "name": f"🏢 {job['company']}",
        },
        "footer": {
            "text": f"📌 {job['source']}  •  Klik judul untuk apply",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Tambah company logo sebagai author icon (kalau ada & valid)
    logo = job.get("logo", "")
    if logo and logo.startswith("http") and "ui-avatars" not in logo:
        embed["author"]["icon_url"] = logo

    # Tambah screenshot sebagai gambar besar di bawah (style artikel)
    if screenshot:
        embed["image"] = {"url": screenshot}

    return embed


def send_to_discord(jobs):
    """Kirim loker ke Discord webhook, 10 embed per pesan (batas Discord)."""
    if not jobs:
        log.info("📭 Tidak ada loker baru yang cocok kriteria.")
        return 0

    total_sent = 0

    # Kirim header message pertama
    header_payload = {
        "content": (
            f"## 🔔 Loker Digital Baru!\n"
            f"Ditemukan **{len(jobs)}** lowongan baru yang cocok niche kamu.\n"
            f"Klik judul untuk langsung apply! ⬇️"
        )
    }
    try:
        http.post(WEBHOOK_URL, json=header_payload, timeout=20)
        time.sleep(1)
    except Exception:
        pass  # Header opsional, lanjut aja

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

        time.sleep(1.5)

    return total_sent


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    log.info("=" * 55)
    log.info("🚀 Discord Loker Digital Notifier v2.0 — mulai")
    log.info("=" * 55)

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

    log.info("-" * 55)
    log.info("📊 Total ditemukan  : %d loker cocok niche", len(all_jobs))
    log.info("📊 Sudah dikirim    : %d (skip)", len(all_jobs) - len(new_jobs))
    log.info("📊 Baru (akan kirim): %d", len(new_jobs))
    log.info("-" * 55)

    # --- Send ---
    sent_count = send_to_discord(new_jobs)

    # --- Save ---
    seen.update(job["id"] for job in new_jobs)
    save_seen(seen)

    # --- Summary ---
    log.info("=" * 55)
    log.info("✅ Selesai — %d loker baru terkirim ke Discord", sent_count)
    log.info("=" * 55)


if __name__ == "__main__":
    main()
