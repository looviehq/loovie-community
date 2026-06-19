# @loovie/mcp

One-shot installer for the [Loovie MCP server](https://api.loovie.app/v1/mcp). Wires the hosted endpoint into your AI clients (Cursor, Claude Code, Claude Desktop, VS Code, Continue, Cline, OpenCode) with one command.

```bash
npx -y @loovie/mcp                 # interactive
npx -y @loovie/mcp install --all   # everything we support
npx -y @loovie/mcp doctor          # report what's wired
```

No telemetry. No postinstall scripts. The only runtime dependency is `prompts`.

## Quick start

Interactive (recommended):

```bash
npx -y @loovie/mcp
```

You'll see a checklist grouped by support tier. Pick clients, hit enter, done.

Explicit:

```bash
npx -y @loovie/mcp install --client cursor --client claude-code
npx -y @loovie/mcp install --client vscode --project
npx -y @loovie/mcp install --all
```

## Commands

| Command | What it does |
|---|---|
| `(default)` | Interactive picker, then install |
| `install` | Install into clients passed via `--client`/`--all` |
| `update` | Refresh selected clients to the latest. For Claude Code, re-pulls the marketplace plugin (skills, commands, MCP block); for config-file clients, rewrites the canonical `loovie` entry (installing it if absent) |
| `uninstall` | Remove the `loovie` entry only — other servers are left alone |
| `doctor` | Print a table of which clients have Loovie configured, plus an endpoint reachability check |
| `--help`, `-h` | Help |
| `--version`, `-v` | Version |

### Flags

- `--all` — apply to every supported client
- `--client <id>` — repeatable. Valid ids: `cursor`, `claude-code`, `claude-desktop`, `vscode`, `continue`, `cline`, `opencode`
- `--global` — write to user-global config (default)
- `--project` — write to `<cwd>/.cursor/mcp.json` or `.vscode/mcp.json` instead
- `--force` — replace a differing existing `loovie` entry without prompting (handy for non-interactive runs)
- `--verbose` — print the config path before writing

On every run the CLI does a short, non-blocking check against the npm registry and prints a one-line notice if a newer `@loovie/mcp` is published. Suppress it with `LOOVIE_NO_UPDATE_CHECK=1`.

## Support tiers

| Tier | Clients | What it means |
|---|---|---|
| **Officially supported** | Cursor, Claude Code | Tested in CI, first-class. |
| **Compatible** (community, not officially tested) | Claude Desktop, VS Code, Continue, Cline, OpenCode | Should work, but we don't run them in CI. File an issue if you hit something. |

## What each client gets

| Client | Where we write | Mechanism |
|---|---|---|
| Cursor | `~/.cursor/mcp.json` (or `<cwd>/.cursor/mcp.json` with `--project`) | JSON merge under `mcpServers.loovie` |
| Claude Code | (no file) | Runs `claude plugin marketplace add looviehq/loovie-community` and `claude plugin install loovie-mcp@loovie` |
| Claude Desktop | macOS `~/Library/Application Support/Claude/claude_desktop_config.json` / Windows `%APPDATA%/Claude/claude_desktop_config.json` / Linux `~/.config/Claude/claude_desktop_config.json` | JSON merge. Claude Desktop's config is **stdio-only**, so we wire the `mcp-remote` bridge (`npx -y mcp-remote@latest <url>`) which also handles OAuth — same as the `.dxt` bundle. Needs Node on PATH. Restart Claude Desktop after. |
| VS Code (MCP) | `<cwd>/.vscode/mcp.json` (requires `--project`) | JSON merge |
| Continue | (printed instructions) | Continue's config shape varies by version; we print both YAML and JSON snippets for you to paste |
| Cline | (printed instructions) | Cline stores MCP config inside VS Code settings; we don't touch settings.json |
| OpenCode | `~/.config/opencode/opencode.json` (Linux/macOS) or `%APPDATA%/opencode/opencode.json` (Windows) | JSON merge under `mcp.loovie` with `type: "remote"` |

## Safety

- Every JSON mutation is **atomic** (write tempfile + rename).
- Before mutating, we **back up** the file once per run to `<file>.loovie-backup-<timestamp>`.
- We **never** touch keys other than `mcpServers.loovie` (or `mcp.loovie` for OpenCode).
- If you already have a `loovie` entry pointing somewhere else, we ask before replacing (interactive only — non-interactive runs skip with a warning unless you pass `--force`).
- `uninstall` removes only the `loovie` key. Other servers are untouched.
- No postinstall scripts. No telemetry. No network calls during install (apart from optional `doctor` reachability ping).

## Endpoint

```text
https://api.loovie.app/v1/mcp
```

Standard Streamable HTTP MCP server with OAuth 2.0 + Dynamic Client Registration. Any spec-compliant MCP client works.

## Bug reports

[github.com/looviehq/loovie-community/issues](https://github.com/looviehq/loovie-community/issues) — please include:

- Output of `npx -y @loovie/mcp doctor`
- OS + node version
- Which client + what happened

## License

Apache-2.0
