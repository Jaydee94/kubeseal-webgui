// Helpers for drag and drop of files.

/** True if the drag carries files; dragged text or links are not ours to handle. */
export function carriesFiles(event) {
  return Array.from(event.dataTransfer?.types ?? []).includes('Files')
}
