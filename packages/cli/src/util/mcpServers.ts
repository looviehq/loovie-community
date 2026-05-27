import prompts from "prompts";
import { SERVER_KEY, LOOVIE_MCP_URL } from "../constants.js";
import { log } from "./log.js";
import {
  type JsonObject,
  atomicWriteJson,
  backupOnce,
  deepMerge,
  readJsonIfExists,
} from "./jsonFile.js";
import type { InstallContext, InstallResult } from "../types.js";

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
    const sameUrl =
      typeof current.url === "string" && current.url === LOOVIE_MCP_URL;
    if (sameUrl) {
      return { kind: "already-installed", detail: `${clientLabel}: already configured (${filePath})` };
    }
    if (ctx.interactive) {
      const { replace } = await prompts({
        type: "confirm",
        name: "replace",
        message: `${clientLabel} already has an "${entryKey}" entry pointing to ${String(current.url ?? "<unknown>")}. Replace it?`,
        initial: false,
      });
      if (!replace) {
        return { kind: "skipped", reason: `${clientLabel}: user declined to replace existing entry` };
      }
    } else {
      return {
        kind: "skipped",
        reason: `${clientLabel}: existing entry differs (${String(current.url ?? "<unknown>")}). Re-run interactively or pass --force (not yet implemented) to replace.`,
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
