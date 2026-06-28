/**
 * Fix class syntax after object-literal conversion: remove method commas, fix field colons.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

/** @param {string} dir @returns {string[]} */
function walk(dir) {
  const out = [];
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) out.push(...walk(p));
    else if (ent.name.endsWith('.js')) out.push(p);
  }
  return out;
}

/** @param {string} s */
function fixClassSyntax(s) {
  if (!/^class \w+/m.test(s) && !/export const \w+ = new \w+/m.test(s)) return s;

  let out = s;
  // Method trailing commas before next member
  out = out.replace(/\}(\s*),(\s*\n\s*(?:\/\*\*|async |#\w+|get[A-Z]|\w+\())/g, '}$1$2');
  // Method trailing comma before class close
  out = out.replace(/\}(\s*),(\s*\n\})/g, '}$1$2');
  // Public field colon syntax (not in object literals - heuristic: at class indent)
  out = out.replace(/^(\s{2})(\w+)\s*:\s*([^,\n]+),$/gm, '$1$2 = $3;');
  return out;
}

let n = 0;
for (const fp of walk(path.join(root, 'src'))) {
  const s = fs.readFileSync(fp, 'utf8');
  const out = fixClassSyntax(s);
  if (out !== s) {
    fs.writeFileSync(fp, out);
    console.log('Fixed:', path.relative(root, fp));
    n++;
  }
}
console.log(`Done: ${n} files`);
