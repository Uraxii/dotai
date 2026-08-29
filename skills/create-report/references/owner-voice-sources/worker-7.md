# Slice 7: code projects (Text_Adventure, TurnBasedCombat_Test, xml_parser, inventory_manager.pl, Mice-Sensors non-docx)

## Inventory

| File | Context | Authorship | Words |
|---|---|---|---|
| Text_Adventure_0.1/main.cpp | code | hers | 1131 |
| Text_Adventure_0.1/Scrap.txt (earlier draft of same code) | code | hers | 210 |
| Text_Adventure_0.1/main.cpp.save-failed (autosave draft) | code | hers | 129 |
| TurnBasedCombat_Test/main.cpp | code | hers | 150 |
| TurnBasedCombat_Test/abilities.cpp + abilities.h | code | hers | 91 |
| TurnBasedCombat_Test/src/Abilities.cpp + include/Abilities.h (duplicate/leftover scaffold) | code | hers | 32 |
| TurnBasedCombat_Test/Abilities.txt | code/data | hers | 1 |
| TurnBasedCombat_Test/Ability_Data.txt | code/data | hers | 63 |
| xml_parser/main.cpp | code | hers | — |
| xml_parser/xmlparse.cpp + xmlparse.h | code | hers | 214 combined w/ test.xml |
| xml_parser/test.xml | code/data | hers (placeholder content, low signal) | — |
| inventory_manager.pl | code | hers | 545 |
| Mice-Sensors/Mooses.pptx | assignment (presentation) | hers, high confidence (no co-author names found, no metadata present) | 255 |
| Mice-Sensors/CS 223-B T1 stavens_opencv_optical_flow.pdf | third-party | not hers (Stanford AI Lab slide deck, author David Stavens) | unread past p.1 |
| Mice-Sensors/OPTICAL_MOUSE_SENSOR.pdf | third-party | not hers (NST Technologies datasheet) | unread past p.1 |

Skipped, no prose: `.exe`/`.o` binaries, `.cbp`/`.depend`/`.layout` Code::Blocks project files (checked for author/title fields — only contain project name, matches folder name, no names).

## Per-context profile

### Code — C++ (Text_Adventure_0.1, TurnBasedCombat_Test, xml_parser)

Register/tone: functional, terse, talks to herself mid-comment. Drops into first person to flag things she doesn't understand or is unsure of, right inside otherwise plain code comments.

Sentence shape: short imperative/declarative fragments in comments ("Generates rows on x-coordinate"). Player-facing strings are full sentences, occasionally elaborate ("You ran around the room aimlessly. Never finding, and ultimately forgetting, exactly what you were searching for.").

Word choice: no contractions in Javadoc-style blocks, contractions appear in casual asides ("Don't ask", "I'm not sure"). No hedges in code comments except the self-aware aside. All-caps used for shouted system messages ("INVALID COMMAND...", "ERROR FILE DID NOT OPEN").

Structure habits: ASCII banner dividers to mark sections — `//-----     FUNCTIONS       -----`, `//-----     MAIN FUNCTION   -----`. Javadoc-style `/** @param @return */` blocks in Text_Adventure_0.1/main.cpp, several left with blank param/return lines (documented the shape of the doc before filling it in). Dead code left commented out rather than deleted, in all three projects. TurnBasedCombat_Test has duplicate ability-class scaffolding in two locations (`abilities.h/.cpp` lowercase vs `include/Abilities.h`, `src/Abilities.cpp` capitalized) — reorg cruft never cleaned up.

Punctuation/spelling quirks: "formated" for formatted (main.cpp docstring). "Quiting game..." for Quitting. Comma-spacing inconsistent in data/comment lines — `Use,Description` and `attack,dealing` run words into the comma with no space, elsewhere she does space it.

Naming: mixed casing conventions inside the same project — camelCase locals (`roomNumber`, `maxX`) next to PascalCase-with-underscore functions (`Set_Coordinates`, `Current_Room`, `Lower_Case`, `Set_Abilities`). Player-state variables carry a `p` prefix (`pX`, `pHealth`, `pMana`, `pGold`, `pLvl`, `pXP`).

Quotes:
- "Actual max values should be <max value> - 1. So the if maxZ = 3, the highest value Z the player should have is 2 because there is a floor 0." — Text_Adventure_0.1/main.cpp
- "You ran around the room aimlessly. Never finding, and ultimately forgetting, exactly what you were searching for." — Text_Adventure_0.1/main.cpp
- "Don't ask my why this works right now. I'm not sure." — Text_Adventure_0.1/main.cpp
- "Shoots a ball of fire at a target." — TurnBasedCombat_Test/Ability_Data.txt
- "Counter an attack,dealing half the damage taken to the attacker." — TurnBasedCombat_Test/Ability_Data.txt
- "-->>>GetAll method called<<<--" — xml_parser/xmlparse.cpp (commented-out debug print)

### Code — Perl (inventory_manager.pl)

Register/tone: narrative and self-directed, more monologue than spec. Comments talk through what the program should eventually do, hedge with "if I REALLY want to," muse about implementation options ("I suppose, I could...").

Sentence shape: comment sentences run longer than the C++ comments, nested asides using extra levels of indentation to mark "thinking out loud" versus the main comment line (see the tabbed sub-bullets under the file header).

Word choice: "REALLY" in caps for emphasis. First-person planning language: "I can probably," "I suppose," "I never finished." No contractions in the header comment, contractions appear once she's musing casually.

Structure habits: banner dividers carried over from the C++ style — `# ---------- MAIN MENU ----------`, same convention, different comment character. Bracket-wrapped debug tag repeated verbatim throughout: `---DEBUG--- \$input=[$input]\n`. POD `=comment`/`=cut` blocks used to shelve an entire earlier, abandoned version of the script with an apology-note header rather than deleting it.

Punctuation/spelling quirks: consistent space-before-semicolon (`use strict ;`, `exit ;`) — a stable habit, not scattered typos. Recurring misspelling of "inventory" as "invintory" (3 occurrences). Other one-off typos: "applocation" (application), "appliaction" (application), "refference" (reference), "everytime" (every time), section header "SEACH FOR ITEM" (search), header "STAEMENTS" (statements).

Quotes:
- "This application will create and modify an invintory system." — inventory_manager.pl
- "Being able to use a HTML file for this would be nice." — inventory_manager.pl
- "This is a half-baked previous attempt I never finished." — inventory_manager.pl
- "I suppose, I could probably use recursion to populate the @s." — inventory_manager.pl
- "ERROR [1] --- Invalid Command. Please try again." — inventory_manager.pl

### Assignment — presentation (Mice-Sensors/Mooses.pptx)

Register/tone: deadpan comic, first person, undercuts the academic subject on purpose. Reads as a solo class presentation she wrote to entertain herself/the room, not a formal deck.

Sentence shape: short punchy slide lines, several one-liners standing alone as a full slide ("TRY A RAT!"). Occasional longer explanatory line per slide, rarely more than two sentences.

Word choice: sarcastic asides framed as confessions ("I stole from a random ... document I found"), scare quotes around slang ("the 'good old days'", "real jobs"), a made-up nickname presented as fact ("The 'Nipple'"). No hedges — declarative even when joking.

Structure habits: title-plus-punchline slide pattern, one fake-citation gag slide ("- Some person on Wikipedia, some point in time."), a recurring joke thread (mouse vs. rat) that returns across three slides.

Punctuation/spelling quirks: curly quotes used natively (via PowerPoint autocorrect) rather than straight quotes; trademark symbol used as a joke ("PetSmart™ - 2017"); title-case slide headers.

Quotes:
- "Don't Like Mice? TRY A RAT!" — Mooses.pptx, slide 3
- "This is a block diagram I stole from a random NST Techsemic document I found" — Mooses.pptx, slide 8
- "Refers to the "good old days" when mice had to do "real jobs" and performed physically intensive mouse tracking" — Mooses.pptx, slide 6
- "Pointing Stick AKA The "Nipple"" — Mooses.pptx, slide 13
- "Old mice used to work like old people things" — Mooses.pptx, slide 6

## Cross-cutting observations

- Constant across all three contexts: first-person asides that break from the task to comment on her own uncertainty or lack of effort ("Don't ask my why this works right now. I'm not sure." / "I stole from a random ... document I found" / "This is a half-baked previous attempt I never finished."). This self-deprecating aside is the strongest single marker of her voice — it shows up whether the surface is a code comment or a slide.
- Constant: ASCII banner-style section dividers, present in both C++ (`//-----`) and Perl (`# ----------`) — same organizing habit ported across languages.
- Constant: leaves earlier/abandoned work in place next to the current version rather than deleting it — commented-out debug prints, a full previous script shelved in a POD block, a duplicate class-file scaffold, a `.save-failed` draft and a `Scrap.txt` draft kept alongside the final file.
- Shifts: formality of comments. Text_Adventure_0.1 uses structured Javadoc-style docstrings (`@param`/`@return`) even when left half-empty; TurnBasedCombat_Test and xml_parser drop that structure for bare inline comments; Perl comments are the most narrative/conversational of the three.
- Shifts: humor register. Deadpan/self-aware humor is restrained to single asides in code (one or two per file) but is the dominant mode of the whole presentation — the presentation is where her voice is least filtered.
- What marks a piece as hers vs. generic: the self-directed narration in comments/notes (thinking through a decision on the page, admitting uncertainty), the recurring debug-bracket habit, the specific misspellings (invintory, refference, appliaction/applocation), and inconsistent-but-patterned naming (banner dividers, `p`-prefixed variables, Pascal_With_Underscore function names). Generic/non-hers material in this slice (the two Mice-Sensors PDFs) reads as flat, third-person, and citation-formal by contrast — no first-person asides, no jokes, standard technical register.

## Status

PASS — slice covered. All in-scope source and text files were read in full; the two PDFs were sampled (page 1 each) to confirm third-party authorship, per the triage rule, then set aside as not hers. No files unread due to missing tools (pdftotext and unzip were both available). No group-work / multi-author filenames found in this slice — nothing tagged co-authored.
