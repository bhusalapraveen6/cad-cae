"""Seed the material library on first startup."""
from __future__ import annotations
import structlog
from app.database import get_db_context
from app.models.db_models import Material
from sqlalchemy import select

logger = structlog.get_logger(__name__)

BUILTIN_MATERIALS = [
    {"name": "Structural Steel (A36)", "category": "Metal",
     "youngs_modulus": 200.0, "poissons_ratio": 0.26, "density": 7850.0,
     "yield_strength": 250.0, "ultimate_strength": 400.0,
     "thermal_conductivity": 50.0, "specific_heat": 490.0, "thermal_expansion": 12.0,
     "sn_curve_data": [[1e3,500],[1e4,350],[1e5,250],[1e6,180],[2e6,160],[1e7,145]]},
    {"name": "Stainless Steel 304", "category": "Metal",
     "youngs_modulus": 193.0, "poissons_ratio": 0.29, "density": 8000.0,
     "yield_strength": 215.0, "ultimate_strength": 505.0,
     "thermal_conductivity": 16.2, "specific_heat": 500.0, "thermal_expansion": 17.2},
    {"name": "Aluminium 6061-T6", "category": "Metal",
     "youngs_modulus": 68.9, "poissons_ratio": 0.33, "density": 2700.0,
     "yield_strength": 276.0, "ultimate_strength": 310.0,
     "thermal_conductivity": 167.0, "specific_heat": 896.0, "thermal_expansion": 23.6},
    {"name": "Titanium Ti-6Al-4V", "category": "Metal",
     "youngs_modulus": 114.0, "poissons_ratio": 0.34, "density": 4430.0,
     "yield_strength": 880.0, "ultimate_strength": 950.0,
     "thermal_conductivity": 6.7, "specific_heat": 526.0, "thermal_expansion": 8.6},
    {"name": "Cast Iron (Grey)", "category": "Metal",
     "youngs_modulus": 100.0, "poissons_ratio": 0.26, "density": 7200.0,
     "yield_strength": 100.0, "ultimate_strength": 200.0,
     "thermal_conductivity": 46.0, "specific_heat": 500.0},
    {"name": "Nylon 6/6 (PA66)", "category": "Plastic",
     "youngs_modulus": 3.3, "poissons_ratio": 0.39, "density": 1140.0,
     "yield_strength": 80.0, "ultimate_strength": 85.0,
     "thermal_conductivity": 0.25, "specific_heat": 1600.0, "thermal_expansion": 80.0},
    {"name": "ABS Plastic", "category": "Plastic",
     "youngs_modulus": 2.3, "poissons_ratio": 0.35, "density": 1050.0,
     "yield_strength": 40.0, "ultimate_strength": 45.0,
     "thermal_conductivity": 0.17, "specific_heat": 1400.0},
    {"name": "Carbon Fibre CFRP (UD)", "category": "Composite",
     "youngs_modulus": 135.0, "poissons_ratio": 0.30, "density": 1600.0,
     "yield_strength": 600.0, "ultimate_strength": 800.0,
     "thermal_conductivity": 5.0, "specific_heat": 710.0},
    {"name": "Air (20°C)", "category": "Fluid",
     "density": 1.225, "specific_heat": 1005.0, "thermal_conductivity": 0.0257},
    {"name": "Water (20°C)", "category": "Fluid",
     "density": 998.0, "specific_heat": 4182.0, "thermal_conductivity": 0.598},
]


async def seed_materials():
    async with get_db_context() as db:
        existing = (await db.execute(select(Material))).scalars().first()
        if existing:
            return
        for m in BUILTIN_MATERIALS:
            mat = Material(**m)
            db.add(mat)
    logger.info("Material library seeded", count=len(BUILTIN_MATERIALS))
