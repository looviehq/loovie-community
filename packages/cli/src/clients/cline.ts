import { LOOVIE_MCP_URL, SERVER_KEY } from "../constants.js";
import type { ClientPlugin, DoctorResult } from "../types.js";

/**
 * Cline reads MCP server config from VS Code extension settings, which lives
 * in a deep settings.json key alongside many unrelated things. Mutating it
 * blindly is dangerous — we surface manual instructions instead.
 */
export const cline: ClientPlugin = {
  id: "cline",
  label: "Cline",
  tier: "compatible",
  async detect() {
    return null;
  },
  async install() {
    const block = JSON.stringify(
      { mcpServers: { [SERVER_KEY]: { url: LOOVIE_MCP_URL } } },
      null,
      2,
    );
    return {
      kind: "manual",
      instructions:
        "Cline manages MCP servers from inside VS Code. To install Loovie:\n" +
        "  1. Open the Cline panel in VS Code.\n" +
        "  2. Click the MCP Servers icon (top-right of the Cline panel).\n" +
        "  3. Click 'Edit MCP Settings' and paste:\n\n" +
        block.replace(/^/gm, "     "),
    };
  },
  async uninstall() {
    return {
      kind: "manual",
      instructions:
        "Open Cline → MCP Servers → Edit MCP Settings and remove the `loovie` entry under `mcpServers`.",
    };
  },
  async doctor(): Promise<DoctorResult> {
    return {
      client: "cline",
      configPath: null,
      exists: false,
      loovieConfigured: false,
      url: null,
      notes: ["Cline config lives in VS Code settings — not auto-detected."],
    };
  },
};
