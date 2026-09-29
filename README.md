<div align="center">

<!-- ============================================================ -->
<!--        BANNER IMAGE — replace src with your actual image     -->
<!-- ============================================================ -->
# 🤖 Linkedin-Automation
**An Agentic AI-Powered Linkedin Automation to fetch post and post them into Linkedin**

<br/>

<!-- ============================================================ -->
<!--                        BADGES                               -->
<!-- ============================================================ -->
![Python](https://img.shields.io/badge/Python-3.10--3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Gemini AI](https://img.shields.io/badge/Gemini_AI-Powered-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-Database-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)
![LinkedIn](https://img.shields.io/badge/LinkedIn-Auto--Posting-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI%2FCD-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

<br/>

**An intelligent, fully-automated multi-stage pipeline that scrapes fresh job listings from LinkedIn & Indeed, ranks the best opportunities using Google Gemini AI, generates beautiful visual job-card images, stores everything in Supabase, and auto-posts to LinkedIn — all on a schedule via GitHub Actions.**

---

</div>

## 📋 Table of Contents

- [📸 Project Overview](#-project-overview)
- [✨ Key Features](#-key-features)
- [⚙️ Pipeline Flow — How the System Works](#️-pipeline-flow--how-the-system-works)
- [🖼️ Automation Pipeline](#️-automation-pipeline)
- [📁 Folder Structure](#-folder-structure)
- [🚀 Installation & Setup Guide](#-installation--setup-guide)
- [🔐 Environment Variables](#-environment-variables)
- [🤖 GitHub Actions — Automation Workflows](#-github-actions--automation-workflows)
- [🛠️ Tech Stack](#️-tech-stack)

---

## 📸 Project Overview

**LinkedIn Job Automation** is a production-grade, fully-automated job discovery and social media posting pipeline built entirely in Python. It is designed to run **hands-free on a schedule**, discovering the most relevant junior/mid-level tech job listings in Pakistan every day, enriching them with AI, generating branded visual cards, and posting them to LinkedIn automatically — without any manual effort.

### What it does, end-to-end:

| Stage | What Happens |
|-------|-------------|
| 🔍 **Scrape** | Scrapes LinkedIn & Indeed daily for 5 job categories |
| 🤖 **Rank** | Google Gemini AI picks the single best job per category |
| 📋 **Enrich** | Fetches full job descriptions, logos, salary data |
| ✍️ **Summarize** | Gemini AI distills each job into a clean LinkedIn-ready post |
| 🎨 **Design** | Playwright renders beautiful color-coded job card images |
| ☁️ **Store** | Uploads images and all data to Supabase cloud |
| 📤 **Post** | Buffer GraphQL API publishes posts to LinkedIn on schedule |

> **Target Audience:** Job seekers, recruiters, and tech communities in Pakistan looking for curated, daily-fresh junior and mid-level tech opportunities.

---

## ✨ Key Features

### 🔍 Multi-Platform Job Scraping
Scrapes **LinkedIn** and **Indeed** simultaneously for 5 tech job categories (Full Stack, AI/Data, Mobile, UI/UX Design, Software/DevOps). Uses smart deduplication — enforcing **1 job per company** per category and filtering out senior/director/manager roles automatically.

### 🤖 Gemini AI-Powered Job Ranking
Uses **Google Gemini `gemini-3.5-flash-lite`** to evaluate every scraped job on company reputation, hiring prestige, market performance, and role seniority fit — then picks the **single absolute best job** per category.

### 📋 Deep Job Enrichment
Re-scrapes LinkedIn with `linkedin_fetch_description=True` to pull full job descriptions, company logos, company URLs, and salary/pay information for each ranked job.

### ✍️ Structured AI Summarization
Gemini AI processes each enriched job into a **Pydantic-validated structured summary**, extracting: job summary, key requirements, required skills, company perks, workplace type (Remote/Hybrid/On-site), smart hashtags, and a matching brand color code.

### 🎨 Dynamic Visual Job Card Generator
Uses **Playwright** (headless Chrome/Edge) to render a branded HTML/CSS job card template dynamically injected with each job's data and color scheme — then screenshots it as a **PNG image**, ready for social posting.

### ☁️ Supabase Cloud Storage & Database
Uploads generated PNG images to **Supabase Storage** (`job-images` bucket) and inserts all structured job data into a **Supabase PostgreSQL** `jobs` table with `pending` status — creating a posting queue.

### 📤 Buffer GraphQL Auto-Posting
The LinkedIn posting pipeline fetches the oldest `pending` job from Supabase, downloads its image, formats a rich LinkedIn post text with emojis and hashtags, then publishes via the **Buffer GraphQL API** — and marks the job `posted` when complete.

### 🔄 Cloud-Resilient Fallback System
Scrapers are known to be blocked by anti-bot filters in CI/CD environments. The pipeline includes a **smart fallback cache system** — if a scraper is blocked, pre-defined sample job data is injected so the AI ranking and downstream steps always complete successfully.

### ⚡ GitHub Actions CI/CD — Fully Automated
Three independent GitHub Actions workflows handle everything:
- **`run-job.yml`** — Runs the full scrape → rank → enrich → summarize → design → store pipeline
- **`linkdin-post.yml`** — Fetches pending jobs and posts to LinkedIn
- **`remove-job.yml`** — Cleans up old/expired jobs

---

## ⚙️ Pipeline Flow — How the System Works

The system operates as **two independent pipelines** triggered by GitHub Actions (manually or via cron-job.org):

### Pipeline 1 — Job Discovery & Storage (`python main.py`)

```
┌─────────────────────────────────────────────────────────────────┐
│                    MASTER PIPELINE  (main.py)                   │
└───────────────────────┬─────────────────────────────────────────┘
                        │
        ┌───────────────▼─────────────────┐
        │     STEP 1 — Core Pipeline       │
        │       Core/main-core.py          │
        └──┬──────────────────────────┬───┘
           │                          │
┌──────────▼──────────┐   ┌───────────▼──────────┐
│  LinkedIn Engine     │   │  Indeed Engine        │
│ linkdin-engine.py    │   │ indeed-engine.py      │
│                      │   │                       │
│ Scrapes 5 categories │   │ Appends 5 unique jobs │
│ (15 raw → 5 unique)  │   │ per category below    │
│ → Data/Job-Result-   │   │ LinkedIn results      │
│   cache/*.json       │   │                       │
└──────────────────────┘   └───────────────────────┘
           │                          │
           └──────────┬───────────────┘
                      │
                      ▼  [Fallback cache injected if scrapers blocked]
        ┌─────────────────────────────┐
        │  Core/job-rank.py            │
        │  Gemini AI ranks each        │
        │  category → picks best job   │
        │  → Data/Job_Rank.json        │
        └─────────────┬───────────────┘
                      │
        ┌─────────────▼───────────────┐
        │  Core/job-info.py            │
        │  Re-scrapes LinkedIn for     │
        │  full description + logo     │
        │  + pay info                  │
        │  → Data/Job-Info.json        │
        └─────────────┬───────────────┘
                      │
        ┌─────────────▼───────────────┐
        │  Core/job-summery.py         │
        │  Gemini AI → Pydantic schema │
        │  Structured LinkedIn post    │
        │  data + color codes          │
        │  → Data/Job-summery.json     │
        └─────────────┬───────────────┘
                      │
        ┌─────────────▼───────────────┐
        │  STEP 2 — Design Generator   │
        │  Job-Post-Design/            │
        │  main-job-post.py            │
        │                              │
        │  post-data.py → batches      │
        │  path-finder.py → Playwright │
        │  renders HTML card → PNG     │
        │  → Generated-Images/*.png    │
        └─────────────┬───────────────┘
                      │
        ┌─────────────▼───────────────┐
        │  STEP 3 — Storage            │
        │  Main-Storage/main-storage.py│
        │  Merges image paths + data   │
        │  → main-storage.json         │
        └─────────────┬───────────────┘
                      │
        ┌─────────────▼───────────────┐
        │  STEP 4 — Supabase Sync      │
        │  Main-Storage/Supabse.py     │
        │  Uploads PNG to Storage      │
        │  Inserts job record to DB    │
        │  status = "pending"          │
        └─────────────────────────────┘
```

### Pipeline 2 — LinkedIn Auto-Posting (`python Linkdin-posting/main-post.py`)

```
┌──────────────────────────────────────────────────┐
│         LINKEDIN POSTING PIPELINE                 │
└───────────────────────┬──────────────────────────┘
                        │
        ┌───────────────▼─────────────────┐
        │  post.py                         │
        │  Fetches oldest "pending" job    │
        │  from Supabase → downloads image │
        │  → saves post.json locally       │
        └───────────────┬─────────────────┘
                        │
        ┌───────────────▼─────────────────┐
        │  linkdin-post.py                 │
        │  Formats rich post text          │
        │  with emojis + hashtags          │
        │  → Buffer GraphQL API            │
        │  → Publishes to LinkedIn         │
        │  → Updates Supabase              │
        │     status = "posted"            │
        └─────────────────────────────────┘
```

### Job Categories Scraped

| # | Category | Output Cache File |
|---|----------|-------------------|
| 1 | Frontend, Full Stack & Backend | `Fullstack.json` |
| 2 | AI & Data Engineering | `AIEngineer.json` |
| 3 | Mobile Developer | `MobileDeveloper.json` |
| 4 | UI/UX & Graphic Designer | `Designer.json` |
| 5 | Software & DevOps Engineering | `SoftwareEngineer.json` |

### AI Color Coding System

Each job category gets a distinct brand color injected into the visual card:

| Category | Color Name | Hex Code |
|----------|-----------|----------|
| Full Stack | Deep Teal | `#1A6B72` |
| AI Engineering | Muted Violet | `#5B4A8A` |
| Design | Steel Blue | `#2E6B8A` |
| Software Engineering | Forest Green | `#3D6B52` |
| Other / Default | Dusty Plum | `#6B4E71` |

---

## 🖼️ Automation Pipeline

<!-- Add your automation pipeline images below -->

<img width="1204" height="526" alt="image" src="https://github.com/user-attachments/assets/6b9109f4-23cd-4e08-8b22-415dbcf3ddd2" />
<img width="1091" height="520" alt="image" src="https://github.com/user-attachments/assets/f222b52c-c55a-4043-98ab-ae173bf6de61" />
<img width="1176" height="488" alt="image" src="https://github.com/user-attachments/assets/2d9b6ecd-058e-4600-89d6-9f66aae9c41f" />




---

## 📁 Folder Structure

```
Linkdin-Automation/
│
├── main.py                          # Master entry point — runs the full pipeline
├── buffer.py                        # Buffer API utility (channel/org ID helper)
├── requirements.txt                 # All Python dependencies
├── .env                             # Local secrets (NEVER commit this)
├── .gitignore                       # Git ignore rules
│
├── Core/                            # Core job discovery & AI processing pipeline
│   ├── main-core.py                 # Orchestrates all core steps with resilience
│   ├── job-rank.py                  # Gemini AI ranks jobs, picks best per category
│   ├── job-info.py                  # Re-scrapes LinkedIn for full job enrichment
│   ├── job-summery.py               # Gemini AI structured Pydantic summarization
│   │
│   └── Job-search/                  # Web scraper engines
│       ├── linkdin-engine.py        # LinkedIn scraper (5 categories, deduped)
│       ├── indeed-engine.py         # Indeed scraper (appends to LinkedIn cache)
│       └── job_quries.py            # Search query definitions & role keywords
│
├── Data/                            # Pipeline data cache (auto-generated)
│   ├── Job-Result-cache/            # Raw scraper output (per-category JSON files)
│   │   ├── Fullstack.json
│   │   ├── AIEngineer.json
│   │   ├── MobileDeveloper.json
│   │   ├── Designer.json
│   │   └── SoftwareEngineer.json
│   ├── Job_Rank.json                # Gemini-ranked best job per category
│   ├── Job-Info.json                # Enriched job details (description, logo, pay)
│   └── Job-summery.json             # Final structured summaries ready for posting
│
├── Job-Post-Design/                 # Visual job card image generator
│   ├── main-job-post.py             # Orchestrates design pipeline steps
│   ├── post-data.py                 # Batches job data into Post-data.json
│   ├── path-finder.py               # Playwright renderer → PNG screenshots
│   ├── Post-data.json               # Batched post data (auto-generated)
│   │
│   ├── Design-Template/
│   │   └── index.html               # HTML/CSS job card template (dynamic)
│   │
│   └── Generated-Images/            # Output PNG job card images (auto-generated)
│       └── *.png
│
├── Main-Storage/                    # Storage & Supabase sync layer
│   ├── main-storage.py              # Merges data + image paths → main-storage.json
│   ├── Supabse.py                   # Uploads images + inserts jobs to Supabase
│   └── main-storage.json            # Final merged dataset (auto-generated)
│
├── Linkdin-posting/                 # LinkedIn auto-posting pipeline
│   ├── main-post.py                 # Orchestrates the posting workflow
│   ├── post.py                      # Fetches pending job from Supabase queue
│   ├── linkdin-post.py              # Formats text + publishes via Buffer GraphQL
│   │
│   └── Post-Data/                   # Temporary posting data (auto-generated)
│       ├── post.json
│       └── post_image.png
│
├── Data-Remove/                     # Cleanup utilities
│   └── remove.py                    # Removes old/expired jobs from Supabase
│
└── .github/
    └── workflows/                   # GitHub Actions automation
        ├── run-job.yml              # Triggers the full pipeline
        ├── linkdin-post.yml         # Triggers LinkedIn posting
        └── remove-job.yml           # Triggers job cleanup
```

---

## 🚀 Installation & Setup Guide

### Prerequisites

- **Python 3.10 – 3.12** — [Download here](https://www.python.org/downloads/)
- **Git** — [Download here](https://git-scm.com/downloads)
- **Google Chrome** or **Microsoft Edge** (required for Playwright screenshots)

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/Linkdin-Automation.git
cd Linkdin-Automation
```

---

### Step 2 — Install Libraries

```bash
pip install python-jobspy pandas python-dotenv
```

```bash
pip install google-genai
```

```bash
pip install playwright
playwright install
```

```bash
pip install supabase python-dotenv
```

Or install everything at once from `requirements.txt`:

```bash
pip install -r requirements.txt
playwright install
```

---

### Step 3 — Configure Environment Variables

Create a `.env` file in the root of the project and fill in your credentials:

```env
# Google Gemini AI
GEMINI_API_KEY=your_gemini_api_key_here

# Supabase — Database & Storage
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_service_role_key_here

# Buffer — LinkedIn Auto-Posting
BUFFER_API_KEY=your_buffer_api_key_here
BUFFER_CHANNEL_ID=your_buffer_linkedin_channel_id_here
```

| Key | Where to Get It |
|-----|----------------|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) → Create API Key |
| `SUPABASE_URL` | Supabase Dashboard → Settings → API → Project URL |
| `SUPABASE_KEY` | Supabase Dashboard → Settings → API → `service_role` secret key |
| `BUFFER_API_KEY` | [Buffer Developer Portal](https://buffer.com/developers/apps) → Access Token |
| `BUFFER_CHANNEL_ID` | Run `python buffer.py` — prints your connected channel IDs |

---

### Step 4 — Set Up Supabase Database

In your Supabase project, go to **SQL Editor** and run:

```sql
CREATE TABLE jobs (
    id              BIGSERIAL PRIMARY KEY,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    job_title       TEXT,
    company         TEXT,
    location        TEXT,
    job_url         TEXT,
    company_email   TEXT,
    source          TEXT,
    pay_info        TEXT,
    job_summary     TEXT,
    requirements    JSONB,
    required_skills JSONB,
    what_we_offer   JSONB,
    about_company   TEXT,
    workplace_type  TEXT,
    image_url       TEXT,
    status          TEXT DEFAULT 'pending'
);
```

Then in **Supabase → Storage**, create a **Public** bucket named `job-images`.

---

### Step 5 — Run the Full Pipeline

```bash
python main.py
```

---

### Step 6 — Run the LinkedIn Posting Pipeline

```bash
python Linkdin-posting/main-post.py
```

---

## 🔐 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ Yes | Google Gemini AI API key (raw key only, no prefix) |
| `SUPABASE_URL` | ✅ Yes | Your Supabase project URL |
| `SUPABASE_KEY` | ✅ Yes | Supabase service role key (has full DB access) |
| `BUFFER_API_KEY` | ✅ Yes | Buffer access token for GraphQL API |
| `BUFFER_CHANNEL_ID` | ✅ Yes | Buffer LinkedIn channel ID for posting |

> ⚠️ **Security Warning:** Never commit your `.env` file to Git. It is already listed in `.gitignore`. For GitHub Actions, add all secrets via: **Repository → Settings → Secrets and Variables → Actions → New repository secret**.

---

## 🤖 GitHub Actions — Automation Workflows

### `run-job.yml` — Full Pipeline
Runs `python main.py` — the complete scrape → rank → enrich → design → store pipeline.

**Required Secrets:** `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`

**Trigger:** Manual (`workflow_dispatch`) or via [cron-job.org](https://cron-job.org) API call for daily scheduling.

---

### `linkdin-post.yml` — LinkedIn Posting
Runs `python Linkdin-posting/main-post.py` — fetches the next pending job and posts to LinkedIn.

**Required Secrets:** `SUPABASE_URL`, `SUPABASE_KEY`, `BUFFER_API_KEY`, `BUFFER_CHANNEL_ID`

**Trigger:** Manual (`workflow_dispatch`) or scheduled via cron-job.org.

---

### `remove-job.yml` — Job Cleanup
Runs the cleanup script to remove old or expired job records from Supabase.

**Trigger:** Manual (`workflow_dispatch`).

---

### Adding Secrets to GitHub

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add each of the following:

```
GEMINI_API_KEY      →  Your raw Google AI Studio key (starts with AIza...)
SUPABASE_URL        →  https://your-project.supabase.co
SUPABASE_KEY        →  Your service_role key from Supabase
BUFFER_API_KEY      →  Your Buffer access token
BUFFER_CHANNEL_ID   →  Your Buffer LinkedIn channel ID
```

---

## 🛠️ Tech Stack

| Technology | Role |
|-----------|------|
| **Python 3.10 – 3.12** | Core language for all pipeline logic |
| **Google Gemini AI** (`gemini-3.5-flash-lite`) | Job ranking, structured summarization, NLP |
| **python-jobspy** | Multi-site job scraping (LinkedIn + Indeed) |
| **Playwright** | Headless browser for HTML→PNG job card generation |
| **Supabase** | PostgreSQL database + S3-compatible image storage |
| **Buffer GraphQL API** | LinkedIn post publishing & scheduling |
| **Pydantic** | Strict schema validation for Gemini AI outputs |
| **GitHub Actions** | CI/CD orchestration & cloud automation |
| **python-dotenv** | Secure environment variable management |
| **pandas** | DataFrame processing for scraper results |

---

<div align="center">

**Built with ❤️ for automating the job discovery grind — so you can focus on applying.**

![Made with Python](https://img.shields.io/badge/Made%20with-Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Powered by Gemini](https://img.shields.io/badge/Powered%20by-Gemini%20AI-4285F4?style=flat-square&logo=google&logoColor=white)
![Auto-posts to LinkedIn](https://img.shields.io/badge/Auto--posts%20to-LinkedIn-0077B5?style=flat-square&logo=linkedin&logoColor=white)

</div>
