import { describe, it, expect, afterEach } from "vitest";
import { promises as fs } from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { claudeDesktop } from "../src/clients/claudeDesktop.js";
import { claudeDesktopConfigPath } from "../src/util/paths.js";

const LOOVIE_URL = "https://api.loovie.app/v1/mcp";
const origHome = process.env.HOME;

afterEach(() => {
  if (origHome === undefined) delete process.env.HOME;
  else process.env.HOME = origHome;
});

async function withConfig(entry: unknown): Promise<ReturnType<typeof claudeDesktop.doctor>> {
  const home = await fs.mkdtemp(path.join(os.tmpdir(), "loovie-cd-"));
  process.env.HOME = home;
  const cfg = claudeDesktopConfigPath();
  await fs.mkdir(path.dirname(cfg), { recursive: true });
  await fs.writeFile(cfg, JSON.stringify({ mcpServers: { loovie: entry } }));
  return claudeDesktop.doctor({} as never);
}

describe("claudeDesktop.doctor", () => {
  // Linux resolves the config path via HOME, so these only assert on linux.
  const onLinux = os.platform() === "linux" ? it : it.skip;

  onLinux("recognises the mcp-remote bridge entry and reports its endpoint", async () => {
    const r = await withConfig({
      command: "npx",
      args: ["-y", "mcp-remote@latest", LOOVIE_URL],
    });
    expect(r.loovieConfigured).toBe(true);
    expect(r.url).toBe(LOOVIE_URL);
    expect(r.notes).toEqual([]);
  });

  onLinux("flags an entry that points elsewhere", async () => {
    const r = await withConfig({ command: "npx", args: ["-y", "mcp-remote@latest", "https://evil.example"] });
    expect(r.loovieConfigured).toBe(true);
    expect(r.url).toBe("https://evil.example");
    expect(r.notes.length).toBe(1);
  });
});
