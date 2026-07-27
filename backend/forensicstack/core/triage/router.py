"""
Automatic analysis planning.

This is the piece that turns "upload a file, any file, and the platform works
out what to do with it" into something concrete: identification produces an
:class:`ArtifactIdentity`, and this module turns that identity into an ordered
list of (tool, feature) jobs to run — using only what the plugin manifests
declare, so a newly dropped-in plugin joins the automation with no code change.

Two rules keep it honest:

* **Never silently drop work.**  Anything considered and rejected lands in
  ``plan.skipped`` with a reason.  A truncated plan that looks complete is worse
  than no plan.
* **Low confidence changes the plan, it doesn't stop it.**  An unidentified blob
  still gets the generic path (hashing, strings, carving, YARA) rather than a
  guessed tool that fails forty minutes later.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from forensicstack.core.plugins.manifest import FeatureSpec, PluginManifest
from forensicstack.core.plugins.registry import PluginRegistry, registry as default_registry
from forensicstack.core.triage.identify import ArtifactIdentity
from forensicstack.core.triage.kinds import ArtifactKind, KindFamily

log = logging.getLogger(__name__)

#: Below this, we only run tools that accept anything.
CONFIDENCE_FLOOR = 0.45

#: Hard cap on auto-scheduled jobs per upload, so one file cannot saturate the
#: worker pool. Anything beyond the cap is reported, never hidden.
MAX_AUTO_STEPS = 12


@dataclass(frozen=True)
class PlannedStep:
    tool: str
    feature: str
    priority: int
    reason: str
    stage: int = 1

    def key(self) -> tuple[str, str]:
        return (self.tool, self.feature)


@dataclass
class AnalysisPlan:
    identity: ArtifactIdentity
    steps: list[PlannedStep] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.steps

    def to_dict(self) -> dict:
        return {
            "identity": self.identity.to_dict(),
            "steps": [
                {
                    "tool": s.tool,
                    "feature": s.feature,
                    "priority": s.priority,
                    "stage": s.stage,
                    "reason": s.reason,
                }
                for s in self.steps
            ],
            "skipped": [{"target": t, "reason": r} for t, r in self.skipped],
            "notes": self.notes,
        }


def _os_compatible(feature: FeatureSpec, identity: ArtifactIdentity) -> tuple[bool, str]:
    if not feature.os_hint:
        return True, ""
    if not identity.os_hint:
        # Identification could not tell; run it anyway rather than silently
        # dropping the only plugin that handles this artifact.
        return True, ""
    if feature.os_hint == identity.os_hint:
        return True, ""
    return False, (
        f"feature targets {feature.os_hint} but the artifact looks like "
        f"{identity.os_hint}"
    )


def _size_compatible(
    manifest: PluginManifest, feature: FeatureSpec, identity: ArtifactIdentity
) -> tuple[bool, str]:
    accepts = manifest.accepts_for(feature)
    if identity.size > accepts.max_size_bytes:
        return False, f"artifact is larger than the declared maximum {accepts.max_size}"
    if identity.size < accepts.min_size_bytes:
        return False, f"artifact is smaller than the declared minimum {accepts.min_size}"
    return True, ""


def _accepts_anything(manifest: PluginManifest, feature: FeatureSpec) -> bool:
    """A plugin with no declared kinds is generic (triage, hashing, strings)."""
    return not manifest.accepts_for(feature).kinds


def _order(steps: list[PlannedStep], manifests: dict[str, PluginManifest]) -> list[PlannedStep]:
    """Sort by stage, then priority, honouring intra-plugin ``requires``."""
    steps = sorted(steps, key=lambda s: (s.stage, s.priority, s.tool, s.feature))
    ordered: list[PlannedStep] = []
    pending = list(steps)
    placed: set[tuple[str, str]] = set()
    guard = 0
    while pending and guard <= len(steps) + 1:
        guard += 1
        progressed = False
        for step in list(pending):
            manifest = manifests.get(step.tool)
            deps = []
            if manifest:
                try:
                    deps = manifest.feature(step.feature).requires
                except KeyError:  # pragma: no cover - defensive
                    deps = []
            unmet = [
                d for d in deps
                if (step.tool, d) not in placed
                and any(p.key() == (step.tool, d) for p in pending)
            ]
            if unmet:
                continue
            ordered.append(step)
            placed.add(step.key())
            pending.remove(step)
            progressed = True
        if not progressed:
            # Cycle in `requires` — the manifest validator forbids unknown deps
            # but not cycles. Emit the rest in priority order rather than hang.
            ordered.extend(pending)
            break
    return ordered


def plan_for(
    identity: ArtifactIdentity,
    *,
    reg: PluginRegistry | None = None,
    max_steps: int = MAX_AUTO_STEPS,
    include_manual: bool = False,
) -> AnalysisPlan:
    """Build the automatic analysis plan for an identified artifact.

    ``include_manual=True`` also returns features that are *applicable* but not
    marked ``auto`` — used to populate the "you could also run…" list in the UI
    instead of showing the analyst every tool in the catalogue.
    """
    reg = reg or default_registry
    plan = AnalysisPlan(identity=identity)
    manifests: dict[str, PluginManifest] = {}

    if identity.kind is ArtifactKind.UNKNOWN or identity.confidence < CONFIDENCE_FLOOR:
        plan.notes.append(
            f"artifact not confidently identified (kind={identity.kind.value}, "
            f"confidence={identity.confidence:.2f}) — restricting the automatic "
            "plan to tools that accept any input"
        )
        generic_only = True
    else:
        generic_only = False

    candidates: list[PlannedStep] = []
    for manifest in reg:
        manifests[manifest.id] = manifest
        for feature in manifest.features:
            target = f"{manifest.id}/{feature.id}"
            generic = _accepts_anything(manifest, feature)
            accepts = manifest.accepts_for(feature)

            if not generic and identity.kind not in accepts.kinds:
                continue  # simply not applicable — not worth reporting
            if generic_only and not generic:
                plan.skipped.append((target, "artifact kind is not confidently known"))
                continue
            if not feature.auto and not include_manual:
                plan.skipped.append((target, "feature is not marked auto in its manifest"))
                continue

            ok, why = _os_compatible(feature, identity)
            if not ok:
                plan.skipped.append((target, why))
                continue
            ok, why = _size_compatible(manifest, feature, identity)
            if not ok:
                plan.skipped.append((target, why))
                continue

            reason = (
                "accepts any input" if generic
                else f"declares support for {identity.kind.value}"
            )
            if feature.os_hint and identity.os_hint:
                reason += f"; OS matches ({identity.os_hint})"
            candidates.append(
                PlannedStep(
                    tool=manifest.id,
                    feature=feature.id,
                    priority=feature.auto_priority,
                    reason=reason,
                    stage=0 if generic else 1,
                )
            )

    ordered = _order(candidates, manifests)

    if len(ordered) > max_steps:
        dropped = ordered[max_steps:]
        ordered = ordered[:max_steps]
        for step in dropped:
            plan.skipped.append(
                (f"{step.tool}/{step.feature}",
                 f"automatic plan capped at {max_steps} steps — run it manually")
            )
        plan.notes.append(
            f"{len(dropped)} applicable step(s) were dropped by the {max_steps}-step cap"
        )

    plan.steps = ordered
    if not plan.steps:
        plan.notes.append(
            "no plugin declared support for this artifact — install one, or run "
            "a tool manually"
        )
    return plan


def suggest_tools(identity: ArtifactIdentity, *, reg: PluginRegistry | None = None) -> list[dict]:
    """Everything applicable, auto or not — for the UI's suggestion list."""
    reg = reg or default_registry
    out: list[dict] = []
    for manifest in reg:
        for feature in manifest.features:
            accepts = manifest.accepts_for(feature)
            if accepts.kinds and identity.kind not in accepts.kinds:
                continue
            ok_os, _ = _os_compatible(feature, identity)
            ok_size, _ = _size_compatible(manifest, feature, identity)
            out.append({
                "tool": manifest.id,
                "tool_name": manifest.name,
                "feature": feature.id,
                "label": feature.label,
                "description": feature.description,
                "auto": feature.auto,
                "recommended": bool(ok_os and ok_size),
                "generic": not accepts.kinds,
            })
    out.sort(key=lambda d: (not d["recommended"], not d["auto"], d["tool"], d["feature"]))
    return out


FAMILY_ADVICE: dict[KindFamily, str] = {
    KindFamily.MEMORY: "Start with process listing, then network connections, "
                       "then injected-code detection.",
    KindFamily.DISK: "Enumerate partitions and the filesystem first, then build "
                     "a timeline before carving.",
    KindFamily.MOBILE: "Run the full extraction; it produces messages, calls, "
                       "locations and app data in one pass.",
    KindFamily.NETWORK: "Extract conversations and DNS first — they usually "
                        "answer the question on their own.",
    KindFamily.ARCHIVE: "Expand first: the interesting artifact is almost always "
                        "a member, not the container.",
    KindFamily.MEDIA: "Check metadata, then look for appended or embedded data.",
    KindFamily.OPAQUE: "High entropy — treat as encrypted or packed. Carve for "
                       "embedded structures before assuming it is noise.",
}
