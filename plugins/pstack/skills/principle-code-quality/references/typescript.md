# TypeScript and JavaScript guidelines

Generated from `guidelines/` by `scripts/guideline_references.py`.
Edit the guideline files, then run the script.

- `ts.async.no-floating-promises` (warn): No floating promises. Await or return each promise, or attach a handler, so every rejection is handled.
- `ts.binding.no-var` (block): Never use `var`. Use `const`, or `let` when the binding is reassigned.
- `ts.binding.prefer-const` (warn): Default to `const`. Use `let` only when the binding is reassigned.
- `ts.boundary.schema-validation` (warn): Validate external data at API boundaries with Zod or valibot. Never trust its shape.
- `ts.class.readonly` (warn): Mark properties `readonly` when they should not change.
- `ts.config.strict` (warn): Set `strict: true` in tsconfig.
- `ts.default.nullish-coalescing` (warn): Use `??` instead of `||` for defaults.
- `ts.enum.no-enum` (warn): No `enum`. Use an `as const` object or a union of literal types.
- `ts.function.object-args` (warn): Pass one object argument instead of several positional ones, so each call site names its values. Skip this on hot paths such as per-frame render code, tokenizers, and parsers.
- `ts.import.named-exports` (warn): Use named exports and imports instead of default ones. Named imports stay correct when you refactor.
- `ts.logging.no-console` (warn): No `console.log` in shipped code. Use a structured logger whose output you can trace from an id.
- `ts.narrowing.hierarchy` (warn): Narrow with discriminated unions, not type casts. Use the best tool that works, in this order: discriminant switch, `in`, `typeof` or `instanceof`, a user-defined type guard, and `as` last.
- `ts.object.no-delete` (warn): No `delete` operator. Restructure the object or use a `Map`.
- `ts.switch.exhaustive` (warn): Make every switch exhaustive. Put `const _exhaustive: never = x;` in the default arm, so a new variant breaks the build.
- `ts.typing.brand-primitives` (warn): Brand semantic primitives, as in `type UserId = string & { readonly __brand: "UserId" }`. Validate once at creation and trust the value downstream.
- `ts.typing.construct-legal-values` (warn): Construct types so the illegal value cannot exist. Use `[T, ...T[]]` for non-empty, `[T, T][]` for even length, and `start` + `duration` for a range.
- `ts.typing.derive-types` (warn): Derive a type before you declare a new one. Use `Pick`, `Omit`, `Parameters`, `ReturnType`, `Awaited`, or `typeof`.
- `ts.typing.honest-type-guards` (warn): Make each type guard verify the claim it makes. A lying guard is worse than `as`. Name guards `isX` or `hasX`.
- `ts.typing.no-any` (warn): No `any` without a comment that justifies it (bare external data or generic constraints). Prefer `unknown` and validate at the boundary.
- `ts.typing.no-non-null-assertion` (warn): No `!` non-null assertion without a comment that says why it is safe.
- `ts.typing.no-wrapper-types` (warn): No `Object`, `Function`, or `String` types. Use the lowercase primitives.
- `ts.typing.satisfies-over-as` (warn): Use `satisfies` instead of `as` when you check type compatibility.
- `ts.typing.strengthen-where-partial` (warn): Keep `T[]` while every operation stays total. Strengthen to `NonEmpty<T>` only where the loose type forces `!`, a cast, or a never-happens throw.

## All languages

- `all.comment.no-commented-out-code` (warn): Delete commented-out code instead of keeping it as a comment.
- `all.comment.no-correctness-suppression` (warn): Never silence a correctness or safety check (`eslint-disable`, `@ts-ignore`, `@ts-expect-error`, `noqa`). Fix the flagged symbol instead. A style-only suppression such as `prettier-ignore` may stay.
- `all.complexity.cognitive` (warn): Keep cognitive complexity at 15 or less per function. Flatten with guard clauses, or extract a function.
- `all.complexity.cyclomatic` (warn): Keep cyclomatic complexity at 10 or less per function. Replace a long branch chain with a map, registry, or discriminated union, or extract a function.
- `all.error.no-broad-catch` (warn): No catch-all or empty catch blocks. Catch the errors you can handle and handle each one explicitly, per the surrounding context.
- `all.file.max-lines` (warn): Keep each file at 600 lines or fewer, with one cohesive responsibility. Split it by responsibility when it grows past that.
- `all.function.max-lines` (warn): Keep each function at 40 lines or fewer. Extract a named function when it grows past that.
- `all.function.return-types` (warn): Declare an explicit return type on every function, including `-> None` in Python. State the function contract.
- `all.line.max-length` (warn): Keep lines at 80 characters or fewer. Allow up to 100 when the longer line reads better.
- `all.literal.no-magic-numbers` (warn): No magic numbers. Use a named constant that carries the domain and the units, as in `REVIVE_TIME_SEC`.
- `all.naming.no-filler-words` (warn): Name the thing and its effect. Do not use structure filler (Manager, Controller, Handler, Helper, Util, Service, Data, Info, Object, Item) or scheduling words (Deferred, Pending, Delayed, Async, Lazy) as identity. Service is allowed only under an established subsystem convention, and its prefix must still carry meaning.
- `all.nesting.max-depth` (warn): Keep nesting at 3 levels or fewer. Use guard clauses with early returns, or extract a function.
- `all.string.second-language` (warn): No second language in a string past one line, such as SQL in a string, a Python heredoc in shell, or shell in YAML. Give it its own file so its linter checks it.
