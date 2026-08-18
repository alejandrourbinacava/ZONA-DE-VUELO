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
- {"text":"<fragmento>", "kind":"ai", "query":"<prompt EN INGLES describiendo la imagen a generar>", "label":"<etiqueta opcional>"}
    USA ESTO solo para escenas concretas que NO existen en bancos de stock ni en Wikipedia: recreaciones
    historicas de un momento (ej. "cinco aviones torpederos desapareciendo sobre el mar en 1945"), o una
    imagen conceptual muy especifica. Se generara con IA. Usalo con moderacion (1-2 por seccion como mucho).
- {"text":"<fragmento>", "kind":"stat", "value":<numero>, "suffix":"<opcional>", "label":"<que es, <=40car>", "color":"cyan|amber|red|green"}
    Solo para una cifra o año clave que aparezca en el fragmento (ej. 1945, 1974).
- {"text":"<fragmento>", "kind":"fact", "kicker":"<ETIQUETA <=22car>", "body":"<frase impacto <=55car>", "accent":"cyan|amber|red|green"}
    Para rematar una idea potente sin entidad ni cifra.

REGLA DE ORO (obligatoria): CADA plano debe mostrar EXACTAMENTE lo que dice su fragmento.

COMO ELEGIR LA FUENTE DE CADA PLANO (piensa esto para cada fragmento):
1. ¿Nombra una entidad REAL y concreta con fotos (persona con nombre, lugar/pais, modelo de avion, suceso
   historico, barco, objeto identificable)? -> "image" (foto real de esa cosa).
2. ¿Describe una accion o escena GENERICA y comun que un banco de stock SEGURO tiene bien grabada (un avion
   despegando, nubes, una cabina, hielo, el mar, un radar, un motor)? -> "broll" (consulta que lo describa).
3. ¿Es un concepto, un fenomeno o una escena ESPECIFICA/HISTORICA que el stock NO va a clavar y solo daria
   material generico o sin relacion (ej. "la radiacion solar incide mas en los polos", "el campo magnetico
   desviando la brujula", "cinco aviones desapareciendo en 1945", una recreacion)? -> "ai" (se genera a medida).
   Ante la duda entre broll generico y ai: si el stock daria algo que NO cuadra, elige "ai".
4. ¿Es una cifra, una frase de remate, o una llamada a la accion (suscribete/like/comenta)? -> "stat"/"fact"/"outro".

PROHIBIDO: usar "broll" para botones de YouTube, "subscribe/like button", pantallas de croma verde, o cualquier
cosa que no aparezca literalmente en el guion. Las llamadas a la accion del cierre van SIEMPRE como "outro"/"fact",
NUNCA como clip de stock.

Reglas:
- No inventes cifras. Fragmentos en el idioma del guion (español). Consultas "broll" en ingles.
- RITMO: fragmentos CORTOS de ~1 frase. Entre 12 y 18 planos por seccion (cuantos mas, mas dinamico).
- En el cierre, el ultimo plano debe ser {"text":"<cierre>","kind":"outro"}.
- Devuelve UNICAMENTE JSON valido:
{"sections":[{"key":"hook","shots":[ ... ]}, ... 7 secciones en orden ...]}"""


def main():
    src = sys.argv[1]
    guion = open(src, encoding="utf-8").read()
    user = f"GUION:\n\n{guion}\n\nGenera el plan de planos JSON de las 7 secciones."
    text, usage = gs.call_claude(SYSTEM, user, max_tokens=13000, thinking={"type": "disabled"})
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
