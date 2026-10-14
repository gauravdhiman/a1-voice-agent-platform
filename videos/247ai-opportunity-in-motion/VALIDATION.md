# Delivery validation

## Output

- File: renders/247ai-opportunity-in-motion.mp4
- Duration: 72.000000 seconds.
- Picture: H.264, 1920 × 1080, 30 fps, 2,160 frames.
- Audio: AAC, stereo, 48 kHz.
- Optional English subtitle track plus captions.srt; subtitles are not burned into the picture.
- Size: 9.00 MB.
- The rendered film and homepage MP4 are byte-identical. The homepage WebVTT matches the embedded subtitle track and source SRT.
- The local development site returned the same final MP4 and WebVTT byte-for-byte (HTTP 200).

## Composition and visual inspection

HyperFrames 0.8.155 composition check: passed.

- Runtime errors: 0.
- Layout errors: 0; four informational findings describe the intentional off-canvas owner-control pan in scene 7.
- Contrast: 49 / 49 sampled text checks passed.
- Two duplicate-media warnings are the intentional repeated official mark in scenes 1 and 3.
- Inspected the revised opening at 3.0 and 6.5 seconds, the outcome message at 13.0 seconds, and the after-hours brand lockup at 69.5 seconds. Other scene source is unchanged.
- Rendered and encoded the complete 72-second master; the final MP4 was probed after adding its optional subtitle stream.

## Audio

Measured final mix: -15.70 LUFS integrated, -1.47 dBTP true peak, 10.20 LU loudness range. Music has authored narration ducking. A master limiter provides headroom. The score naturally resolves around 70 seconds, and the remaining tail fades into the held brand invitation.

The opening narration now matches the rest of the film: MiniMax Speech 2.8 HD, `English_expressive_narrator`, speed 0.96, calm delivery. The rendered mix was transcribed to confirm: “Your doors are closed. Customers still get answers.” and “Twenty-four seven AI answers calls, helps customers, and books appointments.”

## Render

Delivery quality. Hardware GPU, screenshot capture, four workers. Completed in 54.5 seconds.

## Scope

This export includes the final narration, timing, music mix, composition, and
homepage video asset. The poster is the approved frame from the final render.
Production release status is tracked with the application change that embeds
the film on the homepage.
