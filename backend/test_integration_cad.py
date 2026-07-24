import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import os
import shutil
from pathlib import Path

# Override database URL to a test sqlite database before importing app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_cae_local.db"
os.environ["MOCK_CAD_MODE"] = "true"  # Ensure mock mode is true to test regex/cascadio fallback behavior

from app.main import app
from app.config import settings
from app.database import init_db

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_test_db():
    db_file = Path("test_cae_local.db")
    if db_file.exists():
        try:
            db_file.unlink()
        except OSError:
            pass
            
    # Initialize database tables
    await init_db()
        
    yield
    
    # Clean up database
    if db_file.exists():
        try:
            db_file.unlink()
        except OSError:
            pass
    # Clean up test uploads directory
    test_storage = Path(settings.local_storage_path)
    if test_storage.exists() and "test" in str(test_storage):
        shutil.rmtree(test_storage, ignore_errors=True)

@pytest.mark.asyncio
async def test_cad_parsing_pipeline():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        
        # 1. Sign up/Log in guest user to get access token
        signup_res = await ac.post("/api/auth/signup", json={"username": "test_user_cad", "password": "test_password_cad"})
        assert signup_res.status_code in (200, 201, 400), f"Signup failed: {signup_res.text}"
        
        login_res = await ac.post("/api/auth/login", json={"username": "test_user_cad", "password": "test_password_cad"})
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Upload test_cube.stl (STL)
        stl_path = Path(__file__).parent / "test_cube.stl"
        with open(stl_path, "rb") as f:
            files = {"file": ("test_cube.stl", f.read(), "application/octet-stream")}
        upload_stl_res = await ac.post("/api/upload", files=files, headers=headers)
        assert upload_stl_res.status_code == 201, f"STL Upload failed: {upload_stl_res.text}"
        stl_data = upload_stl_res.json()
        assert stl_data["parsing_status"] == "success"
        stl_features = stl_data["geometry_features"]
        assert stl_features is not None
        assert abs(stl_features["volume"]) > 0
        
        # 3. Upload test_cube.step (STEP - parsed via cascadio or regex fallback)
        step_path = Path(__file__).parent / "test_cube.step"
        with open(step_path, "rb") as f:
            files = {"file": ("test_cube.step", f.read(), "application/octet-stream")}
        upload_step_res = await ac.post("/api/upload", files=files, headers=headers)
        assert upload_step_res.status_code == 201, f"STEP Upload failed: {upload_step_res.text}"
        step_data = upload_step_res.json()
        assert step_data["parsing_status"] == "success"
        step_features = step_data["geometry_features"]
        assert step_features is not None
        
        # 4. Upload test_assembly.step (STEP multi-body - verify different volume/bbox)
        assembly_path = Path(__file__).parent / "test_assembly.step"
        with open(assembly_path, "rb") as f:
            files = {"file": ("test_assembly.step", f.read(), "application/octet-stream")}
        upload_assembly_res = await ac.post("/api/upload", files=files, headers=headers)
        assert upload_assembly_res.status_code == 201, f"Assembly Upload failed: {upload_assembly_res.text}"
        assembly_data = upload_assembly_res.json()
        assert assembly_data["parsing_status"] == "success"
        assembly_features = assembly_data["geometry_features"]
        assert assembly_features is not None
        
        # Assert properties change per file and are not the placeholder box constants:
        # Placeholder box constants: volume=90000.0, area=22800.0, bbox=(100, 50, 30)
        assert stl_features["volume"] != 90000.0
        assert step_features["volume"] != 90000.0
        assert assembly_features["volume"] != 90000.0
        
        # Check that different files have different volumes
        assert stl_features["volume"] != step_features["volume"]
        assert step_features["volume"] != assembly_features["volume"]
        
        # Check that bounding box sizes are different
        assert step_features["bounding_box"]["x"] != assembly_features["bounding_box"]["x"]
        
        # 5. Upload IGES file (should parse successfully via local fallback mode)
        iges_path = Path(__file__).parent / "test_edge.iges"
        with open(iges_path, "rb") as f:
            files = {"file": ("test_edge.iges", f.read(), "application/octet-stream")}
        upload_iges_res = await ac.post("/api/upload", files=files, headers=headers)
        assert upload_iges_res.status_code == 201, f"IGES Upload failed: {upload_iges_res.text}"
        iges_data = upload_iges_res.json()
        assert iges_data["parsing_status"] == "success", f"IGES parsing status is not success: {iges_data.get('error_message')}"
        iges_features = iges_data["geometry_features"]
        assert iges_features is not None
        assert iges_features["volume"] > 0
        assert len(iges_data["suggestions"]) > 0

        # 6. Upload invalid/unsupported file (should fail parsing gracefully)
        with open(stl_path, "rb") as f:
            # Send file with unsupported extension .xyz
            files = {"file": ("test_invalid.xyz", f.read(), "application/octet-stream")}
        upload_invalid_res = await ac.post("/api/upload", files=files, headers=headers)
        assert upload_invalid_res.status_code == 201, f"Invalid file upload failed: {upload_invalid_res.text}"
        invalid_data = upload_invalid_res.json()
        assert invalid_data["parsing_status"] == "failed"
        assert invalid_data["error_message"] is not None
        assert "Unsupported CAD format" in invalid_data["error_message"]
        assert invalid_data["geometry_features"] is None
        assert len(invalid_data["suggestions"]) == 0
