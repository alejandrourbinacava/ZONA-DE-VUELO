# shotlists/

Shot-lists escritos A MANO (por Claude Code en sesión) y commiteados. Si existe
`shotlists/<slug>.json` para una idea, `produce.py` lo REUSA en vez de llamar a Gemini
(mejor control de motion-graphics y coste 0). El `<slug>` es el mismo que el del guion en
`guiones/<slug>.md`. Si no hay fichero aquí, el shot-list lo genera Gemini automáticamente.

Formato: `{"sections":[{"key":"hook","shots":[ ... ]}, ... 7 secciones ...]}`
(kinds: broll, image, ai, map, annotate, compare, timeline, stat, fact, outro).
