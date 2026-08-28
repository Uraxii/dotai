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
- Brand primitives so they can't be swapped: `type UserId = string & {
  readonly __brand: "UserId" }`. Validate once at creation.
- Construct the shape so the illegal value can't exist: `[T, ...T[]]` for
  non-empty, `[T, T][]` for even length, `start` + `duration` for a range. Not
  a runtime guard, not a wish for refinement types.
- Simplest total type: keep `T[]` while every operation on it stays total.
  Strengthen to `NonEmpty<T>` only where the loose type force `!`, a cast, or a
  "should never happen" throw.
- Narrowing hierarchy, best first: discriminant switch > `in` > `typeof` /
  `instanceof` > user-defined type guard > `as`.
- Type guard must verify the claim it makes. Lying guard worse than `as`: bug
  hide behind a name saying it's safe. Name `isX` / `hasX`.
- Exhaustiveness: inline `const _exhaustive: never = x;` in default arms, so a
  new variant break the build.
- Derive types from what already exist: `Pick` / `Omit` / `Parameters` /
  `ReturnType` / `Awaited` / `typeof` before declaring a new interface.
- Object args over positional, so argument order self-document. Skip on hot
  paths (per-frame render, tokenizers, parsers).
- No `console.log` in shipped code. Structured logger with enough context to
  debug from an id.
