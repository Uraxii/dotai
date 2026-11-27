# Python guidelines

Generated from `guidelines/` by `scripts/guideline_references.py`.
Edit the guideline files, then run the script.

- `py.comprehension.no-nested-call` (warn): No `f(g(x))` inside a comprehension; name the inner result first.
- `py.comprehension.one-for` (block): One `for` per comprehension. Use a loop or `itertools.chain.from_iterable`.
- `py.data.dataclass-over-dict` (warn): Use a `dataclass` or `NamedTuple` instead of a raw dict for structured data.
- `py.error.bare-except` (block): No bare `except:`. Catch the specific exception and handle it explicitly, per the surrounding context.
- `py.error.no-assert-in-prod` (warn): No bare `assert` in production code, because `-O` strips it. Use `raise` instead.
- `py.function.mutable-default` (block): No mutable default arguments such as `def f(x=[])`. Default to `None` and build the value inside the function.
- `py.import.no-star` (block): No star imports (`from x import *`). Import the names you use.
- `py.import.order` (warn): Order imports stdlib, then third-party, then local, with a blank line between groups.
- `py.logging.no-print` (warn): Use `logging` instead of `print` in library and app code.
- `py.module.dunder-all` (warn): Define `__all__` in every public module.
- `py.path.pathlib` (warn): Use `pathlib` instead of `os.path`.
- `py.resource.context-manager` (warn): Open every resource (files, locks, connections) in a `with` context manager.
- `py.string.f-strings` (warn): Use f-strings. Prefer them over `.format()`, and `.format()` over `%`.
- `py.testing.pytest-style` (warn): Follow `pytest` conventions. Give tests a `test_` prefix, and use fixtures instead of `setUp`.
- `py.typing.collections-abc` (warn): Import annotation types from `collections.abc`, not `typing` (Python 3.9+).
- `py.typing.ignore-needs-reason` (warn): Every `type: ignore` carries an inline comment that says why.
- `py.typing.strict` (warn): Type-hint every function signature, with `-> None` explicit. No untyped public API.

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
