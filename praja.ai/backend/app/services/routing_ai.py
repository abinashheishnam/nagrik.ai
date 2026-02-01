from __future__ import annotations

# Simple category -> department router (Phase-2 MVP)
# Later this becomes ML-driven with workload, district, and officer assignment.

CATEGORY_TO_DEPT = {
    "emergency_disaster": "Emergency Response / Fire & Ambulance",
    "public_safety_law": "Police / Law & Order",
    "healthcare": "Health Department / Hospitals",
    "roads_transport": "Public Works / Roads",
    "water_supply": "Public Health Engineering / Water",
    "electricity": "Electricity Department",
    "sanitation_waste": "Municipal Sanitation / Waste",
    "drainage_flooding": "Drainage & Flood Control / Municipal",
    "education": "Education Department",
    "government_services": "District Administration / Citizen Services",
    "environment": "Environment / Forest Department",
    "housing_land": "Revenue / Land & Housing",
    "other": "General Administration",
}

def suggest_department(category_id: str) -> str:
    return CATEGORY_TO_DEPT.get(category_id, "General Administration")
