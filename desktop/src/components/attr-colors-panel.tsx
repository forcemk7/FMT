"use client";

import { Palette } from "lucide-react";
import { useEffect, useState } from "react";
import {
  ATTR_COLOR_BANDS,
  FM_IN_GAME_ATTR_COLORS,
  applyAttrColorPalette,
  loadAttrColorPalette,
  saveAttrColorPalette,
  type AttrColorPalette,
} from "@/domain/attr-colors";
import { Button } from "@/components/ui/button";

export function AttrColorsPanel() {
  const [palette, setPalette] = useState<AttrColorPalette>(FM_IN_GAME_ATTR_COLORS);

  useEffect(() => {
    const loaded = loadAttrColorPalette();
    setPalette(loaded);
    applyAttrColorPalette(loaded);
  }, []);

  const updateBand = (key: keyof AttrColorPalette, value: string) => {
    const next = { ...palette, [key]: value };
    setPalette(next);
    saveAttrColorPalette(next);
    applyAttrColorPalette(next);
  };

  const reset = () => {
    const next = { ...FM_IN_GAME_ATTR_COLORS };
    setPalette(next);
    saveAttrColorPalette(next);
    applyAttrColorPalette(next);
  };

  return (
    <article className="attr-colors-panel">
      <Palette aria-hidden="true" />
      <div>
        <strong>Attribute colors</strong>
        <span>FM in-game four bands (1–20). Ability/Potential use the same bands on tenths.</span>
      </div>
      <div className="attr-colors-swatches">
        {ATTR_COLOR_BANDS.map((band) => (
          <label key={band.key} className="attr-color-swatch">
            <input
              type="color"
              aria-label={`${band.label} band ${band.range}`}
              value={palette[band.key]}
              onChange={(event) => updateBand(band.key, event.target.value)}
            />
            <span>
              <b>{band.label}</b>
              <small>{band.range}</small>
            </span>
          </label>
        ))}
        <Button type="button" variant="outline" size="sm" onClick={reset}>
          Reset FM defaults
        </Button>
      </div>
    </article>
  );
}
