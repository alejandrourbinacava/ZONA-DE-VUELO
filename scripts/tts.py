#!/usr/bin/env python3
"""Cliente TTS para ai33.pro (endpoint unificado v3). Genera, espera y descarga MP3.
Voz oficial: Gabriel Blanco (ElevenLabs) -> voice_id 'elevenlabs_4R9s73RrCF4wi6GqmzrT'.
Flujo: POST /v3/text-to-speech (FormData) -> task_id -> GET /v3/task/{id} -> data.metadata.data.audio_url."""
import os, sys, time, json, subprocess, tempfile

API = os.environ.get("AI33_BASE", "https://api.ai33.pro")
KEY = os.environ.get("AI33_API_KEY") or os.environ.get("GENAIPRO_API_KEY")
HDR = f"xi-api-key: {KEY}"
PREFIXES = ("elevenlabs_", "minimax_", "clone_", "edge_", "kokoro_", "vbee_", "fishaudio_")


def _get(path):
    # curl por debajo (el almacen de CA de Python en esta maquina esta caducado)
    out = subprocess.run(["curl", "-s", API + path, "-H", HDR],
                         capture_output=True, encoding="utf-8", errors="replace", timeout=90).stdout
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        print("Respuesta no-JSON:", out[:300], file=sys.stderr)
        return {}


def _download(url, out_path):
    # --max-time hace que curl aborte solo; el try/except evita que una descarga lenta tumbe la voz
    try:
        subprocess.run(["curl", "-s", "-L", "--max-time", "150", "--connect-timeout", "20", url, "-o", out_path],
                       timeout=170)
    except subprocess.TimeoutExpired:
        try: os.remove(out_path)
        except OSError: pass
        return False
    return os.path.exists(out_path) and os.path.getsize(out_path) > 2000


def _create_task(text, voice_id, speed, stability, similarity, style):
    """Crea la tarea TTS (FormData) y devuelve su task_id, reintentando si no hay id.
    El texto se pasa desde un fichero para preservar acentos, comillas y saltos de linea.
    Ajustes expresivos (menos monotona): stability baja + style alto."""
    tf = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    tf.write(text); tf.close(); tpath = tf.name
    try:
        for intento in range(4):
            out = subprocess.run(
                ["curl", "-s", "-X", "POST", API + "/v3/text-to-speech", "-H", HDR,
                 "-F", f"text=<{tpath}",
                 "-F", f"voice_id={voice_id}",
                 "-F", f"speed={speed}",
                 "-F", f"stability={stability}",
                 "-F", f"similarity={similarity}",
                 "-F", f"style={style}"],
                capture_output=True, encoding="utf-8", errors="replace", timeout=90).stdout
            try:
                d = json.loads(out)
            except json.JSONDecodeError:
                d = {}
            tid = d.get("task_id")
            if tid:
                return tid
            print(f"  (sin task_id, reintento {intento+1}/4): {out[:120]}", flush=True)
            time.sleep(5)
    finally:
        try:
            os.remove(tpath)
        except OSError:
            pass
    return None


# ---------- PROVEEDOR GenAIPro (VOICE_PROVIDER=genaipro): API Labs estilo ElevenLabs ----------
GP_API = os.environ.get("GENAIPRO_BASE", "https://genaipro.io/api")
GP_KEY = os.environ.get("GENAIPRO_API_KEY", "")
GP_AUTH = f"Authorization: Bearer {GP_KEY}"


def _gp_req(method, path, body=None):
    cmd = ["curl", "-s", "--max-time", "60", "-X", method, GP_API + path, "-H", GP_AUTH]
    tf = None
    if body is not None:
        # cuerpo por fichero: preserva acentos/saltos de linea del guion en Windows
        tf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(body, tf); tf.close()
        cmd += ["-H", "Content-Type: application/json", "--data-binary", "@" + tf.name]
    try:
        out = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=75).stdout
    except subprocess.TimeoutExpired:
        return {}
    finally:
        if tf:
            try: os.remove(tf.name)
            except OSError: pass
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        print("Respuesta no-JSON (GenAIPro):", out[:200], file=sys.stderr)
        return {}


def gp_balance():
    """Saldo de la cuenta GenAIPro (GET /v2/me). None si falla."""
    return _gp_req("GET", "/v2/me").get("balance")


def _synth_genaipro(text, voice_id, out_path, model, stability, similarity, style, speed):
    voice_id = voice_id.split("_", 1)[1] if voice_id.startswith(PREFIXES) else voice_id   # GenAIPro: id sin prefijo
    bal = gp_balance()
    if bal is not None and bal < len(text):
        print(f"  ! saldo GenAIPro insuficiente ({bal} < {len(text)} caracteres). Recarga en genaipro.io", file=sys.stderr)
        return None
    body = {"input": text, "voice_id": voice_id, "model_id": model, "stability": stability,
            "similarity": similarity, "style": style, "speed": speed, "use_speaker_boost": True}
    for ronda in range(3):
        tid = None
        for intento in range(4):
            t = _gp_req("POST", "/v1/labs/task", body)
            tid = t.get("task_id") or t.get("id")
            if tid:
                break
            print(f"  (sin task_id, reintento {intento+1}/4): {json.dumps(t)[:120]}", flush=True)
            time.sleep(5)
        if not tid:
            time.sleep(8); continue
        print(f"  task_id={tid}  ...generando", end="", flush=True)
        for _ in range(255):   # ~8.5 min por ronda
            time.sleep(2)
            t = _gp_req("GET", f"/v1/labs/task/{tid}")
            st = t.get("status")
            if st == "completed" and t.get("result"):
                for _dl in range(3):
                    if _download(t["result"], out_path):
                        print(f" OK -> {out_path}")
                        return {"task_id": tid, "url": t["result"], "path": out_path}
                    time.sleep(4)
                break
            if st in ("failed", "error"):
                print(" FALLO:", json.dumps(t)[:200], flush=True); break
            print(".", end="", flush=True)
        print(f"  (ronda {ronda+1}/3 sin exito, reintento)", flush=True)
        time.sleep(8)
    print("  TTS GenAIPro agotado tras 3 rondas"); return None


def synth(text, voice_id, out_path, model="eleven_multilingual_v2",
          stability=0.5, similarity=0.75, style=0.0, speed=1.0):
    if os.environ.get("VOICE_PROVIDER", "ai33").lower() == "genaipro":
        return _synth_genaipro(text, voice_id, out_path, model, stability, similarity, style, speed)
    # el voice_id de ai33 v3 requiere prefijo de proveedor; lo garantizamos
    if not voice_id.startswith(PREFIXES):
        voice_id = "elevenlabs_" + voice_id
    for ronda in range(3):
        tid = _create_task(text, voice_id, speed, stability, similarity, style)
        if not tid:
            print(f"  no se pudo crear la tarea (ronda {ronda+1}/3)", flush=True)
            time.sleep(8); continue
        print(f"  task_id={tid}  ...generando", end="", flush=True)
        for _ in range(180):   # ~6 min de margen (ai33 suele tardar segundos)
            time.sleep(2)
            t = _get(f"/v3/task/{tid}")
            d = t.get("data") or {}
            st = d.get("status")
            if st == "done":
                # la audio_url esta en data.metadata.audio_url; puede tardar un instante en poblarse
                url = (d.get("metadata") or {}).get("audio_url")
                for _try in range(6):
                    if url:
                        break
                    time.sleep(2)
                    d = _get(f"/v3/task/{tid}").get("data") or {}
                    url = (d.get("metadata") or {}).get("audio_url")
                if url:
                    for _dl in range(3):   # la descarga puede colgarse si ai33 va lento: reintenta
                        if _download(url, out_path):
                            print(f" OK -> {out_path}")
                            return {"task_id": tid, "url": url, "path": out_path}
                        print(" (descarga lenta, reintento)", end="", flush=True)
                        time.sleep(4)
                print(" done sin audio_url", flush=True); break
            if st in ("failed", "error"):
                print(" FALLO:", json.dumps(t)[:200], flush=True); break
            print(".", end="", flush=True)
        print(f"  (ronda {ronda+1}/3 sin exito, reintento)", flush=True)
        time.sleep(8)
    print("  TTS agotado tras 3 rondas"); return None


if __name__ == "__main__":
    # args: text voice_id out_path
    text, voice_id, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    synth(text, voice_id, out_path)
