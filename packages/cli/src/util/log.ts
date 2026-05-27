/* eslint-disable no-console */
const COLOR = process.stdout.isTTY && !process.env.NO_COLOR;
const c = (code: string, s: string) => (COLOR ? `\x1b[${code}m${s}\x1b[0m` : s);

export const log = {
  info: (s: string) => console.log(s),
  success: (s: string) => console.log(`${c("32", "✓")} ${s}`),
  warn: (s: string) => console.log(`${c("33", "!")} ${s}`),
  error: (s: string) => console.error(`${c("31", "✗")} ${s}`),
  dim: (s: string) => console.log(c("2", s)),
  step: (s: string) => console.log(`\n${c("36", "›")} ${c("1", s)}`),
  raw: (s: string) => console.log(s),
};
