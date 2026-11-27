# C# guidelines

Generated from `guidelines/` by `scripts/guideline_references.py`.
Edit the guideline files, then run the script.

- `cs.async.configure-await` (warn): Use `ConfigureAwait(false)` in library code. Omit it in app and UI code.
- `cs.async.iasyncenumerable` (warn): Use `IAsyncEnumerable` for streaming data. Do not buffer entire collections.
- `cs.async.no-blocking` (warn): Use `async`/`await` for IO. No `.Result`, `.Wait()`, or `.GetAwaiter().GetResult()`.
- `cs.boundary.argument-exceptions` (warn): Throw `ArgumentException` or `ArgumentNullException` at public API boundaries.
- `cs.class.sealed` (warn): Make classes `sealed` by default. Unseal a class only when its inheritance is designed.
- `cs.collection.expressions` (warn): Use collection expressions (`[1, 2, 3]`), not `new List<int>{...}` (C# 12+).
- `cs.data.records` (warn): Use `record` or `record struct` for immutable data. No manual `Equals` or `GetHashCode`.
- `cs.field.no-public` (warn): No `public` fields. Use properties, also on internal types.
- `cs.nullable.enable` (warn): Turn on nullable reference types: `<Nullable>enable</Nullable>`. Handle nulls explicitly.
- `cs.pattern.matching` (warn): Use pattern matching, not type casting: `is Type t`, not `as` plus a null check.
- `cs.perf.span` (warn): Use `Span<T>` or `Memory<T>`, not array slicing, on perf-critical paths.
- `cs.resource.using` (warn): Use `using` or `await using` for every `IDisposable`. No manual `.Dispose()`.
- `cs.string.interpolation` (warn): Use string interpolation, not `String.Format`.
- `cs.string.ordinal-comparison` (warn): Use `StringComparison.Ordinal` for strings that are not shown to users.
- `cs.struct.readonly` (warn): Use `readonly struct` for small value types. Do not write mutable structs.
- `cs.typing.no-dynamic` (block): No `dynamic`. Ever.

## All languages

- `all.comment.no-commented-out-code` (warn): Delete commented-out code instead of keeping it as a comment.
- `all.comment.no-correctness-suppression` (warn): Never silence a correctness or safety check (`eslint-disable`, `@ts-ignore`, `@ts-expect-error`, `noqa`). Fix the flagged symbol instead. A style-only suppression such as `prettier-ignore` may stay.
- `all.complexity.cognitive` (warn): Keep cognitive complexity at 15 or less per function. Flatten with guard clauses, or extract a function.
- `all.complexity.cyclomatic` (warn): Keep cyclomatic complexity at 10 or less per function. Replace a long branch chain with a map, registry, or discriminated union, or extract a function.
- `all.error.no-broad-catch` (warn): No catch-all or empty catch blocks. Catch the errors you can handle and handle each one explicitly, per the surrounding context.
- `all.file.max-lines` (warn): Keep each file at 600 lines or fewer, with one cohesive responsibility. Split it by responsibility when it grows past that.
- `all.function.max-lines` (warn): Keep each function at 40 lines or fewer. Extract a named function when it grows past that.
- `all.line.max-length` (warn): Keep lines at 80 characters or fewer. Allow up to 100 when the longer line reads better.
- `all.literal.no-magic-numbers` (warn): No magic numbers. Use a named constant that carries the domain and the units, as in `REVIVE_TIME_SEC`.
- `all.naming.no-filler-words` (warn): Name the thing and its effect. Do not use structure filler (Manager, Controller, Handler, Helper, Util, Service, Data, Info, Object, Item) or scheduling words (Deferred, Pending, Delayed, Async, Lazy) as identity. Service is allowed only under an established subsystem convention, and its prefix must still carry meaning.
- `all.nesting.max-depth` (warn): Keep nesting at 3 levels or fewer. Use guard clauses with early returns, or extract a function.
- `all.string.second-language` (warn): No second language in a string past one line, such as SQL in a string, a Python heredoc in shell, or shell in YAML. Give it its own file so its linter checks it.
