import prompts from "prompts";
import { LOOVIE_MCP_URL, SERVER_KEY } from "../constants.js";
import type { ClientPlugin, DoctorResult, InstallResult } from "../types.js";
import { opencodeConfigPath } from "../util/paths.js";
import {
  atomicWriteJson,
  backupOnce,
  deepMerge,
  readJsonIfExists,
  type JsonObject,
} from "../util/jsonFile.js";
import { log } from "../util/log.js";

/**
 * OpenCode uses `opencode.json` with a top-level `mcp` map (not `mcpServers`):
 *   {
 *     "$schema": "https://opencode.ai/config.json",
 *     "mcp": { "loovie": { "type": "remote", "url": "...", "enabled": true } }
 *   }
 * Source: https://opencode.ai/docs (config reference).
 */
const PARENT_KEY = "mcp";
const SCHEMA_URL = "https://opencode.ai/config.json";

export const opencode: ClientPlugin = {
  id: "opencode",
  label: "OpenCode",
  tier: "compatible",
  async detect() {
    return null;
  },
  async install(ctx): Promise<InstallResult> {
    const filePath = opencodeConfigPath();
    const existing = (await readJsonIfExists(filePath)) ?? {};
    const parent = (existing[PARENT_KEY] as JsonObject | undefined) ?? {};
    const current = parent[SERVER_KEY] as JsonObject | undefined;

    if (current) {
      if (current.url === LOOVIE_MCP_URL && current.type === "remote") {
        return { kind: "already-installed", detail: `OpenCode: already configured (${filePath})` };
      }
      if (ctx.force) {
        log.dim(`  OpenCode: replacing existing "${SERVER_KEY}" entry (--force)`);
      } else if (ctx.interactive) {
        const { replace } = await prompts({
          type: "confirm",
          name: "replace",
          message: `OpenCode already has an "${SERVER_KEY}" entry. Replace it?`,
          initial: false,
        });
        if (!replace) {
          return { kind: "skipped", reason: "OpenCode: user declined to replace existing entry" };
        }
      } else {
        return { kind: "skipped", reason: "OpenCode: existing entry differs — re-run interactively or pass --force" };
      }
    }

    if (ctx.verbose) log.dim(`  would write: ${filePath}`);
    const backup = await backupOnce(filePath, ctx);
    if (backup && ctx.verbose) log.dim(`  backed up to: ${backup}`);

    const patch: JsonObject = {
      $schema: SCHEMA_URL,
      [PARENT_KEY]: {
        [SERVER_KEY]: { type: "remote", url: LOOVIE_MCP_URL, enabled: true },
      },
    };
    await atomicWriteJson(filePath, deepMerge(existing, patch));
    return { kind: "installed", detail: `OpenCode: wrote ${filePath}` };
  },
  async uninstall(ctx) {
    const filePath = opencodeConfigPath();
    const existing = await readJsonIfExists(filePath);
    if (!existing) return { kind: "skipped", reason: `OpenCode: no config at ${filePath}` };
    const parent = existing[PARENT_KEY] as JsonObject | undefined;
    if (!parent || !(SERVER_KEY in parent)) {
      return { kind: "skipped", reason: "OpenCode: not installed" };
    }
    const backup = await backupOnce(filePath, ctx);
    if (backup && ctx.verbose) log.dim(`  backed up to: ${backup}`);
    delete parent[SERVER_KEY];
    existing[PARENT_KEY] = parent;
    await atomicWriteJson(filePath, existing);
    return { kind: "installed", detail: `OpenCode: removed ${SERVER_KEY} from ${filePath}` };
  },
  async doctor(): Promise<DoctorResult> {
    const filePath = opencodeConfigPath();
    const parsed = await readJsonIfExists(filePath);
    const entry = (parsed?.[PARENT_KEY] as JsonObject | undefined)?.[SERVER_KEY] as
      | JsonObject
      | undefined;
    return {
      client: "opencode",
      configPath: filePath,
      exists: parsed !== null,
      loovieConfigured: !!entry,
      url: typeof entry?.url === "string" ? entry.url : null,
      notes:
        entry && entry.url !== LOOVIE_MCP_URL
          ? [`URL mismatch (expected ${LOOVIE_MCP_URL})`]
          : [],
    };
  },
};
