from src.utils import cleanup_session_directory
from src.config import BASE_DIR


def test_cleanup_session_directory(setup_session_directory):
    session_dir = setup_session_directory
    dense_dir = session_dir / "dense"
    
    # Run the cleanup function
    result = cleanup_session_directory(session_dir)
    
    # Verify results
    assert result is True
    assert dense_dir.exists()
    assert (dense_dir / "meshed-poisson.ply").exists()
    assert (dense_dir / "meshed-poisson.glb").exists()
    assert not (session_dir / "sfm").exists()


if __name__ == "__main__":
    test_dir = BASE_DIR / "app/output/6eaa040c-e608-40f7-b9e9-d8f21ddb213c"
    test_cleanup_session_directory(test_dir)