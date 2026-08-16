import React from "react";
import { AbsoluteFill, OffthreadVideo, staticFile, useCurrentFrame, interpolate } from "remotion";
import { COLORS } from "../theme";

/** Reproduce un clip de stock a pantalla completa (cover) con overlay para
 *  mantener legibles voz/subtítulos. Se usa como fondo de una escena o como
 *  escena B-roll completa con un rótulo (lower-third). */
export const Broll: React.FC<{
  src: string;              // ruta dentro de public/ (staticFile)
  startFrom?: number;       // segundo inicial del clip
  overlay?: number;         // 0-1 oscurecimiento
  kenBurns?: boolean;       // zoom lento
  lowerThird?: string;      // rótulo opcional
  accent?: string;
}> = ({ src, startFrom = 0, overlay = 0.45, kenBurns = true, lowerThird, accent = COLORS.cyan }) => {
  const frame = useCurrentFrame();
  const scale = kenBurns ? interpolate(frame, [0, 300], [1.06, 1.14]) : 1;
  const fade = interpolate(frame, [0, 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ backgroundColor: "#000", opacity: fade }}>
      <AbsoluteFill style={{ transform: `scale(${scale})` }}>
        <OffthreadVideo
          src={staticFile(src)}
          startFrom={Math.round(startFrom * 30)}
          loop
          muted
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </AbsoluteFill>
      {/* oscurecimiento + viñeta para legibilidad */}
      <AbsoluteFill style={{
        background: `linear-gradient(180deg, rgba(5,13,28,${overlay * 0.9}) 0%, rgba(5,13,28,${overlay * 0.35}) 35%, rgba(5,13,28,${overlay * 0.55}) 70%, rgba(5,13,28,${Math.min(0.95, overlay + 0.35)}) 100%)`,
      }} />
      {lowerThird && (
        <div style={{ position: "absolute", left: 90, bottom: 190,
          borderLeft: `6px solid ${accent}`, paddingLeft: 22 }}>
          <div style={{ fontSize: 40, fontWeight: 800, color: "#fff",
            textShadow: "0 3px 14px rgba(0,0,0,0.9)" }}>{lowerThird}</div>
        </div>
      )}
    </AbsoluteFill>
  );
};
