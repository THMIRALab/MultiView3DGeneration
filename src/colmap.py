import shutil
import urllib.request
import zipfile
import enlighten
import pycolmap
import os
import subprocess

from pycolmap import logging
from pathlib import Path

os.environ["OMP_NUM_THREADS"] = "4"  # Limit threads globally
COLMAP_BIN = shutil.which("colmap")  # Automatically resolves the full path


def run_reconstruction_pipeline_multiview(images_dir, database_path, sfm_dir, dense_dir):
    print(f"ColmapBIN: {COLMAP_BIN}")
    pycolmap.set_random_seed(0)
    pycolmap.extract_features(database_path, images_dir)
    pycolmap.match_exhaustive(database_path)

    pycolmap.incremental_mapping(database_path, images_dir, sfm_dir)

    subprocess.run([
        COLMAP_BIN, "image_undistorter",
        "--image_path", str(images_dir),
        "--input_path", str(sfm_dir / "0"),
        "--output_path", str(dense_dir),
        "--output_type", "COLMAP"
    ], check=True)

    subprocess.run([
        COLMAP_BIN, "patch_match_stereo",
        "--workspace_path", str(dense_dir),
        "--workspace_format", "COLMAP",
        "--PatchMatchStereo.geom_consistency", "true"
    ], check=True)

    subprocess.run([
        COLMAP_BIN, "stereo_fusion",
        "--workspace_path", str(dense_dir),
        "--workspace_format", "COLMAP",
        "--input_type", "geometric",
        "--output_path", str(dense_dir / "fused.ply")
    ], check=True)

    mesh_path = dense_dir / "meshed-poisson.ply"
    subprocess.run([
        COLMAP_BIN, "poisson_mesher",
        "--input_path", str(dense_dir / "fused.ply"),
        "--output_path", str(mesh_path)
    ], check=True)

    mesh_path_glb = dense_dir / "meshed-poisson.glb"

    return mesh_path, mesh_path_glb