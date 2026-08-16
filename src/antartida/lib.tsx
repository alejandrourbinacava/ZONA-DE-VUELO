import React from "react";
import { useCurrentFrame, interpolate, spring, Easing } from "remotion";
import { COLORS } from "../theme";

export const ICE = "#eaf3ff";
export const ICE_DIM = "#c3d6ef";

// ---------------- Fondo base con viñeta + rejilla sutil ----------------
export const SceneBG: React.FC<{ tint?: string }> = ({ tint = COLORS.bgTop }) => (
  <div
    style={{
      position: "absolute",
      inset: 0,
      background: `radial-gradient(circle at 50% 42%, ${tint} 0%, ${COLORS.bgBottom} 78%)`,
    }}
  />
);

// ---------------- Mapa polar de la Antártida ----------------
type MapProps = {
  cx?: number;
  cy?: number;
  R?: number;
  planes?: boolean;
  rings?: boolean;      // anillos de alcance ETOPS en el borde
  danger?: boolean;     // pulso rojo "sin aeropuertos" en el centro
  label?: boolean;
  scale?: number;
};

// contorno estilizado del continente (coordenadas unitarias respecto al centro)
const CONT: [number, number][] = [
  [0.0, -0.52], [0.20, -0.46], [0.34, -0.30], [0.52, -0.26], [0.50, -0.05],
  [0.40, 0.14], [0.46, 0.30], [0.28, 0.40], [0.10, 0.36], [-0.06, 0.50],
  [-0.26, 0.42], [-0.34, 0.24], [-0.52, 0.16], [-0.46, -0.06], [-0.40, -0.24],
  [-0.22, -0.34], [-0.16, -0.48],
];

export const AntarcticaMap: React.FC<MapProps> = ({
  cx = 960, cy = 560, R = 380, planes = false, rings = false,
  danger = false, label = false, scale = 1,
}) => {
  const frame = useCurrentFrame();
  const rot = frame * 0.15; // rotacion lenta del enjambre
  const contPath =
    "M " +
    CONT.map(([x, y]) => `${(cx + x * R).toFixed(1)} ${(cy + y * R).toFixed(1)}`).join(" L ") +
    " Z";

  // enjambre de aviones en el anillo oceanico (nunca en el centro)
  const N = 26;
  const swarm = [];
  if (planes) {
    for (let i = 0; i < N; i++) {
      const ang = (i * 137.5 + rot) * (Math.PI / 180);
      const rad = R * (0.66 + ((i * 7) % 5) * 0.075);
      const px = cx + Math.cos(ang) * rad;
      const py = cy + Math.sin(ang) * rad;
      const appear = interpolate(frame, [10 + i, 30 + i], [0, 1], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      });
      swarm.push(
        <circle key={i} cx={px} cy={py} r={5} fill={COLORS.amber}
          opacity={appear} style={{ filter: `drop-shadow(0 0 5px ${COLORS.amber})` }} />
      );
    }
  }

  // anillos de alcance desde 3 aeropuertos del borde
  const ringPts = [
    { a: -60, r: 1.02, name: "USHUAIA" },
    { a: 70, r: 1.02, name: "CIUDAD DEL CABO" },
    { a: 175, r: 1.02, name: "NUEVA ZELANDA" },
  ];

  return (
    <g transform={`translate(${cx} ${cy}) scale(${scale}) translate(${-cx} ${-cy})`}>
      {/* oceano */}
      <circle cx={cx} cy={cy} r={R * 1.12} fill="#081a33" stroke={COLORS.grid} strokeWidth={2} />
      {/* graticula */}
      {[0.35, 0.62, 0.9, 1.12].map((s, i) => (
        <circle key={i} cx={cx} cy={cy} r={R * s} fill="none" stroke={COLORS.grid} strokeWidth={1.4} />
      ))}
      {[0, 30, 60, 90, 120, 150].map((deg, i) => {
        const a = (deg * Math.PI) / 180;
        return (
          <line key={i}
            x1={cx - Math.cos(a) * R * 1.12} y1={cy - Math.sin(a) * R * 1.12}
            x2={cx + Math.cos(a) * R * 1.12} y2={cy + Math.sin(a) * R * 1.12}
            stroke={COLORS.grid} strokeWidth={1.2} />
        );
      })}
      {/* continente */}
      <defs>
        <radialGradient id="ice" cx="50%" cy="42%" r="60%">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="70%" stopColor={ICE} />
          <stop offset="100%" stopColor={ICE_DIM} />
        </radialGradient>
      </defs>
      <path d={contPath} fill="url(#ice)" stroke="#9fc0e8" strokeWidth={2}
        style={{ filter: "drop-shadow(0 6px 22px rgba(120,180,255,0.25))" }} />

      {rings && ringPts.map((p, i) => {
        const a = (p.a * Math.PI) / 180;
        const ax = cx + Math.cos(a) * R * p.r;
        const ay = cy + Math.sin(a) * R * p.r;
        const grow = spring({ frame: frame - 20 - i * 12, fps: 30, config: { damping: 200 } });
        return (
          <g key={i}>
            <circle cx={ax} cy={ay} r={R * 0.5 * grow} fill={COLORS.cyan} fillOpacity={0.07}
              stroke={COLORS.cyan} strokeOpacity={0.5} strokeWidth={2} strokeDasharray="8 8" />
            <circle cx={ax} cy={ay} r={7} fill={COLORS.cyan} />
            <text x={ax} y={ay - 16} fill={COLORS.cyanSoft} fontSize={20} fontWeight={700}
              textAnchor="middle">{p.name}</text>
          </g>
        );
      })}

      {swarm}

      {danger && (() => {
        const pulse = 0.5 + 0.5 * Math.sin(frame / 9);
        return (
          <g>
            <circle cx={cx} cy={cy} r={R * (0.34 + 0.05 * pulse)} fill="none"
              stroke={COLORS.red} strokeWidth={3} strokeDasharray="10 10"
              opacity={0.4 + 0.4 * pulse} />
            <circle cx={cx} cy={cy} r={30} fill={COLORS.red} opacity={0.9} />
            <text x={cx} y={cy + 9} fill="#fff" fontSize={30} fontWeight={900} textAnchor="middle">✕</text>
          </g>
        );
      })()}

      {label && (
        <text x={cx} y={cy - R * 0.02} fill="#20456f" fontSize={30} fontWeight={900}
          textAnchor="middle" style={{ letterSpacing: 3 }}>ANTÁRTIDA</text>
      )}
    </g>
  );
};

// ---------------- Tarjeta informativa que entra deslizando ----------------
export const Card: React.FC<{
  x: number; y: number; w?: number; delay?: number; accent?: string;
  from?: "left" | "right" | "up"; children: React.ReactNode;
}> = ({ x, y, w = 560, delay = 0, accent = COLORS.cyan, from = "right", children }) => {
  const frame = useCurrentFrame();
  const s = spring({ frame: frame - delay, fps: 30, config: { damping: 15 } });
  const dx = from === "right" ? 500 : from === "left" ? -500 : 0;
  const dy = from === "up" ? 400 : 0;
  return (
    <div style={{
      position: "absolute", left: x, top: y, width: w,
      transform: `translate(${dx * (1 - s)}px, ${dy * (1 - s)}px)`, opacity: s,
      background: "rgba(9,25,48,0.92)", border: `2px solid ${accent}`,
      borderRadius: 18, padding: "26px 30px", boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
    }}>{children}</div>
  );
};

// ---------------- Numero grande animado ----------------
export const StatBig: React.FC<{
  x: number; y: number; value: number; suffix?: string; label: string;
  delay?: number; color?: string; decimals?: number;
}> = ({ x, y, value, suffix = "", label, delay = 0, color = COLORS.cyan, decimals = 0 }) => {
  const frame = useCurrentFrame();
  const s = spring({ frame: frame - delay, fps: 30, config: { damping: 18 } });
  const n = interpolate(s, [0, 1], [0, value]);
  return (
    <div style={{ position: "absolute", left: x, top: y, textAlign: "center", opacity: s,
      transform: `scale(${0.7 + 0.3 * s})` }}>
      <div style={{ fontSize: 130, fontWeight: 900, color, lineHeight: 1,
        textShadow: `0 0 30px ${color}55` }}>
        {n.toFixed(decimals)}{suffix}
      </div>
      <div style={{ fontSize: 30, fontWeight: 600, color: COLORS.dim, marginTop: 10 }}>{label}</div>
    </div>
  );
};

// ---------------- Item de lista con check/cross ----------------
export const Bullet: React.FC<{
  x: number; y: number; delay: number; icon?: string; text: string; color?: string; w?: number;
}> = ({ x, y, delay, icon = "✓", text, color = COLORS.cyan, w = 700 }) => {
  const frame = useCurrentFrame();
  const s = spring({ frame: frame - delay, fps: 30, config: { damping: 16 } });
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, display: "flex",
      alignItems: "center", gap: 20, opacity: s, transform: `translateX(${(1 - s) * 40}px)` }}>
      <div style={{ minWidth: 52, height: 52, borderRadius: 12, background: color,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 30, fontWeight: 900, color: COLORS.bgBottom }}>{icon}</div>
      <div style={{ fontSize: 34, fontWeight: 600, color: COLORS.white }}>{text}</div>
    </div>
  );
};

// ---------------- Titulo de seccion (kicker + titular) ----------------
export const SectionTitle: React.FC<{ kicker: string; title: string; accent?: string }> = ({
  kicker, title, accent = COLORS.cyan,
}) => {
  const frame = useCurrentFrame();
  const s = spring({ frame, fps: 30, config: { damping: 16 } });
  return (
    <div style={{ position: "absolute", left: 90, top: 120, opacity: s,
      transform: `translateY(${(1 - s) * -30}px)` }}>
      <div style={{ fontSize: 26, fontWeight: 800, color: accent, letterSpacing: 4 }}>{kicker}</div>
      <div style={{ fontSize: 62, fontWeight: 900, color: COLORS.white, maxWidth: 1000,
        lineHeight: 1.05, marginTop: 8, textShadow: "0 4px 20px rgba(0,0,0,0.5)" }}>{title}</div>
    </div>
  );
};
