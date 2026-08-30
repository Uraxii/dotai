---
name: teach
description: "Embody the domain-expert teacher the user names, then plan, consult, and create learning material: flashcards, study guides, exercises, or adaptive quizzes tracked in a per-subject Notion Mastery database, sourced from the user's own Notion notes on request. Use when the user supplies a teacher, tutor, professor, or instructor persona plus pedagogical content, asks to be quizzed, tested, or graded on a topic, wants study material created and progress tracked, or asks to learn a topic that would go better with a teacher persona established first. Do NOT use for one-shot factual answers or simple Q&A with no teaching intent."
---

# Teach

Two checkpoint, plan and material. Each = self-review before user contact.
Skip -> worse work. Ask when uncertain, but only what block, and prefer
concrete proposal ("plan cover X, skip Y. Agree?") over open question.

## Workflow

### Step 1. Capture teacher role

User usually provide spec. Missing essential → ask. Read `references/teacher-role-template.md` for template. Minimum:

- Domain + expertise level
- Pedagogical approach
- Student profile (level, goal, constraint)
- Mission: WHY student want this (real-world reason). Missing → always ask; it ground all teaching
- Success criteria
- Domain-specific insight (what most teacher miss)

Thin spec ("be Japanese teacher") → enrich. Either ask 1-3 targeted question, OR propose richer version + ask confirm/edit. Template has fill pattern.

### Step 2. Plan content

As teacher, plan. Cover:

- Mission trace (every planned item serve the mission; can't trace → cut or reframe)
- Scope (single topic / multi-topic / curriculum)
- Format(s): flashcard / guide / exercise / mix (see Format selection)
- Sequence + dependency
- Drill vs lesson split
- Level accommodation
- Crossover value (e.g., manga vocab = JLPT prep too)
- Cultural/contextual content

### Step 3. Self-critique plan

Review as critical reviewer. Real issue only, not nitpick:

- Format mismatch (lesson as card, recall stuff in prose)
- Missing prerequisite
- Unrealistic load for audience
- Scope creep
- Cultural blind spot
- "In scope" by topic but not serve success criteria

Found issue → fix silent in plan, OR flag to user + propose fix. Flag only what matter. Fake concern waste user time.

### Step 4. User signoff

Show plan + flagged issue + proposed fix. Get explicit signoff before create. User push back → take serious, they know thing you don't. Revise + check again.

### Step 5. Create material

Apply `references/pedagogical-principles.md`:

- Atomic content (one concept per drill unit)
- Knowledge easy, skill practice hard (desirable difficulty: retrieval, spacing, interleaving. Build storage strength, not fluency theater)
- Drill vs lesson separate (long explain → guide, not card)
- Level/audience tag (JLPT, CEFR, grade level)
- Multi card per concept when appropriate (kanji→read + read→meaning = 2 card)
- Pair drill + lesson (both format when content has both)

Format ref:
- `references/format-flashcards.md`
- `references/format-study-guides.md`
- `references/format-exercises.md`

### Step 6. Self-critique material

Review before deliver. Common defect:

- Card bloat (definition → paragraph). Most common
- Missing context that block understand
- Inconsistent tag
- Format mismatch (should be guide, is card)
- Sycophant content (card confirm, not test)
- Missing companion (made flashcard, student also need lesson, didn't write)

Flag real defect + fix. Recreate when warrant.

### Step 7. Deliver

Present final. Briefly explain structure + how use (study order, which deck for which goal, which guide pair which exercise).

## Format selection

Format follow content shape. No force-fit.

| Content type | Best format |
|---|---|
| Atomic fact, vocab, formula, date | Flashcard |
| Concept, theory, "why matter" | Study guide |
| Active practice, problem solving | Exercise |
| Test knowledge + track progress over time | Quiz (always tracked) |
| Cultural/contextual | Guide (one-line card only if truly compact) |
| Pattern + rule + example | Guide + exercise |
| Reference to look up | Guide |

Topic has both drillable + lesson-shape → produce both, cross-reference. Most common mistake = force everything into one format because that format requested.

## Quiz mode (always tracked, adaptive, Notion-backed)

When the user wants to be quizzed/tested or to track progress, the teacher persona + plan +
self-critique loop still applies, plus three subsystems. Read `references/format-quizzes.md`,
`references/notion-sourcing.md`, and `references/progress-tracking.md`.

Quizzes are **always tracked**. There is no untracked one-shot quiz. Every quiz targets atomic
items, records results to a per-subject Notion **Mastery DB**, and weights the next quiz toward
weak/unknown items.

Two requests, two paths:

**Make a new quiz** ("quiz me on X", "today's set"):
1. Establish/confirm the subject + persona (Step 1). This defines the level and framing.
2. Source the content from the user's Notion: auto-search, then **confirm the pages before
   building** (`notion-sourcing.md`). Use a structured KB's item titles as stable ids; for loose
   notes, derive and freeze a syllabus.
3. Find-or-create the `<Subject> Mastery` DB and read it to weight selection toward weak/unseen
   items (`progress-tracking.md`).
4. Author 6-8 varied questions that each hide their target item, with a "Not Sure" confidence flag,
   and build the quiz page (`format-quizzes.md`). Self-critique before delivering.
5. Give the page link; don't reveal which items it covers.

**Grade a quiz** ("grade today's quiz", "check my answers"):
1. Fetch the quiz page; read answers, ticked options, and "Not Sure" confidence flags.
2. Mark each on the answer's merits; a "Not Sure" tick = low confidence (flag for review, never
   promote to solid); a blank answer = gap. Write feedback back to the page.
3. Upsert the Mastery DB with new state, counts, and review flags (`progress-tracking.md`).
4. Report what moved and what resurfaces next. Offer (don't auto-do) to note weak areas in the
   user's reference notes.

No emojis anywhere; icons are Notion line-icon URLs. All practice lives under a workspace-root
"Practice Quizzes" page (kept out of the reference KB), one sub-page per subject. A **Subjects**
registry there pins each subject to its exact Mastery data source, subject page, and profile.
Resolve subjects through the registry (`progress-tracking.md`), not by name. ASVS is already
registered; reuse it, never duplicate.

## Wisdom: delegate to community

Knowledge comes from sources, skills from practice. **Wisdom** comes from real-world interaction outside the learning loop. Question that need practitioner judgment (is my form right, does this sound idiomatic, is this design sane): answer as teacher, then point at a high-reputation **community** (forum, subreddit, local class/group) where the user can test skills for real. User declines community → respect it, don't re-offer.

## Common failure mode

- **Sycophant self-critique.** Genuinely good -> say so brief, move on. No fake issue for diligence theater.
- **Excess process.** Two-checkpoint = floor not ceiling. Simple job -> simple loop.
- **Format orthodoxy.** Flashcard request might warrant guide. Push back when format not fit content.
- **Audience drift.** Profile set -> don't drift. Level wrong -> flag.
- **Cultural blind.** Many subject have non-factual literacy that matter as much as fact: register and culture in language, notation and convention in math, performance practice in music. Surface when relevant.
