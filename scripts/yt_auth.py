#!/usr/bin/env python3
"""AUTORIZACION UNICA (en local): da permiso al canal y guarda YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN
como secretos de GitHub Actions (cifrados). NO imprime ningun secreto.
Uso: python scripts/yt_auth.py ruta/client_secret.json
  (el JSON se descarga de Google Cloud Console -> APIs y servicios -> Credenciales -> ID de cliente OAuth "Aplicacion de escritorio")
Se abre el navegador: inicia sesion TU con la cuenta del canal y acepta los permisos."""
import os, sys, subprocess
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]


def load_env():
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for ln in open(p, encoding="utf-8"):
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, _, v = ln.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    load_env()
    flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline",
                                  authorization_prompt_message="Abriendo el navegador para autorizar el canal...")
    if not creds.refresh_token:
        print("Google no devolvio refresh_token. Revoca el acceso previo en https://myaccount.google.com/permissions y repite.")
        sys.exit(1)
    yt = build("youtube", "v3", credentials=creds)
    ch = yt.channels().list(part="snippet", mine=True).execute().get("items", [])
    print("Canal autorizado:", ch[0]["snippet"]["title"] if ch else "(no se pudo leer el canal)")
    cfg = flow.client_config
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    sys.argv = ["gh_secrets.py", f"YT_CLIENT_ID={cfg['client_id']}", f"YT_CLIENT_SECRET={cfg['client_secret']}",
                f"YT_REFRESH_TOKEN={creds.refresh_token}"]
    import gh_secrets
    gh_secrets.main()
    print("Secretos guardados en GitHub (YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN).")


if __name__ == "__main__":
    main()
