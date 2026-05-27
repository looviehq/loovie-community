import type { ClientId, ClientPlugin } from "../types.js";
import { cursor } from "./cursor.js";
import { claudeCode } from "./claudeCode.js";
import { claudeDesktop } from "./claudeDesktop.js";
import { vscode } from "./vscode.js";
import { continueDev } from "./continueDev.js";
import { cline } from "./cline.js";
import { opencode } from "./opencode.js";

export const CLIENTS: Record<ClientId, ClientPlugin> = {
  cursor,
  "claude-code": claudeCode,
  "claude-desktop": claudeDesktop,
  vscode,
  continue: continueDev,
  cline,
  opencode,
};

export const ALL_CLIENT_IDS: ClientId[] = [
  "cursor",
  "claude-code",
  "claude-desktop",
  "vscode",
  "continue",
  "cline",
  "opencode",
];

export const OFFICIAL_IDS: ClientId[] = ALL_CLIENT_IDS.filter(
  (id) => CLIENTS[id].tier === "official",
);
export const COMPATIBLE_IDS: ClientId[] = ALL_CLIENT_IDS.filter(
  (id) => CLIENTS[id].tier === "compatible",
);
