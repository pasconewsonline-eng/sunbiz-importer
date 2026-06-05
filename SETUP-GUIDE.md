# Sunbiz New-Business Importer — Setup Guide

This sets up a FREE automated job that runs every morning, downloads the
Florida Sunbiz daily business filings, keeps only Pasco-area cities, and
sends them to your website's New Businesses page.

You will NOT write any code. You just create a free account, paste in files
I gave you, and add two secret values. Takes about 15 minutes, one time.

---

## STEP 1 — Get your two values from WordPress (2 min)

1. Log into WordPress.
2. In the left menu, click **New Businesses**.
3. Find the box titled **"Automated Import Settings."**
4. Copy these two things somewhere handy (Notes app, etc.):
   - **Endpoint URL** (looks like `https://yoursite.com/wp-json/pcn-nb/v1/import`)
   - **Import Key** (a long string of letters/numbers)

Keep these private — the key is like a password.

---

## STEP 2 — Create a free GitHub account (3 min)

1. Go to **https://github.com**
2. Click **Sign up**.
3. Use your email, pick a username and password. (Free plan is all you need.)
4. Verify your email when they send the confirmation.

---

## STEP 3 — Create a repository (3 min)

1. Once logged in, click the **+** in the top-right corner → **New repository**.
2. Repository name: type `sunbiz-importer`
3. Set it to **Private** (recommended — only you see it).
4. Click **Create repository**.

---

## STEP 4 — Add the files (5 min)

You have a folder from Claude called `sunbiz-importer` containing:
- `sunbiz_import.py`
- `requirements.txt`
- `.github/workflows/sunbiz.yml`

Easiest way to upload:

1. On your new repository page, click **"uploading an existing file"**
   (it's a link in the middle of the page), OR click **Add file → Upload files**.
2. Drag in `sunbiz_import.py` and `requirements.txt`.
3. Click **Commit changes**.

Now add the workflow file (it lives in a subfolder):
4. Click **Add file → Create new file**.
5. In the filename box, type exactly:  `.github/workflows/sunbiz.yml`
   (As you type the slashes, GitHub makes the folders automatically.)
6. Open the `sunbiz.yml` Claude gave you, copy ALL its text, and paste it in.
7. Click **Commit changes**.

---

## STEP 5 — Add your two secrets (3 min)

1. In your repository, click **Settings** (top tab).
2. Left menu: **Secrets and variables → Actions**.
3. Click **New repository secret**.
   - Name: `WP_ENDPOINT`
   - Secret: paste your Endpoint URL from Step 1.
   - Click **Add secret**.
4. Click **New repository secret** again.
   - Name: `WP_KEY`
   - Secret: paste your Import Key from Step 1.
   - Click **Add secret**.

---

## STEP 6 — Run the first test (2 min)

1. Click the **Actions** tab (top of repository).
2. If GitHub asks to enable workflows, click the green **"I understand… enable"** button.
3. Click **"Sunbiz Daily Import"** on the left.
4. Click **Run workflow** (right side) → **Run workflow** (green button).
5. Wait ~1 minute, then click the run to watch it. Click the **import** job to see the log.

### What to look for in the log:
- It prints a **"Top-level directory listing"** — this shows the real folder names on the Sunbiz server.
- It prints **"Matched X Pasco-area filings"** and a **WordPress response: 200**.

**Copy that log text and send it to Claude.** The first run is partly a discovery
run — the directory listing tells Claude the exact folder path for the daily file,
so the positions can be fine-tuned if needed.

---

## After it works

- It runs automatically every morning (set in the schedule).
- New Pasco filings appear on your **/new-businesses/** page on their own.
- You can always click **Run workflow** to run it on demand.
- To change the time, edit the `cron:` line in `sunbiz.yml`.

---

## Honest notes

- The very first run may show "Could not locate the corporate daily folder
  automatically." That's expected — it prints the real folder names so we can
  point it correctly. Send Claude the log and it's a 1-line fix.
- Fixed-width files sometimes need the city/date positions nudged by a character.
  If imported filings show a slightly cut-off city or date, tell Claude.
- The fictitious-name (DBA) file can be added the same way once the corporate
  file is confirmed working.
