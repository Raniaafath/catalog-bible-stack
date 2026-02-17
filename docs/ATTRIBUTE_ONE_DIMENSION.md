# One attribute = one semantic dimension

When modeling attributes and mapping keywords/columns, keep **one attribute per semantic dimension**. Do not mix dimensions in the same attribute or mapping line.

## Why

- **"acryl oder stahl duschwanne"** describes **material** (acrylic, enameled steel). "Or" between acrylic and steel is fine for material.
- **"installation = a-poser / a-encastrer"** describes **installation** (surface-mounted vs built-in).

If one row or one mapping mixes material logic with installation logic, the semantics are wrong.

## Clean modeling

| Dimension   | Attribute (e.g. `material`) | Values (examples)                    |
|------------|-----------------------------|-------------------------------------|
| Material   | `material`                  | acrylic, enameled steel, …          |
| Installation | `installation`           | surface-mounted, built-in (multi only if marketplace allows) |

- **Material** → one attribute; values can be multi (e.g. "acrylic or steel") only if that is a single option in your catalog.
- **Installation** → separate attribute; same rule for multi-value.

Keyword mapping (and import column mapping) should map:

- Material keywords (acryl, stahl, …) → **material** only.
- Installation keywords (a poser, encastrer, …) → **installation** only.

The AI mapper is instructed to link each keyword to at most one attribute and to avoid mixing dimensions (e.g. no material keyword → installation attribute).
