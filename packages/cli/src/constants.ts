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
 * Claude Code marketplace coordinates.
 */
export const CLAUDE_CODE_MARKETPLACE = "looviehq/loovie-community";
export const CLAUDE_CODE_PLUGIN = "loovie-mcp@loovie";
