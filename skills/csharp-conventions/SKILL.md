---
name: csharp-conventions
description: Apply Kevin Watkins' C# conventions when writing, changing or reviewing C# code and tests.
---

# C# conventions

- Use `var` for locals. Prefer explicit construction types over replacing `var` with a declared type.
- Use explicit string comparers for ordering and string-keyed collections. Prefer ordinal rules for identifiers; preserve intentional case and culture choices.
- Leave one blank line between members, except undocumented fields may be grouped without blank lines. Separate XML-documented fields with one blank line.
- Do not use consecutive blank lines.
- After constructor initializers or generic constraints, put an expression body on the next line after `=>`. Otherwise, choose the more readable layout.
- Hard wrap C# and Markdown at 180 characters.
- Keep comments short and explain why.
- Prefer internal visibility, readonly fields and immutable collection interfaces where appropriate.
- Use camelCase for private fields without an underscore prefix.
- Keep one type per file, named after the type. Generic variants may share a file. Put nested types last.
- Put braces on separate lines, including empty blocks. Put XML summary tags on separate lines from their text.
- Prefer readable null, type and property patterns over repeated checks, member access and casts in conditions.

## Projects

- Use ProjectReference or PackageReference, never assembly Reference. Manage package versions centrally in Directory.Packages.props.

## Tests

- Use MrKWatkins.Assertions. Underscores are allowed in test method names, but not application identifiers.
- For example, use `GetInt32`, `GetInt32_Span` for an overload and `GetInt32_Span_InvalidRange` for an exceptional case.
- Keep mutable state local to each test. Avoid shared mutable fixtures and caches.
- Match test names to the method being tested. Append parameter types for overloads, then exceptional conditions, separated by underscores. Do not add a happy-path suffix.

## Conditional expressions

- Prefer a single ternary for a straightforward return. Do not introduce nested ternaries.
- Put the successful result first and an exception second. Invert the condition when necessary.
- Put `?` and `:` on indented new lines.
- Preserve grouped validation guards, including the final guard before a successful return.
- Keep multi-branch parsing, type dispatch and failure branches with assignments as ordinary statements.

## Asynchronous code

- Prefer `await using` for asynchronously disposable resources in async code.
- Use `ConfigureAwait(false)` for awaits and asynchronous disposal in application and library code, unless a continuation needs its context, such as UI updates.

## Return-value annotations

- Use `[Pure]` only when an operation does not mutate inputs, its receiver or other externally visible state. Modifying locally owned objects is allowed.
- Internal caching without externally visible effects is allowed. Reading from disk may qualify; consuming an input stream changes caller-owned state.
- Use `[MustUseReturnValue]` when an operation mutates caller-owned state or has other side effects and its result must be used.
- Do not apply either attribute to `void`, non-generic `Task` or non-generic `ValueTask` methods.
- For `Task<T>` and `ValueTask<T>`, the annotation concerns the result `T`, not whether the operation must be awaited.
