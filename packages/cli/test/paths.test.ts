import { describe, it, expect } from "vitest";
import {
  claudeDesktopConfigPath,
  continueConfigPath,
  cursorConfigPath,
  opencodeConfigPath,
  vscodeProjectConfigPath,
} from "../src/util/paths.js";

describe("platform path resolution", () => {
  it("Claude Desktop on macOS", () => {
    expect(claudeDesktopConfigPath("darwin", {}, "/Users/jane")).toBe(
      "/Users/jane/Library/Application Support/Claude/claude_desktop_config.json",
    );
  });

  it("Claude Desktop on Windows uses %APPDATA%", () => {
    expect(
      claudeDesktopConfigPath("win32", { APPDATA: "C:\\Users\\jane\\AppData\\Roaming" }, "C:\\Users\\jane"),
    ).toMatch(/Claude[\\/]claude_desktop_config\.json$/);
  });

  it("Claude Desktop on Linux respects XDG_CONFIG_HOME", () => {
    expect(claudeDesktopConfigPath("linux", { XDG_CONFIG_HOME: "/x" }, "/home/jane")).toBe(
      "/x/Claude/claude_desktop_config.json",
    );
  });

  it("Claude Desktop on Linux defaults to ~/.config", () => {
    expect(claudeDesktopConfigPath("linux", {}, "/home/jane")).toBe(
      "/home/jane/.config/Claude/claude_desktop_config.json",
    );
  });

  it("Cursor global vs project", () => {
    expect(cursorConfigPath("global", "/cwd", "/home/jane")).toBe("/home/jane/.cursor/mcp.json");
    expect(cursorConfigPath("project", "/cwd", "/home/jane")).toBe("/cwd/.cursor/mcp.json");
  });

  it("VS Code is always project-scoped", () => {
    expect(vscodeProjectConfigPath("/repo")).toBe("/repo/.vscode/mcp.json");
  });

  it("Continue config", () => {
    expect(continueConfigPath("/home/jane")).toBe("/home/jane/.continue/config.json");
  });

  it("OpenCode on linux respects XDG", () => {
    expect(opencodeConfigPath("linux", { XDG_CONFIG_HOME: "/x" }, "/home/jane")).toBe(
      "/x/opencode/opencode.json",
    );
  });

  it("OpenCode on Windows uses %APPDATA%", () => {
    expect(opencodeConfigPath("win32", { APPDATA: "C:\\u\\AppData\\Roaming" }, "C:\\u")).toMatch(
      /opencode[\\/]opencode\.json$/,
    );
  });
});
