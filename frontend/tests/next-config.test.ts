import { execFileSync } from "node:child_process";
import { describe, expect, it } from "vitest";

function loadConfig(vercel: boolean) {
  const environment = { ...process.env };
  if (vercel) {
    environment.VERCEL = "1";
  } else {
    delete environment.VERCEL;
  }
  const output = execFileSync(
    process.execPath,
    [
      "--input-type=module",
      "--eval",
      'const { default: config } = await import("./next.config.mjs"); console.log(JSON.stringify(config));',
    ],
    { cwd: process.cwd(), encoding: "utf8", env: environment },
  );
  return JSON.parse(output);
}

describe("Next.js deployment output", () => {
  it("uses Vercel's native output tracing during Vercel builds", () => {
    const config = loadConfig(true);

    expect(config.output).toBeUndefined();
  });

  it("keeps standalone output for the frontend Docker image", () => {
    const config = loadConfig(false);

    expect(config.output).toBe("standalone");
  });
});
