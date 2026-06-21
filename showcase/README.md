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

Vercel will read `showcase/app/vercel.json`:

- Install: `cd .. && npm ci`
- Build: `npm run build`

### If Root Directory is empty (repo root)

Vercel reads the repo-root `vercel.json` instead:

- Install: `npm ci --prefix showcase`
- Build: `npm run build --prefix showcase`

Use **one** root-directory mode. If commands look stuck after changing Root Directory, **disconnect and re-import** the GitHub repo or trigger a fresh production deploy from the latest commit.

No environment variables are needed for the replay-only showcase.

```bash
cd showcase/app && npx vercel --prod
```

When the live Modal endpoint is connected later, add its public URL as a Vercel environment variable and keep `HUD_API_KEY` and `ANTHROPIC_API_KEY` only in Modal secrets.
