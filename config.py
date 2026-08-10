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
#
# items_path  : nama key di response yang isinya list job
# *_key       : nama field job (boleh dot-path utk nested, misal "company.name")
# logo_key    : field logo perusahaan (URL gambar)
# salary_key  : field gaji (string/number)
# salary_min_key / salary_max_key / salary_currency_key : field gaji terpisah
# location_key: field lokasi kerja
# job_type_key: field tipe pekerjaan (full-time, part-time, dll)
# tags_key    : field tags/skill
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
        "logo_key": "company_logo",
        "salary_key": "salary",
        "location_key": "candidate_required_location",
        "job_type_key": "job_type",
        "tags_key": "tags",
    },
    {
        "name": "Himalayas",
        "url": "https://himalayas.app/jobs/api?limit=50",
        "items_path": "jobs",
        "title_key": "title",
        "company_key": "companyName",
        "url_key": "applicationLink",
        "category_key": "categories",  # array di response, otomatis digabung
        "logo_key": "companyLogo",
        "salary_min_key": "minSalary",
        "salary_max_key": "maxSalary",
        "salary_currency_key": "currency",
        "salary_period_key": "salaryPeriod",
        "location_key": "locationRestrictions",
        "job_type_key": "employmentType",
        "tags_key": "categories",
    },
    {
        "name": "RemoteJobs.org",
        "url": "https://remotejobs.org/api/v1/jobs?limit=50",
        "items_path": "data",
        "title_key": "title",
        "company_key": "company.name",
        "url_key": "url",
        "category_key": "category.name",
        "logo_key": "company.logo",
        "salary_key": "salary",
        "location_key": "location",
        "job_type_key": "type",
    },
    # --- Jobicy: free API, no key, global + Asia coverage, company logos ---
    {
        "name": "Jobicy",
        "url": "https://jobicy.com/api/v2/remote-jobs?count=50",
        "items_path": "jobs",
        "title_key": "jobTitle",
        "company_key": "companyName",
        "url_key": "url",
        "category_key": "jobIndustry",  # array
        "logo_key": "companyLogo",
        "location_key": "jobGeo",
        "job_type_key": "jobType",  # array
        "tags_key": "jobIndustry",
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
    "Jobicy": 0xFF6B6B,
}
DEFAULT_COLOR = 0x5865F2  # Discord blurple, dipakai kalau source gak ada di atas

# -------------------------------------------------------------------------
# Estimasi gaji default per kategori (USD/tahun) — dipakai kalau API
# tidak menyertakan data gaji. Angka berdasarkan median remote salary
# dari berbagai sumber (Glassdoor, Levels.fyi, Remotive salary data 2025).
# -------------------------------------------------------------------------
SALARY_ESTIMATES = {
    # IT / Engineering
    "software engineer": "$70k – $150k",
    "developer": "$60k – $130k",
    "frontend": "$55k – $120k",
    "backend": "$65k – $140k",
    "full stack": "$65k – $135k",
    "fullstack": "$65k – $135k",
    "devops": "$80k – $160k",
    "cloud engineer": "$80k – $155k",
    "data engineer": "$75k – $150k",
    "data scientist": "$80k – $160k",
    "data analyst": "$50k – $100k",
    "qa engineer": "$50k – $110k",
    "mobile developer": "$60k – $135k",
    "sysadmin": "$50k – $100k",
    "it support": "$35k – $65k",
    # Design
    "designer": "$50k – $120k",
    "ui/ux": "$55k – $125k",
    "ui designer": "$50k – $115k",
    "ux designer": "$55k – $125k",
    "graphic design": "$40k – $90k",
    "product designer": "$70k – $140k",
    # Gaming
    "game developer": "$55k – $130k",
    "game designer": "$50k – $120k",
    "unity": "$55k – $125k",
    "unreal engine": "$60k – $135k",
    # Marketing & Content
    "digital marketing": "$40k – $90k",
    "marketer": "$40k – $95k",
    "seo": "$40k – $85k",
    "content writer": "$35k – $75k",
    "copywriter": "$40k – $80k",
    "content creator": "$35k – $75k",
    "social media": "$35k – $70k",
    "community manager": "$35k – $70k",
    "growth": "$60k – $130k",
    "performance marketing": "$50k – $110k",
    # Finance / Crypto
    "trader": "$60k – $150k",
    "trading": "$60k – $150k",
    "crypto": "$65k – $160k",
    "blockchain": "$70k – $170k",
}
DEFAULT_SALARY_ESTIMATE = "$40k – $100k"
