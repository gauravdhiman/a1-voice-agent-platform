/** Static filenames used by the homepage launch film. */
export const LAUNCH_FILM_ASSET_FILES = {
  video: "247ai-opportunity-in-motion.mp4",
  captions: "247ai-opportunity-in-motion-en.vtt",
  poster: "247ai-opportunity-in-motion-poster.jpg",
} as const;

export type LaunchFilmAssetName = keyof typeof LAUNCH_FILM_ASSET_FILES;

/**
 * Build a launch-film asset URL from an optional CDN directory.
 *
 * An empty CDN directory keeps local development and offline previews on the
 * files packaged with the frontend. Production can point at a versioned R2
 * custom-domain path without changing the page markup.
 */
export function getLaunchFilmAssetUrl(
  asset: LaunchFilmAssetName,
  configuredBaseUrl: string,
): string {
  const baseUrl = configuredBaseUrl.trim().replace(/\/+$/, "") || "/videos";
  return `${baseUrl}/${LAUNCH_FILM_ASSET_FILES[asset]}`;
}
