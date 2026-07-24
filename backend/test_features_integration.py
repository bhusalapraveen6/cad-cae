import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient, ASGITransport
import os
import shutil
from pathlib import Path

# Override database URL to a test sqlite database before importing app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_features_local.db"
os.environ["MOCK_SOLVER_MODE"] = "true"
os.environ["MOCK_CAD_MODE"] = "true"

from app.main import app
from app.config import settings
from app.database import init_db

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_test_db():
    db_file = Path("test_features_local.db")
    if db_file.exists():
        try:
            db_file.unlink()
        except OSError:
            pass
            
    await init_db()
        
    yield
    
    if db_file.exists():
        try:
            db_file.unlink()
        except OSError:
            pass
    test_storage = Path(settings.local_storage_path)
    if test_storage.exists() and "test" in str(test_storage):
        shutil.rmtree(test_storage, ignore_errors=True)

@pytest.mark.asyncio
async def test_end_to_end_features():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        
        # 1. Sign up/Log in guest user to get access token
        signup_res = await ac.post("/api/auth/signup", json={"username": "test_user_feat", "password": "test_password_feat"})
        assert signup_res.status_code in (200, 201, 400)
        
        login_res = await ac.post("/api/auth/login", json={"username": "test_user_feat", "password": "test_password_feat"})
        assert login_res.status_code == 200
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Upload test_cube.stl
        stl_path = Path(__file__).parent / "test_cube.stl"
        with open(stl_path, "rb") as f:
            files = {"file": ("test_cube.stl", f.read(), "application/octet-stream")}
        upload_res = await ac.post("/api/upload", files=files, headers=headers)
        assert upload_res.status_code == 201
        project_id = upload_res.json()["project_id"]
        
        # 3. Create a Job with multiple analysis types and new PrescribedDisplacement boundary condition
        job_params = {
            "material": {
                "name": "Steel",
                "youngs_modulus": 210.0,
                "poissons_ratio": 0.3,
                "density": 7850.0,
                "yield_strength": 250.0
            },
            "mesh_settings": {
                "global_element_size": 5.0,
                "refine_curvature": False
            },
            "boundary_conditions": [
                {
                    "type": "displacement",
                    "face_ids": [1],
                    "dx": 0.0,
                    "dy": "free",
                    "dz": "free",
                    "description": "Prescribed displacement on base"
                },
                {
                    "type": "force",
                    "face_ids": [3],
                    "fx": 0,
                    "fy": 0,
                    "fz": -5000,
                    "description": "Bending force load"
                }
            ]
        }
        
        # Test creating structural job
        create_job_res = await ac.post(
            f"/api/projects/{project_id}/jobs",
            json={
                "project_id": project_id,
                "analysis_types": ["static_structural", "modal"],
                "parameters": job_params
            },
            headers=headers
        )
        assert create_job_res.status_code == 201
        job_id = create_job_res.json()["id"]
        
        # 4. Wait for background inline solver to execute and complete
        completed = False
        for _ in range(20):
            await asyncio.sleep(0.3)
            job_status_res = await ac.get(f"/api/projects/{project_id}/jobs", headers=headers)
            job = next(j for j in job_status_res.json() if j["id"] == job_id)
            if job["status"] == "completed":
                completed = True
                break
            elif job["status"] == "failed":
                pytest.fail(f"Job failed: {job.get('error_message')}")
                
        assert completed, "Job did not complete in time"
        
        # 5. Fetch structural / modal results and verify animated frames are returned in result_data
        results_res = await ac.get(f"/api/jobs/{job_id}/results", headers=headers)
        assert results_res.status_code == 200
        res_data = results_res.json()
        
        # Verify static_structural frames
        static_res = res_data["result_data"]["results"]["static_structural"]
        assert "frames" in static_res
        assert len(static_res["frames"]) == 10
        first_frame = static_res["frames"][0]
        assert "frame_index" in first_frame
        assert "displacement" in first_frame
        assert "stress" in first_frame
        
        # Verify modal oscillation frames
        modal_res = res_data["result_data"]["results"]["modal"]
        assert "modes" in modal_res
        assert len(modal_res["modes"]) > 0
        first_mode = modal_res["modes"][0]
        assert "frames" in first_mode
        assert len(first_mode["frames"]) == 12
        assert "displacement" in first_mode["frames"][0]
        assert "stress" in first_mode["frames"][0]

        # 6. Create and run a CFD simulation
        cfd_params = {
            "fluid_density": 1.225,
            "dynamic_viscosity": 1.81e-5,
            "boundary_conditions": [
                {
                    "type": "inlet",
                    "face_ids": [1],
                    "velocity": 10.0,
                    "description": "CFD Wind tunnel inlet"
                }
              ]
        }
        create_cfd_job_res = await ac.post(
            f"/api/projects/{project_id}/jobs",
            json={
                "project_id": project_id,
                "analysis_types": ["cfd_internal"],
                "parameters": cfd_params
            },
            headers=headers
        )
        assert create_cfd_job_res.status_code == 201
        cfd_job_id = create_cfd_job_res.json()["id"]
        
        # Wait for CFD job completion
        cfd_completed = False
        for _ in range(20):
            await asyncio.sleep(0.3)
            cfd_status_res = await ac.get(f"/api/projects/{project_id}/jobs", headers=headers)
            job = next(j for j in cfd_status_res.json() if j["id"] == cfd_job_id)
            if job["status"] == "completed":
                cfd_completed = True
                break
                
        assert cfd_completed, "CFD Job did not complete in time"
        
        # Fetch CFD results and verify sample points are returned
        cfd_results_res = await ac.get(f"/api/jobs/{cfd_job_id}/results", headers=headers)
        assert cfd_results_res.status_code == 200
        cfd_res_data = cfd_results_res.json()
        cfd_result_obj = cfd_res_data["result_data"]["results"]["cfd_internal"]
        assert "cfd_data" in cfd_result_obj
        assert "sample_points" in cfd_result_obj["cfd_data"]
        assert "velocity_vectors" in cfd_result_obj["cfd_data"]
        assert len(cfd_result_obj["cfd_data"]["sample_points"]) > 0
        assert len(cfd_result_obj["cfd_data"]["velocity_vectors"]) == len(cfd_result_obj["cfd_data"]["sample_points"])
