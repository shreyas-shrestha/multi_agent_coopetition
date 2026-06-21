# Context Window Parliament showcase

Replay data comes from the deterministic Python worlds and policies in this repository.

```bash
python showcase/exporter/export_replays.py
python showcase/exporter/export_strategy_summary.py
cd showcase
npm install
npm run dev
```

Run `npm run build` before shipping. The default hearing is `incident-response-medium-004` with the Trained Speaker policy.

## Deploy to Vercel

Grayed **Install Command** / **Build Command** in the Vercel dashboard is normal — they come from `vercel.json` in the repo, not the UI. Edit the file and push to change them.

### Recommended setup

1. Import `github.com/shreyas-shrestha/multi_agent_coopetition`.
2. **Settings → General → Root Directory** → `showcase/app` → Save.
3. Enable **Include source files outside of the Root Directory** (same section).
4. **Settings → Build & Development Settings** → turn **off** overrides for Install, Build, and Output Directory.
5. Redeploy from latest `main`.

Vercel reads `showcase/app/vercel.json` (edit that file and push to change grayed commands):

- Install: `cd .. && npm ci`
- Build: `npm run build`

If commands still show `npm ci --prefix showcase`, Root Directory is still set to the repo root — change it to `showcase/app` and redeploy. If settings stay stuck, disconnect and re-import the GitHub repo.

No environment variables are needed for the replay-only showcase.

For **live hearings** (Trained Speaker via HUD Gateway + Anthropic Haiku specialists):

1. Deploy the Modal orchestrator:
   ```bash
   modal secret create context-window-parliament-hud \
     HUD_API_KEY="$HUD_API_KEY" \
     ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"
   modal deploy modal_orchestrator.py
   ```
2. Copy the `web` URL from Modal (ends in `.modal.run`).
3. In Vercel → **Environment Variables**, set:
   ```
   NEXT_PUBLIC_ORCHESTRATOR_URL=https://YOUR-WORKSPACE--context-window-parliament-orchestrator-web.modal.run
   ```
4. Redeploy the showcase. Select **Trained Speaker** — the UI switches to live mode automatically.

Specialists use `PARLIAMENT_ANTHROPIC_MODEL=claude-haiku-4-5-20251001` on Modal. The Speaker uses `parliament-qwen36-35b-clean` through the HUD Gateway (no weight export).

```bash
cd showcase/app && npx vercel --prod
```

Keep `HUD_API_KEY` and `ANTHROPIC_API_KEY` in Modal secrets only — never in the browser or Vercel.
