# Initial rule decisions

The starting point is the common configuration from the first consumer repositories, plus the compiler style rules selected for build-time enforcement.
Local overrides can remain where an actual requirement needs them.

## Shared defaults for the 22 differences

| Rules | Default | Reason |
| --- | --- | --- |
| CA1002 | Disabled | Concrete collection APIs can be deliberate. |
| CA1024, CA1052 | Disabled | API and utility type shape are design choices. |
| CA1028 | Disabled | Hardware enums need their actual storage widths. |
| CA1030, CA1043, CA1044, CA1054, CA1055, CA1711 | Disabled | Broad API naming and shape heuristics conflict with domain APIs. |
| CA1063, CA1816 | Error | Preserve disposal correctness checks. |
| CA1305 | Disabled | Not every formatting call needs an explicit provider. |
| CA1307 | Error | Keep string comparison choices explicit. |
| CA1505, CA1506 | Disabled | Avoid arbitrary maintainability and coupling limits. |
| CA1814, CA1819 | Disabled | Array representation is an API and performance decision. |
| CA2007 | Error in application code | Library awaits should choose their context behaviour. |
| CA2008 | Disabled | Task scheduling policy needs context. |
| CA2217 | Disabled | Hardware flag enums can represent intentional bit patterns. |
| CA5394 | Disabled | Ordinary random generation is valid outside security-sensitive uses. |

These are proposed initial defaults for review during the first consumer trials.
The security and correctness rules shared by all five repositories remain intact.

CA1014 is also disabled. The shared global configuration makes compilation-level
rules effective where per-file settings did not. Requiring every assembly to
declare CLS compliance adds no value for these C# projects.

## Selected style rules

Prefer var for locals, file-scoped namespaces, imports outside namespaces, braces,
readonly members and collection expressions with exact type matching. Collection
expressions apply where a target type exists, without replacing var declarations.

Keep IDE0058, IDE1006, forced static lambdas/local functions and missing switch
case checks disabled. IDE0045 and IDE0046 are disabled so conditional expressions remain a readability decision. IDE0305 remains enabled for consistent collection construction.

## Local and test builds

Debug relaxations and test exceptions are shared configuration, rather than
repeated suppression lists in each repository. Release application builds retain
XML documentation and unused-code checks. Generated code uses Roslyn's normal
generated-code handling.

IDE2000 rejects consecutive blank lines. One blank line between members remains an agent convention. Undocumented fields may be grouped without separators; XML-documented fields
use one blank line.
