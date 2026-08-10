# 🎯 Discord Loker Digital Bot

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Discord-Webhook-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord">
  <img src="https://img.shields.io/badge/GitHub_Actions-Serverless-2088FF?style=for-the-badge&logo=githubactions&logoColor=white" alt="GitHub Actions">
  <img src="https://img.shields.io/github/actions/workflow/status/yopaayy/job-notifier/notify.yml?style=for-the-badge&label=Bot%20Status" alt="Bot Status">
</p>

---

Bot **tanpa server (serverless)** yang narik loker dari beberapa job board gratis, saring sesuai niche **digital** (game/esport, remote, IT/dev, programmer, designer, trader, content creator, marketer, dll), lalu kirim yang **baru saja** sebagai embed rapi ke channel Discord kamu — jalan otomatis via GitHub Actions, **gratis**, nggak perlu server nyala 24/7.

## 📡 Sumber Data (Aktif Agustus 2026)

| Sumber | Tipe | Deskripsi |
|--------|------|-----------|
| **Remotive** | API | Job remote internasional, macam-macam kategori |
| **Himalayas** | API | Job remote internasional |
| **RemoteJobs.org** | API | Agregat dari 5 sumber |
| **Jobicy** | API | Job remote global termasuk Asia & worldwide |
| Google Alerts RSS | RSS (opsional) | Untuk loker Indonesia lokal (Glints/Kalibrr/JobStreet) |

## ⚡ Quick Start (± 10 menit)

### 1️⃣ Bikin Webhook di Discord

1. Buka channel target → klik ikon ⚙️ (Edit Channel)
2. **Integrations** → **Webhooks** → **New Webhook**
3. Kasih nama (misal "Loker Digital Bot"), lalu **Copy Webhook URL**

### 2️⃣ Upload ke GitHub

1. Bikin repo baru (boleh **private** — GitHub Actions tetap gratis)
2. Upload semua file di folder ini ke repo

### 3️⃣ Simpan Webhook URL sebagai Secret

1. Di repo GitHub → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret**
3. Name: `DISCORD_WEBHOOK_URL`
4. Value: tempel URL webhook dari langkah 1
5. **Add secret**

### 4️⃣ Jalankan!

- ⏰ **Otomatis**: workflow jalan tiap 6 jam (lihat `.github/workflows/notify.yml`)
- 🔧 **Manual**: tab **Actions** → pilih workflow → **Run workflow**

> ✅ Selesai — loker baru yang cocok niche bakal muncul di channel Discord kamu!

## 🏗️ Struktur Project

```
📦 job-notifier/
├── 📄 job_notifier.py      # Script utama (fetch, filter, kirim, catat histori)
├── 📄 config.py             # KEYWORDS + daftar sumber (paling sering diedit)
├── 📄 seen_jobs.json        # "Ingatan" bot biar loker gak dikirim dobel
├── 📄 requirements.txt      # Dependency Python (requests, feedparser)
├── 📄 .gitignore            # File yang diabaikan git
└── 📂 .github/
    └── 📂 workflows/
        └── 📄 notify.yml    # GitHub Actions: jadwal + langkah otomatis
```

## 🔄 Cara Kerja

```
┌─────────────────────────────────────────────────────┐
│  GitHub Actions (tiap 6 jam) / Manual trigger       │
└───────────────────────┬─────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│  1. Fetch loker terbaru dari semua sumber           │
│     (Remotive, Himalayas, RemoteJobs.org, RSS)      │
└───────────────────────┬─────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│  2. Filter: cuma yang cocok KEYWORDS                │
│     (case-insensitive, substring matching)          │
└───────────────────────┬─────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│  3. Buang yang sudah pernah dikirim                 │
│     (dicek dari seen_jobs.json)                     │
└───────────────────────┬─────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│  4. Kirim ke Discord sebagai embed rapi             │
│     (judul + link + company + sumber)               │
└───────────────────────┬─────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│  5. Update seen_jobs.json & commit ke repo          │
└─────────────────────────────────────────────────────┘
```

## 🎨 Kustomisasi

### Ubah Niche / Kata Kunci

Edit list `KEYWORDS` di `config.py`. Matching-nya substring & case-insensitive:

```python
KEYWORDS = [
    "game", "developer", "designer",    # contoh yang sudah ada
    "kata kunci baru kamu",             # ← tambah di sini
]
```

### Ubah Jadwal

Edit baris `cron` di `.github/workflows/notify.yml`:

```yaml
# Default: tiap 6 jam (4x/hari)
- cron: "0 */6 * * *"

# Contoh lain:
# Tiap 3 jam:   "0 */3 * * *"
# Tiap 12 jam:  "0 */12 * * *"
# Cek crontab.guru untuk custom
```

### Tambah Sumber API Baru

Tambah dict baru di `API_SOURCES` dalam `config.py`:

```python
{
    "name": "NamaSource",
    "url": "https://api.example.com/jobs",
    "items_path": "data",        # key yang isinya list job
    "title_key": "title",        # field judul
    "company_key": "company",    # field perusahaan
    "url_key": "url",            # field link
    "category_key": "category",  # field kategori (opsional)
}
```

### Tambah Sumber Lokal Indonesia (Glints/Kalibrr/dll)

Job board Indonesia nggak punya API publik. Cara gampang tanpa scraping:

1. Buka [Google Alerts](https://www.google.com/alerts)
2. Bikin alert, contoh:
   - `"loker" "digital marketing" site:glints.com`
   - `hiring "game developer" site:hitmarker.net`
3. Klik "Show options" → "Deliver to" → pilih **RSS feed**
4. Copy URL RSS → tempel di `RSS_FEEDS` dalam `config.py`

## 🖥️ Setup di Server Pribadi

Kalau mau jalanin di server sendiri (VPS/Raspberry Pi) daripada GitHub Actions:

### 1. Clone & Install

```bash
git clone https://github.com/yopaayy/job-notifier.git
cd job-notifier
pip install -r requirements.txt
```

### 2. Set Environment Variable

```bash
# Bikin file .env (JANGAN commit ke git!)
echo 'DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_HERE' > .env
```

### 3. Test Manual

```bash
export $(cat .env | xargs)  # load .env
python job_notifier.py
```

### 4. Setup Cron Job (Otomatis Tiap 6 Jam)

```bash
crontab -e
```

Tambahkan baris:

```
0 */6 * * * cd /path/to/job-notifier && export $(cat .env | xargs) && python3 job_notifier.py >> /var/log/job-notifier.log 2>&1
```

### 5. (Opsional) Systemd Service

```bash
sudo nano /etc/systemd/system/job-notifier.timer
```

```ini
[Unit]
Description=Job Notifier Timer

[Timer]
OnCalendar=*-*-* 00/6:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo nano /etc/systemd/system/job-notifier.service
```

```ini
[Unit]
Description=Job Notifier Bot
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/path/to/job-notifier
EnvironmentFile=/path/to/job-notifier/.env
ExecStart=/usr/bin/python3 job_notifier.py
```

```bash
sudo systemctl enable --now job-notifier.timer
```

## ⚠️ Catatan Penting

- **Atribusi sumber**: Remotive & Himalayas mewajibkan link balik ke listing asli + nama sumber — sudah otomatis terpenuhi lewat embed, jangan dihapus
- **Rate limit**: jangan set cron lebih sering dari tiap ~15 menit (terutama Remotive)
- **`seen_jobs.json` di-commit otomatis** oleh workflow supaya histori nggak hilang (GitHub Actions itu stateless)
- **Retry otomatis**: script sudah handle retry 3x untuk error 429/5xx dengan backoff

## 📄 License

MIT — bebas dipakai, dimodifikasi, dan didistribusikan.

---

<p align="center">
  <sub>Made with ❤️ by <a href="https://github.com/yopaayy">yopaayy</a></sub>
</p>
