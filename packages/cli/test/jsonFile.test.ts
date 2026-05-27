import { describe, it, expect, beforeEach } from "vitest";
import { promises as fs } from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import {
  atomicWriteJson,
  backupOnce,
  deepMerge,
  newBackupSuffix,
  readJsonIfExists,
} from "../src/util/jsonFile.js";
import type { InstallContext } from "../src/types.js";

let tmpDir: string;

beforeEach(async () => {
  tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "loovie-cli-"));
});

function ctx(): InstallContext {
  return {
    scope: "global",
    cwd: tmpDir,
    backupSuffix: newBackupSuffix(),
    verbose: false,
    backedUp: new Set(),
    interactive: false,
  };
}

describe("deepMerge", () => {
  it("preserves other mcpServers entries", () => {
    const base = { mcpServers: { other: { url: "https://x" }, third: { command: "y" } } };
    const patch = { mcpServers: { loovie: { url: "https://loovie" } } };
    const out = deepMerge(base, patch);
    expect(out).toEqual({
      mcpServers: {
        other: { url: "https://x" },
        third: { command: "y" },
        loovie: { url: "https://loovie" },
      },
    });
  });

  it("replaces arrays rather than concatenating", () => {
    const out = deepMerge({ a: [1, 2] }, { a: [3] });
    expect(out).toEqual({ a: [3] });
  });

  it("does not mutate base", () => {
    const base = { mcpServers: { other: { url: "x" } } };
    deepMerge(base, { mcpServers: { loovie: { url: "y" } } });
    expect(base).toEqual({ mcpServers: { other: { url: "x" } } });
  });
});

describe("atomicWriteJson + readJsonIfExists", () => {
  it("writes JSON atomically and reads it back", async () => {
    const p = path.join(tmpDir, "deep", "config.json");
    await atomicWriteJson(p, { hello: "world" });
    const back = await readJsonIfExists(p);
    expect(back).toEqual({ hello: "world" });
  });

  it("returns null for missing file", async () => {
    expect(await readJsonIfExists(path.join(tmpDir, "nope.json"))).toBeNull();
  });

  it("returns empty object for empty file", async () => {
    const p = path.join(tmpDir, "empty.json");
    await fs.writeFile(p, "");
    expect(await readJsonIfExists(p)).toEqual({});
  });

  it("leaves no .tmp files behind on success", async () => {
    const p = path.join(tmpDir, "x.json");
    await atomicWriteJson(p, { a: 1 });
    const siblings = await fs.readdir(tmpDir);
    expect(siblings.filter((f) => f.endsWith(".tmp"))).toHaveLength(0);
  });
});

describe("backupOnce", () => {
  it("creates a backup with the run suffix on first call", async () => {
    const p = path.join(tmpDir, "c.json");
    await fs.writeFile(p, '{"a":1}');
    const c = ctx();
    const b = await backupOnce(p, c);
    expect(b).not.toBeNull();
    const exists = await fs.readFile(b!, "utf8");
    expect(exists).toBe('{"a":1}');
  });

  it("is a no-op on subsequent calls for the same file", async () => {
    const p = path.join(tmpDir, "c.json");
    await fs.writeFile(p, '{"a":1}');
    const c = ctx();
    const first = await backupOnce(p, c);
    const second = await backupOnce(p, c);
    expect(first).not.toBeNull();
    expect(second).toBeNull();
  });

  it("returns null when source file does not exist", async () => {
    const c = ctx();
    const b = await backupOnce(path.join(tmpDir, "ghost.json"), c);
    expect(b).toBeNull();
  });
});
