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
  const readFileSync = fs.readFileSync;
  // Each file maps to whether it was read, not only looked for: ESLint
  // looks for every flat config name, also ones it never loads.
  const loaded = new Map();
  const add = (file, probe) => loaded.set(file, loaded.get(file) || !probe);
  const record = (file, probe = false) => {
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
        add(path.join(realpathSync(folder), rest), probe);
        return;
      } catch {
        const up = path.dirname(folder);
        if (up === folder) {
          add(full, probe);
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
      // In Node's order: only the files tried before the one found matter.
      // `import` tries only the exact name; `require` also tries the
      // extensions it knows. These look-ups come from project code, so
      // they count as reads.
      // A folder's package.json `main` comes before its index files, and
      // a name ending in `/` (or `.`, `..`) is only a folder.
      const suffixes = context.conditions?.includes("require") === false
        ? [] : Object.keys(nodeModule._extensions || { ".js": 0, ".json": 0, ".node": 0 });
      const folderOnly = /(^|\/)\.{0,2}$/.test(specifier);
      const indexes = (folder) => suffixes.map((suffix) => path.join(folder, "index" + suffix));
      const mainOf = (folder) => {
        try {
          const main = JSON.parse(readFileSync(path.join(folder, "package.json"), "utf8")).main;
          return typeof main === "string" && main ? path.resolve(folder, main) : null;
        } catch {
          return null;
        }
      };
      const main = base && suffixes.length ? mainOf(base) : null;
      const candidates = !base ? [] : !suffixes.length ? [base] : [
        ...(folderOnly ? [] : [base, ...suffixes.map((suffix) => base + suffix)]),
        path.join(base, "package.json"),
        ...(main ? [main, ...suffixes.map((suffix) => main + suffix), ...indexes(main)] : []),
        ...indexes(base),
      ];
      let result;
      try {
        result = nextResolve(specifier, context);
      } catch (error) {
        for (const candidate of candidates) record(candidate);
        throw error;
      }
      const found = result.url.startsWith("file:") ? fileURLToPath(result.url) : null;
      const index = found ? candidates.indexOf(found) : -1;
      for (const candidate of index < 0 ? candidates : candidates.slice(0, index)) record(candidate);
      if (found) record(found);
      return result;
    },
  });
  // A look-up the project's own config makes, also through a library such
  // as path-exists, can change the config, also for a flat config name, so
  // it counts as a read. ESLint's own look-ups have only node_modules code
  // on the stack.
  const fromProject = () => {
    const limit = Error.stackTraceLimit;
    Error.stackTraceLimit = 200;
    const stack = new Error().stack || "";
    Error.stackTraceLimit = limit;
    return stack.split("\n").slice(1).some((line) =>
      // Frames with no file, such as `new Promise (<anonymous>)`, are skipped.
      !line.includes(__filename) && !line.includes("(node:") && !line.includes(" node:")
      && /[\\/]/.test(line) && !/[\\/]node_modules[\\/]/.test(line));
  };
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
    [fs.promises, "readFile"], [fs.promises, "open"],
  ]) {
    wrap(owner, name, (file) => record(file));
  }
  for (const [owner, name] of [
    [fs, "existsSync"], [fs, "statSync"], [fs, "accessSync"], [fs, "lstatSync"],
    [fs, "exists"], [fs, "stat"], [fs, "access"], [fs, "lstat"],
    [fs, "realpathSync"], [fs, "realpath"],
    [fs.promises, "stat"], [fs.promises, "access"], [fs.promises, "lstat"],
    [fs.promises, "realpath"],
  ]) {
    wrap(owner, name, (file) => record(file, !fromProject()));
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
  // A file only looked for is written with a leading `?`.
  process.on("exit", () => fs.appendFileSync(out, [...loaded].map(
    ([file, read]) => (read ? "" : "?") + file + "\n").join("")));
}
