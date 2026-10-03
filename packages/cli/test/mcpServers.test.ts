import { describe, it, expect, beforeEach } from "vitest";
import { promises as fs } from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { installMcpServerEntry, uninstallMcpServerEntry } from "../src/util/mcpServers.js";
import { readJsonIfExists, newBackupSuffix } from "../src/util/jsonFile.js";
import type { InstallContext } from "../src/types.js";

let tmpDir: string;
let filePath: string;

beforeEach(async () => {
  tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "loovie-cli-mcp-"));
  filePath = path.join(tmpDir, "mcp.json");
});

function ctx(overrides: Partial<InstallContext> = {}): InstallContext {
  return {
    scope: "global",
    cwd: tmpDir,
    backupSuffix: newBackupSuffix(),
    verbose: false,
    backedUp: new Set(),
    interactive: false,
    force: false,
    ...overrides,
  };
}

describe("installMcpServerEntry", () => {
  it("writes a fresh entry when the file does not exist", async () => {
    const res = await installMcpServerEntry({ filePath, ctx: ctx(), clientLabel: "Cursor" });
    expect(res.kind).toBe("installed");
    const written = await readJsonIfExists(filePath);
    expect(written).toEqual({ mcpServers: { loovie: { url: "https://api.loovie.app/v1/mcp" } } });
  });

  it("is idempotent when the existing entry already matches", async () => {
    await installMcpServerEntry({ filePath, ctx: ctx(), clientLabel: "Cursor" });
    const res = await installMcpServerEntry({ filePath, ctx: ctx(), clientLabel: "Cursor" });
    expect(res.kind).toBe("already-installed");
  });

  it("skips a differing entry non-interactively without --force", async () => {
    await fs.writeFile(filePath, JSON.stringify({ mcpServers: { loovie: { url: "https://other" } } }));
    const res = await installMcpServerEntry({ filePath, ctx: ctx(), clientLabel: "Cursor" });
    expect(res.kind).toBe("skipped");
    const untouched = await readJsonIfExists(filePath);
    expect(untouched).toEqual({ mcpServers: { loovie: { url: "https://other" } } });
  });

  it("replaces a differing entry with --force", async () => {
    await fs.writeFile(filePath, JSON.stringify({ mcpServers: { loovie: { url: "https://other" } } }));
    const res = await installMcpServerEntry({ filePath, ctx: ctx({ force: true }), clientLabel: "Cursor" });
    expect(res.kind).toBe("installed");
    const written = await readJsonIfExists(filePath);
    expect(written).toEqual({ mcpServers: { loovie: { url: "https://api.loovie.app/v1/mcp" } } });
  });

  it("preserves sibling mcpServers entries", async () => {
    await fs.writeFile(filePath, JSON.stringify({ mcpServers: { other: { url: "https://x" } } }));
    await installMcpServerEntry({ filePath, ctx: ctx(), clientLabel: "Cursor" });
    const written = await readJsonIfExists(filePath);
    expect(written).toEqual({
      mcpServers: {
        other: { url: "https://x" },
        loovie: { url: "https://api.loovie.app/v1/mcp" },
      },
    });
  });

  it("backs up the file before overwriting an existing entry with --force", async () => {
    await fs.writeFile(filePath, JSON.stringify({ mcpServers: { loovie: { url: "https://other" } } }));
    await installMcpServerEntry({ filePath, ctx: ctx({ force: true }), clientLabel: "Cursor" });
    const siblings = await fs.readdir(tmpDir);
    expect(siblings.some((f) => f.includes(".loovie-backup-"))).toBe(true);
  });
});

describe("uninstallMcpServerEntry", () => {
  it("reports skipped when no config file exists", async () => {
    const res = await uninstallMcpServerEntry({ filePath, ctx: ctx(), clientLabel: "Cursor" });
    expect(res.kind).toBe("skipped");
  });

  it("reports skipped when the loovie entry is not present", async () => {
    await fs.writeFile(filePath, JSON.stringify({ mcpServers: { other: { url: "https://x" } } }));
    const res = await uninstallMcpServerEntry({ filePath, ctx: ctx(), clientLabel: "Cursor" });
    expect(res.kind).toBe("skipped");
    const untouched = await readJsonIfExists(filePath);
    expect(untouched).toEqual({ mcpServers: { other: { url: "https://x" } } });
  });

  it("removes only the loovie entry, leaving siblings intact", async () => {
    await fs.writeFile(
      filePath,
      JSON.stringify({ mcpServers: { other: { url: "https://x" }, loovie: { url: "https://api.loovie.app/v1/mcp" } } }),
    );
    const res = await uninstallMcpServerEntry({ filePath, ctx: ctx(), clientLabel: "Cursor" });
    expect(res.kind).toBe("installed");
    const written = await readJsonIfExists(filePath);
    expect(written).toEqual({ mcpServers: { other: { url: "https://x" } } });
  });
});
