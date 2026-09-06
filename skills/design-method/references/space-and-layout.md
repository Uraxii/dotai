# Space and layout

## Ten named steps on a 4px base

```css
:root {
  --space-3xs: 0.125rem;  /*   2px */
  --space-2xs: 0.25rem;   /*   4px */
  --space-xs:  0.5rem;    /*   8px */
  --space-sm:  0.75rem;   /*  12px */
  --space-md:  1rem;      /*  16px */
  --space-lg:  1.5rem;    /*  24px */
  --space-xl:  2.5rem;    /*  40px */
  --space-2xl: 4rem;      /*  64px */
  --space-3xl: 6rem;      /*  96px */
  --space-4xl: 9rem;      /* 144px */
}
```

The jumps run 2, 2, 1.5, 1.333, 1.5, 1.667, 1.6, 1.5, 1.5, so this is a curated
ladder on a 4px grid, not a generated one. It still does the job: it gives a
fixed set to pick from and forbids raw pixel values.

Names are roles, so changing a value does not mean renaming every use site.

`artifact-design` already says to let layout do the spacing, which makes the
ladder usable: gaps on the container, `margin` for optical nudges. Mix small,
medium and large gaps, because a page where every gap is 24px reads as a
template.

## Fluid space ladder

Generate spacing from the same viewport range and base size as the type ladder,
and the two stay in proportion as the viewport changes. The values below share
the type ladder's inputs: 320px to 1240px, 16px to 18px base.

```css
:root {
  --space-3xs: clamp(0.25rem, 0.23rem + 0.11vw, 0.31rem);
  --space-2xs: clamp(0.50rem, 0.46rem + 0.22vw, 0.63rem);
  --space-xs:  clamp(0.75rem, 0.69rem + 0.33vw, 0.94rem);
  --space-s:   clamp(1.00rem, 0.93rem + 0.33vw, 1.13rem);
  --space-m:   clamp(1.50rem, 1.39rem + 0.54vw, 1.69rem);
  --space-l:   clamp(2.00rem, 1.85rem + 0.76vw, 2.25rem);
  --space-xl:  clamp(3.00rem, 2.78rem + 1.09vw, 3.38rem);
  --space-2xl: clamp(4.00rem, 3.70rem + 1.52vw, 4.50rem);
  --space-3xl: clamp(6.00rem, 5.57rem + 2.17vw, 6.75rem);
}
```

One-up pairs, for space that should grow faster than the rest:

```css
:root {
  --space-s-m:    clamp(1.00rem, 0.76rem + 1.20vw, 1.69rem);
  --space-m-l:    clamp(1.50rem, 1.15rem + 1.74vw, 2.25rem);
  --space-l-xl:   clamp(2.00rem, 1.46rem + 2.72vw, 3.38rem);
  --space-xl-2xl: clamp(3.00rem, 2.17rem + 4.13vw, 4.50rem);
}
```

## Density

references/type.md reads the density off the job. Three names only: dense,
medium, spacious. Section and card padding per density:

```css
/* spacious */
--section-spacing: clamp(5rem, 4rem + 3vi, 8rem);         /* 80 to 128px */
--card-padding:    clamp(2rem, 1.5rem + 1.5vi, 3rem);     /* 32 to  48px */

/* medium */
--section-spacing: clamp(2rem, 1.5rem + 1.5vi, 4rem);     /* 32 to  64px */
--card-padding:    clamp(1rem, 0.75rem + 0.75vi, 1.5rem); /* 16 to  24px */

/* dense */
--section-spacing: clamp(0.5rem, 0.25rem + 0.75vi, 1.5rem); /* 8 to 24px */
```

The source gives no reason for those numbers and ships no dense card padding.

The cheaper alternative, and the one modes/new-page.md uses, treats density as
an operator over the single ladder above: dense shifts every value one step
down, spacious one step up, medium leaves it. Use one or the other on a page,
not both. Spacing is the main signal telling a reader whether they are looking
at a marketing page or a working tool, and the untreated default applies the
same spacing to both.

## Grid

`repeat(auto-fit, minmax(min(280px, 100%), 1fr))` responds continuously instead
of snapping at two or three breakpoints, so there are no intermediate widths
nobody designed. anti-slop-design already ships this exact track, guard and all,
as `repeat(auto-fill, minmax(min(280px, 100%), 1fr))`, and at 300px elsewhere in
the same file. hallmark ships `auto-fit` with a bare `minmax(280px, 1fr)` and no
guard. Taking `auto-fit` onto the guarded track is the whole of our choice, and
`auto-fill` behaves the same way except that it keeps empty tracks.

The `min()` guard is load bearing. Without it the track cannot shrink and the
layout overflows on a narrow screen.

Break the equal-column default at least once: unequal tracks such as
`1.2fr 1fr 0.8fr`, a differing span, or one item spanning two columns. Pick a
primary axis, because centred is what you get when nobody chose.

Auto-fit is for an open-ended list. A fixed set of items takes an explicit
column count that divides it, because auto-fit leaves the last item alone in
its own row at the widths where the count does not come out even.

Grid for page structure, flexbox inside a component. Container queries for
components, media queries for page layout: a component sized off the viewport
breaks the moment somebody drops it in a sidebar.

## When the layout is correct but lifeless

Apply exactly one of these, not all five.

1. Let one element break out of the grid.
2. Make one column width unequal.
3. Move the primary call to action off centre.
4. Delete a card and leave the space empty.
5. Give one section uneven padding.

No source explains the list. Its value is that it turns "this looks flat" into
a bounded set of moves.

## Overflow

A deliberately overflowing element, such as a full-bleed marquee, needs a
global clip or the document scrolls sideways on touch:

```css
html, body { overflow-x: clip; }
```

Use `clip`, not `hidden`. `hidden` creates a scroll container, which breaks
`position: sticky` and `position: fixed` on descendants and can trap focus in
an overflowing input.

## Z-index

```css
:root {
  --z-base:     1;
  --z-raised:   10;
  --z-dropdown: 100;
  --z-sticky:   200;
  --z-modal:    400;
  --z-toast:    500;
  --z-tooltip:  600;
}
```

Never an ad-hoc number. The alternative is `z-index: 9999` and a stacking order
nobody can reason about.
