# Testing report

Last updated 22 October 2026, against the live site on Cloudflare and the data of that day (37 series, 2,333 recordings, 15 videos, 39 Gurbani lines).

## Automated, on every push

Every push runs four checks on GitHub; Cloudflare builds a preview of every branch, and `main` deploys only after merging a pull request whose checks have passed. The daily content update also runs the unit and build tests and saves nothing if they fail.

| Check | Size | Result | What it covers |
|---|---|---|---|
| `tests/test_sources.py` | 18 tests | Pass | Each source adapter against recorded responses (YouTube feed and API, Gurmatveechar, feeds, Google Sheet, Facebook, BaniDB): parsing, keeping previous data when a source is down, secrets never logged, unsafe links dropped, imported items unpublished until approved; BaniDB verified, not-found and **wrong Ang** (a line found on a neighbouring Ang is reported and hidden) |
| `tests/test_knowledge.py` | 14 tests | Pass | Gurmukhi matching; Ang and pauri index; Gurbani display rules; **content integrity**: every Gurbani line fully sourced, no Gurbani quoted loose in prose, every comparison names its source, the journey's seven steps each have text, a source and real topics |
| `tests/test_build.py` | 18 tests | Pass | Every page exists and every internal link resolves; one `h1`, alt text, named buttons, `lang` on every page; unique titles and descriptions; Cloudflare `_headers`, `_redirects` and `wrangler.jsonc`; no inline scripts or styles (so the security policy needs no `unsafe-inline`); provenance labels on themes, topics and the journey; every Gurbani block carries its Ang and a labelled translation; each khand pauri links to Babaji's katha of that pauri; Latest ordering; topic link reasons; search index |
| `tests/browser_check.py` | 57 checks | Pass | In Chromium, served the way Cloudflare serves the site: no script errors on 12 page types; redirects and 404; security headers; the player starts, streams from Gurmatveechar and survives moving between pages; Back button; search across English and Gurmukhi (‘ego’ finds Haumai, ‘gurmukh’ the journey, ਸਚ ਖੰਡ its step); journey path, step links and katha list; topic finder; Latest filters and Show more; Go to Ang; Review page; keyboard skip link; no sideways scrolling at 390px; dark mode |
| `tests/a11y_check.py` | 13 pages, light and dark, desktop and phone | **0 serious, 0 minor** | axe-core 4.10, WCAG 2.1 A and AA rules, including colour contrast in both themes |
| Wrangler dry run | | Pass | Cloudflare's own tool reads `wrangler.jsonc` and runs the build |

Defects found by these checks and fixed: the theme map's links sat inside an image role; the sources table scrolled on phones without keyboard access; search listed every theme for any query; ‘ego’ matched ‘Begowal’; the phone menu overflowed once Journey was added.

## Checked on the live site (22 October 2026)

At `https://spiritualknowledge.imonyx.workers.dev`, in Chrome:

- **Gurbani:** all 39 lines verified against BaniDB by the daily check; all 22 passages on the journey show ‘Checked against BaniDB’.
- **Audio:** a real click on ‘Babaji's katha of the five khands’ played the recording from Gurmatveechar (Japji pauris 28 to 36, 89 minutes); it kept playing after moving to the Topics page.
- **Headers:** Content-Security-Policy, HSTS, nosniff, and `X-Robots-Tag: noindex` on the workers.dev address; the manifest is served as `application/manifest+json`; `/shabadguru` redirects.
- **Fonts:** Alegreya, Alegreya Sans and Noto Serif Gurmukhi load.

## Measurements

Uncompressed / gzip:

| File | Size | Compressed |
|---|---|---|
| Home page | 19 KB | 5 KB |
| Journey | 79 KB | 14 KB |
| Largest page (Suraj Granth, 1,014 recordings) | 739 KB | 23 KB |
| site.css / site.js | 35 / 36 KB | 8 / 11 KB |
| Search index (search page only) | 1.3 MB | 66 KB |
| Latest list data (Latest page only) | 554 KB | 35 KB |

## Not covered

- Screen readers (VoiceOver, TalkBack) by hand, and older browsers.
- PageSpeed Insights on the final domain (run it once harkhowal.com is attached).
- Lock-screen media controls on a phone.
