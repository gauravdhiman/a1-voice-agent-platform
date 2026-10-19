import { describe, expect, it } from "vitest";
import { getLaunchFilmAssetUrl } from "../launch-film-assets";

describe("getLaunchFilmAssetUrl", () => {
  it("uses the packaged video directory when no CDN base is configured", () => {
    expect(getLaunchFilmAssetUrl("video", "")).toBe(
      "/videos/247ai-always-open.mp4",
    );
  });

  it("uses a normalized CDN directory for all film assets", () => {
    const cdn = "https://media.247ai.live/247ai-launch-film-v2-example";
    expect(getLaunchFilmAssetUrl("captions", `  ${cdn}///  `)).toBe(
      `${cdn}/247ai-always-open-en.vtt`,
    );
    expect(getLaunchFilmAssetUrl("poster", cdn)).toBe(
      `${cdn}/247ai-always-open-poster.jpg`,
    );
  });
});
