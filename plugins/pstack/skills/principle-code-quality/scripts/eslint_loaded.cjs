// Loaded by the guideline hook through NODE_OPTIONS when it asks ESLint
// for a config: records every file Node resolves or reads, so the hook
// knows which files the config uses (a TypeScript config loads through
// jiti, which reads with fs). Needs node:module registerHooks (Node
// 22.15+); without it no list is written and the hook treats the result
// as unknown.
const fs = require("node:fs");
const nodeModule = require("node:module");
const path = require("node:path");
const { fileURLToPath } = require("node:url");

const out = process.env.PSTACK_ESLINT_LOADED;
if (out && typeof nodeModule.registerHooks === "function") {
  const loaded = new Set();
  const record = (file) => {
    try {
      const name = file instanceof URL ? fileURLToPath(file) : file;
      if (typeof name === "string") loaded.add(fs.realpathSync(path.resolve(name)));
    } catch {
      // A file that does not exist cannot be changed by recording it.
    }
  };
  nodeModule.registerHooks({
    resolve(specifier, context, nextResolve) {
      const result = nextResolve(specifier, context);
      if (result.url.startsWith("file:")) record(new URL(result.url));
      return result;
    },
  });
  for (const [owner, name] of [
    [fs, "readFileSync"], [fs, "readFile"], [fs, "openSync"], [fs, "open"],
    [fs.promises, "readFile"], [fs.promises, "open"],
  ]) {
    const original = owner[name];
    owner[name] = function (file, ...rest) {
      record(file);
      return original.call(this, file, ...rest);
    };
  }
  process.on("exit", () => fs.writeFileSync(out, [...loaded].join("\n")));
}
