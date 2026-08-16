#!/usr/bin/env python3
"""Orquestador: una idea -> video final en VIDEOS FINALIZADOS.
Uso: python scripts/produce.py "idea del video" [--norender]
Encadena: guion (Claude) -> shot-list (Claude) -> voz (GenAIPro) -> stock (Pexels)
          -> props -> render (Remotion) -> mover + metadatos."""
import os, re, sys, json, shutil, subprocess, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
# En local: carpeta del escritorio. En la nube: se pasa VIDEOS_DIR (ej. ./salidas).
FINAL = os.environ.get("VIDEOS_DIR", r"C:\Users\aleja\Desktop\VIDEOS FINALIZADOS")


def slug(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return (re.sub(r"[^a-zA-Z0-9]+", "_", t).strip("_").lower())[:60] or "video"


def run(cmd, **kw):
    print("»", " ".join(str(c) for c in cmd))
    r = subprocess.run(cmd, cwd=ROOT, **kw)
    if r.returncode != 0:
        print("! fallo en:", cmd[:3]); sys.exit(1)


def main():
    args = [a for a in sys.argv[1:] if a != "--norender"]
    norender = "--norender" in sys.argv
    idea = " ".join(args)
    if not idea:
        print('Uso: python scripts/produce.py "idea" [--norender]'); sys.exit(1)
    s = slug(idea)
    guion = os.path.join(ROOT, "out", "guiones", s + ".md")

    print("\n=== 1/6 GUION ===")
    if os.path.exists(guion) and os.path.getsize(guion) > 500:
        print("guion ya existe, lo reuso:", guion)
    else:
        run([PY, "scripts/generate_script.py", idea])

    print("\n=== 2/6 SHOT-LIST ===")
    run([PY, "scripts/generate_shotlist.py", guion])

    print("\n=== 3/6 VOZ (Gabriel) ===")
    voz_dir = os.path.join(ROOT, "out", "voz")
    if os.path.isdir(voz_dir):
        shutil.rmtree(voz_dir)  # limpiar audios de un tema anterior
    run([PY, "scripts/produce_voice.py", guion])

    print("\n=== 4/6 STOCK (Pexels) ===")
    run([PY, "scripts/fetch_stock.py"])

    print("\n=== 5/6 PROPS + AUDIO ===")
    manifest = json.load(open(os.path.join(ROOT, "out", "voz", "manifest.json"), encoding="utf-8"))
    clips = json.load(open(os.path.join(ROOT, "public", "stock", "clips.json"), encoding="utf-8"))
    shotlist = json.load(open(os.path.join(ROOT, "out", "shotlist.json"), encoding="utf-8"))
    props = {"manifest": manifest, "clips": clips, "shotlist": shotlist}
    props_path = os.path.join(ROOT, "out", "render_props.json")
    json.dump(props, open(props_path, "w", encoding="utf-8"), ensure_ascii=False)
    shutil.copy(os.path.join(ROOT, "out", "voz", "narration_full.mp3"),
                os.path.join(ROOT, "public", "narration_full.mp3"))
    print(f"props -> {props_path}  ({manifest['total_duration']:.0f}s)")

    if norender:
        print("\n[--norender] Paro antes de renderizar."); return

    print("\n=== 6/6 RENDER ===")
    raw = os.path.join(ROOT, "out", s + ".mp4")
    run(["npx", "remotion", "render", "Auto", raw, "--props=out/render_props.json",
         "--concurrency=6"], shell=(os.name == "nt"))  # shell solo en Windows para hallar npx
    # comprimir para subir
    web = os.path.join(ROOT, "out", s + "_web.mp4")
    subprocess.run(["ffmpeg", "-y", "-i", raw, "-c:v", "libx264", "-crf", "22",
                    "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", web],
                   cwd=ROOT, capture_output=True)
    os.makedirs(FINAL, exist_ok=True)
    n = len([f for f in os.listdir(FINAL) if f.endswith(".mp4")]) + 1
    base = f"{n:02d} - {slug(idea)}"
    dst = os.path.join(FINAL, base + ".mp4")
    shutil.copy(web if os.path.exists(web) else raw, dst)
    # metadatos para YouTube (titulo/descripcion/keywords)
    meta_path = os.path.join(FINAL, base + ".json")
    try:
        r = subprocess.run([PY, "scripts/generate_metadata.py", guion], cwd=ROOT,
                           capture_output=True, encoding="utf-8", errors="replace")
        if r.returncode == 0 and r.stdout.strip():
            open(meta_path, "w", encoding="utf-8").write(r.stdout.strip())
    except Exception as e:
        print("aviso: metadatos fallaron:", e)
    print(f"\n✔ LISTO -> {dst}")
    print(f"VIDEO::{dst}")
    print(f"META::{meta_path if os.path.exists(meta_path) else ''}")


if __name__ == "__main__":
    main()
