"""
Execution contract shared by every runner.

The old code had three container-launching implementations
(``core/docker_runner.py`` — dead, ``core/executor/docker_executor.py`` — live,
``core/executor/native_executor.py`` — parallel) that shared *nothing*: no base
class, no common job-directory helper, no common timeout resolution, and — worst
— no common error contract.  DockerExecutor used ``check=True``; NativeExecutor
used ``check=False`` and never looked at ``returncode``, so a crashed tool
produced an empty output directory, the normalizer returned ``[]``, and the job
was reported ``completed`` with zero findings.

One contract, enforced here: a non-zero exit is always a
:class:`ToolExecutionError`, and "the tool ran but found nothing" is always an
empty finding list.  Those two must never be confusable.
"""

from __future__ import annotations

import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from forensicstack.core.plugins.manifest import FeatureSpec, PluginManifest


class ToolError(RuntimeError):
    """Base for every execution failure."""

    retryable = False


class ToolExecutionError(ToolError):
    """The tool ran and failed."""

    def __init__(self, tool: str, exit_code: int, stderr: str = "", stdout: str = ""):
        self.tool, self.exit_code = tool, exit_code
        self.stderr, self.stdout = stderr, stdout
        detail = (stderr or stdout or "").strip()
        if len(detail) > 4000:
            detail = detail[:4000] + f"\n… (+{len(detail) - 4000} bytes truncated)"
        super().__init__(
            f"{tool} exited with code {exit_code}" + (f":\n{detail}" if detail else "")
        )


class ToolTimeoutError(ToolError):
    """The tool exceeded its declared timeout."""

    retryable = False

    def __init__(self, tool: str, timeout: int):
        self.tool, self.timeout = tool, timeout
        super().__init__(f"{tool} exceeded its {timeout}s timeout and was killed")


class ToolUnavailableError(ToolError):
    """Infrastructure problem — the runtime itself is missing or unreachable.

    Retryable, unlike a tool that ran and failed.  The old worker collapsed both
    into ``status=failed`` with no way to tell "MinIO was briefly down" from
    "this input is garbage".
    """

    retryable = True


class InputRejectedError(ToolError):
    """The input does not satisfy the plugin's declared accepts."""


@dataclass
class RunResult:
    tool: str
    feature: str
    exit_code: int
    output_dir: Path
    stdout_path: Path
    stderr_path: Path
    duration_s: float
    command: list[str] = field(default_factory=list)

    @property
    def produced_files(self) -> list[Path]:
        return [p for p in sorted(self.output_dir.rglob("*")) if p.is_file()]

    @property
    def output_bytes(self) -> int:
        return sum(p.stat().st_size for p in self.produced_files)


@dataclass
class JobWorkspace:
    """Per-job scratch area.

    Layout (all under one directory so cleanup is a single ``rmtree``)::

        <root>/<job_id>/
            input/        the artifact, mounted read-only into the container
            output/       the only writable mount
            logs/         stdout / stderr captured from the runtime

    The container therefore sees exactly two paths. Nothing is inherited from
    the worker, which is what makes the ``--volumes-from`` escape impossible by
    construction rather than by remembering to add flags.
    """

    root: Path
    job_id: str

    @property
    def base(self) -> Path:
        return self.root / self.job_id

    @property
    def input_dir(self) -> Path:
        return self.base / "input"

    @property
    def output_dir(self) -> Path:
        return self.base / "output"

    @property
    def log_dir(self) -> Path:
        return self.base / "logs"

    @classmethod
    def create(cls, root: Path, job_id: str | None = None) -> "JobWorkspace":
        ws = cls(root=Path(root), job_id=job_id or uuid.uuid4().hex)
        for d in (ws.input_dir, ws.output_dir, ws.log_dir):
            d.mkdir(parents=True, exist_ok=True)
        # The container runs as a non-root uid; it must be able to write here.
        try:
            ws.output_dir.chmod(0o777)
        except OSError:  # pragma: no cover - Windows
            pass
        return ws

    def place_input(self, source: Path, *, link: bool = True) -> Path:
        """Put the artifact into ``input/`` without copying multi-GB files.

        Hard link when possible (same filesystem, instant, no extra space);
        fall back to copy only when the link cannot be made.
        """
        source = Path(source)
        target = self.input_dir / source.name
        if target.exists():
            return target
        if link:
            try:
                target.hardlink_to(source)
                return target
            except (OSError, AttributeError, NotImplementedError):
                pass
        shutil.copy2(source, target)
        return target

    def cleanup(self) -> None:
        shutil.rmtree(self.base, ignore_errors=True)


@runtime_checkable
class Runner(Protocol):
    kind: str

    def run(
        self,
        manifest: PluginManifest,
        feature: FeatureSpec,
        workspace: JobWorkspace,
        input_file: Path,
    ) -> RunResult:
        ...


def validate_input(
    manifest: PluginManifest, feature: FeatureSpec, input_file: Path
) -> None:
    """Enforce the manifest's ``accepts`` before spending a container on it."""
    accepts = manifest.accepts_for(feature)
    size = input_file.stat().st_size
    if size < accepts.min_size_bytes:
        raise InputRejectedError(
            f"{manifest.id}/{feature.id}: input is {size} bytes, minimum is "
            f"{accepts.min_size}"
        )
    if size > accepts.max_size_bytes:
        raise InputRejectedError(
            f"{manifest.id}/{feature.id}: input is {size} bytes, maximum is "
            f"{accepts.max_size}"
        )


class _Timer:
    def __enter__(self) -> "_Timer":
        self._t0 = time.monotonic()
        return self

    def __exit__(self, *exc: object) -> None:
        self.elapsed = time.monotonic() - self._t0
