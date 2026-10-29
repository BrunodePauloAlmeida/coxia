"""Spotify OAuth helper for WSL2: local server with paste fallback."""

import http.server
import threading
import urllib.parse

import spotipy
from spotipy.oauth2 import SpotifyOAuth

REDIRECT_URI = "http://127.0.0.1:8888/callback"
_PORT = 8888
_TIMEOUT = 120


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    code: str | None = None
    error: str | None = None

    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _CallbackHandler.code = (params.get("code") or [None])[0]
        _CallbackHandler.error = (params.get("error") or [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<h2>Autorizado! Pode fechar esta aba.</h2>")

    def log_message(self, *_):
        pass


def _get_code_via_server(auth_url: str) -> str | None:
    """Start local server, wait for Spotify to redirect back. Returns code or None on timeout."""
    _CallbackHandler.code = None
    _CallbackHandler.error = None
    try:
        server = http.server.HTTPServer(("127.0.0.1", _PORT), _CallbackHandler)
    except OSError:
        return None  # port busy or unavailable

    server.timeout = _TIMEOUT
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    print(f"\nAbra esta URL no seu browser Windows:\n\n  {auth_url}\n")
    print(f"Aguardando autorização ({_TIMEOUT}s)...")

    thread.join(timeout=_TIMEOUT + 2)
    server.server_close()

    if _CallbackHandler.error:
        raise RuntimeError(f"Erro de autorização do Spotify: {_CallbackHandler.error}")
    return _CallbackHandler.code


def _get_code_via_paste(auth_url: str) -> str:
    """Fallback: user pastes the redirect URL after authorizing."""
    print(f"\nAbra esta URL no seu browser:\n\n  {auth_url}\n")
    print("Depois de autorizar, o browser vai tentar abrir http://127.0.0.1:8888/callback")
    print("A página não vai carregar — isso é normal.")
    print("Copie a URL COMPLETA da barra de endereço e cole aqui:\n")
    pasted = input("> ").strip()
    params = urllib.parse.parse_qs(urllib.parse.urlparse(pasted).query)
    code = (params.get("code") or [None])[0]
    if not code:
        raise RuntimeError("Não foi possível extrair o código da URL. Cole a URL completa.")
    return code


def get_spotify_client(scope: str) -> spotipy.Spotify:
    auth = SpotifyOAuth(
        scope=scope,
        redirect_uri=REDIRECT_URI,
        open_browser=False,
        cache_path=".cache",
    )

    # Use cached token if still valid
    cached = auth.validate_token(auth.cache_handler.get_cached_token())
    if cached:
        return spotipy.Spotify(auth_manager=auth)

    auth_url = auth.get_authorize_url()

    code = _get_code_via_server(auth_url)
    if not code:
        print("Servidor local não recebeu o callback. Mudando para modo manual...")
        code = _get_code_via_paste(auth_url)

    auth.get_access_token(code, as_dict=False, check_cache=False)
    return spotipy.Spotify(auth_manager=auth)
