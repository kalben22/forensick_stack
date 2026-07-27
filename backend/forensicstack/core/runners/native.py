"""
Native (host-process) runner, for tools that cannot be containerised —
in practice the Eric Zimmerman suite on Windows.

It obeys the *same* contract as :class:`DockerRunner`: non-zero exit raises
:class:`ToolExecutionError`, timeouts raise :class:`ToolTimeoutError`, and
stderr is always written to ``logs/stderr.log``.

The previous implementation ran with ``check=False`` and never inspected
``returncode``, so a crashed tool yielded an empty output directory, the
normalizer returned ``[]``, and the job was reported ``completed`` with zero
findings — indistinguishable from a clean run that genuinely found nothing.
Its stderr went to the worker's stdout and nowhere else, and the normalizer's
``*.log`` fallback could never fire because nothing wrote a log file.

There is no sandbox here. A native tool runs with the worker's privileges, so
this runner refuses to start unless explicitly enabled.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

from forensicstack.core.plugins.manifest import FeatureSpec, PluginManifest
from forensicstack.core.runners.base import (
    JobWorkspace,
    RunResult,
    ToolExecutionError,
    ToolTimeoutError,
    ToolUnavailableError,
    validate_input,
)

log = logging.getLogger(__name__)

_ENABLE_FLAG = "FORENSICSTACK_ALLOW_NATIVE_TOOLS"


class NativeRunner:
    kind = "native"

    def run(
        self,
        manifest: PluginManifest,
        feature: FeatureSpec,
        workspace: JobWorkspace,
        input_file: Path,
    ) -> RunResult:
        if os.getenv(_ENABLE_FLAG, "").lower() not in ("1", "true", "yes"):
            raise ToolUnavailableError(
                f"plugin {manifest.id!r} needs the native runner, which executes "
                f"tools with the worker's own privileges and no sandbox. Set "
                f"{_ENABLE_FLAG}=1 to allow it."
            )
        validate_input(manifest, feature, input_file)

        exe = self._resolve(manifest)
        timeout = manifest.effective_timeout(feature)

        cmd = [str(exe), *self._args(manifest, feature, workspace, input_file)]
        env = {
            **os.environ,
            "INPUT_PATH": str(input_file),
            "OUTPUT_PATH": str(workspace.output_dir),
            "FEATURE": feature.id,
            **manifest.runtime.env,
        }
        if manifest.feature_env:
            env[manifest.feature_env] = feature.id

        stdout_path = workspace.log_dir / "stdout.log"
        stderr_path = workspace.log_dir / "stderr.log"

        log.info("running native %s/%s: %s", manifest.id, feature.id, cmd)
        started = time.monotonic()
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
                check=False, env=env, cwd=str(workspace.output_dir),
            )
        except FileNotFoundError as exc:
            raise ToolUnavailableError(f"{manifest.id}: executable not found: {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            stderr_path.write_text(
                (exc.stderr or "") + f"\nkilled after {timeout}s\n",
                encoding="utf-8", errors="replace",
            )
            raise ToolTimeoutError(manifest.id, timeout) from None

        duration = time.monotonic() - started
        stdout_path.write_text(proc.stdout or "", encoding="utf-8", errors="replace")
        stderr_path.write_text(proc.stderr or "", encoding="utf-8", errors="replace")

        if proc.returncode != 0:
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
    def _resolve(manifest: PluginManifest) -> Path:
        exe = manifest.runtime.executable or ""
        if manifest.runtime.tool_dir_env:
            base = os.getenv(manifest.runtime.tool_dir_env, "").strip()
            if base:
                candidate = Path(base) / exe
                if candidate.exists():
                    return candidate
        found = shutil.which(exe)
        if found:
            return Path(found)
        candidate = Path(exe)
        if candidate.exists():
            return candidate
        raise ToolUnavailableError(
            f"{manifest.id}: cannot locate executable {exe!r}. Set "
            f"{manifest.runtime.tool_dir_env or 'PATH'} appropriately."
        )

    @staticmethod
    def _args(
        manifest: PluginManifest,
        feature: FeatureSpec,
        workspace: JobWorkspace,
        input_file: Path,
    ) -> list[str]:
        """Substitute placeholders declared in ``runtime.env['ARGS']``.

        Kept intentionally dumb: the argv is a list, never a shell string, and
        only three placeholders are recognised.
        """
        template = manifest.runtime.env.get("ARGS", "")
        if not template:
            return ["-f", str(input_file), "--csv", str(workspace.output_dir)]
        subs = {
            "{input}": str(input_file),
            "{output}": str(workspace.output_dir),
            "{feature}": feature.id,
        }
        args = []
        for token in template.split():
            for key, value in subs.items():
                token = token.replace(key, value)
            args.append(token)
        return args
