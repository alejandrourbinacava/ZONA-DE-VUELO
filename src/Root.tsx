import React from "react";
import { Composition } from "remotion";
import { TibetScene } from "./components";
import { Auto, Manifest, Shotlist } from "./auto/Auto";

const EMPTY_MANIFEST: Manifest = { total_duration: 1, fps: 30, sections: [] };
const EMPTY_SHOT: Shotlist = { sections: [] };

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Composicion generica: recibe manifest + clips + shotlist por --props */}
      <Composition
        id="Auto"
        component={Auto as React.FC<Record<string, unknown>>}
        durationInFrames={30}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{ manifest: EMPTY_MANIFEST, clips: {}, shotlist: EMPTY_SHOT }}
        calculateMetadata={({ props }) => {
          const m = (props as { manifest: Manifest }).manifest;
          const fps = m.fps || 30;
          return { durationInFrames: Math.max(1, Math.ceil((m.total_duration || 1) * fps)), fps };
        }}
      />
      <Composition
        id="Demo"
        component={TibetScene}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
