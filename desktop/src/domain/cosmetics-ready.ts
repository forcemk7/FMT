let cosmeticsReady = false;

export function markFmtCosmeticsReady() {
  if (typeof window === "undefined") return;
  cosmeticsReady = true;
  window.dispatchEvent(new Event("fmt-cosmetics-ready"));
}

export function isFmtCosmeticsReady() {
  return cosmeticsReady;
}

export function whenFmtCosmeticsReady(callback: () => void) {
  if (typeof window === "undefined") return () => undefined;
  if (cosmeticsReady) {
    callback();
    return () => undefined;
  }
  const handler = () => callback();
  window.addEventListener("fmt-cosmetics-ready", handler);
  return () => window.removeEventListener("fmt-cosmetics-ready", handler);
}
