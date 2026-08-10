# =========================================================================
# KONFIGURASI — edit file ini kalau mau ubah niche, tambah/kurangi sumber
# =========================================================================

# Kata kunci niche "Digital" (game/esport, remote, IT/dev, programmer,
# designer, trader, content creator, marketer, dll). Loker baru dari semua
# sumber akan disaring: hanya yang judul/kategori-nya mengandung salah satu
# kata kunci ini yang dikirim ke Discord. Edit bebas — huruf besar/kecil
# tidak masalah (dicek case-insensitive), dan matching-nya "substring" jadi
# "design" otomatis match "designer", "ui designer", dst.
KEYWORDS = [
    # gaming / esports
    "game", "gaming", "esport", "esports", "game designer", "game developer",
    "unity", "unreal engine", "level design",
    # IT / dev
    "developer", "programmer", "software engineer", "backend", "frontend",
    "full stack", "fullstack", "devops", "data engineer", "data scientist",
    "data analyst", "qa engineer", "mobile developer", "it support",
    "sysadmin", "cloud engineer",
    # design
    "designer", "ui/ux", "ui designer", "ux designer", "graphic design",
    "product designer",
    # trading / finance digital
    "trader", "trading", "crypto", "blockchain",
    # content & marketing
    "content creator", "content writer", "copywriter", "social media",
    "digital marketing", "marketer", "growth", "seo", "performance marketing",
    "community manager",
    # umum remote
    "remote",
    # padanan Indonesia (berguna kalau nanti nambah sumber RSS lokal)
    "desainer", "pemasaran digital", "kreator konten", "programer",
]

# ------------------------------------------------------------------------
# Sumber berbasis JSON API — gratis, tanpa API key (dicek per Agustus 2026)
# items_path: nama key di response yang isinya list job
# *_key: nama field job (boleh dot-path utk nested, misal "company.name")
# ------------------------------------------------------------------------
API_SOURCES = [
    {
        "name": "Remotive",
        "url": "https://remotive.com/api/remote-jobs?limit=100",
        "items_path": "jobs",
        "title_key": "title",
        "company_key": "company_name",
        "url_key": "url",
        "category_key": "category",
    },
    {
        "name": "Himalayas",
        "url": "https://himalayas.app/jobs/api?limit=20",
        "items_path": "jobs",
        "title_key": "title",
        "company_key": "companyName",
        "url_key": "applicationLink",
        "category_key": "categories",  # array di response, otomatis digabung
    },
    {
        "name": "RemoteJobs.org",
        "url": "https://remotejobs.org/api/v1/jobs?limit=50",
        "items_path": "data",
        "title_key": "title",
        "company_key": "company.name",
        "url_key": "url",
        "category_key": "category.name",
    },
]

# ------------------------------------------------------------------------
# Sumber RSS (opsional, kosong secara default). Berguna banget buat nambah
# loker Indonesia (Glints/Kalibrr/JobStreet nggak punya API publik) atau
# niche khusus (misal Hitmarker buat gaming/esport, yang juga nggak punya
# API publik). Caranya:
#   1. Buka https://www.google.com/alerts
#   2. Bikin alert dgn query spesifik, contoh:
#        "loker" "digital marketing" site:glints.com
#        "hiring" game developer site:hitmarker.net
#   3. Klik "Show options" -> "Deliver to" -> pilih "RSS feed"
#   4. Copy URL RSS yang muncul, tempel di bawah ini
# Setiap entri RSS tetap difilter pakai KEYWORDS di atas.
# ------------------------------------------------------------------------
RSS_FEEDS = [
    # {
    #     "name": "Google Alert - Loker Digital Indonesia",
    #     "url": "TEMPEL_URL_RSS_DI_SINI",
    # },
]

MAX_EMBEDS_PER_MESSAGE = 10       # batas Discord: maksimal 10 embed/pesan
SEEN_FILE = "seen_jobs.json"      # penyimpanan histori biar gak nge-post dobel
MAX_SEEN_HISTORY = 3000           # biar file histori gak membesar terus-terusan

# Warna embed per sumber (opsional, biar gampang dibedain sekilas)
SOURCE_COLORS = {
    "Remotive": 0x00A264,
    "Himalayas": 0x6C5CE7,
    "RemoteJobs.org": 0x2F80ED,
}
DEFAULT_COLOR = 0x5865F2  # Discord blurple, dipakai kalau source gak ada di atas
