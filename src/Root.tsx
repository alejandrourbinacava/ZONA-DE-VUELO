import React from "react";
import { Composition } from "remotion";
import { TibetScene } from "./components";
import { Auto, Manifest, Media } from "./auto/Auto";
import { MapRoute, Annotate } from "./auto/MotionGraphics";

const EMPTY_MANIFEST: Manifest = { total_duration: 1, fps: 30, sections: [] };
const EMPTY_MEDIA: Media = { sections: [] };

const MGTestMap: React.FC = () => (
  <MapRoute from={{ name: "Madrid", lat: 40.42, lon: -3.70 }} to={{ name: "Nueva York", lat: 40.71, lon: -74.01 }} label="Madrid → Nueva York" />
);
const MGTestAnnotate: React.FC = () => (
  <Annotate file="worldmap.jpg" callouts={[{ label: "Turbina de alta presión" }, { label: "Álabes del fan" }, { label: "Tobera de escape" }]} label="EL MOTOR" />
);

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
        defaultProps={{ manifest: EMPTY_MANIFEST, media: EMPTY_MEDIA }}
        calculateMetadata={({ props }) => {
          const m = (props as { manifest: Manifest }).manifest;
          const fps = m.fps || 30;
          return { durationInFrames: Math.max(1, Math.ceil((m.total_duration || 1) * fps)), fps };
        }}
      />
      <Composition id="MGTestMap" component={MGTestMap} durationInFrames={90} fps={30} width={1920} height={1080} />
      <Composition id="MGTestAnnotate" component={MGTestAnnotate} durationInFrames={90} fps={30} width={1920} height={1080} />
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
