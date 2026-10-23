#!/usr/bin/env python3
"""Sube un video a YouTube (API Data v3) con OAuth de refresh token + pone la MINIATURA.
Pensado para correr en la nube (GitHub Actions). Secretos por entorno:
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
Uso: python scripts/upload_youtube.py <ruta.mp4> <ruta_metadata.json> [privacy] [miniatura.jpg]
privacy: public | private | unlisted | schedule (por defecto public). 'schedule' = privado + publishAt
  a las 18:30 de Madrid (PUBLISH_TIME para cambiarlo)

AVISO: los proyectos de Google Cloud creados tras jul-2020 y SIN auditar fuerzan los videos subidos por API a
PRIVADO. Este script lo detecta (compara la visibilidad devuelta con la pedida) y lo dice claramente."""
import os, sys, json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]


def creds():
    return Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )


def next_publish_utc(hhmm=None, tz="Europe/Madrid"):
    """Proxima hora 'hhmm' (por defecto 18:30) en hora de Madrid -> ISO UTC para publishAt. Respeta el cambio horario.
    Si faltan menos de 15 min (o ya paso), se programa para el dia siguiente."""
    hhmm = hhmm or os.environ.get("PUBLISH_TIME", "18:30")
    z = ZoneInfo(tz); now = datetime.now(z)
    h, m = [int(x) for x in hhmm.split(":")]
    t = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if t <= now + timedelta(minutes=15):
        t += timedelta(days=1)
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"), t.strftime("%d/%m/%Y %H:%M (%Z)")


def main():
    video = sys.argv[1]
    meta = json.load(open(sys.argv[2], encoding="utf-8")) if len(sys.argv) > 2 and sys.argv[2] else {}
    privacy = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else "public"
    thumb = sys.argv[4] if len(sys.argv) > 4 else ""
    yt = build("youtube", "v3", credentials=creds())
    body = {
        "snippet": {
            "title": (meta.get("title") or "Zona de Vuelo")[:100],
            "description": meta.get("description", ""),
            "tags": meta.get("keywords", [])[:30],
            "categoryId": "27",  # Educación
            "defaultLanguage": "es",
            "defaultAudioLanguage": "es",
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    when = None
    if privacy == "schedule":
        iso, when = next_publish_utc()
        # YouTube exige privacyStatus=private + publishAt (futuro): el video se publica SOLO a esa hora
        body["status"].update({"privacyStatus": "private", "publishAt": iso})
        print(f"PROGRAMADO para publicarse el {when}")
    media = MediaFileUpload(video, chunksize=-1, resumable=True, mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"Subiendo... {int(status.progress()*100)}%")
    vid = resp["id"]
    got = (resp.get("status") or {}).get("privacyStatus")
    pub = (resp.get("status") or {}).get("publishAt")
    print(f"SUBIDO: https://youtu.be/{vid}  (visibilidad: {got}" + (f", publicacion programada: {pub}" if pub else "") + ")")
    print(f"YTID::{vid}")
    if privacy == "schedule":
        if not pub:
            print("::warning::YouTube NO guardo la hora de publicacion (publishAt): el video se queda PRIVADO. "
                  "Posible bloqueo por proyecto de Google Cloud sin auditar.")
        else:
            print(f"Se publicara solo el {when}.")
    elif got and got != privacy:
        print(f"::warning::YouTube dejo el video en '{got}' aunque se pidio '{privacy}'. Si es 'private', el proyecto de "
              f"Google Cloud esta SIN AUDITAR y YouTube bloquea las subidas por API en privado.")

    if thumb and os.path.exists(thumb):
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(thumb, mimetype="image/jpeg")).execute()
            print("MINIATURA puesta:", thumb)
        except HttpError as e:
            # p.ej. canal sin verificar por telefono (no permite miniaturas personalizadas)
            print(f"::warning::No se pudo poner la miniatura: {str(e)[:200]}")
    elif thumb:
        print("::warning::miniatura indicada pero no existe:", thumb)


if __name__ == "__main__":
    main()
