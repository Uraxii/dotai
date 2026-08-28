# Prototype

Pick when: "prototype", "mock it up", "sketch this", "try this layout", or
exploring a UI, interaction, or layout before committing. Also for settling an
empirical fork (which behaviour, which timing, which approach) by observing it
run, when you would otherwise ask the human a question a quick sketch answers.
You own the design decision, not the code. The prototype is a throwaway
instrument; the real build follows Feature. Load `prototype` for the build
mechanics.

The one role where "smallest change" and the verification bar invert. Speed
over polish, code quality does not matter, no planning. The rigor is in
picking the right design cheaply. Be bold: propose variations the user did not
ask for, throw an approach away and try another.

1. Scope the decision the prototype exists to make: which layout, which
   interaction, which density; for an empirical fork, which behaviour, timing,
   or approach. No decision means no prototype; route to Feature.
2. Gather references when the design space is open. Search prior art,
   summarize a moodboard of themes, palettes, and layouts, let the user pick
   directions before building. Skip when the direction is set.
3. Build throwaway in an isolated scratch dir, separate from production
   source. Visual decision -> vanilla HTML/CSS/JS or the lightest stack that
   renders the idea, CDN deps, a dev server with hot reload. Behavioural or
   timing decision -> the smallest script exercising the question. No
   production framework, no tests, no abstractions.
4. Comparing alternatives -> build them behind one switcher (buttons or a
   keypress), each variant labeled so the user can name it. This is
   `principle-exhaust-the-design-space` made cheap.
5. Verify on the matching surface. Visual decision -> screenshot each variant
   and drive the interaction; the eye is the test. Behavioural or timing
   decision -> observe the thing you are deciding: log the timing, print the
   output, watch the render. The observation is the test here, not an
   assertion.
6. Present alternatives, tradeoffs, and a recommendation. The output is the
   decision plus the throwaway artifact, not shippable code. Hand the chosen
   direction to Feature (or `architect-designer` for the shape) for the real
   build.

**Reply:** the variants explored, the evidence (screenshots for a visual
decision, observed output or timing for a behavioural one), tradeoffs, your
recommendation, the scratch path. Say plainly the prototype is throwaway.
