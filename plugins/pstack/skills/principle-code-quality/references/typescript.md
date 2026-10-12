# TypeScript rules

- `strict: true` in tsconfig. No `any` w/o comment justifying (bare,
  external data, or generic constraints); prefer `unknown`, validate at boundary.
- No `!` non-null assertion w/o comment why safe.
- `const` default. `let` only when reassigned. Never `var`.
- Discriminated unions over type casting for narrowing.
- No `enum`, use `as const` objects or union literal types.
- Async: always handle rejection. No floating promises.
- Named imports over default (refactor-safe).
- No `Object`, `Function`, `String`, use lowercase primitives.
- `readonly` on properties that shouldn't mutate.
- No `delete` operator, restructure or use `Map`.
- Zod/valibot at API boundaries. No trust of external shape.
- `satisfies` over `as` when asserting type compatibility.
- Nullish coalescing (`??`) over logical OR (`||`) for defaults.
- Brand primitives: `type UserId = string & { readonly __brand: "UserId" }`.
- Construct so the illegal value can't exist: `[T, ...T[]]` non-empty, `[T,
  T][]` even length, `start` + `duration` for a range.
- Keep `T[]` while every operation stays total. Strengthen to `NonEmpty<T>`
  only where the loose type force `!`, a cast, or a never-happens throw.
- Narrowing hierarchy, best first: discriminant switch > `in` > `typeof` /
  `instanceof` > user-defined type guard > `as`.
- Type guard must verify the claim it makes; lying guard worse than `as`.
  Name `isX` / `hasX`.
- Exhaustiveness: inline `const _exhaustive: never = x;` in default arms, so a
  new variant break the build.
- Derive before declaring: `Pick` / `Omit` / `Parameters` / `ReturnType` /
  `Awaited` / `typeof`.
- Object args over positional, so argument order self-document. Skip on hot
  paths (per-frame render, tokenizers, parsers).
- No `console.log` in shipped code. Structured logger, debuggable from an id.
