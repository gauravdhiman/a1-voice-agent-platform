# 24x7 AI — Opportunity in motion

Original 72-second product launch film, 1920 × 1080, 30 fps. Nine editable HyperFrames scenes, an original generated instrumental, synthetic narration, and original procedural transition sounds.

## Watch and edit

- Final video: `renders/247ai-opportunity-in-motion.mp4` (also packaged at
  `frontend/public/videos/247ai-opportunity-in-motion.mp4`)
- Story and shot plan: `STORYBOARD.md`
- Product evidence and reference study: `RESEARCH.md`
- Spoken script: `SCRIPT.md`
- Brand system: `frame.md`
- Optional subtitles: `renders/captions.srt`
- Scene files: `compositions/scenes/`
- Audio provenance and generation costs: `assets/audio/provenance.json`

Start Studio with `npm run dev -- --background`. The project uses HyperFrames
0.8.155. The final film is authored at 72 seconds, with separate narration,
music, and sound-effect tracks.

Edit the individual scene HTML files for direct timeline work. `build_film.py` is a reproducible source generator; running it replaces those scene files and the master with its definitions. Keep edits in the generator if you intend to rebuild that way. Audio and captured assets are frozen local files.

Workflow surfaces are labeled illustrations. The website detail is a fresh
capture of the public 24x7 AI site. No reference footage or audio was reused.

## Checks

`npm run check` runs the composition audit. The final audit and export evidence
are recorded in `VALIDATION.md`. The two static duplicate-image warnings describe
the intentional repeated official brand mark in the header and phone; rendered
snapshots confirm both placements.
