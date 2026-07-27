"""
Hardened Docker runner.

What changed, and why it matters
--------------------------------

The previous implementation did::

    worker_name = _WORKER_CONTAINER or "fs_worker"
    cmd += ["--volumes-from", worker_name]

``--volumes-from`` inherits *every* mount of the source container — bind mounts
included.  ``docker-compose.yml`` gave the worker both ``.:/app:rw`` (the whole
source tree, writable) and ``/var/run/docker.sock``.  So every forensic tool
container received the Docker socket and the application's own source code.
``--cap-drop=ALL``, ``--security-opt no-new-privileges``, ``--pids-limit`` and
``--read-only`` were all applied on the same command line and were all
irrelevant: a process that can call ``POST /containers/create`` with
``Privileged: true`` and ``/:/host`` owns the host.

Concretely: analysing a memory dump supplied by a third party, with a parsing
bug in Volatility 3, meant host root. That is precisely the scenario the
platform exists to make safe.

This runner instead mounts exactly two paths, both derived from the job's own
workspace, and never inherits anything:

* ``<workspace>/input``  → ``/input``  (read-only)
* ``<workspace>/output`` → ``/output`` (read-write, the only writable mount)

The worker still needs to reach *a* Docker endpoint, but it should be a
socket proxy with a create/start/wait/remove allowlist (``DOCKER_HOST``),
not the raw socket.
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import time
from pathlib import Path

from forensicstack.core.plugins.manifest import FeatureSpec, NetworkMode, PluginManifest
from forensicstack.core.runners.base import (
    JobWorkspace,
    RunResult,
    ToolExecutionError,
    ToolTimeoutError,
    ToolUnavailableError,
    validate_input,
)

log = logging.getLogger(__name__)

CONTAINER_INPUT = "/input"
CONTAINER_OUTPUT = "/output"

#: When the worker itself runs inside a container, the paths it sees are not the
#: paths the Docker daemon sees.  Set HOST_WORKSPACE_ROOT to the *host* path that
#: backs the workspace volume; leave it empty when the worker runs natively.
_HOST_WORKSPACE_ROOT = os.getenv("HOST_WORKSPACE_ROOT", "").strip()
_WORKSPACE_ROOT = os.getenv("FORENSICSTACK_WORKSPACE", "").strip()

#: Grace period given to `docker kill` itself, so a wedged daemon cannot hang
#: the worker forever.  The old code called `docker kill` with no timeout and
#: discarded its result.
_KILL_TIMEOUT = 30


def _translate(path: Path) -> str:
    """Map a worker-visible path to its daemon-visible equivalent."""
    p = Path(path).resolve()
    if not _HOST_WORKSPACE_ROOT or not _WORKSPACE_ROOT:
        return str(p)
    root = Path(_WORKSPACE_ROOT).resolve()
    try:
        rel = p.relative_to(root)
    except ValueError:
        return str(p)
    return str(Path(_HOST_WORKSPACE_ROOT) / rel)


class DockerRunner:
    kind = "docker"

    def __init__(self, docker_bin: str = "docker") -> None:
        self.docker_bin = docker_bin

    # ---- command construction --------------------------------------------- #

    def build_command(
        self,
        manifest: PluginManifest,
        feature: FeatureSpec,
        workspace: JobWorkspace,
        input_file: Path,
        container_name: str,
    ) -> list[str]:
        rt = manifest.runtime
        cmd: list[str] = [
            self.docker_bin, "run", "--rm",
            "--name", container_name,
            # --- isolation ------------------------------------------------- #
            "--network", rt.network.value,
            "--cap-drop=ALL",
            "--security-opt", "no-new-privileges",
            # --- resources ------------------------------------------------- #
            "--memory", manifest.effective_memory(feature),
            "--memory-swap", manifest.effective_memory(feature),  # no swap escape
            "--cpus", rt.cpus,
            "--pids-limit", str(rt.pids_limit),
        ]
        if rt.user:
            cmd += ["--user", rt.user]
        if rt.readonly:
            cmd.append("--read-only")
            # A read-only rootfs needs somewhere to scribble; give it tmpfs
            # rather than dropping --read-only for the whole tool.
            cmd += ["--tmpfs", "/tmp:rw,noexec,nosuid,size=512m"]
        for t in rt.tmpfs:
            cmd += ["--tmpfs", t]
        for vol in rt.volumes:  # named volumes only — validated in the manifest
            cmd += ["-v", vol]

        # --- the only two mounts the tool ever sees ------------------------ #
        cmd += [
            "-v", f"{_translate(workspace.input_dir)}:{CONTAINER_INPUT}:ro",
            "-v", f"{_translate(workspace.output_dir)}:{CONTAINER_OUTPUT}:rw",
        ]

        env: dict[str, str] = {
            "INPUT_PATH": f"{CONTAINER_INPUT}/{input_file.name}",
            "INPUT_DIR": CONTAINER_INPUT,
            "INPUT_FILENAME": input_file.name,
            "OUTPUT_PATH": CONTAINER_OUTPUT,
            "OUTPUT_DIR": CONTAINER_OUTPUT,
            "FEATURE": feature.id,
            **rt.env,
        }
        if manifest.feature_env:
            # feature.id came from manifest.feature(), so it is necessarily one
            # of the declared ids — it can never be attacker-chosen.
            env[manifest.feature_env] = feature.id
        for k, v in env.items():
            cmd += ["-e", f"{k}={v}"]

        cmd.append(manifest.runtime.image or "")
        return cmd

    # ---- execution --------------------------------------------------------- #

    def run(
        self,
        manifest: PluginManifest,
        feature: FeatureSpec,
        workspace: JobWorkspace,
        input_file: Path,
    ) -> RunResult:
        validate_input(manifest, feature, input_file)

        timeout = manifest.effective_timeout(feature)
        container_name = f"fs_{manifest.id}_{workspace.job_id[:12]}"
        cmd = self.build_command(manifest, feature, workspace, input_file, container_name)

        stdout_path = workspace.log_dir / "stdout.log"
        stderr_path = workspace.log_dir / "stderr.log"

        log.info("running %s/%s: %s", manifest.id, feature.id,
                 " ".join(shlex.quote(c) for c in cmd))
        started = time.monotonic()
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout, check=False
            )
        except FileNotFoundError as exc:
            raise ToolUnavailableError(
                f"the '{self.docker_bin}' client is not available to the worker "
                f"({exc}). Install the Docker CLI in the worker image or point "
                "DOCKER_HOST at a reachable endpoint."
            ) from exc
        except subprocess.TimeoutExpired:
            self._kill(container_name)
            stderr_path.write_text(
                f"killed after exceeding the {timeout}s timeout\n", encoding="utf-8"
            )
            raise ToolTimeoutError(manifest.id, timeout) from None

        duration = time.monotonic() - started
        stdout_path.write_text(proc.stdout or "", encoding="utf-8", errors="replace")
        stderr_path.write_text(proc.stderr or "", encoding="utf-8", errors="replace")

        if proc.returncode != 0:
            if self._is_infrastructure_failure(proc.stderr or ""):
                raise ToolUnavailableError(
                    f"Docker could not run {manifest.id}: {(proc.stderr or '').strip()}"
                )
            raise ToolExecutionError(
                manifest.id, proc.returncode, proc.stderr or "", proc.stdout or ""
            )

        return RunResult(
            tool=manifest.id,
            feature=feature.id,
            exit_code=proc.returncode,
            output_dir=workspace.output_dir,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            duration_s=duration,
            command=cmd,
        )

    # ---- helpers ----------------------------------------------------------- #

    @staticmethod
    def _is_infrastructure_failure(stderr: str) -> bool:
        """Separate 'Docker is broken' (retryable) from 'the tool failed'."""
        markers = (
            "Cannot connect to the Docker daemon",
            "error during connect",
            "no such host",
            "permission denied while trying to connect",
            "manifest unknown",
            "pull access denied",
            "Unable to find image",
        )
        return any(m in stderr for m in markers)

    def _kill(self, container_name: str) -> None:
        try:
            subprocess.run(
                [self.docker_bin, "kill", container_name],
                capture_output=True, timeout=_KILL_TIMEOUT, check=False,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:  # pragma: no cover
            log.warning("could not kill container %s: %s", container_name, exc)


def default_runner_for(manifest: PluginManifest):
    from forensicstack.core.runners.native import NativeRunner

    if manifest.runtime.kind.value == "native":
        return NativeRunner()
    return DockerRunner()
