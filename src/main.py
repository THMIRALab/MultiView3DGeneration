from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, status
from fastapi.responses import FileResponse, JSONResponse
from src.colmap import run_reconstruction_pipeline_multiview
from pathlib import Path
from src.utils import convert_ply_to_glb, create_dir_structure, extract_frames_from_video, extract_frames_one_per_second, convert_ply_to_glb_trimesh
from src.config import BASE_DIR
from typing import Tuple, List, Dict, Any, Optional
from src.worker import run_reconstruction_task

import traceback
import logging
import uuid
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MultiView-ENIGMA API",
    description="API for 3D reconstruction from multi-view images or video",
    version="1.0.0",
    debug=True
)

# Common response models
SUCCESS_RESPONSE = Dict[str, Any]
ERROR_RESPONSE = Dict[str, str]


async def save_uploaded_file(file: UploadFile, destination: Path) -> None:
    """Save an uploaded file to the specified destination."""

    with open(destination, "wb") as f:
        f.write(await file.read())

    
async def save_uploaded_files(files: List[UploadFile], directory: Path) -> None:
    """Save multiple uploaded files to a directory."""
    for file in files:
        dest = directory / file.filename
        await save_uploaded_file(file, dest)


'''def run_reconstruction_background_task(
    session_id: str,
    images_dir: Path,
    output_dir: Path,
    sfm_dir: Path,
    dense_dir: Path
) -> None:
    """Execute 3D reconstruction as a background task."""
    try:
        # Run reconstruction pipeline
        logger.info(f"[{session_id}] Starting 3D reconstruction...")
        mesh_path, mesh_path_glb = run_reconstruction_pipeline_multiview(
            images_dir,
            output_dir / "database.db",
            sfm_dir,
            dense_dir
        )
        logger.info(f"[{session_id}] Multi-view reconstruction completed!")

        # Convert to GLB format
        convert_ply_to_glb_trimesh(mesh_path, mesh_path_glb)
        logger.info(f"[{session_id}] Converted PLY to GLB!")
    except Exception as e:
        logger.error(f"[{session_id}] Background task failed: {str(e)}")
        traceback.print_exc()
'''

def get_model_path(session_id: str, file_type: str = "glb") -> Tuple[Path, bool]:
    """Get the path to the GLB model and whether it exists."""
    if file_type.lower() not in ["ply", "glb"]:
        raise ValueError("File type must be either 'ply' or 'glb'")
    
    file_name = f"meshed-poisson.{file_type.lower()}"
    mesh_path = BASE_DIR / f"app/output/{session_id}/dense" / file_name
    
    return mesh_path, mesh_path.exists()


'''@app.post("/multiview_to_3d")
async def multiview_to_3d(background_tasks: BackgroundTasks, files: list[UploadFile] = File(...)):
    try:
        session_id = str(uuid.uuid4())
        images_dir, output_dir, sfm_dir, dense_dir = create_dir_structure(session_id)

        for file in files:
            dest = images_dir / file.filename
            with open(dest, "wb") as f:
                f.write(await file.read())

        # Uncomment the following line if you want to load the files from a specific directory.
        #images_dir = Path(f"examples/small_object/")


        mesh_path, mesh_path_glb = run_reconstruction_pipeline_multiview(images_dir,
                                                                        output_dir / "database.db",
                                                                        sfm_dir,
                                                                        dense_dir)
        print("[INFO] Multi-view reconstruction completed!")

        #convert_ply_to_glb(mesh_path, mesh_path_glb)
        convert_ply_to_glb_trimesh(mesh_path, mesh_path_glb)
        print("[INFO] Converted PLY to GLB!")

        return FileResponse(
            mesh_path_glb,
            filename="meshed-poisson.glb",
            media_type="application/octet-stream"
        )
    except Exception as e:
        print("Exception:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
'''
@app.post("/multiview_to_3d", response_model=Dict[str, Any], status_code=status.HTTP_202_ACCEPTED)
async def multiview_to_3d(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
) -> JSONResponse:
    """
    Create a 3D model from multiple images.
    
    Uploads images are processed in the background to create a 3D model.
    """
    try:
        # Generate session ID and create directory structure
        session_id = str(uuid.uuid4())
        images_dir, output_dir, sfm_dir, dense_dir = create_dir_structure(session_id)
        
        # Save uploaded files
        await save_uploaded_files(files, images_dir)
        logger.info(f"[{session_id}] Saved {len(files)} images")
        
        # Schedule background task
        run_reconstruction_task.delay(
            session_id,
            str(images_dir),
            str(output_dir),
            str(sfm_dir),
            str(dense_dir)
        )
        
        return JSONResponse({
            "message": "Reconstruction started",
            "session_id": session_id,
            "status_url": f"/status/{session_id}"
        })
        
    except Exception as e:
        logger.error(f"Error in multiview_to_3d: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process images: {str(e)}"
        )

'''@app.post("/video_to_3d")
async def video_to_3d(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    session_id = str(uuid.uuid4())

    video_dir, images_dir, output_dir, sfm_dir, dense_dir = create_dir_structure(session_id, from_video=True)

    video_path = video_dir / "input.mp4"
    with open(video_path, "wb") as f:
        f.write(await file.read())

    extract_frames_one_per_second(video_path, images_dir)
    print("[INFO] Extracted frames from video!")

    mesh_path, mesh_path_glb = run_reconstruction_pipeline_multiview(images_dir,
                                                                     output_dir / "database.db",
                                                                     sfm_dir,
                                                                     dense_dir)
    print("[INFO] Multi-view reconstruction completed!")

    #convert_ply_to_glb(mesh_path, mesh_path_glb)
    convert_ply_to_glb_trimesh(mesh_path, mesh_path_glb)
    print("[INFO] Converted PLY to GLB!")
    
    return FileResponse(
        mesh_path_glb,
        filename="meshed-poisson.glb",
        media_type="application/octet-stream"
    )
'''
@app.post("/video_to_3d", response_model=Dict[str, Any], status_code=status.HTTP_202_ACCEPTED)
async def video_to_3d(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> JSONResponse:
    """
    Create a 3D model from a video.
    
    Video is processed by extracting frames and then creating a 3D model in the background.
    """
    try:
        # Generate session ID and create directory structure
        session_id = str(uuid.uuid4())
        video_dir, images_dir, output_dir, sfm_dir, dense_dir = create_dir_structure(
            session_id, from_video=True
        )
        
        # Save uploaded video
        video_path = video_dir / "input.mp4"
        await save_uploaded_file(file, video_path)
        logger.info(f"[{session_id}] Saved video file")
        
        # Extract frames
        extract_frames_one_per_second(video_path, images_dir)
        logger.info(f"[{session_id}] Extracted frames from video")
        
        run_reconstruction_task.delay(
            session_id,
            str(images_dir),
            str(output_dir),
            str(sfm_dir),
            str(dense_dir)
        )
        
        return JSONResponse({
            "message": "Video reconstruction started",
            "session_id": session_id,
            "status_url": f"/status/{session_id}"
        })
        
    except Exception as e:
        logger.error(f"Error in video_to_3d: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process video: {str(e)}"
        )


@app.get("/status/{session_id}", response_model=Dict[str, Any])
async def check_status(session_id: str) -> Dict[str, Any]:
    """
    Check the status of a reconstruction job.
    
    Returns:
    - "ready" if models are available
    - "processing" if job is in progress
    - "not_found" if session doesn't exist
    - "error" if reconstruction failed
    """

    session_dir = BASE_DIR / f"app/output/{session_id}"
    if not session_dir.exists():
        return {
            "status": "not_found",
            "message": "No reconstruction job found with this session ID."
        }
    
    error_file = session_dir / "error.log"
    if error_file.exists():
        return {
            "status": "error",
            "message": "Reconstruction failed. Please, follow the instructions to images/videos requirements."
        }

    _, glb_exists = get_model_path(session_id, "glb")
    
    if glb_exists:
        _, ply_exists = get_model_path(session_id, "ply")
        
        response = {
            "status": "ready",
            "download_urls": {
                "glb": f"/download/{session_id}?file_type=glb"
            }
        }
        
        if ply_exists:
            response["download_urls"]["ply"] = f"/download/{session_id}?file_type=ply"
            
        return response
    else:
        return {"status": "processing"}
    

@app.get("/download/{session_id}", response_class=FileResponse)
async def download_file(
    session_id: str, 
    file_type: str = "glb"
) -> FileResponse:
    """
    Download the generated 3D model.
    
    Args:
        session_id: The session identifier
        file_type: The file type to download, either "ply" or "glb"
        
    Returns:
        The requested 3D model file
    """
    if file_type.lower() not in ["ply", "glb"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File type must be either 'ply' or 'glb'"
        )
        
    mesh_path, exists = get_model_path(session_id, file_type.lower())
    
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not ready or does not exist yet for format: {file_type}"
        )

    # Set correct file name and media type
    filename = f"meshed-poisson.{file_type.lower()}"
    media_type = "application/octet-stream"
    if file_type.lower() == "glb":
        media_type = "model/gltf-binary"
    elif file_type.lower() == "ply":
        media_type = "application/octet-stream"

    return FileResponse(
        mesh_path,
        filename=filename,
        media_type=media_type
    )