# Deployment quick reference

Production target: **247ai.live**. Start with the [deployment index](README.md) for the full doc map.

## One-command deploy

Credentials live in **`.env.prod`** only (gitignored). Template: **`.env.prod.example`**.

```bash
chmod +x scripts/deploy.sh   # once

# GCP backend + frontend
./scripts/deploy.sh gcp

# voice-ws on OCI (SSH key defaults to ~/.ssh/oci_voice_ws)
OCI_SSH_HOST=132.145.130.61 ./scripts/deploy.sh voice-ws

# Full stack (GCP, then voice-ws if OCI_SSH_HOST is set)
OCI_SSH_HOST=132.145.130.61 ./scripts/deploy.sh all

# Single components
./scripts/deploy.sh backend
./scripts/deploy.sh frontend
./scripts/deploy.sh migrate
./scripts/deploy.sh domains
./scripts/deploy.sh --help
```

| Component | What it deploys |
|-----------|-----------------|
| `all` | Backend + frontend on GCP, then voice-ws on OCI (skips OCI if `OCI_SSH_HOST` unset) |
| `gcp` | Backend + frontend on Cloud Run only |
| `backend` | FastAPI → `backend-247ai` |
| `frontend` | Next.js → `frontend-247ai` |
| `voice-ws` / `voice` / `worker` | Pipecat WebSocket worker on OCI VM |
| `migrate` | Alembic `upgrade head` against Supabase |
| `domains` | Cloud Run mappings for `api.247ai.live` + `www.247ai.live` |

## Production URLs

| Service | URL |
|---------|-----|
| Frontend | https://www.247ai.live |
| Backend API | https://api.247ai.live |
| voice-ws health | https://voice.247ai.live/health |
| voice-ws WebSocket | wss://voice.247ai.live/ws |

## Smoke checks

```bash
curl -s https://api.247ai.live/health
curl -s https://www.247ai.live
curl -s https://voice.247ai.live/health
```

These are liveness checks only. Before calling a deployment complete, follow
the [mandatory browser and PSTN voice release gate](runbook.md#mandatory-release-gate-ai-agent-calling)
with a release-test organization that has active voice entitlements and
prepaid credit headroom.

## Prerequisites

- **gcloud** CLI — project `project-bb848762-18cb-4cd6-858`, region `us-central1`
- **Docker** — local builds use `linux/amd64` for Cloud Run
- **`.env.prod`** — from `.env.prod.example`
- **voice-ws:** OCI VM with Docker; ports 22/80/443 open; DNS A record `voice.247ai.live` → VM IP

## OCI SSH (voice-ws only)

Not stored in `.env.prod`:

```bash
export OCI_SSH_HOST=132.145.130.61      # VM public IP
export OCI_SSH_USER=ubuntu               # default
export OCI_SSH_KEY=~/.ssh/oci_voice_ws   # default private key
```

Test: `ssh -i ~/.ssh/oci_voice_ws ubuntu@132.145.130.61 "echo ok"`

## Custom domains (Cloudflare)

1. Verify domain: `gcloud domains verify 247ai.live`
2. Map domains: `./scripts/deploy.sh domains`
3. Cloudflare DNS (grey cloud / DNS-only):
   - `www` CNAME → Cloud Run frontend target
   - `api` CNAME → Cloud Run backend target
   - `voice` A → OCI VM public IP

## Post-deploy webhooks

| Vendor | URL |
|--------|-----|
| Stripe | `https://api.247ai.live/api/v1/billing/webhook/stripe` |
| Twilio voice | `https://api.247ai.live/api/v1/voice/twilio/incoming` |
| Twilio status | `https://api.247ai.live/api/v1/voice/twilio/status` |
| Google OAuth (tools) | `https://api.247ai.live/api/v1/tools/callback` |
| Supabase Auth | Site URL `https://www.247ai.live`; redirect `https://www.247ai.live/**` |

See [Runbook](runbook.md) for architecture and first-time setup details.
