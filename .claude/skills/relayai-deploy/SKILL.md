---
name: relayai-deploy
description: "How RelayAI is deployed — co-hosted on the same home-lab server as convoxio-v2, behind the same Cloudflare Tunnel, on relay-ai.cloud. SSH access, Docker Compose stack, DNS/tunnel setup, redeploy steps, pending OAuth setup. Use whenever the user asks to deploy, check status, connect to the server, debug the live site, or touch anything about relay-ai.cloud."
trigger: /relayai-deploy
---

# RelayAI deployment

RelayAI is co-hosted on the **same home-lab server as convoxio-v2** (see that
repo's own `convoxio-deploy` skill at
`~/test/voice/convoxio-v2/.claude/skills/convoxio-deploy/SKILL.md` for the
underlying server/Tailscale/tunnel-service details — this skill only covers
what's specific to RelayAI). Two independent Docker Compose stacks share one
laptop and one `cloudflared` tunnel; ports were chosen not to collide with
convoxio-v2's.

## Connecting to the server

```
ssh convoxio-server
```

Same alias, same server, as convoxio-v2 (Tailscale IP `100.76.220.102`, LAN
fallback `192.168.1.2`, alias defined in `~/.ssh/config` on the dev machine).
There is no separate `relayai-server` alias — it's the same box.

## Architecture

```
Internet → Cloudflare (DNS + Tunnel) → cloudflared (systemd, on laptop, shared with convoxio-v2)
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
              relay-ai.cloud              www.relay-ai.cloud      (convoxio-v2 hostnames)
              → localhost:8002            → localhost:8002        → localhost:3001 / :8001
              (relay-ai api container)     (same)
```

Docker Compose stack lives at `~/relay-ai` on the server, cloned via git
(`git@github.com:harsh-u/relay-ai.git`, same SSH access as convoxio-v2 uses).
Compose file: `docker-compose.prod.yml`.

| Service    | Container port | Host port | Notes |
|------------|-----------------|-----------|-------|
| `api`      | 8000            | 8002      | FastAPI — everything (marketing site, `/v1/*`, `/login`, `/dashboard`) |
| `postgres` | 5432            | 5434      | `pgvector/pgvector:pg17`, container name `relayai-postgres` |

Deliberately distinct ports from convoxio-v2's own stack (8001/3001/5433) so
`docker compose ps` across both projects never collides. Both use
`restart: unless-stopped`.

The embedding model (`models/indic-sentence-bert-nli-int8`, ~237MB) is
**bind-mounted**, not baked into the image — `./models:/app/models` in
`docker-compose.prod.yml`. If it's ever missing after a fresh clone, copy it
over with `rsync -avz --progress models/indic-sentence-bert-nli-int8
convoxio-server:~/relay-ai/models/` from the dev machine (plain `scp -r` has
been observed to silently no-op here — use `rsync`).

## Cloudflare Tunnel

- **Same Cloudflare account and same tunnel** as convoxio-v2:
  `Vikramrajput9304@gmail.com`, tunnel name `convoxio`, id
  `60b598f7-dec9-4acd-9c6d-510c26261d99`. RelayAI does not have (and doesn't
  need) its own tunnel — one ingress config, multiple hostnames.
- **`relay-ai.cloud` is registered at Hostinger**, a separate zone from
  `convoxio.com`. Its nameservers were repointed to Cloudflare's
  (`mallory.ns.cloudflare.com`, `santino.ns.cloudflare.com`) and the zone was
  added to the same Cloudflare account, so both domains' DNS now live in
  Cloudflare even though they're registered at different registrars/zones.
- DNS records for `relay-ai.cloud` (in *its own* zone, not convoxio.com's):
  `relay-ai.cloud` and `www.relay-ai.cloud`, both `CNAME` →
  `60b598f7-dec9-4acd-9c6d-510c26261d99.cfargotunnel.com`, proxied. Cloudflare
  displays these as type "Tunnel" once saved correctly.
  - **Gotcha hit during setup**: `cloudflared tunnel route dns <tunnel> relay-ai.cloud`
    run from the CLI on the server creates the record in whichever zone the
    server's local `cert.pem` is scoped to — which was `convoxio.com`, not
    `relay-ai.cloud`. It silently created `relay-ai.cloud.convoxio.com`
    instead. Cross-zone record creation for a tunnel must be done manually via
    the Cloudflare **dashboard UI** (edit the record, change Type to CNAME,
    set Target to `<tunnel-id>.cfargotunnel.com`), not the CLI, unless you
    have an API token scoped to the target zone.
  - **Gotcha #2**: when editing an existing record's Target field via
    browser automation, a plain "fill" can *append* to the existing value
    instead of replacing it (e.g. `2.57.91.9160b598f7-...cfargotunnel.com` —
    old IP + new target concatenated) rather than erroring — always
    select-all (Ctrl+A) and clear before typing the new value, then verify
    the saved record shows as type "Tunnel" in the list view before moving on.
- Ingress config at `/etc/cloudflared/config.yml` on the server (shared
  file — convoxio-v2's hostnames live in the same file):
  ```yaml
  tunnel: 60b598f7-dec9-4acd-9c6d-510c26261d99
  credentials-file: /home/harsh/.cloudflared/60b598f7-dec9-4acd-9c6d-510c26261d99.json

  ingress:
    - hostname: app.convoxio.com
      service: http://localhost:3001
    - hostname: api.convoxio.com
      service: http://localhost:8001
    - hostname: convoxio.com
      service: http://localhost:3001
    - hostname: www.convoxio.com
      service: http://localhost:3001
    - hostname: relay-ai.cloud
      service: http://localhost:8002
    - hostname: www.relay-ai.cloud
      service: http://localhost:8002
    - service: http_status:404
  ```
  The catch-all `http_status:404` must stay the **last** rule. Validate any
  edit before restarting the live service:
  ```bash
  sudo cloudflared --config /etc/cloudflared/config.yml tunnel ingress validate
  ```
  (`--config` is a *global* flag, before the subcommand — `cloudflared tunnel
  ingress validate --config ...` fails with "flag provided but not defined".)
  Then apply with `sudo systemctl restart cloudflared` — this affects
  convoxio-v2's live traffic too since it's the same service, so immediately
  re-check `https://convoxio.com` and `https://app.convoxio.com` after
  restarting.

## Deploying / redeploying

No dedicated deploy script yet (unlike convoxio-v2's
`scripts/deploy-staging.sh`) — manual steps:

```bash
ssh convoxio-server
cd ~/relay-ai
git fetch origin && git checkout main && git pull
docker compose -f docker-compose.prod.yml run --rm api uv run alembic upgrade head   # if migrations changed
docker compose -f docker-compose.prod.yml up -d --build
```

## Useful commands on the server

```bash
cd ~/relay-ai
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs api --tail=50
docker compose -f docker-compose.prod.yml restart api      # e.g. after editing .env
git log -1 --oneline                                        # what commit is live
```

### Database access

```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U relayai -d relayai
```

## Secrets (`~/relay-ai/.env` on the server, chmod 600, never committed)

Generated once via Python's `secrets.token_urlsafe()` and written directly on
the server. Current keys in the file:

- `APP_NAME`, `APP_ENV=production`, `LOG_LEVEL=INFO`
- `POSTGRES_PASSWORD` — set
- `SESSION_SECRET_KEY` — set (Starlette session signing)
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — **blank, not yet configured**
- `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` — **blank, not yet configured**
- `BETA_ALLOWLIST_EMAILS` — comma-separated list, currently just
  `harsh.raj@screen-magic.com`

To add or rotate any of these:
```bash
ssh convoxio-server
nano ~/relay-ai/.env          # or: sed -i 's/^GOOGLE_CLIENT_ID=.*/GOOGLE_CLIENT_ID=xxx/' ~/relay-ai/.env
cd ~/relay-ai && docker compose -f docker-compose.prod.yml restart api
```
`.env` is loaded via `env_file` in `docker-compose.prod.yml`, so a container
restart (not rebuild) is enough to pick up changes.

## Pending / not yet done

- **OAuth apps not registered yet** — login is non-functional in production
  until Google/GitHub OAuth client credentials exist and are added to
  `.env` (see above). Redirect URIs needed:
  `https://relay-ai.cloud/auth/google/callback` and
  `https://relay-ai.cloud/auth/github/callback`.
- **No automated deploy script** (convoxio-v2 has one at
  `scripts/deploy-staging.sh`; RelayAI doesn't yet — worth porting the same
  pattern if deploys become frequent).
- **onnxruntime thread-capping** for the embedding model was flagged during
  capacity planning as worth doing before real production load, but not
  implemented.

## Public URLs

- https://relay-ai.cloud — marketing site / login / dashboard
- https://relay-ai.cloud/health — health check (`{"status":"ok","service":"relay-ai"}`)
- https://www.relay-ai.cloud — same app, `www` alias
