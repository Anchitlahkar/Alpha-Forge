# Product

## Register

product

## Users

One person: a software engineer who follows AI research, quantum computing,
semiconductors, startups and investing. The brief sits open on a second monitor
beside an editor and gets glanced at repeatedly through the day rather than read
once in a sitting. It must survive peripheral vision: the top story has to be
readable at arm's length, and a glance should answer "is there anything new worth
stopping for?" without a full read.

## Product Purpose

A pipeline fetches ~14 feeds, has Gemini score each article for signal (1-10) and
personal relevance, ranks them, and publishes a static page to GitHub Pages once a
day. Success is the owner actually reading it. A brief that is technically correct
and visually inert gets ignored, which makes the whole pipeline pointless.

## Brand Personality

Terse, mechanical, legible-at-distance. The physical object is a departure board
or a wire-service printout, not a magazine and not a SaaS dashboard. It reports;
it does not sell. Voice is written to one person who already knows the context.

## Anti-references

- **SaaS dashboard** (what it was): card grids, badge pills, indigo/violet accents.
- **Crypto/AI terminal**: neon on black, glows, monospace-everything, fake live
  indicators. The first-order reflex for this subject matter; reject it.
- **Editorial-typographic**: display serif italic headline, small tracked mono
  labels, ruled three-column restraint. The second-order reflex, now saturated.
- **Bloomberg terminal**: maximum density with no editing. The pipeline's whole
  job is to cut 14 feeds down to five things; the design must show that editing.
- **Substack/Medium**: centred serif column, generous whitespace. Wrong for a
  glanceable surface.

## Design Principles

1. **Rank must be visible without reading.** The pipeline computes a ranking; the
   layout has to spend its scale on it. Five equal boxes throws away the work.
2. **Show the editing.** 14 feeds became 5 items. Say so, and show what was cut,
   never by repeating what was kept.
3. **Real material over ornament.** Merged source counts, relevance divergence,
   feed health, staleness. The page has no imagery and must not fake any.
4. **Honest when empty.** An empty state that names what will fill it, and a stale
   day that admits it is stale, beat an invented full page.
5. **Glanceable first, readable second.** Optimise the top 400px for a passing
   look; depth is for when he stops.

## Accessibility & Inclusion

WCAG AA: body text >=4.5:1, large text >=3:1, verified rather than assumed. Rank is
never carried by colour alone (it carries a number too). Every interactive element
has a visible `:focus-visible` state. `prefers-reduced-motion` is honoured.
