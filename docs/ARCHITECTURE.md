# Architecture, content model and design

## 1. Strategic direction

The subject is not "spirituality in general". It is the katha of a living Sikh sant, rooted in Gurbani, with an unusually wide reach into Sikh history, Bhai Gurdas Ji and Bhai Nand Lal Ji, and classical Indian philosophy read through Gurmat. The platform is built to serve three kinds of visitor:

- **Sangat who already listen**: they want the newest divan, and to carry on where they left off. Served by the home page, the persistent player and the library.
- **Seekers with a question but not a vocabulary**: they would search "ego", not ਹਉਮੈ. Served by themes framed as questions, and search that understands both languages.
- **Readers who want depth**: served by the five-layer theme pages, the Gurbani-to-katha links, honest comparisons with other traditions, and text profiles.

Principles, in priority order: Gurmat as the frame; integrity before novelty; Babaji's katha as the author's voice, never paraphrased; depth over volume; zero running cost and no machinery the Dera cannot maintain.

## 2. Information architecture

```
/                     Newest katha (hero) · Begin with a question · Continue listening · Recent divans · Library shelves · Programmes · Dera
/themes/              Eleven themes as questions + map of their connections
/themes/<slug>/       Discover · Understand · Explore Babaji's katha · How this connects · Reflect · Go deeper
/listen/              Six shelves (Gurbani; Bhai Sahiban; Itihaas; Indian philosophy read through Gurmat; Talks; Divans)
/listen/<series>/     Text profile (labelled) · every recording · Go to Ang (Guru Granth Sahib series)
/watch/               Babaji's videos, filterable by theme · curated videos by others (labelled)
/search/              One search across themes, series, recordings and videos, English and Gurmukhi
/about/               Babaji, Dera Sant Ghar, Sant Jawala Singh Ji, lineage
/sources/             What comes from where, how it is checked, privacy, credits
/review/              Editorial queue (noindex)
Old Wix URLs          /shabadguru, /sggs-katha, … redirect to their new homes
```

The old site's structure (menus by media type) was not kept. Themes are the primary way in; the library is organised by **what is being taught** rather than where it was uploaded.

## 3. Content model

Everything is a file in the repository: easy to review, version and restore.

### Provenance kinds (shown on every page)

| Kind | Where it lives | How it is shown |
|---|---|---|
| Gurbani | `content/gurbani.json` | Gurmukhi, transliteration, translation (all labelled), Granth, Ang, bani, author, check status, link to the full Ang, Babaji's katha of that Ang |
| Translation, editorial | inside each Gurbani line | labelled "Translation, editorial"; `translation_note` records alternative readings |
| Babaji's katha | `data/audio.json`, `data/videos.json` (imported) | linked by title or Ang, never summarised |
| Editorial introduction | `content/themes/*.md`, `content/texts.json`, `content/graph.json` | margin gloss "Editorial introduction … Not Gurbani and not Babaji's words" + review status |
| Comparative note | `::: compare Tradition | Source` blocks | names tradition and source; states connection and difference |
| Where views differ | `::: tension` blocks | makes contested points visible |
| Other teachers and makers | `content/external.json`, `data/feeds.json` | creator credited, linked not copied, approval required |

### Entities

- **Gurbani line**: `id, gurmukhi, translit, rendering, source{granth, ang, bani, author}, japji_pauri?, confidence (high | to-verify), translation_note?`. Verification results live separately in `data/gurbani-verification.json` (`status: verified | not-found | error | not-applicable`, date, fingerprint of the text).
- **Theme**: a Markdown file with a JSON header: `slug, gurmukhi, title, subtitle, question, summary, terms (English synonyms for search), match {gurmukhi[], roman[], series[]}, anchor, review{status, drafted, by}`; sections `discover, understand, reflect, practise`.
- **Relationship** (`content/graph.json`): `a, b, kind, why, tension?, gurbani[]`. Relationships are explicit and explained, not inferred from shared tags.
- **Series / text profile** (`content/texts.json`): `text, tradition, author (or "unknown"), about, uncertainty?, themes[]`, grouped into shelves.
- **Recording** (imported): `p` (path at Gurmatveechar, the canonical id), `t` title, `d` upload date, `g` sub-group. Id `a:<path>`.
- **Video** (imported): `id, title, published, description` (first 400 characters). Id `yt:<videoId>`.
- **Feed item** (imported): `id f:<feed>:<hash>, feed, title, link, published, author, summary (≤280 chars, plain text), first_seen, last_seen, auto_publish`.
- **Theme link** (computed at build): item id → theme → `{via, confirmed}`. `via` records how the link was made: `title: ‘ਹੁਕਮ’`, `description: …`, `series: listed for this theme`, `curated`, `editor`.

### Lifecycle

| Stage | Meaning | Where |
|---|---|---|
| Discovered | seen at the source | adapter run |
| Imported | stored with metadata and canonical id | `data/*.json` |
| Processed | classified, linked to Angs, indexed for search | `scripts/knowledge.py` at build |
| Reviewed | an editor confirmed or corrected it | `content/editorial/overrides.json` |
| Published | visible on the site | build output |

Babaji's own channel and katha folder are trusted sources: their items publish once processed, and their theme links show as automatic until reviewed. Feed items from anywhere else stay unpublished until approved. Gurbani lines marked `to-verify` stay unpublished until BaniDB or an editor confirms them.

### Editorial overrides (`content/editorial/overrides.json`)

`theme_add`, `theme_remove`, `theme_confirmed` (item id → theme slugs), `approve`, `reject` (feed item ids), `gurbani_confirmed` (line ids), `theme_review` (slug → status, reviewer, date). The Review page writes this file's new contents for the editor to paste.

## 4. Source integration architecture

```
config.json "sources"  ──>  scripts/update.py  ──>  scripts/sources/<adapter>.py  ──>  data/*.json
                                   │                                                      │
                                   └──> data/sync-status.json (state, message, counts,    │
                                        last attempt, last success per source)            │
content/*  ───────────────────────────────────────────────────────────────────────────────┤
                                                                                           v
                              scripts/knowledge.py (classify, Ang index, display rules)
                                                                                           │
                                                   scripts/build.py ──> _site/ ──> Cloudflare
```

Each adapter exposes `run(cfg, source, fetch=...)` and returns a `SourceResult(state, message, counts)`. Rules every adapter follows:

- **Keep yesterday's data on failure.** An unreachable or shrunken source never empties the site (`kept-previous`).
- **Polite and bounded.** Gurmatveechar: one page a second, 150 pages and 3,000 date look-ups per run at most, and each date is looked up once ever. BaniDB: only lines whose text changed are re-checked.
- **Retries with backoff** (`common.request`), timeouts, and secrets scrubbed from every logged message.
- **Never copy what can be linked.** Audio streams from Gurmatveechar; videos embed from YouTube on demand; feed items keep a short summary and link out.
- **Testable offline.** `fetch` is injectable; tests use recorded fixtures.

Adding a source: write `scripts/sources/<name>.py` with `run()`, add it to `ADAPTERS` in `update.py`, register it in `config.json`. Adding a feed needs no code at all (see SOURCES.md).

## 5. Knowledge layer

- **Classification** is rule-based and transparent: each theme lists Gurmukhi terms (matched by whole word or word start, after folding nukta, tippi/bindi and addak) and roman patterns, plus whole series. Video descriptions are used up to the first hashtag or link. Every link records why it was made, so an editor can judge it. Rules were tuned against the real titles to remove false positives (for example *karam* matching the name Karam Singh).
- **Gurbani ↔ katha.** Recording titles are parsed for Ang ranges ("Ang 0465 to 0467") and Japji pauris. Every Gurbani line on the site resolves to Babaji's katha of that Ang or pauri: 23 of 23 lines today.
- **Search** is a compact JSON index (59 KB compressed) searched in the browser. Queries are folded the same way as the content, matched at word starts, and expanded through theme vocabularies, so "ego", "pride", ਹੰਕਾਰ and ਹਉਮੈ all reach Haumai and the items linked to it. Semantic embeddings were considered and not used: the corpus is mostly short titles, so embeddings would add cost and an external dependency without a measurable gain. They become worthwhile once transcripts exist (see ROADMAP).
- **No AI question-answering yet.** With no transcripts, an AI answer would have to invent what Babaji said. It is on the roadmap behind transcripts and a retrieval design that cites recordings and timestamps.

## 6. Front end

- Static HTML for every page (fast, indexable, works without JavaScript). One stylesheet and one script, no frameworks, no build tools.
- **Persistent player.** Links are followed in-page (fetch, swap `<main>`, update history), so audio keeps playing while browsing; any failure falls back to a normal page load. Positions, speed and recent listening are kept in the visitor's own browser, with a "forget" button on the Sources page.
- Videos load from `youtube-nocookie.com` only when pressed.
- Accessibility: semantic landmarks, skip link, one `h1` per page, `lang="pa"` on Gurmukhi, labelled controls, visible focus, reduced-motion support, keyboard shortcuts (`/` search, space play/pause).

## 7. Design system

**Concept: amrit vela**, the hour before dawn when simran is done. Night indigo above, the first light of a dawn horizon as the single recurring motif (a thin kesri line under the hero and theme headers), limewash below.

| Token | Light | Dark | Use |
|---|---|---|---|
| night | #161A33 | | header, hero, footer, player |
| paper | #F1F2EF | #11142A | page |
| ink | #1C1F2A | #ECEBF4 | text |
| neela | #3B4A8C | #AFBBF2 | links, Gurmukhi theme names |
| kesri | #E08A2E | #F0A04B | only what is live or playing |
| bani-bg | #F7F3EA | #1B1F3D | the Gurbani "lectern" |

**Type.** Alegreya (humanist serif with calligraphic roots) for reading; Alegreya Sans for interface; Noto Serif Gurmukhi for display Gurmukhi; Mukta Mahee for Gurmukhi in lists.

**The memorable element: the tika layout.** Theme pages set Gurbani like a shabad on a lectern, with commentary in a reading column and provenance glosses in the margin, the way a traditional tika places commentary around the text. On phones the glosses move above each section.

Deliberately avoided: card grids, caps eyebrows, decorative religious symbols used as ornament, stock imagery, entrance animations.
