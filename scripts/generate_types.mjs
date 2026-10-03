import { compile } from "json-schema-to-typescript";
import { readFile, writeFile } from "node:fs/promises";
const schema = JSON.parse(await readFile(new URL("../contracts/desktop.schema.json", import.meta.url), "utf8"));
const output = await compile(schema, "DesktopContracts", { bannerComment: "/* Generated from backend/app/contracts.py. Do not edit. */", additionalProperties: false });
await writeFile(new URL("../apps/desktop/src/contracts.ts", import.meta.url), output);
