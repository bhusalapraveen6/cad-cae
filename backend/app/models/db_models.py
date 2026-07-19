"""
SQLAlchemy ORM models for the CAD-CAE application.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Enums ──────────────────────────────────────────────────────────────────────

class JobStatus(str, enum.Enum):
    PENDING   = "pending"
    MESHING   = "meshing"
    SOLVING   = "solving"
    PARSING   = "parsing"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


class AnalysisType(str, enum.Enum):
    STATIC_STRUCTURAL = "static_structural"
    MODAL             = "modal"
    BUCKLING          = "buckling"
    NONLINEAR         = "nonlinear"
    THERMAL_STEADY    = "thermal_steady"
    THERMAL_TRANSIENT = "thermal_transient"
    THERMAL_STRUCTURAL= "thermal_structural"
    FATIGUE           = "fatigue"
    CFD_INTERNAL      = "cfd_internal"
    CFD_EXTERNAL      = "cfd_external"


# ── Models ─────────────────────────────────────────────────────────────────────

class User(Base):
    """User account model for authentication and scoping workspaces."""
    __tablename__ = "users"

    id:              Mapped[str]      = mapped_column(String(36), primary_key=True, default=_uuid)
    username:        Mapped[str]      = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str]      = mapped_column(String(255), nullable=False)
    gemini_api_key:  Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at:      Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    projects:        Mapped[list["Project"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id!r} username={self.username!r}>"


class Project(Base):
    """Top-level container for a CAD file and all its analyses."""
    __tablename__ = "projects"

    id:          Mapped[str]      = mapped_column(String(36), primary_key=True, default=_uuid)
    name:        Mapped[str]      = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at:  Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at:  Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # User scoping
    user_id:     Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)

    # CAD file metadata
    cad_filename:   Mapped[Optional[str]] = mapped_column(String(255))
    cad_format:     Mapped[Optional[str]] = mapped_column(String(20))   # step, iges, stl…
    cad_file_path:  Mapped[Optional[str]] = mapped_column(String(1024))
    cad_file_size:  Mapped[Optional[int]] = mapped_column(Integer)      # bytes

    # Relationships
    user:      Mapped[Optional["User"]]             = relationship(back_populates="projects")
    geometry:  Mapped[Optional["GeometryFeatures"]] = relationship(back_populates="project", cascade="all, delete-orphan", uselist=False)
    jobs:      Mapped[list["Job"]]                  = relationship(back_populates="project", cascade="all, delete-orphan", order_by="Job.created_at.desc()")

    def __repr__(self) -> str:
        return f"<Project id={self.id!r} name={self.name!r}>"


class GeometryFeatures(Base):
    """Auto-detected geometric features from the uploaded CAD file."""
    __tablename__ = "geometry_features"

    id:         Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), unique=True)

    # Basic geometry
    volume:       Mapped[Optional[float]] = mapped_column(Float)        # mm³
    surface_area: Mapped[Optional[float]] = mapped_column(Float)        # mm²
    bbox_x:       Mapped[Optional[float]] = mapped_column(Float)        # mm
    bbox_y:       Mapped[Optional[float]] = mapped_column(Float)        # mm
    bbox_z:       Mapped[Optional[float]] = mapped_column(Float)        # mm
    center_of_mass: Mapped[Optional[str]] = mapped_column(String(100))  # "x,y,z"

    # Derived ratios
    slenderness_ratio: Mapped[Optional[float]] = mapped_column(Float)
    surface_volume_ratio: Mapped[Optional[float]] = mapped_column(Float)

    # Feature flags
    is_thin_walled:     Mapped[bool] = mapped_column(Boolean, default=False)
    has_holes:          Mapped[bool] = mapped_column(Boolean, default=False)
    has_fillets:        Mapped[bool] = mapped_column(Boolean, default=False)
    has_internal_cavity:Mapped[bool] = mapped_column(Boolean, default=False)
    has_symmetry:       Mapped[bool] = mapped_column(Boolean, default=False)
    is_sheet_metal:     Mapped[bool] = mapped_column(Boolean, default=False)

    # Mesh stats (populated after meshing)
    element_count: Mapped[Optional[int]]   = mapped_column(Integer)
    node_count:    Mapped[Optional[int]]   = mapped_column(Integer)
    mesh_quality:  Mapped[Optional[float]] = mapped_column(Float)  # 0-1, higher is better

    # Raw feature data as JSON
    raw_features: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    # Analysis suggestions (list of dicts: [{type, rationale, confidence}])
    suggestions: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    project: Mapped["Project"] = relationship(back_populates="geometry")

    def __repr__(self) -> str:
        return f"<GeometryFeatures project_id={self.project_id!r}>"


class Job(Base):
    """A single analysis job (one analysis type, one parameter set)."""
    __tablename__ = "jobs"

    id:         Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))

    analysis_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(
        Enum(JobStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=JobStatus.PENDING
    )
    celery_task_id:Mapped[Optional[str]] = mapped_column(String(255))

    # Parameters as JSON blob (material, BCs, mesh settings, solver settings)
    parameters: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    # Progress tracking
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    progress_message: Mapped[Optional[str]] = mapped_column(String(500))
    log_messages: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    # Timing
    created_at:   Mapped[datetime]          = mapped_column(DateTime, default=func.now())
    started_at:   Mapped[Optional[datetime]]= mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]]= mapped_column(DateTime, nullable=True)

    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    project: Mapped["Project"]                       = relationship(back_populates="jobs")
    result:  Mapped[Optional["AnalysisResult"]]      = relationship(back_populates="job", cascade="all, delete-orphan", uselist=False)
    chat_messages: Mapped[list["ChatMessage"]]        = relationship(back_populates="job", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Job id={self.id!r} types={self.analysis_types!r} status={self.status!r}>"


class AnalysisResult(Base):
    """Parsed results from a completed analysis job."""
    __tablename__ = "analysis_results"

    id:     Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), unique=True)

    # Scalar summary values
    max_stress:       Mapped[Optional[float]] = mapped_column(Float)   # MPa (von Mises)
    min_stress:       Mapped[Optional[float]] = mapped_column(Float)
    max_displacement: Mapped[Optional[float]] = mapped_column(Float)   # mm
    max_temperature:  Mapped[Optional[float]] = mapped_column(Float)   # °C
    min_safety_factor:Mapped[Optional[float]] = mapped_column(Float)
    natural_frequencies: Mapped[Optional[list]] = mapped_column(JSON)  # [Hz, Hz, …]
    buckling_factors:    Mapped[Optional[list]] = mapped_column(JSON)  # [multiplier, …]
    fatigue_life_cycles: Mapped[Optional[float]]= mapped_column(Float)

    # File paths to result data
    vtk_file_path:    Mapped[Optional[str]] = mapped_column(String(1024))   # .vtu for 3D viewer
    report_pdf_path:  Mapped[Optional[str]] = mapped_column(String(1024))
    report_docx_path: Mapped[Optional[str]] = mapped_column(String(1024))

    # Full result data as JSON (for smaller datasets)
    result_data: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    job: Mapped["Job"] = relationship(back_populates="result")

    def __repr__(self) -> str:
        return f"<AnalysisResult job_id={self.job_id!r}>"


class ChatMessage(Base):
    """A message in the project chatbot conversation."""
    __tablename__ = "chat_messages"

    id:         Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    job_id:     Mapped[Optional[str]] = mapped_column(ForeignKey("jobs.id"), nullable=True)

    role:    Mapped[str] = mapped_column(String(20))  # "user" | "assistant" | "system"
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Extra metadata: citations, tool calls, etc. (renamed to avoid SQLAlchemy reserved word)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    project: Mapped["Project"] = relationship()
    job:     Mapped[Optional["Job"]] = relationship(back_populates="chat_messages")

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id!r} role={self.role!r}>"


class Material(Base):
    """Built-in material library."""
    __tablename__ = "materials"

    id:   Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(50))  # Metal, Plastic, Composite…

    # Mechanical properties
    youngs_modulus:   Mapped[Optional[float]] = mapped_column(Float)   # GPa
    poissons_ratio:   Mapped[Optional[float]] = mapped_column(Float)
    density:          Mapped[Optional[float]] = mapped_column(Float)   # kg/m³
    yield_strength:   Mapped[Optional[float]] = mapped_column(Float)   # MPa
    ultimate_strength:Mapped[Optional[float]] = mapped_column(Float)   # MPa

    # Thermal properties
    thermal_conductivity: Mapped[Optional[float]] = mapped_column(Float)  # W/(m·K)
    specific_heat:        Mapped[Optional[float]] = mapped_column(Float)  # J/(kg·K)
    thermal_expansion:    Mapped[Optional[float]] = mapped_column(Float)  # 1/K ×10⁻⁶

    # S-N curve data (JSON list of [cycles, stress_amplitude] pairs)
    sn_curve_data: Mapped[Optional[list]] = mapped_column(JSON)

    is_custom:  Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"<Material name={self.name!r}>"
