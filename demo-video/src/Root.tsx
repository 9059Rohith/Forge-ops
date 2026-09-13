import { Composition } from "remotion";
import { Demo } from "./Demo";
import scenes from "./timing.json";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition id="ForgeGuardDemo" component={Demo} durationInFrames={scenes.reduce((sum, scene) => sum + scene.frames, 0)} fps={24} width={1920} height={1080} />
    </>
  );
};
