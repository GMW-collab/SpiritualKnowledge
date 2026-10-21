# Testing report

Run on 21 October 2026, Python 3.13, Chromium 141 (headless), against the data imported from harkhowal-site on the same day (37 series, 2,333 recordings, 15 videos).

## Automated tests

Run with `python -m unittest discover -s tests -p "test_*.py"` (44 tests) and `python tests/browser_check.py` (37 checks). Both run on every pull request (`.github/workflows/test.yml`); the unit and build tests also run before every publish.

| Suite | Tests | Result | What it covers |
|---|---|---|---|
| `test_sources.py` | 15 | Pass | Each adapter against recorded fixtures, no network: YouTube feed and Data API paging (private videos dropped, API key scrubbed from messages), keeping the archive and keeping previous data when offline; Gurmatveechar listing parsing, titles, date memory, refusal to save a listing that shrank by half; RSS/Atom parsing, HTML stripped, summaries shortened, `javascript:` links dropped, items imported unpublished; Google Sheet dates and link sanitising; Facebook needing credentials, and importing posts for review; BaniDB normalisation, verified and not-found checks, one request per Ang, no re-checking of verified lines |
| `test_knowledge.py` | 14 | Pass | Gurmukhi folding and whole-word matching (ਮਨ does not match ਮਨਮੁਖ; ਬ੍ਰਹਮ does not match ਬ੍ਰਹਮਚਾਰੀ); Ang ranges and Japji pauris to katha; Gurbani display rules; **content integrity**: every Gurbani line fully sourced, every theme's Gurbani known, no Gurbani quoted loose in prose, every comparison names its tradition and source, graph and shelves reference real items, external items attributed, every theme link records how it was made, overrides add/remove/confirm |
| `test_build.py` | 15 | Pass | Cloudflare files: `_redirects` targets exist and are not shadowed, `_headers` carries the security policy, no inline scripts or style attributes (so the policy needs no `unsafe-inline`), `wrangler.jsonc` points at the build; Full build: every page exists (11 themes, 37 series); every internal link resolves; one `h1`, alt text, named buttons, `lang`, skip link on every page; unique titles, descriptions, canonical links; provenance glosses and all five layers on every theme page; every Gurbani block has Ang, a labelled translation and `lang="pa"`; unverified lines hidden; Ang 466 links to Babaji's katha of Ang 465 to 467; sitemap valid and excludes `/review/`; Wix redirects; search index contents; no template leaks |
| `browser_check.py` | 37 | Pass | Served the way Cloudflare serves the site (headers, redirects, trailing slashes, 404 page): old Wix addresses redirect, unknown addresses get the 404 page, security headers are sent, no Content-Security-Policy violations; No script errors on ten page types; pressing a recording opens the player and streams from Gurmatveechar; moving to another page keeps the same document and the same track (audio continues); URL, title and Back button behave; search for "ego" puts Haumai first, ਹੁਕਮ finds Hukam, "vichar sagar" finds the series, a nonsense query explains what to try; "Go to Ang 466" finds the right recording; Gurmukhi filter on the library; theme chips on Watch; Review page produces override JSON; first Tab reaches the skip link; no sideways scrolling at 390 px on six pages; dark mode uses the night palette; page weight |

Defects found by these tests and fixed during the work: search listed every theme for any query (relevance bonus applied to non-matches); "ego" matched "Begowal" (substring matching, now word-start); a shelf listed divan series with no profile; a duplicated sentence in theme glosses.

## Cloudflare

Checked on 21 October 2026 against the real Cloudflare account:

- `wrangler deploy --dry-run` passes in GitHub Actions on every push.
- Cloudflare's own build of the `platform` branch (Wrangler 4.151.3) ran `python3 scripts/build.py`, read 122 files and uploaded them successfully. Earlier failures, and how they were fixed: the Worker name did not match (`harkhowal` vs `spiritualknowledge`); branch previews need a `previews` block.
- The production build of `main` still fails until the pull request is merged, because `main` holds only the imported old page and no Wrangler configuration.

## Measurements

Uncompressed / gzip (Cloudflare compresses responses):

| File | Size | Compressed |
|---|---|---|
| Home page | 16.8 KB | 4.5 KB |
| A theme page (Haumai) | 24.2 KB | 7.3 KB |
| Library index | 23.8 KB | 5.4 KB |
| Largest page (Suraj Granth, 1,014 recordings) | 680 KB | 21.3 KB |
| site.css / site.js | 28.4 / 29.8 KB | 7.0 / 9.5 KB |
| Search index (loaded only on the search page) | 1.24 MB | 59 KB |

Local load (no network latency, fonts and thumbnails blocked): DOMContentLoaded 53 to 118 ms on the home, theme and largest series pages. Real-world timing depends on Google Fonts and YouTube thumbnails, and should be measured with PageSpeed Insights on the preview address.

## Manual review

Done by screenshot at 1280 px and 390 px, light and dark: home, themes index, three theme pages, library, two series pages, watch, search, about, sources. Fonts and YouTube thumbnails could not load in the test environment, so screenshots show fallback fonts and empty thumbnails; check both on the preview.

Also checked by hand:
- Every one of the 23 Gurbani lines resolves to a recording of Babaji's katha of that Ang or pauri.
- Every automatic theme link was read once against the real titles; rules producing false links were corrected (for example the name "Karam Singh" matching *karam*, ਬ੍ਰਹਮ matching ਬ੍ਰਹਮਚਾਰੀ, and the generic word "vichar").
- A build for the GitHub preview address (`/SpiritualKnowledge/`) contains no links outside that path; navigation, the player and search work there.

## Not tested here (cannot be, from this environment)

- **Live sources.** This environment cannot reach YouTube, Gurmatveechar, BaniDB or Facebook. The adapters are tested against recorded responses; their first live run is the first workflow run after merging. The YouTube and Gurmatveechar logic is carried over from the existing site, whose daily runs already work.
- **BaniDB verification.** No Gurbani line is yet machine-checked; the pages say so ("Not yet machine-checked against BaniDB"), and the one line marked `to-verify` stays hidden until it passes. The BaniDB response format is handled defensively (any `unicode` field anywhere in the response); if the first run reports errors, check the Review page.
- **Real audio playback**, screen readers (VoiceOver, TalkBack), and older browsers.

## Before going live

- [ ] Open the preview on a phone and a desktop; play a recording, move between pages, use the lock-screen controls.
- [ ] Check the Sources page after the first run: YouTube, Gurmatveechar and BaniDB should show "Working".
- [ ] Check the Review page's Gurbani section: every line verified, none failed.
- [ ] Run PageSpeed Insights on the home page and a theme page.
- [ ] Have the theme essays reviewed (EDITORIAL.md).
