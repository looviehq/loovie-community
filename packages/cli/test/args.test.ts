import { describe, it, expect } from "vitest";
import { parseArgs, resolveForce, resolveMode } from "../src/args.js";

describe("parseArgs", () => {
  it("defaults to interactive install", () => {
    const a = parseArgs([]);
    expect(a.command).toBe("default");
    expect(a.scope).toBe("global");
    expect(a.force).toBe(false);
    expect(a.clients).toEqual([]);
  });

  it("parses the update command and --force", () => {
    const a = parseArgs(["update", "--force", "--client", "cursor"]);
    expect(a.command).toBe("update");
    expect(a.force).toBe(true);
    expect(a.clients).toEqual(["cursor"]);
  });

  it("accumulates repeated --client and honours --project", () => {
    const a = parseArgs(["install", "--client", "cursor", "--client", "vscode", "--project"]);
    expect(a.clients).toEqual(["cursor", "vscode"]);
    expect(a.scope).toBe("project");
  });

  it("rejects an unknown client", () => {
    expect(() => parseArgs(["install", "--client", "nope"])).toThrow(/Unknown client/);
  });

  it("rejects an unknown command and an unknown flag", () => {
    expect(() => parseArgs(["frobnicate"])).toThrow(/Unknown command/);
    expect(() => parseArgs(["--wat"])).toThrow(/Unknown flag/);
  });

  it("requires a value after --client", () => {
    expect(() => parseArgs(["--client"])).toThrow(/requires a value/);
  });
});

describe("resolveMode", () => {
  it("maps commands to verbs, defaulting to install", () => {
    expect(resolveMode("update")).toBe("update");
    expect(resolveMode("uninstall")).toBe("uninstall");
    expect(resolveMode("install")).toBe("install");
    expect(resolveMode("default")).toBe("install");
    expect(resolveMode("doctor")).toBe("install");
  });
});

describe("resolveForce", () => {
  it("is true when --force is passed", () => {
    expect(resolveForce({ force: true, command: "install" })).toBe(true);
  });

  it("is implied by the update command", () => {
    expect(resolveForce({ force: false, command: "update" })).toBe(true);
  });

  it("is false for a plain install without --force", () => {
    expect(resolveForce({ force: false, command: "install" })).toBe(false);
  });
});
