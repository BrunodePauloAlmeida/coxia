# spotify-playlist-creator

Turn the setlists couples send to wedding musicians into Spotify playlists.

I play at weddings. Before every event the couple sends a setlist, usually a Word file, a PDF or a WhatsApp message, written in whatever format they like: numbered lists, "moment: song - artist (key)", notes for the band mixed in. I need those songs in a Spotify playlist to rehearse. This tool reads the file, works out which lines are songs, finds them on Spotify and creates the playlist, or updates it when the couple changes the list.

## How it works

1. **Extract text** from a PDF (PyMuPDF), DOCX (python-docx) or TXT file.
2. **Find the songs** with Gemini, which returns title and original artist for each one and ignores headers, keys and notes for the band.
3. **Search Spotify** for each song, first by title and artist, then by title only.
4. **Create or sync the playlist.** If a playlist with the same name already exists, it shows which songs will be added or removed and fixes the order. Nothing changes until you confirm.

The playlist name comes from the date in the file name: `2030_05_18.txt` becomes `Casamento 2030-05-18`. You can also pass a name explicitly.

## Built with

Python 3.13, [uv](https://docs.astral.sh/uv/), [spotipy](https://spotipy.readthedocs.io/), [google-genai](https://pypi.org/project/google-genai/) (Gemini), PyMuPDF and python-docx.

## Setup

1. **Spotify app.** Create an app at the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and add `http://127.0.0.1:8888/callback` as a Redirect URI. Spotify requires the app owner to have Premium, and apps in Development Mode can only be used by accounts you add in the dashboard.
2. **Gemini key.** Get one at [Google AI Studio](https://aistudio.google.com/apikey).
3. **Configure and install:**

   ```bash
   cp .env.example .env   # then fill in the keys
   uv sync
   ```

## Usage

```bash
uv run main.py examples/2030_05_18.txt
uv run main.py examples/2030_05_18_recepcao.txt "Casamento 2030-05-18 Recepção"
```

The first run prints a Spotify authorization URL. Open it in your browser; the tool catches the redirect on port 8888. On WSL, where the callback sometimes doesn't reach the local server, it falls back to asking you to paste the redirect URL. The token is cached in `.cache`.

Helper scripts:

- `list_playlists.py` saves all your playlists to `playlists.txt`.
- `delete_playlists.py` removes **every** playlist from your account (your own are deleted, others are unfollowed). It asks for confirmation, but use it with care.

## Privacy

Real setlists include the couple's names, the date and the venue. Keep them in `roteiros/`, which is ignored by git, and never commit them. The files in `examples/` are made up.

## Roadmap

See [ROADMAP.md](ROADMAP.md): a public web version, smarter song matching with confidence levels, and a setlist sheet for the band.

## License

[MIT](LICENSE)
