export type ClientId =
  | "cursor"
  | "claude-code"
  | "claude-desktop"
  | "vscode"
  | "continue"
  | "cline"
  | "opencode";

export type SupportTier = "official" | "compatible";

export type InstallScope = "global" | "project";

export type InstallContext = {
  scope: InstallScope;
  cwd: string;
  /** Created lazily on first JSON mutation per run; all backups share one suffix. */
  backupSuffix: string;
  verbose: boolean;
  /** Tracks files already backed up this run so we don't double-back-up. */
  backedUp: Set<string>;
  /** When true, asks before replacing a differing existing entry. */
  interactive: boolean;
  /** When true, replace a differing existing entry without prompting. */
  force: boolean;
};

export type InstallResult =
  | { kind: "installed"; detail: string }
  | { kind: "already-installed"; detail: string }
  | { kind: "skipped"; reason: string }
  | { kind: "manual"; instructions: string }
  | { kind: "error"; message: string };

export type DoctorResult = {
  client: ClientId;
  configPath: string | null;
  exists: boolean;
  loovieConfigured: boolean;
  url: string | null;
  notes: string[];
};

export type ClientPlugin = {
  id: ClientId;
  label: string;
  tier: SupportTier;
  /** Best-effort detection (binary on PATH, config file present, etc.) — null = unknown. */
  detect(): Promise<boolean | null>;
  install(ctx: InstallContext): Promise<InstallResult>;
  uninstall(ctx: InstallContext): Promise<InstallResult>;
  /**
   * Refresh an existing install to the latest content. Optional — clients
   * without a dedicated update path fall back to a forced re-install, which
   * for config-file clients simply rewrites the canonical entry. Clients with
   * out-of-band content (Claude Code's marketplace plugin: skills, commands,
   * MCP block) override this to re-pull that content.
   */
  update?(ctx: InstallContext): Promise<InstallResult>;
  doctor(ctx: InstallContext): Promise<DoctorResult>;
};
