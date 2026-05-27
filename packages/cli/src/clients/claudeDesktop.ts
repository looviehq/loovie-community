import { promises as fs } from "node:fs";
import { LOOVIE_MCP_URL, SERVER_KEY } from "../constants.js";
import type { ClientPlugin, DoctorResult } from "../types.js";
import { claudeDesktopConfigPath } from "../util/paths.js";
import {
  installMcpServerEntry,
  uninstallMcpServerEntry,
} from "../util/mcpServers.js";
import { readJsonIfExists, type JsonObject } from "../util/jsonFile.js";
import { log } from "../util/log.js";

export const claudeDesktop: ClientPlugin = {
  id: "claude-desktop",
  label: "Claude Desktop",
  tier: "compatible",
  async detect() {
    try {
      await fs.access(claudeDesktopConfigPath());
      return true;
    } catch {
      return null;
    }
  },
  async install(ctx) {
    const filePath = claudeDesktopConfigPath();
    const res = await installMcpServerEntry({ filePath, ctx, clientLabel: "Claude Desktop" });
    if (res.kind === "installed") {
      log.warn("Restart Claude Desktop for the new MCP server to load.");
    }
    return res;
  },
  async uninstall(ctx) {
    const filePath = claudeDesktopConfigPath();
    return uninstallMcpServerEntry({ filePath, ctx, clientLabel: "Claude Desktop" });
  },
  async doctor(): Promise<DoctorResult> {
    const filePath = claudeDesktopConfigPath();
    const parsed = await readJsonIfExists(filePath);
    const entry = (parsed?.mcpServers as JsonObject | undefined)?.[SERVER_KEY] as
      | JsonObject
      | undefined;
    return {
      client: "claude-desktop",
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
