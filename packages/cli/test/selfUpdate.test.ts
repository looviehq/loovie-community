import { describe, it, expect } from "vitest";
import { isNewer } from "../src/util/selfUpdate.js";

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
});
