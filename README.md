# CampMap

露營版 Trivago — 聚合多個台灣露營訂位平台的資料，提供統一篩選介面，導向原站訂位。

## 支援平台

| 平台     | 網址                         |
| -------- | ---------------------------- |
| 露營樂   | https://www.easycamp.com.tw  |
| 玩露趣   | https://www.camptrip.tw      |
| 愛露營   | https://www.icamping.app     |

## 架構

```
CampMap/
│
├── packages/
│   ├── scraper/                 # Python 爬蟲 (Playwright + BS4)
│   │   ├── scrapers/            # 各平台爬蟲模組
│   │   │   ├── base.py          #   爬蟲基底類別
│   │   │   ├── easycamp.py      #   露營樂
│   │   │   ├── camptrip.py      #   玩露趣
│   │   │   └── icamping.py      #   愛露營
│   │   ├── models/
│   │   │   └── campsite.py      #   統一營地資料結構
│   │   ├── utils/
│   │   │   ├── db.py            #   Supabase 連線
│   │   │   └── geo.py           #   地理編碼工具
│   │   └── main.py              #   爬蟲主程式入口
│   │
│   └── web/                     # React 前端 (Vite + Tailwind)
│       └── src/
│           ├── components/      #   Map / Search / Filter / Camp / Layout
│           ├── pages/           #   Home / Search / CampDetail / Favorites
│           ├── services/        #   Supabase client
│           └── store/           #   Zustand 狀態管理
│
├── supabase/
│   └── migrations/
│       └── 001_init.sql         # 資料庫 schema
│
└── .github/workflows/
    ├── scrape.yml               # 爬蟲排程 (GitHub Actions cron)
    └── deploy.yml               # 前端部署 (GitHub Pages)
```

```
┌──────────────┐  cron   ┌──────────────┐  upsert  ┌──────────────┐
│  GitHub      │ ──────► │   Scraper    │ ───────► │   Supabase   │
│  Actions     │         │  (Playwright)│          │  (PostgreSQL)│
└──────────────┘         └──────────────┘          └──────┬───────┘
                                                          │ query
                                                          ▼
                                                   ┌──────────────┐
                                                   │   React SPA  │
                                                   │  (Vite)      │
                                                   └──────┬───────┘
                                                          │
                                                          ▼
                                                   ┌──────────────┐
                                                   │   使用者瀏覽  │
                                                   │   → 導向原站  │
                                                   └──────────────┘
```

## 快速開始

### 前端

```bash
cd packages/web
npm install
npm run dev
```

### 爬蟲

```bash
cd packages/scraper
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python main.py
```

### 環境變數

在專案根目錄建立 `.env`：

```env
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_service_key
```

## 技術棧

- **前端**: React + TypeScript + Vite + Tailwind CSS
- **地圖**: Leaflet + react-leaflet
- **狀態管理**: Zustand
- **後端**: Supabase (PostgreSQL + REST API)
- **爬蟲**: Python + Playwright + BeautifulSoup4
- **CI/CD**: GitHub Actions
