# Harkhowal Online

The website of Sant Baba Jagjit Singh Ji Harkhowal Wale and Dera Sant Ghar, Harkhowal: a Gurmat-centred knowledge platform built around Babaji's katha.

It does four things:

1. **Keeps Babaji's katha in one place and up to date by itself.** Every day it collects new videos from Babaji's YouTube channel and new recordings from Babaji's folder on Gurmatveechar.com (2,333 recordings in 37 series today), and publishes them. Nobody has to edit anything.
2. **Lists everything newest first.** The Latest page shows every recording and video in the order it arrived, with a simple filter for audio, video and words in the title.
3. **Opens Gurmat through themes.** Eleven themes drawn from what Babaji actually teaches (Haumai, Hukam, Naam, Shabad Guru, Seva, Maya, the mind, Gian, Bhagti, Rahini, Mukti), each moving from a first introduction through Gurbani and Babaji's katha to reflection. Every Gurbani line shown is linked to Babaji's katha of that very Ang.
4. **Is honest about where every word comes from.** Gurbani, Babaji's katha, editorial writing and other people's material are labelled on every page. Gurbani quotations are checked against BaniDB automatically. AI-assisted writing is marked as such and waits for review by a learned reader.

It costs nothing to run beyond the domain name. It is a set of plain web pages, built by a short Python program and hosted free on Cloudflare, which rebuilds and publishes it whenever the repository changes.

## Where things are

| You want to… | Go to |
|---|---|
| See how the site works and what it is connected to | the **Sources** page on the site, or [docs/SOURCES.md](docs/SOURCES.md) |
| Review theme links, Gurbani checks and essays | the **/review/** page on the site (not listed in search engines); see [docs/EDITORIAL.md](docs/EDITORIAL.md) |
| Edit a theme essay or the About page | `content/themes/*.md`, `content/pages/about.md` |
| Add or correct a Gurbani line | `content/gurbani.json` |
| Describe a text Babaji has taught | `content/texts.json` |
| Add programmes, social links, a new feed | `config.json` |
| Publish the site, connect harkhowal.com | [docs/OPERATIONS.md](docs/OPERATIONS.md) |
| Understand the design and the code | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| See what was audited, tested and is planned | [docs/AUDIT.md](docs/AUDIT.md), [docs/TESTING.md](docs/TESTING.md), [docs/ROADMAP.md](docs/ROADMAP.md) |

Any file can be edited on GitHub in the browser: open it, click the pencil, change it, and commit. The site rebuilds itself within a few minutes.

## Running it on your own computer

You need Python 3.10 or newer; nothing else to install.

```
python scripts/update.py      # optional: fetch new material (needs internet)
python scripts/build.py       # build the site into _site/
python -m http.server -d _site 8000   # then open http://localhost:8000
python -m unittest discover -s tests -p "test_*.py"   # tests
```

## Credits

Audio is hosted by Gurmatveechar.com. Gurbani text is checked with BaniDB (Khalis Foundation). This repository began as an import of `GMW-collab/harkhowal-site`.
