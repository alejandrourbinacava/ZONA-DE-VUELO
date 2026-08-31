import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig, interpolate, spring, Easing } from "remotion";
import { COLORS } from "../theme";

const EASE = { easing: Easing.inOut(Easing.ease) } as const;

// ---------- helpers de proyeccion equirectangular ----------
type Pt = { name?: string; lat: number; lon: number };
const uOf = (lon: number) => (lon + 180) / 360;   // 0..1 (oeste->este)
const vOf = (lat: number) => (90 - lat) / 180;     // 0..1 (norte->sur)

// ============================================================
//  MAPA CON RUTA ANIMADA (arco tipo circulo maximo + avion)
// ============================================================
export const MapRoute: React.FC<{ from: Pt; to: Pt; label?: string }> = ({ from, to, label }) => {
  const frame = useCurrentFrame();
  const { durationInFrames, width, height } = useVideoConfig();
  const enter = spring({ frame, fps: 30, config: { damping: 200, stiffness: 90 } });

  const uA = uOf(from.lon), vA = vOf(from.lat), uB = uOf(to.lon), vB = vOf(to.lat);
  const cU = (uA + uB) / 2, cV = (vA + vB) / 2;
  const spanU = Math.max(Math.abs(uA - uB), 0.02);
  const spanV = Math.max(Math.abs(vA - vB), 0.02);

  // ancho del mapa (px) para que la ruta ocupe ~55% del cuadro; el mapa es 2:1
  const forX = (0.5 * width) / spanU;
  const forY = (0.5 * height) / (spanV / 2);
  const baseW = Math.min(Math.max(Math.min(forX, forY), width), 6200);
  const zoom = interpolate(frame, [0, durationInFrames], [1, 1.1], EASE);   // push-in suave
  const mapW = baseW * zoom;
  const mapH = mapW / 2;
  const mapLeft = width / 2 - cU * mapW;
  const mapTop = height / 2 - cV * mapH;

  const P = (u: number, v: number) => ({ x: mapLeft + u * mapW, y: mapTop + v * mapH });
  const A = P(uA, vA), B = P(uB, vB);
  // punto de control: arquea hacia el polo mas cercano (circulo maximo aproximado)
  const northern = (from.lat + to.lat) / 2 >= 0;
  const bowV = cV + (northern ? -1 : 1) * 0.42 * Math.abs(uA - uB);
  const C = P(cU, bowV);

  // progreso del trazado del arco y del avion
  const draw = interpolate(frame, [8, durationInFrames * 0.85], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", ...EASE });
  const bez = (t: number) => ({
    x: (1 - t) * (1 - t) * A.x + 2 * (1 - t) * t * C.x + t * t * B.x,
    y: (1 - t) * (1 - t) * A.y + 2 * (1 - t) * t * C.y + t * t * B.y,
  });
  const plane = bez(Math.max(0.001, draw));
  const planePrev = bez(Math.max(0, draw - 0.02));
  const ang = (Math.atan2(plane.y - planePrev.y, plane.x - planePrev.x) * 180) / Math.PI;

  const pathLen = 4000;   // aprox para dashoffset
  const dot = (p: { x: number; y: number }, c: string) => (
    <>
      <circle cx={p.x} cy={p.y} r={13} fill="none" stroke={c} strokeWidth={3} opacity={0.5} />
      <circle cx={p.x} cy={p.y} r={6} fill={c} />
    </>
  );
  const cityLabel = (p: { x: number; y: number }, name?: string, delay = 0) => {
    if (!name) return null;
    const o = interpolate(frame, [delay, delay + 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    return (
      <g opacity={o} transform={`translate(${p.x + 16}, ${p.y - 14})`}>
        <text x={0} y={0} fontSize={34} fontWeight={800} fill="#fff"
          style={{ paintOrder: "stroke", stroke: "rgba(3,8,18,0.9)", strokeWidth: 6 }}>{name}</text>
      </g>
    );
  };

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bgBottom, overflow: "hidden", opacity: enter }}>
      <Img src={staticFile("worldmap.jpg")} style={{ position: "absolute", left: mapLeft, top: mapTop, width: mapW, height: mapH, filter: "brightness(0.6) saturate(1.1) contrast(1.05)" }} />
      <AbsoluteFill style={{ background: `radial-gradient(circle at ${(A.x + B.x) / 2}px ${(A.y + B.y) / 2}px, rgba(5,12,26,0.15) 30%, rgba(4,9,20,0.8) 90%)` }} />
      <svg width={width} height={height} style={{ position: "absolute", inset: 0 }}>
        <path d={`M ${A.x} ${A.y} Q ${C.x} ${C.y} ${B.x} ${B.y}`} fill="none"
          stroke={COLORS.cyan} strokeWidth={5} strokeLinecap="round"
          strokeDasharray={pathLen} strokeDashoffset={pathLen * (1 - draw)}
          style={{ filter: `drop-shadow(0 0 8px ${COLORS.cyan})` }} />
        {dot(A, COLORS.cyan)}
        {draw > 0.98 ? dot(B, COLORS.amber) : null}
        <g transform={`translate(${plane.x}, ${plane.y}) rotate(${ang})`}>
          <text x={0} y={0} fontSize={44} textAnchor="middle" dominantBaseline="central"
            style={{ filter: "drop-shadow(0 2px 6px rgba(0,0,0,0.8))" }}>✈️</text>
        </g>
        {cityLabel(A, from.name, 8)}
        {cityLabel(B, to.name, Math.round(durationInFrames * 0.7))}
      </svg>
      {label ? (
        <div style={{ position: "absolute", left: 60, bottom: 54, borderLeft: `6px solid ${COLORS.cyan}`, paddingLeft: 16, opacity: enter }}>
          <div style={{ fontSize: 34, fontWeight: 800, color: "#fff", textShadow: "0 3px 14px rgba(0,0,0,0.9)" }}>{label}</div>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// ============================================================
//  EXPLICADOR ANOTADO: imagen con zoom + flechas + textos que entran
// ============================================================
type Callout = { label: string; x?: number; y?: number };   // x,y = fraccion 0..1 (donde ESTA la parte)

export const Annotate: React.FC<{ file: string; callouts: Callout[]; label?: string }> = ({ file, callouts, label }) => {
  const frame = useCurrentFrame();
  const { durationInFrames, width, height } = useVideoConfig();
  const enter = spring({ frame, fps: 30, config: { damping: 18, stiffness: 130 } });
  const cs = (callouts || []).filter((c) => typeof c.x === "number" && typeof c.y === "number").slice(0, 4);

  // zoom SINCRONIZADO con la imagen (escala respecto al centro) para que las flechas no se despeguen
  const s = interpolate(frame, [0, durationInFrames], [1.05, 1.16], EASE);
  const cxpx = width / 2, cypx = height / 2;
  const mapPt = (fx: number, fy: number) => ({ x: cxpx + (fx * width - cxpx) * s, y: cypx + (fy * height - cypx) * s });

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bgBottom, overflow: "hidden" }}>
      <AbsoluteFill style={{ opacity: enter }}>
        <Img src={staticFile(file)} style={{ width: "100%", height: "100%", objectFit: "cover",
          transform: `scale(${s})`, transformOrigin: "50% 50%" }} />
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(4,9,20,0.4) 0%, transparent 28%, transparent 62%, rgba(4,9,20,0.65) 100%)" }} />
      <svg width={width} height={height} style={{ position: "absolute", inset: 0 }}>
        {cs.map((c, i) => {
          const p = mapPt(c.x as number, c.y as number);
          const fromLeft = (c.x as number) < 0.5;
          const lx = fromLeft ? Math.max(60, p.x - 230) : Math.min(width - 60, p.x + 230);
          const ly = Math.max(70, Math.min(height - 90, p.y - 56));
          const delay = 10 + i * Math.max(14, Math.round((durationInFrames - 24) / (cs.length + 1)));
          const app = interpolate(frame, [delay, delay + 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const grow = interpolate(frame, [delay, delay + 15], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", ...EASE });
          const ex = lx + (p.x - lx) * grow, ey = ly + (p.y - ly) * grow;
          return (
            <g key={i} opacity={app}>
              <circle cx={p.x} cy={p.y} r={15} fill="none" stroke={COLORS.cyan} strokeWidth={2.5} opacity={grow * 0.8} />
              <circle cx={p.x} cy={p.y} r={4} fill={COLORS.cyan} opacity={grow} />
              <line x1={lx} y1={ly} x2={ex} y2={ey} stroke={COLORS.cyan} strokeWidth={3}
                style={{ filter: `drop-shadow(0 0 5px ${COLORS.cyan})` }} />
              <text x={lx} y={ly - 14} fontSize={38} fontWeight={800} fill="#fff"
                textAnchor={fromLeft ? "start" : "end"}
                style={{ paintOrder: "stroke", stroke: "rgba(3,8,18,0.92)", strokeWidth: 7 }}>{c.label}</text>
            </g>
          );
        })}
      </svg>
      {label ? (
        <div style={{ position: "absolute", left: 60, bottom: 48 }}>
          <div style={{ fontSize: 30, letterSpacing: 4, color: COLORS.cyan, fontWeight: 800 }}>{label}</div>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
