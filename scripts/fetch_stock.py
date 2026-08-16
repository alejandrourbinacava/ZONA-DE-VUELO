#!/usr/bin/env python3
"""Descarga B-roll de Pexels usando las palabras clave del shot-list.
Lee out/shotlist.json, guarda en public/stock/ y escribe public/stock/clips.json
keyed por seccion. Requiere PEXELS_KEY."""
import os, sys, json, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = os.environ.get("PEXELS_KEY")
OUT = os.path.join(ROOT, "public", "stock")
SHOT = os.path.join(ROOT, "out", "shotlist.json")


def curl_json(url):
    out = subprocess.run(["curl", "-s", "-H", f"Authorization: {KEY}", url],
                         capture_output=True, encoding="utf-8", errors="replace").stdout
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {}


def best_file(video, target_h=720):
    files = [f for f in video.get("video_files", []) if f.get("file_type") == "video/mp4"]
    if not files:
        return None
    files.sort(key=lambda f: abs((f.get("height") or 0) - target_h))
    return files[0]


def main():
    if not KEY:
        print("FALTA PEXELS_KEY"); sys.exit(1)
    os.makedirs(OUT, exist_ok=True)
    shot = json.load(open(SHOT, encoding="utf-8"))
    # limpiar stock anterior para no mezclar temas
    for f in os.listdir(OUT):
        if f.endswith(".mp4"):
            try: os.remove(os.path.join(OUT, f))
            except OSError: pass
    manifest = {}
    for sec in shot["sections"]:
        key = sec["key"]
        clips = []
        for q in sec.get("broll", [])[:4]:
            url = (f"https://api.pexels.com/videos/search?query={q.replace(' ', '%20')}"
                   f"&per_page=3&orientation=landscape&size=medium")
            data = curl_json(url)
            for vid in data.get("videos", [])[:1]:
                vf = best_file(vid)
                if not vf:
                    continue
                fn = f"{key}_{vid['id']}.mp4"
                dst = os.path.join(OUT, fn)
                if not os.path.exists(dst):
                    print(f"[{key}] {q[:35]} -> {fn}")
                    subprocess.run(["curl", "-s", "-L", vf["link"], "-o", dst], timeout=180)
                clips.append({"file": f"stock/{fn}", "query": q,
                              "duration": vid.get("duration", 0),
                              "credit": vid.get("user", {}).get("name", "")})
        # respaldo si una seccion se quedo sin clips
        if not clips and manifest:
            clips = list(manifest.get("hook", []))[:2]
        manifest[key] = clips
    json.dump(manifest, open(os.path.join(OUT, "clips.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    total = sum(len(v) for v in manifest.values())
    print(f"LISTO: {total} clips -> public/stock/clips.json")


if __name__ == "__main__":
    main()
