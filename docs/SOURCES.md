# Sources: what is connected, what is not, and how to connect more

Status as of 21 October 2026. The live status of each source is shown on the site's **Sources** page after every daily run; a source is only shown as working when its last run succeeded.

## Summary

| Source | Method | Status | What is needed |
|---|---|---|---|
| Babaji's YouTube channel | Public Atom feed (newest 15), channel feed then playlist feed | **Working, but unreliable from GitHub**: YouTube sometimes answers 404 to GitHub's servers, so the update tries both feeds twice a day and keeps the previous list if both fail | An API key (next row) makes it dependable |
| … full upload history, and Shorts | YouTube Data API v3: the uploads playlist (UU…) and the Shorts playlist (UUSH…) | **Working** since 23 Oct 2026 (key saved as `YOUTUBE_API_KEY`). The whole archive is read once, then only new pages | Nothing |
| … captions / transcripts | YouTube captions API | **Not possible without the channel owner** | OAuth consent by the channel owner (roadmap) |
| Gurmatveechar.com, Babaji's folder | Polite crawl of public folder pages; audio streamed, not copied | **Working**: 37 series, 2,333 recordings, all dated | Courtesy email to Gurmatveechar recommended |
| Programmes | Google Sheet published as CSV | **Built, not set up** | A published sheet link in `config.json` |
| BaniDB | API check of each quoted Gurbani line against its Ang | **Built**; first run happens in GitHub Actions (this work environment cannot reach BaniDB) | Nothing |
| Facebook page | Graph API, Page posts | **Built, needs permission** | Page admin creates a token (below) |
| Other websites, blogs, channels | RSS / Atom feed adapter | **Built**; none registered yet | Add a feed to `config.json` |
| SikhNet Play playlist (30 divans, mostly 1990 and 1994) | No feed offered | **Linked** on Listen and Watch | Nothing |
| Previous harkhowal.com (Wix) | One-off migration | **Done** for text; files outstanding | Download two PDFs and portraits before cancelling Wix |

Nothing here scrapes sites that have not published their content for this kind of use. Public visibility is not treated as permission: YouTube and Facebook are read only through their official feeds and APIs; Gurmatveechar's audio is streamed from Gurmatveechar and credited, as on the current site.

## YouTube

**Feed (no setup).** `https://www.youtube.com/feeds/videos.xml?channel_id=UCAq_dxXKBpMJQmr-msu0YmA` gives the newest 15 uploads. Older videos already stored are kept, so the archive grows from the day the site started.

**Full history (optional, free).**
1. Sign in to <https://console.cloud.google.com/> with any Google account. Create a project (for example "Harkhowal site").
2. *APIs & Services → Library*: enable **YouTube Data API v3**.
3. *APIs & Services → Credentials → Create credentials → API key*. Click the key, under *API restrictions* choose *Restrict key* and tick only YouTube Data API v3.
4. In GitHub: *Settings → Secrets and variables → Actions → New repository secret*, name `YOUTUBE_API_KEY`, paste the key.
5. Run *Actions → Update, build and publish → Run workflow*. The whole upload history is fetched once; after that only new pages. Daily use is far inside the free quota (10,000 units/day; this uses roughly one unit per 50 videos).

**Transcripts.** YouTube only lets the channel owner download captions, through OAuth. If the Dera wants transcripts (they would make search and source-grounded answers far better), see ROADMAP item 3.

## Gurmatveechar.com

The adapter reads Babaji's folder listings once a day, pausing a second between pages, and looks up each new recording's upload date once. If the folder ever appears to have shrunk by more than half, the previous data is kept. It is courteous to tell Gurmatveechar that harkhowal.com plays the recordings in its own player; the footer and every series page credit and link them.

## Programmes sheet

1. Make a Google Sheet with headings `Date`, `End date`, `Place`, `Title`, `Link` (dates like `2026-11-14` or `14/11/2026`).
2. *File → Share → Publish to web*, choose the sheet and **Comma-separated values (.csv)**, *Publish*, copy the link.
3. Paste it into `"programmes_csv_url"` in `config.json` and commit.

Programmes appear on the home page the next morning and drop off once past. Links that are not `http(s)` are ignored.

## Facebook page

The Graph API only gives Page posts to an app that a Page admin has authorised. A Page admin does this once:

1. At <https://developers.facebook.com/> create an app (type *Business*), and add the **Facebook Login for Business** or **Pages API** use case, as Meta's current set-up flow offers.
2. In the *Graph API Explorer*, select the app, choose *Get Page Access Token*, select the Harkhowal Wale page and grant `pages_show_list` and `pages_read_engagement`.
3. Exchange it for a long-lived token (*Access Token Debugger → Extend Access Token*), then request the Page token again with the long-lived user token; Page tokens obtained this way do not expire.
4. Note the Page's numeric id (the page's *About → Page transparency*, or `GET /me/accounts` in the Explorer).
5. Add both as GitHub secrets: `FACEBOOK_PAGE_ID`, `FACEBOOK_PAGE_TOKEN`.

Meta changes these screens often; follow its current documentation where it differs. Imported posts appear on the Review page and are published only when an editor approves them. If the page is a personal profile rather than a Page, the API cannot read it; the footer link remains.

## Adding a website, blog or channel feed

Add an entry to `"sources"` in `config.json`:

```json
{"id": "feed:example", "adapter": "feed", "title": "Example Gurmat essays", "kind": "Other teachers",
 "url": "https://example.org/feed.xml", "creator": "Name of the author or publisher",
 "auto_publish": false, "method": "RSS feed", "terms": "Linked with credit; summaries only"}
```

Any YouTube channel has a feed at `https://www.youtube.com/feeds/videos.xml?channel_id=<id>`. Items wait for approval on the Review page. Only the title, link, date, author and a 280-character plain-text summary are stored; the site links to the original.

## Wix migration checklist (before cancelling the Wix plan)

- [ ] Download `Aarti.pdf` and `Punjabi Primer.pdf` from the old Literature page, record their authors, and add them under `files/` (then list them on the About page).
- [ ] Download the nine portraits from the old Sants page and the Bansawli Nama image, if the Dera holds the rights to publish them.
- [ ] Confirm the Sant Jawala Singh Ji biography on the About page (rewritten from the old site). The old page also said he supported the Akali and Babbar Akali movements and opposed the Panch Khalsa Diwan of Bhasaur; these were left out pending confirmation.
- [ ] The old "Shabad Guru" page reproduced material credited to a Harvard/edX course. It was not migrated; its subjects are covered by original theme pages, and `/shabadguru` redirects to the Shabad Guru theme.
