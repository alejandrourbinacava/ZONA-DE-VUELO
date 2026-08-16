import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame, interpolate } from "remotion";
import { COLORS } from "../theme";
import { Broll } from "../antartida/Broll";
import { Beat, BeatSpec } from "../antartida/beats";
import { Subtitles, Cue } from "../antartida/Subtitles";

export type Section = {
  key: string; title: string; offset: number; duration: number; cues: Cue[];
};
export type Manifest = { total_duration: number; fps: number; sections: Section[] };
type Clip = { file: string; query: string; duration: number; credit: string };
type ShotSection = { key: string; broll: string[]; beats: BeatSpec[] };
export type Shotlist = { sections: ShotSection[] };

const MAX_CELL = 4.5;
const CMAP: Record<string, string> = {
  cyan: COLORS.cyan, amber: COLORS.amber, red: COLORS.red, green: "#9be08a",
};
function mapSpec(spec: any): BeatSpec {
  const s = { ...spec };
  if (s.color && CMAP[s.color]) s.color = CMAP[s.color];
  if (s.accent && CMAP[s.accent]) s.accent = CMAP[s.accent];
  return s as BeatSpec;
}

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
  return <div style={{ position: "absolute", bottom: 0, left: 0, height: 6, width: `${p * 100}%`,
    background: COLORS.cyan, boxShadow: `0 0 12px ${COLORS.cyan}`, zIndex: 10 }} />;
};

type Cell =
  | { type: "broll"; from: number; dur: number; clip: Clip; startFrom: number }
  | { type: "beat"; from: number; dur: number; spec: BeatSpec };

function buildCells(manifest: Manifest, clips: Record<string, Clip[]>, shot: Shotlist): Cell[] {
  const fps = manifest.fps || 30;
  const cells: Cell[] = [];
  const use: Record<string, number> = {};
  for (const sec of manifest.sections) {
    const pool = clips[sec.key] || [];
    const beats = (shot.sections.find((s) => s.key === sec.key)?.beats || []).map(mapSpec);
    const n = Math.max(1, Math.ceil(sec.duration / MAX_CELL));
    const cellDur = sec.duration / n;
    let g = 0, b = 0;
    for (let i = 0; i < n; i++) {
      const from = Math.round((sec.offset + i * cellDur) * fps);
      const to = Math.round((sec.offset + (i + 1) * cellDur) * fps);
      const dur = Math.max(1, to - from);
      const wantBeat = beats.length > 0 && i % 3 === 1;
      if (wantBeat || pool.length === 0) {
        if (beats.length === 0) continue;
        cells.push({ type: "beat", from, dur, spec: beats[g % beats.length] }); g++;
      } else {
        const clip = pool[b % pool.length];
        const u = use[clip.file] || 0; use[clip.file] = u + 1;
        const cd = clip.duration || 8;
        // punto de inicio seguro: nunca pedir mas alla del final del clip
        const maxStart = Math.max(0, cd - MAX_CELL - 0.5);
        const startFrom = maxStart > 0 ? (u * MAX_CELL) % maxStart : 0;
        cells.push({ type: "broll", from, dur, clip, startFrom }); b++;
      }
    }
  }
  return cells;
}

export const Auto: React.FC<{ manifest: Manifest; clips: Record<string, Clip[]>; shotlist: Shotlist }> =
({ manifest, clips, shotlist }) => {
  const fps = manifest.fps || 30;
  const totalFrames = Math.ceil(manifest.total_duration * fps);
  const cues: Cue[] = manifest.sections.flatMap((s) => s.cues);
  const cells = buildCells(manifest, clips, shotlist);
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bgBottom, fontFamily: "Montserrat, 'Segoe UI', sans-serif" }}>
      <Audio src={staticFile("narration_full.mp3")} />
      {cells.map((c, i) => (
        <Sequence key={i} from={c.from} durationInFrames={c.dur} name={c.type}>
          {c.type === "broll"
            ? <Broll src={c.clip.file} startFrom={c.startFrom} overlay={0.4} />
            : <Beat spec={c.spec} />}
        </Sequence>
      ))}
      <Subtitles cues={cues} />
      <BrandCorner />
      <ProgressBar total={totalFrames} />
    </AbsoluteFill>
  );
};
