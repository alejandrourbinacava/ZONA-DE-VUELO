import React from "react";
import { AbsoluteFill, Audio, OffthreadVideo, Img, Sequence, staticFile,
  useCurrentFrame, useVideoConfig, interpolate, spring, Easing } from "remotion";
import { COLORS } from "../theme";
import { Cue } from "../antartida/Subtitles";
import { MapRoute, Annotate, Compare, Timeline, KeywordTag } from "./MotionGraphics";

export type Section = { key: string; title: string; offset: number; duration: number; cues: Cue[] };
export type Manifest = { total_duration: number; fps: number; sections: Section[] };
type Pt = { name?: string; lat: number; lon: number };
type Shot = {
  kind: string; text: string; file?: string; label?: string; source?: string; key?: string;
  value?: number; suffix?: string; color?: string; kicker?: string; body?: string; accent?: string;
  from?: Pt; to?: Pt; straight?: boolean; bow?: number; callouts?: { label: string; x?: number; y?: number }[];
  a?: number; b?: number; alabel?: string; blabel?: string; unit?: string;
  events?: { year: string | number; text: string }[];
};
export type Media = { sections: { key: string; shots: Shot[] }[] };

const CMAP: Record<string, string> = { cyan: COLORS.cyan, amber: COLORS.amber, red: COLORS.red, green: "#9be08a" };
const col = (c?: string) => (c && CMAP[c]) || COLORS.cyan;
const MAX_CELL = 5.0;   // ningun plano supera esto (ritmo)

// ---------- ESTILO POR VIDEO: semilla = titulo -> cada video tiene su propio aspecto (no es una plantilla) ----------
type Mode = "bleed" | "card" | "wide";                       // encuadre del clip: pantalla completa / tarjeta / cine 2.39:1
type Fx = "fade" | "zoom" | "slide" | "whip" | "wipe" | "flash";   // transicion de entrada
const StyleCtx = React.createContext<{ tint: string; hue: number }>({ tint: "rgba(0,0,0,0)", hue: 0 });
const hashStr = (s: string) => { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; };
const makeRng = (seed: number) => () => { seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return seed / 4294967296; };

// ---------- fondo de rejilla en movimiento ----------
const GridBG: React.FC = () => {
  const { hue } = React.useContext(StyleCtx);
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bgBottom }}>
      <OffthreadVideo src={staticFile("grid.mp4")} loop muted
        style={{ width: "100%", height: "100%", objectFit: "cover", opacity: 0.5, filter: `hue-rotate(${hue}deg)` }} />
      <AbsoluteFill style={{ background: `radial-gradient(circle at 50% 45%, transparent 30%, ${COLORS.bgBottom} 95%)` }} />
    </AbsoluteFill>
  );
};

// entrada suave de cada plano (fade + leve escala)
const useEnter = () => {
  const f = useCurrentFrame();
  const s = spring({ frame: f, fps: 30, config: { damping: 200, stiffness: 120 } });
  return { opacity: interpolate(f, [0, 8], [0, 1], { extrapolateRight: "clamp" }), s };
};

// ---------- clip de stock enmarcado (esquinas redondeadas, rejilla alrededor) ----------
const ClipCard: React.FC<{ file: string; startFrom: number; mode?: Mode }> = ({ file, startFrom, mode = "card" }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const { tint } = React.useContext(StyleCtx);
  const enter = spring({ frame, fps: 30, config: { damping: 18, stiffness: 130 } });
  const scale = interpolate(frame, [0, durationInFrames], [1.0, 1.08]);
  if (mode !== "card") {
    // pantalla completa (o franja panoramica de cine): metraje a sangre, con leve "mano" y gradacion de color
    const wide = mode === "wide";
    const drift = Math.sin(frame / 38) * 6;
    return (
      <AbsoluteFill>
        <div style={{ position: "absolute", left: 0, right: 0, top: wide ? "14%" : 0, bottom: wide ? "14%" : 0,
          overflow: "hidden", background: "#000" }}>
          <OffthreadVideo src={staticFile(file)} startFrom={Math.round(startFrom * 30)} loop muted
            style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${1.04 * scale}) translate(${drift}px, 0px)` }} />
          <AbsoluteFill style={{ background: tint }} />
          <AbsoluteFill style={{ background: "linear-gradient(180deg, transparent 62%, rgba(2,6,14,0.55) 100%)" }} />
        </div>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <div style={{ position: "absolute", inset: "10% 8%", borderRadius: 30, overflow: "hidden",
        boxShadow: "0 40px 90px rgba(0,0,0,0.6)", border: "3px solid rgba(140,190,255,0.22)",
        opacity: enter, transform: `scale(${(0.94 + enter * 0.06) * scale})` }}>
        <OffthreadVideo src={staticFile(file)} startFrom={Math.round(startFrom * 30)} loop muted
          style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </div>
    </AbsoluteFill>
  );
};

// ---------- imagen de entidad: marco PREMIUM centrado, entra con efecto, rejilla alrededor ----------
const ImageCard: React.FC<{ file: string; label?: string; i: number }> = ({ file, label, i }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const enter = spring({ frame, fps: 30, config: { damping: 15, stiffness: 110 } });
  const dir = i % 2 === 0 ? 1 : -1;
  const scale = interpolate(frame, [0, durationInFrames], [1.06, 1.2]);   // Ken Burns continuo
  const pan = interpolate(frame, [0, durationInFrames], [0, 20 * dir]);
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <div style={{
        width: 860, height: 700, maxWidth: "56%", borderRadius: 26, overflow: "hidden",
        background: "#0a1830",
        border: "3px solid rgba(120,200,255,0.45)",
        boxShadow: "0 40px 110px rgba(0,0,0,0.65), 0 0 0 10px rgba(10,24,48,0.7), 0 0 60px rgba(55,226,255,0.15)",
        opacity: enter,
        transform: `translateY(${(1 - enter) * 60}px) scale(${0.82 + enter * 0.18})`,
      }}>
        <Img src={staticFile(file)} style={{ width: "100%", height: "100%", objectFit: "cover",
          transform: `scale(${scale}) translateX(${pan}px)` }} />
        <AbsoluteFill style={{ background: "linear-gradient(180deg, transparent 60%, rgba(5,13,28,0.9) 100%)" }} />
        {label ? (
          <div style={{ position: "absolute", left: 26, bottom: 22, borderLeft: `6px solid ${COLORS.cyan}`, paddingLeft: 16 }}>
            <div style={{ fontSize: 36, fontWeight: 800, color: "#fff", textShadow: "0 3px 14px rgba(0,0,0,0.9)" }}>{label}</div>
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

// ---------- imagen IA como CLIP: pantalla completa, MOVIMIENTO cinematografico (parece metraje) ----------
// Alterna 3 patrones (push-in, pull-out, paneo) segun el indice para que NUNCA parezca una foto fija.
const AiClip: React.FC<{ file: string; i: number; mode?: Mode }> = ({ file, i, mode = "card" }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const { tint } = React.useContext(StyleCtx);
  const enter = spring({ frame, fps: 30, config: { damping: 18, stiffness: 130 } });
  const dir = i % 2 === 0 ? 1 : -1;
  const patt = i % 3;
  // [scaleFrom, scaleTo, panXfrom, panXto, panYfrom, panYto] — movimiento amplio pero suave
  const P = patt === 0
    ? [1.06, 1.26, -26 * dir, 26 * dir, 0, -18]      // acercamiento con deriva
    : patt === 1
    ? [1.28, 1.10, 22 * dir, -14 * dir, -12, 8]      // alejamiento lento
    : [1.12, 1.22, -40 * dir, 40 * dir, 6, -8];      // paneo lateral con leve zoom
  const ease = { easing: Easing.inOut(Easing.ease) } as const;
  const scale = interpolate(frame, [0, durationInFrames], [P[0], P[1]], ease);
  const panX = interpolate(frame, [0, durationInFrames], [P[2], P[3]], ease);
  const panY = interpolate(frame, [0, durationInFrames], [P[4], P[5]], ease);
  if (mode !== "card") {
    const wide = mode === "wide";
    return (
      <AbsoluteFill>
        <div style={{ position: "absolute", left: 0, right: 0, top: wide ? "14%" : 0, bottom: wide ? "14%" : 0,
          overflow: "hidden", background: "#000" }}>
          <Img src={staticFile(file)} style={{ width: "100%", height: "100%", objectFit: "cover",
            transformOrigin: ["50% 50%", "30% 42%", "70% 56%"][i % 3],
            transform: `scale(${scale}) translate(${panX}px, ${panY}px)` }} />
          <AbsoluteFill style={{ background: tint }} />
          <AbsoluteFill style={{ background: "linear-gradient(180deg, transparent 62%, rgba(2,6,14,0.55) 100%)" }} />
        </div>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <div style={{ position: "absolute", inset: "10% 8%", borderRadius: 30, overflow: "hidden",
        boxShadow: "0 40px 90px rgba(0,0,0,0.6)", border: "3px solid rgba(140,190,255,0.22)",
        opacity: enter, transform: `scale(${0.94 + enter * 0.06})` }}>
        <Img src={staticFile(file)} style={{ width: "100%", height: "100%", objectFit: "cover",
          transformOrigin: ["50% 50%", "30% 42%", "70% 56%"][i % 3],   // punto de enfoque distinto por toma
          transform: `scale(${scale}) translate(${panX}px, ${panY}px)` }} />
      </div>
    </AbsoluteFill>
  );
};

// ---------- tarjeta de respaldo: si un plano se queda SIN visual, mostramos la frase con estilo
//            (nunca una rejilla vacia). Texto legible, no gigante, para frases largas. ----------
const FallbackCard: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const s = spring({ frame, fps: 30, config: { damping: 16 } });
  const scale = interpolate(frame, [0, durationInFrames], [1.0, 1.06]);
  const clean = (text || "").replace(/\s+/g, " ").trim();
  const t = clean.length > 120 ? clean.slice(0, 117).trimEnd() + "…" : clean;
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <AbsoluteFill style={{ background: "radial-gradient(circle at 50% 45%, rgba(20,45,85,0.55), rgba(5,10,20,0.9) 80%)" }} />
      <div style={{ maxWidth: "72%", textAlign: "center", opacity: s,
        transform: `translateY(${(1 - s) * 30}px) scale(${(0.92 + s * 0.08) * scale})` }}>
        <div style={{ fontSize: 30, letterSpacing: 6, color: COLORS.cyan, marginBottom: 22, fontWeight: 800 }}>🛩️ ZONA DE VUELO</div>
        <div style={{ fontSize: 58, fontWeight: 800, color: "#fff", lineHeight: 1.18,
          textShadow: "0 4px 24px rgba(0,0,0,0.85)" }}>{t}</div>
      </div>
    </AbsoluteFill>
  );
};

// ---------- frase clave: texto blanco gigante sobre fondo oscuro (estilo editora) ----------
const KeyPhrase: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const s = spring({ frame, fps: 30, config: { damping: 14 } });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <AbsoluteFill style={{ background: "rgba(5,10,20,0.72)" }} />
      <div style={{ padding: "0 120px", textAlign: "center", opacity: s,
        transform: `scale(${0.9 + s * 0.1})` }}>
        <div style={{ fontSize: 90, fontWeight: 900, color: "#fff", textTransform: "uppercase",
          letterSpacing: 1, lineHeight: 1.05,
          textShadow: "0 4px 0 rgba(0,0,0,0.55), 0 10px 40px rgba(0,0,0,0.8)",
          WebkitTextStroke: "2px rgba(0,0,0,0.25)" }}>{text}</div>
      </div>
    </AbsoluteFill>
  );
};

// ---------- cifra grande ----------
const StatCard: React.FC<{ value: number; suffix?: string; label?: string; color?: string }> =
({ value, suffix, label, color }) => {
  const frame = useCurrentFrame();
  const s = spring({ frame, fps: 30, config: { damping: 16 } });
  const n = interpolate(s, [0, 1], [0, value]);
  const c = col(color);
  const dec = Number.isInteger(value) ? 0 : 1;
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <Audio src={staticFile("tick.mp3")} volume={0.5} />   {/* acento al aparecer la cifra (sound design) */}
      <AbsoluteFill style={{ background: "rgba(5,10,20,0.55)" }} />
      <div style={{ textAlign: "center", opacity: s, transform: `scale(${0.7 + s * 0.3})` }}>
        <div style={{ fontSize: 230, fontWeight: 900, color: c, lineHeight: 1, textShadow: `0 0 50px ${c}66` }}>
          {n.toFixed(dec)}{suffix || ""}
        </div>
        {label ? <div style={{ fontSize: 44, fontWeight: 700, color: "#fff", marginTop: 16 }}>{label}</div> : null}
      </div>
    </AbsoluteFill>
  );
};

const Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const s = spring({ frame, fps: 30, config: { damping: 14 } });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <AbsoluteFill style={{ background: "rgba(5,10,20,0.6)" }} />
      <div style={{ textAlign: "center", opacity: s, transform: `scale(${0.85 + s * 0.15})` }}>
        <div style={{ fontSize: 36, color: COLORS.dim, letterSpacing: 8 }}>SUSCRÍBETE A</div>
        <div style={{ fontSize: 120, fontWeight: 900, color: "#fff", letterSpacing: 3 }}>
          ZONA DE <span style={{ color: COLORS.cyan }}>VUELO</span> 🛩️
        </div>
      </div>
    </AbsoluteFill>
  );
};

const BrandCorner: React.FC = () => (
  <div style={{ position: "absolute", top: 40, left: 60, display: "flex", alignItems: "center", gap: 12, opacity: 0.92, zIndex: 20 }}>
    <span style={{ fontSize: 30 }}>🛩️</span>
    <span style={{ fontWeight: 900, fontSize: 24, color: "#fff", letterSpacing: 2 }}>
      ZONA DE <span style={{ color: COLORS.cyan }}>VUELO</span>
    </span>
  </div>
);
const ProgressBar: React.FC<{ total: number }> = ({ total }) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [0, total], [0, 1], { extrapolateRight: "clamp" });
  return <div style={{ position: "absolute", bottom: 0, left: 0, height: 6, width: `${p * 100}%`,
    background: COLORS.cyan, boxShadow: `0 0 12px ${COLORS.cyan}`, zIndex: 20 }} />;
};

type Cell = { from: number; dur: number; shot: Shot; sub: number; secStart: boolean };

function buildCells(manifest: Manifest, media: Media): Cell[] {
  const fps = manifest.fps || 30;
  const byKey: Record<string, Shot[]> = {};
  media.sections.forEach((s) => (byKey[s.key] = s.shots));
  const cells: Cell[] = [];
  for (const sec of manifest.sections) {
    const shots = byKey[sec.key] || [];
    if (!shots.length) continue;
    const weights = shots.map((sh) => Math.max(8, (sh.text || "").length));
    const total = weights.reduce((a, b) => a + b, 0);
    let t = sec.offset;
    shots.forEach((shot, si) => {
      const shotDur = (sec.duration * weights[si]) / total;
      // UN plano continuo por escena (sin trocear -> sin parpadeo del mismo clip)
      const from = Math.round(t * fps);
      const to = Math.round((t + shotDur) * fps);
      const dur = Math.max(1, to - from);
      // FOTO fija larga -> varias tomas de ~3.5s con encuadre/movimiento DISTINTO (punch-in, alejar, paneo):
      // asi nunca se queda "plantada" una imagen varios segundos (lo mas importante: los primeros segundos)
      const isPhoto = shot.kind === "image" && shot.source !== "FOTO";
      const isLongClip = shot.kind === "broll" && !!shot.file && dur > 8 * fps;   // clip largo -> tomas de ~5s con otro punto de entrada
      const n = isPhoto && dur > 4.2 * fps ? Math.max(2, Math.round(dur / (3.5 * fps)))
        : isLongClip ? Math.max(2, Math.round(dur / (5.5 * fps))) : 1;
      for (let k = 0; k < n; k++) {
        const a = from + Math.round((dur * k) / n);
        const b = from + Math.round((dur * (k + 1)) / n);
        cells.push({ from: a, dur: Math.max(1, b - a), shot, sub: k, secStart: si === 0 && k === 0 });
      }
      t += shotDur;
    });
  }
  return cells;
}

// clip de stock / foto IA con rotulo opcional encima (para que NO parezca stock crudo)
const withTag = (node: React.ReactNode, shot: Shot, i: number) => (
  <>
    {node}
    {shot.key ? <KeywordTag text={shot.key} i={i} /> : null}
  </>
);

const CellView: React.FC<{ shot: Shot; sub: number; index: number; mode?: Mode }> = ({ shot, sub, index, mode }) => {
  switch (shot.kind) {
    case "image":
      if (!shot.file) return <FallbackCard text={shot.text} />;   // nunca vacio
      // foto real de entidad -> tarjeta premium con rotulo; imagen IA -> clip a pantalla completa con movimiento
      return shot.source === "FOTO"
        ? <ImageCard file={shot.file} label={shot.label} i={sub} />
        : withTag(<AiClip file={shot.file} i={sub} mode={mode} />, shot, index);
    case "broll":
      return shot.file ? withTag(<ClipCard file={shot.file} startFrom={sub * MAX_CELL} mode={mode} />, shot, index) : <FallbackCard text={shot.text} />;
    case "map":
      return shot.from && shot.to
        ? <MapRoute from={shot.from} to={shot.to} label={shot.label} straight={shot.straight} bow={shot.bow} />
        : <FallbackCard text={shot.text} />;
    case "annotate":
      return shot.file
        ? <Annotate file={shot.file} callouts={shot.callouts || []} label={shot.label} />
        : <FallbackCard text={shot.text} />;
    case "compare":
      return (typeof shot.a === "number" && typeof shot.b === "number")
        ? <Compare a={shot.a} b={shot.b} alabel={shot.alabel || ""} blabel={shot.blabel || ""} unit={shot.unit} label={shot.label} color={shot.color} />
        : <FallbackCard text={shot.text} />;
    case "timeline":
      return (shot.events && shot.events.length)
        ? <Timeline events={shot.events} label={shot.label} />
        : <FallbackCard text={shot.text} />;
    case "stat":
      return <StatCard value={shot.value || 0} suffix={shot.suffix} label={shot.label} color={shot.color} />;
    case "fact":
      return <KeyPhrase text={shot.body || shot.text} />;
    case "outro":
      return <Outro />;
    default:
      return null;
  }
};

// ---------- transicion entre escenas: barrido de luz + whoosh en los cambios notables ----------
const GRAPHIC_KINDS = new Set(["map", "annotate", "stat", "fact", "image", "compare", "timeline"]);
const TransitionFX: React.FC<{ index: number; kind: string; dur: number; sweep?: boolean }> = ({ index, kind, dur, sweep = true }) => {
  const frame = useCurrentFrame();
  const { width } = useVideoConfig();
  const notable = GRAPHIC_KINDS.has(kind) || index % 3 === 0;   // whoosh en escenas graficas y de vez en cuando
  const whoosh = index % 2 === 0 ? "whoosh1.mp3" : "whoosh2.mp3";
  const p = interpolate(frame, [0, 11], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const x = interpolate(p, [0, 1], [-0.55, 1.55]) * width;
  const op = interpolate(frame, [0, 3, 11], [0, 0.55, 0], { extrapolateRight: "clamp" });
  return (
    <>
      {notable && dur > 22 ? <Audio src={staticFile(whoosh)} volume={GRAPHIC_KINDS.has(kind) ? 0.32 : 0.18} /> : null}
      {sweep ? (
        <AbsoluteFill style={{ overflow: "hidden", pointerEvents: "none", zIndex: 15 }}>
          <div style={{ position: "absolute", top: -40, bottom: -40, left: x, width: width * 0.22,
            background: "linear-gradient(90deg, transparent, rgba(180,220,255,0.55), transparent)",
            opacity: op, transform: "skewX(-16deg)", filter: "blur(7px)" }} />
        </AbsoluteFill>
      ) : null}
    </>
  );
};

// ---------- capa cinematografica global: vineta + grano de pelicula sutil en movimiento ----------
const NOISE =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    "<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix type='saturate' values='0'/></filter><rect width='100%' height='100%' filter='url(#n)'/></svg>"
  );
const CineLayer: React.FC = () => {
  const f = useCurrentFrame();
  const gx = (f * 7) % 120, gy = (f * 5) % 120;   // grano en leve deriva -> parece pelicula
  return (
    <AbsoluteFill style={{ pointerEvents: "none", zIndex: 18 }}>
      {/* vineta */}
      {/* (radial-gradient: mismo aspecto que el box-shadow enorme pero MUCHO mas barato de renderizar) */}
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, rgba(2,6,14,0) 52%, rgba(2,6,14,0.78) 100%)" }} />
      {/* grano: sin mix-blend-mode (el blend por frame era el mayor coste del render local) */}
      <AbsoluteFill style={{ backgroundImage: `url("${NOISE}")`, backgroundRepeat: "repeat",
        opacity: 0.035, transform: `translate(${-gx}px, ${-gy}px) scale(1.3)` }} />
    </AbsoluteFill>
  );
};

// ---------- transicion de ENTRADA por escena: la nueva se superpone a la anterior (que sigue debajo OV frames) ----------
const OV = 10;
const clampB = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const CellFx: React.FC<{ dur: number; fx: Fx; dir: number; nextOpaque: boolean; first: boolean; children: React.ReactNode }> =
  ({ dur, fx, dir, nextOpaque, first, children }) => {
    const f = useCurrentFrame();
    const p = first ? 1 : interpolate(f, [0, OV], [0, 1], { ...clampB, easing: Easing.out(Easing.cubic) });
    const q = 1 - p;
    // cola de la escena anterior: si la siguiente es opaca (pantalla completa) se queda hasta ser tapada; si no, se desvanece
    const exitO = nextOpaque ? 1 : interpolate(f, [dur, dur + OV], [1, 0], clampB);
    let st: React.CSSProperties = {};
    if (fx === "fade") st = { opacity: first ? 1 : interpolate(f, [0, 7], [0, 1], clampB) };
    else if (fx === "zoom") st = { opacity: first ? 1 : interpolate(f, [0, 4], [0, 1], clampB), transform: `scale(${1 + q * 0.3})`,
      filter: q > 0.02 ? `blur(${q * 10}px)` : undefined };
    else if (fx === "slide") st = { transform: `translateX(${dir * q * 100}%)`, filter: q > 0.02 ? `blur(${q * 6}px)` : undefined };
    else if (fx === "whip") st = { opacity: first ? 1 : interpolate(f, [0, 3], [0, 1], clampB),
      transform: `translateX(${dir * q * 38}%) scale(${1 + q * 0.08})`,
      filter: q > 0.02 ? `blur(${q * 18}px) brightness(${1 + q * 0.35})` : undefined };
    else if (fx === "wipe") {
      const x = p * 150 - 20;
      st = { clipPath: p >= 1 ? undefined : (dir > 0
        ? `polygon(0 0, ${x}% 0, ${x - 22}% 100%, 0 100%)`
        : `polygon(100% 0, ${100 - x}% 0, ${122 - x}% 100%, 100% 100%)`) };
    }
    return (
      <AbsoluteFill style={{ opacity: exitO }}>
        <AbsoluteFill style={st}>{children}</AbsoluteFill>
        {fx === "flash" && !first ? <AbsoluteFill style={{ background: "#fff", opacity: q * q * 0.8, pointerEvents: "none" }} /> : null}
      </AbsoluteFill>
    );
  };

// destello de luz calido al cambiar de seccion (tipo "light leak"), con el tono propio de cada video
const Leak: React.FC<{ hue: number }> = ({ hue }) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [0, 7, 24], [0, 0.7, 0], clampB);
  const x = interpolate(f, [0, 24], [-10, 60], clampB);
  return <AbsoluteFill style={{ pointerEvents: "none", zIndex: 16, opacity: o, mixBlendMode: "screen",
    background: `radial-gradient(ellipse at ${x}% 30%, hsla(${hue},100%,60%,0.55), transparent 55%), radial-gradient(ellipse at ${x + 35}% 80%, hsla(${hue + 30},100%,55%,0.35), transparent 50%)` }} />;
};

// ---------- plan de estilo del video (determinista por titulo) ----------
const FX_SETS: Fx[][] = [["zoom", "slide", "flash"], ["whip", "wipe", "zoom"], ["slide", "wipe", "flash", "whip"], ["zoom", "whip", "flash"]];
const HUES = [0, -30, 25, 70];
const TINTS = ["rgba(255,170,90,0.07)", "rgba(80,160,255,0.07)", "rgba(0,0,0,0)", "rgba(120,255,200,0.05)"];
const LEAK_HUES = [28, 190, 330, 45];
const isMediaShot = (s: Shot) => !!s.file && (s.kind === "broll" || (s.kind === "image" && s.source !== "FOTO"));
type CellPlan = { mode: Mode; fx: Fx; dir: number; opaque: boolean };

function planStyle(manifest: Manifest, cells: Cell[]) {
  const seed = hashStr(manifest.sections.map((s) => s.title).join("|"));
  const r = makeRng(seed);
  const pick = <T,>(a: T[]) => a[Math.floor(r() * a.length)];
  const fxSet = pick(FX_SETS), hue = pick(HUES), tint = pick(TINTS), leakHue = pick(LEAK_HUES);
  const plans: CellPlan[] = [];
  let lastFx: Fx = "fade", lastModes: Mode[] = [];
  cells.forEach((c, i) => {
    let mode: Mode = "card";
    if (isMediaShot(c.shot)) {
      const u = r();
      mode = i < 4 ? "bleed" : u < 0.52 ? "bleed" : u < 0.82 ? "card" : "wide";   // el arranque siempre a pantalla completa
      const n = lastModes.length;
      if (n >= 2 && lastModes[n - 1] === mode && lastModes[n - 2] === mode) mode = mode === "bleed" ? "card" : "bleed";   // no 3 iguales seguidas
      lastModes.push(mode);
    }
    let fx: Fx = "fade";
    if (isMediaShot(c.shot) && i > 0) {
      fx = c.secStart ? "whip" : c.sub > 0 ? "zoom" : pick(fxSet);
      if (fx === lastFx) fx = fxSet[(fxSet.indexOf(fx) + 1) % fxSet.length];   // nunca la misma transicion dos veces seguidas
    }
    if (fx !== "fade") lastFx = fx;
    plans.push({ mode, fx, dir: r() < 0.5 ? 1 : -1, opaque: isMediaShot(c.shot) && mode === "bleed" });
  });
  return { plans, hue, tint, leakHue };
}

export const Auto: React.FC<{ manifest: Manifest; media: Media }> = ({ manifest, media }) => {
  const fps = manifest.fps || 30;
  const totalFrames = Math.ceil(manifest.total_duration * fps);
  const cells = buildCells(manifest, media);
  const plan = planStyle(manifest, cells);
  return (
    <StyleCtx.Provider value={{ tint: plan.tint, hue: plan.hue }}>
      <AbsoluteFill style={{ backgroundColor: COLORS.bgBottom, fontFamily: "Montserrat, 'Segoe UI', sans-serif" }}>
        <GridBG />
        <Audio src={staticFile("narration_full.mp3")} />
        <Audio src={staticFile("music.mp3")} volume={0.03} loop />
        {cells.map((c, i) => {
          const st = plan.plans[i];
          const last = i === cells.length - 1;
          return (
            <Sequence key={i} from={c.from} durationInFrames={c.dur + (last ? 0 : OV)}>
              <CellFx dur={c.dur} fx={st.fx} dir={st.dir} nextOpaque={!last && plan.plans[i + 1].opaque} first={i === 0}>
                <CellView shot={c.shot} sub={c.sub} index={i} mode={st.mode} />
              </CellFx>
              <TransitionFX index={i} kind={c.shot.kind} dur={c.dur} sweep={st.fx === "fade" && i > 0} />
              {c.secStart && i > 0 ? <Leak hue={plan.leakHue} /> : null}
            </Sequence>
          );
        })}
        <CineLayer />
        <BrandCorner />
        <ProgressBar total={totalFrames} />
      </AbsoluteFill>
    </StyleCtx.Provider>
  );
};
