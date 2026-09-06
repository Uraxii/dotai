---
name: principle-decomposition
description: Use the moment a brief lands in your hands, before the first tool call, and whenever you are about to write a brief for someone else. Also use when a unit comes back partial, or when you are tempted to fan one artifact out across several agents. Decides whether the job is one unit you do yourself or a split you delegate, and bounds how far a split may spread.
---

# Decomposition

Every agent sizes its own work when the brief lands; nobody plans the tree up front.

- Unit test: one artifact, one verify command, one kind of work, and a reviewer
  could reject it while approving its neighbour. Fold setup, config, and docs into
  the unit whose deliverable needs them. Passes -> do it yourself. Fails -> split.
- Spawn only when it buys breadth, isolation, or independence. Buys none -> do it
  inline. Write one line per child naming its scope; two overlap -> merge them.
- Scale waves, not width. Dependent work chains as fresh spawns; a wave that finds
  new territory gets a second targeted wave, not a bigger first one.
- A child that only re-delegates what it received is a layer. Delete it.
- Partial return: re-cut the remainder into new units. Never re-spawn the same brief
  bigger. Regular overruns mean this text is wrong: fix the text.
- No ceilings, budgets, scripts, hooks, or watchers size work. Judgment at receipt does.
