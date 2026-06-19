import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { claudeCode, runtime } from "../src/clients/claudeCode.js";
import { newBackupSuffix } from "../src/util/jsonFile.js";
import type { InstallContext } from "../src/types.js";

const realWhich = runtime.which;
const realRun = runtime.run;

function ctx(): InstallContext {
  return {
    scope: "global",
    cwd: process.cwd(),
    backupSuffix: newBackupSuffix(),
    verbose: false,
    backedUp: new Set(),
    interactive: false,
    force: false,
  };
}

let calls: string[][];

beforeEach(() => {
  calls = [];
  runtime.which = async () => "/usr/local/bin/claude";
});

afterEach(() => {
  runtime.which = realWhich;
  runtime.run = realRun;
});

const ok = { code: 0, stdout: "", stderr: "" };
const fail = { code: 1, stdout: "boom", stderr: "boom" };

describe("claudeCode.update", () => {
  it("refreshes the marketplace then updates the plugin on the happy path", async () => {
    runtime.run = async (_cmd, args) => {
      calls.push(args);
      return ok;
    };
    const res = await claudeCode.update!(ctx());
    expect(res.kind).toBe("installed");
    expect(res).toMatchObject({ detail: expect.stringMatching(/updated to latest/i) });
    expect(calls).toEqual([
      ["plugin", "marketplace", "update", "loovie"],
      ["plugin", "update", "loovie-mcp@loovie"],
    ]);
  });

  it("falls back to a clean install when marketplace update fails (never added)", async () => {
    runtime.run = async (_cmd, args) => {
      calls.push(args);
      // marketplace update fails; the install path's add+install succeed.
      if (args[1] === "marketplace" && args[2] === "update") return fail;
      return ok;
    };
    const res = await claudeCode.update!(ctx());
    expect(res.kind).toBe("installed");
    // Proves it routed through install(): marketplace add + plugin install ran.
    expect(calls).toContainEqual(["plugin", "marketplace", "add", "looviehq/loovie-community"]);
    expect(calls).toContainEqual(["plugin", "install", "loovie-mcp@loovie"]);
  });

  it("falls back to install when the plugin was never installed", async () => {
    runtime.run = async (_cmd, args) => {
      calls.push(args);
      if (args[0] === "plugin" && args[1] === "update") return fail; // not installed
      return ok;
    };
    const res = await claudeCode.update!(ctx());
    expect(res.kind).toBe("installed");
    expect(calls).toContainEqual(["plugin", "install", "loovie-mcp@loovie"]);
  });

  it("returns manual instructions when the claude CLI is absent", async () => {
    runtime.which = async () => null;
    runtime.run = async (_cmd, args) => {
      calls.push(args);
      return ok;
    };
    const res = await claudeCode.update!(ctx());
    expect(res.kind).toBe("manual");
    expect(calls).toEqual([]); // never shelled out
  });
});
