#!/usr/bin/env python3
"""List all Spotify playlists and save to a text file."""

from pathlib import Path

from dotenv import load_dotenv

from auth import get_spotify_client

load_dotenv()

sp = get_spotify_client("playlist-read-private playlist-read-collaborative")

me = sp.me()
print(f"Logged in as: {me['display_name']} ({me['id']})\n")

playlists = []
result = sp.current_user_playlists(limit=50)
while result:
    for item in result["items"]:
        owner = item["owner"]["display_name"] or item["owner"]["id"]
        tracks = (item.get("tracks") or {}).get("total", "?")
        playlists.append((item["name"], owner, tracks))
    result = sp.next(result) if result["next"] else None

playlists.sort(key=lambda x: x[0].lower())

output = Path("playlists.txt")
lines = [f"{name}  [{tracks} faixas]  — criada por: {owner}" for name, owner, tracks in playlists]
output.write_text("\n".join(lines), encoding="utf-8")

print(f"{len(playlists)} playlists encontradas. Salvo em {output.resolve()}\n")
for line in lines:
    print(line)
