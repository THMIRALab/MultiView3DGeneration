import os
import subprocess
from celery import Celery
from pathlib import Path
from src.colmap import run_reconstruction_pipeline_multiview
from src.utils import convert_ply_to_glb_trimesh, cleanup_session_directory
import traceback
import logging
import sys
import multiprocessing as mp

mp.set_start_method("spawn", force=True)

# Get Redis connection details from environment variables with defaults
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")
REDIS_DB = os.environ.get("REDIS_DB", "0")

REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

app = Celery(
    "tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

@app.task(bind=True)
def run_reconstruction_task(self, session_id: str, images_dir: str, output_dir: str, sfm_dir: str, dense_dir: str):
    try:
        logger.info(f"[{session_id}] Starting 3D reconstruction...")

        mesh_path, mesh_path_glb = run_reconstruction_pipeline_multiview(
            Path(images_dir),
            Path(output_dir) / "database.db",
            Path(sfm_dir),
            Path(dense_dir)
        )

        convert_ply_to_glb_trimesh(mesh_path, mesh_path_glb)
        logger.info(f"[{session_id}] 3D in GLB completed successfully.")

        cleanup_session_directory(output_dir)

        logger.info(f"[{session_id}] Task completed.")
        return {"status": "done"}
    
    except Exception as e:
        logger.error(f"[{session_id}] Task failed: {str(e)}")
        
        output_dir_path = Path(output_dir)
        error_file = output_dir_path / "error.log"
        
        with open(error_file, "w") as f:
            f.write(f"Error: {str(e)}\n")
            f.write(traceback.format_exc())
            
        return False
    
    '''except subprocess.CalledProcessError as e:
        logger.error(f"[{session_id}] Subprocess error: {e}")
        return {"status": "error", "message": str(e), "session_id": session_id}

    except Exception as e:
        logger.error(f"[{session_id}] Error: {e}")
        traceback.print_exc()
        raise self.retry(exc=e, countdown=10, max_retries=3)'''
