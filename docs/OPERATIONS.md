# Deployment, configuration, maintenance and costs

Nothing in this repository has been deployed. Every step below that makes something public needs the owner's go-ahead.

## Deploying (in order)

**1. Review the pull request** from the `platform` branch and merge it into `main`. Merging alone publishes nothing: the workflow builds and tests the site, and skips publishing while GitHub Pages is switched off.

**2. Preview on GitHub's address.** In this repository: *Settings → Pages → Build and deployment → Source: GitHub Actions*. Then *Actions → Update, build and publish → Run workflow*. The site appears at `https://gmw-collab.github.io/SpiritualKnowledge/` (the build adjusts its links to that address automatically). This first run also performs the first live BaniDB check and the first runs of every source; their results appear on the site's Sources and Review pages.

> GitHub Pages is free for public repositories. For a private repository it needs a paid GitHub plan.

**3. Move harkhowal.com to it** once you are happy with the preview.
1. In the *old* repository `harkhowal-site`: *Settings → Pages* → remove its custom domain if one is set, and in *Actions* disable its "Daily content update" workflow, so the two do not both crawl Gurmatveechar or claim the domain.
2. Here: *Settings → Pages → Custom domain* → `www.harkhowal.com` → *Save*. Tick *Enforce HTTPS* when offered.
3. At the domain's registrar (Wix, if bought there): `www` → **CNAME** → `gmw-collab.github.io`; the bare domain `@` → **A** records `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`.
4. Run the workflow again so links are rebuilt for the root of the domain. DNS can take a few hours.
5. Complete the Wix migration checklist in [SOURCES.md](SOURCES.md), then cancel the Wix plan (keep the domain).

Old Wix addresses (`/shabadguru`, `/sggs-katha`, `/babaji-videos` …) redirect to their new pages.

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
| GitHub Pages hosting | Free (public repository; generous limits: sites up to 1 GB, about 100 GB of traffic a month) |
| GitHub Actions | Free for public repositories. A private repository's free allowance (2,000 minutes a month) also covers it: a daily run takes a few minutes, longer on days with many new recordings |
| YouTube Data API | Free within the daily quota; this site uses a small fraction |
| BaniDB API | Free; a handful of requests only when Gurbani lines change |
| Facebook Graph API | Free |
| Fonts | Google Fonts, free |
| Domain harkhowal.com | The existing renewal fee |
| AI services | None. No AI model runs on the live site. The theme essays were drafted once, with AI assistance, and are now ordinary files. Future AI features would carry usage-based costs; see ROADMAP |

There is no server, no database and nothing to patch.
