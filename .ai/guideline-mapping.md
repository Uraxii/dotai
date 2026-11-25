# Guideline mapping (from split agent; files not yet written, hook blocked .md writes)

File name = id with dots -> hyphens, in guidelines/. Frontmatter keys in order:
id, languages, scope, severity, enabled, detectors. Body 1-4 lines, imperative, keep limits.
Rule: a guideline is global when any listed language has no detector.

## all (languages: python, typescript, javascript, csharp, gdscript unless noted)
- all.function.max-lines (<=40) contextual warn: lizard:length, ruff:PLR0915, eslint:max-lines-per-function, sonar:S138
- all.file.max-lines (<=600) contextual warn: pylint:C0302, eslint:max-lines, sonar:S104, gdlint:max-file-lines
- all.line.max-length (<=80) contextual warn: ruff:E501, eslint:@stylistic/max-len, sonar:S103, gdlint:max-line-length
- all.function.return-types (py, ts) contextual warn: ruff:ANN201, ruff:ANN202, eslint:@typescript-eslint/explicit-function-return-type
- py.error.bare-except contextual block: ruff:E722
- all.error.no-broad-catch (py, ts, js, cs) contextual warn: ruff:BLE001, eslint:no-empty, roslyn:CA1031, sonar:S2221
- all.literal.no-magic-numbers global warn: ruff:PLR2004, eslint:@typescript-eslint/no-magic-numbers, sonar:S109
- all.nesting.max-depth (>3) contextual warn: ruff:PLR1702, eslint:sonarjs/nested-control-flow, sonar:S134, lizard:nested_structures
- all.complexity.cognitive (<=15) global warn: complexipy:cognitive, eslint:sonarjs/cognitive-complexity, sonar:S3776
- all.complexity.cyclomatic (<=10) contextual warn: ruff:C901, lizard:ccn, eslint:sonarjs/cyclomatic-complexity, sonar:S1541, roslyn:CA1505
- all.string.second-language global warn: ruff:S608
- all.comment.no-correctness-suppression global warn: ruff:PGH004, ruff:RUF100, eslint:@typescript-eslint/ban-ts-comment, eslint:eslint-comments/no-use, roslyn:IDE0079
- all.comment.no-commented-out-code global warn: ruff:ERA001
- all.naming.no-filler-words global warn: pylint:C0104, eslint:@typescript-eslint/naming-convention, roslyn:IDE1006

## python
- py.comprehension.one-for contextual block: code_quality:CQ001
- py.comprehension.no-nested-call contextual warn: code_quality:CQ002
- py.typing.strict contextual warn: mypy:strict
- py.function.mutable-default contextual block: ruff:B006
- py.import.no-star contextual block: ruff:F403
- contextual warn: py.path.pathlib (ruff:PTH), py.resource.context-manager (ruff:SIM115, pylint:R1732), py.string.f-strings (ruff:UP031, UP032), py.logging.no-print (ruff:T201), py.testing.pytest-style (ruff:PT009, PT027), py.error.no-assert-in-prod (ruff:S101), py.typing.collections-abc (ruff:UP035), py.import.order (ruff:I001)
- global warn, no detector: py.typing.ignore-needs-reason, py.data.dataclass-over-dict, py.module.dunder-all

## typescript / javascript
- ts.binding.no-var (ts, js) contextual block: eslint:no-var
- contextual warn (ts, js): ts.binding.prefer-const, ts.import.named-exports (import-x/no-default-export), ts.function.object-args (max-params), ts.logging.no-console
- contextual warn (ts): ts.typing.no-any, ts.typing.no-non-null-assertion, ts.typing.satisfies-over-as (consistent-type-assertions), ts.enum.no-enum (tsc:erasableSyntaxOnly), ts.async.no-floating-promises (+no-misused-promises), ts.typing.no-wrapper-types (no-wrapper-object-types, no-unsafe-function-type), ts.class.readonly, ts.default.nullish-coalescing, ts.switch.exhaustive
- global warn, no detector: ts.config.strict, ts.narrowing.hierarchy, ts.object.no-delete (ts, js), ts.boundary.schema-validation (ts, js), ts.typing.brand-primitives, ts.typing.construct-legal-values, ts.typing.strengthen-where-partial, ts.typing.honest-type-guards, ts.typing.derive-types

## csharp
- contextual warn: cs.resource.using (CA2000, IDE0063), cs.class.sealed (CA1852), cs.struct.readonly (IDE0250), cs.async.no-blocking (sonar:S4462), cs.pattern.matching (IDE0019, IDE0020), cs.perf.span (CA1846), cs.field.no-public (CA1051, stylecop:SA1401), cs.async.configure-await (CA2007), cs.string.ordinal-comparison (CA1307, CA1309), cs.boundary.argument-exceptions (CA1062, CA1510), cs.collection.expressions (IDE0028, IDE0300)
- cs.typing.no-dynamic global block, no detector
- global warn, no detector: cs.nullable.enable, cs.data.records, cs.async.iasyncenumerable, cs.string.interpolation

## gdscript
- gd.typing.static-hints contextual warn: godot:untyped_declaration
- global warn, no detector: gd.node.onready, gd.node.no-parent-chains, gd.node.null-check-before-tree, gd.node.is-instance-valid, gd.class.class-name, gd.export.inspector-values, gd.signal.connect-in-code, gd.signal.decouple, gd.process.early-return, gd.async.await, gd.state.enum-match, gd.resource.preload, gd.lookup.string-name, gd.group.cache-lookup, gd.doc.why-only, gd.doc.member-length, gd.doc.no-file-header, gd.doc.no-private-docs, gd.doc.no-process-references, gd.doc.bbcode, gd.comment.no-body-comments (grep detector in body), gd.null.truthiness, gd.nesting.guard-clause, gd.naming.effect-names

Unmapped: roslyn IDE0010/IDE0072 (no reference rule for C# switch exhaustiveness).
Stay in SKILL.md: compute-or-mutate, YAGNI, no-new-dependency, all judgement prose.
