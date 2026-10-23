# Deployment, configuration, maintenance and costs

The site is hosted on **Cloudflare** as a Worker named `spiritualknowledge` that serves static files (no server code runs). Cloudflare is connected to this repository: every push to `main` is built and deployed, and every other branch gets a preview build. Nothing goes live except through `main`.

## How a deploy works

1. Something changes `main`: a merged pull request, an editor's commit, or the daily update saving new data.
2. Cloudflare runs `npx wrangler deploy`. Wrangler reads `wrangler.jsonc`, runs `python3 scripts/build.py` to generate `_site/`, and uploads the files that changed.
3. Cloudflare serves `_site/` with the rules the build writes into it: `_headers` (security policy and caching) and `_redirects` (permanent redirects from the old Wix addresses). `/themes` redirects to `/themes/`, and unknown addresses get the 404 page.

On every push, GitHub also runs the tests, the browser checks (served the way Cloudflare serves the site) and `wrangler deploy --dry-run`, so a broken configuration shows up on the pull request.

## Production status

Live at **`https://www.harkhowal.com`** since 23 October 2026, deployed by Cloudflare from `main`. `harkhowal.com` redirects there (301, Cloudflare redirect rule). The working address `https://spiritualknowledge.imonyx.workers.dev` stays up but is not indexed.

**Domain and email set-up.** The domain is registered at GoDaddy with Cloudflare's nameservers (randy / rihana.ns.cloudflare.com); DNS is managed in Cloudflare. The Wix A and CNAME records were removed and both names are attached to the Worker as custom domains. Cloudflare Email Routing forwards `satnam@harkhowal.com` to harkhowal@outlook.com (MX and SPF records added by Cloudflare); the site's contact address is `satnam@harkhowal.com`.

**Done and checked**
- Every push is tested before it can go live: 50 unit and build tests, 57 browser checks served the way Cloudflare serves the site, an axe-core accessibility audit (WCAG 2.1 A and AA) of every kind of page in light and dark mode at desktop and phone widths, and a Wrangler dry run. Cloudflare builds a preview of every branch.
- The content update runs twice a day (04:17 and 16:17 UTC), refuses to save data if the tests fail, and keeps the previous day's material if a source is unreachable.
- Security headers (Content-Security-Policy without `unsafe-inline`, HSTS, nosniff, referrer and permissions policies) are served, confirmed on Cloudflare.
- The workers.dev address sends `X-Robots-Tag: noindex`, so only harkhowal.com will be indexed once attached. Confirmed on Cloudflare.
- Gurbani quotations are checked against BaniDB every day; a line that fails, or turns out to be on a neighbouring Ang, is hidden until corrected.
- No cookies, no analytics, no third-party scripts. Videos load from YouTube's privacy-enhanced player only when pressed.
- Home-screen icon and web manifest; custom 404 page; permanent redirects from the old Wix addresses.

**Needs the owner** (in order of importance)
1. **Learned review** of the eleven theme essays and the journey (the Review page records it). Until then each page says "Awaiting review by a learned reader".
2. **Search Console**: add `www.harkhowal.com` in Google Search Console and submit `https://www.harkhowal.com/sitemap.xml`.
3. **Retire the old set-up**: disable the "Daily content update" workflow in the `harkhowal-site` repository, and check its Worker has no custom domain.
4. **Optional connections**: `FACEBOOK_PAGE_ID` and `FACEBOOK_PAGE_TOKEN` for Facebook posts; a published Google Sheet for programmes (SOURCES.md).
5. **Wix migration checklist** before cancelling Wix (SOURCES.md).

## Moving harkhowal.com to Cloudflare (done 22–23 October 2026; kept for reference)

1. In Cloudflare: *Add a domain* → `harkhowal.com` (Free plan). Cloudflare copies the existing DNS records; check that any email (MX) records are among them before continuing.
2. At the registrar (GoDaddy), replace the nameservers with the two Cloudflare gives you. This can take a few hours.
3. *Workers & Pages → spiritualknowledge → Settings → Domains & Routes → Add → Custom domain*: add `www.harkhowal.com`, then `harkhowal.com`. Cloudflare creates the DNS records and certificates.
4. *Rules → Redirect Rules → Create from template → "Redirect from root to WWW"* so `harkhowal.com` goes to `www.harkhowal.com`, the canonical address used in the site's links and sitemap.
5. In Google Search Console, add `www.harkhowal.com` and submit `https://www.harkhowal.com/sitemap.xml`.
6. Complete the Wix migration checklist in [SOURCES.md](SOURCES.md), then cancel the Wix plan (keep the domain).

Old Wix addresses (`/shabadguru`, `/sggs-katha`, `/babaji-videos` …) redirect permanently to their new pages.

## Cloudflare files in this repository

| File | Purpose |
|---|---|
| `wrangler.jsonc` | Worker name (must match the dashboard), build command, the `_site` folder, trailing-slash and 404 handling, workers.dev and preview URLs |
| `_site/_headers` (generated) | Content-Security-Policy, HSTS and other security headers; long caching for `/assets/`; `noindex` for `/review/` and for the workers.dev address |
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

- **Nothing daily.** New katha and videos appear by themselves (updates at 04:17 and 16:17 UTC).
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
