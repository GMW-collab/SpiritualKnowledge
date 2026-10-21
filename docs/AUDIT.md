# Audit: harkhowal.com and the harkhowal-site repository

Audited 21 October 2026. Two things exist today, and they are at very different stages.

## 1. The live harkhowal.com (Wix)

harkhowal.com is still served by Wix. Its navigation is Sikhi (Shabad Guru, Sants), Babaji Katha (five audio pages), Videos (three pages), Literature and Updates.

| Area | What it holds | Assessment |
|---|---|---|
| Home | Short pieces on Guru Granth Sahib Ji, Guru Nanak Dev Ji and the Panj Pyare; an "Updates" box last dated 11/02/2019 | Dated. Says almost nothing about Babaji himself. |
| Shabad Guru (`/shabadguru`) | Long essay on Guru, Shabad, Hukam and Haumai with Ang references | The page credits a Harvard/edX course ("Sikhism through its scriptures") as its source and reads as reproduced course text. **Not migrated verbatim**; its subjects are covered by new, original theme pages. |
| Sants (`/sants-gurmukhs`) | Portrait gallery; biography of Sant Jawala Singh Ji (b. 1 May 1889, Lagari; army 1907; disciple of Sant Aiya Singh Ji 1911; Dera Sant Ghar from 1918; d. 13 Nov 1957); a Bansawli Nama image | The only substantive original-history content. Facts are carried into the new About page, rewritten, and flagged for the family/sevadars to confirm. Portraits and the Bansawli Nama image need to be supplied as files (see migration checklist). |
| Katha pages | Five pages of audio | Superseded by the repository's automatic Gurmatveechar import (2,333 recordings). "Misc Katha" says "more coming soon". |
| Videos | Babaji Divans; 4 "Jeevan Katha" videos of other mahapurakhs; 3 documentaries (BBC and others) | Babaji's divans are superseded by the YouTube import. The 7 curated external videos are kept as attributed, reviewed items. |
| Literature | `Aarti.pdf`, `Punjabi Primer.pdf` (no author given) | Must be downloaded from Wix and committed before the Wix plan ends; authorship should be recorded. |

There are no articles, no YouTube or Facebook links, and no structured data. The site is rigid because every addition is manual.

## 2. The repository (GMW-collab/harkhowal-site)

A rebuild already exists and is published by GitHub Pages from `main` at `gmw-collab.github.io/harkhowal-site` (DNS still points to Wix, so this is effectively staging).

**Stack.** One 50 KB `index.html` (inline CSS and JS), a standard-library Python updater (`scripts/update.py`) run daily by GitHub Actions, JSON data files and `config.json`. No build step, no dependencies, no paid services. Hosting is free; the only cost is the domain.

**Data sources that genuinely work today**

| Source | Method | State |
|---|---|---|
| Babaji's YouTube channel | Public Atom feed (no key). Returns only the newest 15; older ones are kept as they accumulate. | Working. 15 videos stored. |
| Gurmatveechar.com, Babaji's folder | Polite crawl of public folder pages (1 s between pages), MP3s streamed from Gurmatveechar | Working. 37 series, 2,333 recordings. Upload dates were empty in the committed data; a run that looks them up was in progress during the audit. |
| Programmes Google Sheet | Published CSV | Built but unconfigured (`programmes_csv_url` empty). |
| Facebook | — | Link only. |

**Strengths worth keeping:** the in-page audio player (resume position, speed, media-session controls), the daily automation with "keep yesterday's data if a source fails", Gurmukhi series names, zero running cost, a README written for a non-technical owner.

**Limitations**

1. **One URL for everything.** 2,333 recordings and 37 series have no pages of their own, so nothing is findable from Google, shareable, or linkable from a theme.
2. **No knowledge layer.** Content is organised only by where it was uploaded. There are no themes, no link between a Gurbani reference and the katha that explains it, no account of what the Vedanta and Yoga texts are or why a Gurmat teacher reads them.
3. **Search is substring-only**, English and Gurmukhi kept apart ("ego" finds nothing; ਹੰਕਾਰ and ਹਉਮੈ are not connected).
4. **Ingestion is one script** with three hard-wired sources; adding a feed or another channel means editing code. No record of when each source last succeeded.
5. **No editorial controls.** Everything imported is published; there is nowhere to correct a classification or hold an item for review.
6. **No SEO plumbing:** no sitemap, robots.txt, canonical URLs, structured data or social images; Wix URLs would 404 after the switch.
7. **No tests.**

## 3. What the material itself reveals

Mining the titles (not assumptions) shows what Babaji actually teaches:

- **Gurbani katha indexed by Ang.** The Guru Granth Sahib series (380 recordings) is titled by Ang range ("Ang 0449 to 0455"), Japji by pauri, Bhai Gurdas by vaar. Any Gurbani line quoted on the site can therefore link to Babaji's katha of that very Ang.
- **Recent YouTube titles are topic lists** in Babaji's own words: ਹੁਕਮ ਮੰਨਣਾਂ ਬਹੁਤ ਔਖਾ, ਨਾਮ ਦਾ ਭਰੋਸਾ, ਮੁਕਤ ਕਿਵੇਂ ਹੋਈਏ, ਮਨ ਦੀਆਂ ਵਾਸ਼ਨਾਵਾਂ, ਹੰਕਾਰ ਦੇ ਪੱਲੇ ਕੁੱਝ ਨਹੀਂ, ਕਰਮਾਂ ਦਾ ਹਿਸਾਬ, ਇਕਾਂਤ ਦੇ ਲਾਭ, ਗੁਰੂ ਧਾਰਨ ਕਰਨਾ.
- **A wide philosophical range read through Gurmat:** Vedant Darshan, Yog Darshan, Ashtavakra Gita, Vichar Sagar, Vichar Mala, Vairagya Shatak, Dhammapada, Chanakya Niti, Prabodh Chandar Natak, alongside Sikh history (Suraj Parkash, Nanak Parkash) and Bhai Gurdas and Bhai Nand Lal. This range, typical of the sant and Nirmala tradition of learning, is the platform's most distinctive intellectual asset, and the place where honest comparison (where these texts agree with Gurbani, and where they do not) adds real value.
- **Topic-titled talks** (Man Budh Atam: Bhagti Te Prem, Sansaar Da Tiyaag, Kaamna Gyan Nu Rokda, Aatma Ki Hai, Gyan Ki Hai; Patanjali: Moksh, Naam Di Mehima, Satsangat) and **lineage katha** (Sant Jawala Singh Ji's jeevan in ten parts, Sant Karam Singh Ji Hoti Mardan, the Naurangabad mahapurakhs).

The themes on the new site are taken from these, not from a generic spiritual taxonomy.

## 4. Technical and access constraints

- The work environment can reach GitHub but not YouTube, Gurmatveechar or BaniDB. Ingestion therefore runs where it already works: in GitHub Actions. New adapters were tested against recorded fixtures, and run live on the first workflow run.
- GitHub run logs and the Pages settings API are not readable from this environment; the Pages source must be switched by the owner (one setting).
- YouTube's public feed caps at 15 items. Full archive needs a free YouTube Data API key. Captions/transcripts of the channel can only be downloaded through OAuth by the channel owner.
- Facebook's Graph API needs a Page access token granted by a page admin; the Facebook presence is a profile-style page. Blocked until the owner grants access.
- No transcripts exist for the audio, so anything claiming to state "what Babaji said about X" would be invented. Links between katha and themes are made from titles and Ang ranges only, and are labelled as such.
