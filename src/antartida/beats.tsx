import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, spring, Easing } from "remotion";
import { COLORS } from "../theme";
import { SceneBG, AntarcticaMap, ICE } from "./lib";

const svg = (children: React.ReactNode) => (
  <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{ position: "absolute" }}>{children}</svg>
);

// ---- BEAT: número grande ----
const StatBeat: React.FC<{ value: number; suffix?: string; label: string; color?: string; decimals?: number; tint?: string }> =
({ value, suffix = "", label, color = COLORS.cyan, decimals = 0, tint }) => {
  const frame = useCurrentFrame();
  const s = spring({ frame, fps: 30, config: { damping: 16 } });
  const n = interpolate(s, [0, 1], [0, value]);
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", backgroundColor: COLORS.bgBottom }}>
      <SceneBG tint={tint} />
      <div style={{ textAlign: "center", opacity: s, transform: `scale(${0.7 + 0.3 * s})` }}>
        <div style={{ fontSize: 240, fontWeight: 900, color, lineHeight: 1, textShadow: `0 0 50px ${color}66` }}>
          {n.toFixed(decimals)}{suffix}
        </div>
        <div style={{ fontSize: 46, fontWeight: 700, color: COLORS.white, marginTop: 20 }}>{label}</div>
      </div>
    </AbsoluteFill>
  );
};

// ---- BEAT: frase con kicker ----
const FactBeat: React.FC<{ kicker: string; text: string; accent?: string; tint?: string }> =
({ kicker, text, accent = COLORS.cyan, tint }) => {
  const frame = useCurrentFrame();
  const s = spring({ frame, fps: 30, config: { damping: 16 } });
  const k = spring({ frame: frame - 4, fps: 30, config: { damping: 200 } });
  return (
    <AbsoluteFill style={{ justifyContent: "center", backgroundColor: COLORS.bgBottom }}>
      <SceneBG tint={tint} />
      <div style={{ padding: "0 150px", opacity: s }}>
        <div style={{ display: "inline-block", fontSize: 32, fontWeight: 800, color: COLORS.bgBottom,
          background: accent, padding: "8px 24px", borderRadius: 10, letterSpacing: 3,
          transform: `translateX(${(1 - k) * -40}px)` }}>{kicker}</div>
        <div style={{ fontSize: 88, fontWeight: 900, color: COLORS.white, marginTop: 30, lineHeight: 1.1,
          textShadow: "0 4px 24px rgba(0,0,0,0.6)", transform: `translateY(${(1 - s) * 30}px)` }}>{text}</div>
      </div>
    </AbsoluteFill>
  );
};

// ---- BEAT: mapa polar ----
const MapBeat: React.FC<{ planes?: boolean; rings?: boolean; danger?: boolean; caption?: string }> =
({ planes, rings, danger, caption }) => {
  const frame = useCurrentFrame();
  const s = spring({ frame, fps: 30, config: { damping: 18 } });
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bgBottom }}>
      <SceneBG />
      <div style={{ opacity: s }}>
        {svg(<AntarcticaMap cx={960} cy={540} R={360} planes={planes} rings={rings} danger={danger} label />)}
      </div>
      {caption && (
        <div style={{ position: "absolute", bottom: 90, width: "100%", textAlign: "center" }}>
          <span style={{ fontSize: 44, fontWeight: 800, color: COLORS.white, background: "rgba(5,13,28,0.7)",
            padding: "8px 26px", borderRadius: 12 }}>{caption}</span>
        </div>
      )}
    </AbsoluteFill>
  );
};

// ---- BEAT: termómetro compacto ----
const ThermoBeat: React.FC = () => {
  const frame = useCurrentFrame();
  const fill = interpolate(frame, [6, 90], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const temp = interpolate(fill, [0, 1], [20, -89.2]);
  const barTop = 250, barH = 480, barX = 900, barW = 90;
  const mercuryH = interpolate(fill, [0, 1], [0, barH]);
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bgBottom }}>
      <SceneBG tint="#0a2036" />
      {svg(<>
        <rect x={barX} y={barTop} width={barW} height={barH} rx={45} fill="#0e2340" stroke="#26456b" strokeWidth={3} />
        <rect x={barX + 10} y={barTop + (barH - mercuryH)} width={barW - 20} height={mercuryH} rx={35} fill="url(#cb)" />
        <circle cx={barX + barW / 2} cy={barTop + barH + 50} r={75} fill="url(#cb)" stroke="#26456b" strokeWidth={3} />
        <defs>
          <linearGradient id="cb" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#8bf0ff" /><stop offset="100%" stopColor="#3aa0ff" />
          </linearGradient>
        </defs>
      </>)}
      <div style={{ position: "absolute", left: 0, top: 420, width: 820, textAlign: "right", paddingRight: 40 }}>
        <div style={{ fontSize: 120, fontWeight: 900, color: "#8bf0ff" }}>{temp.toFixed(1)}°C</div>
        <div style={{ fontSize: 34, color: COLORS.dim }}>récord en la Tierra · base Vostok</div>
      </div>
    </AbsoluteFill>
  );
};

// ---- BEAT: comparativa Ártico vs Antártida ----
const CompareBeat: React.FC = () => {
  const frame = useCurrentFrame();
  const routes = [];
  for (let i = 0; i < 8; i++) {
    const a = (i * 45) * Math.PI / 180;
    const app = interpolate(frame, [10 + i * 3, 30 + i * 3], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    routes.push(<line key={i} x1={560 - Math.cos(a) * 230} y1={540 - Math.sin(a) * 230}
      x2={560 + Math.cos(a) * 230} y2={540 + Math.sin(a) * 230}
      stroke={COLORS.amber} strokeWidth={4} opacity={0.55 * app} strokeDasharray="6 8" />);
  }
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bgBottom }}>
      <SceneBG />
      {svg(<>
        <circle cx={560} cy={540} r={220} fill="#0d2038" stroke={COLORS.grid} strokeWidth={2} />
        {routes}
        <circle cx={1360} cy={540} r={220} fill="#0d2038" stroke={COLORS.grid} strokeWidth={2} />
        <circle cx={1360} cy={540} r={120} fill={ICE} stroke="#9fc0e8" strokeWidth={2} />
        <text x={1360} y={550} fill="#20456f" fontSize={30} fontWeight={900} textAnchor="middle">VACÍO</text>
      </>)}
      <div style={{ position: "absolute", left: 360, top: 800, width: 400, textAlign: "center", fontSize: 46, fontWeight: 900, color: COLORS.amber }}>ÁRTICO</div>
      <div style={{ position: "absolute", left: 1160, top: 800, width: 400, textAlign: "center", fontSize: 46, fontWeight: 900, color: COLORS.cyan }}>ANTÁRTIDA</div>
    </AbsoluteFill>
  );
};

// ---- BEAT: outro de marca ----
const OutroBeat: React.FC = () => {
  const frame = useCurrentFrame();
  const s = spring({ frame, fps: 30, config: { damping: 14 } });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", backgroundColor: COLORS.bgBottom }}>
      <SceneBG />
      <div style={{ textAlign: "center", opacity: s, transform: `scale(${0.85 + 0.15 * s})` }}>
        <div style={{ fontSize: 34, color: COLORS.dim, letterSpacing: 8 }}>SUSCRÍBETE A</div>
        <div style={{ fontSize: 110, fontWeight: 900, color: COLORS.white, letterSpacing: 3 }}>
          ZONA DE <span style={{ color: COLORS.cyan }}>VUELO</span> 🛩️
        </div>
      </div>
    </AbsoluteFill>
  );
};

export type BeatSpec =
  | { t: "stat"; value: number; suffix?: string; label: string; color?: string; decimals?: number; tint?: string }
  | { t: "fact"; kicker: string; text: string; accent?: string; tint?: string }
  | { t: "map"; planes?: boolean; rings?: boolean; danger?: boolean; caption?: string }
  | { t: "thermo" }
  | { t: "compare" }
  | { t: "outro" };

export const Beat: React.FC<{ spec: BeatSpec }> = ({ spec }) => {
  switch (spec.t) {
    case "stat": return <StatBeat {...spec} />;
    case "fact": return <FactBeat {...spec} />;
    case "map": return <MapBeat {...spec} />;
    case "thermo": return <ThermoBeat />;
    case "compare": return <CompareBeat />;
    case "outro": return <OutroBeat />;
  }
};

// beats por sección (se rotan en las celdas gráficas)
export const SECTION_BEATS: Record<string, BeatSpec[]> = {
  hook: [
    { t: "map", planes: true, danger: true, caption: "Ni un solo avión" },
    { t: "fact", kicker: "MAPA EN VIVO", text: "La Antártida: un vacío absoluto en el cielo" },
    { t: "stat", value: 0, label: "aviones sobre el continente", color: COLORS.red },
  ],
  etops: [
    { t: "map", rings: true, danger: true, caption: "Sin aeropuerto de desvío" },
    { t: "stat", value: 0, label: "aeropuertos comerciales", color: COLORS.red },
    { t: "fact", kicker: "REGLA ETOPS", text: "Un bimotor debe alcanzar un desvío con un solo motor" },
    { t: "stat", value: 370, suffix: " min", label: "máximo con un motor… y no basta", color: COLORS.amber },
  ],
  frio: [
    { t: "thermo" },
    { t: "stat", value: -89.2, decimals: 1, suffix: "°C", label: "récord en la Tierra", color: "#8bf0ff", tint: "#0a2036" },
    { t: "fact", kicker: "COMBUSTIBLE", text: "El queroseno se congela a −47 °C", accent: COLORS.amber, tint: "#0a2036" },
    { t: "fact", kicker: "SUPERVIVENCIA", text: "A la intemperie, el frío mata en minutos", accent: COLORS.red, tint: "#0a2036" },
  ],
  infraestructura: [
    { t: "fact", kicker: "SIN COMUNICACIONES", text: "Los satélites apenas alcanzan el polo" },
    { t: "fact", kicker: "SIN NAVEGACIÓN", text: "La brújula magnética se vuelve loca", accent: COLORS.amber },
    { t: "fact", kicker: "SIN METEOROLOGÍA", text: "Volar a ciegas, sin datos del tiempo", accent: "#9be08a" },
    { t: "stat", value: 0, label: "servicios de tierra disponibles", color: COLORS.red },
  ],
  excepciones: [
    { t: "fact", kicker: "TURÍSTICOS", text: "Sobrevuelos en Boeing 787, sin aterrizar" },
    { t: "fact", kicker: "MILITARES", text: "C-130 con esquís sobre pistas de hielo", accent: COLORS.amber },
    { t: "fact", kicker: "RUTAS QUE ROZAN", text: "Se acercan al borde, pero no entran", accent: "#9be08a" },
  ],
  geografia: [
    { t: "compare" },
    { t: "stat", value: 90, suffix: "%", label: "de la población vive en el norte", color: COLORS.amber },
    { t: "fact", kicker: "EL FACTOR OCULTO", text: "Casi ninguna ruta tiene su camino por allí", accent: "#9be08a" },
  ],
  cierre: [
    { t: "fact", kicker: "EN RESUMEN", text: "Cuatro barreras que crean un vacío" },
    { t: "stat", value: 4, label: "razones insalvables", color: COLORS.cyan },
    { t: "outro" },
  ],
};
