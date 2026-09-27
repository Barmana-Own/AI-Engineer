# Design System Contract

## Table of contents

1. Principles
2. Foundations
3. Color
4. Typography
5. Spacing and sizing
6. Radius and borders
7. Elevation and layering
8. Iconography
9. Motion
10. Density
11. Data visualization
12. Theming
13. Design decisions

## 1. Principles

Build the design system from product needs and repeated interaction patterns. It must be coherent enough for Stage 03 to implement and flexible enough to avoid page-specific styling forks.

Use semantic roles before component-level styling. Define a small, explainable system rather than a huge token inventory with no proven use.

## 2. Foundations

Document:

- visual intent and product personality only to the extent needed for implementation;
- brand constraints inherited from Stage 01 or supplied assets;
- typography system;
- color semantics;
- spacing rhythm;
- size/control-height scale;
- radius strategy;
- border strategy;
- elevation/layering;
- icon family and directional behavior;
- motion principles;
- density modes where needed;
- chart/data-visualization behavior if applicable.

Every material system choice should have a reason or `DSD-*` record.

## 3. Color

Separate primitive palette values from semantic usage.

Define semantic roles such as:

- page/surface/canvas;
- elevated surface;
- text primary/secondary/subtle/inverse;
- border default/strong/subtle;
- interactive primary/secondary;
- focus;
- link;
- success/warning/error/info;
- destructive action;
- selection/highlight;
- disabled states.

For each interactive semantic role, define relevant default, hover, active, disabled, and focus behavior when applicable.

Do not encode status meaning through color alone. Pair with text, iconography, shape, or another perceivable cue.

## 4. Typography

Define role-based typography, not arbitrary per-page font sizes.

At minimum cover:

- display/hero when needed;
- page title;
- section title;
- subsection title;
- body regular;
- body strong;
- label;
- caption/meta;
- code/identifier style when relevant;
- numeric/data style when tabular alignment matters.

For multilingual interfaces, document font fallback and whether numeral width, script shaping, or line-height differs by locale.

## 5. Spacing and sizing

Use a predictable base scale. Define:

- micro spacing;
- inline gaps;
- control internal padding;
- field/group gaps;
- card/panel padding;
- section gaps;
- page gutters;
- control height families;
- icon sizes.

Avoid one-off values unless a specific visual/technical constraint justifies them.

## 6. Radius and borders

Define a small radius scale and explain intended use. Define border width/style semantics and separators. Avoid mixing many unrelated rounding styles.

## 7. Elevation and layering

Define layer purposes, not arbitrary shadow values:

- base content;
- sticky/navigation;
- dropdown/popover;
- modal/drawer;
- toast/notification;
- critical overlay when required.

Stage 03 may map these to z-index values. Stage 02 should specify relative layering and collision behavior.

## 8. Iconography

Define:

- icon family/style;
- default sizes;
- stroke/fill consistency;
- icon-only button labeling obligation;
- decorative icon handling;
- directional icons that mirror in RTL;
- non-directional icons that remain unchanged;
- status icon pairing rules.

Do not mix multiple icon systems without a documented reason.

## 9. Motion

Define motion by purpose:

- feedback;
- spatial continuity;
- reveal/disclosure;
- navigation transition;
- progress/state change.

Specify duration/easing token categories rather than screen-specific animation values. Respect reduced-motion preferences. Do not make completion dependent on decorative animation.

## 10. Density

If the product includes operational data-dense screens, define whether the system supports comfortable/compact density. Density changes must preserve target size and readability requirements.

## 11. Data visualization

When charts exist, define:

- chart role selection guidance;
- semantic color usage;
- categorical palette limits;
- label/legend behavior;
- tooltip behavior;
- no-data/error states;
- table/data alternative when needed for accessibility;
- RTL axis/legend behavior based on data semantics rather than blind mirroring.

## 12. Theming

Do not add dark mode or multiple themes by default. Define them only when required or materially justified. If theming exists, semantic tokens must absorb theme changes instead of components using raw palette values.

## 13. Design decisions

Use `DSD-*` for material decisions that Stage 03 should not casually reinterpret. Include:

- statement;
- rationale;
- affected token/component/layout IDs;
- related Stage 01 constraints;
- reversibility/impact when useful.
