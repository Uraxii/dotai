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
    // An absent file the config looks for can be added by the edit, so it
    // is kept below the real path of its nearest existing folder.
    let folder = full;
    let rest = "";
    for (;;) {
      try {
        loaded.add(path.join(fs.realpathSync(folder), rest));
        return;
      } catch {
        const up = path.dirname(folder);
        if (up === folder) {
          loaded.add(full);
          return;
        }
        rest = path.join(path.basename(folder), rest);
        folder = up;
      }
    }
  };
  nodeModule.registerHooks({
    resolve(specifier, context, nextResolve) {
      // Every file a relative lookup tries can be added by the edit, also
      // the ones tried before the file it found.
      if (/^\.{1,2}(\/|$)/.test(specifier) && context.parentURL?.startsWith("file:")) {
        const base = path.resolve(path.dirname(fileURLToPath(context.parentURL)), specifier);
        const suffixes = ["", ".js", ".cjs", ".mjs", ".ts", ".cts", ".mts", ".json", ".node"];
        for (const suffix of suffixes) record(base + suffix);
        record(path.join(base, "package.json"));
        for (const suffix of suffixes.slice(1)) record(path.join(base, "index" + suffix));
      }
      const result = nextResolve(specifier, context);
      if (result.url.startsWith("file:")) record(new URL(result.url));
      return result;
    },
  });
  for (const [owner, name] of [
    [fs, "readFileSync"], [fs, "readFile"], [fs, "openSync"], [fs, "open"],
    [fs, "existsSync"], [fs, "statSync"], [fs, "accessSync"], [fs, "lstatSync"],
    [fs, "exists"], [fs, "stat"], [fs, "access"], [fs, "lstat"],
    [fs.promises, "readFile"], [fs.promises, "open"],
    [fs.promises, "stat"], [fs.promises, "access"], [fs.promises, "lstat"],
  ]) {
    const original = owner[name];
    owner[name] = function (file, ...rest) {
      record(file);
      return original.call(this, file, ...rest);
    };
  }
  // Appended, as Node processes the config starts record to the same list.
  process.on("exit", () => fs.appendFileSync(out, [...loaded].map((file) => file + "\n").join("")));
}
