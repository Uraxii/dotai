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
  const realpathSync = fs.realpathSync;
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
        loaded.add(path.join(realpathSync(folder), rest));
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
      // Every file a path lookup from project code tries can be added by
      // the edit, also the ones tried before the file it found. Lookups
      // inside node_modules are left out: there are thousands.
      const parent = context.parentURL?.startsWith("file:") ? fileURLToPath(context.parentURL) : null;
      let base = null;
      if (parent && !parent.split(path.sep).includes("node_modules")) {
        if (specifier.startsWith("file:")) {
          try {
            base = fileURLToPath(specifier);
          } catch {}
        } else if (/^\.{1,2}(\/|$)/.test(specifier) || path.isAbsolute(specifier)) {
          base = path.resolve(path.dirname(parent), specifier);
        }
      }
      if (base) {
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
  // The wrapper keeps the original's own properties, such as the custom
  // promisify of fs.exists and realpathSync.native.
  const wrap = (owner, name, before) => {
    const original = owner[name];
    const wrapper = function (file, ...rest) {
      before(file);
      return original.call(this, file, ...rest);
    };
    for (const key of Reflect.ownKeys(original)) {
      if (!Object.hasOwn(wrapper, key)) {
        Object.defineProperty(wrapper, key, Object.getOwnPropertyDescriptor(original, key));
      }
    }
    owner[name] = wrapper;
  };
  for (const [owner, name] of [
    [fs, "readFileSync"], [fs, "readFile"], [fs, "openSync"], [fs, "open"],
    [fs, "existsSync"], [fs, "statSync"], [fs, "accessSync"], [fs, "lstatSync"],
    [fs, "exists"], [fs, "stat"], [fs, "access"], [fs, "lstat"],
    [fs, "realpathSync"], [fs, "realpath"],
    [fs.promises, "readFile"], [fs.promises, "open"],
    [fs.promises, "stat"], [fs.promises, "access"], [fs.promises, "lstat"],
    [fs.promises, "realpath"],
  ]) {
    wrap(owner, name, (file) => record(file));
  }
  // A listed folder is kept as `folder/*`: a file the edit adds in it
  // can change the config, also when a glob library lists it.
  for (const [owner, name] of [
    [fs, "readdirSync"], [fs, "readdir"], [fs, "opendirSync"], [fs, "opendir"],
    [fs.promises, "readdir"], [fs.promises, "opendir"],
  ]) {
    wrap(owner, name, (folder) =>
      record(path.join(folder instanceof URL ? fileURLToPath(folder) : String(folder), "*")));
  }
  // Appended, as Node processes the config starts record to the same list.
  process.on("exit", () => fs.appendFileSync(out, [...loaded].map((file) => file + "\n").join("")));
}
