# Harkhowal Online

The website for Sant Baba Jagjit Singh Ji Harkhowal Wale. It updates itself every day, with no editing needed:

- **Videos**: new uploads on Babaji's YouTube channel appear at the top of the site.
- **Audio katha**: new recordings added to Babaji's section on Gurmatveechar appear automatically, newest first. They play on the site in its own player, which remembers where each listener stopped.
- **Programmes** (optional): upcoming programmes listed in a Google Sheet appear in a small section. If the sheet is empty, the section stays hidden.

Hosting is free on GitHub Pages. The only running cost is the harkhowal.com domain renewal.

The daily update runs at about 05:17 UK time. To run it straight away, open the **Actions** tab, choose **Daily content update**, and click **Run workflow**.

---

## Point harkhowal.com at the site

1. In the repository, go to **Settings → Pages → Custom domain**, enter `www.harkhowal.com` and click **Save**. Tick **Enforce HTTPS** once it becomes available.
2. Where your domain is managed (Wix, if you bought it through Wix, or your registrar), change the DNS records:
   - `www` → **CNAME** → `gmw-collab.github.io`
   - `@` (the bare domain) → four **A** records: `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
3. DNS changes can take a few hours. Once the new site shows at harkhowal.com, you can cancel the Wix premium plan. Keep the domain itself.

## Add Babaji's programmes (optional)

1. Create a Google Sheet with these column headings in row 1: `Date`, `End date`, `Place`, `Title`, `Link`.
   Write dates like `2026-11-14` or `14/11/2026`. Only `Date` and either `Place` or `Title` are required.
2. In Google Sheets choose **File → Share → Publish to web**, pick the sheet, choose **Comma-separated values (.csv)**, and click **Publish**. Copy the link it gives you.
3. In this repository, open `config.json`, click the pencil icon, paste the link into `"programmes_csv_url"`, and commit.

From then on, anyone with edit access to the sheet can add a programme from their phone. It appears on the site the next morning, and disappears once the date has passed.

## Other settings in `config.json`

- **Social links**: fill in `"facebook"` or `"tiktok"` under `"social"`. They appear in the footer.
- **Series names in Gurmukhi**: `"series_gurmukhi"` maps each Gurmatveechar folder to the name shown on the site. Correct or add names here.
- **Grouping**: `"audio_categories"` decides which group each series appears under. Each group lists words to match in the folder name.

## About the audio

Recordings stream directly from Gurmatveechar.com, which hosts Babaji's katha. It's courteous to let them know harkhowal.com now plays the recordings in its own player, for example with a short email through their contact page. The site credits Gurmatveechar in the footer.

The update job checks Gurmatveechar once a day and pauses between requests, so it puts very little load on their server.

## If something looks wrong

- **The Actions tab shows a red cross:** open the run to see which source failed. One source failing never affects the others, and the site keeps the previous day's content.
- **GitHub pauses scheduled jobs** on repositories with no activity for 60 days. Because the job saves new content most days, this rarely happens. If it does, GitHub emails you; click **Enable workflow** in the Actions tab.
