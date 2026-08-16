#!/usr/bin/env python3
"""Convierte un guion .md en un shot-list JSON: por cada seccion, una secuencia
ORDENADA de planos alineados con lo que se dice. Cada plano es imagen de entidad,
clip de stock, o beat grafico. Usa Claude.
Uso: python scripts/generate_shotlist.py out/guiones/xxx.md"""
import os, re, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_script as gs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS = ["hook", "parte1", "parte2", "parte3", "parte4", "parte5", "cierre"]

SYSTEM = """Eres el director de arte del canal "Zona de Vuelo". Recibes el guion de un video
(7 secciones: hook, parte1..parte5, cierre) y produces un PLAN DE PLANOS en JSON, seccion a seccion,
para un montaje automatico donde lo que se VE debe coincidir con lo que se DICE en ese momento.

Para cada seccion, divide su texto narrado en fragmentos CONSECUTIVOS de ~1 frase que cubran TODO el
texto en orden. Para CADA fragmento decide el plano mas literal posible. Un plano ("shot") es:

- {"text":"<el fragmento de narracion, textual>", "kind":"image", "query":"<termino para Wikipedia en español>", "label":"<etiqueta corta en pantalla>"}
    USA ESTO cuando el fragmento menciona algo CONCRETO Y VISUAL: un lugar con nombre (Bermudas, Florida,
    el Tibet), una persona con nombre propio (Charles Berlitz), un modelo o tipo de avion concreto, un
    suceso historico con nombre (el Vuelo 19), un barco, un objeto identificable. La imagen debe ser DE ESA COSA.
- {"text":"<fragmento>", "kind":"broll", "query":"<consulta EN INGLES para banco de video Pexels, concreta y visual>"}
    USA ESTO para acciones o conceptos generales sin entidad concreta (un avion volando, una cabina,
    turbulencia, un radar, el mar). La consulta debe describir EXACTAMENTE lo que se dice.
- {"text":"<fragmento>", "kind":"stat", "value":<numero>, "suffix":"<opcional>", "label":"<que es, <=40car>", "color":"cyan|amber|red|green"}
    Solo para una cifra o año clave que aparezca en el fragmento (ej. 1945, 1974).
- {"text":"<fragmento>", "kind":"fact", "kicker":"<ETIQUETA <=22car>", "body":"<frase impacto <=55car>", "accent":"cyan|amber|red|green"}
    Para rematar una idea potente sin entidad ni cifra.

REGLA DE ORO (obligatoria): si se nombra algo concreto (lugar, persona, avion, suceso, objeto), el plano
DEBE ser "image" de esa cosa exacta. Nunca pongas un plano generico que no tenga relacion con lo que se dice.

Reglas:
- No inventes cifras. Fragmentos en el idioma del guion (español). Consultas "broll" en ingles.
- Entre 5 y 9 planos por seccion. En el cierre, el ultimo plano debe ser {"text":"<cierre>","kind":"outro"}.
- Devuelve UNICAMENTE JSON valido:
{"sections":[{"key":"hook","shots":[ ... ]}, ... 7 secciones en orden ...]}"""


def main():
    src = sys.argv[1]
    guion = open(src, encoding="utf-8").read()
    user = f"GUION:\n\n{guion}\n\nGenera el plan de planos JSON de las 7 secciones."
    text, usage = gs.call_claude(SYSTEM, user, max_tokens=8000, thinking={"type": "disabled"})
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        print("No devolvio JSON valido:\n", text[:800], file=sys.stderr); sys.exit(1)
    secs = data.get("sections", [])
    for i, s in enumerate(secs[:7]):
        s["key"] = KEYS[i]
    out = {"sections": secs[:7]}
    dst = os.path.join(ROOT, "out", "shotlist.json")
    json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"LISTO -> {dst}  (tokens salida={usage.get('output_tokens')})")
    for s in out["sections"]:
        kinds = [sh.get("kind") for sh in s.get("shots", [])]
        print(f"  [{s['key']}] {len(kinds)} planos: {kinds}")
    return dst


if __name__ == "__main__":
    main()
