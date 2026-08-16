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


def synth(text, voice_id, out_path, model="eleven_multilingual_v2",
          stability=0.5, similarity=0.75, style=0.0, speed=1.0):
    task = _req("POST", "/v1/labs/task", {
        "input": text, "voice_id": voice_id, "model_id": model,
        "stability": stability, "similarity": similarity,
        "style": style, "speed": speed, "use_speaker_boost": True,
    })
    tid = task.get("task_id") or task.get("id")
    print(f"  task_id={tid}  ...generando", end="", flush=True)
    for _ in range(120):
        time.sleep(2)
        t = _req("GET", f"/v1/labs/task/{tid}")
        st = t.get("status")
        if st == "completed" and t.get("result"):
            url = t["result"]
            _download(url, out_path)
            print(f" OK -> {out_path}")
            return {"task_id": tid, "url": url, "path": out_path}
        if st in ("failed", "error"):
            print(" FALLO:", json.dumps(t)[:300]); return None
        print(".", end="", flush=True)
    print(" timeout"); return None


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
