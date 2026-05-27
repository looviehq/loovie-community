# Loovie MCP

Create AI characters, generate images and videos, and edit Loovie projects from your AI agent — Claude Code, Cursor, Claude Desktop, VS Code, Continue, Cline, OpenCode, or any spec-compliant MCP client.

[![npm](https://img.shields.io/npm/v/@loovie/mcp?label=%40loovie%2Fmcp&color=brightgreen)](https://www.npmjs.com/package/@loovie/mcp)
[![Smithery](https://smithery.ai/badge/looviehq/loovie-mcp)](https://smithery.ai/server/looviehq/loovie-mcp)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](../LICENSE)

The plugin connects your client to the hosted Loovie MCP server at `https://api.loovie.app/v1/mcp`. Auth is OAuth — the first time you call a tool, your browser opens to sign you in and your client remembers the token.

## Quickstart

Pick the install path for your client:

```bash
# Cross-client interactive installer (handles all clients in one go)
npx -y @loovie/mcp
```

That's it. The installer detects which clients you have installed, asks which to wire Loovie into, and writes the right config files. Re-run to add more clients later, or run `npx -y @loovie/mcp doctor` to see what's wired.

Prefer per-client instructions? Jump to your client below.

## Support tiers

We test the endpoint end-to-end against four clients. Everything else uses the same standard transport (Streamable HTTP + OAuth/DCR) and should work, but the integration hasn't been formally verified.

| Tier | Clients | What it means |
|---|---|---|
| **Officially supported** | Cursor, Claude Code, Claude Desktop, Claude.ai (web) | Smoke-tested end-to-end. Bugs get fixed. Surface won't break without a deprecation window. |
| **Compatible (community-supported)** | VS Code Copilot Chat, Continue, Cline, OpenCode, ChatGPT MCP, any other Streamable HTTP MCP client | Spec-compliant — should work. File issues at [looviehq/loovie-community](https://github.com/looviehq/loovie-community/issues); no SLA. Promoted to "officially supported" as we verify each. |

## Install per client

### Cursor (officially supported)

[![Install in Cursor](https://cursor.com/deeplink/mcp-install-dark.svg)](cursor://anysphere.cursor-deeplink/mcp/install?name=loovie&config=eyJ1cmwiOiJodHRwczovL2FwaS5sb292aWUuYXBwL3YxL21jcCJ9)

One-click via the button above, or paste into `~/.cursor/mcp.json` (global) or `<project>/.cursor/mcp.json` (per-project):

```json
{
  "mcpServers": {
    "loovie": {
      "url": "https://api.loovie.app/v1/mcp"
    }
  }
}
```

### Claude Code (officially supported)

```bash
claude plugin marketplace add looviehq/loovie-community
claude plugin install loovie-mcp@loovie
```

Then run `/mcp` in any session to sign in. The plugin also bundles workflow skills (`making-a-loovie-video`, `character-from-photo`, `editing-an-existing-project`, `exporting-and-sharing`) and slash commands (`/loovie-new-project`, `/loovie-status`, `/loovie-credits`).

### Claude Desktop (officially supported)

**One-click bundle** (`.dxt` / `.mcpb`):

Download [`loovie-mcp.dxt`](https://github.com/looviehq/loovie-community/releases/latest/download/loovie-mcp.dxt) and open it in Claude Desktop — Settings → Extensions → Install from file.

**Or manually**: Settings → Connectors → Add custom connector → URL `https://api.loovie.app/v1/mcp`, transport HTTP. Sign in when prompted.

### VS Code Copilot Chat (compatible)

Add to `.vscode/mcp.json` in your repo root:

```json
{
  "mcpServers": {
    "loovie": {
      "url": "https://api.loovie.app/v1/mcp"
    }
  }
}
```

### Continue (compatible)

Continue's MCP config shape varies by version. Paste one of these into your Continue config:

`config.yaml`:

```yaml
mcpServers:
  - name: loovie
    url: https://api.loovie.app/v1/mcp
```

`config.json` (legacy):

```json
{
  "experimental": {
    "modelContextProtocolServers": [
      { "name": "loovie", "url": "https://api.loovie.app/v1/mcp" }
    ]
  }
}
```

### Cline (compatible)

Open the Cline panel in VS Code → MCP Servers → paste:

```json
{
  "mcpServers": {
    "loovie": {
      "url": "https://api.loovie.app/v1/mcp"
    }
  }
}
```

### OpenCode (compatible)

Add to `~/.config/opencode/opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "loovie": {
      "type": "remote",
      "url": "https://api.loovie.app/v1/mcp",
      "enabled": true
    }
  }
}
```

### Smithery directory (compatible)

```bash
npx -y @smithery/cli install looviehq/loovie-mcp --client cursor
```

Replace `cursor` with `claude` / `vscode` / etc. — Smithery handles the per-client config dispatch.

### Any other MCP client (compatible)

The endpoint is a standard Streamable HTTP MCP server with OAuth 2.0 + DCR. Any spec-compliant client works — point it at `https://api.loovie.app/v1/mcp`.

## What it does

The Loovie MCP server exposes 100+ tools and 20+ resources covering the creative core of Loovie. Story-mode flows, sketches, keyframe animation, and LUTs aren't in MCP yet — they still live in the mobile app. What's in:

- **Characters** — create from a photo or a prompt, generate optional character sheets, manage variations.
- **Generation** — text-to-image, image-to-video, first/last frame, swap (face/character), motion control, AI VFX.
- **Editing** — clips, captions, picture-in-picture, transitions, music, color grading, speed curves.
- **Library** — backgrounds, music, sound effects, style presets, transitions, starter characters.
- **Lifecycle** — projects, exports, generation history, credits, spend approvals.

All spend tools follow a two-step pattern: `estimate_*` returns a credit cost and an approval token; `execute_*` consumes the token and starts the job. Your client confirms with you before each spend.

## What you'll see in each client

Loovie's output is media: images, videos, audio. The server returns markdown image syntax in tool results so chat clients render images inline in the assistant's reply. How it actually looks:

| Client | Images | Video / audio |
|---|---|---|
| Cursor | Rendered inline in chat, auto-saved to `assets/` | Clickable markdown link — opens in browser |
| Claude Desktop / Claude.ai web | Rendered inline in the assistant's reply (markdown image) | Clickable markdown link |
| Claude Code (CLI) | Clickable URL (`cmd+click` in iTerm2, `ctrl+click` in others) | Clickable URL |
| Other Streamable HTTP clients | Markdown-dependent — most render `![]()` inline | Clickable URL |

Every result also includes the plain URL on a second line as a fallback, so it works in every client even when inline rendering doesn't.

## Uploads — direct to R2

Loovie stores assets in Cloudflare R2 and uses presigned URLs so the client uploads **straight to R2** with no server proxy.

- **Local file + you have shell access**: `request_image_upload_url` (or `request_video_upload_url`) returns a presigned PUT URL plus an exact `curl` command. Run the curl. Then call `finalize_image_upload` (or `finalize_video_upload`). Bytes never transit the MCP server.
- **Remote URL the user shared**: the agent downloads the file locally first (`curl -L -o /tmp/...`), then uploads via the same presigned-PUT flow above. The MCP server doesn't fetch URLs on the agent's behalf for normal flows.
- **No shell access (rare)**: fallback only — `upload_image_for_reference({ url })` (server fetches once) or `upload_image_for_reference({ dataBase64 })` for small inline bytes.
- **Reads**: every asset URL the MCP returns is a presigned R2 URL — your client / browser fetches directly from R2, not through the API.

## What's bundled in the Claude Code plugin

- **Skills** — auto-invoked workflow guides for common tasks:
  - `making-a-loovie-video` — full happy path from idea to exported MP4
  - `character-from-photo` — turn a reference image into a reusable character
  - `editing-an-existing-project` — modify clips, captions, music, transitions
  - `exporting-and-sharing` — render and download
- **Slash commands** — `/loovie-new-project`, `/loovie-status`, `/loovie-credits`.

These ship inside the Claude Code plugin specifically (Claude Code has first-class plugin support for skills + commands). Other clients still get the tools and resources — they just don't get the bundled workflow guides.

## Credits and approvals

Loovie generations are paid for in credits. The plugin always shows the credit cost up front and waits for your approval before spending. Set an `autoApproveBelow` threshold via the `set_mcp_spend_preferences` tool to skip prompts for small spends.

## CLI reference

The `@loovie/mcp` package is the cross-client installer.

```bash
npx -y @loovie/mcp                                # interactive: detect + ask
npx -y @loovie/mcp install --all                  # non-interactive: install to every detected client
npx -y @loovie/mcp install --client cursor        # specific client
npx -y @loovie/mcp install --client cursor --project  # project-scoped .cursor/mcp.json
npx -y @loovie/mcp uninstall --all                # remove from every client
npx -y @loovie/mcp doctor                         # report which clients are wired
```

All JSON file mutations are atomic (temp file + rename) and back up the prior config once per run. Re-running install when already installed is a no-op.

## Sign up

You need a Loovie account to sign in. Get one at [loovie.app](https://loovie.app).

## Issues

File at [looviehq/loovie-community/issues](https://github.com/looviehq/loovie-community/issues). Officially-supported clients get fixed first; compatible clients are best-effort.

## License

Apache-2.0. See [LICENSE](../LICENSE).
