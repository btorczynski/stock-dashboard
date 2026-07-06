# Host the dashboard for free, at a permanent link

This publishes your dashboard to a **permanent URL that never changes** —
`https://stock-dashboard.pages.dev` — and refreshes it automatically. Total cost: **$0**.

**How it works (no always-on server needed):** a free scheduled job on GitHub runs your
Python every 30 minutes during market hours, builds a static snapshot
(`public/data.json` + `public/index.html`), and publishes it to **Cloudflare Pages**.
Cloudflare serves that snapshot at your permanent link, fast, worldwide, for free.

You do this **once**. After that it runs itself.

---

## What you need (both free)

1. A **GitHub** account — https://github.com/signup
2. A **Cloudflare** account — https://dash.cloudflare.com/sign-up

---

## Step 1 — Put this folder on GitHub

Easiest way (no command line):

1. Install **GitHub Desktop** — https://desktop.github.com
2. Open it → **File ▸ Add Local Repository** → choose this folder
   (`Claude Stock Simulator`). It will offer to create a repository here — say yes.
3. Click **Publish repository**.
   - **Uncheck "Keep this code private."** A **public** repo gets *unlimited* free
     GitHub Actions minutes; private repos are capped at 2,000/month, which ~30-minute
     refreshes can exceed. (Your secrets stay encrypted and private either way — only
     the code is public, and there's nothing sensitive in it.)

> Already comfortable with git? Just `git init && git add . && git commit -m "init"`
> and push to a new **public** GitHub repo.

---

## Step 2 — Create the Cloudflare Pages project (this sets your URL)

1. Go to the Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** →
   **Upload assets** (a.k.a. "Direct Upload").
2. Name the project exactly **`stock-dashboard`**.
   - **This name is your permanent URL:** the project becomes
     `https://stock-dashboard.pages.dev`. Pick a different name if you want a different
     URL — but if you do, change `--project-name=stock-dashboard` in
     `.github/workflows/refresh.yml` to match.
3. It may ask you to upload something to finish creating it — just drag in any file
   (even this `.md`); the real content gets published by the Action in Step 5. Finish
   creating the project.

---

## Step 3 — Make a Cloudflare API token + grab your Account ID

**API token:**
1. Cloudflare dashboard → your profile (top-right) → **My Profile ▸ API Tokens** →
   **Create Token**.
2. Use the **"Edit Cloudflare Workers"** template (it includes Pages), **or** create a
   custom token with permission **Account ▸ Cloudflare Pages ▸ Edit**.
3. Create it and **copy the token** (you only see it once).

**Account ID:**
- On **Workers & Pages**, your **Account ID** is shown in the right-hand sidebar
  (and in the URL `dash.cloudflare.com/<account-id>/...`). Copy it.

---

## Step 4 — Add those two values to GitHub as secrets

In your GitHub repo: **Settings ▸ Secrets and variables ▸ Actions ▸ New repository secret**.
Add exactly these two:

| Secret name | Value |
|---|---|
| `CLOUDFLARE_API_TOKEN` | the token from Step 3 |
| `CLOUDFLARE_ACCOUNT_ID` | your Account ID from Step 3 |

(Secrets are encrypted and never shown in logs — safe even in a public repo.)

---

## Step 5 — Run it

1. In your repo, open the **Actions** tab. If prompted, click **"I understand my
   workflows, enable them."**
2. Pick **"Refresh dashboard → Cloudflare Pages"** on the left → **Run workflow** →
   **Run workflow**.
3. Watch it run (~2–4 min the first time — it fetches ~20 years of history to build the
   backtests). When it's green, open:

   **https://stock-dashboard.pages.dev**

That's it. From now on it refreshes automatically every 30 minutes during market hours.
The link stays the same forever.

---

## Good to know

- **The link never changes.** It always deploys to the *production* branch
  (`--branch=main`), which maps to `stock-dashboard.pages.dev`. (Preview deploys get a
  random per-build URL — we deliberately don't use those.)
- **Change how often it refreshes:** edit the `cron:` line in
  `.github/workflows/refresh.yml`. It's in **UTC**; the default `*/30 12-23 * * 1-5`
  is every 30 min, noon–11pm UTC, weekdays (covers US pre-market → after-hours).
  GitHub's minimum is every 5 minutes and runs can be delayed a few minutes.
- **Refresh by hand anytime:** Actions tab → Run workflow.
- **Want your own domain** (e.g. `dashboard.yoursite.com`)? In the Pages project →
  **Custom domains** → add it. Still free.
- **Yahoo Finance occasionally rate-limits cloud IPs.** If a run shows gaps, it's
  usually that — the next run fixes it, and the committed `*_state.json` seed keeps the
  backtests from going blank. The build refuses to publish an empty snapshot over a good
  one.
- **Public-repo housekeeping:** GitHub disables scheduled workflows after **60 days with
  no repo activity**. If that ever happens you'll get an email — one click re-enables it
  (or push any small change).
- **Cost:** $0. Public-repo Actions minutes are free and unlimited; Cloudflare Pages'
  free plan covers this easily.

---

## Files involved

| File | Purpose |
|---|---|
| `build_snapshot_static.py` | Runs your data build once, writes `public/data.json` + a static `public/index.html` pointed at it. |
| `.github/workflows/refresh.yml` | The scheduled job: build the snapshot, publish to Cloudflare Pages. |
| `.gitignore` | Keeps build output out of git. |

Your existing local dashboard (`run_dashboard.bat` / `python stock_dashboard.py`) still
works exactly as before — this only **adds** the hosted version.
