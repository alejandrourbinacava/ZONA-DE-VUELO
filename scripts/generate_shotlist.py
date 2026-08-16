#!/usr/bin/env python3
"""Convierte un guion .md en un 'shot-list' JSON: por cada seccion, palabras clave
de B-roll (para Pexels) y beats graficos (cifras/frases). Usa Claude.
Uso: python scripts/generate_shotlist.py out/guiones/xxx.md"""
import os, re, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_script as gs  # reutiliza call_claude()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS = ["hook", "parte1", "parte2", "parte3", "parte4", "parte5", "cierre"]

SYSTEM = """Eres el director de arte del canal "Zona de Vuelo". Recibes el guion de un video
y produces un plan visual (shot-list) en JSON para un montaje automatico.

El video tiene 7 secciones en este orden: hook, parte1, parte2, parte3, parte4, parte5, cierre.

Para CADA seccion debes dar:
- "broll": 4 consultas de busqueda EN INGLES para un banco de video de stock (Pexels), concretas y
  visuales, relacionadas con el contenido de esa seccion (aviones, cabina, cielo, radar, tormenta,
  mapa, aeropuerto, motor, etc. segun toque). Evita terminos abstractos.
- "beats": 2 o 3 golpes graficos que resuman lo clave de la seccion. Cada beat es uno de:
    {"t":"stat","value":<numero>,"suffix":"<texto corto opcional ej. ' m' o '%'>","label":"<que es esa cifra, <=40 car>","color":"cyan|amber|red|green"}
    {"t":"fact","kicker":"<ETIQUETA CORTA EN MAYUSCULAS <=22 car>","text":"<frase de impacto <=60 car>","accent":"cyan|amber|red|green"}
  Usa "stat" solo con cifras que aparezcan o se deriven del guion; si no hay cifra clara, usa "fact".
  Para el cierre incluye siempre un beat {"t":"outro"} al final.

Reglas:
- No inventes cifras que no esten en el guion.
- Texto en espanol, salvo las consultas de "broll" que van en ingles.
- Devuelve UNICAMENTE JSON valido, sin markdown, con esta forma exacta:
{"sections":[{"key":"hook","broll":[...],"beats":[...]}, ... 7 secciones ...]}"""


def main():
    src = sys.argv[1]
    guion = open(src, encoding="utf-8").read()
    user = f"GUION:\n\n{guion}\n\nGenera el shot-list JSON de las 7 secciones."
    text, usage = gs.call_claude(SYSTEM, user, max_tokens=4000)
    # limpiar posibles fences
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        print("No devolvio JSON valido:\n", text[:600], file=sys.stderr); sys.exit(1)
    # normalizar: asegurar 7 secciones con las claves correctas por orden
    secs = data.get("sections", [])
    for i, s in enumerate(secs[:7]):
        s["key"] = KEYS[i]
    out = {"sections": secs[:7]}
    dst = os.path.join(ROOT, "out", "shotlist.json")
    json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"LISTO -> {dst}  (tokens salida={usage.get('output_tokens')})")
    for s in out["sections"]:
        print(f"  [{s['key']}] broll={len(s.get('broll',[]))} beats={len(s.get('beats',[]))}")
    return dst


if __name__ == "__main__":
    main()
