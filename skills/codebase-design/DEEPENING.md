# Deepening

How to deepen a cluster of shallow modules given its dependencies. Assumes the
vocabulary in [SKILL.md](SKILL.md): **module**, **interface**, **seam**,
**adapter**. Seam discipline (one adapter is hypothetical, two is real;
internal seams stay internal) lives there too and governs ports here.

## Dependency categories

Classify the candidate's dependencies. The category decides how the deepened
module is tested across its seam.

1. **In-process.** Pure computation, in-memory state, no I/O. Always
   deepenable: merge the modules, test through the new interface, no adapter.
2. **Local-substitutable.** Has a local test stand-in (PGLite for Postgres,
   in-memory filesystem). Deepenable if the stand-in exists; it runs in the
   test suite. The seam is internal, so no port at the external interface.
3. **Remote but owned.** Your own services across a network. Define a port at
   the seam. The deep module owns the logic; the transport is an injected
   adapter, in-memory for tests and HTTP/gRPC/queue in production.
4. **True external.** Third-party services you do not control. Same shape as 3:
   injected port, mock adapter in tests.

## Testing strategy: replace, do not layer

- Old unit tests on the shallow modules become waste once tests at the deepened
  interface exist. Delete them.
- Write the new tests at the deepened module's interface. The interface is the
  test surface.
- Assert on observable outcomes through the interface, never internal state. A
  test that must change when the implementation changes is testing past the
  interface.
