"""Input validation utilities."""

SECTORS = ["BTP", "Commerce", "Industrie", "Services", "Agriculture", "Finance", "Immobilier", "Transport", "Autre"]
SIZES = ["TPE", "PME", "ETI", "GE"]
FORMES_JURIDIQUES = ["SA", "SARL", "SAS", "EURL", "GIE"]


def validate_company_input(data: dict) -> list:
    """Validate company input data. Returns list of errors (empty if valid)."""
    errors = []
    
    if not data.get("company_name", "").strip():
        errors.append("Le nom de l'entreprise est requis.")
    
    if data.get("sector") and data["sector"] not in SECTORS:
        errors.append(f"Secteur invalide. Choix: {', '.join(SECTORS)}")
    
    if data.get("size") and data["size"] not in SIZES:
        errors.append(f"Taille invalide. Choix: {', '.join(SIZES)}")
    
    return errors
