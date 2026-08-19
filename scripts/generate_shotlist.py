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
- {"text":"<fragmento>", "kind":"ai", "query":"<PROMPT EN INGLES rico y cinematografico>", "label":"<opcional>"}
    USA ESTO GENEROSAMENTE, no lo raciones. Es para TODO lo que no sea una toma real y literal de aviacion:
    conceptos, fenomenos fisicos, metaforas/analogias, recreaciones historicas e ideas abstractas.
    El prompt debe ser DETALLADO (sujeto + escena + estilo + luz) y SIEMPRE anclado a aviacion/cielo/atmosfera.
    Ejemplos de buen prompt:
      "a powerful jet stream shown as a glowing ribbon of fast-moving air high in the stratosphere, an airliner
       riding it, volumetric light, cinematic, photorealistic, 16:9"
      "cross-section diagram-like view of warm equator air and cold polar air colliding, forming a fast wind
       band, dramatic atmospheric lighting, cinematic, photorealistic"
    Apunta a que un BUEN numero de planos por seccion sean "ai" cuando el tema es conceptual (fisica, fenomenos):
    en esos casos "ai" puede ser la mayoria de los planos. Si dudas entre broll y ai, elige ai.
- {"text":"<fragmento>", "kind":"stat", "value":<numero>, "suffix":"<opcional>", "label":"<que es, <=40car>", "color":"cyan|amber|red|green"}
    Solo para una cifra o año clave que aparezca en el fragmento (ej. 1945, 1974).
- {"text":"<fragmento>", "kind":"fact", "kicker":"<ETIQUETA <=22car>", "body":"<frase impacto <=55car>", "accent":"cyan|amber|red|green"}
    Para rematar una idea potente sin entidad ni cifra.

REGLA DE ORO (obligatoria): CADA plano debe mostrar EXACTAMENTE lo que dice su fragmento.

COMO ELEGIR LA FUENTE DE CADA PLANO (piensa esto para cada fragmento):
1. ¿Nombra una entidad REAL y concreta con fotos (persona con nombre, lugar/pais, modelo de avion, suceso
   historico, barco, objeto identificable)? -> "image" (foto real de esa cosa).
2. ¿Describe una accion o escena LITERAL de aviacion/cielo/aeropuerto que un banco de stock SEGURO tiene
   grabada TAL CUAL (un avion despegando, nubes, una cabina, una pista, un panel de salidas, un motor)?
   -> "broll", con una consulta que sea esa escena REAL de aviacion. La consulta NUNCA es una metafora.
3. ¿Es un CONCEPTO, un fenomeno fisico, o una METAFORA/ANALOGIA ("como una cinta transportadora", "un rio de
   aire", "como un pez en el agua", "el viento empuja/frena", "la radiacion solar en los polos", "el aire se
   desvia por la rotacion") o una recreacion historica? -> "ai" SIEMPRE. Se genera la idea EN CONTEXTO DE
   AVIACION/ATMOSFERA (ej. "jet stream as a glowing river of air in the sky pushing an airliner").
4. ¿Es una cifra, una frase de remate, o una llamada a la accion (suscribete/like/comenta)? -> "stat"/"fact"/"outro".

REGLA ANTI-DESAJUSTE (obligatoria): NUNCA mandes a stock ("broll") una metafora, una analogia, una comparacion
("como...", "imagina...", "es como si...") ni un concepto abstracto. El stock devuelve cosas literales sin
relacion (una moto para "cinta transportadora", una melena para "viento", una carretera para "no ir recto").
Todo eso va como "ai". El "broll" es SOLO para escenas de aviacion reales y literales.

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
