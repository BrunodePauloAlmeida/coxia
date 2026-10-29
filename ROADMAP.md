# Roadmap

**Where this is going:** paste or upload the messy setlist a couple sent (Word, PDF, WhatsApp text, even a screenshot) and get back two things: a Spotify playlist with the right recordings, and a clean setlist sheet for the band. The tool should only ask a human when it is genuinely unsure, and then offer two or three options instead of guessing.

## Constraints that shape this plan (October 2026)

- **Spotify Development Mode** allows at most 5 authorized users per app, and the app owner needs Premium. Extended quota is only granted to organizations with 250k+ monthly active users, so a single hosted app can't serve the public.
- **Search** returns at most 10 results per call, and dev-mode apps no longer receive track `popularity` or artist `genres`. "Prefer the famous version" and "prefer the religious version" need other signals.
- **Playlist rows** moved from `track` to `item`, and the old key is now a boolean.
- **Privacy:** setlists carry the couple's names, the date and the venue. The tool should never store setlists or Spotify tokens on a server I control.

## Phase 0: Solid foundations for the CLI

- [ ] **Bug:** syncing an existing playlist reads `row["track"]`, which is now a boolean. Read `row["item"]`.
- [ ] **Bug:** `.doc` files are accepted, but python-docx only reads `.docx`. Convert with LibreOffice or reject them with a clear message.
- [ ] **Bug:** `2030_05_18.txt` and `2030_05_18_recepcao.txt` both map to `Casamento 2030-05-18`, so the second run overwrites the first playlist. Keep the suffix in the name.
- [ ] Replace the private `sp._post("me/playlists")` with `current_user_playlist_create`.
- [ ] Sync with `playlist_replace_items` instead of removing every track and adding them back.
- [ ] Use Gemini structured output (`response_schema`) instead of stripping Markdown fences with regex.
- [ ] Split the code into `parse → resolve → sync` modules behind a real CLI with `--dry-run`, `--name` and `--yes`.
- [ ] Add pytest tests with Spotify and Gemini mocked, plus GitHub Actions running ruff and pytest.
- [ ] Make it installable with `uv tool install`.

## Phase 1: Understand the setlist, not just the song names

Each entry becomes structured data: title, artist (optional), section (processional, ceremony, reception), moment ("bride's entrance"), version hint (original, instrumental, live, acoustic), key (`RÉ MAIOR` → `D`, `Gm`), performer (band member) and notes.

- [ ] **Band roster:** know that names like "Alan" or "Letícia" are the band's singers, not the song's artist.
- [ ] **Deterministic parser first** for the common formats (`N- Title - Key`, `Moment: Title - Artist (Key)`). Call the LLM only when the heuristics fail. This makes the tool cheaper, lets it work offline, and keeps simple lists on your machine.
- [ ] **Image input:** WhatsApp screenshots and photos of handwritten lists, read by a multimodal model.
- [ ] **Ceremony templates** (Catholic, evangelical, civil) that map entries to standard moments and flag missing ones, like "no song for the recessional".

## Phase 2: Pick the right recording

**Candidate generation**

- [ ] Run several queries per song: title + artist, title only, accent-free, and alternate titles. Merge the results and drop duplicates.

**Scoring.** Every candidate gets a score and human-readable reasons.

- [ ] Title and artist similarity, ignoring case and accents and suffixes like "Ao Vivo", "Remastered" or "feat.".
- [ ] Version penalties for karaoke, covers and tributes, playback, 8D, sped up or slowed, and remixes, unless the setlist asks for one. Boost instrumental, piano and strings versions when the hint says instrumental, and the original artist when it says original.
- [ ] Popularity from an outside source, since Spotify no longer returns it. Candidates to evaluate: Deezer `rank`, Last.fm listeners, ListenBrainz popularity.
- [ ] Context preference. In ceremony sections, prefer religious recordings, based on artist tags from Last.fm or MusicBrainz, a cached classification and artists I've used before. At the reception, prefer the most popular version.
- [ ] Personal memory: once I pick a recording for a song, reuse it next time.

**Confidence and asking the user**

- [ ] Combine the top score and its margin over the runner-up into a high, medium or low confidence level.
- [ ] High confidence is added automatically. Medium and low show the top 2–3 options with the reasons and a Spotify embed to listen, plus "search manually" and "skip".
- [ ] Matching regression tests: made-up setlists, and song-only extracts of real ones (no names), each with its expected tracks. Track the share resolved automatically, the share of automatic picks I later changed, and the number of questions per setlist. CI runs them so changes to the scoring can't quietly make matching worse.

## Phase 3: Public web app

Anyone can paste or upload a setlist, sign in with Spotify, review the uncertain picks and get the playlist.

Because of the 5-user limit:

- [ ] The app runs in the browser as a static site. Spotify login uses Authorization Code with PKCE, so there's no client secret and no backend.
- [ ] **Bring your own Spotify app:** a guided 5-minute setup to create a free Spotify developer app and paste its Client ID. The hosted instance with my own Client ID serves me and my band.
- [ ] No server-side storage. Tokens and personal memory stay in the browser and can be exported and imported as JSON.
- [ ] LLM parsing is optional and uses the user's own key. The deterministic parser is the default.
- [ ] **Review screen:** a confidence color for each song, a choice between options, drag to reorder, rename, and public or private.
- [ ] **Update flow:** when the couple changes the list, show the diff before applying it.
- [ ] Portuguese and English UI, mobile first, since most setlists arrive by WhatsApp on a phone.

**Open decision:** port the core to TypeScript (one codebase for web and CLI), run the Python core in the browser with Pyodide, or keep Python behind a small stateless API.

## Phase 4: Beyond the playlist, for musicians

- [ ] **Band setlist sheet** (PDF, printable or shareable): moment, song, key, singer, duration, notes and a chords link (Cifra Club search).
- [ ] **Repertoire:** the songs the band knows, with the usual key and singer. Flag new songs to rehearse, and show stats from past weddings like "played 6 times, always in G".
- [ ] **Timing:** duration per section and in total, with warnings like "processional songs add up to 9 minutes".
- [ ] **Suggestions** for empty moments, based on what I've played before.
- [ ] **Rehearsal links:** YouTube searches for instrumental and acoustic versions.
- [ ] One playlist per section, or one playlist that lists the moments in its description.
- [ ] Export to other services or CSV (YouTube Music, Apple Music, playlist-transfer tools).

## Ideas parking lot

- Telegram bot: forward the couple's message, get the playlist and the band sheet back.
- A form where couples choose songs per moment. It would collect personal data, so it needs a privacy design first and must not store names.
