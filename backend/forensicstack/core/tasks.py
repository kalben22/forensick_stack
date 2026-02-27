from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "Al0n3lyPssw0rd")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_DB = os.getenv("REDIS_CELERY_DB", "1")

if REDIS_PASSWORD and REDIS_PASSWORD.strip():
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

print(f"[Celery] Connecting to Redis: redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")

celery_app = Celery(
    "forensicstack",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)


# ── ChromaDB helper ────────────────────────────────────────────────────────────

def _index_in_chroma(findings: list, artifact_id: int, case_id: int):
    """
    Vectorise and store findings in ChromaDB for semantic search.
    Silently skips if ChromaDB is unavailable — never crashes an analysis.
    """
    try:
        from forensicstack.core.chroma_service import get_chroma_service
        get_chroma_service().add_findings(findings, artifact_id=artifact_id, case_id=case_id)
    except Exception as e:
        print(f"[ChromaDB] Skipped indexing (artifact {artifact_id}): {e}")


# ============================================================
# VOLATILITY TASKS
# ============================================================

@celery_app.task(name="forensicstack.analyze_memory_volatility")
def analyze_memory_volatility(artifact_id: int, plugin: str, output_format: str = "json"):
    """Analyze memory dump with Volatility 3"""
    from forensicstack.core.database import SessionLocal
    from forensicstack.core import crud
    from forensicstack.plugins.memory.volatility import VolatilityPlugin
    from forensicstack.core.normalizers.volatility_normalizer import VolatilityNormalizer

    db = SessionLocal()
    try:
        artifact = crud.get_artifact(db, artifact_id)
        if not artifact:
            return {"status": "error", "error": "Artifact not found"}

        print(f"[Volatility] Analyzing artifact {artifact_id} with {plugin}")

        vol = VolatilityPlugin()
        result = vol.run(artifact.file_path, plugin, output_format=output_format)

        analysis_status = "completed" if result["status"] == "success" else "failed"
        crud.create_analysis(db, {
            "artifact_id": artifact_id,
            "module_name": f"volatility.{plugin}",
            "status": analysis_status,
            "result_summary": result,
        })

        # Index in ChromaDB if successful
        if result["status"] == "success":
            import tempfile, json
            with tempfile.TemporaryDirectory() as tmp:
                out_file = os.path.join(tmp, f"{plugin}.json")
                json_result = vol.run(artifact.file_path, plugin, output_format="json", output_file=tmp)
                try:
                    findings = VolatilityNormalizer().normalize(tmp)
                    _index_in_chroma(findings, artifact_id=artifact_id, case_id=artifact.case_id)
                except Exception:
                    pass  # Normalizer/chroma failure must not crash task

        return result

    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


# ============================================================
# YARA TASKS
# ============================================================

@celery_app.task(name="forensicstack.scan_yara")
def scan_yara(artifact_id: int, rules_path: str):
    """Scan artifact with YARA rules"""
    from forensicstack.core.database import SessionLocal
    from forensicstack.core import crud
    from forensicstack.plugins.yara.scanner import YaraPlugin
    from forensicstack.core.models.finding_models import Finding

    db = SessionLocal()
    try:
        artifact = crud.get_artifact(db, artifact_id)
        if not artifact:
            return {"status": "error", "error": "Artifact not found"}

        print(f"[YARA] Scanning artifact {artifact_id}")

        yara_plugin = YaraPlugin()
        result = yara_plugin.scan_file(artifact.file_path, rules_path)

        crud.create_analysis(db, {
            "artifact_id": artifact_id,
            "module_name": "yara.scan",
            "status": "completed" if result["status"] == "success" else "failed",
            "result_summary": result,
        })

        # Index matches in ChromaDB
        if result["status"] == "success" and result.get("matches"):
            findings = [
                Finding(
                    tool="yara",
                    artifact_type="malware_match",
                    source=artifact.file_path,
                    timestamp=None,
                    data=match,
                    confidence=0.9,
                )
                for match in result["matches"]
            ]
            _index_in_chroma(findings, artifact_id=artifact_id, case_id=artifact.case_id)

        return result

    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


# ============================================================
# TSK TASKS
# ============================================================

@celery_app.task(name="forensicstack.analyze_disk_tsk")
def analyze_disk_tsk(artifact_id: int, action: str, partition_offset: int = 0):
    """Analyze disk image with The Sleuth Kit (TSK)"""
    from forensicstack.core.database import SessionLocal
    from forensicstack.core import crud
    from forensicstack.plugins.disk.tsk import TSKPlugin
    from forensicstack.core.models.finding_models import Finding

    db = SessionLocal()
    try:
        artifact = crud.get_artifact(db, artifact_id)
        if not artifact:
            return {"status": "error", "error": "Artifact not found"}

        print(f"[TSK] Analyzing disk image {artifact_id} - action: {action}")

        tsk = TSKPlugin()
        if action == "partitions":
            result = tsk.list_partitions(artifact.file_path)
        elif action == "files":
            result = tsk.list_files(artifact.file_path, partition_offset)
        elif action == "timeline":
            result = tsk.generate_timeline(artifact.file_path)
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}

        crud.create_analysis(db, {
            "artifact_id": artifact_id,
            "module_name": f"tsk.{action}",
            "status": "completed" if result["status"] == "success" else "failed",
            "result_summary": result,
        })

        # Index in ChromaDB
        if result["status"] == "success":
            items = result.get("files") or result.get("partitions") or result.get("events") or []
            findings = [
                Finding(
                    tool="tsk",
                    artifact_type=action,
                    source=artifact.file_path,
                    timestamp=item.get("date"),
                    data=item,
                    confidence=0.7,
                )
                for item in items
            ]
            _index_in_chroma(findings, artifact_id=artifact_id, case_id=artifact.case_id)

        return result

    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


# ============================================================
# PLASO TASKS
# ============================================================

@celery_app.task(name="forensicstack.generate_timeline_plaso")
def generate_timeline_plaso(artifact_id: int, output_file: str):
    """Generate forensic super-timeline with Plaso (log2timeline)"""
    from forensicstack.core.database import SessionLocal
    from forensicstack.core import crud
    from forensicstack.plugins.timeline.plaso import PlasoPlugin

    db = SessionLocal()
    try:
        artifact = crud.get_artifact(db, artifact_id)
        if not artifact:
            return {"status": "error", "error": "Artifact not found"}

        print(f"[Plaso] Generating timeline for artifact {artifact_id}")

        plaso = PlasoPlugin()
        result = plaso.create_timeline(artifact.file_path, output_file)

        crud.create_analysis(db, {
            "artifact_id": artifact_id,
            "module_name": "plaso.timeline",
            "status": "completed" if result["status"] == "success" else "failed",
            "result_summary": result,
        })

        return result

    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


# ============================================================
# TEST TASK
# ============================================================

@celery_app.task(name="forensicstack.test_task")
def test_task():
    """Simple connectivity test task"""
    print("[Celery] Test task executed successfully!")
    return {"status": "ok", "message": "Test task completed"}


if __name__ == "__main__":
    print("[Celery] Starting worker...")
