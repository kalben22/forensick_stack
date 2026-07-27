"""Tests for the plugin manifest system, the router, and runner hardening."""

from __future__ import annotations

import textwrap

import pytest

from forensicstack.core.plugins.manifest import PluginManifest, parse_size
from forensicstack.core.plugins.registry import (
    ManifestError,
    PluginRegistry,
    UnknownPluginError,
    load_manifest,
    registry as shipped_registry,
)
from forensicstack.core.runners.base import (
    InputRejectedError,
    JobWorkspace,
    ToolExecutionError,
    validate_input,
)
from forensicstack.core.runners.docker import DockerRunner
from forensicstack.core.triage.identify import ArtifactIdentity
from forensicstack.core.triage.kinds import ArtifactKind
from forensicstack.core.triage.router import plan_for, suggest_tools

MINIMAL = """
id: demo
name: Demo Tool
version: "1.0"
runtime:
  kind: docker
  image: example/demo:1.0
normalizer: some.module:DemoNormalizer
features:
  - id: scan
    label: Scan
"""


def write_plugin(root, name: str, body: str):
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "plugin.yaml").write_text(textwrap.dedent(body), encoding="utf-8")
    return d


# --------------------------------------------------------------------------- #
# Manifest validation
# --------------------------------------------------------------------------- #


def test_minimal_manifest_loads(tmp_path):
    write_plugin(tmp_path, "demo", MINIMAL)
    m = load_manifest(tmp_path / "demo" / "plugin.yaml")
    assert m.id == "demo"
    assert m.feature("scan").id == "scan"
    assert m.feature(None).id == "scan", "no feature given should default to the first"


def test_defaults_are_the_hardened_values(tmp_path):
    """Hardening must be what you get by not thinking about it."""
    write_plugin(tmp_path, "demo", MINIMAL)
    rt = load_manifest(tmp_path / "demo" / "plugin.yaml").runtime
    assert rt.network.value == "none"
    assert rt.readonly is True
    assert rt.user == "1000:1000"
    assert rt.is_hardened


def test_unknown_feature_is_rejected(tmp_path):
    """This is the whitelist that closes arbitrary-plugin execution.

    `feature` used to be an unvalidated free string interpolated into the
    container environment, so any authenticated user could run any Volatility
    plugin they liked (windows.dumpfiles, windows.memmap, ...).
    """
    write_plugin(tmp_path, "demo", MINIMAL)
    m = load_manifest(tmp_path / "demo" / "plugin.yaml")
    with pytest.raises(KeyError):
        m.feature("../../etc/passwd")
    with pytest.raises(KeyError):
        m.feature("windows.dumpfiles")


def test_host_bind_mounts_are_refused(tmp_path):
    write_plugin(tmp_path, "bad", MINIMAL + """
    """)
    bad = tmp_path / "bad" / "plugin.yaml"
    bad.write_text(textwrap.dedent("""
        id: bad
        name: Bad
        runtime:
          kind: docker
          image: x:1
          volumes:
            - /var/run/docker.sock:/var/run/docker.sock
        normalizer: m:C
        features:
          - id: a
            label: A
    """), encoding="utf-8")
    with pytest.raises(ManifestError, match="host bind mount"):
        load_manifest(bad)


def test_duplicate_feature_ids_rejected(tmp_path):
    p = tmp_path / "dup" / "plugin.yaml"
    p.parent.mkdir(parents=True)
    p.write_text(textwrap.dedent("""
        id: dup
        name: Dup
        runtime: {kind: docker, image: x:1}
        normalizer: m:C
        feature_env: F
        features:
          - {id: a, label: A}
          - {id: a, label: B}
    """), encoding="utf-8")
    with pytest.raises(ManifestError, match="duplicate feature"):
        load_manifest(p)


def test_multi_feature_plugin_must_declare_feature_env(tmp_path):
    """Without it the container cannot be told which feature to run."""
    p = tmp_path / "nofenv" / "plugin.yaml"
    p.parent.mkdir(parents=True)
    p.write_text(textwrap.dedent("""
        id: nofenv
        name: NoFenv
        runtime: {kind: docker, image: x:1}
        normalizer: m:C
        features:
          - {id: a, label: A}
          - {id: b, label: B}
    """), encoding="utf-8")
    with pytest.raises(ManifestError, match="feature_env"):
        load_manifest(p)


def test_unknown_requires_is_rejected(tmp_path):
    p = tmp_path / "req" / "plugin.yaml"
    p.parent.mkdir(parents=True)
    p.write_text(textwrap.dedent("""
        id: req
        name: Req
        runtime: {kind: docker, image: x:1}
        normalizer: m:C
        feature_env: F
        features:
          - {id: a, label: A, requires: [nope]}
          - {id: b, label: B}
    """), encoding="utf-8")
    with pytest.raises(ManifestError, match="unknown feature"):
        load_manifest(p)


def test_docker_runtime_requires_an_image(tmp_path):
    p = tmp_path / "noimg" / "plugin.yaml"
    p.parent.mkdir(parents=True)
    p.write_text("id: noimg\nname: N\nruntime: {kind: docker}\n"
                 "normalizer: m:C\nfeatures: [{id: a, label: A}]\n", encoding="utf-8")
    with pytest.raises(ManifestError, match="runtime.image"):
        load_manifest(p)


def test_normalizer_must_be_a_dotted_path(tmp_path):
    p = tmp_path / "badnorm" / "plugin.yaml"
    p.parent.mkdir(parents=True)
    p.write_text("id: bad\nname: N\nruntime: {kind: docker, image: x:1}\n"
                 "normalizer: NotDotted\nfeatures: [{id: a, label: A}]\n", encoding="utf-8")
    with pytest.raises(ManifestError, match="ClassName"):
        load_manifest(p)


@pytest.mark.parametrize(
    "literal,expected",
    [("1B", 1), ("512", 512), ("1KiB", 1024), ("2MiB", 2 * 1024**2),
     ("6GiB", 6 * 1024**3), ("1GB", 10**9), ("1.5GiB", int(1.5 * 1024**3))],
)
def test_size_parsing(literal, expected):
    assert parse_size(literal) == expected


def test_bad_size_literal_raises():
    with pytest.raises(ValueError):
        parse_size("many gigabytes")


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #


def test_registry_discovers_plugins(tmp_path):
    write_plugin(tmp_path, "demo", MINIMAL)
    write_plugin(tmp_path, "nested/other", MINIMAL.replace("id: demo", "id: other"))
    reg = PluginRegistry([tmp_path]).load()
    assert set(reg.ids) == {"demo", "other"}
    assert len(reg) == 2


def test_registry_rejects_duplicate_ids(tmp_path):
    write_plugin(tmp_path, "one", MINIMAL)
    write_plugin(tmp_path, "two", MINIMAL)
    with pytest.raises(ManifestError, match="duplicate plugin id"):
        PluginRegistry([tmp_path]).load()


def test_disabled_plugin_is_skipped(tmp_path):
    write_plugin(tmp_path, "demo", MINIMAL + "\nenabled: false\n")
    assert PluginRegistry([tmp_path]).load().ids == []


def test_resolve_rejects_unknown_tool_and_feature(tmp_path):
    write_plugin(tmp_path, "demo", MINIMAL)
    reg = PluginRegistry([tmp_path]).load()
    with pytest.raises(UnknownPluginError):
        reg.resolve("nope", None)
    with pytest.raises(UnknownPluginError):
        reg.resolve("demo", "not-a-feature")


def test_a_broken_manifest_fails_at_load_not_after_two_hours(tmp_path):
    """Validation happens up front, not after the container has run.

    Previously a missing entry in NORMALIZERS surfaced only *after* the tool
    finished — up to 7200 s for Volatility.
    """
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "plugin.yaml").write_text("id: [not, a, string]\n", encoding="utf-8")
    with pytest.raises(ManifestError):
        PluginRegistry([tmp_path]).load()


# --------------------------------------------------------------------------- #
# The shipped manifests must be valid
# --------------------------------------------------------------------------- #


def test_shipped_plugins_load_and_are_hardened():
    reg = PluginRegistry().load(force=True)
    assert {"volatility", "exiftool", "ileapp", "aleapp", "triage"} <= set(reg.ids)
    for manifest in reg:
        assert manifest.runtime.is_hardened, f"{manifest.id} is not hardened"
        assert manifest.features, f"{manifest.id} declares no features"


def test_volatility_has_a_usable_default_feature():
    """Regression: with no feature selected the old code emitted
    `VOLATILITY_PLUGIN=fs`, producing `vol -f dump --renderer json fs` — a
    guaranteed failure, because the registry entry had no default_type."""
    m = PluginRegistry().load(force=True).get("volatility")
    default = m.feature(None)
    assert default.id.startswith(("windows.", "linux.")), default.id


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #


def _identity(kind, os_hint=None, confidence=0.95, size=64 * 1024 * 1024):
    return ArtifactIdentity(kind=kind, os_hint=os_hint, confidence=confidence, size=size)


def test_memory_dump_plans_volatility_in_dependency_order():
    plan = plan_for(_identity(ArtifactKind.MEMORY_DUMP, "windows"),
                    reg=PluginRegistry().load(force=True))
    ids = [f"{s.tool}/{s.feature}" for s in plan.steps]
    assert "volatility/windows.info" in ids
    assert "volatility/windows.pslist" in ids
    assert ids.index("volatility/windows.info") < ids.index("volatility/windows.pslist")
    assert "triage/scan" in ids, "the generic pass should always be planned"


def test_os_mismatch_is_skipped_with_a_reason():
    plan = plan_for(_identity(ArtifactKind.MEMORY_DUMP, "windows"),
                    reg=PluginRegistry().load(force=True))
    ids = {f"{s.tool}/{s.feature}" for s in plan.steps}
    assert "volatility/linux.pslist" not in ids
    assert any("linux" in target for target, _ in plan.skipped)


def test_unknown_artifact_still_gets_the_generic_path():
    plan = plan_for(_identity(ArtifactKind.UNKNOWN, confidence=0.0),
                    reg=PluginRegistry().load(force=True))
    assert plan.steps, "an unidentified blob must still be triaged"
    assert all(s.stage == 0 for s in plan.steps)
    assert any("not confidently" in n for n in plan.notes)


def test_oversized_artifact_is_skipped_not_attempted():
    plan = plan_for(_identity(ArtifactKind.MEMORY_DUMP, "windows", size=200 * 1024**3),
                    reg=PluginRegistry().load(force=True))
    assert any("larger than the declared maximum" in why for _, why in plan.skipped)


def test_cap_is_reported_never_silent():
    """A truncated plan that looks complete is worse than no plan."""
    plan = plan_for(_identity(ArtifactKind.MEMORY_DUMP, "windows"),
                    reg=PluginRegistry().load(force=True), max_steps=2)
    assert len(plan.steps) == 2
    assert any("capped" in why for _, why in plan.skipped)
    assert any("dropped" in n for n in plan.notes)


def test_suggestions_include_manual_features():
    s = suggest_tools(_identity(ArtifactKind.MEMORY_DUMP, "windows"),
                      reg=PluginRegistry().load(force=True))
    assert any(x["feature"] == "windows.filescan" for x in s), \
        "manual-only features should still be suggested to the analyst"


# --------------------------------------------------------------------------- #
# Runner hardening — the security regression tests
# --------------------------------------------------------------------------- #


def _demo_manifest() -> PluginManifest:
    return PluginManifest.model_validate({
        "id": "demo", "name": "Demo",
        "runtime": {"kind": "docker", "image": "example/demo:1.0", "memory": "1g"},
        "normalizer": "m:C",
        "features": [{"id": "scan", "label": "Scan"}],
    })


def _command(tmp_path):
    manifest = _demo_manifest()
    ws = JobWorkspace.create(tmp_path, "job123")
    src = tmp_path / "artifact.bin"
    src.write_bytes(b"x" * 1024)
    staged = ws.place_input(src)
    return DockerRunner().build_command(
        manifest, manifest.feature("scan"), ws, staged, "fs_demo_job123"
    ), ws


def test_runner_never_uses_volumes_from(tmp_path):
    """THE regression test.

    `--volumes-from fs_worker` inherited every mount of the worker, including
    /var/run/docker.sock and the writable source tree, into each tool container.
    Any code execution inside a forensic tool was therefore host root.
    """
    cmd, _ = _command(tmp_path)
    assert "--volumes-from" not in cmd


def test_runner_never_mounts_the_docker_socket(tmp_path):
    cmd, _ = _command(tmp_path)
    assert not any("docker.sock" in part for part in cmd)


def test_runner_mounts_exactly_two_paths(tmp_path):
    cmd, ws = _command(tmp_path)
    mounts = [cmd[i + 1] for i, c in enumerate(cmd) if c == "-v"]
    assert len(mounts) == 2
    assert any(m.endswith("/input:ro") for m in mounts), "input must be read-only"
    assert any(m.endswith("/output:rw") for m in mounts)
    assert all(str(ws.base) in m for m in mounts), \
        "a tool must only ever see its own job workspace"


def test_runner_applies_isolation_flags(tmp_path):
    cmd, _ = _command(tmp_path)
    joined = " ".join(cmd)
    assert "--cap-drop=ALL" in cmd
    assert "--security-opt no-new-privileges" in joined
    assert "--network none" in joined
    assert "--read-only" in cmd
    assert "--user 1000:1000" in joined
    assert "--pids-limit" in cmd
    assert "--memory-swap" in cmd, "without it, memory limits are escapable via swap"


def test_feature_reaches_the_container_only_via_the_manifest(tmp_path):
    manifest = PluginManifest.model_validate({
        "id": "vol", "name": "V",
        "runtime": {"kind": "docker", "image": "x:1"},
        "normalizer": "m:C", "feature_env": "VOLATILITY_PLUGIN",
        "features": [{"id": "windows.pslist", "label": "P"},
                     {"id": "windows.netscan", "label": "N"}],
    })
    ws = JobWorkspace.create(tmp_path, "j")
    src = tmp_path / "a.bin"
    src.write_bytes(b"x")
    staged = ws.place_input(src)
    cmd = DockerRunner().build_command(
        manifest, manifest.feature("windows.netscan"), ws, staged, "c"
    )
    assert "VOLATILITY_PLUGIN=windows.netscan" in cmd
    with pytest.raises(KeyError):
        manifest.feature("windows.memmap; rm -rf /")


def test_workspace_isolates_and_cleans_up(tmp_path):
    ws = JobWorkspace.create(tmp_path, "abc")
    assert ws.input_dir.is_dir() and ws.output_dir.is_dir() and ws.log_dir.is_dir()
    src = tmp_path / "in.bin"
    src.write_bytes(b"data")
    staged = ws.place_input(src)
    assert staged.parent == ws.input_dir
    assert staged.read_bytes() == b"data"
    ws.cleanup()
    assert not ws.base.exists()


def test_input_size_bounds_are_enforced_before_spending_a_container(tmp_path):
    manifest = PluginManifest.model_validate({
        "id": "demo_sized", "name": "D",
        "runtime": {"kind": "docker", "image": "x:1"},
        "normalizer": "m:C",
        "accepts": {"min_size": "1KiB", "max_size": "2KiB"},
        "features": [{"id": "s", "label": "S"}],
    })
    small = tmp_path / "small.bin"
    small.write_bytes(b"x" * 10)
    with pytest.raises(InputRejectedError):
        validate_input(manifest, manifest.feature("s"), small)

    big = tmp_path / "big.bin"
    big.write_bytes(b"x" * 5000)
    with pytest.raises(InputRejectedError):
        validate_input(manifest, manifest.feature("s"), big)


def test_tool_execution_error_truncates_huge_stderr():
    err = ToolExecutionError("demo", 1, "x" * 10000)
    assert "truncated" in str(err)
    assert len(str(err)) < 6000
