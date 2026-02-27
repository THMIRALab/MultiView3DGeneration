import shutil
import traceback
import open3d as o3d
import trimesh
import cv2
import os
import numpy as np
import logging

from pathlib import Path
from skimage.metrics import structural_similarity as ssim
from src.config import BASE_DIR

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def convert_ply_to_glb(ply_path, glb_path):
    mesh = o3d.io.read_triangle_mesh(ply_path)
    mesh.compute_vertex_normals()  # optional but helps with rendering
    o3d.io.write_triangle_mesh(glb_path, mesh, write_ascii=False, compressed=False)


def convert_ply_to_glb_trimesh(ply_path, glb_path):
    mesh = trimesh.load(ply_path, force='mesh')

    rotation_matrix = trimesh.transformations.rotation_matrix(
        np.radians(-90), [1, 0, 0]
    )
    mesh.apply_transform(rotation_matrix)
    mesh.apply_translation(-mesh.centroid)

    mesh.export(glb_path)


def create_dir_structure(session_id, from_video=False):
    #images_dir = Path(f"app/input/{session_id}/images")
    images_dir = BASE_DIR / f"app/input/{session_id}/images"
    images_dir.mkdir(parents=True, exist_ok=True)

    #output_dir = Path(f"app/output/{session_id}")
    output_dir = BASE_DIR / f"app/output/{session_id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    #sfm_dir = Path(f"app/output/{session_id}/sfm")
    sfm_dir = BASE_DIR / f"app/output/{session_id}/sfm"
    sfm_dir.mkdir(parents=True, exist_ok=True)

    #dense_dir = Path(f"app/output/{session_id}/dense")
    dense_dir = BASE_DIR / f"app/output/{session_id}/dense"
    dense_dir.mkdir(parents=True, exist_ok=True) 

    if from_video:
        #video_dir = Path(f"app/input/{session_id}/video")
        video_dir = BASE_DIR / f"app/input/{session_id}/video"
        video_dir.mkdir(parents=True, exist_ok=True)

        return video_dir, images_dir, output_dir, sfm_dir, dense_dir

    return images_dir, output_dir, sfm_dir, dense_dir

def is_significant_change_frames(frame1, frame2, threshold=0.85):
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    score, _ = ssim(gray1, gray2, full=True)
    return score < threshold


def extract_frames_from_video(video_path, images_path, ssim_threshold=0.85):
    cap = cv2.VideoCapture(video_path)

    success, prev_frame = cap.read()
    if not success:
        raise RuntimeError("Failed to read the video")
    
    count = 0
    saved = 0
    while True:
        success, frame = cap.read()
        if not success:
            break
        '''if resize_width:
            frame = cv2.resize(frame, (resize_width, int(frame.shape[0] * resize_width / frame.shape[1])))
            prev_frame = cv2.resize(prev_frame, (resize_width, int(prev_frame.shape[0] * resize_width / prev_frame.shape[1])))'''

        if is_significant_change_frames(prev_frame, frame, threshold=ssim_threshold):
            filename = images_path / f"frame_{saved:04d}.png"
            cv2.imwrite(str(filename), frame)
            saved += 1
            prev_frame = frame.copy()
        count += 1

    cap.release()

    print(f"[INFO] Saved {saved} keyframes to {images_path}")


def extract_frames_one_per_second(video_path, images_path):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps == 0:
        raise ValueError("Failed to read FPS from video.")

    frame_interval = int(fps)  # 1 frame per second
    frame_idx = 0
    image_idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            filename = os.path.join(images_path, f"{image_idx:05d}.jpg")
            cv2.imwrite(filename, frame)
            image_idx += 1

        frame_idx += 1

    cap.release()
    print(f"Saved {image_idx} frames to {images_path}")


def cleanup_session_directory(session_dir) -> bool:
    """
    Delete unnecessary files from the session directory,
    keeping only the final 3D model files.
    
    Args:
        session_dir: The session directory to clean up.
        
    Returns:
        True if cleanup was successful, False otherwise
    """
    try:
        # Get the base output directory for this session
        session_dir = Path(session_dir)
        dense_dir = session_dir / "dense"
        
        # Ensure the directories exist
        if not session_dir.exists():
            logger.warning(f"Session directory not found: {session_dir}")
            return False
            
        # Find all model files to preserve
        models_to_preserve = []
        if dense_dir.exists():
            models_to_preserve = list(dense_dir.glob("meshed-poisson.*"))
            logger.info(f"Found {len(models_to_preserve)} model files to preserve")
        
        # Temporarily move model files to a safe location
        temp_dir = session_dir / ".temp"
        temp_dir.mkdir(exist_ok=True)
        
        for model in models_to_preserve:
            temp_path = temp_dir / model.name
            shutil.copy2(model, temp_path)
            logger.info(f"Preserved: {model.name}")
        
        # Delete all content except .temp directory
        for item in session_dir.iterdir():
            if item != temp_dir:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
        
        # Recreate dense directory
        dense_dir.mkdir(exist_ok=True)
        
        # Move preserved files back
        for model in temp_dir.iterdir():
            dest = dense_dir / model.name
            shutil.copy2(model, dest)
        
        # Delete temp directory
        shutil.rmtree(temp_dir)
        
        logger.info(f"Cleaned up session directory: {session_dir}")
        return True
        
    except Exception as e:
        logger.error(f"Error cleaning up session directory: {str(e)}")
        traceback.print_exc()
        return False


