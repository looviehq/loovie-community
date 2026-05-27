import prompts from "prompts";
import { CLIENTS, COMPATIBLE_IDS, OFFICIAL_IDS } from "../clients/index.js";
import type { ClientId, InstallContext, InstallResult } from "../types.js";
import { log } from "../util/log.js";

function reportResult(label: string, r: InstallResult): void {
  switch (r.kind) {
    case "installed":
      log.success(r.detail);
      break;
    case "already-installed":
      log.dim(`  ${r.detail}`);
      break;
    case "skipped":
      log.warn(`${label}: ${r.reason}`);
      break;
    case "manual":
      log.warn(`${label}: manual step required`);
      log.raw(r.instructions);
      break;
    case "error":
      log.error(`${label}: ${r.message}`);
      break;
  }
}

export async function runInstall(
  selected: ClientId[],
  ctx: InstallContext,
  mode: "install" | "uninstall",
): Promise<void> {
  for (const id of selected) {
    const plugin = CLIENTS[id];
    log.step(`${mode === "install" ? "Installing" : "Uninstalling"} ${plugin.label}${plugin.tier === "compatible" ? "  [compatible — community support, not officially tested]" : ""}`);
    try {
      const res =
        mode === "install" ? await plugin.install(ctx) : await plugin.uninstall(ctx);
      reportResult(plugin.label, res);
    } catch (err: unknown) {
      log.error(`${plugin.label}: ${(err as Error).message}`);
    }
  }
}

export async function pickClientsInteractively(ctx: InstallContext): Promise<ClientId[]> {
  const choices = [
    { title: "── Officially supported ──", value: "__sep1__", disabled: true },
    ...OFFICIAL_IDS.map((id) => ({
      title: CLIENTS[id].label,
      value: id,
      selected: id === "cursor" || id === "claude-code",
    })),
    { title: "── Compatible (community, not officially tested) ──", value: "__sep2__", disabled: true },
    ...COMPATIBLE_IDS.map((id) => ({
      title: CLIENTS[id].label,
      value: id,
      selected: false,
    })),
  ];

  const { selected } = await prompts({
    type: "multiselect",
    name: "selected",
    message: "Select MCP clients to install Loovie into",
    choices,
    hint: "space to toggle, enter to confirm",
    instructions: false,
  });

  if (!Array.isArray(selected)) return [];
  void ctx; // currently unused but reserved for future scope-aware prompts
  return selected.filter((v): v is ClientId => typeof v === "string" && !v.startsWith("__"));
}
