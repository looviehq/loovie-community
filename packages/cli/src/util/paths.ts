import * as os from "node:os";
import * as path from "node:path";

export type Platform = "darwin" | "win32" | "linux";

export function getPlatform(): Platform {
  const p = process.platform;
  if (p === "darwin" || p === "win32" || p === "linux") return p;
  // Fall back to linux semantics on BSDs etc — best-effort.
  return "linux";
}

/**
 * Claude Desktop config path per platform.
 * Sources:
 *  - macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
 *  - Windows: %APPDATA%/Claude/claude_desktop_config.json
 *  - Linux: ~/.config/Claude/claude_desktop_config.json (unofficial — Anthropic
 *    doesn't ship Claude Desktop for Linux, but the community uses this path).
 */
export function claudeDesktopConfigPath(
  platform: Platform = getPlatform(),
  env: NodeJS.ProcessEnv = process.env,
  home: string = os.homedir(),
): string {
  switch (platform) {
    case "darwin":
      return path.join(home, "Library", "Application Support", "Claude", "claude_desktop_config.json");
    case "win32": {
      const appData = env.APPDATA ?? path.join(home, "AppData", "Roaming");
      return path.join(appData, "Claude", "claude_desktop_config.json");
    }
    case "linux":
    default: {
      const xdg = env.XDG_CONFIG_HOME ?? path.join(home, ".config");
      return path.join(xdg, "Claude", "claude_desktop_config.json");
    }
  }
}

export function cursorConfigPath(scope: "global" | "project", cwd: string, home = os.homedir()): string {
  return scope === "project"
    ? path.join(cwd, ".cursor", "mcp.json")
    : path.join(home, ".cursor", "mcp.json");
}

export function vscodeProjectConfigPath(cwd: string): string {
  return path.join(cwd, ".vscode", "mcp.json");
}

export function continueConfigPath(home = os.homedir()): string {
  return path.join(home, ".continue", "config.json");
}

export function opencodeConfigPath(
  platform: Platform = getPlatform(),
  env: NodeJS.ProcessEnv = process.env,
  home: string = os.homedir(),
): string {
  // OpenCode primary config is opencode.json at the project or home root.
  // Per docs (https://opencode.ai/docs) the global location is ~/.config/opencode/opencode.json.
  if (platform === "win32") {
    const appData = env.APPDATA ?? path.join(home, "AppData", "Roaming");
    return path.join(appData, "opencode", "opencode.json");
  }
  const xdg = env.XDG_CONFIG_HOME ?? path.join(home, ".config");
  return path.join(xdg, "opencode", "opencode.json");
}
