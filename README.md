# FileScan — Multi-source malware analysis

Self-hosted, Kleenscan/Euroscan-style scanning service. Users upload a file and
get back per-engine verdicts from **multiple scanners** running in parallel —
local engines (ClamAV, YARA) and aggregated commercial APIs (VirusTotal,
MetaDefender, Hybrid Analysis, MalwareBazaar, CIRCL Hashlookup).

> Files are streamed to a private quarantine directory, scanned, then shredded
> after every engine completes. They're never executed on the host.

---

## Live deploy in ~10 minutes (Contabo / Hetzner / DigitalOcean)

You need:
- A Ubuntu 24.04 server with a public IPv4 (a €4.50/mo Contabo VPS S is plenty)
- A domain pointing at the server (`A` record → server IP)
- Free API keys (instant signup):
  - VirusTotal — https://www.virustotal.com/gui/my-apikey
  - MetaDefender — https://metadefender.opswat.com/account/api-key
  - Hybrid Analysis — https://www.hybrid-analysis.com/apikeys/info

Then on the server (as root):

```bash
git clone https://github.com/siegelws/filescanner.git /opt/filescanner
cd /opt/filescanner
cp .env.example .env
# edit .env — paste the API keys + generate SECRET_KEY with: openssl rand -hex 32
nano .env
bash infra/deploy.sh your-domain.com
```

That one script installs Docker, opens the firewall, fetches a Let's Encrypt
cert, builds the containers, runs the DB migration, and launches the stack.

When it finishes, open `https://your-domain.com` — drag a file in, watch
results stream live.

---

## Architecture

```
Browser ──HTTPS──> Next.js (web) ──┐
                                   │ REST + WS
                                   ▼
                                FastAPI (api) ──── PostgreSQL
                                   │
                                   │ enqueue
                                   ▼
                              Redis (queue + pub/sub)
                                   │
                                   ▼
                          Celery worker(s)
                          │
        ┌─────────────────┼──────────────────────────────────────┐
        ▼                 ▼                                      ▼
    ClamAV daemon     YARA (in-proc)            HTTP API adapters
    (clamd TCP)       w/ rule packs             VirusTotal · MetaDefender
                                                Hybrid Analysis · MalwareBazaar
                                                CIRCL Hashlookup
```

| Layer    | Tech                                                       |
|----------|------------------------------------------------------------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind, react-dropzone |
| Backend  | FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2        |
| Queue    | Celery + Redis                                             |
| DB       | PostgreSQL 16                                              |
| Realtime | WebSocket + Redis pub/sub                                  |
| Engines  | ClamAV daemon · YARA · VT/MD/HA/MalwareBazaar/CIRCL APIs   |
| TLS      | nginx + Let's Encrypt (via `infra/deploy.sh`)              |

---

## Folder layout

```
filescanner/
├── docker-compose.yml          # web + api + worker + postgres + redis + clamav + nginx
├── .env.example
├── backend/
│   ├── app/
│   │   ├── api/                # scans, auth, engines, ws routers
│   │   ├── core/               # JWT, rate limit
│   │   ├── models/             # User, Scan, EngineResult
│   │   ├── schemas/            # Pydantic DTOs
│   │   ├── services/           # upload (quarantine), hash, notify (pub/sub)
│   │   ├── scanners/           # ONE FILE PER ENGINE
│   │   │   ├── base.py
│   │   │   ├── clamav.py            ← INSTREAM over TCP to clamd
│   │   │   ├── yara_scanner.py      ← compiled rule cache, hot-reload
│   │   │   ├── virustotal.py        ← hash lookup → upload+poll fallback
│   │   │   ├── metadefender.py      ← OPSWAT v4 API
│   │   │   ├── hybrid_analysis.py   ← CrowdStrike Falcon hash search
│   │   │   ├── malwarebazaar.py     ← abuse.ch (no key, free)
│   │   │   └── hashlookup.py        ← CIRCL EU CERT (no key, free)
│   │   └── workers/            # celery_app, scan_tasks (fan-out dispatcher)
│   ├── rules/                  # YARA rule pack (mounted into worker)
│   ├── engines.json            # registry — toggle engines without code changes
│   └── alembic/                # database migrations
├── frontend/                   # Next.js app
├── infra/
│   ├── deploy.sh               # one-shot Ubuntu 24.04 deploy
│   └── nginx.conf              # TLS termination + WS upgrade
└── storage/                    # bind-mounted upload quarantine (gitignored)
```

---

## Engine list (out of the box)

| ID                 | What                                  | API key needed?   | Coverage             |
|--------------------|---------------------------------------|-------------------|----------------------|
| `clamav`           | ClamAV daemon (in-cluster)            | no                | 1 engine, real-time  |
| `yara`             | YARA + bundled rule pack              | no                | rule-based heuristic |
| `virustotal`       | VirusTotal v3                         | yes (free tier OK) | 70+ engines aggregated |
| `metadefender`     | OPSWAT MetaDefender Cloud             | yes (free tier OK) | ~20 engines aggregated |
| `hybrid_analysis`  | CrowdStrike Falcon Sandbox            | yes (free tier OK) | sandbox + AV verdicts  |
| `malwarebazaar`    | abuse.ch hash corpus                  | no                | known-bad lookup     |
| `hashlookup`       | CIRCL Hashlookup (NSRL/MISP)          | no                | known-good/bad       |

So one upload yields verdicts from **roughly 90+ engines** when you have the
three free API keys configured. Without keys you still get ClamAV + YARA +
MalwareBazaar + Hashlookup — fully usable.

Disable individual engines by editing `backend/engines.json` and restarting the
worker. No code changes needed.

---

## API

```
POST   /api/auth/register     { email, password }            → { access_token, user }
POST   /api/auth/login        { email, password }            → { access_token, user }
GET    /api/auth/me                                         → UserPublic

GET    /api/engines                                         → [{ id, name, vendor, enabled }, …]

POST   /api/scans             multipart: file, engines?     → { id, status, engines_requested, ws_url }
GET    /api/scans                                           → [ScanSummary]   (user's history)
GET    /api/scans/{id}                                      → ScanDetail
WS     /api/ws/scans/{id}                                   → stream { snapshot | result | progress | completed }
```

OpenAPI docs at `/api/docs`.

---

## Security model

- **No execution on the host.** Files are streamed to `storage/uploads/` (mode
  `0600`, opaque random name), hashed, then either sent to local engines
  (clamd over TCP, YARA in-proc) or to vendor APIs by hash. Nothing is `exec`'d.
- **Auto-shred.** When every engine finishes, the upload is overwritten and
  unlinked.
- **Rate limiting.** SlowAPI on `/api/scans` (10/min/IP) and `/api/auth/*` (5/min).
- **Auth.** JWT (HS256), bcrypt passwords. Guest scans allowed; the scan ID is
  a capability (share the URL only with people you'd share the verdict with).
- **TLS.** Let's Encrypt + nginx termination; HSTS / X-Frame-Options / etc.

---

## Development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+asyncpg://scanner:scanner_dev_pw@localhost/scanner
export REDIS_URL=redis://localhost:6379/0
export SECRET_KEY=$(openssl rand -hex 32)
alembic upgrade head
uvicorn app.main:app --reload --port 8000
# in another shell:
celery -A app.workers.celery_app.celery worker --loglevel=info

# Frontend
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 \
NEXT_PUBLIC_WS_URL=ws://localhost:8000 \
npm run dev
```

---

## Costs at a glance

| Item                      | $/mo |
|---------------------------|------|
| Contabo VPS S (4 vCPU/8GB) | ~$5 |
| ClamAV + YARA              | free |
| VirusTotal free API        | free (500 req/day, 4/min — fine up to ~5k scans/mo if hash hits dominate) |
| MetaDefender free          | free (modest quota) |
| Hybrid Analysis free       | free |
| MalwareBazaar, Hashlookup  | free |
| **Total to run as-is**     | **~$5/mo** |

For higher volume (5k+ scans/mo) upgrade the VT/MetaDefender tiers — see the
README at `vm-scripts/README.md` for the old VM-based path if you ever want to
add real local AV engines as well.
