/**
 * Hardcoded source-of-truth for the hosted Loovie MCP endpoint.
 * If this ever moves, bump the CLI version and update here.
 */
export const LOOVIE_MCP_URL = "https://api.loovie.app/v1/mcp";

/**
 * Well-known OAuth metadata endpoint — used by `doctor` to verify reachability.
 * Per MCP spec, OAuth-enabled MCP servers expose this.
 */
export const LOOVIE_OAUTH_METADATA_URL =
  "https://api.loovie.app/v1/.well-known/oauth-authorization-server";

/**
 * Server key under `mcpServers` (and the marketplace plugin slug).
 */
export const SERVER_KEY = "loovie";

/**
 * Claude Desktop's `claude_desktop_config.json` only understands stdio
 * servers (command/args) — it cannot consume a bare remote `url` the way
 * Cursor/VS Code can. `mcp-remote` is the stdio<->Streamable-HTTP bridge that
 * also handles OAuth + Dynamic Client Registration. This mirrors the
 * mcp_config block in loovie-mcp/manifest.json (the .dxt bundle) so the CLI
 * and the bundle install produce an identical, working entry.
 */
export const CLAUDE_DESKTOP_ENTRY = {
  command: "npx",
  args: ["-y", "mcp-remote@latest", LOOVIE_MCP_URL],
} as const;

/**
 * Claude Code marketplace coordinates.
 */
export const CLAUDE_CODE_MARKETPLACE = "looviehq/loovie-community";
/** The marketplace's declared name (see .claude-plugin/marketplace.json) — the
 *  handle `claude plugin marketplace update <name>` expects. */
export const CLAUDE_CODE_MARKETPLACE_NAME = "loovie";
export const CLAUDE_CODE_PLUGIN = "loovie-mcp@loovie";
