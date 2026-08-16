import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame, interpolate } from "remotion";
import { COLORS } from "../theme";
import { Broll } from "./Broll";
import { Beat, SECTION_BEATS } from "./beats";
import clipsData from "../../public/stock/clips.json";

export type Cue = { start: number; end: number; text: string };
export type Section = {
  key: string; title: string; mp3: string;
  offset: number; duration: number; text: string; cues: Cue[];
};
export type Manifest = {
  voice: string; total_duration: number; fps: number; sections: Section[];
};
type Clip = { file: string; query: string; duration: number; credit: string };
const CLIPS = clipsData as unknown as Record<string, Clip[]>;

const MAX_CELL = 4.5; // segundos: ningún plano supera esto

const BrandCorner: React.FC = () => (
  <div style={{ position: "absolute", top: 40, left: 60, display: "flex", alignItems: "center", gap: 12, opacity: 0.9, zIndex: 10 }}>
    <span style={{ fontSize: 30 }}>🛩️</span>
    <span style={{ fontWeight: 900, fontSize: 24, color: COLORS.white, letterSpacing: 2 }}>
      ZONA DE <span style={{ color: COLORS.cyan }}>VUELO</span>
    </span>
  </div>
);

const ProgressBar: React.FC<{ total: number }> = ({ total }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [0, total], [0, 1], { extrapolateRight: "clamp" });
  return (
    <div style={{ position: "absolute", bottom: 0, left: 0, height: 6, width: `${p * 100}%`,
      background: COLORS.cyan, boxShadow: `0 0 12px ${COLORS.cyan}`, zIndex: 10 }} />
  );
};

type Cell =
  | { type: "broll"; from: number; dur: number; clip: Clip; startFrom: number }
  | { type: "beat"; from: number; dur: number; specKey: string; beatIdx: number };

// construye la lista de celdas (≤ MAX_CELL) para todo el vídeo
function buildCells(manifest: Manifest): Cell[] {
  const fps = manifest.fps || 30;
  const cells: Cell[] = [];
  const clipUse: Record<string, number> = {};
  for (const s of manifest.sections) {
    const clips = CLIPS[s.key] || [];
    const beats = SECTION_BEATS[s.key] || [];
    const nCells = Math.max(1, Math.ceil(s.duration / MAX_CELL));
    const cellDur = s.duration / nCells;
    let gCount = 0, bCount = 0;
    for (let i = 0; i < nCells; i++) {
      const from = Math.round((s.offset + i * cellDur) * fps);
      const to = Math.round((s.offset + (i + 1) * cellDur) * fps);
      const dur = Math.max(1, to - from);
      const isBeat = beats.length > 0 && i % 3 === 1; // ~1/3 gráficos, arranca en B-roll
      if (isBeat) {
        cells.push({ type: "beat", from, dur, specKey: s.key, beatIdx: gCount % beats.length });
        gCount++;
      } else if (clips.length > 0) {
        const clip = clips[bCount % clips.length];
        const use = clipUse[clip.file] || 0;
        clipUse[clip.file] = use + 1;
        const span = Math.max(1, (clip.duration || 8) - MAX_CELL);
        const startFrom = (clip.duration || 0) > 5 ? (use * MAX_CELL) % span : 0;
        cells.push({ type: "broll", from, dur, clip, startFrom });
        bCount++;
      } else if (beats.length > 0) {
        cells.push({ type: "beat", from, dur, specKey: s.key, beatIdx: gCount % beats.length });
        gCount++;
      }
    }
  }
  return cells;
}

export const Antartida: React.FC<{ manifest: Manifest }> = ({ manifest }) => {
  const fps = manifest.fps || 30;
  const totalFrames = Math.ceil(manifest.total_duration * fps);
  const cells = buildCells(manifest);
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bgBottom, fontFamily: "Montserrat, 'Segoe UI', sans-serif" }}>
      <Audio src={staticFile("narration_full.mp3")} />
      {cells.map((c, i) => (
        <Sequence key={i} from={c.from} durationInFrames={c.dur} name={c.type === "broll" ? `broll-${i}` : `beat-${i}`}>
          {c.type === "broll" ? (
            <Broll src={c.clip.file} startFrom={c.startFrom} overlay={0.4} />
          ) : (
            <Beat spec={SECTION_BEATS[c.specKey][c.beatIdx]} />
          )}
        </Sequence>
      ))}
      <BrandCorner />
      <ProgressBar total={totalFrames} />
    </AbsoluteFill>
  );
};
