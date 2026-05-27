import { LOOVIE_MCP_URL, SERVER_KEY } from "../constants.js";
import type { ClientPlugin, DoctorResult, InstallResult } from "../types.js";
import { vscodeProjectConfigPath } from "../util/paths.js";
import {
  installMcpServerEntry,
  uninstallMcpServerEntry,
} from "../util/mcpServers.js";
import { readJsonIfExists, type JsonObject } from "../util/jsonFile.js";

export const vscode: ClientPlugin = {
  id: "vscode",
  label: "VS Code (MCP)",
  tier: "compatible",
  async detect() {
    // No reliable global detection — VS Code MCP is workspace-scoped.
    return null;
  },
  async install(ctx): Promise<InstallResult> {
    if (ctx.scope !== "project") {
      return {
        kind: "manual",
        instructions:
          "VS Code MCP is workspace-scoped. Re-run from your repo root with `--project`:\n" +
          "    npx -y @loovie/mcp install --client vscode --project",
      };
    }
    const filePath = vscodeProjectConfigPath(ctx.cwd);
    return installMcpServerEntry({ filePath, ctx, clientLabel: "VS Code" });
  },
  async uninstall(ctx) {
    const filePath = vscodeProjectConfigPath(ctx.cwd);
    return uninstallMcpServerEntry({ filePath, ctx, clientLabel: "VS Code" });
  },
  async doctor(ctx): Promise<DoctorResult> {
    const filePath = vscodeProjectConfigPath(ctx.cwd);
    const parsed = await readJsonIfExists(filePath);
    const entry = (parsed?.mcpServers as JsonObject | undefined)?.[SERVER_KEY] as
      | JsonObject
      | undefined;
    return {
      client: "vscode",
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
