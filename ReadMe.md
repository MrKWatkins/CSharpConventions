# CSharpConventions

Shared C# compiler, testing and packaging conventions for my projects.

The NuGet package is `MrKWatkins.CSharpConventions`. It contains MSBuild settings, analyzer configuration and a shared package icon, with no runtime assembly.

## Use

Add the reference once in `Directory.Build.props` with `PrivateAssets="all"`. Keep its version in `Directory.Packages.props` when using central package management.

```xml
<PackageReference Include="MrKWatkins.CSharpConventions" PrivateAssets="all" />
```

Projects are non-packable by default. Add `<IsPackable>true</IsPackable>` to each project you publish. Packaging includes the shared icon and the nearest ancestor `ReadMe.md`,
conventionally at the repository root. The default licence is `GPL-3.0-only`; set `PackageLicenseExpression` to override it.

Target frameworks, language versions, package references, repository URLs and project descriptions stay in the consumer repository. Source Link comes from the .NET SDK. The package
enables repository metadata publication. The copyright notice is `Copyright © Kevin Watkins`, without a year.

## Rules

Nullable reference types, implicit usings, warnings as errors and compiler style checks are enabled by default. Local project properties and `.editorconfig` settings can override
the defaults.

Naming enforcement is disabled, except CA1707 rejects underscores in application API identifiers, including private and internal members. Test projects allow underscores. This does
not enforce local variable names.

Tests are identified by `IsTestProject`, defaulting to true for project names ending in `Tests`. NUnit global usings are selected from the project's package references.
NUnit runners, MTP support and the standard `.Tests` friend assembly are configured automatically. Additional friend assemblies stay in the consuming project.

Test projects permit missing XML comments, instance methods without instance data and awaits without `ConfigureAwait`. Debug additionally suppresses missing XML comments, unused
locals, unused private members and unused parameters. Release retains these checks for application code. Nullable analysis stays enabled.

See [rule decisions](https://github.com/MrKWatkins/CSharpConventions/blob/main/RULES.md) for the initial rationalisation of existing settings.

## Development

```sh
uv sync --locked
uv run pytest
```

The tests pack the package, restore consumers from a temporary local NuGet feed, and check both compilation and package contents. No publication is required. Tests require the
.NET 10 SDK. NUnit smoke tests also use nuget.org or packages already available in the NuGet cache.

## Licence

GPL-3.0-only.
