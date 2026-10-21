# Editorial guide

The platform's value depends on trust. These rules apply to everything published.

## The foundation

- **Gurmat is the frame.** Gurbani and the Sikh Gurus' teaching are the standard against which every other text is read. Other traditions are explored where they add insight, never treated as interchangeable with Gurbani.
- **Babaji's katha is Babaji's.** The site links recordings and videos; it never summarises or paraphrases what Babaji said, because no one has transcribed the recordings. "Babaji's katha on this" means "recordings whose titles or Angs show they concern this".
- **Never invent** a Gurbani line, Ang, author, historical claim, doctrinal position or attribution. If something is not known, say so ("unknown", "not recorded").
- **Make uncertainty visible.** Use `translation_note` for lines read in more than one way, `uncertainty` in text profiles, and `::: tension` blocks where Sikh opinion differs.

## Review workflow

Open `/review/` on the site. It shows:

1. **Sources**: the last automatic run of each.
2. **Gurbani checks**: every quoted line, whether BaniDB confirmed it, and whether it is shown. A failed line is hidden; correct its text or Ang in `content/gurbani.json`. Tick *Confirmed by hand* only after checking a printed saroop or trusted source (for example a line from a source BaniDB does not cover).
3. **Theme essays**: record a review (*reviewed* or *needs changes*) with the reviewer's name. Until then each page says "Awaiting review by a learned reader".
4. **Automatic theme links**: untick wrong links, tick *confirmed* for checked ones.
5. **Videos with no theme**: add a theme the title did not reveal.
6. **Imported items**: approve or reject feed and Facebook items.

Your choices build up a block of text at the bottom. Copy it, press *Open overrides.json on GitHub*, replace the file's contents with it, and commit. The site rebuilds within minutes.

**Who should review theme essays.** The essays were drafted with AI assistance and checked against the sources available, but theological interpretation and comparative claims need a reader learned in Gurmat and, for the comparisons, in the other tradition. Comparative notes and "where views differ" blocks deserve the closest reading.

## Writing and editing a theme

A theme is `content/themes/<slug>.md`: a JSON header, a line `---`, then sections `## discover`, `## understand`, `## reflect`, `## practise`.

- Quote Gurbani only with `[[gurbani:<id>]]` on a line of its own, after adding the line to `content/gurbani.json` with Gurmukhi, transliteration, translation, Granth, Ang, bani and author. A test fails the build if Gurbani appears loose in the prose.
- New lines you are not certain of: set `"confidence": "to-verify"`. They stay hidden until BaniDB confirms them.
- Comparisons: a block opening `::: compare <Tradition> | <Text or source>` and closing `:::`. State the connection, then the difference, and keep Gurmat as the frame. A test fails the build if the tradition or source is missing.
- Contested points: `::: tension <short title>` … `:::`.
- Write `**bold**`, `*italic*`, `[link](https://…)`, and lists with `- `.
- Keep the voice: plain, humble, exploratory; questions rather than instructions; no claims that spiritual practices are scientifically proven.
- After a substantive edit, set the essay's review status back to awaiting review.

## Matching rules

In each theme's header, `match.gurmukhi` terms match at the start of a word (`ਵਾਸ਼ਨਾ` matches ਵਾਸ਼ਨਾਵਾਂ); prefix a term with `=` to match the whole word only (`=ਮਨ` does not match ਮਨਮੁਖ). `match.roman` entries are regular expressions matched as whole words. `match.series` lists whole series. Keep rules specific: a false link costs more trust than a missing one.
