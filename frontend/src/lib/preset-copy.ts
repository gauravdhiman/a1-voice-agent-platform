/** Helpers for creating a safe name when cloning a platform voice preset. */

const COPY_PREFIX = "Copy of ";
const MAX_PRESET_NAME_LENGTH = 100;

/**
 * Builds a unique, backend-valid name for a copied preset.
 *
 * Preset creation is an upsert by name, so a copy must never reuse an existing
 * name. Names are compared case-insensitively for a friendlier UI guarantee,
 * and the source name is truncated when the generated copy would exceed the
 * backend's 100-character limit.
 *
 * @param sourceName - Name of the preset being copied.
 * @param existingNames - Names already present in the platform catalog.
 * @returns A unique name beginning with `Copy of ` and no longer than 100 characters.
 */
export function getClonePresetName(
  sourceName: string,
  existingNames: readonly string[],
): string {
  const normalizedExistingNames = new Set(
    existingNames.map((name) => name.trim().toLowerCase()),
  );
  const trimmedSourceName = sourceName.trim();

  const buildCandidate = (suffix: string) => {
    const availableSourceLength = Math.max(
      0,
      MAX_PRESET_NAME_LENGTH - COPY_PREFIX.length - suffix.length,
    );
    const boundedSourceName = trimmedSourceName
      .slice(0, availableSourceLength)
      .trimEnd();
    return `${COPY_PREFIX}${boundedSourceName}${suffix}`;
  };

  let candidate = buildCandidate("");
  if (!normalizedExistingNames.has(candidate.toLowerCase())) {
    return candidate;
  }

  for (let copyNumber = 2; ; copyNumber += 1) {
    candidate = buildCandidate(` (${copyNumber})`);
    if (!normalizedExistingNames.has(candidate.toLowerCase())) {
      return candidate;
    }
  }
}
