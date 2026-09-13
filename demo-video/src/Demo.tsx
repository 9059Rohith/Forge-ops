import { AbsoluteFill, Img, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { Audio } from "@remotion/media";
import scenes from "./timing.json";

const mint = "#64e6bd";
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

function Scene({ scene }: { scene: (typeof scenes)[number] }) {
  const frame = useCurrentFrame();
  const hasImage = "image" in scene;
  return <AbsoluteFill style={{ padding: "64px 88px", opacity: interpolate(frame, [0, 10, scene.frames - 10, scene.frames], [0, 1, 1, 0], clamp) }}>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 20, letterSpacing: 3, color: mint }}>
      <span style={{ fontWeight: 750, fontSize: 30, letterSpacing: -1 }}>⬡ FORGEGUARD</span>
      <span>PRODUCT WALKTHROUGH</span>
    </div>
    <div style={{ marginTop: hasImage ? 34 : 110, color: mint, fontSize: 22, letterSpacing: 4 }}>{scene.kicker}</div>
    <h1 style={{ fontSize: hasImage ? 60 : 112, maxWidth: 1560, lineHeight: 1.06, letterSpacing: -3, fontWeight: 750, whiteSpace: "pre-line", margin: hasImage ? "15px 0 25px" : "28px 0 42px", translate: `0 ${interpolate(frame, [0, 22], [18, 0], clamp)}px` }}>{scene.title}</h1>
    {hasImage ? <div style={{ flex: 1, minHeight: 0, border: "1px solid #29453e", borderRadius: 18, background: "#0b141c", overflow: "hidden", boxShadow: "0 24px 70px #0008", position: "relative" }}>
      <div style={{ height: 36, background: "#17232c", display: "flex", alignItems: "center", padding: "0 18px", gap: 8 }}><span style={{ color: "#ff7777" }}>●</span><span style={{ color: "#e8ba63" }}>●</span><span style={{ color: mint }}>●</span><span style={{ marginLeft: 22, fontSize: 14, color: "#a1b1bd", letterSpacing: 1 }}>ForgeGuard / captured application</span></div>
      {scene.id === "block" ? <div style={{ display: "flex", height: "calc(100% - 36px)", gap: 64, padding: "0 42px" }}>
        <div style={{ width: 590, overflow: "hidden", position: "relative", flexShrink: 0 }}><Img src={staticFile(scene.image!)} style={{ width: 590, position: "absolute", top: -420 }} /></div>
        <div style={{ alignSelf: "center", display: "grid", gap: 28 }}>
          <div style={{ color: mint, fontSize: 30 }}>CHECKOUT TESTS <strong style={{ fontSize: 60, display: "block" }}>5 / 5 passed</strong></div>
          <div style={{ color: "#ff7c88", fontSize: 30 }}>SECURITY REVIEW <strong style={{ fontSize: 60, display: "block" }}>18% · Critical</strong></div>
          <div style={{ color: "#ff7c88", fontSize: 40, border: "1px solid #ff7c8855", padding: "14px 24px", borderRadius: 10 }}>PATCH BLOCKED</div>
        </div>
      </div> : <Img src={staticFile(scene.image!)} style={{ width: "100%", height: "calc(100% - 36px)", objectFit: "contain", objectPosition: "top", scale: interpolate(frame, [0, scene.frames], [1, 1.018], clamp) }} />}
    </div> : <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>{scene.accent?.split(" • ").map((text) => <div key={text} style={{ color: mint, fontSize: 30, borderLeft: `3px solid ${mint}`, padding: "12px 24px", background: "#64e6bd09" }}>{text}</div>)}</div>}
    <div style={{ marginTop: "auto", paddingTop: 26, fontSize: 29, color: "#dae7e5", minHeight: 65 }}>{scene.caption}</div>
    <div style={{ display: "flex", justifyContent: "space-between", color: "#839b9d", fontSize: 16, marginTop: 12, letterSpacing: 1 }}><span>Explicit deterministic showcase · Actual application capture</span><span>{String(scenes.indexOf(scene) + 1).padStart(2, "0")} / 08</span></div>
  </AbsoluteFill>;
}

export function Demo() {
  const frame = useCurrentFrame();
  const duration = scenes.reduce((sum, scene) => sum + scene.frames, 0);
  return <AbsoluteFill style={{ background: "radial-gradient(ellipse at 90% 5%, #153c36 0%, #0a171e 42%, #070e15 80%)", color: "#f1f7f6", fontFamily: "Arial, sans-serif" }}>
    <AbsoluteFill style={{ backgroundImage: "linear-gradient(#5ae5b606 1px, transparent 1px), linear-gradient(90deg, #5ae5b606 1px, transparent 1px)", backgroundSize: "72px 72px" }} />
    <Audio src={staticFile("ambient.wav")} volume={0.6} />
    {scenes.map((scene) => <Sequence key={scene.id} from={scene.from} durationInFrames={scene.frames}>
      <Scene scene={scene} />
      <Sequence from={12}><Audio src={staticFile(`${scene.id}.mp3`)} /></Sequence>
    </Sequence>)}
    <div style={{ position: "absolute", bottom: 0, left: 0, height: 5, width: `${frame / (duration - 1) * 100}%`, background: mint }} />
  </AbsoluteFill>;
}
