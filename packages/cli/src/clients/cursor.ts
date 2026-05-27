import { promises as fs } from "node:fs";
import { LOOVIE_MCP_URL, SERVER_KEY } from "../constants.js";
import type { ClientPlugin, DoctorResult } from "../types.js";
import { cursorConfigPath } from "../util/paths.js";
import {
  installMcpServerEntry,
  uninstallMcpServerEntry,
} from "../util/mcpServers.js";
import { readJsonIfExists, type JsonObject } from "../util/jsonFile.js";

export const cursor: ClientPlugin = {
  id: "cursor",
  label: "Cursor",
  tier: "official",
  async detect() {
    // Best-effort: presence of ~/.cursor dir.
    try {
      await fs.access(cursorConfigPath("global", process.cwd()).replace(/mcp\.json$/, ""));
      return true;
    } catch {
      return null;
    }
  },
  async install(ctx) {
    const filePath = cursorConfigPath(ctx.scope, ctx.cwd);
    return installMcpServerEntry({ filePath, ctx, clientLabel: "Cursor" });
  },
  async uninstall(ctx) {
    const filePath = cursorConfigPath(ctx.scope, ctx.cwd);
    return uninstallMcpServerEntry({ filePath, ctx, clientLabel: "Cursor" });
  },
  async doctor(ctx): Promise<DoctorResult> {
    const filePath = cursorConfigPath(ctx.scope, ctx.cwd);
    const parsed = await readJsonIfExists(filePath);
    const entry = (parsed?.mcpServers as JsonObject | undefined)?.[SERVER_KEY] as
      | JsonObject
      | undefined;
    return {
      client: "cursor",
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
