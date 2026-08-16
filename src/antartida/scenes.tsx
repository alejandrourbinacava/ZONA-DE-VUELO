import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, spring, Easing } from "remotion";
import { COLORS } from "../theme";
import { SceneBG, AntarcticaMap, Card, StatBig, Bullet, SectionTitle, ICE } from "./lib";

const svg = (children: React.ReactNode) => (
  <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{ position: "absolute" }}>{children}</svg>
);

// ---------- 1. HOOK ----------
export const Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const titleIn = spring({ frame: frame - 8, fps: 30, config: { damping: 16 } });
  const dangerIn = frame > 150;
  const big = spring({ frame: frame - 200, fps: 30, config: { damping: 14 } });
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bgBottom }}>
      <SceneBG />
      {svg(<AntarcticaMap cx={960} cy={600} R={360} planes label danger={dangerIn} />)}
      <div style={{ position: "absolute", top: 70, width: "100%", textAlign: "center",
        opacity: titleIn, transform: `translateY(${(1 - titleIn) * -30}px)` }}>
        <div style={{ fontSize: 30, fontWeight: 700, color: COLORS.amber, letterSpacing: 4 }}>
          MAPA DE VUELOS EN TIEMPO REAL
        </div>
        <div style={{ fontSize: 64, fontWeight: 900, color: COLORS.white, marginTop: 6 }}>
          El continente que <span style={{ color: COLORS.cyan }}>nadie</span> sobrevuela
        </div>
      </div>
      {frame > 200 && (
        <div style={{ position: "absolute", bottom: 210, width: "100%", textAlign: "center",
          opacity: big, transform: `scale(${0.8 + 0.2 * big})` }}>
          <span style={{ fontSize: 78, fontWeight: 900, color: "#fff",
            background: COLORS.red, padding: "6px 34px", borderRadius: 16,
            boxShadow: "0 12px 40px rgba(255,84,104,0.5)" }}>UN VACÍO ABSOLUTO</span>
        </div>
      )}
    </AbsoluteFill>
  );
};

// ---------- 2. ETOPS ----------
export const Etops: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bgBottom }}>
      <SceneBG />
      <SectionTitle kicker="RAZÓN Nº 1 · NORMATIVA ETOPS" title="No hay dónde aterrizar" />
      {svg(<AntarcticaMap cx={640} cy={640} R={300} rings danger label />)}
      <StatBig x={1180} y={300} value={0} label="aeropuertos comerciales" color={COLORS.red} />
      <Card x={1120} y={560} w={680} delay={40} accent={COLORS.cyan}>
        <div style={{ color: COLORS.cyanSoft, fontWeight: 800, fontSize: 24, letterSpacing: 2 }}>
          REGLA ETOPS
        </div>
        <div style={{ color: COLORS.white, fontSize: 28, marginTop: 10, lineHeight: 1.35 }}>
          Un bimotor debe poder llegar a un aeropuerto de desvío con <b style={{ color: COLORS.amberSoft }}>un solo motor</b> en un tiempo máximo:
        </div>
      </Card>
      <Bullet x={1160} y={758} delay={70} icon="120" text="min — certificación básica" />
      <Bullet x={1160} y={824} delay={85} icon="180" text="min — la más común" />
      <Bullet x={1160} y={890} delay={100} icon="370" text="min — la más avanzada… y aún no basta" color={COLORS.red} />
    </AbsoluteFill>
  );
};

// ---------- 3. FRÍO ----------
export const Frio: React.FC = () => {
  const frame = useCurrentFrame();
  const fill = interpolate(frame, [20, 90], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const temp = interpolate(fill, [0, 1], [20, -89.2]);
  const barTop = 300, barH = 520, barX = 360, barW = 70;
  const mercuryH = interpolate(fill, [0, 1], [0, barH]);
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bgBottom }}>
      <SceneBG tint="#0a2036" />
      <SectionTitle kicker="RAZÓN Nº 2 · EL FRÍO" title="Tan extremo que ataca al avión" accent="#7fd8ff" />
      {svg(<>
        {/* termometro */}
        <rect x={barX} y={barTop} width={barW} height={barH} rx={35} fill="#0e2340" stroke="#26456b" strokeWidth={3} />
        <rect x={barX + 8} y={barTop + (barH - mercuryH)} width={barW - 16} height={mercuryH}
          rx={27} fill="url(#cold)" />
        <circle cx={barX + barW / 2} cy={barTop + barH + 40} r={60} fill="url(#cold)" stroke="#26456b" strokeWidth={3} />
        <defs>
          <linearGradient id="cold" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#8bf0ff" />
            <stop offset="100%" stopColor="#3aa0ff" />
          </linearGradient>
        </defs>
        {[0, -20, -40, -60, -89].map((t, i) => {
          const yy = barTop + interpolate(t, [-89.2, 20], [barH, 0]);
          return <g key={i}>
            <line x1={barX + barW + 6} y1={yy} x2={barX + barW + 26} y2={yy} stroke="#4f6d92" strokeWidth={2} />
            <text x={barX + barW + 34} y={yy + 8} fill="#7fa3cc" fontSize={22}>{t}°</text>
          </g>;
        })}
      </>)}
      <div style={{ position: "absolute", left: 20, top: 430, width: 300, textAlign: "right" }}>
        <div style={{ fontSize: 60, fontWeight: 900, color: "#8bf0ff" }}>{temp.toFixed(1)}°C</div>
        <div style={{ fontSize: 24, color: COLORS.dim }}>récord — base Vostok</div>
      </div>
      <Card x={780} y={360} w={720} delay={50} accent={COLORS.amber}>
        <div style={{ color: COLORS.amber, fontWeight: 800, fontSize: 24, letterSpacing: 2 }}>⛽ EL COMBUSTIBLE SE CONGELA</div>
        <div style={{ color: COLORS.white, fontSize: 30, marginTop: 12, lineHeight: 1.4 }}>
          El queroseno forma cristales de cera a <b style={{ color: "#8bf0ff" }}>-47 °C</b> y puede obstruir conductos y filtros.
        </div>
      </Card>
      <Card x={780} y={620} w={720} delay={80} accent={COLORS.red}>
        <div style={{ color: COLORS.red, fontWeight: 800, fontSize: 24, letterSpacing: 2 }}>❄ ATERRIZAR = SOBREVIVIR</div>
        <div style={{ color: COLORS.white, fontSize: 30, marginTop: 12, lineHeight: 1.4 }}>
          A la intemperie, el frío puede matar en <b style={{ color: COLORS.red }}>minutos</b>. El rescate tarda horas o días.
        </div>
      </Card>
    </AbsoluteFill>
  );
};

// ---------- 4. INFRAESTRUCTURA ----------
export const Infraestructura: React.FC = () => {
  const items = [
    { icon: "📡", t: "Comunicaciones", d: "Satélites geoestacionarios apenas llegan al polo" },
    { icon: "🧭", t: "Navegación", d: "La brújula magnética se vuelve loca cerca del polo sur" },
    { icon: "🌦️", t: "Meteorología", d: "Casi sin estaciones: volar a ciegas" },
    { icon: "⛽", t: "Servicios en tierra", d: "Sin repostaje, mantenimiento ni personal" },
  ];
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bgBottom }}>
      <SceneBG />
      <SectionTitle kicker="RAZÓN Nº 3 · SIN INFRAESTRUCTURA" title="La red invisible que aquí no existe" />
      {items.map((it, i) => {
        const delay = 25 + i * 18;
        return (
          <CardTile key={i} i={i} delay={delay} {...it} />
        );
      })}
    </AbsoluteFill>
  );
};
const CardTile: React.FC<{ i: number; delay: number; icon: string; t: string; d: string }> = ({ i, delay, icon, t, d }) => {
  const frame = useCurrentFrame();
  const s = spring({ frame: frame - delay, fps: 30, config: { damping: 15 } });
  const col = i % 2, row = Math.floor(i / 2);
  const x = 220 + col * 780, y = 340 + row * 320;
  const crossIn = spring({ frame: frame - delay - 20, fps: 30, config: { damping: 12 } });
  return (
    <div style={{ position: "absolute", left: x, top: y, width: 680, height: 250,
      opacity: s, transform: `translateY(${(1 - s) * 50}px)`,
      background: "rgba(9,25,48,0.9)", border: `2px solid #26456b`, borderRadius: 20,
      padding: 30, display: "flex", gap: 24, alignItems: "center" }}>
      <div style={{ fontSize: 90 }}>{icon}</div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 40, fontWeight: 800, color: COLORS.white }}>{t}</div>
        <div style={{ fontSize: 26, color: COLORS.dim, marginTop: 8, lineHeight: 1.3 }}>{d}</div>
      </div>
      <div style={{ position: "absolute", top: 20, right: 24, fontSize: 46, color: COLORS.red,
        opacity: crossIn, transform: `scale(${crossIn})` }}>✕</div>
    </div>
  );
};

// ---------- 5. EXCEPCIONES ----------
export const Excepciones: React.FC = () => {
  const frame = useCurrentFrame();
  const cards = [
    { icon: "🛫", tag: "TURÍSTICOS", txt: "Sobrevuelos sin aterrizar (Boeing 787) que nunca se alejan de la costa segura", c: COLORS.cyan },
    { icon: "🎖️", tag: "CIENTÍFICOS / MILITARES", txt: "C-17 y C-130 Hércules, algunos con esquís para pistas de hielo", c: COLORS.amber },
    { icon: "🧭", tag: "RUTAS QUE ROZAN EL BORDE", txt: "Vuelos del hemisferio sur que se acercan, pero no entran al continente", c: "#9be08a" },
  ];
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bgBottom }}>
      <SceneBG />
      <SectionTitle kicker="LA EXCEPCIÓN QUE CONFIRMA LA REGLA" title="Entonces, ¿quién SÍ vuela allí?" accent={COLORS.amber} />
      {cards.map((c, i) => {
        const s = spring({ frame: frame - (30 + i * 22), fps: 30, config: { damping: 15 } });
        return (
          <div key={i} style={{ position: "absolute", left: 130 + i * 570, top: 360, width: 520, height: 480,
            opacity: s, transform: `translateY(${(1 - s) * 60}px)`,
            background: "rgba(9,25,48,0.92)", border: `2px solid ${c.c}`, borderRadius: 22, padding: 36 }}>
            <div style={{ fontSize: 110 }}>{c.icon}</div>
            <div style={{ fontSize: 30, fontWeight: 900, color: c.c, marginTop: 16, letterSpacing: 1 }}>{c.tag}</div>
            <div style={{ fontSize: 30, color: COLORS.white, marginTop: 16, lineHeight: 1.4 }}>{c.txt}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ---------- 6. GEOGRAFÍA (Ártico vs Antártida) ----------
export const Geografia: React.FC = () => {
  const frame = useCurrentFrame();
  const barN = interpolate(frame, [60, 110], [0, 90], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const pole = (cx: number, busy: boolean, color: string) => {
    const routes = [];
    if (busy) {
      for (let i = 0; i < 8; i++) {
        const a = (i * 45) * Math.PI / 180;
        const app = interpolate(frame, [20 + i * 4, 45 + i * 4], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        routes.push(<line key={i} x1={cx - Math.cos(a) * 210} y1={520 - Math.sin(a) * 210}
          x2={cx + Math.cos(a) * 210} y2={520 + Math.sin(a) * 210}
          stroke={COLORS.amber} strokeWidth={3} opacity={0.5 * app} strokeDasharray="6 8" />);
      }
    }
    return <g>
      <circle cx={cx} cy={520} r={200} fill="#0d2038" stroke={COLORS.grid} strokeWidth={2} />
      <circle cx={cx} cy={520} r={110} fill={busy ? "#123" : ICE} stroke="#9fc0e8" strokeWidth={2} opacity={busy ? 0.3 : 1} />
      {routes}
      {!busy && <text x={cx} y={528} fill="#20456f" fontSize={26} fontWeight={900} textAnchor="middle">VACÍO</text>}
    </g>;
  };
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bgBottom }}>
      <SceneBG />
      <SectionTitle kicker="EL FACTOR QUE NADIE MENCIONA" title="Dónde decidió vivir la humanidad" accent="#9be08a" />
      {svg(<>
        {pole(560, true, COLORS.amber)}
        {pole(1360, false, COLORS.cyan)}
      </>)}
      <div style={{ position: "absolute", left: 460, top: 760, width: 200, textAlign: "center" }}>
        <div style={{ fontSize: 40, fontWeight: 900, color: COLORS.amber }}>ÁRTICO</div>
        <div style={{ fontSize: 24, color: COLORS.dim }}>rutas Norteamérica–Asia–Europa</div>
      </div>
      <div style={{ position: "absolute", left: 1260, top: 760, width: 200, textAlign: "center" }}>
        <div style={{ fontSize: 40, fontWeight: 900, color: COLORS.cyan }}>ANTÁRTIDA</div>
        <div style={{ fontSize: 24, color: COLORS.dim }}>casi ninguna ruta pasa por aquí</div>
      </div>
      <div style={{ position: "absolute", left: 660, top: 400, width: 600, textAlign: "center" }}>
        <div style={{ fontSize: 92, fontWeight: 900, color: COLORS.amber, lineHeight: 1 }}>~{barN.toFixed(0)}%</div>
        <div style={{ fontSize: 30, fontWeight: 700, color: COLORS.white, marginTop: 10 }}>
          de la población vive en el <span style={{ color: COLORS.amber }}>hemisferio norte</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ---------- 7. CIERRE ----------
export const Cierre: React.FC = () => {
  const frame = useCurrentFrame();
  const outro = spring({ frame: frame - 200, fps: 30, config: { damping: 16 } });
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bgBottom }}>
      <SceneBG />
      <SectionTitle kicker="EN RESUMEN" title="Por qué la Antártida es un vacío" />
      <Bullet x={140} y={330} delay={20} icon="1" text="Sin aeropuertos → imposible cumplir ETOPS" color={COLORS.red} w={860} />
      <Bullet x={140} y={445} delay={40} icon="2" text="Frío extremo → amenaza combustible y supervivencia" color="#8bf0ff" w={860} />
      <Bullet x={140} y={560} delay={60} icon="3" text="Sin infraestructura de navegación ni meteorología" color={COLORS.amber} w={860} />
      <Bullet x={140} y={675} delay={80} icon="4" text="Casi ninguna ruta tiene su camino más corto por allí" color="#9be08a" w={860} />
      {frame > 200 && (
        <div style={{ position: "absolute", bottom: 130, width: "100%", textAlign: "center",
          opacity: outro, transform: `scale(${0.85 + 0.15 * outro})` }}>
          <div style={{ fontSize: 30, color: COLORS.dim, letterSpacing: 6 }}>SUSCRÍBETE A</div>
          <div style={{ fontSize: 90, fontWeight: 900, color: COLORS.white, letterSpacing: 3 }}>
            ZONA DE <span style={{ color: COLORS.cyan }}>VUELO</span> 🛩️
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};

export const SCENES: Record<string, React.FC> = {
  hook: Hook, etops: Etops, frio: Frio, infraestructura: Infraestructura,
  excepciones: Excepciones, geografia: Geografia, cierre: Cierre,
};
