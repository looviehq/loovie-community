import { LOOVIE_OAUTH_METADATA_URL } from "../constants.js";
import { ALL_CLIENT_IDS, CLIENTS } from "../clients/index.js";
import type { InstallContext } from "../types.js";
import { log } from "../util/log.js";

async function checkEndpoint(): Promise<"reachable" | "unreachable" | "skipped"> {
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 3000);
    const res = await fetch(LOOVIE_OAUTH_METADATA_URL, {
      method: "HEAD",
      signal: ctrl.signal,
    });
    clearTimeout(timer);
    return res.ok || res.status < 500 ? "reachable" : "unreachable";
  } catch {
    return "skipped";
  }
}

export async function runDoctor(ctx: InstallContext): Promise<void> {
  log.step("Loovie MCP — doctor");

  const reach = await checkEndpoint();
  if (reach === "reachable") {
    log.success(`OAuth metadata endpoint reachable: ${LOOVIE_OAUTH_METADATA_URL}`);
  } else if (reach === "unreachable") {
    log.warn(`OAuth metadata endpoint returned an error: ${LOOVIE_OAUTH_METADATA_URL}`);
  } else {
    log.dim(`(skipped network check for ${LOOVIE_OAUTH_METADATA_URL})`);
  }

  log.raw("");
  const rows: Array<{ client: string; status: string; path: string }> = [];
  for (const id of ALL_CLIENT_IDS) {
    const r = await CLIENTS[id].doctor(ctx);
    const status = r.loovieConfigured
      ? r.url && r.notes.some((n) => n.includes("URL mismatch"))
        ? "configured (URL mismatch!)"
        : "configured"
      : r.exists
        ? "config present, loovie missing"
        : "not configured";
    rows.push({
      client: CLIENTS[id].label,
      status,
      path: r.configPath ?? "(n/a)",
    });
  }

  const wClient = Math.max(...rows.map((r) => r.client.length), "Client".length);
  const wStatus = Math.max(...rows.map((r) => r.status.length), "Status".length);
  log.raw(
    `  ${"Client".padEnd(wClient)}  ${"Status".padEnd(wStatus)}  Config`,
  );
  log.raw(`  ${"-".repeat(wClient)}  ${"-".repeat(wStatus)}  ${"-".repeat(20)}`);
  for (const r of rows) {
    log.raw(`  ${r.client.padEnd(wClient)}  ${r.status.padEnd(wStatus)}  ${r.path}`);
  }
}
