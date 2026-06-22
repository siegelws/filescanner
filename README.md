# FileScan — Multi-AV malware analysis platform

A self-hosted, Kleenscan / Euroscan-style scanning service. Uploads are sent to
multiple **isolated VMware virtual machines**, each running a different
antivirus engine, and the per-engine verdicts are streamed back to the browser
over WebSocket.

> **Files are never executed on the host.** Every scan runs inside a VM that is
> reverted to a clean snapshot before and (in failure modes) after each scan.

---

## Architecture

```
Browser ──HTTPS──> Next.js 14 (web)
                       │
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
                       │  fan-out per engine
                       ▼
        VM Orchestrator (vmrun)
        ├── revert "clean" snapshot
        ├── power on VM
        ├── POST file → in-VM HTTPS agent
        ├── agent runs scan.ps1 → AV CLI
        ├── agent returns {detected, name, raw, version}
        └── power off + revert again
```

| Layer        | Tech                                                              |
|--------------|-------------------------------------------------------------------|
| Frontend     | Next.js 14 (App Router), TypeScript, Tailwind, react-dropzone     |
| Backend      | FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2                |
| Queue        | Celery + Redis                                                    |
| DB           | PostgreSQL 16                                                     |
| Realtime     | WebSocket + Redis pub/sub                                         |
| VM control   | VMware `vmrun` (Workstation/Player/Fusion). Swap for `pyVmomi` on ESXi/vCenter. |
| In-VM agent  | FastAPI HTTPS endpoint + per-engine PowerShell wrapper            |

---

## Folder layout

```
file-scanner/
├── docker-compose.yml         # api + worker + web + redis + postgres
├── .env.example
├── backend/                   # FastAPI app + Celery worker
│   ├── app/
│   │   ├── api/               # scans, auth, engines, ws routers
│   │   ├── core/              # security (JWT), rate limit
│   │   ├── models/            # User, Scan, EngineResult
│   │   ├── schemas/           # Pydantic DTOs
│   │   ├── services/          # upload, hash, notify (pub/sub)
│   │   └── workers/           # celery_app, scan_tasks, vm_orchestrator
│   ├── engines.json           # registry of AV engines (id, vendor, vm, agent URL)
│   └── alembic/               # database migrations
├── frontend/                  # Next.js app
│   ├── app/                   # page.tsx, scan/[id], history, login, register
│   ├── components/            # UploadZone, EngineSelector, ScanProgress, ResultsTable, ScanSummary
│   └── lib/                   # api.ts, ws.ts, utils.ts
├── vm-scripts/                # what runs INSIDE each AV VM
│   ├── common/agent.py        # shared HTTPS scan agent
│   └── <engine>/scan.ps1      # per-AV CLI wrapper (Defender/Kaspersky/...)
├── infra/nginx.conf
└── storage/                   # bind-mounted upload quarantine
```

---

## Quick start (host services)

```bash
# 1. Configure secrets
cp .env.example .env
openssl rand -hex 32   # paste as SECRET_KEY
openssl rand -hex 32   # paste as VM_AGENT_TOKEN

# 2. Bring up postgres + redis + api + worker + web
docker compose up -d --build

# 3. Run initial migration
docker compose exec api alembic upgrade head

# 4. Open the app
open http://localhost:3000
```

Out of the box you'll see the UI and be able to submit a file — but with no VMs
configured the per-engine scans will fail with "vmx_path required". Either:

- Provision real AV VMs (see `vm-scripts/README.md`), **or**
- Run in **mock mode** by setting `SKIP_VM_LIFECYCLE=true` on the worker and
  pointing each engine's `agent_url` in `backend/engines.json` to a stub that
  responds to `/scan` (handy for frontend development).

---

## Setting up the AV VMs

See [`vm-scripts/README.md`](vm-scripts/README.md) for the full per-engine
playbook. Summary:

1. Create one VMware VM per AV product (Windows 10/11 LTSC + Python 3.12).
2. Install the AV product. Disable cloud sample-sharing.
3. Drop `vm-scripts/common/agent.py` and the engine-specific `scan.ps1` into
   `C:\agent\` inside the VM.
4. Set `VM_AGENT_TOKEN` (same value as the host `.env`) + `SCAN_COMMAND`.
5. Run the agent on port 7443 with a self-signed cert.
6. Take a snapshot named **`clean`** — that's what the orchestrator reverts to.
7. On the worker host, export `ENGINES_VMX_<ID>=/path/to/<engine>.vmx`.

---

## Security model

- **Files never execute on the host.** They're streamed to `storage/uploads/`,
  hashed, then sent over HTTPS to in-VM agents. The host worker only `revertToSnapshot`s,
  `start`s, and `stop`s the VMs.
- **VM isolation.** VMs sit on a host-only `vmnet` segment with no default route.
  The "clean" snapshot is taken before any sample ever runs.
- **Per-VM single-product policy.** One AV per VM eliminates cross-engine
  interference and keeps detection names verbatim.
- **Random storage names.** Original filenames are kept only in PostgreSQL; the
  on-disk name is `secrets.token_hex(16) + ext`, mode `0o600`.
- **Auto-shred.** When all engines finish, the upload is overwritten and unlinked.
- **Rate limiting.** SlowAPI on `/api/scans` (10/min/IP) and `/api/auth/*` (5/min).
- **Auth.** JWT (HS256), bcrypt passwords. Guest scans allowed; the scan ID is
  the capability — share the URL only with people you'd share the verdict with.
- **Defence in depth.** Strict CORS, security headers via nginx, all DB access
  through SQLAlchemy parameterised queries, all file paths sanitised.

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

OpenAPI docs auto-served at `/api/docs`.

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
export VM_AGENT_TOKEN=$(openssl rand -hex 32)
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

## Roadmap

- YARA pre-scan on the host before VM dispatch (very cheap "known bad" tier)
- Dedup: if SHA256 was scanned in the last N days, surface the cached verdict
- Per-engine version pinning + automated "definitions freshness" rebuilds
- Linux engine VMs (ClamAV, Sophos for Linux) on KVM
- API keys + per-key quotas for programmatic use
