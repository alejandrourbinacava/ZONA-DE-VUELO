#!/usr/bin/env python3
"""Sube un video a YouTube (API Data v3) usando OAuth de refresh token.
Pensado para correr en la nube (GitHub Actions). Secretos por entorno:
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
Uso: python scripts/upload_youtube.py <ruta.mp4> <ruta_metadata.json> [privacy]
privacy: public | private | unlisted  (por defecto public)"""
import os, sys, json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def creds():
    return Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )


def main():
    video = sys.argv[1]
    meta = json.load(open(sys.argv[2], encoding="utf-8")) if len(sys.argv) > 2 else {}
    privacy = sys.argv[3] if len(sys.argv) > 3 else "public"
    yt = build("youtube", "v3", credentials=creds())
    body = {
        "snippet": {
            "title": (meta.get("title") or "Zona de Vuelo")[:100],
            "description": meta.get("description", ""),
            "tags": meta.get("keywords", [])[:30],
            "categoryId": "27",  # Educación
            "defaultLanguage": "es",
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(video, chunksize=-1, resumable=True, mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"Subiendo... {int(status.progress()*100)}%")
    print(f"PUBLICADO: https://youtu.be/{resp['id']}")


if __name__ == "__main__":
    main()
