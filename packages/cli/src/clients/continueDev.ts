import { LOOVIE_MCP_URL, SERVER_KEY } from "../constants.js";
import type { ClientPlugin, DoctorResult } from "../types.js";

/**
 * Continue's MCP config shape has shifted between releases (config.json with
 * experimental.modelContextProtocolServers vs config.yaml with mcpServers).
 * To avoid corrupting users' configs, we print manual instructions and let
 * them paste the right block themselves.
 *
 * Doc reference: https://docs.continue.dev (search "MCP" in their docs).
 */
export const continueDev: ClientPlugin = {
  id: "continue",
  label: "Continue",
  tier: "compatible",
  async detect() {
    return null;
  },
  async install() {
    const yamlBlock =
      "mcpServers:\n" +
      `  - name: ${SERVER_KEY}\n` +
      `    url: ${LOOVIE_MCP_URL}\n` +
      "    transport: http\n";
    const jsonBlock = JSON.stringify(
      {
        experimental: {
          modelContextProtocolServers: [{ name: SERVER_KEY, url: LOOVIE_MCP_URL, transport: "http" }],
        },
      },
      null,
      2,
    );
    return {
      kind: "manual",
      instructions:
        "Continue's MCP config shape varies by version. Add ONE of the following to your Continue config:\n\n" +
        "  ~/.continue/config.yaml (newer Continue):\n" +
        yamlBlock.replace(/^/gm, "    ") +
        "\n  ~/.continue/config.json (older Continue):\n" +
        jsonBlock.replace(/^/gm, "    ") +
        "\n\nRestart Continue after editing.",
    };
  },
  async uninstall() {
    return {
      kind: "manual",
      instructions: "Open your Continue config (~/.continue/config.yaml or config.json) and remove the loovie MCP entry.",
    };
  },
  async doctor(): Promise<DoctorResult> {
    return {
      client: "continue",
      configPath: null,
      exists: false,
      loovieConfigured: false,
      url: null,
      notes: ["Continue MCP config shape varies by version — not auto-detected."],
    };
  },
};
