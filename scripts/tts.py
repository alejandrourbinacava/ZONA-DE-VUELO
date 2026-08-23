#!/usr/bin/env python3
"""Cliente TTS para GenAIPro (Labs / ElevenLabs). Genera, espera y descarga MP3."""
import os, sys, time, json, subprocess

API = os.environ.get("GENAIPRO_BASE", "https://genaipro.io/api")
KEY = os.environ["GENAIPRO_API_KEY"]
AUTH = f"Authorization: Bearer {KEY}"


def _req(method, path, body=None):
    # Usa curl por debajo (el almacen de CA de Python en esta maquina esta caducado)
    cmd = ["curl", "-s", "-X", method, API + path, "-H", AUTH]
    if body is not None:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(body)]
    out = subprocess.run(cmd, capture_output=True, encoding="utf-8",
                         errors="replace", timeout=90).stdout
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        print("Respuesta no-JSON:", out[:400], file=sys.stderr)
        raise


def _download(url, out_path):
    subprocess.run(["curl", "-s", "-L", url, "-o", out_path], check=True, timeout=120)


def _create_task(text, voice_id, model, stability, similarity, style, speed):
    """Crea la tarea TTS y devuelve su id, reintentando si la API no responde con id."""
    body = {"input": text, "voice_id": voice_id, "model_id": model,
            "stability": stability, "similarity": similarity,
            "style": style, "speed": speed, "use_speaker_boost": True}
    for intento in range(4):
        try:
            task = _req("POST", "/v1/labs/task", body)
        except Exception as e:
            print(f"  (POST fallo: {str(e)[:80]})", flush=True); task = {}
        tid = task.get("task_id") or task.get("id")
        if tid:
            return tid
        # sin id -> puede ser hipo transitorio del servicio; esperar y reintentar
        print(f"  (sin task_id, reintento {intento+1}/4)", flush=True)
        time.sleep(5)
    return None


def synth(text, voice_id, out_path, model="eleven_multilingual_v2",
          stability=0.5, similarity=0.75, style=0.0, speed=1.0):
    # hasta 3 intentos completos (crear tarea + esperar); TTS es el cuello de botella critico
    for ronda in range(3):
        tid = _create_task(text, voice_id, model, stability, similarity, style, speed)
        if not tid:
            print(f"  no se pudo crear la tarea (ronda {ronda+1}/3)", flush=True)
            time.sleep(8); continue
        print(f"  task_id={tid}  ...generando", end="", flush=True)
        for _ in range(255):   # hasta ~8.5 min por ronda (GenAIPro a veces va lento con secciones largas)
            time.sleep(2)
            try:
                t = _req("GET", f"/v1/labs/task/{tid}")
            except Exception:
                print("x", end="", flush=True); continue
            st = t.get("status")
            if st == "completed" and t.get("result"):
                url = t["result"]
                _download(url, out_path)
                if os.path.exists(out_path) and os.path.getsize(out_path) > 2000:
                    print(f" OK -> {out_path}")
                    return {"task_id": tid, "url": url, "path": out_path}
                print(" descarga vacia", flush=True); break
            if st in ("failed", "error"):
                print(" FALLO:", json.dumps(t)[:200], flush=True); break
            print(".", end="", flush=True)
        print(f"  (ronda {ronda+1}/3 sin exito, reintento)", flush=True)
        time.sleep(8)
    print("  TTS agotado tras 3 rondas"); return None


def subtitle(task_id, out_path, max_chars=32, max_lines=1, max_seconds=4.0):
    """Pide export de subtitulos y descarga el VTT. Devuelve la ruta local."""
    _req("POST", f"/v1/labs/task/subtitle/{task_id}", {
        "max_characters_per_line": max_chars,
        "max_lines_per_cue": max_lines,
        "max_seconds_per_cue": max_seconds,
    })
    for _ in range(60):
        t = _req("GET", f"/v1/labs/task/{task_id}")
        sub = t.get("subtitle")
        if sub and sub.startswith("http"):
            _download(sub, out_path)
            return out_path
        time.sleep(2)
    return None


if __name__ == "__main__":
    # args: text voice_id out_path [model]
    text, voice_id, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    model = sys.argv[4] if len(sys.argv) > 4 else "eleven_multilingual_v2"
    synth(text, voice_id, out_path, model=model)
