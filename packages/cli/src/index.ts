import { ALL_CLIENT_IDS, CLIENTS, COMPATIBLE_IDS, OFFICIAL_IDS } from "./clients/index.js";
import { LOOVIE_MCP_URL } from "./constants.js";
import type { ClientId, InstallContext } from "./types.js";
import { type ParsedArgs, parseArgs, resolveForce, resolveMode } from "./args.js";
import { runDoctor } from "./commands/doctor.js";
import { pickClientsInteractively, runInstall } from "./commands/install.js";
import { newBackupSuffix } from "./util/jsonFile.js";
import { log } from "./util/log.js";
import { printUpdateNoticeIfAny } from "./util/selfUpdate.js";

// Version is replaced at build time but we keep a fallback for `--version`.
const VERSION = "0.1.0";

function printHelp(): void {
  log.raw(`Loovie MCP installer v${VERSION}

Wires the hosted Loovie MCP server (${LOOVIE_MCP_URL}) into your AI clients.

Usage:
  npx -y @loovie/mcp                       Interactive install (detect + pick)
  npx -y @loovie/mcp install [opts]        Install into selected clients
  npx -y @loovie/mcp update [opts]         Refresh installed clients to latest
  npx -y @loovie/mcp uninstall [opts]      Remove from selected clients
  npx -y @loovie/mcp doctor                Report which clients have Loovie wired

Options:
  --all                    Apply to every supported client
  --client <id>            Repeatable. One of: ${ALL_CLIENT_IDS.join(", ")}
  --global                 Write to user-global config (default)
  --project                Write to <cwd>/.cursor/mcp.json or .vscode/mcp.json
  --force                  Replace a differing existing entry without prompting
  --verbose                Show config paths before writing
  -h, --help               This help
  -v, --version            Print version

Support tiers:
  Officially supported:    ${OFFICIAL_IDS.map((id) => CLIENTS[id].label).join(", ")}
  Compatible (untested):   ${COMPATIBLE_IDS.map((id) => CLIENTS[id].label).join(", ")}

Endpoint: ${LOOVIE_MCP_URL}
`);
}

async function main(): Promise<void> {
  let args: ParsedArgs;
  try {
    args = parseArgs(process.argv.slice(2));
  } catch (err) {
    log.error((err as Error).message);
    process.exit(2);
  }

  if (args.command === "help") {
    printHelp();
    return;
  }
  if (args.command === "version") {
    log.raw(VERSION);
    return;
  }

  const ctx: InstallContext = {
    scope: args.scope,
    cwd: process.cwd(),
    backupSuffix: newBackupSuffix(),
    verbose: args.verbose,
    backedUp: new Set(),
    interactive: process.stdout.isTTY === true,
    force: resolveForce(args),
  };

  if (args.command === "doctor") {
    await runDoctor(ctx);
    await printUpdateNoticeIfAny(VERSION);
    return;
  }

  // Resolve client selection.
  let selected: ClientId[];
  if (args.all) {
    selected = [...ALL_CLIENT_IDS];
  } else if (args.clients.length > 0) {
    selected = args.clients;
  } else {
    if (!ctx.interactive) {
      log.error("No --client or --all specified, and stdin is not a TTY. Pick clients explicitly.");
      process.exit(2);
    }
    log.raw(`Loovie MCP installer v${VERSION}`);
    log.dim(`Endpoint: ${LOOVIE_MCP_URL}`);
    selected = await pickClientsInteractively(ctx);
    if (selected.length === 0) {
      log.warn("Nothing selected. Exiting.");
      return;
    }
  }

  if (args.verbose) {
    log.dim(`Backup suffix for this run: ${ctx.backupSuffix}`);
    log.dim(`Selected: ${selected.join(", ")}`);
  }

  await runInstall(selected, ctx, resolveMode(args.command));

  log.raw("");
  log.success("Done. Run `npx -y @loovie/mcp doctor` to verify.");
  await printUpdateNoticeIfAny(VERSION);
}

main().catch((err: unknown) => {
  log.error(`Unexpected error: ${(err as Error).stack ?? String(err)}`);
  process.exit(1);
});
