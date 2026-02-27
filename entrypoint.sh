#!/bin/bash
set -e

# Activate the conda environment
source /workspace/miniconda3/etc/profile.d/conda.sh
conda activate multiview-enigma

# Start Celery in the background
celery -A src.worker.app worker --loglevel=info --concurrency=1 --pool=solo &

# Start FastAPI server in foreground
exec uvicorn src.main:app --host 0.0.0.0 --port 8002 --log-level debug --access-log
