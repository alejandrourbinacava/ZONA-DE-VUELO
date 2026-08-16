#!/usr/bin/env python3
"""Descarga B-roll de stock (gratis, con licencia Pexels) por seccion.
Requiere PEXELS_KEY en entorno. Guarda en public/stock/ y escribe clips.json.
Uso: PEXELS_KEY=xxx python scripts/fetch_pexels.py"""
import os, sys, json, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = os.environ.get("PEXELS_KEY")
OUT = os.path.join(ROOT, "public", "stock")
os.makedirs(OUT, exist_ok=True)

# consultas de busqueda por seccion (ingles = mas resultados en stock)
QUERIES = {
    "hook": ["commercial airplane flying clouds", "airplane sky aerial",
             "airport departure board", "airplane taking off", "airliner above clouds"],
    "etops": ["airplane landing runway", "jet engine turbine closeup",
              "twin engine airliner", "airplane cockpit pilots", "airport apron aircraft"],
    "frio": ["antarctica ice landscape", "blizzard snow storm",
             "frozen ocean ice", "glacier aerial", "icebergs antarctica"],
    "infraestructura": ["air traffic control tower", "satellite dish antenna",
                        "radar screen technology", "weather station snow", "airport ground crew"],
    "excepciones": ["airplane window wing view", "military cargo aircraft",
                    "boeing 787 airplane", "research base antarctica", "airplane on snow"],
    "geografia": ["planet earth from space", "arctic aerial ice",
                  "world map globe", "city lights night aerial", "ocean aerial waves"],
    "cierre": ["airplane sunset silhouette", "antarctica aerial drone",
               "airplane golden hour", "airplane contrail sky", "airplane wing sunset"],
}


def curl_json(url):
    out = subprocess.run(["curl", "-s", "-H", f"Authorization: {KEY}", url],
                         capture_output=True, encoding="utf-8", errors="replace").stdout
    return json.loads(out)


def best_file(video, target_h=720):
    files = [f for f in video.get("video_files", []) if (f.get("file_type") == "video/mp4")]
    if not files:
        return None
    files.sort(key=lambda f: abs((f.get("height") or 0) - target_h))
    return files[0]


def main():
    if not KEY:
        print("FALTA PEXELS_KEY en el entorno."); sys.exit(1)
    manifest = {}
    for sec, queries in QUERIES.items():
        clips = []
        for q in queries:
            url = f"https://api.pexels.com/videos/search?query={q.replace(' ', '%20')}&per_page=3&orientation=landscape&size=medium"
            data = curl_json(url)
            for vid in data.get("videos", [])[:1]:  # 1 por consulta
                vf = best_file(vid)
                if not vf:
                    continue
                fn = f"{sec}_{vid['id']}.mp4"
                dst = os.path.join(OUT, fn)
                if not os.path.exists(dst):
                    print(f"[{sec}] descargando {q} -> {fn}")
                    subprocess.run(["curl", "-s", "-L", vf["link"], "-o", dst], check=True)
                clips.append({"file": f"stock/{fn}", "query": q,
                              "duration": vid.get("duration", 0),
                              "credit": vid.get("user", {}).get("name", "")})
        manifest[sec] = clips
    json.dump(manifest, open(os.path.join(OUT, "clips.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\nLISTO -> public/stock/clips.json")
    print("Creditos (Pexels): incluir en la descripcion del video.")


if __name__ == "__main__":
    main()
