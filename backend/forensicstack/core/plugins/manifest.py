"""
Plugin manifest schema.

A plugin is a *directory* containing a ``plugin.yaml``.  That file is the single
source of truth for the tool: its container image, its resource envelope, the
features it exposes, what inputs it accepts, and which normalizer parses its
output.

This replaces the old triple source of truth (``core/plugin_registry.py`` dict +
``core/normalization_engine.py`` dict + ``plugins/external/*/config.py``) which
could — and did — disagree with each other.

Adding a tool is now: create a directory, drop a ``plugin.yaml`` in it.  No core
module is edited, no service is redeployed to pick up the feature list.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from forensicstack.core.triage.kinds import ArtifactKind

# --------------------------------------------------------------------------- #
# Primitives
# --------------------------------------------------------------------------- #

_SIZE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([KMGT]?i?B?)\s*$", re.IGNORECASE)
_SIZE_UNITS = {
    "": 1,
    "b": 1,
    "k": 1000, "kb": 1000, "ki": 1024, "kib": 1024,
    "m": 1000**2, "mb": 1000**2, "mi": 1024**2, "mib": 1024**2,
    "g": 1000**3, "gb": 1000**3, "gi": 1024**3, "gib": 1024**3,
    "t": 1000**4, "tb": 1000**4, "ti": 1024**4, "tib": 1024**4,
}


def parse_size(value: str | int) -> int:
    """'6GiB' -> 6442450944.  Raises ValueError on garbage."""
    if isinstance(value, int):
        return value
    m = _SIZE_RE.match(str(value))
    if not m:
        raise ValueError(f"invalid size literal: {value!r}")
    number, unit = m.group(1), m.group(2).lower()
    if unit not in _SIZE_UNITS:
        raise ValueError(f"unknown size unit in {value!r}")
    return int(float(number) * _SIZE_UNITS[unit])


PluginId = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{1,31}$")]
FeatureId = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_.\-]{0,63}$")]


class RunnerKind(str, Enum):
    docker = "docker"
    native = "native"


class NetworkMode(str, Enum):
    none = "none"
    bridge = "bridge"


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #


class RuntimeSpec(BaseModel):
    """How to execute the tool.

    Defaults are the *hardened* values.  A plugin must opt out explicitly and
    visibly (and ``registry.py`` logs a warning when it does), rather than
    hardening being something each call site remembers to add.
    """

    model_config = ConfigDict(extra="forbid")

    kind: RunnerKind = RunnerKind.docker

    # docker
    image: str | None = None
    network: NetworkMode = NetworkMode.none
    readonly: bool = True
    user: str | None = "1000:1000"
    memory: str = "2g"
    cpus: str = "1"
    pids_limit: int = 256
    tmpfs: list[str] = Field(default_factory=list)
    volumes: list[str] = Field(default_factory=list)
    """Extra named volumes, ``name:/path[:ro]``.  Host bind mounts are rejected —
    a plugin may never reach into the host filesystem."""

    # native
    executable: str | None = None
    tool_dir_env: str | None = None

    # both
    timeout: int = Field(default=600, ge=1, le=86_400)
    env: dict[str, str] = Field(default_factory=dict)

    @field_validator("volumes")
    @classmethod
    def _no_host_binds(cls, v: list[str]) -> list[str]:
        for spec in v:
            src = spec.split(":", 1)[0]
            if "/" in src or "\\" in src or src.startswith("."):
                raise ValueError(
                    f"host bind mount {spec!r} is not allowed in a plugin manifest; "
                    "use a named volume"
                )
        return v

    @model_validator(mode="after")
    def _check_kind(self) -> RuntimeSpec:
        if self.kind is RunnerKind.docker and not self.image:
            raise ValueError("runtime.image is required when runtime.kind is 'docker'")
        if self.kind is RunnerKind.native and not self.executable:
            raise ValueError(
                "runtime.executable is required when runtime.kind is 'native'"
            )
        return self

    @property
    def is_hardened(self) -> bool:
        return (
            self.network is NetworkMode.none
            and self.readonly
            and self.user not in (None, "root", "0:0", "0")
        )


class AcceptSpec(BaseModel):
    """What this plugin will take as input.

    ``kinds`` is what the auto-router uses; ``extensions`` is a fallback hint for
    the UI.  Identification by content always wins over the file name.
    """

    model_config = ConfigDict(extra="forbid")

    kinds: list[ArtifactKind] = Field(default_factory=list)
    extensions: list[str] = Field(default_factory=list)
    max_size: str = "64GiB"
    min_size: str = "1B"

    @field_validator("extensions")
    @classmethod
    def _normalise_ext(cls, v: list[str]) -> list[str]:
        out = []
        for e in v:
            e = e.strip().lower()
            if not e.startswith("."):
                e = "." + e
            out.append(e)
        return out

    @property
    def max_size_bytes(self) -> int:
        return parse_size(self.max_size)

    @property
    def min_size_bytes(self) -> int:
        return parse_size(self.min_size)


class FeatureSpec(BaseModel):
    """One analysis a plugin can perform.

    ``id`` is passed to the container as the plugin's ``env_var``.  The registry
    turns the set of feature ids into the whitelist the API validates against —
    which is what closes the "arbitrary Volatility plugin execution" hole for
    free, instead of needing a hand-maintained second list.
    """

    model_config = ConfigDict(extra="forbid")

    id: FeatureId
    label: str
    description: str = ""
    timeout: int | None = Field(default=None, ge=1, le=86_400)
    memory: str | None = None
    accepts: AcceptSpec | None = None
    emits: list[str] = Field(default_factory=list)
    """Finding kinds this feature produces.  Used by the chain planner to know
    what a later stage can consume, and by tests to assert output shape."""

    auto: bool = False
    """Include this feature in the automatic triage plan when the artifact
    matches.  Keeps 'run everything' from being the default."""

    auto_priority: int = Field(default=50, ge=0, le=100)
    """Lower runs first within an auto plan."""

    os_hint: Literal["windows", "linux", "macos", "android", "ios"] | None = None
    """Only auto-schedule when identification agrees on the OS."""

    requires: list[str] = Field(default_factory=list)
    """Feature ids (same plugin) that must complete first."""


class PluginManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: PluginId
    name: str
    version: str = "0.0.0"
    category: str = "misc"
    description: str = ""
    homepage: str | None = None
    license: str | None = None

    runtime: RuntimeSpec
    accepts: AcceptSpec = Field(default_factory=AcceptSpec)
    features: list[FeatureSpec] = Field(min_length=1)

    normalizer: str
    """Dotted path ``module:ClassName``.  Imported lazily, on first use — so a
    broken normalizer for tool X cannot stop the whole app from booting, and the
    import cost is not paid by every process that merely lists tools."""

    feature_env: str | None = None
    """Env var carrying the selected feature id into the container."""

    enabled: bool = True

    # populated by the registry, not by the YAML
    source_dir: str = ""

    @field_validator("normalizer")
    @classmethod
    def _check_normalizer(cls, v: str) -> str:
        if ":" not in v:
            raise ValueError(
                "normalizer must be 'package.module:ClassName', "
                f"got {v!r}"
            )
        return v

    @model_validator(mode="after")
    def _check_features(self) -> PluginManifest:
        seen: set[str] = set()
        for f in self.features:
            if f.id in seen:
                raise ValueError(f"duplicate feature id {f.id!r} in plugin {self.id!r}")
            seen.add(f.id)
        for f in self.features:
            for dep in f.requires:
                if dep not in seen:
                    raise ValueError(
                        f"feature {f.id!r} requires unknown feature {dep!r}"
                    )
        if len(self.features) > 1 and not self.feature_env:
            raise ValueError(
                f"plugin {self.id!r} exposes several features but declares no "
                "feature_env, so the container cannot be told which one to run"
            )
        return self

    # ---- lookup helpers ---------------------------------------------------- #

    @property
    def feature_ids(self) -> set[str]:
        return {f.id for f in self.features}

    def feature(self, feature_id: str | None) -> FeatureSpec:
        """Resolve a feature id, defaulting to the first declared feature.

        Raises ``KeyError`` for anything not declared.  This is the whitelist:
        a feature id that is not in the manifest never reaches a container.
        """
        if feature_id is None:
            return self.features[0]
        for f in self.features:
            if f.id == feature_id:
                return f
        raise KeyError(
            f"unknown feature {feature_id!r} for plugin {self.id!r}; "
            f"available: {sorted(self.feature_ids)}"
        )

    def accepts_for(self, feature: FeatureSpec) -> AcceptSpec:
        return feature.accepts or self.accepts

    def effective_timeout(self, feature: FeatureSpec) -> int:
        return feature.timeout or self.runtime.timeout

    def effective_memory(self, feature: FeatureSpec) -> str:
        return feature.memory or self.runtime.memory

    def to_api_dict(self) -> dict[str, Any]:
        """Shape consumed by ``GET /api/v1/jobs/tools`` and the UI."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "category": self.category,
            "description": self.description,
            "features": [
                {
                    "id": f.id,
                    "label": f.label,
                    "description": f.description,
                    "accepted_extensions": self.accepts_for(f).extensions,
                    "emits": f.emits,
                    "auto": f.auto,
                }
                for f in self.features
            ],
        }
