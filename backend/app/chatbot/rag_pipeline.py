"""RAG knowledge base initialization (ChromaDB + sentence-transformers)."""
from __future__ import annotations
import structlog
logger = structlog.get_logger(__name__)

async def init_knowledge_base():
    """Initialize ChromaDB with CAE knowledge docs."""
    try:
        import chromadb
        from app.config import settings
        client = chromadb.Client()
        collection = client.get_or_create_collection(settings.rag_collection_name)
        if collection.count() == 0:
            _seed_knowledge(collection)
            logger.info("RAG knowledge base seeded")
    except ImportError:
        logger.warning("chromadb not installed — RAG disabled")


def _seed_knowledge(collection):
    """Seed the vector store with CAE engineering knowledge."""
    docs = [
        {
            "id": "von_mises",
            "doc": "Von Mises stress is a scalar stress measure used to predict yielding under complex loading. "
                   "Yielding occurs when von Mises stress exceeds the material yield strength. "
                   "Formula: σ_vm = √(σ₁²+σ₂²+σ₃²−σ₁σ₂−σ₂σ₃−σ₁σ₃)",
        },
        {
            "id": "modal_analysis",
            "doc": "Modal analysis computes natural frequencies (eigenvalues) and mode shapes (eigenvectors) "
                   "of a structure. If operating frequency matches a natural frequency, resonance occurs. "
                   "CalculiX uses *FREQUENCY step with Lanczos method.",
        },
        {
            "id": "boundary_conditions",
            "doc": "Fixed support: constrains all 6 DOF (UX,UY,UZ,RX,RY,RZ). "
                   "Symmetry BC: constrains normal displacement and tangential rotations. "
                   "Force is applied in Newtons (N). Pressure in MPa (N/mm²).",
        },
        {
            "id": "mesh_convergence",
            "doc": "Mesh convergence: reduce element size by 50% and check if key results (max stress, "
                   "max displacement) change by less than 5%. Stress concentrations near holes/fillets "
                   "require local refinement. Second-order elements (C3D20R) are preferred for accuracy.",
        },
        {
            "id": "fatigue_sn",
            "doc": "S-N (Wöhler) curve relates stress amplitude to fatigue life in cycles. "
                   "Log-log interpolation between data points. Endurance limit (infinite life) "
                   "is typically 0.4×UTS for steel. Goodman correction: σ_a/S_e + σ_m/S_u = 1.",
        },
        {
            "id": "safety_factor",
            "doc": "Factor of Safety (FoS) = allowable stress / actual stress. "
                   "FoS < 1.0 → failure. FoS < 1.5 → marginal (re-examine loading assumptions). "
                   "FoS ≥ 2.0 → generally acceptable for static loads. "
                   "Safety-critical parts require FoS ≥ 3.0 and licensed engineer sign-off.",
        },
    ]
    collection.add(
        ids=[d["id"] for d in docs],
        documents=[d["doc"] for d in docs],
    )
