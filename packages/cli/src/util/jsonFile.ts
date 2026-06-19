import { promises as fs } from "node:fs";
import * as path from "node:path";
import { randomBytes } from "node:crypto";
import type { InstallContext } from "../types.js";

export type JsonObject = { [k: string]: unknown };

export async function readJsonIfExists(filePath: string): Promise<JsonObject | null> {
  try {
    const raw = await fs.readFile(filePath, "utf8");
    const trimmed = raw.trim();
    if (!trimmed) return {};
    const parsed = JSON.parse(trimmed);
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error(`Expected JSON object at ${filePath}`);
    }
    return parsed as JsonObject;
  } catch (err: unknown) {
    if ((err as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw err;
  }
}

/**
 * Atomic write: write to a temp sibling, then rename. The OS guarantees
 * either the old or new contents are observable, never a half-written file.
 */
export async function atomicWriteJson(filePath: string, data: JsonObject): Promise<void> {
  const dir = path.dirname(filePath);
  await fs.mkdir(dir, { recursive: true });
  const tmp = path.join(dir, `.${path.basename(filePath)}.${randomBytes(6).toString("hex")}.tmp`);
  const body = `${JSON.stringify(data, null, 2)}\n`;
  await fs.writeFile(tmp, body, "utf8");
  await fs.rename(tmp, filePath);
}

/**
 * Back up the file once per install run. Re-runs are no-ops so we don't
 * spam the user's directory with N backups for N clients.
 */
export async function backupOnce(filePath: string, ctx: InstallContext): Promise<string | null> {
  if (ctx.backedUp.has(filePath)) return null;
  ctx.backedUp.add(filePath);
  try {
    await fs.access(filePath);
  } catch {
    return null; // nothing to back up
  }
  const backupPath = `${filePath}.loovie-backup-${ctx.backupSuffix}`;
  await fs.copyFile(filePath, backupPath);
  return backupPath;
}

/**
 * Deep-merge two plain JSON objects. Arrays are replaced (not concatenated)
 * since merging arrays semantically is rarely what users want for config.
 */
export function deepMerge(base: JsonObject, patch: JsonObject): JsonObject {
  const out: JsonObject = { ...base };
  for (const [k, v] of Object.entries(patch)) {
    const existing = out[k];
    if (
      v &&
      typeof v === "object" &&
      !Array.isArray(v) &&
      existing &&
      typeof existing === "object" &&
      !Array.isArray(existing)
    ) {
      out[k] = deepMerge(existing as JsonObject, v as JsonObject);
    } else {
      out[k] = v;
    }
  }
  return out;
}

/**
 * Structural equality for JSON-compatible values. Used to decide whether an
 * existing MCP entry already matches what we'd write (idempotent install).
 * Object key order is ignored; array order is significant.
 */
export function deepEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (a === null || b === null || typeof a !== "object" || typeof b !== "object") {
    return false;
  }
  const aArr = Array.isArray(a);
  const bArr = Array.isArray(b);
  if (aArr !== bArr) return false;
  if (aArr && bArr) {
    if (a.length !== b.length) return false;
    return a.every((v, i) => deepEqual(v, b[i]));
  }
  const ao = a as JsonObject;
  const bo = b as JsonObject;
  const aKeys = Object.keys(ao);
  const bKeys = Object.keys(bo);
  if (aKeys.length !== bKeys.length) return false;
  return aKeys.every((k) => k in bo && deepEqual(ao[k], bo[k]));
}

export function newBackupSuffix(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}` +
    `-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`
  );
}
