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
  doctor(ctx: InstallContext): Promise<DoctorResult>;
};
