import { describe, expect, it } from "vitest";
import { getLaunchFilmAssetUrl } from "../launch-film-assets";

describe("getLaunchFilmAssetUrl", () => {
  it("uses the packaged video directory when no CDN base is configured", () => {
    expect(getLaunchFilmAssetUrl("video", "")).toBe(
      "/videos/247ai-opportunity-in-motion.mp4",
    );
  });

  it("uses a normalized CDN directory for all film assets", () => {
    expect(
      getLaunchFilmAssetUrl(
        "captions",
        "  https://media.247ai.live/247ai-launch-film-2b838a5653ff///  ",
      ),
    ).toBe(
      "https://media.247ai.live/247ai-launch-film-2b838a5653ff/247ai-opportunity-in-motion-en.vtt",
    );
  });
});
