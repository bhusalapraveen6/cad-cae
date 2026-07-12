"""
Analysis Suggestion Engine.
Maps detected geometry features + optional user context to a ranked list
of recommended CAE analyses with rationale strings and confidence scores.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import structlog

from app.geometry_analysis.feature_extractor import GeometryFeatures
from app.models.db_models import AnalysisType

logger = structlog.get_logger(__name__)


@dataclass
class SuggestionResult:
    analysis_type: AnalysisType
    title: str
    rationale: str
    confidence: float           # 0.0 – 1.0
    priority: int               # 1 = highest
    icon: str
    category: str               # structural | thermal | cfd | fatigue


# Human-readable titles and icons per analysis type
_META: Dict[AnalysisType, Dict] = {
    AnalysisType.STATIC_STRUCTURAL: {
        "title": "Static Structural",
        "icon": "FaBolt",
        "category": "structural",
    },
    AnalysisType.MODAL: {
        "title": "Modal Analysis",
        "icon": "FaWaveSquare",
        "category": "structural",
    },
    AnalysisType.BUCKLING: {
        "title": "Buckling Analysis",
        "icon": "FaCompress",
        "category": "structural",
    },
    AnalysisType.NONLINEAR: {
        "title": "Nonlinear Structural",
        "icon": "FaProjectDiagram",
        "category": "structural",
    },
    AnalysisType.THERMAL_STEADY: {
        "title": "Thermal (Steady-State)",
        "icon": "FaFire",
        "category": "thermal",
    },
    AnalysisType.THERMAL_TRANSIENT: {
        "title": "Thermal (Transient)",
        "icon": "FaThermometerHalf",
        "category": "thermal",
    },
    AnalysisType.THERMAL_STRUCTURAL: {
        "title": "Thermal-Structural Coupled",
        "icon": "FaLayerGroup",
        "category": "thermal",
    },
    AnalysisType.FATIGUE: {
        "title": "Fatigue Life (S-N)",
        "icon": "FaExclamationTriangle",
        "category": "fatigue",
    },
    AnalysisType.CFD_INTERNAL: {
        "title": "CFD — Internal Flow",
        "icon": "FaWind",
        "category": "cfd",
    },
    AnalysisType.CFD_EXTERNAL: {
        "title": "CFD — External Flow",
        "icon": "FaWater",
        "category": "cfd",
    },
}


def suggest_analyses(
    features: GeometryFeatures,
    user_context: Optional[Dict] = None,
) -> List[SuggestionResult]:
    """
    Rule-based suggestion engine.
    Produces a deduplicated, priority-sorted list of analysis recommendations.

    user_context keys (all optional):
      - "use_case": str   e.g. "bracket", "heat_sink", "pipe", "pressure_vessel"
      - "cyclic_load": bool
      - "high_temperature": bool
      - "fluid_flow": bool
      - "safety_critical": bool
    """
    if user_context is None:
        user_context = {}

    suggestions: List[SuggestionResult] = []

    def add(atype: AnalysisType, rationale: str, confidence: float, priority: int = 5):
        meta = _META[atype]
        suggestions.append(SuggestionResult(
            analysis_type=atype,
            title=meta["title"],
            rationale=rationale,
            confidence=min(max(confidence, 0.0), 1.0),
            priority=priority,
            icon=meta["icon"],
            category=meta["category"],
        ))

    use_case = user_context.get("use_case", "").lower()

    # ── Static Structural — always recommended ─────────────────────────────────
    add(
        AnalysisType.STATIC_STRUCTURAL,
        "Baseline stress and deformation check recommended for all structural parts.",
        confidence=0.95,
        priority=1,
    )

    # ── Modal — recommend broadly ──────────────────────────────────────────────
    add(
        AnalysisType.MODAL,
        "Natural frequency check recommended to verify no resonance with operating loads.",
        confidence=0.85,
        priority=2,
    )

    # ── Thin-wall → thermal ────────────────────────────────────────────────────
    if features.is_thin_walled:
        add(
            AnalysisType.THERMAL_STEADY,
            f"Thin-walled geometry (surface/volume ratio = {features.surface_volume_ratio:.2f} mm⁻¹) "
            "is a good candidate for thermal analysis — check heat dissipation.",
            confidence=0.80,
            priority=3,
        )
        if user_context.get("high_temperature"):
            add(
                AnalysisType.THERMAL_STRUCTURAL,
                "High operating temperature detected: thermal-structural coupling recommended to capture thermally induced stresses.",
                confidence=0.88,
                priority=2,
            )

    # ── Holes / fillets → fatigue ──────────────────────────────────────────────
    if features.has_holes or features.has_fillets:
        add(
            AnalysisType.FATIGUE,
            "Stress concentrators (holes/fillets) detected — fatigue life check strongly recommended for cyclic loads.",
            confidence=0.85 if user_context.get("cyclic_load") else 0.65,
            priority=3 if user_context.get("cyclic_load") else 4,
        )

    if user_context.get("cyclic_load"):
        add(
            AnalysisType.FATIGUE,
            "User indicated cyclic loading — fatigue S-N analysis required.",
            confidence=0.90,
            priority=2,
        )

    # ── Internal cavity → CFD ─────────────────────────────────────────────────
    if features.has_internal_cavity or user_context.get("fluid_flow"):
        add(
            AnalysisType.CFD_INTERNAL,
            "Internal flow path detected — CFD analysis recommended to evaluate pressure drop, flow distribution, and heat transfer.",
            confidence=0.80,
            priority=3,
        )

    # ── Slender → buckling ────────────────────────────────────────────────────
    if features.is_slender:
        add(
            AnalysisType.BUCKLING,
            f"High slenderness ratio ({features.slenderness_ratio:.1f}) under compressive loads "
            "creates buckling risk — linear buckling analysis recommended.",
            confidence=0.78,
            priority=3,
        )

    # ── Use-case specific rules ────────────────────────────────────────────────
    if "heat sink" in use_case or "heatsink" in use_case:
        add(
            AnalysisType.THERMAL_STEADY,
            "Heat sink application: steady-state thermal analysis to optimise fin effectiveness.",
            confidence=0.92,
            priority=1,
        )
        add(
            AnalysisType.CFD_EXTERNAL,
            "Natural/forced convection CFD recommended for accurate heat transfer coefficient estimation.",
            confidence=0.80,
            priority=2,
        )

    if "pressure vessel" in use_case or "tank" in use_case:
        add(
            AnalysisType.STATIC_STRUCTURAL,
            "Pressure vessel: static structural under internal pressure (per ASME BPVC Section VIII).",
            confidence=0.95,
            priority=1,
        )
        add(
            AnalysisType.FATIGUE,
            "Pressure vessels are subject to cyclic pressurisation — fatigue life assessment is required by most design codes.",
            confidence=0.88,
            priority=2,
        )
        add(
            AnalysisType.BUCKLING,
            "External pressure scenarios require buckling analysis for thin-walled vessels.",
            confidence=0.72,
            priority=3,
        )

    if "pipe" in use_case or "duct" in use_case:
        add(
            AnalysisType.CFD_INTERNAL,
            "Pipe/duct geometry: internal flow CFD to compute velocity profiles, pressure drop, and Re.",
            confidence=0.90,
            priority=1,
        )
        add(
            AnalysisType.THERMAL_STRUCTURAL,
            "Thermal expansion stresses in piping systems: coupled thermal-structural analysis.",
            confidence=0.70,
            priority=4,
        )

    if "bracket" in use_case or "mount" in use_case:
        add(
            AnalysisType.STATIC_STRUCTURAL,
            "Bracket/mount: check load-path efficiency and factor of safety under worst-case load.",
            confidence=0.95,
            priority=1,
        )

    if user_context.get("safety_critical"):
        add(
            AnalysisType.NONLINEAR,
            "Safety-critical part: nonlinear analysis recommended to capture plasticity, large deformation, and contact effects.",
            confidence=0.75,
            priority=4,
        )

    # ── Deduplicate by analysis_type, keeping highest confidence ──────────────
    seen: Dict[AnalysisType, SuggestionResult] = {}
    for s in suggestions:
        if s.analysis_type not in seen or s.confidence > seen[s.analysis_type].confidence:
            seen[s.analysis_type] = s

    results = list(seen.values())
    results.sort(key=lambda x: (x.priority, -x.confidence))

    logger.info("Analysis suggestions generated", count=len(results))
    return results
