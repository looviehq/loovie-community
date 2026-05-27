import { defineConfig } from "tsup";

export default defineConfig({
  entry: { index: "src/index.ts" },
  format: ["esm"],
  target: "node18",
  platform: "node",
  bundle: true,
  clean: true,
  minify: false,
  sourcemap: false,
  splitting: false,
  shims: false,
  banner: { js: "#!/usr/bin/env node" },
});
