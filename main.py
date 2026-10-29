#!/usr/bin/env python3
"""Create a Spotify playlist from a PDF or DOCX file containing a song list."""

import json
import os
import re
import sys
from pathlib import Path

import fitz  # pymupdf
import spotipy
from docx import Document
from dotenv import load_dotenv
from google import genai

from auth import get_spotify_client

load_dotenv()

GEMINI_MODEL = "gemini-3.5-flash"


def extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        doc = fitz.open(file_path)
        return "\n".join(page.get_text() for page in doc)
    elif suffix in (".docx", ".doc"):
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    elif suffix == ".txt":
        return file_path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {suffix}. Use PDF, DOCX or TXT.")


def derive_playlist_name(file_path: Path) -> str:
    stem = file_path.stem
    match = re.search(r"(\d{4})_(\d{2})_(\d{2})", stem)
    if match:
        year, month, day = match.groups()
        return f"Casamento {year}-{month}-{day}"
    return stem


def parse_songs_with_gemini(raw_text: str) -> list[dict]:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    prompt = f"""You will receive raw text extracted from a document containing a list of songs.
Your job is to identify all songs mentioned and return them as a JSON array.

For each song, return an object with:
- "title": the song title
- "artist": the original artist or composer (not a cover artist)

Rules:
- Ignore any text that is not a song (headers, descriptions, notes, etc.)
- If the artist is ambiguous, use the most famous/original version
- Return ONLY a valid JSON array, no markdown, no explanation

Text:
{raw_text}"""

    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    response_text = response.text.strip()
    response_text = re.sub(r"^```(?:json)?\s*", "", response_text)
    response_text = re.sub(r"\s*```$", "", response_text)

    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"Gemini returned invalid JSON: {e}")
        print("Raw response:", response_text[:500])
        sys.exit(1)


def search_track(sp: spotipy.Spotify, title: str, artist: str) -> dict | None:
    """Returns {"uri", "name", "artist"} or None."""
    for query in [f"track:{title} artist:{artist}", f"track:{title}"]:
        results = sp.search(q=query, type="track", limit=1)
        items = results["tracks"]["items"]
        if items:
            track = items[0]
            label = "Found" if "artist:" in query else "Fallback"
            print(f"  {label}: {track['name']} — {track['artists'][0]['name']}")
            return {"uri": track["uri"], "name": track["name"], "artist": track["artists"][0]["name"]}

    print(f"  Not found: {title} — {artist}")
    return None


def find_playlist_by_name(sp: spotipy.Spotify, name: str) -> dict | None:
    result = sp.current_user_playlists(limit=50)
    while result:
        for p in result["items"]:
            if p["name"] == name:
                return p
        result = sp.next(result) if result["next"] else None
    return None


def get_playlist_tracks(sp: spotipy.Spotify, playlist_id: str) -> list[dict]:
    """Returns list of {"uri", "name", "artist"} for all tracks in the playlist."""
    tracks = []
    result = sp.playlist_items(playlist_id, limit=100)
    while result:
        for item in result["items"]:
            t = item.get("track")
            if t and t.get("uri"):
                tracks.append({
                    "uri": t["uri"],
                    "name": t["name"],
                    "artist": t["artists"][0]["name"] if t.get("artists") else "?",
                })
        result = sp.next(result) if result["next"] else None
    return tracks


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run main.py <file.pdf|file.docx|file.txt> [playlist name]")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    playlist_name = sys.argv[2] if len(sys.argv) > 2 else derive_playlist_name(file_path)

    print(f"Extracting text from {file_path.name}...")
    raw_text = extract_text(file_path)
    print(f"  {len(raw_text)} characters extracted.\n")

    print("Asking Gemini to identify songs...")
    songs = parse_songs_with_gemini(raw_text)
    print(f"  {len(songs)} songs identified:\n")
    for s in songs:
        print(f"  - {s['title']} — {s['artist']}")

    print("\nAuthenticating with Spotify...")
    sp = get_spotify_client("playlist-modify-private playlist-modify-public")
    print(f"  Logged in as: {sp.me()['display_name']}\n")

    print("Searching for tracks on Spotify...")
    found_tracks = []
    not_found = []
    for song in songs:
        result = search_track(sp, song["title"], song["artist"])
        if result:
            found_tracks.append(result)
        else:
            not_found.append(song)

    print(f"\n{len(found_tracks)}/{len(songs)} tracks found.")

    if not found_tracks:
        print("No tracks found. Aborting.")
        sys.exit(1)

    if not_found:
        print(f"\nNot found on Spotify ({len(not_found)}):")
        for s in not_found:
            print(f"  - {s['title']} — {s['artist']}")

    # Check if playlist already exists
    existing = find_playlist_by_name(sp, playlist_name)

    if existing:
        playlist_id = existing["id"]
        playlist_url = existing["external_urls"]["spotify"]
        print(f"\nPlaylist '{playlist_name}' já existe. Comparando músicas...")

        current_tracks = get_playlist_tracks(sp, playlist_id)
        current_uris = {t["uri"] for t in current_tracks}
        file_uris = [t["uri"] for t in found_tracks]

        to_add = [t for t in found_tracks if t["uri"] not in current_uris]
        to_remove = [t for t in current_tracks if t["uri"] not in set(file_uris)]

        # Detect order mismatch among tracks present in both sides
        current_ordered = [t["uri"] for t in current_tracks if t["uri"] in set(file_uris)]
        file_ordered = [uri for uri in file_uris if uri in current_uris]
        order_changed = current_ordered != file_ordered

        if not to_add and not to_remove and not order_changed:
            print("  Playlist já está sincronizada, nada a fazer.")
            sys.exit(0)

        if to_add:
            print(f"\n  {len(to_add)} música(s) para adicionar:")
            for t in to_add:
                print(f"    + {t['name']} — {t['artist']}")

        if to_remove:
            print(f"\n  {len(to_remove)} música(s) para remover (não estão no arquivo):")
            for t in to_remove:
                print(f"    - {t['name']} — {t['artist']}")

        if order_changed and not to_add and not to_remove:
            print(f"\n  Ordem será ajustada para corresponder ao arquivo.")

        confirm = input(f"\nAplicar alterações na playlist '{playlist_name}'? [s/N] ").strip().lower()
        if confirm != "s":
            print("Abortado.")
            sys.exit(0)

        # Clear all tracks then re-add in file order to guarantee correct ordering
        all_current_uris = [t["uri"] for t in current_tracks]
        for i in range(0, len(all_current_uris), 100):
            sp.playlist_remove_all_occurrences_of_items(playlist_id, all_current_uris[i:i+100])

        for i in range(0, len(found_tracks), 100):
            sp.playlist_add_items(playlist_id, [t["uri"] for t in found_tracks[i:i+100]])

        print(f"  Playlist atualizada: {len(found_tracks)} música(s), na ordem do arquivo.")

    else:
        confirm = input(f"\nCriar playlist '{playlist_name}' com {len(found_tracks)} músicas? [s/N] ").strip().lower()
        if confirm != "s":
            print("Abortado.")
            sys.exit(0)

        print(f"\nCriando playlist '{playlist_name}'...")
        playlist = sp._post(
            "me/playlists",
            payload={
                "name": playlist_name,
                "public": False,
                "description": "Created automatically from document by spotify-playlist-creator",
            },
        )
        playlist_id = playlist["id"]
        playlist_url = playlist["external_urls"]["spotify"]

        for i in range(0, len(found_tracks), 100):
            sp.playlist_add_items(playlist_id, [t["uri"] for t in found_tracks[i:i+100]])

    print(f"\nPronto! Abra aqui:\n{playlist_url}")


if __name__ == "__main__":
    main()
