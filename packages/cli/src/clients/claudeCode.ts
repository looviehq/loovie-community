import { spawn } from "node:child_process";
import { promises as fs } from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import {
  CLAUDE_CODE_MARKETPLACE,
  CLAUDE_CODE_MARKETPLACE_NAME,
  CLAUDE_CODE_PLUGIN,
  LOOVIE_MCP_URL,
  SERVER_KEY,
} from "../constants.js";
import type { ClientPlugin, DoctorResult, InstallResult } from "../types.js";
import { readJsonIfExists, type JsonObject } from "../util/jsonFile.js";

function which(bin: string): Promise<string | null> {
  return new Promise((resolve) => {
    const cmd = process.platform === "win32" ? "where" : "which";
    const child = spawn(cmd, [bin], { stdio: ["ignore", "pipe", "ignore"] });
    let out = "";
    child.stdout.on("data", (d) => (out += d.toString()));
    child.on("close", (code) => resolve(code === 0 ? out.trim().split(/\r?\n/)[0] || null : null));
    child.on("error", () => resolve(null));
  });
}

function run(cmd: string, args: string[]): Promise<{ code: number; stdout: string; stderr: string }> {
  return new Promise((resolve) => {
    const child = spawn(cmd, args, { stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d) => (stdout += d.toString()));
    child.stderr.on("data", (d) => (stderr += d.toString()));
    child.on("close", (code) => resolve({ code: code ?? 1, stdout, stderr }));
    child.on("error", (e) => resolve({ code: 1, stdout, stderr: String(e) }));
  });
}

export const claudeCode: ClientPlugin = {
  id: "claude-code",
  label: "Claude Code",
  tier: "official",
  async detect() {
    return (await which("claude")) !== null;
  },
  async install(): Promise<InstallResult> {
    const bin = await which("claude");
    if (!bin) {
      return {
        kind: "manual",
        instructions:
          "Claude Code CLI not found. Install it from https://docs.claude.com/en/docs/claude-code, then re-run:\n" +
          `    claude plugin marketplace add ${CLAUDE_CODE_MARKETPLACE}\n` +
          `    claude plugin install ${CLAUDE_CODE_PLUGIN}`,
      };
    }
    const r1 = await run("claude", ["plugin", "marketplace", "add", CLAUDE_CODE_MARKETPLACE]);
    if (r1.code !== 0 && !/already/i.test(r1.stderr + r1.stdout)) {
      return { kind: "error", message: `claude plugin marketplace add failed: ${r1.stderr || r1.stdout}` };
    }
    const r2 = await run("claude", ["plugin", "install", CLAUDE_CODE_PLUGIN]);
    if (r2.code !== 0) {
      if (/already installed/i.test(r2.stderr + r2.stdout)) {
        return { kind: "already-installed", detail: "Claude Code: plugin already installed" };
      }
      return { kind: "error", message: `claude plugin install failed: ${r2.stderr || r2.stdout}` };
    }
    return { kind: "installed", detail: "Claude Code: installed via marketplace" };
  },
  async update(ctx): Promise<InstallResult> {
    const bin = await which("claude");
    if (!bin) {
      return {
        kind: "manual",
        instructions:
          "Claude Code CLI not found. To update manually, run:\n" +
          `    claude plugin marketplace update ${CLAUDE_CODE_MARKETPLACE_NAME}\n` +
          `    claude plugin update ${CLAUDE_CODE_PLUGIN}`,
      };
    }
    // Refresh the marketplace cache so the newest plugin (skills, commands,
    // MCP block) is visible, then update the installed plugin.
    const r1 = await run("claude", ["plugin", "marketplace", "update", CLAUDE_CODE_MARKETPLACE_NAME]);
    if (r1.code !== 0 && /not found|no marketplace/i.test(r1.stderr + r1.stdout)) {
      // Marketplace was never added — fall back to a clean install.
      return claudeCode.install(ctx);
    }
    const r2 = await run("claude", ["plugin", "update", CLAUDE_CODE_PLUGIN]);
    if (r2.code !== 0) {
      if (/not installed|no plugin/i.test(r2.stderr + r2.stdout)) {
        return claudeCode.install(ctx);
      }
      return { kind: "error", message: `claude plugin update failed: ${r2.stderr || r2.stdout}` };
    }
    return { kind: "installed", detail: "Claude Code: updated to latest (restart Claude Code to apply)" };
  },
  async uninstall(): Promise<InstallResult> {
    const bin = await which("claude");
    if (!bin) {
      return {
        kind: "manual",
        instructions: `Claude Code CLI not found. To uninstall manually, run:\n    claude plugin uninstall ${CLAUDE_CODE_PLUGIN}`,
      };
    }
    const r = await run("claude", ["plugin", "uninstall", CLAUDE_CODE_PLUGIN]);
    if (r.code !== 0) {
      return { kind: "error", message: `claude plugin uninstall failed: ${r.stderr || r.stdout}` };
    }
    return { kind: "installed", detail: "Claude Code: removed via marketplace" };
  },
  async doctor(): Promise<DoctorResult> {
    // We don't edit ~/.claude.json directly, but we can peek at it for read-only doctor reporting.
    const configPath = path.join(os.homedir(), ".claude.json");
    let exists = false;
    try {
      await fs.access(configPath);
      exists = true;
    } catch {
      /* missing is fine */
    }
    const parsed = exists ? await readJsonIfExists(configPath) : null;
    // Heuristic: look for loovie under any mcpServers map (Claude Code stores it nested).
    let url: string | null = null;
    if (parsed) {
      const walk = (node: unknown): void => {
        if (url) return;
        if (!node || typeof node !== "object") return;
        const obj = node as JsonObject;
        const mcp = obj.mcpServers as JsonObject | undefined;
        if (mcp && mcp[SERVER_KEY] && typeof (mcp[SERVER_KEY] as JsonObject).url === "string") {
          url = (mcp[SERVER_KEY] as JsonObject).url as string;
          return;
        }
        for (const v of Object.values(obj)) walk(v);
      };
      walk(parsed);
    }
    return {
      client: "claude-code",
      configPath,
      exists,
      loovieConfigured: !!url,
      url,
      notes:
        url && url !== LOOVIE_MCP_URL
          ? [`URL mismatch (expected ${LOOVIE_MCP_URL})`]
          : [(await which("claude")) ? "claude CLI on PATH" : "claude CLI not found on PATH"],
    };
  },
};
