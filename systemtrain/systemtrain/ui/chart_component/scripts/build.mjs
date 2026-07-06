import { access, readFile } from "node:fs/promises";
import { constants } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const templatePath = resolve(root, "template.py");
const packagePath = resolve(root, "package.json");

await access(templatePath, constants.R_OK);
await access(packagePath, constants.R_OK);

const template = await readFile(templatePath, "utf8");
if (!template.includes("lightweight-charts") || !template.includes("createChart")) {
  throw new Error("Lightweight Charts template is missing expected runtime hooks.");
}

console.log("Chart component build validation passed.");
