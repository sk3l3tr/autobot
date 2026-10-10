# UX Style Guide

## Visual Tokens
- Background: `#02030a`
- Surface: `#0b0618`
- Surface alt: `#140a24`
- Text: `#f5f5f7`
- Muted text: `#b0b3c7`
- Primary accent: `#ff0080`
- Secondary accent: `#00f6ff`
- Accent alt: `#7a00ff`
- Error / destructive cue: native red is used in some controls such as the close button
- Border: `#26253a` plus frequent dashed white borders in list and card treatments

## Layout / Spacing
- Base spacing unit: 4px grid.
- Panel gap: commonly `1rem` to `1.5rem`.
- Panel padding: small cards and list items often use `5px`; layout containers use `1rem`-scale spacing.
- Header padding: fixed header/footer wrappers use approximately `1rem` horizontal padding and `1.5rem` top/bottom offsets.

## Borders / Depth
- Border style: mostly crisp dashed outlines, typically `1px dashed white` or `2px dashed var(--text)`.
- Shadow style: minimal to none; the current visual system relies more on neon color contrast than on soft depth.
- Effects policy: avoid visual noise; prefer crisp, readable UI.

## Typography
- Font family: custom `Doto` for headings, buttons, and links; sans-serif fallback elsewhere.
- Heading style: `h1` uses large display sizing around `3rem` with the primary accent color.
- Body style: default browser body sizing with high-contrast text on dark backgrounds.
- Label style: uppercase-like arcade/pixel tone via iconography, monospaced-feeling labels, and compact control text.

## Components / Interaction Rules
- Buttons: icon-heavy controls with transparent backgrounds are common; hover states often switch to the cyan accent.
- Inputs: favor readability over decoration; settings and schedule forms are plain and direct rather than heavily skinned.
- Data views: list items and schedule cards use centered layouts, narrow widths, and explicit action affordances for play, edit, and delete flows.
- Feedback states: loading uses a rotating pixel-style loader; operational feedback is also surfaced through logs and native alert/error handling patterns.

## Motion / Performance
- Keep animations minimal and purposeful.
- Prefer readability and responsiveness over decoration.
- Avoid expensive full-screen effects in frequent update paths.
