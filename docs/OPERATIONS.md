# Deployment, configuration, maintenance and costs

The site is hosted on **Cloudflare** as a Worker named `spiritualknowledge` that serves static files (no server code runs). Cloudflare is connected to this repository: every push to `main` is built and deployed, and every other branch gets a preview build. Nothing goes live except through `main`.

## How a deploy works

1. Something changes `main`: a merged pull request, an editor's commit, or the daily update saving new data.
2. Cloudflare runs `npx wrangler deploy`. Wrangler reads `wrangler.jsonc`, runs `python3 scripts/build.py` to generate `_site/`, and uploads the files that changed.
3. Cloudflare serves `_site/` with the rules the build writes into it: `_headers` (security policy and caching) and `_redirects` (permanent redirects from the old Wix addresses). `/themes` redirects to `/themes/`, and unknown addresses get the 404 page.

On every push, GitHub also runs the tests, the browser checks (served the way Cloudflare serves the site) and `wrangler deploy --dry-run`, so a broken configuration shows up on the pull request.

## Going live (in order)

**1. Merge pull request #1** into `main`. Cloudflare deploys it within a few minutes at `https://spiritualknowledge.<your-subdomain>.workers.dev` (*Workers & Pages → spiritualknowledge → Domains* shows the exact address). The daily update then starts at 04:17 UTC; its first run performs the first live BaniDB check and the first run of every source, shown on the site's Sources and Review pages. To run it at once: *Actions → Daily content update → Run workflow*.

**2. Retire the old set-up**, so the two do not both crawl Gurmatveechar or claim the domain: in the old `harkhowal-site` repository, *Actions* → disable "Daily content update"; in Cloudflare, check that the older `harkhowal-site` Worker has no custom domain attached.

**3. Move harkhowal.com to Cloudflare** once you are happy with the workers.dev site.
1. In Cloudflare: *Add a domain* → `harkhowal.com` (Free plan). Cloudflare copies the existing DNS records; check that any email (MX) records are among them before continuing.
2. At the registrar where the domain is held (Wix, if bought there), replace the nameservers with the two Cloudflare gives you. This can take a few hours.
3. *Workers & Pages → spiritualknowledge → Settings → Domains & Routes → Add → Custom domain*: add `www.harkhowal.com`, then `harkhowal.com`. Cloudflare creates the DNS records and certificates.
4. *Rules → Redirect Rules → Create from template → "Redirect from root to WWW"* so `harkhowal.com` goes to `www.harkhowal.com`, the canonical address used in the site's links and sitemap.
5. Complete the Wix migration checklist in [SOURCES.md](SOURCES.md), then cancel the Wix plan (keep the domain).

Old Wix addresses (`/shabadguru`, `/sggs-katha`, `/babaji-videos` …) redirect permanently to their new pages.

## Cloudflare files in this repository

| File | Purpose |
|---|---|
| `wrangler.jsonc` | Worker name (must match the dashboard), build command, the `_site` folder, trailing-slash and 404 handling, workers.dev and preview URLs |
| `_site/_headers` (generated) | Content-Security-Policy, HSTS and other security headers; long caching for `/assets/`; `noindex` for `/review/` |
| `_site/_redirects` (generated) | 301 redirects from the old Wix addresses |

If the Worker is ever renamed in Cloudflare, change `name` in `wrangler.jsonc` to match, or builds fail.

## Configuration (`config.json`)

| Key | Meaning |
|---|---|
| `site_name`, `site_url`, `contact_email` | Shown on every page; `site_url` is used for canonical links and the sitemap |
| `repository` | Used for the "Open overrides.json on GitHub" button on the Review page |
| `sources` | The source registry; see SOURCES.md |
| `youtube_channel_id`, `youtube_url`, `social` | Babaji's channel and links |
| `gurmatveechar_root`, `audio_categories`, `series_gurmukhi` | The katha folder, and Gurmukhi names for series |
| `programmes_csv_url` | The published Google Sheet |

**Secrets** (*Settings → Secrets and variables → Actions*): `YOUTUBE_API_KEY` (optional), `FACEBOOK_PAGE_ID` and `FACEBOOK_PAGE_TOKEN` (optional). They are only read by the update step, never written to the site or the logs.

## Routine maintenance

- **Nothing daily.** New katha appears by itself each morning (04:17 UTC).
- **Weekly or monthly:** open `/review/`; confirm new theme links, approve imported items, check for Gurbani lines that failed.
- **When a new series appears on Gurmatveechar** it shows under "Newly added" in the library. Give it a Gurmukhi name in `config.json` (`series_gurmukhi`), place it on a shelf and describe it in `content/texts.json`.
- **If the Actions tab shows a red cross**, open the run: each source reports separately, one failing never affects the others, and the site keeps the previous day's material.
- **GitHub pauses scheduled workflows** after 60 days without repository activity. The daily data commits normally prevent this; if it happens, GitHub emails the owner and the workflow can be re-enabled in the Actions tab.

## Running costs

| Item | Cost |
|---|---|
| Cloudflare hosting | Free on the Workers Free plan: requests for static files are free and unlimited; the site is about 150 files, far inside the per-deploy file limit |
| GitHub Actions | Free for public repositories. A private repository's free allowance (2,000 minutes a month) also covers it: a daily run takes a few minutes, longer on days with many new recordings |
| YouTube Data API | Free within the daily quota; this site uses a small fraction |
| BaniDB API | Free; a handful of requests only when Gurbani lines change |
| Facebook Graph API | Free |
| Fonts | Google Fonts, free |
| Domain harkhowal.com | The existing renewal fee |
| AI services | None. No AI model runs on the live site. The theme essays were drafted once, with AI assistance, and are now ordinary files. Future AI features would carry usage-based costs; see ROADMAP |

There is no server code, no database and nothing to patch.
