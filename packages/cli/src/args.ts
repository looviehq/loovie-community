import { ALL_CLIENT_IDS } from "./clients/index.js";
import type { ClientId, InstallScope } from "./types.js";

export type Command =
  | "install"
  | "uninstall"
  | "update"
  | "doctor"
  | "help"
  | "version"
  | "default";

export type ParsedArgs = {
  command: Command;
  clients: ClientId[];
  all: boolean;
  scope: InstallScope;
  verbose: boolean;
  force: boolean;
};

export function parseArgs(argv: string[]): ParsedArgs {
  let command: Command = "default";
  const clients: ClientId[] = [];
  let all = false;
  let scope: InstallScope = "global";
  let verbose = false;
  let force = false;

  const positional: string[] = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]!;
    switch (a) {
      case "-h":
      case "--help":
        command = "help";
        break;
      case "-v":
      case "--version":
        command = "version";
        break;
      case "--all":
        all = true;
        break;
      case "--global":
        scope = "global";
        break;
      case "--project":
        scope = "project";
        break;
      case "--verbose":
        verbose = true;
        break;
      case "--force":
        force = true;
        break;
      case "--client": {
        const next = argv[++i];
        if (!next) throw new Error("--client requires a value");
        if (!ALL_CLIENT_IDS.includes(next as ClientId)) {
          throw new Error(`Unknown client: ${next}. Valid: ${ALL_CLIENT_IDS.join(", ")}`);
        }
        clients.push(next as ClientId);
        break;
      }
      default:
        if (a.startsWith("-")) throw new Error(`Unknown flag: ${a}`);
        positional.push(a);
    }
  }

  if (command === "default" && positional.length > 0) {
    const cmd = positional[0];
    if (cmd === "install" || cmd === "uninstall" || cmd === "update" || cmd === "doctor") {
      command = cmd;
    } else {
      throw new Error(`Unknown command: ${cmd}`);
    }
  }

  return { command, clients, all, scope, verbose, force };
}

/** The install/uninstall/update verb implied by a parsed command. */
export function resolveMode(command: Command): "install" | "uninstall" | "update" {
  return command === "uninstall" || command === "update" ? command : "install";
}

/** Whether a run should replace differing entries without prompting. `update`
 *  always refreshes the canonical entry, so it implies force. */
export function resolveForce(args: Pick<ParsedArgs, "force" | "command">): boolean {
  return args.force || args.command === "update";
}
