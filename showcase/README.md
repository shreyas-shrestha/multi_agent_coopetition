# Showcase — All I Have Is Attention

Static Next.js demo for **Context Window Parliament**: replay bundled hearings or stream live sessions from the Modal orchestrator.

Full project documentation: [../README.md](../README.md)

## Local development

```bash
# From repo root — regenerate replay JSON (optional)
python showcase/exporter/export_replays.py
python showcase/exporter/export_strategy_summary.py

cd showcase
npm install
npm run dev
```

Default docket: `incident-response-medium-004` (Incident Response).

### Live mode locally

```bash
cp showcase/app/.env.example showcase/app/.env.local
# Edit NEXT_PUBLIC_ORCHESTRATOR_URL to your Modal orchestrator URL
```

Live mode activates when `NEXT_PUBLIC_ORCHESTRATOR_URL` is set and the **Trained Speaker** policy is selected.

## Build

```bash
cd showcase
npm run build
```

Output is a static export in `showcase/app/out/` (`output: "export"` in `next.config.ts`).

## Deploy to Vercel

1. Import the repository.
2. Set **Root Directory** to `showcase/app`.
3. Leave install/build commands as defined in `showcase/app/vercel.json`:
   - Install: `cd .. && npm ci`
   - Build: `npm run build`
4. Add for live hearings:
   ```bash
   NEXT_PUBLIC_ORCHESTRATOR_URL=https://<workspace>--context-window-parliament-orchestrator-web.modal.run
   ```
5. Deploy.

Replay mode works without environment variables. Keep `HUD_API_KEY` and `ANTHROPIC_API_KEY` in Modal secrets only — not in Vercel.

**Common mistake:** Do not combine Root Directory `showcase/app` with install command `npm ci --prefix showcase` — that path is wrong and causes lockfile errors.

```bash
cd showcase/app
npx vercel --prod
```

## Modes

| Mode | Requirement | Source |
|------|-------------|--------|
| Replay | None | `public/replays/*.json` |
| Live | `NEXT_PUBLIC_ORCHESTRATOR_URL` | Modal SSE (`/api/hearing/stream`) |

Policies in replay JSON: **Trained Speaker**, **Loud Capture**, **Uniform Floor**.
