import React from "react";
import { useCurrentFrame, useVideoConfig, spring } from "remotion";
import { COLORS } from "../theme";

export type Cue = { start: number; end: number; text: string };

export const Subtitles: React.FC<{ cues: Cue[] }> = ({ cues }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const idx = cues.findIndex((c) => t >= c.start && t < c.end);
  if (idx < 0) return null;
  const cue = cues[idx];
  const pop = spring({ frame: frame - Math.round(cue.start * fps), fps, config: { damping: 200, stiffness: 220 } });
  return (
    <div style={{ position: "absolute", bottom: 54, width: "100%", display: "flex", justifyContent: "center", padding: "0 140px" }}>
      <div style={{
        background: "rgba(5,13,28,0.82)", borderRadius: 14, padding: "12px 30px",
        border: "1px solid rgba(120,180,255,0.25)", maxWidth: 1400,
        transform: `translateY(${(1 - pop) * 14}px) scale(${0.98 + 0.02 * pop})`,
      }}>
        <span style={{ fontSize: 42, fontWeight: 700, color: COLORS.white, textShadow: "0 2px 8px rgba(0,0,0,0.8)" }}>
          {cue.text}
        </span>
      </div>
    </div>
  );
};
