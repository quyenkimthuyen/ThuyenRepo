/**
 * Convert object-literal modules with # private members to ES classes.
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
function convert(s, name, isExportConst) {
  let out = s;
  if (isExportConst) {
    out = out.replace(`export const ${name} = {`, `class ${name} {`);
    out = out.replace(/\};(\s*)$/, `}\n\nexport const ${name} = new ${name}();$1`);
  } else {
    out = out.replace(`const ${name} = {`, `class ${name} {`);
    out = out.replace(/\};\s*\n\s*export default \w+\s*;/, `}\n\nexport default new ${name}();`);
  }

  out = out.replace(/(#\w+)\s*:\s*([^,\n]+),/g, '$1 = $2;');
  out = out.replace(/\},(\n\s+(?:\/\*\*|async |get[A-Z]|#\w+|\w+\())/g, '}$1');
  return out;
}

/** @param {string} fp */
function fixFile(fp) {
  const s = fs.readFileSync(fp, 'utf8');
  if (!/#\w+/.test(s)) return false;
  if (/^export default class /m.test(s)) return false;

  const exportConst = s.match(/export const (\w+) = \{/);
  const defaultConst = s.match(/(?:^|\n)const (\w+) = \{/);

  let name;
  let isExportConst = false;

  if (exportConst && s.includes(`#`)) {
    name = exportConst[1];
    isExportConst = true;
  } else if (defaultConst) {
    name = defaultConst[1];
  } else {
    return false;
  }

  const bodyStart = s.indexOf(isExportConst ? `export const ${name} = {` : `const ${name} = {`);
  if (bodyStart < 0) return false;

  const out = convert(s, name, isExportConst);
  if (out === s) return false;

  fs.writeFileSync(fp, out);
  console.log('Fixed:', path.relative(root, fp));
  return true;
}

let n = 0;
for (const fp of walk(path.join(root, 'src'))) {
  if (fixFile(fp)) n++;
}
console.log(`Done: ${n} files`);
