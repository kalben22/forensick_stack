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

print(f"🔗 Connecting to Redis: redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")

celery_app = Celery(
    "forensicstack",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)

# ============================================================
# VOLATILITY TASKS
# ============================================================

@celery_app.task(name="forensicstack.analyze_memory_volatility")
def analyze_memory_volatility(artifact_id: int, plugin: str, output_format: str = "json"):
    """
    Analyze memory dump with Volatility 3
    """
    from forensicstack.core.database import SessionLocal
    from forensicstack.core import crud
    from forensicstack.plugins.memory.volatility import VolatilityPlugin
    
    db = SessionLocal()
    
    try:
        artifact = crud.get_artifact(db, artifact_id)
        if not artifact:
            return {"status": "error", "error": "Artifact not found"}
        
        dump_path = artifact.file_path
        
        print(f"Analyzing artifact {artifact_id} with {plugin}")
        
        vol = VolatilityPlugin()
        result = vol.run(dump_path, plugin, output_format=output_format)
        
        # Create analysis record
        analysis_data = {
            "artifact_id": artifact_id,
            "module_name": f"volatility.{plugin}",
            "status": "completed" if result["status"] == "success" else "failed",
            "result_summary": result
        }
        # crud.create_analysis(db, analysis_data)  # TODO: Implement create_analysis
        
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
    """
    Scan artifact with YARA rules
    """
    from forensicstack.core.database import SessionLocal
    from forensicstack.core import crud
    from forensicstack.plugins.yara.scanner import YaraPlugin
    
    db = SessionLocal()
    
    try:
        artifact = crud.get_artifact(db, artifact_id)
        if not artifact:
            return {"status": "error", "error": "Artifact not found"}
        
        file_path = artifact.file_path
        
        print(f"🔍 Scanning artifact {artifact_id} with YARA")
        
        yara = YaraPlugin()
        result = yara.scan_file(file_path, rules_path)
        
        # Create analysis record
        analysis_data = {
            "artifact_id": artifact_id,
            "module_name": f"yara.scan",
            "status": "completed" if result["status"] == "success" else "failed",
            "result_summary": result
        }
        # crud.create_analysis(db, analysis_data)
        
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
    """
    Analyze disk image with TSK
    
    Args:
        action: "partitions" or "files"
    """
    from forensicstack.core.database import SessionLocal
    from forensicstack.core import crud
    from forensicstack.plugins.disk.tsk import TSKPlugin
    
    db = SessionLocal()
    
    try:
        artifact = crud.get_artifact(db, artifact_id)
        if not artifact:
            return {"status": "error", "error": "Artifact not found"}
        
        image_path = artifact.file_path
        
        print(f"💿 Analyzing disk image {artifact_id} - action: {action}")
        
        tsk = TSKPlugin()
        
        if action == "partitions":
            result = tsk.list_partitions(image_path)
        elif action == "files":
            result = tsk.list_files(image_path, partition_offset)
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}
        
        # Create analysis record
        analysis_data = {
            "artifact_id": artifact_id,
            "module_name": f"tsk.{action}",
            "status": "completed" if result["status"] == "success" else "failed",
            "result_summary": result
        }
        # crud.create_analysis(db, analysis_data)
        
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
    """
    Generate timeline with Plaso
    """
    from forensicstack.core.database import SessionLocal
    from forensicstack.core import crud
    from forensicstack.plugins.timeline.plaso import PlasoPlugin
    
    db = SessionLocal()
    
    try:
        artifact = crud.get_artifact(db, artifact_id)
        if not artifact:
            return {"status": "error", "error": "Artifact not found"}
        
        source_path = artifact.file_path
        
        print(f"⏱️  Generating timeline for artifact {artifact_id}")
        
        plaso = PlasoPlugin()
        result = plaso.create_timeline(source_path, output_file)
        
        # Create analysis record
        analysis_data = {
            "artifact_id": artifact_id,
            "module_name": "plaso.timeline",
            "status": "completed" if result["status"] == "success" else "failed",
            "result_summary": result
        }
        # crud.create_analysis(db, analysis_data)
        
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
    """Simple test task"""
    print("Celery test task executed successfully!")
    return {"status": "ok", "message": "Test task completed"}


if __name__ == "__main__":
    print("Starting Celery worker...")
