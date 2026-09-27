# RTL and Localization Contract

## Table of contents

1. Direction model
2. Mixed-direction content
3. Numbers and identifiers
4. Dates and time
5. Currency and units
6. Icons and mirroring
7. Navigation and progress
8. Tables and charts
9. Text expansion and truncation
10. Locale switching
11. Validation checklist

## 1. Direction model

Define interface direction per locale. Do not assume every locale uses the same direction. Direction should be a system-level property that components consume rather than a per-page patch.

## 2. Mixed-direction content

Explicitly handle LTR fragments inside RTL interfaces and RTL fragments inside LTR interfaces. Common examples:

- URLs;
- email addresses;
- code;
- version strings;
- tracking numbers;
- account/IBAN-like identifiers;
- Latin product names;
- mixed Persian/English labels.

Preserve logical character order and avoid punctuation jumping caused by uncontrolled bidi behavior.

## 3. Numbers and identifiers

Decide separately for:

- human-readable localized numbers;
- machine identifiers;
- phone numbers;
- financial/account identifiers;
- OTP/PIN-like sequences;
- percentages/decimals.

Do not localize digits in a way that makes a machine identifier ambiguous or copy/paste-incompatible.

## 4. Dates and time

Define:

- display calendar(s);
- input calendar expectation;
- Gregorian/Jalali/Hijri coexistence when relevant;
- timezone behavior;
- 12/24-hour format;
- absolute versus relative dates;
- unambiguous format for audit/transaction history.

Do not invent calendar requirements; inherit or mark assumptions.

## 5. Currency and units

Define currency code/symbol placement, digit grouping, decimal precision, and unit placement. For financial or regulated contexts, prefer unambiguous display over decorative abbreviation.

## 6. Icons and mirroring

Usually mirror icons that communicate spatial direction in the interface, such as next/back chevrons when semantics follow reading direction.

Usually do not mirror:

- logos;
- media play symbols where platform convention says otherwise;
- phone/handset symbols;
- checkmarks;
- clocks;
- download/upload symbols;
- charts whose axes reflect data semantics;
- maps or real-world directional imagery.

Document exceptions.

## 7. Navigation and progress

Define reading/progression direction for:

- breadcrumbs;
- steppers;
- timelines;
- carousels;
- pagination;
- tab overflow;
- back/forward history.

Progression may follow language direction or domain chronology. Choose intentionally.

## 8. Tables and charts

Define:

- label column alignment;
- numeric alignment;
- action column placement;
- column order strategy;
- horizontal scroll origin;
- chart axes and legends;
- tooltip text direction.

Do not blindly reverse all data columns when domain conventions require a fixed order.

## 9. Text expansion and truncation

Design for translated text expansion and script-specific line height. Avoid fixed-height containers for variable text. Define truncation only when users can still access the full important value.

## 10. Locale switching

Only define a language switcher if multilingual behavior is in scope. Specify persistence and whether switching preserves current task context. Do not discard unsaved work on locale change without warning.

## 11. Validation checklist

Verify at minimum:

- mixed emails/URLs/IDs render correctly;
- form labels and validation text align logically;
- numeric data stays readable;
- directional icons behave correctly;
- tables do not become semantically reversed by blind mirroring;
- long translated text reflows;
- modal and drawer origin is intentional;
- dates/currency remain unambiguous.
