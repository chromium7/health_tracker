# Agent Guidelines for Code Quality

This document provides guidelines for maintaining high-quality code across Python, JavaScript, and CSS. These rules MUST be followed by all AI coding agents and contributors.

---

## Core Principles

All code you write MUST be fully optimized:

- Maximize algorithmic efficiency (time and space complexity)
- Follow proper style conventions for the language in use
- Maximize code reuse (DRY) — if a small, low-overhead library already solves a problem optimally, use it instead of reimplementing
- Write no more code than is absolutely necessary — no speculative abstractions, no technical debt

---

## Python: Code Style and Formatting

- **MUST** use meaningful, descriptive variable and function names
- **MUST** follow PEP 8 style guidelines
- **MUST** use 4 spaces for indentation (never tabs)
- **NEVER** use emoji or unicode that emulates emoji (e.g. ✓, ✗) — exception: tests exercising multibyte character handling
- Use snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants
- Limit line length to 120 characters
- **MUST** avoid redundant comments that are tautological or self-demonstrating
- **MUST** never include comments that leak the original user prompt or are irrelevant to the output code

## Python: Documentation

- **MUST** include docstrings for all public functions, classes, and methods
- **MUST** document parameters, return values, and exceptions raised
- Keep comments up-to-date with code changes
- Include examples in docstrings for complex functions

## Python: Type Hints

- **MUST** use type hints for all function signatures (parameters and return values)
- **NEVER** use `Any` unless absolutely necessary
- Use `T | None` for nullable types

## Python: Error Handling

- **NEVER** silently swallow exceptions without logging
- **MUST** never use bare `except:` clauses
- **MUST** catch specific exceptions rather than broad types
- **MUST** use context managers (`with` statements) for resource cleanup
- Provide meaningful error messages

## Python: Function Design

- **MUST** keep functions focused on a single responsibility
- **NEVER** use mutable objects (lists, dicts) as default argument values
- Limit function parameters to 5 or fewer
- Return early to reduce nesting

## Python: Class Design

- **MUST** keep classes focused on a single responsibility
- **MUST** keep `__init__` simple — no complex logic
- Use dataclasses for simple data containers
- Prefer composition over inheritance
- Only add class methods when necessary
- Use `@property` for computed attributes

## Python: Testing

- **MUST** write unit tests for all new functions and classes
- **MUST** mock external dependencies (APIs, databases, file systems)
- **NEVER** run generated tests without first saving them as their own discrete file
- **NEVER** delete files created as part of testing

## Python: Best Practices

- **MUST** use context managers for file/resource management
- Use list comprehensions and generator expressions where appropriate
- Use `enumerate()` instead of manual counter variables

## Python: Django Forms

- **MUST** put single-field validation in `clean_<field>` methods. Reserve `clean()` for cross-field validation that depends on more than one field.
- **MUST NOT** use `assert` statements in `save()` (or other post-validation paths) to re-check form data — by the time `save()` runs the data is already validated. Validate at the boundary (`clean_*` / `clean`), not after.

## Python: Django Views, Forms, and Utils Layering

Each app's Python code MUST be split across these files by responsibility. Keep `views.py` thin; promote anything else to `forms.py` or `utils.py`.

- **`views.py`** — request/response controllers only. A view reads request input, instantiates a form, dispatches to form methods or utils, and assembles the template context. Views MUST NOT contain business logic, ORM aggregations, CSV writers, or other data shaping.
- **`forms.py`** — owns validation AND the data-generation logic for the page the form backs. When a filter form drives a report, dashboard, or computed result, expose a method like `generate_data()` (and any sibling actions like `export_csv()`) so the view can simply call `form.generate_data()`. The form is the single entry point for "given these inputs, produce the answer."
- **`utils.py`** — reusable helpers: queryset builders, formatters, CSV writers, dataclasses, constants, URL builders, page-metadata tables. Helpers MUST live here, not as private functions inside `views.py`. Form methods may delegate to utils.

Per-app file layout: `views.py`, `forms.py`, `urls.py`, `utils.py`, `models.py`, `admin.py`. When a helper grows beyond a single function, give it a home in `utils.py` from the start — do not let `views.py` accumulate `_helper` functions.

## Python: Django Apps

- **MUST** use `snake_case` for Django app module names (e.g., `stock_takes`, not `stocktakes`). The auto-derived `app_label` inherits this and is used for admin URL reverses (`admin:<app_label>_<model>_changelist`) and database table prefixes.
- Keep `__init__.py` empty. Do not add `apps.py` unless overriding the default `AppConfig`.
- Register new apps in `INSTALLED_APPS` using their fully qualified module path.

## Python: Django Admin

When a feature needs both a list view and a custom multi-step add page (e.g., "Add Order", "Add Stock Take"):

- **MUST** use Django's standard admin changelist as the list page — it provides search, filtering, and pagination for free. Configure `list_display`, `list_filter`, `search_fields` on the `ModelAdmin`.
- **MUST** override `add_view` on the `ModelAdmin` to redirect to the custom add view via `HttpResponseRedirect(reverse("<custom_url_name>"))`.
- Override the standard changelist's "Add" button via `templates/admin/<app>/change_list.html` extending `admin/change_list.html` and replacing `{% block object-tools-items %}`.
- Sidebar entries point to the **changelist** URL (`admin:<app_label>_<model>_changelist`), not the custom add view.

## Python: Database Efficiency

- **MUST** use `bulk_create` (or `bulk_update`) when persisting multiple model instances of the same type. Never loop and call `Model.objects.create()` per row when one `bulk_create` will do.
- **MUST** use `select_related` / `prefetch_related` to avoid N+1 queries when accessing related objects in loops or templates.

## Python: Tools

- **MUST** use Ruff for formatting and linting (`ruff format` and `ruff check`)

---

## Templates: Admin Page Layouts

- Custom add pages with line-item formsets MUST reuse existing CSS classes defined in the project's admin stylesheet. Do not invent new grid layouts for the same job — extend the existing block with a new modifier instead.
- Dynamic add/remove rows MUST follow a single canonical pattern across the project: a hidden `<template>` with `__prefix__` placeholders for the empty form, an "+ Add" button that clones the template and bumps `TOTAL_FORMS`, and a delete button that removes the row and reindexes remaining rows.
- The header form (parent fields) and the line-item formset MUST be submitted under the same `<form>`. Use a distinct `prefix` for the formset (e.g., `prefix="items"`) and pass `data=request.POST or None` to both.

---

## Frontend: Mobile-only PWA

This product targets a single form factor: a smartphone browser, with installation as a Progressive Web App (PWA). Treat every screen as a portrait phone view.

- **MUST** design and style for a 320 - 430 px viewport. There are no desktop, tablet, or wide-screen layouts. Do not add media queries for larger breakpoints.
- **MUST** keep the bottom navigation visible on every authenticated screen and use the same five-slot pattern: Today, Meds, Log (centre FAB), Water, Docs.
- **MUST** render the manifest at `/manifest.webmanifest` and the service worker at `/sw.js`. Both are served by `TemplateView` from project `urls.py`; the registration tag and `<link rel="manifest">` live in `base.html`.
- **MUST** keep `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">` and the `theme-color` / `apple-mobile-web-app-*` meta tags in `base.html` intact. They are required for PWA installability.
- **MUST** ship icons at `static_files/icons/icon-192.png` and `icon-512.png`. Both paths are referenced from the manifest.
- Touch targets are at least 44 x 44 px. Forms use large, readable inputs.
- Service-worker caching strategy is network-first with a small offline shell. Do not add caching for authenticated responses without considering session leakage.

## CSS: BEM Convention

This project uses **BEM (Block, Element, Modifier)** for all CSS class naming, in **plain CSS only**. **Do not use SCSS, Sass, LESS, or utility-first frameworks (Tailwind, etc.)** and avoid ad-hoc class names — every class must fit the BEM grammar so styles remain greppable and ownership stays clear.

### Naming grammar

- **Block** — a standalone component: `.card`, `.order-line`, `.product-search`
- **Element** — a part of a block, joined by `__`: `.card__title`, `.order-line__qty`, `.product-search__icon`
- **Modifier** — a variant or state, joined by `--`: `.card--featured`, `.button--primary`, `.order-line__qty--invalid`

### Rules

- **MUST** use lowercase kebab-case for the block name. Multi-word blocks use a single hyphen (`.product-search`), not nested underscores.
- **MUST** use `__` (double underscore) to join element to block and `--` (double dash) to join modifier to block or element.
- **MUST NOT** chain elements (`.block__el1__el2`). Nesting is conceptual, not syntactic — flatten to `.block__el2` and rely on the DOM for hierarchy.
- **MUST NOT** use modifiers as standalone classes (`<div class="--primary">`); always pair with the block/element they modify (`<div class="button button--primary">`).
- **MUST NOT** style by tag or id (`div.card`, `#sidebar`). Style by class only — this keeps specificity flat (0,1,0) across the codebase.
- **MUST NOT** use `!important` to override BEM rules. If you need an override, introduce a modifier.
- **MUST NOT** write nested or descendant selectors (`.card .title`, `.card > .card__title`). Each rule targets exactly one BEM class so specificity stays at 0,1,0.

### Modifier vs. new block

If a variant only changes appearance/state of an existing component, it's a modifier (`.card--compact`). If it introduces new structure or semantically different elements, it's a new block. Keep modifiers cosmetic; promote to a new block when responsibilities diverge.

### CSS structure

- **MUST** write a separate rule per BEM class (block, each element, each modifier). Example:

  ```css
  .card {
    padding: 1rem;
  }

  .card__title {
    font-weight: 600;
  }

  .card--featured {
    border: 2px solid gold;
  }
  ```

- **MUST** define shared design tokens (colours, spacing, typography) as CSS custom properties on `:root` in a single tokens file, and reference them with `var(--token)` from each rule. Never hard-code the same colour or spacing value in multiple places.
- Group rules for one block contiguously inside the stylesheet so block code is easy to locate.

### JavaScript hooks

- **MUST** prefix classes used only for JS targeting with `js-` (e.g., `js-toggle-menu`). JS hooks are never styled, and BEM classes are never targeted from JS. This keeps the visual and behavioural layers independently refactorable.

---

## JavaScript: Code Style and Formatting

- **MUST** use meaningful, descriptive variable and function names
- **MUST** use 2 spaces for indentation
- Use camelCase for variables/functions, PascalCase for classes/components, UPPER_CASE for constants
- Limit line length to 120 characters
- **MUST** avoid redundant or self-demonstrating comments
- **MUST** use `const` by default, `let` only when reassignment is required — never `var`
- **MUST** use strict equality (`===`) over loose equality (`==`)
- Prefer arrow functions for callbacks and anonymous functions
- Use destructuring for objects and arrays where it improves clarity

## JavaScript: Documentation

- **MUST** include JSDoc comments for all public functions, classes, and exported modules
- **MUST** document parameters (`@param`), return values (`@returns`), and thrown errors (`@throws`)
- Include a brief description at the top of each module explaining its responsibility
- Keep comments up-to-date with code changes

## JavaScript: Error Handling

- **NEVER** silently swallow exceptions without logging
- **MUST** always handle Promise rejections — use `try/catch` with `async/await` or `.catch()` on promise chains
- Provide meaningful error messages

## JavaScript: Function and Module Design

- **MUST** keep functions focused on a single responsibility
- Return early to reduce nesting
- Keep modules focused — one concern per file

---

**Remember:** Prioritize clarity and maintainability over cleverness. The codebase must remain clean and navigable as it grows.
