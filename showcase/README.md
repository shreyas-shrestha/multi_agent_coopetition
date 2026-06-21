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

1. Import `github.com/shreyas-shrestha/multi_agent_coopetition`.
2. **Settings → General → Root Directory** → set to **`showcase/app`** and save.
3. **Settings → Build & Development Settings** → turn **off** any overrides for Install Command, Build Command, and Output Directory. `showcase/app/vercel.json` owns those values:
   - Install: `cd .. && npm ci`
   - Build: `npm run build`
   - Framework: Next.js
4. Enable **Include source files outside of the Root Directory** (same General / Root Directory section) so the workspace install in `showcase/` works.
5. Redeploy. No environment variables are needed for the replay-only showcase.

For CLI deploy from the app directory:

```bash
cd showcase/app
npx vercel
npx vercel --prod
```

When the live Modal endpoint is connected later, add its public URL as a Vercel environment variable and keep `HUD_API_KEY` and `ANTHROPIC_API_KEY` only in Modal secrets.
