// Loaded by the guideline hook through NODE_OPTIONS when it asks ESLint
// for a config: records every file Node resolves or reads, so the hook
// knows which files the config uses or looks for (a TypeScript config loads through
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
    let name;
    try {
      name = file instanceof URL ? fileURLToPath(file) : file;
    } catch {
      return;
    }
    if (typeof name !== "string") return;
    const full = path.resolve(name);
    try {
      loaded.add(fs.realpathSync(full));
    } catch {
      // An absent file the config looks for can be added by the edit.
      try {
        loaded.add(path.join(fs.realpathSync(path.dirname(full)), path.basename(full)));
      } catch {
        loaded.add(full);
      }
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
    [fs, "existsSync"], [fs, "statSync"], [fs, "accessSync"],
    [fs.promises, "readFile"], [fs.promises, "open"],
    [fs.promises, "stat"], [fs.promises, "access"],
  ]) {
    const original = owner[name];
    owner[name] = function (file, ...rest) {
      record(file);
      return original.call(this, file, ...rest);
    };
  }
  process.on("exit", () => fs.writeFileSync(out, [...loaded].join("\n")));
}
