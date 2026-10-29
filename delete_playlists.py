#!/usr/bin/env python3
"""Unfollow/delete all playlists from the authenticated Spotify account."""

from dotenv import load_dotenv

from auth import get_spotify_client

load_dotenv()

sp = get_spotify_client("playlist-read-private playlist-modify-private playlist-modify-public")

me = sp.me()
user_id = me["id"]
print(f"Logged in as: {me['display_name']} ({user_id})\n")

# Fetch all playlists
playlists = []
result = sp.current_user_playlists(limit=50)
while result:
    playlists.extend(result["items"])
    result = sp.next(result) if result["next"] else None

print(f"{len(playlists)} playlists encontradas:\n")
for p in playlists:
    owner = p["owner"]["id"]
    tag = "sua" if owner == user_id else f"seguida — de {p['owner']['display_name'] or owner}"
    print(f"  {p['name'] or '(sem nome)'}  [{tag}]")

print(f"\nIsso vai remover TODAS as {len(playlists)} playlists da sua conta.")
print("Playlists suas serão deletadas. Playlists de outros serão desseguidas.")
confirm = input("\nDigite 'sim' para confirmar: ").strip().lower()

if confirm != "sim":
    print("Cancelado.")
    exit(0)

print()
for p in playlists:
    name = p["name"] or "(sem nome)"
    try:
        sp.current_user_unfollow_playlist(p["id"])
        print(f"  Removida: {name}")
    except Exception as e:
        print(f"  Erro em '{name}': {e}")

print("\nConcluído.")
