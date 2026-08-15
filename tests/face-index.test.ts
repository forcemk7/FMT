import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import {
  buildFaceIndex,
  resolveFacePath,
} from "../shared/faces/face-index.ts";

const tmpRoots: string[] = [];
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
  "base64",
);

const SEIMEN = 2000175080;
const KIZZA = 2002185604;

function makeRoot(): string {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "fmt-faces-"));
  tmpRoots.push(root);
  return root;
}

function writeRegenConfig(dir: string, fromName: string, uid: number): void {
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(
    path.join(dir, "config.xml"),
    `<record from="${fromName}" to="graphics/pictures/person/r-${uid}/portrait"/>\n`,
  );
}

afterEach(() => {
  for (const root of tmpRoots.splice(0)) {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

describe("face index", () => {
  it("resolves cutout face_{uid}.png and regen XML; config-only duplicate pack does not steal the uid", async () => {
    const root = makeRoot();

    const cutoutFaces = path.join(
      root,
      "Cutout_Player_Faces_Megapack_2026.08",
      "faces",
    );
    fs.mkdirSync(cutoutFaces, { recursive: true });
    fs.writeFileSync(path.join(cutoutFaces, `face_${SEIMEN}.png`), PNG);
    fs.writeFileSync(
      path.join(cutoutFaces, "config.xml"),
      Buffer.concat([
        Buffer.from("<record/>\n"),
        Buffer.alloc(2_000_001, 0x20),
      ]),
    );

    const emptyRegen = path.join(
      root,
      "NG Regens Newgens Megapack",
      "EastAfrica",
    );
    writeRegenConfig(emptyRegen, "PP14EastAfrica0540", KIZZA);

    const realRegen = path.join(
      root,
      "NGRegens_Newgens_Megapack",
      "EastAfrica",
    );
    writeRegenConfig(realRegen, "PP14EastAfrica0540", KIZZA);
    fs.writeFileSync(path.join(realRegen, "PP14EastAfrica0540.png"), PNG);

    const idx = await buildFaceIndex(root);

    const seimen = resolveFacePath(idx, SEIMEN);
    expect(seimen).toBe(path.join(cutoutFaces, `face_${SEIMEN}.png`));

    const kizza = resolveFacePath(idx, KIZZA);
    expect(kizza).toBe(path.join(realRegen, "PP14EastAfrica0540.png"));

    expect(resolveFacePath(idx, 1)).toBeNull();
  });
});
