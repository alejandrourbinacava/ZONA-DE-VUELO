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

- {"text":"<fragmento>", "kind":"broll", "query":"<consulta EN INGLES para banco de video, concreta y visual>"}
    ESTE ES EL PLANO POR DEFECTO: casi TODO es un CLIP REAL de lo que se dice. Acciones, escenas, objetos,
    fenomenos Y TAMBIEN CIUDADES/LUGARES (¡una ciudad se muestra con un CLIP de la ciudad, NUNCA con una bandera
    ni un mapa!). Ejemplos: "Madrid" -> "Madrid Spain city aerial skyline"; "Nueva York" -> "New York City
    skyline aerial"; "una cabina" -> "airliner cockpit pilots"; "turbulencia" -> "airplane turbulence clouds".
    La consulta describe EXACTAMENTE lo que se ve, en ingles. Prioriza SIEMPRE clip real.
    IMPORTANTE (metaforas/conceptos): NO hay generacion de video IA disponible. Para una metafora o concepto,
    elige "broll" con la MEJOR ESCENA REAL DE AVIACION/CIELO que transmita la idea. REGLA CRITICA: cuando la
    metafora usa un objeto de TIERRA para hablar del cielo (autopistas/carreteras del cielo, rios de aire,
    fronteras invisibles, obstaculos...), la consulta debe ser SIEMPRE de AVIACION, NUNCA del objeto terrestre.
    Ej.: "autopistas/carreteras del cielo", "aerovias" -> "air traffic control radar screen flight routes" o
    "airplanes flying busy sky" (NUNCA "highway"/"road"/"cars"). "fronteras/espacio aereo soberano" ->
    "world map with country borders" o "airplane over map" (NUNCA carteles ni protestas). "obstaculos en la
    ruta" -> "storm clouds airplane" o "mountains aerial" (NUNCA objetos random). Piensa SIEMPRE en aviacion.
- {"text":"<fragmento>", "kind":"ai", "query":"<escena real que transmita la idea>", "label":"<opcional>"}
    Casi NUNCA. Solo si de verdad no existe NINGUNA escena real que sirva. Aun asi, el sistema buscara metraje
    o FOTO REAL (nunca imagenes IA). Prefiere SIEMPRE "broll".
- {"text":"<fragmento>", "kind":"image", "query":"<termino para Wikipedia en español>", "label":"<etiqueta>"}
    USO MUY RESTRINGIDO: SOLO para PERSONAJES PUBLICOS con nombre propio (un piloto famoso, un investigador,
    un politico), MARCAS/EMPRESAS con nombre (Airbus, Boeing, una aerolinea concreta) o un OBJETO/PRODUCTO
    concreto que hay que ver tal cual. NUNCA para ciudades, paises ni conceptos (esos van SIEMPRE como "broll"
    con clip real). Si dudas, NO uses "image": usa "broll".
- {"text":"<fragmento>", "kind":"map", "from":{"name":"Madrid","lat":40.42,"lon":-3.70}, "to":{"name":"Nueva York","lat":40.71,"lon":-74.01}, "label":"<opcional>"}
    MOTION GRAPHICS (mapa animado con arco de vuelo entre dos ciudades). USA ESTO SIEMPRE que el fragmento
    hable de una RUTA, un vuelo de X a Y, cruzar un oceano, una distancia entre dos lugares, el trazado de un
    trayecto, "de A a B", circulo maximo, rutas polares, etc. Pon las coordenadas REALES (lat/lon) de las dos
    ciudades/lugares. Es MUCHO mejor que un clip: se dibuja el mapa, el arco y un avion recorriendolo.
- {"text":"<fragmento>", "kind":"annotate", "query":"<consulta EN INGLES de una FOTO del sujeto>", "callouts":[{"label":"Turbina"},{"label":"Alabes del fan"}], "label":"<ETIQUETA>"}
    MOTION GRAPHICS (explicador). USA ESTO cuando el fragmento EXPLICA las PARTES o elementos de algo (el motor
    y sus piezas, las partes del ala, la cabina, un sistema): se coge una foto real del sujeto, se hace ZOOM y
    entran FLECHAS con TEXTOS señalando 2-4 elementos. En "callouts" pon 2-4 etiquetas cortas (lo que se nombra).
    Hace el video dinamico, no un simple clip.
- {"text":"<fragmento>", "kind":"stat", "value":<numero>, "suffix":"<opcional>", "label":"<que es, <=40car>", "color":"cyan|amber|red|green"}
    Solo para una cifra o año clave que aparezca en el fragmento (ej. 1945, 1974).
- {"text":"<fragmento>", "kind":"fact", "kicker":"<ETIQUETA <=22car>", "body":"<frase impacto <=55car>", "accent":"cyan|amber|red|green"}
    Para rematar una idea potente sin entidad ni cifra.

REGLA DE ORO (obligatoria): CADA plano debe mostrar EXACTAMENTE lo que dice su fragmento.

COMO ELEGIR LA FUENTE DE CADA PLANO (por defecto, CLIP REAL):
1. ¿Es un PERSONAJE PUBLICO con nombre, una MARCA/EMPRESA o un OBJETO concreto que hay que ver tal cual?
   -> "image". (Esto es la EXCEPCION, poco frecuente.)
2. TODO LO DEMAS que sea real y grabable -acciones, escenas, aviones, cabinas, cielo, aeropuertos, CIUDADES,
   paises, mar, objetos- -> "broll" (CLIP REAL de eso). Una ciudad = clip de la ciudad, NO una bandera/mapa.
3. ¿Es una metafora/analogia visual, un fenomeno fisico o una recreacion que NINGUN stock tendra tal cual?
   -> "ai" (CLIP DE VIDEO IA fotorealista, con moderacion). El objetivo es que SIEMPRE parezca metraje real.
4. ¿Cifra, frase de remate, o llamada a la accion? -> "stat"/"fact"/"outro".

META de dinamismo: NO todo clips. Aprovecha los MOTION GRAPHICS siempre que el guion lo permita para que el
video no sea plano: usa "map" en cuanto se hable de rutas/vuelos entre lugares, "annotate" cuando se expliquen
partes de algo, y "stat"/"fact" para cifras y remates. Apunta a meter varios "map"/"annotate" por video cuando
el tema lo permita (rutas, motores, partes del avion...). El resto, "broll" (clips reales). "image" solo para
nombres propios/marcas. Nada de ilustraciones ni dibujos: mapas reales, fotos reales, clips reales.

REGLA ANTI-DESAJUSTE: NUNCA mandes a "broll" una metafora pura ("como una cinta transportadora"). Si el stock
no lo tiene literal, va como "ai" (clip video). Pero una CIUDAD, un avion, una cabina, el mar... SI van a "broll".

PROHIBIDO: usar "broll" para botones de YouTube, "subscribe/like button", pantallas de croma verde, o cualquier
cosa que no aparezca literalmente en el guion. Las llamadas a la accion del cierre van SIEMPRE como "outro"/"fact",
NUNCA como clip de stock.

Reglas:
- No inventes cifras. Fragmentos en el idioma del guion (español). Consultas "broll" en ingles.
- SINCRONIA (critico): el campo "text" de cada plano debe ser el fragmento de narracion COPIADO TEXTUALMENTE
  del guion, palabra por palabra. Los fragmentos, en orden, deben CUBRIR TODO el texto de la seccion SIN saltarse
  ni resumir nada (el sistema usa la longitud de cada fragmento para sincronizar con la voz; si resumes, se desfasa).
- RITMO: fragmentos CORTOS de ~1 frase. Entre 12 y 18 planos por seccion (cuantos mas, mas dinamico).
- En el cierre, el ultimo plano debe ser {"text":"<cierre>","kind":"outro"}.
- Devuelve UNICAMENTE JSON valido:
{"sections":[{"key":"hook","shots":[ ... ]}, ... 7 secciones en orden ...]}"""


def salvage_json(text):
    """Intenta recuperar un JSON de secciones aunque venga truncado: recorta al ultimo
    shot completo y cierra los corchetes. Devuelve dict o None."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # cortar tras el ultimo objeto-shot completo ('}' seguido de coma o cierre) y cerrar estructura
    cut = max(text.rfind("},"), text.rfind("}]"))
    if cut == -1:
        return None
    frag = text[:cut + 1]
    for tail in ("]}]}", "}]}]}", "]}", "}]}"):   # varios cierres posibles
        try:
            return json.loads(frag + tail)
        except json.JSONDecodeError:
            continue
    return None


def main():
    src = sys.argv[1]
    guion = open(src, encoding="utf-8").read()
    user = f"GUION:\n\n{guion}\n\nGenera el plan de planos JSON de las 7 secciones."
    data = None
    for intento in range(3):
        text, usage = gs.call_claude(SYSTEM, user, max_tokens=20000, thinking={"type": "disabled"})
        text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
        try:
            data = json.loads(text)
            break
        except json.JSONDecodeError:
            data = salvage_json(text)   # rescatar truncado
            if data and data.get("sections"):
                print(f"  (JSON rescatado en intento {intento+1}: {len(data['sections'])} secciones)", file=sys.stderr)
                break
            print(f"  (intento {intento+1}/3 JSON invalido, reintento)", file=sys.stderr)
            data = None
    if not data or not data.get("sections"):
        print("No devolvio JSON valido tras 3 intentos:\n", (text or "")[:800], file=sys.stderr); sys.exit(1)
    secs = data.get("sections", [])
    for i, s in enumerate(secs[:7]):
        s["key"] = KEYS[i]
    out = {"sections": secs[:7]}
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)   # out/ puede no existir si el guion se reuso
    dst = os.path.join(ROOT, "out", "shotlist.json")
    json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"LISTO -> {dst}  (tokens salida={usage.get('output_tokens')})")
    for s in out["sections"]:
        kinds = [sh.get("kind") for sh in s.get("shots", [])]
        print(f"  [{s['key']}] {len(kinds)} planos: {kinds}")
    return dst


if __name__ == "__main__":
    main()
