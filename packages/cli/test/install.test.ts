import { describe, it, expect, beforeEach } from "vitest";
import { promises as fs } from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import {
  installMcpServerEntry,
  uninstallMcpServerEntry,
} from "../src/util/mcpServers.js";
import { newBackupSuffix, readJsonIfExists } from "../src/util/jsonFile.js";
import type { InstallContext } from "../src/types.js";

let tmpDir: string;

beforeEach(async () => {
  tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "loovie-cli-install-"));
});

function ctx(): InstallContext {
  return {
    scope: "global",
    cwd: tmpDir,
    backupSuffix: newBackupSuffix(),
    verbose: false,
    backedUp: new Set(),
    interactive: false,
    force: false,
  };
}

describe("installMcpServerEntry", () => {
  it("creates the config when none exists", async () => {
    const filePath = path.join(tmpDir, "nested", "mcp.json");
    const res = await installMcpServerEntry({ filePath, ctx: ctx(), clientLabel: "Test" });
    expect(res.kind).toBe("installed");
    expect(await readJsonIfExists(filePath)).toEqual({
      mcpServers: { loovie: { url: "https://api.loovie.app/v1/mcp" } },
    });
  });

  it("preserves other mcpServers entries", async () => {
    const filePath = path.join(tmpDir, "mcp.json");
    await fs.writeFile(
      filePath,
      JSON.stringify({ mcpServers: { other: { url: "https://other" } } }),
    );
    await installMcpServerEntry({ filePath, ctx: ctx(), clientLabel: "Test" });
    const after = await readJsonIfExists(filePath);
    expect(after).toEqual({
      mcpServers: {
        other: { url: "https://other" },
        loovie: { url: "https://api.loovie.app/v1/mcp" },
      },
    });
  });

  it("is idempotent on re-install with the same URL", async () => {
    const filePath = path.join(tmpDir, "mcp.json");
    const c = ctx();
    await installMcpServerEntry({ filePath, ctx: c, clientLabel: "Test" });
    const res = await installMcpServerEntry({ filePath, ctx: c, clientLabel: "Test" });
    expect(res.kind).toBe("already-installed");
  });

  it("skips when an existing differing entry is present and non-interactive", async () => {
    const filePath = path.join(tmpDir, "mcp.json");
    await fs.writeFile(
      filePath,
      JSON.stringify({ mcpServers: { loovie: { url: "https://wrong" } } }),
    );
    const res = await installMcpServerEntry({ filePath, ctx: ctx(), clientLabel: "Test" });
    expect(res.kind).toBe("skipped");
  });

  it("creates a single backup per run across multiple installs to the same file", async () => {
    const filePath = path.join(tmpDir, "mcp.json");
    await fs.writeFile(filePath, JSON.stringify({ mcpServers: {} }));
    const c = ctx();
    await installMcpServerEntry({ filePath, ctx: c, clientLabel: "A" });
    // Call again — should not create a second backup file.
    await installMcpServerEntry({ filePath, ctx: c, clientLabel: "B" });
    const backups = (await fs.readdir(tmpDir)).filter((f) => f.includes(".loovie-backup-"));
    expect(backups).toHaveLength(1);
  });
});

describe("uninstallMcpServerEntry", () => {
  it("removes only the loovie key, leaving others", async () => {
    const filePath = path.join(tmpDir, "mcp.json");
    await fs.writeFile(
      filePath,
      JSON.stringify({
        mcpServers: {
          other: { url: "https://other" },
          loovie: { url: "https://api.loovie.app/v1/mcp" },
        },
      }),
    );
    const res = await uninstallMcpServerEntry({ filePath, ctx: ctx(), clientLabel: "Test" });
    expect(res.kind).toBe("installed");
    expect(await readJsonIfExists(filePath)).toEqual({
      mcpServers: { other: { url: "https://other" } },
    });
  });

  it("leaves an empty mcpServers map rather than deleting it", async () => {
    const filePath = path.join(tmpDir, "mcp.json");
    await fs.writeFile(
      filePath,
      JSON.stringify({ mcpServers: { loovie: { url: "https://api.loovie.app/v1/mcp" } } }),
    );
    await uninstallMcpServerEntry({ filePath, ctx: ctx(), clientLabel: "Test" });
    expect(await readJsonIfExists(filePath)).toEqual({ mcpServers: {} });
  });

  it("is a no-op when not installed", async () => {
    const filePath = path.join(tmpDir, "mcp.json");
    await fs.writeFile(filePath, JSON.stringify({ mcpServers: {} }));
    const res = await uninstallMcpServerEntry({ filePath, ctx: ctx(), clientLabel: "Test" });
    expect(res.kind).toBe("skipped");
  });

  it("is a no-op when file does not exist", async () => {
    const res = await uninstallMcpServerEntry({
      filePath: path.join(tmpDir, "ghost.json"),
      ctx: ctx(),
      clientLabel: "Test",
    });
    expect(res.kind).toBe("skipped");
  });
});

describe("installMcpServerEntry — non-url (Claude Desktop bridge) entries", () => {
  const bridge = {
    command: "npx",
    args: ["-y", "mcp-remote@latest", "https://api.loovie.app/v1/mcp"],
  };

  it("writes a command/args entry and is idempotent on re-install", async () => {
    const filePath = path.join(tmpDir, "claude_desktop_config.json");
    const c = ctx();
    const first = await installMcpServerEntry({
      filePath,
      ctx: c,
      entryValue: { ...bridge, args: [...bridge.args] },
      clientLabel: "Claude Desktop",
    });
    expect(first.kind).toBe("installed");
    expect(await readJsonIfExists(filePath)).toEqual({ mcpServers: { loovie: bridge } });

    const second = await installMcpServerEntry({
      filePath,
      ctx: c,
      entryValue: { ...bridge, args: [...bridge.args] },
      clientLabel: "Claude Desktop",
    });
    expect(second.kind).toBe("already-installed");
  });

  it("replaces a differing entry when --force is set, without prompting", async () => {
    const filePath = path.join(tmpDir, "mcp.json");
    await fs.writeFile(
      filePath,
      JSON.stringify({ mcpServers: { loovie: { url: "https://stale.example" } } }),
    );
    const res = await installMcpServerEntry({
      filePath,
      ctx: { ...ctx(), force: true },
      clientLabel: "Test",
    });
    expect(res.kind).toBe("installed");
    expect(await readJsonIfExists(filePath)).toEqual({
      mcpServers: { loovie: { url: "https://api.loovie.app/v1/mcp" } },
    });
  });
});
