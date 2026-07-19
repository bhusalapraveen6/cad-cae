"""
Results parser and report generator.
Generates fully-detailed PDF and Word reports summarizing materials, boundary conditions, mesh, and results.
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import db_models as M

logger = structlog.get_logger(__name__)


async def generate_reports_for_job(job_id: str, db: AsyncSession) -> tuple[Path | None, Path | None]:
    """Generates both PDF and DOCX reports for a job and updates the DB paths."""
    job = (await db.execute(select(M.Job).where(M.Job.id == job_id))).scalar_one_or_none()
    if not job:
        return None, None

    project = (await db.execute(select(M.Project).where(M.Project.id == job.project_id))).scalar_one_or_none()
    geo = (await db.execute(select(M.GeometryFeatures).where(M.GeometryFeatures.project_id == job.project_id))).scalar_one_or_none()
    res = (await db.execute(select(M.AnalysisResult).where(M.AnalysisResult.job_id == job_id))).scalar_one_or_none()

    if not res:
        return None, None

    # Determine paths
    storage_dir = Path(settings.local_storage_path) / "reports"
    storage_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = storage_dir / f"{job_id}_report.pdf"
    docx_path = storage_dir / f"{job_id}_report.docx"

    try:
        # Build PDF
        _build_pdf(pdf_path, job, project, geo, res)
        res.report_pdf_path = str(pdf_path)
    except Exception as e:
        logger.error("Failed to generate PDF report", job_id=job_id, error=str(e))
        pdf_path = None

    try:
        # Build DOCX
        _build_docx(docx_path, job, project, geo, res)
        res.report_docx_path = str(docx_path)
    except Exception as e:
        logger.error("Failed to generate DOCX report", job_id=job_id, error=str(e))
        docx_path = None

    await db.commit()
    return pdf_path, docx_path


def _build_pdf(output_path: Path, job: M.Job, project: M.Project | None, geo: M.GeometryFeatures | None, res: M.AnalysisResult):
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    doc = SimpleDocTemplate(str(output_path), pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        name='TitleStyle',
        parent=styles['Heading1'],
        textColor=colors.HexColor('#002d62'),
        spaceAfter=15
    )
    section_style = ParagraphStyle(
        name='SectionStyle',
        parent=styles['Heading2'],
        textColor=colors.HexColor('#004b93'),
        spaceBefore=12,
        spaceAfter=6
    )

    # Title & Metadata
    story.append(Paragraph("CAD-CAE Simulation Analysis Report", title_style))
    story.append(Paragraph(f"<b>Job ID:</b> {job.id}", styles['Normal']))
    story.append(Paragraph(f"<b>Project Name:</b> {project.name if project else 'N/A'}", styles['Normal']))
    story.append(Paragraph(f"<b>Generated At:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}", styles['Normal']))
    story.append(Spacer(1, 15))

    # Section 1: Analysis Inputs
    story.append(Paragraph("1. Analysis Inputs", section_style))
    story.append(Spacer(1, 4))

    # Geometry / Mesh inputs
    mesh_size = "N/A"
    element_order = "N/A"
    materials_list = []
    bcs_list = []

    if job.parameters:
        for atype, params in job.parameters.items():
            if not isinstance(params, dict):
                continue
            # Material
            mat = params.get("material")
            if mat and isinstance(mat, dict):
                mat_name = mat.get("name", "Unknown")
                mat_props = []
                if mat.get("youngs_modulus"): mat_props.append(f"E: {mat.get('youngs_modulus')} MPa")
                if mat.get("poissons_ratio"): mat_props.append(f"Nu: {mat.get('poissons_ratio')}")
                if mat.get("density"): mat_props.append(f"Density: {mat.get('density')} kg/mm³")
                mat_desc = f"{mat_name} ({', '.join(mat_props)})"
                if mat_desc not in materials_list:
                    materials_list.append(mat_desc)

            # Mesh Settings
            mesh_set = params.get("mesh_settings")
            if mesh_set and isinstance(mesh_set, dict):
                mesh_size = f"{mesh_set.get('global_element_size', '5.0')} mm"
                element_order = f"Quadratic (Order {mesh_set.get('element_order', 2)})"

            # BCs
            bcs = params.get("boundary_conditions")
            if bcs and isinstance(bcs, list):
                for bc in bcs:
                    if not isinstance(bc, dict):
                        continue
                    bc_type = bc.get("type", "Unknown").replace("_", " ").title()
                    bc_faces = f"Faces: {bc.get('face_ids', [])}"
                    bc_vals = []
                    for k, v in bc.items():
                        if k not in ("type", "face_ids", "description") and isinstance(v, (int, float)):
                            bc_vals.append(f"{k}: {v}")
                    bc_desc = f"{bc_type} on {bc_faces}"
                    if bc_vals:
                        bc_desc += f" ({', '.join(bc_vals)})"
                    if bc_desc not in bcs_list:
                        bcs_list.append(bc_desc)

    inputs_data = [
        ["Input Parameter", "Value / Details"],
        ["Analysis Types Run", ", ".join(job.analysis_types).replace("_", " ").title()],
        ["Material Name(s)", "\n".join(materials_list) if materials_list else "N/A"],
        ["Boundary Conditions", "\n".join(bcs_list) if bcs_list else "N/A"],
        ["Target Global Mesh Size", mesh_size],
        ["Element Order / Type", element_order],
        ["Element Count", f"{geo.element_count:,}" if geo and geo.element_count else "N/A"],
        ["Node Count", f"{geo.node_count:,}" if geo and geo.node_count else "N/A"]
    ]

    t_inputs = Table(inputs_data, colWidths=[180, 320])
    t_inputs.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#004b93')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d5dd')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f9fafb')])
    ]))
    story.append(t_inputs)
    story.append(Spacer(1, 15))

    # Section 2: Results Summary
    story.append(Paragraph("2. Simulation Scalar Results", section_style))
    story.append(Spacer(1, 4))

    results_data = [["Metric", "Value", "Unit"]]
    if res.max_stress is not None:
        results_data.append(["Max von Mises Stress", f"{res.max_stress:,.2f}", "MPa"])
    if res.min_stress is not None:
        results_data.append(["Min von Mises Stress", f"{res.min_stress:,.2f}", "MPa"])
    if res.max_displacement is not None:
        results_data.append(["Max Displacement", f"{res.max_displacement:,.4f}", "mm"])
    if res.min_safety_factor is not None:
        results_data.append(["Min Safety Factor", f"{res.min_safety_factor:,.2f}", "-"])
    if res.max_temperature is not None:
        results_data.append(["Max Temperature", f"{res.max_temperature:,.1f}", "°C"])
    if res.natural_frequencies:
        results_data.append(["Natural Frequencies (Modes 1-3)", ", ".join([f"{f:.1f} Hz" for f in res.natural_frequencies[:3]]), "Hz"])
    if res.buckling_factors:
        results_data.append(["Buckling Load Multipliers", ", ".join([f"{f:.2f}x" for f in res.buckling_factors[:3]]), "x"])
    if res.fatigue_life_cycles is not None:
        results_data.append(["Min Fatigue Life", f"{res.fatigue_life_cycles:,.0f}", "cycles"])

    t_res = Table(results_data, colWidths=[200, 200, 100])
    t_res.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2979ff')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d5dd')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f9fafb')])
    ]))
    story.append(t_res)
    story.append(Spacer(1, 20))
    story.append(Paragraph("<i>Disclaimer: This report is a decision-support helper. Final engineering decisions require approval by a licensed professional engineer.</i>", styles['Italic']))

    doc.build(story)


def _build_docx(output_path: Path, job: M.Job, project: M.Project | None, geo: M.GeometryFeatures | None, res: M.AnalysisResult):
    from docx import Document

    doc = Document()
    doc.add_heading("CAD-CAE Simulation Analysis Report", level=0)

    # Metadata
    doc.add_paragraph(f"Job ID: {job.id}")
    doc.add_paragraph(f"Project Name: {project.name if project else 'N/A'}")
    doc.add_paragraph(f"Generated At: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

    # Section 1: Analysis Inputs
    doc.add_heading("1. Analysis Inputs", level=1)
    
    mesh_size = "N/A"
    element_order = "N/A"
    materials_list = []
    bcs_list = []

    if job.parameters:
        for atype, params in job.parameters.items():
            if not isinstance(params, dict):
                continue
            mat = params.get("material")
            if mat and isinstance(mat, dict):
                mat_name = mat.get("name", "Unknown")
                mat_props = []
                if mat.get("youngs_modulus"): mat_props.append(f"E: {mat.get('youngs_modulus')} MPa")
                if mat.get("poissons_ratio"): mat_props.append(f"Nu: {mat.get('poissons_ratio')}")
                if mat.get("density"): mat_props.append(f"Density: {mat.get('density')} kg/mm³")
                mat_desc = f"{mat_name} ({', '.join(mat_props)})"
                if mat_desc not in materials_list:
                    materials_list.append(mat_desc)

            mesh_set = params.get("mesh_settings")
            if mesh_set and isinstance(mesh_set, dict):
                mesh_size = f"{mesh_set.get('global_element_size', '5.0')} mm"
                element_order = f"Quadratic (Order {mesh_set.get('element_order', 2)})"

            bcs = params.get("boundary_conditions")
            if bcs and isinstance(bcs, list):
                for bc in bcs:
                    if not isinstance(bc, dict):
                        continue
                    bc_type = bc.get("type", "Unknown").replace("_", " ").title()
                    bc_faces = f"Faces: {bc.get('face_ids', [])}"
                    bc_vals = []
                    for k, v in bc.items():
                        if k not in ("type", "face_ids", "description") and isinstance(v, (int, float)):
                            bc_vals.append(f"{k}: {v}")
                    bc_desc = f"{bc_type} on {bc_faces}"
                    if bc_vals:
                        bc_desc += f" ({', '.join(bc_vals)})"
                    if bc_desc not in bcs_list:
                        bcs_list.append(bc_desc)

    table_inputs = doc.add_table(rows=1, cols=2)
    table_inputs.style = 'Table Grid'
    hdr_cells = table_inputs.rows[0].cells
    hdr_cells[0].text = "Input Parameter"
    hdr_cells[1].text = "Value / Details"

    inputs = [
        ("Analysis Types Run", ", ".join(job.analysis_types).replace("_", " ").title()),
        ("Material Name(s)", "\n".join(materials_list) if materials_list else "N/A"),
        ("Boundary Conditions", "\n".join(bcs_list) if bcs_list else "N/A"),
        ("Target Global Mesh Size", mesh_size),
        ("Element Order / Type", element_order),
        ("Element Count", f"{geo.element_count:,}" if geo and geo.element_count else "N/A"),
        ("Node Count", f"{geo.node_count:,}" if geo and geo.node_count else "N/A")
    ]

    for param, val in inputs:
        row_cells = table_inputs.add_row().cells
        row_cells[0].text = param
        row_cells[1].text = val

    # Section 2: Results
    doc.add_heading("2. Simulation Scalar Results", level=1)
    
    table_res = doc.add_table(rows=1, cols=3)
    table_res.style = 'Table Grid'
    hdr_cells = table_res.rows[0].cells
    hdr_cells[0].text = "Metric"
    hdr_cells[1].text = "Value"
    hdr_cells[2].text = "Unit"

    def add_res_row(m, v, u):
        row_cells = table_res.add_row().cells
        row_cells[0].text = str(m)
        row_cells[1].text = str(v)
        row_cells[2].text = str(u)

    if res.max_stress is not None:
        add_res_row("Max von Mises Stress", f"{res.max_stress:,.2f}", "MPa")
    if res.min_stress is not None:
        add_res_row("Min von Mises Stress", f"{res.min_stress:,.2f}", "MPa")
    if res.max_displacement is not None:
        add_res_row("Max Displacement", f"{res.max_displacement:,.4f}", "mm")
    if res.min_safety_factor is not None:
        add_res_row("Min Safety Factor", f"{res.min_safety_factor:,.2f}", "-")
    if res.max_temperature is not None:
        add_res_row("Max Temperature", f"{res.max_temperature:,.1f}", "°C")
    if res.natural_frequencies:
        add_res_row("Natural Frequencies (Modes 1-3)", ", ".join([f"{f:.1f} Hz" for f in res.natural_frequencies[:3]]), "Hz")
    if res.buckling_factors:
        add_res_row("Buckling Load Multipliers", ", ".join([f"{f:.2f}x" for f in res.buckling_factors[:3]]), "x")
    if res.fatigue_life_cycles is not None:
        add_res_row("Min Fatigue Life", f"{res.fatigue_life_cycles:,.0f}", "cycles")

    doc.add_paragraph("\nDisclaimer: This report is a decision-support helper. Final engineering decisions require approval by a licensed professional engineer.")
    
    doc.save(str(output_path))
