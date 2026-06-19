import prompts from "prompts";
import { SERVER_KEY, LOOVIE_MCP_URL } from "../constants.js";
import { log } from "./log.js";
import {
  type JsonObject,
  atomicWriteJson,
  backupOnce,
  deepEqual,
  deepMerge,
  readJsonIfExists,
} from "./jsonFile.js";
import type { InstallContext, InstallResult } from "../types.js";

/** Human-readable summary of an MCP entry for prompts/skip messages. */
function describeEntry(entry: JsonObject | undefined): string {
  if (!entry) return "<unknown>";
  if (typeof entry.url === "string") return entry.url;
  if (typeof entry.command === "string") {
    const args = Array.isArray(entry.args) ? ` ${(entry.args as unknown[]).join(" ")}` : "";
    return `${entry.command}${args}`;
  }
  return "<custom entry>";
}

/**
 * Generic install path for clients whose config uses the standard
 * `mcpServers.<name>` shape (Cursor, Claude Desktop, VS Code).
 *
 * Returns one of: already-installed, installed, skipped (user declined).
 */
export async function installMcpServerEntry(args: {
  filePath: string;
  ctx: InstallContext;
  entryKey?: string;
  entryValue?: JsonObject;
  /** Wrapping key — defaults to "mcpServers". VS Code, Cursor, Claude Desktop all share it. */
  parentKey?: string;
  clientLabel: string;
}): Promise<InstallResult> {
  const {
    filePath,
    ctx,
    entryKey = SERVER_KEY,
    entryValue = { url: LOOVIE_MCP_URL },
    parentKey = "mcpServers",
    clientLabel,
  } = args;

  const existing = (await readJsonIfExists(filePath)) ?? {};
  const parent = (existing[parentKey] as JsonObject | undefined) ?? {};
  const current = parent[entryKey] as JsonObject | undefined;

  if (current) {
    // Idempotent when the existing entry already matches what we'd write —
    // works for both URL-shaped (Cursor, VS Code) and command-shaped
    // (Claude Desktop via the mcp-remote bridge) entries.
    if (deepEqual(current, entryValue)) {
      return { kind: "already-installed", detail: `${clientLabel}: already configured (${filePath})` };
    }
    if (ctx.force) {
      log.dim(`  ${clientLabel}: replacing existing "${entryKey}" entry (--force)`);
    } else if (ctx.interactive) {
      const { replace } = await prompts({
        type: "confirm",
        name: "replace",
        message: `${clientLabel} already has an "${entryKey}" entry (${describeEntry(current)}). Replace it?`,
        initial: false,
      });
      if (!replace) {
        return { kind: "skipped", reason: `${clientLabel}: user declined to replace existing entry` };
      }
    } else {
      return {
        kind: "skipped",
        reason: `${clientLabel}: existing entry differs (${describeEntry(current)}). Re-run interactively or pass --force to replace.`,
      };
    }
  }

  if (ctx.verbose) log.dim(`  would write: ${filePath}`);

  const backup = await backupOnce(filePath, ctx);
  if (backup && ctx.verbose) log.dim(`  backed up to: ${backup}`);

  const merged = deepMerge(existing, { [parentKey]: { [entryKey]: entryValue } });
  await atomicWriteJson(filePath, merged);
  return { kind: "installed", detail: `${clientLabel}: wrote ${filePath}` };
}

/**
 * Inverse — remove our entry only, leave the file otherwise untouched.
 * If the parent map becomes empty, leave it as `{}` (don't delete sibling keys).
 */
export async function uninstallMcpServerEntry(args: {
  filePath: string;
  ctx: InstallContext;
  entryKey?: string;
  parentKey?: string;
  clientLabel: string;
}): Promise<InstallResult> {
  const { filePath, ctx, entryKey = SERVER_KEY, parentKey = "mcpServers", clientLabel } = args;
  const existing = await readJsonIfExists(filePath);
  if (!existing) {
    return { kind: "skipped", reason: `${clientLabel}: no config file at ${filePath}` };
  }
  const parent = existing[parentKey] as JsonObject | undefined;
  if (!parent || !(entryKey in parent)) {
    return { kind: "skipped", reason: `${clientLabel}: not installed` };
  }
  const backup = await backupOnce(filePath, ctx);
  if (backup && ctx.verbose) log.dim(`  backed up to: ${backup}`);
  delete parent[entryKey];
  existing[parentKey] = parent;
  await atomicWriteJson(filePath, existing);
  return { kind: "installed", detail: `${clientLabel}: removed ${entryKey} from ${filePath}` };
}
