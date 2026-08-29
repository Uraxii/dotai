# Swarm brief: owner voice study (writing samples)

## Goal
Find documents the owner wrote herself inside your slice of /home/nicole/Downloads/college-work, and describe HOW she writes in each context: stylistic choices, tone, word choice, sentence shape, punctuation/spelling habits, with verbatim examples. This feeds a style reference for a report-writing skill. The owner is the student named in filenames as "Brandon Paul" / "Brandon-Paul" / "Paul" (she now goes by Nicole; same person).

## Scope
ONLY your slice (given in your spawn message). Read nothing outside it.

## Authorship filter
- Likely hers: assignments, papers, reports, notes, reflections, discussion posts, emails, resumes, cover letters, personal docs, code comments/READMEs.
- NOT hers, skip: lecture slides, textbook chapters, third-party papers (author names not Paul), sample quizzes, instructor handouts, syllabi, templates, downloaded forms.
- Group work (several names in filename or title page): include but tag `co-authored, low confidence`.
- If unsure, say so; do not guess silently.

## Hard rules
- NEVER open: password.txt, *.key, *.crt, *.pem, images, audio, video, archives, pcap.
- Do not quote grades, addresses, phone numbers, ID numbers, financial figures, medical or legal detail. Quote only lines that show style.
- Quotes: 2-5 per document, each <= 40 words, verbatim, preserve her spelling and punctuation exactly.
- Do not paste whole documents into your report. Your report must stay under ~2500 words.
- Do not write anywhere except your own output file.
- Do not spawn other agents.
- Never write ~/.knowledgebase or ~/.beads-hub.

## How to read a .docx (no pandoc, no python-docx installed)
unzip -p "FILE.docx" word/document.xml | sed -e 's/<\/w:p>/\n/g' -e 's/<[^>]*>//g' | sed '/^\s*$/d'
PDFs: pdftotext if present (`which pdftotext`), else skip and list as unread.
Triage fast: run `wc -w` on extracted text; sample first, read fully only docs that pass the authorship filter.

## Output
Write Markdown to your output file (given in your spawn message) with:
1. `## Inventory` table: file, context (assignment/notes/personal/email/report/code), authorship verdict (hers / co-authored / not hers / unread), words.
2. `## Per-context profile`: one section per context found. For each: register and tone; sentence shape (typical length, structure, fragments?); word choice (favourite words, hedges, intensifiers, jargon, contractions y/n); structure habits (headings, lists, paragraph length, intros/conclusions); punctuation and spelling quirks (recurring typos, comma habits, dashes, capitalisation); 3-6 verbatim quotes with file name.
3. `## Cross-cutting observations`: what stays constant across contexts, what shifts, and what marks a piece as hers vs generic.
4. `## Status`: PASS (slice covered), ISSUES (covered with caveats, list them), or BLOCKED (why). List unread files.

Style of your report: terse, concrete, no filler, no praise of the writing.
