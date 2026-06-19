import { describe, it, expect, afterEach, vi } from "vitest";
import { checkForUpdate, isNewer } from "../src/util/selfUpdate.js";

describe("isNewer", () => {
  it("detects a higher patch/minor/major", () => {
    expect(isNewer("0.1.1", "0.1.0")).toBe(true);
    expect(isNewer("0.2.0", "0.1.9")).toBe(true);
    expect(isNewer("1.0.0", "0.9.9")).toBe(true);
  });

  it("returns false for equal or older versions", () => {
    expect(isNewer("0.1.0", "0.1.0")).toBe(false);
    expect(isNewer("0.1.0", "0.1.1")).toBe(false);
    expect(isNewer("0.9.9", "1.0.0")).toBe(false);
  });

  it("tolerates a leading v", () => {
    expect(isNewer("v0.2.0", "0.1.0")).toBe(true);
  });

  it("ranks a stable release above its prerelease", () => {
    expect(isNewer("0.2.0", "0.2.0-beta.1")).toBe(true);
    expect(isNewer("0.2.0-beta.1", "0.2.0")).toBe(false);
    expect(isNewer("0.2.0-beta.2", "0.2.0-beta.1")).toBe(true);
  });

  it("compares numeric prerelease identifiers numerically, not lexically", () => {
    expect(isNewer("0.2.0-beta.10", "0.2.0-beta.9")).toBe(true);
    expect(isNewer("0.2.0-beta.9", "0.2.0-beta.10")).toBe(false);
    // numeric identifiers rank below alphanumeric (SemVer §11)
    expect(isNewer("0.2.0-rc.1", "0.2.0-1")).toBe(true);
  });
});

describe("checkForUpdate", () => {
  const realFetch = globalThis.fetch;
  afterEach(() => {
    globalThis.fetch = realFetch;
    delete process.env.LOOVIE_NO_UPDATE_CHECK;
  });

  function mockFetch(impl: () => Promise<unknown>) {
    globalThis.fetch = vi.fn(async () => {
      const body = await impl();
      return { ok: true, json: async () => body } as Response;
    });
  }

  it("returns a notice when a newer version is published", async () => {
    mockFetch(async () => ({ version: "9.9.9" }));
    const notice = await checkForUpdate("0.1.0");
    expect(notice).toMatch(/0\.1\.0 → 9\.9\.9/);
  });

  it("returns null when already on the latest", async () => {
    mockFetch(async () => ({ version: "0.1.0" }));
    expect(await checkForUpdate("0.1.0")).toBeNull();
  });

  it("stays silent (and skips the network) when opted out", async () => {
    process.env.LOOVIE_NO_UPDATE_CHECK = "1";
    const spy = vi.fn();
    globalThis.fetch = spy as unknown as typeof fetch;
    expect(await checkForUpdate("0.1.0")).toBeNull();
    expect(spy).not.toHaveBeenCalled();
  });

  it("swallows network failures", async () => {
    globalThis.fetch = vi.fn(async () => {
      throw new Error("offline");
    }) as unknown as typeof fetch;
    expect(await checkForUpdate("0.1.0")).toBeNull();
  });

  it("returns null on a non-ok response", async () => {
    globalThis.fetch = vi.fn(async () => ({ ok: false }) as Response) as unknown as typeof fetch;
    expect(await checkForUpdate("0.1.0")).toBeNull();
  });
});
