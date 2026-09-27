# Design Token Contract

## Table of contents

1. Goals
2. Layers
3. Required top-level structure
4. Naming
5. Required semantic groups
6. References and values
7. Framework neutrality
8. Anti-patterns

## 1. Goals

`design/tokens.json` is the machine-readable source of truth for design-system foundations that Stage 03 can transform into implementation-specific variables or configuration.

## 2. Layers

Use these layers:

1. `primitive`: raw reusable scales/palette values.
2. `semantic`: role-based tokens consumed by the interface.
3. `component`: optional aliases for repeated component-specific semantics. Keep this small.

Components should prefer semantic tokens. Raw primitives should not be used directly in implementation except inside token construction or rare documented cases.

## 3. Required top-level structure

```json
{
  "schema_version": "1.0",
  "meta": {
    "name": "Project design tokens",
    "direction_support": ["ltr", "rtl"]
  },
  "primitive": {},
  "semantic": {
    "color": {},
    "typography": {},
    "space": {},
    "radius": {},
    "motion": {},
    "breakpoint": {}
  },
  "component": {}
}
```

`component` may be empty. Do not omit required semantic groups merely because the project is visually simple.

## 4. Naming

Use lowercase dot-path-compatible keys expressed as nested JSON objects. Prefer role names:

- `semantic.color.text.primary`
- `semantic.color.surface.canvas`
- `semantic.color.status.error`
- `semantic.space.page.gutter`

Avoid:

- `blue500Button`;
- `dashboardCardGap`;
- `homepageTitleSize`;
- route names;
- feature names unless they represent a true domain semantic shared across the product.

## 5. Required semantic groups

Define at least:

- `semantic.color`
- `semantic.typography`
- `semantic.space`
- `semantic.radius`
- `semantic.motion`
- `semantic.breakpoint`

Recommended color subgroups:

- text;
- surface;
- border;
- action;
- status;
- focus.

Recommended typography roles:

- page_title;
- section_title;
- body;
- label;
- caption.

## 6. References and values

Primitive values may be literal design values. Semantic values should preferably reference primitives using a clear project convention such as `{primitive.color.neutral.900}`.

Do not create circular references. Do not reference missing primitive paths.

The Stage 02 validator checks structure but does not fully resolve token graphs; Stage 03 should include token-resolution tests when it generates implementation tokens.

## 7. Framework neutrality

Do not store:

- Tailwind class names;
- CSS selectors;
- CSS-in-JS object syntax;
- React component names as token keys;
- platform-specific variable syntax as the only source of truth.

Stage 03 may generate those outputs from this file.

## 8. Anti-patterns

Do not:

- copy an arbitrary large palette with no semantic roles;
- mix pixels, rems, and framework spacing names without a documented convention;
- encode page-specific values as global tokens;
- create dark-theme values when dark theme is not in scope;
- use color tokens as the only meaning for status;
- put behavior or product requirements inside the token file.
