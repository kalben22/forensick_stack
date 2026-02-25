from celery import Celery
import os
from dotenv import load_dotenv
import tempfile

load_dotenv()

REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "Al0n3lyPssw0rd")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_DB = os.getenv("REDIS_CELERY_DB", "1")

if REDIS_PASSWORD and REDIS_PASSWORD.strip():
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

print(f" Connecting to Redis: redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")

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


@celery_app.task(name="forensicstack.analyze_memory_volatility")
def analyze_memory_volatility(artifact_id: int, plugin: str, output_format: str = "json"):
    """
    Analyze memory dump with Volatility 3
    
    Args:
        artifact_id: ID of the artifact (memory dump)
        plugin: Volatility plugin (e.g., "windows.pslist")
        output_format: Output format ("text", "json", "csv")
    """
    from forensicstack.core.database import SessionLocal
    from forensicstack.core import crud
    from forensicstack.plugins.memory.volatility_plugin import VolatilityPlugin
    
    db = SessionLocal()
    
    try:
        # Get artifact
        artifact = crud.get_artifact(db, artifact_id)
        if not artifact:
            return {"status": "error", "error": "Artifact not found"}
        
        # Pour l'instant, on suppose que le fichier est local
        # TODO: Download from MinIO
        dump_path = artifact.file_path
        
        print(f"🔬 Analyzing artifact {artifact_id} with {plugin}")
        
        # Run Volatility
        vol = VolatilityPlugin()
        result = vol.run(dump_path, plugin, output_format=output_format)
        
        # Create analysis record
        analysis_data = {
            "artifact_id": artifact_id,
            "module_name": f"volatility.{plugin}",
            "status": "completed" if result["status"] == "success" else "failed",
            "result_summary": result
        }
        crud.create_artifact(db, analysis_data)
        
        return result
        
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="forensicstack.test_task")
def test_task():
    """Simple test task"""
    print("Celery test task executed successfully!")
    return {"status": "ok", "message": "Test task completed"}
