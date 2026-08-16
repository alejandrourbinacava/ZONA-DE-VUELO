import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Easing,
} from "remotion";
import { COLORS } from "./theme";

// ---------- Fondo con gradiente + rejilla tipo mapa ----------
export const MapBackground: React.FC = () => {
  const frame = useCurrentFrame();
  const drift = interpolate(frame, [0, 300], [0, -40]);
  const lines = [];
  for (let i = -1; i <= 20; i++) {
    lines.push(
      <line
        key={`v${i}`}
        x1={i * 110 + drift}
        y1={0}
        x2={i * 110 + drift}
        y2={1080}
        stroke={COLORS.grid}
        strokeWidth={1.5}
      />
    );
  }
  for (let j = 0; j <= 11; j++) {
    lines.push(
      <line
        key={`h${j}`}
        x1={0}
        y1={j * 110}
        x2={1920}
        y2={j * 110}
        stroke={COLORS.grid}
        strokeWidth={1.5}
      />
    );
  }
  return (
    <AbsoluteFill>
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at 42% 40%, ${COLORS.bgTop} 0%, ${COLORS.bgBottom} 75%)`,
        }}
      />
      <svg width={1920} height={1080} style={{ position: "absolute" }}>
        {lines}
      </svg>
    </AbsoluteFill>
  );
};

// ---------- Bezier cuadratica: punto y angulo en t ----------
const P0 = { x: 430, y: 760 }; // Delhi (abajo-izq)
const C = { x: 980, y: 1030 }; // control: desvia por el SUR
const P1 = { x: 1520, y: 560 }; // Chengdu (der)
const bez = (t: number) => ({
  x: (1 - t) ** 2 * P0.x + 2 * (1 - t) * t * C.x + t ** 2 * P1.x,
  y: (1 - t) ** 2 * P0.y + 2 * (1 - t) * t * C.y + t ** 2 * P1.y,
});
const bezAngle = (t: number) => {
  const dx = 2 * (1 - t) * (C.x - P0.x) + 2 * t * (P1.x - C.x);
  const dy = 2 * (1 - t) * (C.y - P0.y) + 2 * t * (P1.y - C.y);
  return (Math.atan2(dy, dx) * 180) / Math.PI;
};

// ---------- La meseta (zona prohibida) ----------
const Plateau: React.FC = () => {
  const frame = useCurrentFrame();
  const appear = spring({ frame: frame - 15, fps: 30, config: { damping: 200 } });
  const pulse = 0.5 + 0.5 * Math.sin(frame / 12);
  const shape =
    "M 720 300 L 980 250 L 1240 300 L 1360 430 L 1300 600 L 1080 690 L 820 660 L 690 520 Z";
  return (
    <g style={{ opacity: appear }}>
      <defs>
        <radialGradient id="plat" cx="50%" cy="45%" r="65%">
          <stop offset="0%" stopColor="#5a3a12" />
          <stop offset="60%" stopColor="#3a2a12" />
          <stop offset="100%" stopColor="#241a10" />
        </radialGradient>
      </defs>
      <path d={shape} fill="url(#plat)" stroke={COLORS.amber} strokeWidth={2} />
      {/* curvas de nivel */}
      {[0.82, 0.62, 0.42, 0.24].map((s, i) => (
        <path
          key={i}
          d={shape}
          fill="none"
          stroke={COLORS.amberSoft}
          strokeOpacity={0.25}
          strokeWidth={1.5}
          transform={`translate(${1025 - 1025 * s}, ${470 - 470 * s}) scale(${s})`}
        />
      ))}
      {/* borde no-fly punteado que pulsa */}
      <path
        d={shape}
        fill="none"
        stroke={COLORS.red}
        strokeWidth={3}
        strokeDasharray="14 12"
        strokeOpacity={0.4 + 0.5 * pulse}
        transform="translate(1025,470) scale(1.12) translate(-1025,-470)"
      />
      <text
        x={1025}
        y={455}
        fill={COLORS.amberSoft}
        fontSize={34}
        fontWeight={800}
        textAnchor="middle"
        style={{ letterSpacing: 2 }}
      >
        MESETA DEL TÍBET
      </text>
      <text
        x={1025}
        y={498}
        fill={COLORS.white}
        fontSize={26}
        fontWeight={600}
        textAnchor="middle"
        opacity={0.85}
      >
        Altitud media ~4.500 m
      </text>
    </g>
  );
};

// ---------- Aeropuerto (punto + etiqueta) ----------
const City: React.FC<{ x: number; y: number; label: string; delay: number }> = ({
  x,
  y,
  label,
  delay,
}) => {
  const frame = useCurrentFrame();
  const s = spring({ frame: frame - delay, fps: 30, config: { damping: 12 } });
  const ring = interpolate(frame % 60, [0, 60], [8, 34]);
  const ringO = interpolate(frame % 60, [0, 60], [0.6, 0]);
  return (
    <g style={{ opacity: s }}>
      <circle cx={x} cy={y} r={ring} fill="none" stroke={COLORS.cyan} strokeOpacity={ringO} strokeWidth={2} />
      <circle cx={x} cy={y} r={9} fill={COLORS.cyan} />
      <circle cx={x} cy={y} r={4} fill={COLORS.white} />
      <text x={x} y={y + 42} fill={COLORS.white} fontSize={26} fontWeight={700} textAnchor="middle">
        {label}
      </text>
    </g>
  );
};

// ---------- Ruta directa TACHADA (por que no se puede) ----------
const DirectRoute: React.FC = () => {
  const frame = useCurrentFrame();
  const show = interpolate(frame, [70, 90], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const cross = interpolate(frame, [110, 130], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <g style={{ opacity: show }}>
      <line x1={P0.x} y1={P0.y} x2={P1.x} y2={P1.y} stroke={COLORS.red} strokeWidth={4} strokeDasharray="12 10" opacity={0.85} />
      <g transform="translate(950,560)" style={{ opacity: cross }}>
        <circle r={26} fill={COLORS.red} />
        <line x1={-11} y1={-11} x2={11} y2={11} stroke="#fff" strokeWidth={4} />
        <line x1={11} y1={-11} x2={-11} y2={11} stroke="#fff" strokeWidth={4} />
      </g>
    </g>
  );
};

// ---------- Ruta curva (desvio) + avion en movimiento ----------
const DetourRoute: React.FC = () => {
  const frame = useCurrentFrame();
  const draw = interpolate(frame, [135, 200], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const t = interpolate(frame, [150, 260], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const p = bez(t);
  const ang = bezAngle(t);
  const d = `M ${P0.x} ${P0.y} Q ${C.x} ${C.y} ${P1.x} ${P1.y}`;
  return (
    <g>
      <path
        d={d}
        fill="none"
        stroke={COLORS.cyan}
        strokeWidth={5}
        strokeLinecap="round"
        pathLength={1}
        strokeDasharray={1}
        strokeDashoffset={1 - draw}
        style={{ filter: `drop-shadow(0 0 8px ${COLORS.cyan})` }}
      />
      {t > 0 && t < 1 && (
        <g transform={`translate(${p.x}, ${p.y}) rotate(${ang})`}>
          <text fontSize={44} textAnchor="middle" dominantBaseline="central">
            ✈️
          </text>
        </g>
      )}
    </g>
  );
};

// ---------- Tarjeta de dato (callout) ----------
const StatCard: React.FC = () => {
  const frame = useCurrentFrame();
  const s = spring({ frame: frame - 205, fps: 30, config: { damping: 14 } });
  const x = interpolate(s, [0, 1], [420, 0]);
  return (
    <div
      style={{
        position: "absolute",
        top: 70,
        right: 70,
        width: 560,
        transform: `translateX(${x}px)`,
        opacity: s,
        background: "rgba(9,25,48,0.92)",
        border: `2px solid ${COLORS.red}`,
        borderRadius: 18,
        padding: "28px 32px",
        boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
      }}
    >
      <div style={{ color: COLORS.red, fontWeight: 800, fontSize: 26, letterSpacing: 2 }}>
        ⚠ DESCOMPRESIÓN
      </div>
      <div style={{ color: COLORS.white, fontSize: 30, fontWeight: 600, marginTop: 12, lineHeight: 1.35 }}>
        Ante una fuga de presión hay que <b style={{ color: COLORS.amberSoft }}>descender a 3.000 m en menos de 10 min</b>.
      </div>
      <div style={{ color: COLORS.dim, fontSize: 26, marginTop: 12 }}>
        Sobre el Tíbet, el suelo ya está a <b style={{ color: COLORS.red }}>4.500 m</b>. No hay a dónde bajar.
      </div>
    </div>
  );
};

// ---------- Subtitulos cineticos ----------
const WORDS = [
  { w: "NINGÚN", hl: true },
  { w: "avión", hl: false },
  { w: "sobrevuela", hl: false },
  { w: "el", hl: false },
  { w: "TÍBET", hl: true },
  { w: "—", hl: false },
  { w: "y", hl: false },
  { w: "la", hl: false },
  { w: "razón", hl: false },
  { w: "es", hl: false },
  { w: "el", hl: false },
  { w: "OXÍGENO", hl: true },
];
const KineticSubs: React.FC = () => {
  const frame = useCurrentFrame();
  const start = 60;
  const per = 14;
  return (
    <div
      style={{
        position: "absolute",
        bottom: 70,
        width: "100%",
        display: "flex",
        justifyContent: "center",
        gap: 16,
        flexWrap: "wrap",
        padding: "0 120px",
      }}
    >
      {WORDS.map((it, i) => {
        const appear = spring({ frame: frame - (start + i * per), fps: 30, config: { damping: 200 } });
        const pop = spring({ frame: frame - (start + i * per), fps: 30, config: { damping: 10, stiffness: 180 } });
        return (
          <span
            key={i}
            style={{
              opacity: appear,
              transform: `translateY(${(1 - appear) * 30}px) scale(${0.8 + pop * 0.2})`,
              fontSize: 52,
              fontWeight: 800,
              color: it.hl ? COLORS.bgBottom : COLORS.white,
              background: it.hl ? COLORS.cyan : "transparent",
              padding: it.hl ? "2px 16px" : "2px 0",
              borderRadius: 10,
              textShadow: it.hl ? "none" : "0 3px 12px rgba(0,0,0,0.8)",
            }}
          >
            {it.w}
          </span>
        );
      })}
    </div>
  );
};

// ---------- Logo/marca en esquina ----------
const CornerBrand: React.FC = () => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [45, 65], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{ position: "absolute", top: 54, left: 70, opacity: o, display: "flex", alignItems: "center", gap: 14 }}>
      <div style={{ fontSize: 40 }}>🛩️</div>
      <div style={{ fontWeight: 900, fontSize: 30, color: COLORS.white, letterSpacing: 2 }}>
        ZONA DE <span style={{ color: COLORS.cyan }}>VUELO</span>
      </div>
    </div>
  );
};

// ---------- Intro sting ----------
const IntroSting: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 14 } });
  const planeX = interpolate(frame, [0, 55], [-500, 2400], { easing: Easing.inOut(Easing.ease) });
  const out = interpolate(frame, [45, 58], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", opacity: out }}>
      <div style={{ position: "absolute", left: planeX, top: 430, fontSize: 90 }}>✈️</div>
      <div
        style={{
          fontWeight: 900,
          fontSize: 130,
          color: COLORS.white,
          letterSpacing: 6,
          transform: `scale(${0.6 + s * 0.4})`,
          opacity: s,
          textShadow: "0 10px 40px rgba(0,0,0,0.6)",
        }}
      >
        ZONA DE <span style={{ color: COLORS.cyan }}>VUELO</span>
      </div>
      <div style={{ marginTop: 20, fontSize: 40, color: COLORS.dim, opacity: s, letterSpacing: 8 }}>
        CURIOSIDADES DE AVIACIÓN
      </div>
    </AbsoluteFill>
  );
};

// ---------- Escena completa ----------
export const TibetScene: React.FC = () => {
  const frame = useCurrentFrame();
  const mapIn = interpolate(frame, [38, 58], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ fontFamily: "Montserrat, 'Segoe UI', sans-serif", backgroundColor: COLORS.bgBottom }}>
      <MapBackground />
      <AbsoluteFill style={{ opacity: mapIn }}>
        <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{ position: "absolute" }}>
          <Plateau />
          <DirectRoute />
          <DetourRoute />
          <City x={P0.x} y={P0.y} label="DELHI" delay={45} />
          <City x={P1.x} y={P1.y} label="CHENGDU" delay={55} />
        </svg>
        <CornerBrand />
        <StatCard />
        <KineticSubs />
      </AbsoluteFill>
      {frame < 60 && <IntroSting />}
    </AbsoluteFill>
  );
};
