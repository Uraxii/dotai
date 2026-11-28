// Loaded by the guideline hook through NODE_OPTIONS when it asks ESLint
// for a config: records every file Node resolves, so the hook knows which
// files the config reads. Needs node:module registerHooks (Node 22.15+);
// without it no list is written and the hook treats the result as unknown.
const fs = require("node:fs");
const nodeModule = require("node:module");
const { fileURLToPath } = require("node:url");

const out = process.env.PSTACK_ESLINT_LOADED;
if (out && typeof nodeModule.registerHooks === "function") {
  const loaded = new Set();
  nodeModule.registerHooks({
    resolve(specifier, context, nextResolve) {
      const result = nextResolve(specifier, context);
      if (result.url.startsWith("file:")) loaded.add(fileURLToPath(result.url));
      return result;
    },
  });
  process.on("exit", () => fs.writeFileSync(out, [...loaded].join("\n")));
}
