"""
Runtime plugin discovery.

Walks the plugin roots, parses every ``plugin.yaml``, validates it against
:class:`PluginManifest`, and exposes lookups.  Nothing else in the codebase
hardcodes a tool name.

Failure policy is deliberate:

* A malformed manifest **fails loudly at startup**, listing the offending file.
  The old design deferred the equivalent failure (a missing entry in
  ``normalization_engine.NORMALIZERS``) until *after* the container had already
  burned its full runtime — up to two hours for Volatility.
* A manifest that parses but whose *normalizer* is broken fails only when that
  tool is first used, because the normalizer is imported lazily.  One bad tool
  must not stop the platform from booting.
"""

from __future__ import annotations

import importlib
import logging
import os
import threading
from pathlib import Path
from typing import Iterable, Iterator

import yaml
from pydantic import ValidationError

from forensicstack.core.plugins.manifest import FeatureSpec, PluginManifest
from forensicstack.core.triage.kinds import ArtifactKind

log = logging.getLogger(__name__)

MANIFEST_NAME = "plugin.yaml"

#: Default search root: ``forensicstack/plugins/``.  Override or extend with
#: ``FORENSICSTACK_PLUGIN_PATH`` (os.pathsep-separated) to drop in out-of-tree
#: tools without touching the package.
_DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "plugins"


class PluginError(RuntimeError):
    pass


class ManifestError(PluginError):
    """A plugin.yaml is present but invalid."""


class UnknownPluginError(KeyError, PluginError):
    pass


def _plugin_roots() -> list[Path]:
    roots = [_DEFAULT_ROOT]
    extra = os.getenv("FORENSICSTACK_PLUGIN_PATH", "")
    for part in extra.split(os.pathsep):
        part = part.strip()
        if part:
            roots.append(Path(part).expanduser().resolve())
    return roots


def _iter_manifest_files(roots: Iterable[Path]) -> Iterator[Path]:
    for root in roots:
        if not root.is_dir():
            log.debug("plugin root %s does not exist, skipping", root)
            continue
        # rglob so tools may be grouped (plugins/memory/volatility/plugin.yaml)
        yield from sorted(root.rglob(MANIFEST_NAME))


def load_manifest(path: Path) -> PluginManifest:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ManifestError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ManifestError(f"{path}: top level must be a mapping")
    raw["source_dir"] = str(path.parent)
    try:
        return PluginManifest.model_validate(raw)
    except ValidationError as exc:
        raise ManifestError(f"{path}: {exc}") from exc


class PluginRegistry:
    """Thread-safe, lazily-populated view over the discovered plugins."""

    def __init__(self, roots: Iterable[Path] | None = None) -> None:
        self._roots = list(roots) if roots is not None else _plugin_roots()
        self._plugins: dict[str, PluginManifest] = {}
        self._normalizers: dict[str, object] = {}
        self._lock = threading.RLock()
        self._loaded = False

    # ---- loading ----------------------------------------------------------- #

    def load(self, *, force: bool = False) -> "PluginRegistry":
        with self._lock:
            if self._loaded and not force:
                return self
            plugins: dict[str, PluginManifest] = {}
            errors: list[str] = []
            for manifest_path in _iter_manifest_files(self._roots):
                try:
                    manifest = load_manifest(manifest_path)
                except ManifestError as exc:
                    errors.append(str(exc))
                    continue
                if manifest.id in plugins:
                    errors.append(
                        f"{manifest_path}: duplicate plugin id {manifest.id!r} "
                        f"(already defined in {plugins[manifest.id].source_dir})"
                    )
                    continue
                if not manifest.enabled:
                    log.info("plugin %s is disabled, skipping", manifest.id)
                    continue
                if not manifest.runtime.is_hardened:
                    log.warning(
                        "plugin %s runs unhardened (network=%s readonly=%s user=%s) "
                        "— it will process untrusted input with reduced isolation",
                        manifest.id,
                        manifest.runtime.network.value,
                        manifest.runtime.readonly,
                        manifest.runtime.user,
                    )
                plugins[manifest.id] = manifest
            if errors:
                raise ManifestError(
                    "invalid plugin manifest(s):\n  - " + "\n  - ".join(errors)
                )
            self._plugins = plugins
            self._normalizers.clear()
            self._loaded = True
            log.info("loaded %d plugin(s): %s", len(plugins), ", ".join(sorted(plugins)))
            return self

    def _ensure(self) -> None:
        if not self._loaded:
            self.load()

    # ---- lookups ----------------------------------------------------------- #

    def __contains__(self, plugin_id: object) -> bool:
        self._ensure()
        return plugin_id in self._plugins

    def __iter__(self) -> Iterator[PluginManifest]:
        self._ensure()
        return iter(sorted(self._plugins.values(), key=lambda m: m.id))

    def __len__(self) -> int:
        self._ensure()
        return len(self._plugins)

    @property
    def ids(self) -> list[str]:
        self._ensure()
        return sorted(self._plugins)

    def get(self, plugin_id: str) -> PluginManifest:
        self._ensure()
        try:
            return self._plugins[plugin_id]
        except KeyError:
            raise UnknownPluginError(
                f"unknown tool {plugin_id!r}; available: {', '.join(self.ids)}"
            ) from None

    def resolve(self, plugin_id: str, feature_id: str | None) -> tuple[PluginManifest, FeatureSpec]:
        """Validate a (tool, feature) pair coming from an API request.

        This *is* the whitelist.  Previously ``feature`` was an unvalidated free
        string interpolated into the container's environment, so any
        authenticated user could run an arbitrary Volatility plugin.
        """
        manifest = self.get(plugin_id)
        try:
            return manifest, manifest.feature(feature_id)
        except KeyError as exc:
            raise UnknownPluginError(str(exc)) from None

    def for_kind(self, kind: ArtifactKind) -> list[tuple[PluginManifest, FeatureSpec]]:
        """Every (plugin, feature) that declares it accepts ``kind``."""
        self._ensure()
        out: list[tuple[PluginManifest, FeatureSpec]] = []
        for manifest in self:
            for feature in manifest.features:
                if kind in manifest.accepts_for(feature).kinds:
                    out.append((manifest, feature))
        return out

    def to_api_list(self) -> list[dict]:
        return [m.to_api_dict() for m in self]

    # ---- normalizers ------------------------------------------------------- #

    def normalizer(self, plugin_id: str):
        """Import and cache the plugin's normalizer instance.

        Lazy on purpose: importing every normalizer at module load meant the API
        process paid for parsers it never uses, and one broken import took the
        whole app down.
        """
        self._ensure()
        with self._lock:
            if plugin_id in self._normalizers:
                return self._normalizers[plugin_id]
            manifest = self.get(plugin_id)
            module_path, _, class_name = manifest.normalizer.partition(":")
            try:
                module = importlib.import_module(module_path)
            except ImportError as exc:
                raise PluginError(
                    f"plugin {plugin_id!r}: cannot import normalizer module "
                    f"{module_path!r}: {exc}"
                ) from exc
            try:
                cls = getattr(module, class_name)
            except AttributeError as exc:
                raise PluginError(
                    f"plugin {plugin_id!r}: module {module_path!r} has no "
                    f"{class_name!r}"
                ) from exc
            instance = cls()
            self._normalizers[plugin_id] = instance
            return instance


#: Process-wide registry.  Import this, don't build your own.
registry = PluginRegistry()


def get_registry() -> PluginRegistry:
    """FastAPI dependency."""
    registry._ensure()
    return registry
