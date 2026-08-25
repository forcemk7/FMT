/**
 * One-shot rebrand: user-facing FMT → FMT.
 * Run: node tools/rebrand-fmt.js
 */
const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "..");
const skip = new Set(["node_modules", ".next", "target", ".git"]);

const pairs = [
  [/FMT/g, "FMT"],
  [/FMT/g, "FMT"],
  [/fmt/g, "fmt"],
  [/com\.glassscout\.fm26/g, "com.fmt.fm26"],
  [/fmt-load-progress/g, "fmt-load-progress"],
  [/Install FMT for Windows/g, "Install FMT for Windows"],
  [/Download FMT for Windows/g, "Download FMT for Windows"],
];

function walk(dir, out = []) {
  for (const name of fs.readdirSync(dir)) {
    if (skip.has(name)) continue;
    const p = path.join(dir, name);
    const st = fs.statSync(p);
    if (st.isDirectory()) walk(p, out);
    else if (/\.(tsx?|jsx?|json|md|ps1|cmd|css|toml)$/i.test(name)) out.push(p);
  }
  return out;
}

let changed = 0;
for (const file of walk(root)) {
  // Keep NOTICE / research docs attributing upstream? Still rebrand product strings.
  if (file.includes(`${path.sep}NOTICE`)) continue;
  let text = fs.readFileSync(file, "utf8");
  const before = text;
  for (const [re, to] of pairs) text = text.replace(re, to);
  if (text !== before) {
    fs.writeFileSync(file, text);
    changed++;
    console.log("updated", path.relative(root, file));
  }
}
console.log("files changed:", changed);
