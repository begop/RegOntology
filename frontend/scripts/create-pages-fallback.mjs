import { copyFile, readFile } from "node:fs/promises";
import { resolve } from "node:path";

const outputDirectory = resolve("dist");
const indexPath = resolve(outputDirectory, "index.html");
const fallbackPath = resolve(outputDirectory, "404.html");
const expectedBase = "/RegOntology/";
const indexHtml = await readFile(indexPath, "utf8");

if (!indexHtml.includes(expectedBase)) {
  throw new Error(`Pages build is missing the expected ${expectedBase} asset base.`);
}

await copyFile(indexPath, fallbackPath);
console.log(`GitHub Pages fallback created: ${fallbackPath}`);
