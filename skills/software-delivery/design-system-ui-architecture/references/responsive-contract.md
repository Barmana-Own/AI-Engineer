# Responsive and Adaptive UI Contract

## Table of contents

1. Principles
2. Breakpoints
3. Content priority
4. Navigation
5. Tables and dense data
6. Forms
7. Overlays
8. Fixed and sticky UI
9. Typography and spacing
10. Device capabilities
11. Validation checklist

## 1. Principles

Design from task priority and content behavior, not from named device models. Mobile is a distinct interaction context, not a scaled desktop screenshot.

## 2. Breakpoints

Define breakpoints when a layout or interaction behavior must change. Record:

- minimum/maximum range;
- behavior change;
- affected layouts/components;
- rationale.

Avoid excessive breakpoints that only adjust cosmetic pixel values.

## 3. Content priority

For each important screen decide:

- what must remain immediately visible;
- what may move below the fold;
- what may collapse into disclosure;
- what may move to a secondary screen/drawer;
- what must never be hidden because it affects safety, status, or task completion.

## 4. Navigation

Define transformations such as:

- persistent sidebar to drawer;
- horizontal tab overflow behavior;
- utility actions to overflow menu;
- breadcrumb simplification;
- back-navigation behavior.

Keep important actions discoverable after transformation.

## 5. Tables and dense data

Choose per use case:

- horizontal scroll with anchored key column;
- responsive priority columns;
- row-to-card transformation;
- master-detail split to separate screens;
- compact list with drill-in;
- explicit desktop-only operational surface only when product constraints justify it.

Never silently remove critical columns on narrow screens.

## 6. Forms

Define:

- multi-column to single-column transformation;
- field ordering;
- sticky action bar behavior;
- keyboard/input-mode expectations at conceptual level;
- long helper/error text wrapping;
- stepper transformation;
- date/time/file input considerations.

## 7. Overlays

A desktop dialog may become a bottom sheet, drawer, or full-screen task on smaller viewports. Define the transformation and preserve focus/dismissal semantics.

## 8. Fixed and sticky UI

Evaluate viewport obstruction from:

- sticky headers;
- bottom action bars;
- virtual keyboards;
- browser chrome;
- safe-area insets.

Avoid trapping essential content behind fixed UI.

## 9. Typography and spacing

Use fluid or breakpoint-based adjustments only when they preserve hierarchy and readability. Do not reduce body text or touch targets simply to fit more content.

## 10. Device capabilities

Use capabilities such as camera, file capture, hover, fine pointer, or geolocation only when product requirements justify them. Document fallback behavior when capability is unavailable.

## 11. Validation checklist

For each high-impact screen verify:

- no unintended horizontal page overflow;
- primary task remains possible;
- long translated text does not break layout;
- actions remain reachable with virtual keyboard open where relevant;
- dialogs/menus fit viewport and can scroll;
- tables have an intentional narrow-screen strategy;
- touch targets remain usable;
- sticky regions do not obscure focus or error messages.
