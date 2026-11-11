# CSharpConventions

- This repository builds MrKWatkins.CSharpConventions, a build-only NuGet package.
- Keep shared configuration small. Prefer conventions over configuration switches.
- Put all validation under tests and use Pytest with uv.
- Validate the packed package through a local feed and clean consumer restores.
- Keep library, NUnit, Debug and Release behaviour covered.
- Consumer dependencies remain in their own projects.
- Do not push. The user reviews and pushes.
- Hard wrap Markdown and C# at 180 characters.
- Keep comments short and explain why.
