from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "MrKWatkins.CSharpConventions"
VERSION = os.environ.get("CONVENTIONS_VERSION") or ElementTree.parse(
    ROOT / "src" / PACKAGE / f"{PACKAGE}.csproj"
).findtext("./PropertyGroup/Version")


def run(*args, cwd, env=None):
    return subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, timeout=180, check=False)


def succeeds(result):
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


@pytest.fixture(scope="session")
def feed(tmp_path_factory):
    if supplied := os.environ.get("CONVENTIONS_PACKAGE"):
        package = Path(supplied).resolve(strict=True)
        assert package.name == f"{PACKAGE}.{VERSION}.nupkg"
        return package.parent
    directory = tmp_path_factory.mktemp("feed")
    succeeds(
        run(
            "dotnet",
            "pack",
            "src/CSharpConventions.slnx",
            "-c",
            "Release",
            "-o",
            str(directory),
            f"-p:PackageVersion={VERSION}",
            cwd=ROOT,
        )
    )
    return directory


@pytest.fixture(scope="session")
def environment(tmp_path_factory):
    env = os.environ.copy()
    env["NUGET_PACKAGES"] = str(tmp_path_factory.mktemp("packages"))
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    return env


@pytest.fixture
def consumer(tmp_path, feed, environment):
    def create(source, *, name="Example", properties="", references="", editorconfig="", readme=True):
        if readme:
            (tmp_path / "ReadMe.md").write_text("# Consumer\n")
        config = f'''<configuration><packageSources><clear />
<add key="local" value="{feed}" />
<add key="nuget" value="https://api.nuget.org/v3/index.json" />
</packageSources></configuration>'''
        (tmp_path / "NuGet.Config").write_text(config)
        versions = ElementTree.parse(ROOT / "tests/Directory.Packages.props")
        ElementTree.SubElement(versions.getroot().find("ItemGroup"), "PackageVersion", Include=PACKAGE, Version=VERSION)
        versions.write(tmp_path / "Directory.Packages.props", encoding="unicode")
        (tmp_path / "Directory.Build.props").write_text(f'''<Project>
<PropertyGroup><TargetFramework>net10.0</TargetFramework></PropertyGroup>
<ItemGroup><PackageReference Include="{PACKAGE}" PrivateAssets="all" /></ItemGroup>
</Project>''')
        directory = tmp_path / "src" / name
        directory.mkdir(parents=True, exist_ok=True)
        project = directory / f"{name}.csproj"
        project.write_text(f"""<Project Sdk="Microsoft.NET.Sdk">
<PropertyGroup>{properties}</PropertyGroup><ItemGroup>{references}</ItemGroup></Project>""")
        (directory / "Example.cs").write_text(source)
        if editorconfig:
            (directory / ".editorconfig").write_text("[*.cs]\n" + editorconfig)
        succeeds(run("dotnet", "restore", str(project), cwd=tmp_path, env=environment))
        return project

    return create


def build(project, environment, configuration="Release"):
    return run(
        "dotnet", "build", str(project), "--no-restore", "-c", configuration, cwd=project.parent, env=environment
    )


CLEAN = """namespace Example;

internal static class Example
{
    internal static int Value() => 42;
}
"""


def test_package_contains_only_build_assets(feed):
    with ZipFile(feed / f"{PACKAGE}.{VERSION}.nupkg") as package:
        names = package.namelist()
        assert f"build/{PACKAGE}.props" in names
        assert f"build/{PACKAGE}.targets" in names
        assert f"config/{PACKAGE}.globalconfig" in names
        assert "assets/Icon.png" in names
        assert "ReadMe.md" in names
        assert not any(name.startswith(("lib/", "ref/")) for name in names)
        metadata = ElementTree.fromstring(package.read(f"{PACKAGE}.nuspec"))
        ns = {"n": metadata.tag.split("}")[0].removeprefix("{")}
        assert metadata.find("n:metadata/n:version", ns).text == VERSION
        assert metadata.find("n:metadata/n:license", ns).text == "GPL-3.0-only"
        assert metadata.find("n:metadata/n:dependencies", ns) is None


def test_clean_consumer_builds_and_defaults_are_inherited(consumer, environment):
    project = consumer(CLEAN)
    succeeds(build(project, environment))
    props = json.loads(
        succeeds(
            run(
                "dotnet",
                "msbuild",
                str(project),
                "-getProperty:Nullable,ImplicitUsings,TreatWarningsAsErrors,EnforceCodeStyleInBuild,IsPackable",
                cwd=project.parent,
                env=environment,
            )
        )
    )["Properties"]
    assert props == {
        "Nullable": "enable",
        "ImplicitUsings": "enable",
        "TreatWarningsAsErrors": "true",
        "EnforceCodeStyleInBuild": "true",
        "IsPackable": "false",
    }


@pytest.mark.parametrize(
    ("statement", "diagnostic"),
    [
        ("int value = 42; return value;", "IDE0007"),
        ("var value = 42;", "CS0219"),
        ("int value;", "CS0168"),
    ],
)
def test_release_rejects_invalid_code(consumer, environment, statement, diagnostic):
    source = "namespace Example; internal static class Example { internal static int Read() { " + statement + " } }"
    if "return" not in statement:
        source = source.replace(statement, statement + " return 42;")
    project = consumer(source)
    result = build(project, environment)
    assert result.returncode != 0
    assert diagnostic in result.stdout


@pytest.mark.parametrize("statement", ["var value = 42;", "int value;"])
def test_debug_allows_unused_locals(consumer, environment, statement):
    project = consumer(
        "namespace Example; internal static class Example { internal static int Read() { "
        + statement
        + " return 42; } }"
    )
    succeeds(build(project, environment, "Debug"))
    assert build(project, environment).returncode != 0


def test_xml_comments_are_required_only_for_release_application_code(consumer, environment):
    project = consumer("namespace Example; public static class Example { public static int Value() => 42; }")
    succeeds(build(project, environment, "Debug"))
    result = build(project, environment)
    assert result.returncode != 0
    assert "CS1591" in result.stdout


@pytest.mark.parametrize("name", ["Example.Tests", "Example.ParsingTests"])
def test_test_profile_allows_underscores_and_missing_documentation(consumer, environment, name):
    project = consumer(
        f"namespace {name}; public static class Example {{ public static void Test_Name() {{ }} public static void Main() {{ }} }}",
        name=name,
    )
    succeeds(build(project, environment))


def test_application_code_rejects_underscores(consumer, environment):
    project = consumer("namespace Example; internal static class Example { internal static int Read_Value() => 42; }")
    result = build(project, environment)
    assert result.returncode != 0
    assert "CA1707" in result.stdout


def test_naming_and_unused_return_value_rules_remain_disabled(consumer, environment):
    project = consumer("""namespace Example;
internal static class Example
{
    private static readonly string PC = string.Empty;
    internal static string Read() => PC;
    internal static void Ignore() { Read(); Read(); }
}
""")
    succeeds(build(project, environment))


def test_var_locals_and_collection_expressions_can_coexist(consumer, environment):
    project = consumer("""namespace Example;
internal static class Example
{
    internal static int[] Values()
    {
        var values = new[] { 1, 2 };
        var empty = Array.Empty<int>();
        var list = new List<int>();
        list.Add(values.Length + empty.Length);
        return [.. values, .. list];
    }
}
""")
    succeeds(build(project, environment))


def test_fluent_collection_construction_is_rejected(consumer, environment):
    project = consumer("""namespace Example;
internal static class Example
{
    internal static int[] Append(int[] values) => values.Append(42).ToArray();
}
""")
    result = build(project, environment)
    assert result.returncode != 0
    assert "IDE0305" in result.stdout


def test_local_editorconfig_can_override_a_rule(consumer, environment):
    project = consumer(
        "namespace Example; internal static class Example { internal static int Read_Value() => 42; }",
        editorconfig="dotnet_diagnostic.CA1707.severity = none\n",
    )
    succeeds(build(project, environment))


@pytest.mark.parametrize("licence", [None, "MIT"])
def test_explicit_packaging_includes_shared_assets_without_leaking_conventions(consumer, environment, licence):
    properties = "<IsPackable>true</IsPackable><Description>A consumer.</Description>"
    if licence:
        properties += f"<PackageLicenseExpression>{licence}</PackageLicenseExpression>"
    project = consumer(CLEAN, properties=properties)
    directory = project.parent / "packages"
    succeeds(
        run("dotnet", "pack", str(project), "-c", "Release", "-o", str(directory), cwd=project.parent, env=environment)
    )
    with ZipFile(next(directory.glob("*.nupkg"))) as package:
        assert package.read("ReadMe.md") == b"# Consumer\n"
        assert package.read("Icon.png") == (ROOT / "src" / PACKAGE / "assets/Icon.png").read_bytes()
        manifest = package.read("Example.nuspec").decode()
        assert f'type="expression">{licence or "GPL-3.0-only"}</license>' in manifest
        assert "<authors>Kevin Watkins</authors>" in manifest
        assert "<copyright>Copyright © Kevin Watkins</copyright>" in manifest
        assert PACKAGE not in manifest


def test_packaging_without_readme_fails_with_actionable_error(consumer, environment):
    project = consumer(CLEAN, properties="<IsPackable>true</IsPackable>", readme=False)
    result = run("dotnet", "pack", str(project), "-c", "Release", cwd=project.parent, env=environment)
    assert result.returncode != 0
    assert "Add ReadMe.md at the repository root" in result.stdout


def test_nunit_runs_with_shared_configuration(consumer, environment):
    fixture = ElementTree.parse(ROOT / "tests/fixtures/NUnit/Example.Tests.csproj")
    references = "".join(
        ElementTree.tostring(item, encoding="unicode") for item in fixture.findall(".//PackageReference")
    )
    method = (
        '[Test] public void Test_Name() => typeof(Example).Assembly.GetName().Name.Should().Equal("Example.Tests");'
    )
    project = consumer(
        "namespace Example.Tests; public sealed class Example { " + method + " }",
        name="Example.Tests",
        references=references,
    )
    (project.parent / "global.json").write_text(json.dumps({"test": {"runner": "Microsoft.Testing.Platform"}}))
    result = run(
        "dotnet", "test", "--project", str(project), "--configuration", "Release", cwd=project.parent, env=environment
    )
    output = succeeds(result)
    assert re.search(r"(?:passed|Passed|succeeded)\s*[:=]\s*1", output), output
    assert re.search(r"(?:failed|Failed)\s*[:=]\s*0", output), output


@pytest.mark.parametrize("configuration", ["Debug", "Release"])
def test_nullable_checks_remain_errors(consumer, environment, configuration):
    project = consumer("namespace Example; internal static class Example { internal static string Read() => null; }")
    result = build(project, environment, configuration)
    assert result.returncode != 0
    assert "CS8603" in result.stdout


def test_project_properties_override_defaults(consumer, environment):
    project = consumer(
        "namespace Example; internal static class Example { internal static string Read() => null; }",
        properties="<Nullable>disable</Nullable>",
    )
    succeeds(build(project, environment))


def test_explicit_test_project_uses_test_rules_without_name_convention(consumer, environment):
    project = consumer(
        "namespace Example; public static class Example { public static void Test_Name() { } }",
        properties="<IsTestProject>true</IsTestProject>",
    )
    succeeds(build(project, environment))


def test_test_project_can_opt_out_of_name_convention(consumer, environment):
    project = consumer(
        "namespace Example.Tests; internal static class Example { internal static int Read_Value() => 42; }",
        name="Example.Tests",
        properties="<IsTestProject>false</IsTestProject><OutputType>Library</OutputType>",
    )
    result = build(project, environment)
    assert result.returncode != 0
    assert "CA1707" in result.stdout


def test_sourcelink_uses_sdk_and_package_metadata_contains_commit(consumer, environment):
    project = consumer(CLEAN, properties="<IsPackable>true</IsPackable><Description>A consumer.</Description>")
    root = project.parents[2]
    (root / ".gitignore").write_text("**/bin/\n**/obj/\npackages/\n")
    for command in [
        ("git", "init", "--initial-branch=main"),
        ("git", "remote", "add", "origin", "https://github.com/MrKWatkins/Example.git"),
        ("git", "add", "."),
        (
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "--no-gpg-sign",
            "-m",
            "Fixture.",
        ),
    ]:
        succeeds(run(*command, cwd=root))
    commit = succeeds(run("git", "rev-parse", "HEAD", cwd=root)).strip()
    destination = root / "packages"
    succeeds(run("dotnet", "pack", str(project), "-c", "Release", "-o", str(destination), cwd=root, env=environment))
    with ZipFile(next(destination.glob("*.nupkg"))) as package:
        manifest = package.read("Example.nuspec").decode()
        metadata = ElementTree.fromstring(manifest.lstrip("\ufeff"))
        repository = next(item for item in metadata.iter() if item.tag.endswith("}repository"))
        assert repository.get("url").removesuffix(".git") == "https://github.com/MrKWatkins/Example"
        assert f'commit="{commit}"' in manifest
        assert "Microsoft.SourceLink.GitHub" not in manifest
    sourcelink = json.loads((project.parent / "obj/Release/net10.0/Example.sourcelink.json").read_text())
    assert any(f"/Example/{commit}/" in url for url in sourcelink["documents"].values())


def test_unused_imports_are_rejected(consumer, environment):
    project = consumer("using System.Text;\n" + CLEAN)
    result = build(project, environment)
    assert result.returncode != 0
    assert "IDE0005" in result.stdout


def test_target_typed_new_is_required_for_fields(consumer, environment):
    project = consumer("""namespace Example;
internal static class Example
{
    private static readonly object instance = new object();
    internal static object Read() => instance;
}
""")
    result = build(project, environment)
    assert result.returncode != 0
    assert "IDE0090" in result.stdout


def test_var_object_creation_is_accepted_for_locals(consumer, environment):
    project = consumer("""namespace Example;
internal static class Example
{
    internal static object Create()
    {
        var value = new object();
        return value;
    }
}
""")
    succeeds(build(project, environment))


def test_standard_friend_assembly_can_access_internals(consumer, environment):
    library = consumer(CLEAN)
    project = consumer(
        "namespace Example.Tests; internal static class Program { "
        "private static int Main() => global::Example.Example.Value() == 42 ? 0 : 1; }",
        name="Example.Tests",
        references=f'<ProjectReference Include="{library}" />',
    )
    succeeds(build(project, environment))
    succeeds(
        run(
            "dotnet",
            "run",
            "--project",
            str(project),
            "-c",
            "Release",
            "--no-build",
            cwd=project.parent,
            env=environment,
        )
    )


def test_debug_allows_unused_private_members(consumer, environment):
    project = consumer("""namespace Example;
internal static class Example
{
    private static readonly object unused = new();
    internal static int Read() => 42;
}
""")
    succeeds(build(project, environment, "Debug"))
    result = build(project, environment)
    assert result.returncode != 0
    assert "CA1823" in result.stdout or "IDE0052" in result.stdout


def test_conditional_returns_and_assignments_are_optional(consumer, environment):
    project = consumer(
        """namespace Example;
internal static class Example
{
    internal static int Read(bool condition)
    {
        if (condition)
        {
            return 1;
        }
        return 0;
    }

    internal static int Assign(bool condition)
    {
        int value;
        if (condition)
        {
            value = 1;
        }
        else
        {
            value = 0;
        }
        return value;
    }
}
""",
        editorconfig="dotnet_diagnostic.IDE0007.severity = none\n",
    )
    succeeds(build(project, environment))


@pytest.mark.parametrize("configuration", ["Debug", "Release"])
@pytest.mark.parametrize("blank_lines", [1, 2])
def test_consecutive_blank_lines_are_rejected(consumer, environment, configuration, blank_lines):
    separator = "\n" * (blank_lines + 1)
    source = (
        "namespace Example;\ninternal static class Example\n{\n"
        "    internal static int One() => 1;" + separator + "    internal static int Two() => 2;\n}\n"
    )
    project = consumer(source)
    result = build(project, environment, configuration)
    if blank_lines == 1:
        succeeds(result)
    else:
        assert result.returncode != 0
        assert "IDE2000" in result.stdout
