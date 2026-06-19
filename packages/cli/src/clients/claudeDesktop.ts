import { promises as fs } from "node:fs";
import { CLAUDE_DESKTOP_ENTRY, LOOVIE_MCP_URL, SERVER_KEY } from "../constants.js";
import type { ClientPlugin, DoctorResult } from "../types.js";
import { claudeDesktopConfigPath } from "../util/paths.js";
import {
  installMcpServerEntry,
  uninstallMcpServerEntry,
} from "../util/mcpServers.js";
import { readJsonIfExists, type JsonObject } from "../util/jsonFile.js";
import { log } from "../util/log.js";

/** True when an entry already points at the Loovie endpoint, in either the
 *  modern Connectors `{ url }` shape or the mcp-remote bridge shape. */
function isLoovieEntry(entry: JsonObject | undefined): boolean {
  if (!entry) return false;
  if (entry.url === LOOVIE_MCP_URL) return true;
  return Array.isArray(entry.args) && (entry.args as unknown[]).includes(LOOVIE_MCP_URL);
}

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
    // Claude Desktop's config file is stdio-only — a bare `url` entry never
    // connects. Write the mcp-remote bridge instead (same as the .dxt bundle).
    const res = await installMcpServerEntry({
      filePath,
      ctx,
      entryValue: { ...CLAUDE_DESKTOP_ENTRY, args: [...CLAUDE_DESKTOP_ENTRY.args] },
      clientLabel: "Claude Desktop",
    });
    if (res.kind === "installed") {
      log.dim("  Bridged via mcp-remote (npx). Requires Node on PATH.");
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
      url: typeof entry?.url === "string" ? entry.url : entry ? LOOVIE_MCP_URL : null,
      notes:
        entry && !isLoovieEntry(entry)
          ? [`entry does not point at ${LOOVIE_MCP_URL}`]
          : [],
    };
  },
};
