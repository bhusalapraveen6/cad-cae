import asyncio
import httpx
import json

BASE = "http://127.0.0.1:8000"

async def run_and_verify_job(client, project_id, analysis_type, parameters, verify_fn):
    print(f"\n[JOB] Dispatching {analysis_type}...")
    r = await client.post(f"/api/projects/{project_id}/jobs", json={
        "project_id": project_id,
        "analysis_type": analysis_type,
        "parameters": parameters,
    })
    if r.status_code not in (200, 201):
        print(f"[JOB] FAILED to dispatch {analysis_type}: {r.status_code} {r.text}")
        return False

    job = r.json()
    job_id = job["id"]
    print(f"[JOB] Dispatched {analysis_type} -> job_id={job_id}")

    for attempt in range(30):
        await asyncio.sleep(1)
        r = await client.get(f"/api/jobs/{job_id}")
        job = r.json()
        pct = job.get("progress_percent", 0)
        msg = (job.get("progress_message") or "").encode('ascii', 'replace').decode()
        print(f"      [{pct:3d}%] {msg}")
        if job["status"] in ("completed", "failed"):
            break

    print(f"[JOB] FINAL status={job['status']}")
    if job["status"] != "completed":
        print(f"[JOB] FAILED to complete {analysis_type}. Error: {job.get('error_message')}")
        return False

    r = await client.get(f"/api/jobs/{job_id}/results")
    if r.status_code != 200:
        print(f"[RESULTS] FAILED to get results: {r.status_code}")
        return False

    res = r.json()
    verify_fn(res)
    return True

async def main():
    async with httpx.AsyncClient(base_url=BASE, timeout=60) as client:

        # ── 1. Health check ────────────────────────────────────────────
        r = await client.get("/health")
        h = r.json()
        print(f"[HEALTH] status={h['status']} mock_cad={h['mock_cad']} mock_solver={h['mock_solver']}")
        assert h["status"] == "ok"

        # ── 2. Upload STL ──────────────────────────────────────────────
        with open("test_cube.stl", "rb") as f:
            stl_bytes = f.read()

        r = await client.post(
            "/api/upload",
            files={"file": ("test_cube.stl", stl_bytes, "application/octet-stream")},
            data={"project_name": "Test Cube 50mm", "use_case": "bracket"},
        )
        if r.status_code not in (200, 201):
            print(f"[UPLOAD] FAILED {r.status_code}")
            return
        data = r.json()
        project_id = data.get("project_id")
        print(f"[UPLOAD] project_id={project_id}")
        print(f"[UPLOAD] format={data.get('file_format')} size={data.get('file_size')}B")

        # ── 3. Common Parameters ───────────────────────────────────────
        material = {
            "name": "Structural Steel (A36)",
            "youngs_modulus": 200,
            "poissons_ratio": 0.26,
            "density": 7850,
            "yield_strength": 250,
            "thermal_conductivity": 50.0,
            "specific_heat": 490.0,
        }

        # ── 4. Run & Verify: Static Structural ──────────────────────────
        def verify_static(res):
            summary = res.get("summary", {})
            print(f"[VERIFY-STATIC] max_stress = {summary.get('max_stress')} MPa")
            print(f"[VERIFY-STATIC] max_disp   = {summary.get('max_displacement')} mm")
            assert summary.get('max_stress') is not None
            assert summary.get('max_displacement') is not None

        success = await run_and_verify_job(client, project_id, "static_structural", {
            "material": material,
            "boundary_conditions": [
                {"type": "fixed", "face_ids": []},
                {"type": "force", "fz": -5000, "face_ids": []},
            ],
        }, verify_static)
        assert success

        # ── 5. Run & Verify: Nonlinear Structural ───────────────────────
        def verify_nonlinear(res):
            summary = res.get("summary", {})
            print(f"[VERIFY-NONLINEAR] max_stress = {summary.get('max_stress')} MPa")
            print(f"[VERIFY-NONLINEAR] max_disp   = {summary.get('max_displacement')} mm")
            assert summary.get('max_stress') is not None
            assert summary.get('max_displacement') is not None

        success = await run_and_verify_job(client, project_id, "nonlinear", {
            "material": material,
            "nonlinear": True,
            "boundary_conditions": [
                {"type": "fixed", "face_ids": []},
                {"type": "force", "fz": -5000, "face_ids": []},
            ],
        }, verify_nonlinear)
        assert success

        # ── 6. Run & Verify: Buckling ──────────────────────────────────
        def verify_buckling(res):
            summary = res.get("summary", {})
            factors = summary.get("buckling_factors") or []
            print(f"[VERIFY-BUCKLING] buckling_factors = {factors}")
            assert len(factors) > 0
            assert all(f > 0 for f in factors)

        success = await run_and_verify_job(client, project_id, "buckling", {
            "material": material,
            "num_buckling_modes": 5,
            "boundary_conditions": [
                {"type": "fixed", "face_ids": []},
                {"type": "force", "fz": -1000, "face_ids": []},
            ],
        }, verify_buckling)
        assert success

        # ── 7. Run & Verify: Thermal Transient ─────────────────────────
        def verify_thermal(res):
            summary = res.get("summary", {})
            print(f"[VERIFY-THERMAL] max_temp = {summary.get('max_temperature')} C")
            print(f"[VERIFY-THERMAL] min_temp = {summary.get('min_temperature')} C")
            assert summary.get('max_temperature') is not None

        success = await run_and_verify_job(client, project_id, "thermal_transient", {
            "material": material,
            "steady_state": False,
            "time_period": 10.0,
            "num_time_steps": 20,
            "initial_temperature": 20.0,
            "boundary_conditions": [
                {"type": "convection", "film_coefficient": 15.0, "ambient_temperature": 25.0, "face_ids": []}
            ],
        }, verify_thermal)
        assert success

        # ── 8. Run & Verify: CFD External ──────────────────────────────
        def verify_cfd(res):
            summary = res.get("summary", {})
            result_data = res.get("result_data") or {}
            print(f"[VERIFY-CFD] max_vel     = {summary.get('max_velocity') or result_data.get('max_velocity_ms')} m/s")
            print(f"[VERIFY-CFD] drag_coeff  = {result_data.get('drag_coefficient')}")
            print(f"[VERIFY-CFD] drag_force  = {result_data.get('drag_force_n')} N")
            assert result_data.get('drag_coefficient') is not None
            assert result_data.get('drag_force_n') is not None

        success = await run_and_verify_job(client, project_id, "cfd_external", {
            "fluid_density": 1.225,
            "dynamic_viscosity": 1.81e-5,
            "boundary_conditions": [
                {"type": "inlet", "velocity": 12.0, "face_ids": []}
            ],
        }, verify_cfd)
        assert success

        print("\n[OK] All checks passed successfully for all solver modules!")

asyncio.run(main())
