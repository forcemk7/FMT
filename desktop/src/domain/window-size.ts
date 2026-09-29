/**
 * T293 minimum supported window (inner/client size, logical px): the size at
 * which Player Profile — the tallest desk — shows everything without scrolling.
 * Attributes tab ends at 1057px; the Development tab (chart + attribute desk)
 * needs ~31px more, so 1100 leaves a small margin. Keep in sync with
 * `minWidth`/`minHeight` in src-tauri/tauri.conf.json (the pre-JS default).
 */
export const MIN_WINDOW_WIDTH = 1180;
export const MIN_WINDOW_HEIGHT = 1100;

/** Must match `html[data-density="large"]{zoom}` in globals.css. */
export const LARGE_UI_ZOOM = 1.125;

/**
 * Larger interface scales every px by `zoom`, so the same content needs a
 * proportionally larger window. Raise the OS-enforced minimum to match, and grow
 * the window if it's currently below it. No-op outside Tauri (dev preview).
 */
export async function applyMinWindowSize(zoom: number): Promise<void> {
  if (typeof window === "undefined" || !("__TAURI_INTERNALS__" in window)) return;
  try {
    const { getCurrentWindow, LogicalSize } = await import("@tauri-apps/api/window");
    const win = getCurrentWindow();
    const minWidth = Math.ceil(MIN_WINDOW_WIDTH * zoom);
    const minHeight = Math.ceil(MIN_WINDOW_HEIGHT * zoom);
    await win.setMinSize(new LogicalSize(minWidth, minHeight));
    const inner = (await win.innerSize()).toLogical(await win.scaleFactor());
    if (inner.width < minWidth || inner.height < minHeight) {
      await win.setSize(new LogicalSize(Math.max(inner.width, minWidth), Math.max(inner.height, minHeight)));
    }
  } catch {
    // Window API unavailable or denied — CSS still renders, the OS just won't enforce the larger minimum.
  }
}
