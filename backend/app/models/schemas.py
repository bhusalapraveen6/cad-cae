"""
Pydantic schemas for request/response validation and serialization.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator

from app.models.db_models import AnalysisType, JobStatus


# ── Shared ─────────────────────────────────────────────────────────────────────

class APIResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool = True
    message: str = ""
    data: Optional[Any] = None


# ── Material ───────────────────────────────────────────────────────────────────

class MaterialSchema(BaseModel):
    id: Optional[str] = None
    name: str
    category: str = "Metal"
    youngs_modulus: Optional[float] = None        # GPa
    poissons_ratio: Optional[float] = None
    density: Optional[float] = None               # kg/m³
    yield_strength: Optional[float] = None        # MPa
    ultimate_strength: Optional[float] = None     # MPa
    thermal_conductivity: Optional[float] = None  # W/(m·K)
    specific_heat: Optional[float] = None         # J/(kg·K)
    thermal_expansion: Optional[float] = None     # µm/(m·K)
    sn_curve_data: Optional[List[List[float]]] = None  # [[N_cycles, stress_amp], …]
    is_custom: bool = False

    model_config = {"from_attributes": True}


# ── Project ────────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    cad_filename: Optional[str]
    cad_format: Optional[str]
    cad_file_size: Optional[int]
    created_at: datetime
    updated_at: datetime
    job_count: int = 0

    model_config = {"from_attributes": True}


# ── Geometry ───────────────────────────────────────────────────────────────────

class BoundingBox(BaseModel):
    x: float  # mm
    y: float  # mm
    z: float  # mm


class GeometryFeaturesResponse(BaseModel):
    volume: Optional[float]              # mm³
    surface_area: Optional[float]        # mm²
    bounding_box: Optional[BoundingBox]
    center_of_mass: Optional[List[float]]  # [x, y, z]
    slenderness_ratio: Optional[float]
    surface_volume_ratio: Optional[float]

    # Feature flags
    is_thin_walled: bool = False
    has_holes: bool = False
    has_fillets: bool = False
    has_internal_cavity: bool = False
    has_symmetry: bool = False
    is_sheet_metal: bool = False

    # Mesh stats
    element_count: Optional[int] = None
    node_count: Optional[int] = None
    mesh_quality: Optional[float] = None

    model_config = {"from_attributes": True}


class AnalysisSuggestion(BaseModel):
    analysis_type: AnalysisType
    title: str
    rationale: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    icon: str = "gear"
    category: Literal["structural", "thermal", "cfd", "fatigue"] = "structural"
    priority: int = 1  # 1 = highest


# ── Boundary Conditions ────────────────────────────────────────────────────────

class FixedSupport(BaseModel):
    type: Literal["fixed"] = "fixed"
    face_ids: List[int] = Field(default_factory=list)
    description: str = ""


class Force(BaseModel):
    type: Literal["force"] = "force"
    face_ids: List[int] = Field(default_factory=list)
    fx: float = 0.0   # N
    fy: float = 0.0   # N
    fz: float = 0.0   # N
    description: str = ""


class Pressure(BaseModel):
    type: Literal["pressure"] = "pressure"
    face_ids: List[int] = Field(default_factory=list)
    magnitude: float = 0.0  # MPa
    description: str = ""


class HeatFlux(BaseModel):
    type: Literal["heat_flux"] = "heat_flux"
    face_ids: List[int] = Field(default_factory=list)
    flux: float = 0.0  # W/m²
    description: str = ""


class Convection(BaseModel):
    type: Literal["convection"] = "convection"
    face_ids: List[int] = Field(default_factory=list)
    film_coefficient: float = 10.0   # W/(m²·K)
    ambient_temperature: float = 25.0  # °C
    description: str = ""


class InletBC(BaseModel):
    type: Literal["inlet"] = "inlet"
    face_ids: List[int] = Field(default_factory=list)
    velocity: float = 1.0      # m/s
    pressure: Optional[float] = None  # Pa
    temperature: float = 20.0  # °C
    description: str = ""


BoundaryCondition = Union[FixedSupport, Force, Pressure, HeatFlux, Convection, InletBC]


# ── Analysis Parameters ────────────────────────────────────────────────────────

class MeshSettings(BaseModel):
    global_element_size: float = 5.0      # mm
    refinement_factor: float = 1.0        # 1.0 = coarse, 0.5 = fine
    min_element_size: Optional[float] = None
    element_order: Literal[1, 2] = 2      # linear or quadratic


class StaticStructuralParams(BaseModel):
    material: MaterialSchema
    boundary_conditions: List[Dict[str, Any]] = Field(default_factory=list)
    mesh_settings: MeshSettings = Field(default_factory=MeshSettings)
    nonlinear: bool = False
    load_steps: int = 1


class ModalParams(BaseModel):
    material: MaterialSchema
    boundary_conditions: List[Dict[str, Any]] = Field(default_factory=list)
    mesh_settings: MeshSettings = Field(default_factory=MeshSettings)
    num_modes: int = Field(default=10, ge=1, le=50)
    frequency_shift: float = 0.0   # Hz


class BucklingParams(BaseModel):
    material: MaterialSchema
    boundary_conditions: List[Dict[str, Any]] = Field(default_factory=list)
    mesh_settings: MeshSettings = Field(default_factory=MeshSettings)
    num_buckling_modes: int = Field(default=5, ge=1, le=20)


class ThermalParams(BaseModel):
    material: MaterialSchema
    boundary_conditions: List[Dict[str, Any]] = Field(default_factory=list)
    mesh_settings: MeshSettings = Field(default_factory=MeshSettings)
    steady_state: bool = True
    time_period: float = 1.0       # s (transient only)
    num_time_steps: int = 10       # (transient only)
    initial_temperature: float = 20.0  # °C


class FatigueParams(BaseModel):
    material: MaterialSchema
    static_job_id: str             # reference to completed static job
    mean_stress_correction: Literal["goodman", "soderberg", "gerber", "none"] = "goodman"
    stress_ratio: float = -1.0     # R = σ_min / σ_max
    safety_factor_target: float = 2.0


class CFDParams(BaseModel):
    fluid_density: float = 1.225   # kg/m³ (air default)
    dynamic_viscosity: float = 1.81e-5  # Pa·s
    boundary_conditions: List[Dict[str, Any]] = Field(default_factory=list)
    mesh_settings: MeshSettings = Field(default_factory=MeshSettings)
    solver: Literal["simpleFoam", "pisoFoam", "buoyantSimpleFoam"] = "simpleFoam"
    num_iterations: int = 500
    turbulence_model: Literal["laminar", "kEpsilon", "kOmegaSST"] = "kEpsilon"


# ── Job ────────────────────────────────────────────────────────────────────────

class JobCreate(BaseModel):
    project_id: str
    analysis_type: AnalysisType
    parameters: Dict[str, Any] = Field(default_factory=dict)


class JobResponse(BaseModel):
    id: str
    project_id: str
    analysis_type: AnalysisType
    status: JobStatus
    progress_percent: int
    progress_message: Optional[str]
    celery_task_id: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]

    model_config = {"from_attributes": True}


class JobProgressUpdate(BaseModel):
    """Sent via SSE during job execution."""
    job_id: str
    status: JobStatus
    progress_percent: int
    message: str
    timestamp: datetime


# ── Results ────────────────────────────────────────────────────────────────────

class ResultSummary(BaseModel):
    max_stress: Optional[float] = None        # MPa
    min_stress: Optional[float] = None        # MPa
    max_displacement: Optional[float] = None  # mm
    max_temperature: Optional[float] = None   # °C
    min_safety_factor: Optional[float] = None
    natural_frequencies: Optional[List[float]] = None  # Hz
    buckling_factors: Optional[List[float]] = None     # load multipliers
    fatigue_life_cycles: Optional[float] = None


class AnalysisResultResponse(BaseModel):
    id: str
    job_id: str
    summary: ResultSummary
    vtk_available: bool = False
    report_pdf_available: bool = False
    report_docx_available: bool = False
    result_data: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


# ── Chat ───────────────────────────────────────────────────────────────────────

class ChatMessageRequest(BaseModel):
    project_id: str
    job_id: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=4000)
    stream: bool = True


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    extra_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Upload ─────────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    project_id: str
    filename: str
    file_format: str
    file_size: int
    geometry_features: Optional[GeometryFeaturesResponse] = None
    suggestions: List[AnalysisSuggestion] = Field(default_factory=list)
