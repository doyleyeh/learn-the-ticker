import { compile } from "json-schema-to-typescript";
import { readFile, writeFile } from "node:fs/promises";
const schema = JSON.parse(await readFile(new URL("../contracts/desktop.schema.json", import.meta.url), "utf8"));
const output = await compile(schema, "DesktopContracts", { bannerComment: "/* Generated from backend/app/contracts.py. Do not edit. */", additionalProperties: false });
const target = new URL("../apps/desktop/src/contracts.ts", import.meta.url);
const args = process.argv.slice(2);
if (args.some((arg) => arg !== "--check")) throw new Error("Usage: node scripts/generate_types.mjs [--check]");
if (args.includes("--check")) {
  const stored = await readFile(target, "utf8").catch(() => "");
  if (stored.replaceAll("\r\n", "\n") !== output.replaceAll("\r\n", "\n")) {
    console.error("TypeScript contract drift: run node scripts/generate_types.mjs.");
    process.exitCode = 1;
  } else console.log("TypeScript matches generated JSON Schema.");
} else await writeFile(target, output);
