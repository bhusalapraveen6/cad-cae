import streamlit as st
import os
import sys
import uuid
import json
import asyncio
import time
import httpx
from datetime import datetime, timezone
from pathlib import Path
import plotly.graph_objects as go
import numpy as np

# Ensure backend folder is in sys.path
BASE_DIR = Path(__file__).resolve().parent
backend_path = BASE_DIR / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# In standalone mode, we can import backend functions directly.
try:
    from app.config import settings
    from app.database import init_db, get_db_context
    from app.models.db_models import Project, GeometryFeatures, Job, AnalysisResult, Material, ChatMessage, JobStatus, AnalysisType
    from app.workers.seed import seed_materials
    from app.cad_import.parser import parse_cad_file
    from app.geometry_analysis.feature_extractor import extract_features
    from app.geometry_analysis.suggestion_engine import suggest_analyses
    from app.workers.inline_runner import run_analysis_inline
    from app.chatbot.claude_client import stream_chat_response
    STANDALONE_AVAILABLE = True
except Exception as e:
    STANDALONE_AVAILABLE = False
    STANDALONE_ERROR = e

# Set up page configurations
st.set_page_config(
    page_title="CAD-CAE Analyzer — Streamlit Dashboard",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern design aesthetics matching the React dashboard
st.markdown("""
<style>
    /* Styling overrides */
    .stApp {
        background-color: #060d1a;
        color: #e8f0fe;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #00e5ff !important;
        font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
    }
    p, span, label, li {
        color: #8ba3c7;
    }
    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #2979ff, #00e5ff) !important;
        color: white !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 0.5rem 1.5rem !important;
        box-shadow: 0 4px 16px rgba(0, 229, 255, 0.2) !important;
        transition: all 0.2s !important;
    }
    .stButton>button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(0, 229, 255, 0.4) !important;
    }
    /* Cards styling */
    .metric-card {
        background: rgba(17, 34, 64, 0.85);
        border: 1px solid rgba(41, 121, 255, 0.2);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        backdrop-filter: blur(12px);
    }
    .metric-title {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #4a6080;
    }
    .metric-value {
        font-size: 26px;
        font-weight: 700;
        color: #e8f0fe;
        margin-top: 4px;
        font-family: 'JetBrains Mono', monospace;
    }
    .suggestion-card {
        background: rgba(23, 42, 74, 0.7);
        border: 1px solid rgba(0, 229, 255, 0.25);
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .suggestion-title {
        font-weight: 600;
        color: #00e5ff !important;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .badge {
        font-size: 10px;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 12px;
        display: inline-block;
    }
    .badge-high {
        background: rgba(255, 82, 82, 0.2);
        color: #ff5252;
        border: 1px solid rgba(255, 82, 82, 0.4);
    }
    .badge-medium {
        background: rgba(255, 171, 64, 0.2);
        color: #ffab40;
        border: 1px solid rgba(255, 171, 64, 0.4);
    }
    .badge-low {
        background: rgba(0, 230, 118, 0.2);
        color: #00e676;
        border: 1px solid rgba(0, 230, 118, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# ── Helper for Running Async Coroutines in Streamlit ─────────────────────────
def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)

# ── Initialize DB & Materials in Standalone mode ─────────────────────────────
@st.cache_resource
def setup_database():
    if STANDALONE_AVAILABLE:
        run_async(init_db())
        run_async(seed_materials())
        return True
    return False

db_ready = setup_database()

# ── Session State Setup ───────────────────────────────────────────────────────
if "op_mode" not in st.session_state:
    st.session_state.op_mode = "Standalone"
if "api_url" not in st.session_state:
    st.session_state.api_url = "http://localhost:8000/api"
if "active_project_id" not in st.session_state:
    st.session_state.active_project_id = None
if "active_job_id" not in st.session_state:
    st.session_state.active_job_id = None
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "📐 Geometry Analysis"

# ── API Client Implementation ────────────────────────────────────────────────
def api_request(method, endpoint, **kwargs):
    url = f"{st.session_state.api_url}{endpoint}"
    try:
        response = httpx.request(method, url, timeout=30.0, **kwargs)
        if response.status_code >= 400:
            st.error(f"API Error ({response.status_code}): {response.text}")
            return None
        return response.json()
    except Exception as e:
        st.error(f"Failed to connect to API at {url}: {e}")
        return None


def api_chat_stream(api_url, project_id, job_id, message):
    url = f"{api_url}/chat"
    payload = {
        "project_id": project_id,
        "job_id": job_id,
        "message": message,
        "stream": True
    }
    try:
        with httpx.stream("POST", url, json=payload, timeout=60.0) as r:
            if r.status_code >= 400:
                yield f"API Error ({r.status_code}): {r.read().decode()}"
                return
            for line in r.iter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        data_json = json.loads(data_str)
                        if data_json.get("done"):
                            break
                        if "token" in data_json:
                            yield data_json["token"]
                        elif "error" in data_json:
                            yield f"\n[Error: {data_json['error']}]\n"
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        yield f"Failed to connect to chat API: {e}"


def local_upload_cad(file_bytes, filename, project_name, use_case):
    if not STANDALONE_AVAILABLE:
        st.error("Standalone imports failed. Check standard library packages.")
        return None

    # Generate project ID
    project_id = str(uuid.uuid4())
    
    # Save the file
    upload_dir = settings.upload_dir / project_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_path = upload_dir / filename
    saved_path.write_bytes(file_bytes)
    
    # Parse geometry and extract features
    async def _parse_and_persist():
        geom_data = await parse_cad_file(saved_path)
        features = extract_features(geom_data)
        user_context = {"use_case": use_case} if use_case else {}
        suggestions = suggest_analyses(features, user_context)
        
        name = project_name or Path(filename).stem
        suffix = Path(filename).suffix.lower().lstrip(".")
        
        async with get_db_context() as db:
            project = Project(
                id=project_id,
                name=name,
                cad_filename=filename,
                cad_format=suffix,
                cad_file_path=str(saved_path),
                cad_file_size=len(file_bytes),
            )
            db.add(project)
            
            com = features.center_of_mass
            geo_db = GeometryFeatures(
                project_id=project_id,
                volume=features.volume,
                surface_area=features.surface_area,
                bbox_x=features.bbox[0],
                bbox_y=features.bbox[1],
                bbox_z=features.bbox[2],
                center_of_mass=f"{com[0]:.2f},{com[1]:.2f},{com[2]:.2f}",
                slenderness_ratio=features.slenderness_ratio,
                surface_volume_ratio=features.surface_volume_ratio,
                is_thin_walled=features.is_thin_walled,
                has_holes=features.has_holes,
                has_fillets=features.has_fillets,
                has_internal_cavity=features.has_internal_cavity,
                has_symmetry=features.has_symmetry,
                is_sheet_metal=features.is_sheet_metal,
                raw_features=features.raw,
                suggestions=[
                    {
                        "analysis_type": s.analysis_type.value,
                        "title": s.title,
                        "rationale": s.rationale,
                        "confidence": s.confidence,
                        "icon": s.icon,
                        "category": s.category,
                        "priority": s.priority,
                    }
                    for s in suggestions
                ],
            )
            db.add(geo_db)
            
    run_async(_parse_and_persist())
    return project_id


# ── Standalone Mode Database Wrappers ────────────────────────────────────────
def get_standalone_projects():
    async def _fetch():
        async with get_db_context() as db:
            from sqlalchemy import select
            rows = (await db.execute(select(Project).order_by(Project.created_at.desc()))).scalars().all()
            return [{"id": p.id, "name": p.name, "cad_filename": p.cad_filename, "cad_format": p.cad_format} for p in rows]
    return run_async(_fetch()) if STANDALONE_AVAILABLE else []

def get_standalone_project(project_id):
    async def _fetch():
        async with get_db_context() as db:
            from sqlalchemy import select
            p = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
            if not p:
                return None
            g = (await db.execute(select(GeometryFeatures).where(GeometryFeatures.project_id == project_id))).scalar_one_or_none()
            
            geo_dict = {}
            if g:
                com = [float(x) for x in g.center_of_mass.split(",")] if g.center_of_mass else [0, 0, 0]
                geo_dict = {
                    "volume": g.volume,
                    "surface_area": g.surface_area,
                    "bbox_x": g.bbox_x, "bbox_y": g.bbox_y, "bbox_z": g.bbox_z,
                    "center_of_mass": com,
                    "slenderness_ratio": g.slenderness_ratio,
                    "surface_volume_ratio": g.surface_volume_ratio,
                    "is_thin_walled": g.is_thin_walled,
                    "has_holes": g.has_holes,
                    "has_fillets": g.has_fillets,
                    "has_internal_cavity": g.has_internal_cavity,
                    "has_symmetry": g.has_symmetry,
                    "is_sheet_metal": g.is_sheet_metal,
                    "suggestions": g.suggestions or [],
                }
            return {
                "id": p.id, "name": p.name, "cad_filename": p.cad_filename,
                "cad_format": p.cad_format, "cad_file_path": p.cad_file_path,
                "geometry": geo_dict
            }
    return run_async(_fetch()) if STANDALONE_AVAILABLE else None

def get_standalone_materials():
    async def _fetch():
        async with get_db_context() as db:
            from sqlalchemy import select
            mats = (await db.execute(select(Material).order_by(Material.name))).scalars().all()
            return [
                {
                    "id": m.id, "name": m.name, "category": m.category,
                    "youngs_modulus": m.youngs_modulus, "poissons_ratio": m.poissons_ratio,
                    "density": m.density, "yield_strength": m.yield_strength,
                    "ultimate_strength": m.ultimate_strength,
                    "thermal_conductivity": m.thermal_conductivity,
                    "specific_heat": m.specific_heat, "thermal_expansion": m.thermal_expansion
                }
                for m in mats
            ]
    return run_async(_fetch()) if STANDALONE_AVAILABLE else []

def get_standalone_jobs(project_id):
    async def _fetch():
        async with get_db_context() as db:
            from sqlalchemy import select
            rows = (await db.execute(select(Job).where(Job.project_id == project_id).order_by(Job.created_at.desc()))).scalars().all()
            return [{"id": j.id, "analysis_type": j.analysis_type, "status": j.status, "progress_percent": j.progress_percent} for j in rows]
    return run_async(_fetch()) if STANDALONE_AVAILABLE else []

def get_standalone_job(job_id):
    async def _fetch():
        async with get_db_context() as db:
            from sqlalchemy import select
            j = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
            if not j:
                return None
            res = (await db.execute(select(AnalysisResult).where(AnalysisResult.job_id == job_id))).scalar_one_or_none()
            res_dict = {}
            if res:
                res_dict = {
                    "max_stress": res.max_stress,
                    "min_stress": res.min_stress,
                    "max_displacement": res.max_displacement,
                    "max_temperature": res.max_temperature,
                    "min_safety_factor": res.min_safety_factor,
                    "natural_frequencies": res.natural_frequencies,
                    "buckling_factors": res.buckling_factors,
                    "fatigue_life_cycles": res.fatigue_life_cycles,
                    "result_data": res.result_data or {},
                }
            return {
                "id": j.id, "analysis_type": j.analysis_type, "status": j.status,
                "progress_percent": j.progress_percent, "progress_message": j.progress_message,
                "error_message": j.error_message, "results": res_dict
            }
    return run_async(_fetch()) if STANDALONE_AVAILABLE else None


# ── Interactive 3D Plotly Mesh Builder ───────────────────────────────────────
def get_plotly_mesh(vertices, faces, analysis_type=None, result_data=None, field_type="stress"):
    """
    Renders CAD geometry or FEA solver result fields onto the 3D model using Plotly.
    """
    if vertices is None or len(vertices) == 0:
        return None

    verts = np.array(vertices)
    x, y, z = verts[:, 0], verts[:, 1], verts[:, 2]
    faces_arr = np.array(faces)
    i, j, k = faces_arr[:, 0], faces_arr[:, 1], faces_arr[:, 2]

    title = "CAD Geometry Mesh"
    color_intensity = None
    colorscale = "Viridis"
    colorbar_title = ""

    # Generate synthetic results mapped to geometry vertices if in mock/emulation mode
    if result_data:
        num_verts = len(verts)
        max_val = 0.0
        min_val = 0.0

        # Create realistic color contours depending on simulation type
        if analysis_type in ("static_structural", "nonlinear", "fatigue"):
            # Mock stress/displacement gradient (higher near the fixed support (x_min), lower at tips)
            min_x, max_x = np.min(x), np.max(x)
            span_x = max(max_x - min_x, 1.0)
            
            if field_type == "displacement":
                # Displacement is maximum at the tip (x_max)
                disp_max = result_data.get("max_displacement_mm", result_data.get("max_displacement", 0.05))
                color_intensity = disp_max * ((x - min_x) / span_x)**2
                colorbar_title = "Displacement (mm)"
                colorscale = "Plasma"
                title = f"3D Displacement Field (Max: {disp_max:.4f} mm)"
            elif field_type == "safety_factor":
                sf_min = result_data.get("min_safety_factor", 1.5)
                # Safety factor is lowest where stress is highest (at x_min)
                color_intensity = sf_min + (10 - sf_min) * ((x - min_x) / span_x)
                colorbar_title = "Safety Factor"
                colorscale = "Portland"
                title = f"Safety Factor Contour (Min: {sf_min:.2f})"
            else:  # stress
                stress_max = result_data.get("max_stress_mpa", result_data.get("max_stress", 150.0))
                # Stress is maximum at the fixed support
                color_intensity = stress_max * ((max_x - x) / span_x) + np.random.uniform(0, 10, num_verts)
                color_intensity = np.clip(color_intensity, 0, stress_max)
                colorbar_title = "Stress (MPa)"
                colorscale = "Jet"
                title = f"3D von Mises Stress (Max: {stress_max:.1f} MPa)"

        elif "thermal" in str(analysis_type):
            temp_max = result_data.get("max_temperature", 100.0)
            temp_min = result_data.get("min_temperature", result_data.get("min_temperature_c", 20.0))
            # Temperature gradient from bottom to top (y_min to y_max)
            min_y, max_y = np.min(y), np.max(y)
            span_y = max(max_y - min_y, 1.0)
            color_intensity = temp_min + (temp_max - temp_min) * ((y - min_y) / span_y)
            colorbar_title = "Temperature (°C)"
            colorscale = "Hot"
            title = f"Steady-State Thermal Distribution (Max: {temp_max:.1f} °C)"

        elif analysis_type in ("cfd_internal", "cfd_external"):
            vel_max = result_data.get("max_velocity", 5.0)
            # Velocity contours (higher near center of bbox)
            centroid = np.mean(verts, axis=0)
            dist_to_center = np.linalg.norm(verts - centroid, axis=1)
            max_dist = max(np.max(dist_to_center), 1.0)
            color_intensity = vel_max * (1.0 - (dist_to_center / max_dist)**2)
            colorbar_title = "Velocity (m/s)"
            colorscale = "Viridis"
            title = f"CFD Flow Velocity field (Max: {vel_max:.2f} m/s)"

        elif analysis_type in ("modal", "buckling"):
            # Sinusoidal mode shapes
            min_x, max_x = np.min(x), np.max(x)
            span_x = max(max_x - min_x, 1.0)
            color_intensity = np.sin((x - min_x) / span_x * np.pi * 2)
            colorbar_title = "Relative Amplitude"
            colorscale = "RdBu"
            title = "Modal Deformation Mode Shape"

    # Define Plotly Mesh3d Trace
    mesh_trace = go.Mesh3d(
        x=x, y=y, z=z,
        i=i, j=j, k=k,
        intensity=color_intensity,
        colorscale=colorscale,
        colorbar=dict(title=colorbar_title, thickness=20) if color_intensity is not None else None,
        color="#2979ff" if color_intensity is None else None,
        flatshading=True,
        lighting=dict(ambient=0.5, diffuse=0.8, specular=0.2, roughness=0.5),
        lightposition=dict(x=100, y=100, z=100)
    )

    fig = go.Figure(data=[mesh_trace])
    fig.update_layout(
        title=dict(text=title, font=dict(color="#00e5ff")),
        paper_bgcolor="#0d1b2e",
        plot_bgcolor="#0d1b2e",
        margin=dict(l=0, r=0, t=40, b=0),
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            bgcolor="#0d1b2e"
        ),
        height=500
    )
    return fig


def generate_mock_pdf(project_name, analysis_type, results):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        import io
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
        story = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            name='TitleStyle',
            parent=styles['Heading1'],
            textColor=colors.HexColor('#002d62'),
            spaceAfter=20
        )
        
        story.append(Paragraph(f"CAD-CAE Simulation Analysis Report", title_style))
        story.append(Paragraph(f"<b>Project Name:</b> {project_name}", styles['Normal']))
        story.append(Paragraph(f"<b>Simulation Type:</b> {analysis_type.replace('_', ' ').title()}", styles['Normal']))
        story.append(Spacer(1, 12))
        
        story.append(Paragraph("<b>Simulation Scalar Summary:</b>", styles['Heading3']))
        story.append(Spacer(1, 6))
        
        data = [["Metric", "Value", "Unit"]]
        if results.get("max_stress"):
            data.append(["Max von Mises Stress", f"{results.get('max_stress'):,.2f}", "MPa"])
        if results.get("max_displacement"):
            data.append(["Max Displacement", f"{results.get('max_displacement'):,.4f}", "mm"])
        if results.get("min_safety_factor"):
            data.append(["Min Safety Factor", f"{results.get('min_safety_factor'):,.2f}", "-"])
        if results.get("max_temperature"):
            data.append(["Max Temperature", f"{results.get('max_temperature'):,.1f}", "°C"])
            
        t = Table(data, colWidths=[200, 100, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2979ff')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f5f7fa')),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#d0d5dd')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f9fafb')])
        ]))
        story.append(t)
        story.append(Spacer(1, 20))
        story.append(Paragraph("Report generated automatically via CAD-CAE dashboard.", styles['Italic']))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as e:
        return f"CAD-CAE Simulation Analysis Report\nProject: {project_name}\nType: {analysis_type}\nError generating ReportLab PDF: {e}".encode()


def generate_mock_docx(project_name, analysis_type, results):
    try:
        from docx import Document
        import io
        
        doc = Document()
        doc.add_heading("CAD-CAE Simulation Analysis Report", level=0)
        
        doc.add_paragraph(f"Project Name: {project_name}")
        doc.add_paragraph(f"Simulation Type: {analysis_type.replace('_', ' ').title()}")
        
        doc.add_heading("Simulation Summary Metrics", level=2)
        table = doc.add_table(rows=1, cols=3)
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = "Metric"
        hdr_cells[1].text = "Value"
        hdr_cells[2].text = "Unit"
        
        def add_row(m, v, u):
            row_cells = table.add_row().cells
            row_cells[0].text = str(m)
            row_cells[1].text = str(v)
            row_cells[2].text = str(u)
            
        if results.get("max_stress"):
            add_row("Max von Mises Stress", f"{results.get('max_stress'):,.2f}", "MPa")
        if results.get("max_displacement"):
            add_row("Max Displacement", f"{results.get('max_displacement'):,.4f}", "mm")
        if results.get("min_safety_factor"):
            add_row("Min Safety Factor", f"{results.get('min_safety_factor'):,.2f}", "-")
        if results.get("max_temperature"):
            add_row("Max Temperature", f"{results.get('max_temperature'):,.1f}", "°C")
            
        doc.add_paragraph("\nReport generated automatically via CAD-CAE dashboard.")
        
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as e:
        return f"CAD-CAE Simulation Analysis Report\nProject: {project_name}\nType: {analysis_type}\nError generating DOCX: {e}".encode()


# ── Sidebar Configurations ────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/nolan/96/artificial-intelligence.png", width=64)
    st.title("CAD-CAE Dashboard")
    st.write("---")

    # Mode Selector
    st.subheader("⚙️ Deployment Mode")
    op_mode = st.selectbox(
        "Select Operation Mode",
        options=["Standalone (Direct Run)", "API Client"],
        index=0 if st.session_state.op_mode == "Standalone" else 1,
        help="Standalone runs logic locally in this process. API Client communicates with the FastAPI server."
    )
    st.session_state.op_mode = "Standalone" if "Standalone" in op_mode else "API Client"

    if st.session_state.op_mode == "API Client":
        st.session_state.api_url = st.text_input("FastAPI Base URL", value=st.session_state.api_url)
        st.caption("Ensure the backend server is running on this port.")
    else:
        if not STANDALONE_AVAILABLE:
            st.error("Standalone imports failed. Check standard library packages.")
            st.caption(f"Error details: {STANDALONE_ERROR}")
        else:
            st.success("✅ Standalone Python engine ready.")

    st.write("---")

    # Project List & Loader
    st.subheader("📁 Project Workspace")
    projects = []
    if st.session_state.op_mode == "Standalone" and STANDALONE_AVAILABLE:
        projects = get_standalone_projects()
    elif st.session_state.op_mode == "API Client":
        res = api_request("GET", "/projects")
        if res:
            projects = res

    # Build options with a default option for starting/viewing new uploads
    project_options = {"🆕 Start New Project": None}
    for p in projects:
        project_options[p["name"]] = p["id"]
    project_names = list(project_options.keys())

    # Determine default selected index
    default_index = 0
    if st.session_state.active_project_id is not None:
        for idx, pid in enumerate(project_options.values()):
            if pid == st.session_state.active_project_id:
                default_index = idx
                break

    selected_project_name = st.selectbox(
        "Select Existing Project",
        options=project_names,
        index=default_index
    )
    
    selected_id = project_options[selected_project_name]
    if selected_id != st.session_state.active_project_id:
        st.session_state.active_project_id = selected_id
        st.session_state.active_job_id = None
        st.session_state.chat_messages = []
        st.rerun()


# ── Fetch Active Project Details ─────────────────────────────────────────────
active_project = None
if st.session_state.active_project_id:
    if st.session_state.op_mode == "Standalone" and STANDALONE_AVAILABLE:
        active_project = get_standalone_project(st.session_state.active_project_id)
    elif st.session_state.op_mode == "API Client":
        active_project = api_request("GET", f"/projects/{st.session_state.active_project_id}")
        if active_project:
            # Also get geometry features
            geo = api_request("GET", f"/projects/{st.session_state.active_project_id}/geometry")
            sug = api_request("GET", f"/projects/{st.session_state.active_project_id}/suggestions")
            active_project["geometry"] = geo or {}
            active_project["geometry"]["suggestions"] = sug.get("suggestions", []) if sug else []


# ── Main Header ───────────────────────────────────────────────────────────────
if active_project:
    st.title(f"Project: {active_project['name']}")
    st.caption(f"CAD File: {active_project.get('cad_filename', 'N/A')} ({active_project.get('cad_format', '').upper()})")
else:
    st.title("Automated CAD-to-CAE Platform")
    st.write("Upload a CAD model to automatically run feature detection, obtain simulation suggestives, run multiphysics solvers, and check results.")

# ── Set Up Main Tabs ──────────────────────────────────────────────────────────
nav_cols = st.columns(4)
tab_titles = [
    "📐 Geometry Analysis",
    "💻 Simulation Setup",
    "📊 3D Viewer & Results",
    "🤖 AI Assistant Chat"
]

for idx, title in enumerate(tab_titles):
    with nav_cols[idx]:
        if st.button(title, use_container_width=True, type="primary" if st.session_state.active_tab == title else "secondary"):
            st.session_state.active_tab = title
            st.rerun()
st.write("---")

# 🛠 Tab 1: Geometry Feature Extraction & Suggestions
if st.session_state.active_tab == "📐 Geometry Analysis":
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📤 Upload New CAD Model")
        with st.form("cad_upload_form", clear_on_submit=True):
            uploaded_file = st.file_uploader(
                "Upload a CAD file (.stl, .obj, .step, .stp, .iges, .igs)", 
                type=["stl", "obj", "step", "stp", "iges", "igs"]
            )
            proj_name_input = st.text_input("Project Name (Optional)", placeholder="My Analysis Project")
            use_case_input = st.selectbox(
                "Engineered Use Case (Optional)",
                options=["", "bracket", "heat_sink", "pipe", "pressure_vessel", "shaft"]
            )
            submit_upload = st.form_submit_button("Analyze Geometry")

            if submit_upload and uploaded_file is not None:
                file_bytes = uploaded_file.read()
                filename = uploaded_file.name
                
                with st.spinner("Parsing and extracting geometric features..."):
                    if st.session_state.op_mode == "Standalone" and STANDALONE_AVAILABLE:
                        project_id = local_upload_cad(file_bytes, filename, proj_name_input, use_case_input)
                        st.session_state.active_project_id = project_id
                        st.success("CAD parsed and loaded successfully in Standalone mode!")
                        st.session_state.active_tab = "💻 Simulation Setup"
                        st.rerun()
                    elif st.session_state.op_mode == "API Client":
                        files = {"file": (filename, file_bytes)}
                        data = {"project_name": proj_name_input, "use_case": use_case_input}
                        res = api_request("POST", "/upload", files=files, data=data)
                        if res:
                            st.session_state.active_project_id = res["project_id"]
                            st.success("CAD uploaded successfully to API server!")
                            st.session_state.active_tab = "💻 Simulation Setup"
                            st.rerun()

        # Display geometry attributes if loaded
        if active_project and "geometry" in active_project and active_project["geometry"]:
            geo = active_project["geometry"]
            st.write("---")
            st.subheader("📐 Detected Geometry Characteristics")
            
            # Grid display
            g1, g2, g3 = st.columns(3)
            with g1:
                st.markdown(f'<div class="metric-card"><div class="metric-title">Volume</div><div class="metric-value">{geo.get("volume", 0.0):,.1f} <span style="font-size:12px;color:#8ba3c7">mm³</span></div></div>', unsafe_allow_html=True)
            with g2:
                st.markdown(f'<div class="metric-card"><div class="metric-title">Surface Area</div><div class="metric-value">{geo.get("surface_area", 0.0):,.1f} <span style="font-size:12px;color:#8ba3c7">mm²</span></div></div>', unsafe_allow_html=True)
            with g3:
                # bounding box
                bbox = geo.get("bounding_box", {})
                if not bbox and "bbox_x" in geo:
                    bbox = {"x": geo["bbox_x"], "y": geo["bbox_y"], "z": geo["bbox_z"]}
                dx = bbox.get("x", 0.0)
                dy = bbox.get("y", 0.0)
                dz = bbox.get("z", 0.0)
                st.markdown(f'<div class="metric-card"><div class="metric-title">Bounding Box</div><div class="metric-value" style="font-size:16px; margin-top:12px">{dx:.1f} × {dy:.1f} × {dz:.1f} <span style="font-size:11px;color:#8ba3c7">mm</span></div></div>', unsafe_allow_html=True)

            # Feature flags
            st.markdown("##### Geometric Classification Tags:")
            tags = []
            if geo.get("is_thin_walled"): tags.append("Thin-Walled / Shell candidate")
            if geo.get("is_sheet_metal"): tags.append("Sheet Metal structure")
            if geo.get("has_holes"): tags.append("Bolt holes / Curvature detected")
            if geo.get("has_fillets"): tags.append("Fillet transitions detected")
            if geo.get("has_internal_cavity"): tags.append("Internal Cavity flow region")
            if geo.get("has_symmetry"): tags.append("Symmetrical properties")
            
            if tags:
                for tag in tags:
                    st.info(f"🔹 {tag}")
            else:
                st.write("Standard solid mechanical component classification.")

    with col2:
        st.subheader("🔍 3D Model Tessellation")
        # Load mesh vertices and faces
        vertices, faces = None, None
        if active_project:
            with st.spinner("Downloading 3D geometry..."):
                if st.session_state.op_mode == "Standalone" and STANDALONE_AVAILABLE:
                    try:
                        filepath = Path(active_project["cad_file_path"])
                        geom_data = run_async(parse_cad_file(filepath))
                        if geom_data.vertices is not None:
                            vertices = geom_data.vertices.tolist()
                            faces = geom_data.faces.tolist()
                    except Exception as e:
                        st.warning(f"Could not construct local mesh: {e}")
                elif st.session_state.op_mode == "API Client":
                    mesh_res = api_request("GET", f"/projects/{st.session_state.active_project_id}/mesh")
                    if mesh_res:
                        vertices = mesh_res.get("vertices")
                        faces = mesh_res.get("faces")

            if vertices and faces:
                fig = get_plotly_mesh(vertices, faces)
                st.plotly_chart(fig, use_container_width=True, key="geometry_mesh_viewer")
            else:
                st.info("Upload an STL/OBJ or select a project to display the 3D viewer.")

    # Suggestions row
    if active_project and "geometry" in active_project and active_project["geometry"]:
        st.write("---")
        st.subheader("💡 Recommended CAE Simulations")
        sugs = active_project["geometry"].get("suggestions", [])
        
        if sugs:
            cols = st.columns(min(len(sugs), 3))
            for idx, s in enumerate(sugs):
                col_idx = idx % len(cols)
                with cols[col_idx]:
                    conf = s.get("confidence", 0.8)
                    badge_class = "badge-high" if conf >= 0.8 else ("badge-medium" if conf >= 0.5 else "badge-low")
                    st.markdown(f"""
                    <div class="suggestion-card">
                        <div class="suggestion-title">⚙️ {s.get("title", s.get("analysis_type"))}</div>
                        <div style="margin-top:6px; margin-bottom:8px">
                            <span class="badge {badge_class}">Confidence: {conf*100:.0f}%</span>
                            <span class="badge" style="background:rgba(41,121,255,0.15);color:#2979ff;border:1px solid rgba(41,121,255,0.3)">Category: {s.get("category", "FEA")}</span>
                        </div>
                        <p style="font-size:12px; line-height:1.4">{s.get("rationale")}</p>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No recommendations found for this geometry.")


# 💻 Tab 2: Solver Parameter Configurations & Job submission
elif st.session_state.active_tab == "💻 Simulation Setup":
    if not active_project:
        st.warning("Please select or upload a project first.")
    else:
        st.subheader("⚙️ Setup Simulation Run")
        
        # Select analysis type
        sug_types = [s.get("analysis_type") for s in active_project["geometry"].get("suggestions", [])]
        all_types = [e.value for e in AnalysisType]
        # sort so suggestions appear first
        sorted_types = sorted(all_types, key=lambda x: x not in sug_types)
        
        analysis_type = st.selectbox(
            "Select Simulation Type",
            options=sorted_types,
            format_func=lambda x: x.replace("_", " ").title()
        )
        
        # Load material options
        materials = []
        if st.session_state.op_mode == "Standalone" and STANDALONE_AVAILABLE:
            materials = get_standalone_materials()
        elif st.session_state.op_mode == "API Client":
            mat_res = api_request("GET", "/materials")
            if mat_res: materials = mat_res
            
        mat_options = {m["name"]: m for m in materials}
        
        col_mat, col_bc = st.columns(2)
        
        with col_mat:
            st.subheader("🧱 Material Assignment")
            selected_mat_name = st.selectbox("Select Material from Library", options=list(mat_options.keys()))
            
            # Show assigned properties
            if selected_mat_name:
                assigned_mat = mat_options[selected_mat_name]
                st.markdown(f"""
                - **Young's Modulus**: {assigned_mat.get('youngs_modulus', 'N/A')} GPa
                - **Poisson's Ratio**: {assigned_mat.get('poissons_ratio', 'N/A')}
                - **Density**: {assigned_mat.get('density', 'N/A')} kg/m³
                - **Yield Strength**: {assigned_mat.get('yield_strength', 'N/A')} MPa
                - **Thermal Conductivity**: {assigned_mat.get('thermal_conductivity', 'N/A')} W/(m·K)
                """)

        with col_bc:
            st.subheader("⚓ Boundary Conditions")
            
            # Boundary conditions depend on the chosen analysis
            bcs = []
            if "thermal" in analysis_type:
                temp_inlet = st.number_input("Source Temperature (°C)", value=100.0)
                temp_ambient = st.number_input("Ambient/Convection Temp (°C)", value=20.0)
                convection_h = st.number_input("Convective Heat Transfer Coeff H (W/m²K)", value=15.0)
                bcs = [
                    {"type": "temperature", "value": temp_inlet, "location": "boundary_inlet"},
                    {"type": "convection", "ambient_temp": temp_ambient, "h": convection_h, "location": "boundary_ambient"}
                ]
            elif "cfd" in analysis_type:
                inlet_vel = st.number_input("Inlet Flow Velocity (m/s)", value=2.5)
                outlet_p = st.number_input("Outlet Relative Pressure (Pa)", value=0.0)
                bcs = [
                    {"type": "velocity_inlet", "value": inlet_vel, "location": "inlet"},
                    {"type": "pressure_outlet", "value": outlet_p, "location": "outlet"}
                ]
            elif analysis_type == "fatigue":
                stress_amp = st.number_input("Cyclic Stress Amplitude (MPa)", value=100.0)
                stress_ratio = st.number_input("Stress Ratio R (Min/Max stress)", value=-1.0, help="-1.0 for fully reversed loading.")
                mean_correction = st.selectbox("Mean Stress Correction Method", options=["goodman", "soderberg", "gerber"])
                bcs = {
                    "stress_amplitude": stress_amp,
                    "stress_ratio": stress_ratio,
                    "mean_stress_correction": mean_correction
                }
            else:  # Structural (static, modal, buckling, nonlinear)
                force_z = st.number_input("Load Force in Z-direction (N)", value=-1000.0)
                force_y = st.number_input("Load Force in Y-direction (N)", value=0.0)
                force_x = st.number_input("Load Force in X-direction (N)", value=0.0)
                st.caption("Fixes constraints will be automatically applied at the detected root/support boundary.")
                bcs = [
                    {"type": "fixed", "location": "fixed_support"},
                    {"type": "force", "fx": force_x, "fy": force_y, "fz": force_z, "location": "load_point"}
                ]
                
            # Pack parameter payload
            parameters = {
                "material": assigned_mat if selected_mat_name else {},
            }
            if isinstance(bcs, list):
                parameters["boundary_conditions"] = bcs
            else:
                parameters.update(bcs) # fatigue dict unpack
                
        # Solver dispatch triggers
        st.write("---")
        if st.button("🚀 Solve Multiphysics Model"):
            job_id = str(uuid.uuid4())
            
            with st.spinner("Dispatching solver run..."):
                if st.session_state.op_mode == "Standalone" and STANDALONE_AVAILABLE:
                    # Create job record
                    async def save_job():
                        async with get_db_context() as db:
                            job = Job(
                                id=job_id,
                                project_id=st.session_state.active_project_id,
                                analysis_type=analysis_type,
                                status=JobStatus.PENDING,
                                parameters=parameters
                            )
                            db.add(job)
                    run_async(save_job())
                    
                    # Run inline solver in a separate thread to keep streamlit loop reactive
                    import threading
                    mesh_filepath = active_project.get("cad_file_path")
                    async def run_solver():
                        await run_analysis_inline(job_id, analysis_type, parameters, mesh_filepath)
                    
                    thread = threading.Thread(target=run_async, args=(run_solver(),))
                    thread.start()
                    
                    # Show progress updates in real-time
                    prog_bar = st.progress(0.0, text="Initializing runner...")
                    status_lbl = st.empty()
                    
                    while thread.is_alive():
                        job_info = get_standalone_job(job_id)
                        if job_info:
                            pct = job_info.get("progress_percent", 0)
                            msg = job_info.get("progress_message", "Running...")
                            prog_bar.progress(pct / 100.0, text=f"{msg} ({pct}%)")
                            if job_info.get("status") in ("completed", "failed", "cancelled"):
                                break
                        time.sleep(0.5)
                        
                    # Final check
                    job_info = get_standalone_job(job_id)
                    if job_info and job_info.get("status") == "completed":
                        st.session_state.active_job_id = job_id
                        st.success("Simulation finished successfully!")
                        st.session_state.active_tab = "📊 3D Viewer & Results"
                        st.rerun()
                    else:
                        st.error(f"Simulation failed. Error: {job_info.get('error_message') if job_info else 'Unknown'}")
                        
                elif st.session_state.op_mode == "API Client":
                    res = api_request("POST", f"/projects/{st.session_state.active_project_id}/jobs", json={
                        "analysis_type": analysis_type,
                        "parameters": parameters
                    })
                    if res:
                        job_id = res["id"]
                        prog_bar = st.progress(0.0, text="Dispatched...")
                        
                        # Poll REST progress endpoint
                        for _ in range(200): # 100 seconds timeout
                            time.sleep(0.5)
                            job_info = api_request("GET", f"/jobs/{job_id}")
                            if job_info:
                                pct = job_info.get("progress_percent", 0)
                                msg = job_info.get("progress_message", "Executing...")
                                prog_bar.progress(pct / 100.0, text=f"{msg} ({pct}%)")
                                if job_info.get("status") in ("completed", "failed", "cancelled"):
                                    break
                        
                        if job_info and job_info.get("status") == "completed":
                            st.session_state.active_job_id = job_id
                            st.success("Simulation completed on server!")
                            st.session_state.active_tab = "📊 3D Viewer & Results"
                            st.rerun()
                        else:
                            st.error("Simulation run timed out or failed on the API server.")


# 📊 Tab 3: Simulation Results, Contour plots and PDF reports
elif st.session_state.active_tab == "📊 3D Viewer & Results":
    # Let user select from the history of completed jobs for this project
    jobs = []
    if active_project:
        if st.session_state.op_mode == "Standalone" and STANDALONE_AVAILABLE:
            jobs = get_standalone_jobs(st.session_state.active_project_id)
        elif st.session_state.op_mode == "API Client":
            job_res = api_request("GET", f"/projects/{st.session_state.active_project_id}/jobs")
            if job_res: jobs = job_res
            
    completed_jobs = [j for j in jobs if j["status"] == "completed"]
    
    if not completed_jobs:
        st.info("No completed simulation runs found. Configure and run a simulation in Tab 2 first.")
    else:
        job_options = {f"{j['analysis_type'].replace('_', ' ').title()} - {j['id'][:8]}": j["id"] for j in completed_jobs}
        selected_job_lbl = st.selectbox("Select Simulation Results to view", options=list(job_options.keys()))
        active_job_id = job_options[selected_job_lbl]
        
        # Load results payload
        active_job = None
        if st.session_state.op_mode == "Standalone" and STANDALONE_AVAILABLE:
            active_job = get_standalone_job(active_job_id)
        elif st.session_state.op_mode == "API Client":
            active_job = api_request("GET", f"/jobs/{active_job_id}")
            if active_job:
                # also get full results schema
                res_payload = api_request("GET", f"/jobs/{active_job_id}/results")
                active_job["results"] = res_payload or {}
                
        if active_job and "results" in active_job and active_job["results"]:
            res = active_job["results"]
            st.write("---")
            st.subheader("📊 Key Simulation Scalar Metrics")
            
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                val = res.get("max_stress") or res.get("result_data", {}).get("max_stress_mpa")
                if val: st.markdown(f'<div class="metric-card"><div class="metric-title">Max von Mises Stress</div><div class="metric-value">{val:,.2f} <span style="font-size:12px;color:#8ba3c7">MPa</span></div></div>', unsafe_allow_html=True)
            with m2:
                val = res.get("max_displacement") or res.get("result_data", {}).get("max_displacement_mm")
                if val: st.markdown(f'<div class="metric-card"><div class="metric-title">Max Displacement</div><div class="metric-value">{val:,.4f} <span style="font-size:12px;color:#8ba3c7">mm</span></div></div>', unsafe_allow_html=True)
            with m3:
                val = res.get("min_safety_factor")
                if val:
                    sf_color = "#ff5252" if val < 1.2 else ("#ffab40" if val < 2.0 else "#00e676")
                    st.markdown(f'<div class="metric-card"><div class="metric-title">Min Safety Factor</div><div class="metric-value" style="color:{sf_color}">{val:,.2f}</div></div>', unsafe_allow_html=True)
            with m4:
                val = res.get("max_temperature") or res.get("result_data", {}).get("max_temperature")
                if val: st.markdown(f'<div class="metric-card"><div class="metric-title">Max Temperature</div><div class="metric-value">{val:,.1f} <span style="font-size:12px;color:#8ba3c7">°C</span></div></div>', unsafe_allow_html=True)
                
            # Modal natural frequencies
            freqs = res.get("natural_frequencies") or res.get("result_data", {}).get("natural_frequencies_hz")
            if freqs:
                st.info(f"🎵 Detected Natural Frequencies (First {len(freqs)} modes): " + ", ".join([f"{f:.1f} Hz" for f in freqs]))
                
            # Fatigue cycles
            cycles = res.get("fatigue_life_cycles") or res.get("result_data", {}).get("fatigue_life_cycles")
            if cycles:
                st.warning(f"⏳ Min Fatigue Lifetime: {cycles:,.0f} cycles")
                
            # Buckling factors
            bf = res.get("buckling_factors") or res.get("result_data", {}).get("buckling_factors")
            if bf:
                st.info(f"⚖️ Buckling Eigenvalue Load Factors: " + ", ".join([f"{f:.2f}" for f in bf]))

            st.write("---")
            st.subheader("👁️ 3D Interactive Results Contour Map")
            
            # Choose color field
            color_field_choices = ["stress", "displacement", "safety_factor"]
            if "thermal" in active_job["analysis_type"]:
                color_field_choices = ["temperature"]
            elif "cfd" in active_job["analysis_type"]:
                color_field_choices = ["velocity"]
                
            field_choice = st.selectbox("Select Result Field Contour", options=color_field_choices)
            
            # Draw contour plot
            vertices, faces = None, None
            if st.session_state.op_mode == "Standalone" and STANDALONE_AVAILABLE:
                try:
                    filepath = Path(active_project["cad_file_path"])
                    geom_data = run_async(parse_cad_file(filepath))
                    if geom_data.vertices is not None:
                        vertices = geom_data.vertices.tolist()
                        faces = geom_data.faces.tolist()
                except Exception as e:
                    pass
            elif st.session_state.op_mode == "API Client":
                mesh_res = api_request("GET", f"/projects/{st.session_state.active_project_id}/mesh")
                if mesh_res:
                    vertices = mesh_res.get("vertices")
                    faces = mesh_res.get("faces")

            if vertices and faces:
                fig = get_plotly_mesh(vertices, faces, active_job["analysis_type"], res.get("result_data", res), field_choice)
                st.plotly_chart(fig, use_container_width=True, key="results_mesh_viewer")
            else:
                st.error("Failed to load CAD mesh vertices for results post-processing.")
                
            st.write("---")
            st.subheader("📄 Engineering Report Generation")
            col_pdf, col_docx = st.columns(2)
            
            project_name = active_project.get("name", "Unknown")
            analysis_type = active_job.get("analysis_type", "static_structural")
            
            # Generate report bytes
            pdf_data = generate_mock_pdf(project_name, analysis_type, res)
            docx_data = generate_mock_docx(project_name, analysis_type, res)
            
            with col_pdf:
                st.download_button(
                    label="📥 Download PDF Analysis Report",
                    data=pdf_data,
                    file_name=f"{project_name.lower().replace(' ', '_')}_report.pdf",
                    mime="application/pdf"
                )
            with col_docx:
                st.download_button(
                    label="📥 Download Word DOCX Analysis Report",
                    data=docx_data,
                    file_name=f"{project_name.lower().replace(' ', '_')}_report.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )


# 🤖 Tab 4: AI chatbot Grounded in CAE project context
elif st.session_state.active_tab == "🤖 AI Assistant Chat":
    if not active_project:
        st.warning("Please select or upload a project first.")
    else:
        st.subheader("💬 AI Engineering Assistant")
        st.caption("Ask questions about boundary conditions, stress levels, material alternatives, design optimizations, or help interpreting simulation plots.")
        
        # Display chat history
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
        # Handle chat input
        user_input = st.chat_input("Ask a question about the current analysis...")
        
        if user_input:
            # Render user message
            with st.chat_message("user"):
                st.write(user_input)
            st.session_state.chat_messages.append({"role": "user", "content": user_input})
            
            # Prepare context dictionary matching backend _build_chat_context
            active_job_context = {}
            if st.session_state.active_job_id:
                if st.session_state.op_mode == "Standalone" and STANDALONE_AVAILABLE:
                    job_data = get_standalone_job(st.session_state.active_job_id)
                    if job_data and "results" in job_data:
                        r = job_data["results"]
                        active_job_context = {
                            "job": {
                                "type": job_data["analysis_type"],
                                "status": job_data["status"],
                            },
                            "results": {
                                "max_stress_mpa": r.get("max_stress"),
                                "max_displacement_mm": r.get("max_displacement"),
                                "safety_factor": r.get("min_safety_factor"),
                            }
                        }
                elif st.session_state.op_mode == "API Client":
                    job_data = api_request("GET", f"/jobs/{st.session_state.active_job_id}")
                    if job_data:
                        r_data = api_request("GET", f"/jobs/{st.session_state.active_job_id}/results")
                        r = r_data or {}
                        active_job_context = {
                            "job": {
                                "type": job_data["analysis_type"],
                                "status": job_data["status"],
                            },
                            "results": {
                                "max_stress_mpa": r.get("max_stress"),
                                "max_displacement_mm": r.get("max_displacement"),
                                "safety_factor": r.get("min_safety_factor"),
                            }
                        }

            # Build full context
            context = {
                "project_name": active_project["name"],
                "cad_format": active_project.get("cad_format", ""),
                "geometry": {
                    "volume_mm3": active_project["geometry"].get("volume"),
                    "surface_area_mm2": active_project["geometry"].get("surface_area"),
                    "is_thin_walled": active_project["geometry"].get("is_thin_walled"),
                    "has_holes": active_project["geometry"].get("has_holes"),
                },
                "history": st.session_state.chat_messages
            }
            context.update(active_job_context)
            
            # Streaming assistant response
            with st.chat_message("assistant"):
                token_placeholder = st.empty()
                full_response = ""
                
                # Standalone mode: stream directly if Claude is configured
                if st.session_state.op_mode == "Standalone" and STANDALONE_AVAILABLE:
                    if not settings.anthropic_api_key:
                        full_response = (
                            "I'm the CAE Analysis Assistant. The Claude API key is not configured in the `.env` file yet.\n\n"
                            "Based on your geometry:\n"
                            f"- The volume is **{context['geometry']['volume_mm3'] or 0:,.1f} mm³**\n"
                            f"- The surface area is **{context['geometry']['surface_area_mm2'] or 0:,.1f} mm²**\n"
                            f"- Thin-Walled classification: **{context['geometry']['is_thin_walled']}**\n\n"
                            "Please configure `ANTHROPIC_API_KEY` to enable active interactive reasoning."
                        )
                        token_placeholder.write(full_response)
                    else:
                        async def stream_from_claude():
                            response_text = ""
                            async for token in stream_chat_response(user_input, context):
                                response_text += token
                                token_placeholder.write(response_text)
                            return response_text
                        full_response = run_async(stream_from_claude())
                        
                elif st.session_state.op_mode == "API Client":
                    # Call API chat router and parse streaming response
                    try:
                        response_text = ""
                        for token in api_chat_stream(st.session_state.api_url, st.session_state.active_project_id, st.session_state.active_job_id, user_input):
                            response_text += token
                            token_placeholder.write(response_text)
                        full_response = response_text
                    except Exception as e:
                        full_response = f"Could not stream response from API: {e}"
                        token_placeholder.write(full_response)
                        
                st.session_state.chat_messages.append({"role": "assistant", "content": full_response})
