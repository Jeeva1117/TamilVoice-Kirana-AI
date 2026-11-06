"""Product Catalog Resolver Service: Bilingual Tamil/Tanglish/English matching."""
from enum import Enum
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from backend.app.models.product import Product
from backend.app.schemas.ai import ResolvedProduct


class ResolutionStatus(str, Enum):
    MATCH = "MATCH"
    MULTIPLE_MATCHES = "MULTIPLE_MATCHES"
    NO_MATCH = "NO_MATCH"


# Bilingual synonym map: maps search tokens/stems to search keywords in English and Tamil
SYNONYM_KEYWORDS = {
    # Rice
    "rice": ["rice", "ponni", "அரிசி"],
    "arisi": ["rice", "ponni", "அரிசி"],
    "ponni": ["rice", "ponni", "அரிசி"],
    "அரிசி": ["rice", "ponni", "அரிசி"],
    "புழுங்கல்": ["rice", "ponni", "அரிசி"],
    "சாப்பாடு அரிசி": ["rice", "ponni", "அரிசி"],

    # Oil
    "oil": ["oil", "sunflower", "எண்ணெய்"],
    "sunflower": ["oil", "sunflower", "எண்ணெய்"],
    "ennai": ["oil", "sunflower", "எண்ணெய்"],
    "enna": ["oil", "sunflower", "எண்ணெய்"],
    "எண்ணெய்": ["oil", "sunflower", "எண்ணெய்"],
    "சூரியகாந்தி": ["oil", "sunflower", "எண்ணெய்"],

    # Atta / Wheat Flour
    "atta": ["atta", "wheat", "godhumai", "கோதுமை"],
    "wheat": ["atta", "wheat", "godhumai", "கோதுமை"],
    "godhumai": ["atta", "wheat", "godhumai", "கோதுமை"],
    "kothumai": ["atta", "wheat", "godhumai", "கோதுமை"],
    "கோதுமை": ["atta", "wheat", "godhumai", "கோதுமை"],
    "மாவு": ["atta", "wheat", "godhumai", "கோதுமை"],

    # Salt
    "salt": ["salt", "uppu", "உப்பு"],
    "tata salt": ["salt", "uppu", "உப்பு"],
    "uppu": ["salt", "uppu", "உப்பு"],
    "உப்பு": ["salt", "uppu", "உப்பு"],

    # Sugar
    "sugar": ["sugar", "sakkarai", "சர்க்கரை"],
    "sakkarai": ["sugar", "sakkarai", "சர்க்கரை"],
    "sarkarai": ["sugar", "sakkarai", "சர்க்கரை"],
    "சர்க்கரை": ["sugar", "sakkarai", "சர்க்கரை"],
    "சீனி": ["sugar", "sakkarai", "சர்க்கரை"],

    # Milk
    "milk": ["milk", "aavin", "பால்"],
    "paal": ["milk", "aavin", "பால்"],
    "பால்": ["milk", "aavin", "பால்"],
    "aavin": ["milk", "aavin", "பால்"],
    "ஆவின்": ["milk", "aavin", "பால்"],

    # Red Chili
    "chili": ["chili", "chilli", "milagai", "மிளகாய்"],
    "chilli": ["chili", "chilli", "milagai", "மிளகாய்"],
    "milagai": ["chili", "chilli", "milagai", "மிளகாய்"],
    "மிளகாய்": ["chili", "chilli", "milagai", "மிளகாய்"],
    "வற்றல்": ["chili", "chilli", "milagai", "மிளகாய்"],

    # Soap
    "soap": ["soap", "sandal", "சோப்பு"],
    "sandal": ["soap", "sandal", "சோப்பு"],
    "mysore sandal": ["soap", "sandal", "சோப்பு"],
    "சோப்பு": ["soap", "sandal", "சோப்பு"],
    "சந்தனம்": ["soap", "sandal", "சோப்பு"],

    # Coffee
    "coffee": ["coffee", "bru", "காபி"],
    "kaapi": ["coffee", "bru", "காபி"],
    "bru": ["coffee", "bru", "காபி"],
    "காபி": ["coffee", "bru", "காபி"],
    "ப்ரூ": ["coffee", "bru", "காபி"],

    # Eggs
    "egg": ["egg", "muttai", "முட்டை"],
    "eggs": ["egg", "muttai", "முட்டை"],
    "muttai": ["egg", "muttai", "முட்டை"],
    "முட்டை": ["egg", "muttai", "முட்டை"],
    "நாட்டுக்கோழி": ["egg", "muttai", "முட்டை"],

    # Specific Dals
    "toor dal": ["toor", "துவரம்"],
    "tuvaram": ["toor", "துவரம்"],
    "துவரம்": ["toor", "துவரம்"],
    "துவரம் பருப்பு": ["toor", "துவரம்"],

    "urad dal": ["urad", "உளுந்து"],
    "ulundhu": ["urad", "உளுந்து"],
    "உளுந்து": ["urad", "உளுந்து"],
    "உளுத்தம் பருப்பு": ["urad", "உளுந்து"],
}

# Generic category terms that intentionally map to multiple catalog items
GENERIC_MULTI_TERMS = {
    "dal": ["toor", "urad", "துவரம்", "உளுந்து"],
    "paruppu": ["toor", "urad", "துவரம்", "உளுந்து"],
    "பருப்பு": ["toor", "urad", "துவரம்", "உளுந்து"],
}


def to_resolved_schema(product: Product) -> ResolvedProduct:
    """Map SQLAlchemy Product model to Pydantic ResolvedProduct schema."""
    return ResolvedProduct(
        id=product.id,
        name=product.name,
        name_ta=product.name_ta,
        sku=product.sku,
        category=product.category,
        current_stock=product.quantity,
        unit=product.unit,
        selling_price=product.selling_price,
        purchase_price=product.purchase_price,
        is_low_stock=product.is_low_stock,
        is_out_of_stock=product.is_out_of_stock,
    )


def resolve_product(
    db: Session,
    query_text: Optional[str]
) -> Tuple[ResolutionStatus, Optional[ResolvedProduct], List[ResolvedProduct]]:
    """
    Search SQLite product catalog using exact match, synonyms, and fuzzy tokens.
    Returns: (ResolutionStatus, ResolvedProduct | None, List[ResolvedProduct])
    """
    if not query_text or not query_text.strip():
        return ResolutionStatus.NO_MATCH, None, []

    cleaned = query_text.strip().lower()

    # 1. Check generic ambiguous terms (e.g. "dal" / "paruppu" which has multiple variants)
    if cleaned in GENERIC_MULTI_TERMS:
        keywords = GENERIC_MULTI_TERMS[cleaned]
        clauses = []
        for kw in keywords:
            clauses.append(Product.name.ilike(f"%{kw}%"))
            clauses.append(Product.name_ta.ilike(f"%{kw}%"))
        candidates = db.query(Product).filter(Product.is_active == True, or_(*clauses)).all()
        if len(candidates) > 1:
            return ResolutionStatus.MULTIPLE_MATCHES, None, [to_resolved_schema(p) for p in candidates]
        elif len(candidates) == 1:
            return ResolutionStatus.MATCH, to_resolved_schema(candidates[0]), []

    # 2. Check Synonym Map (Tanglish & Tamil keyword matching)
    if cleaned in SYNONYM_KEYWORDS:
        keywords = SYNONYM_KEYWORDS[cleaned]
        clauses = []
        for kw in keywords:
            clauses.append(Product.name.ilike(f"%{kw}%"))
            clauses.append(Product.name_ta.ilike(f"%{kw}%"))
            clauses.append(Product.sku.ilike(f"%{kw}%"))
        matched = db.query(Product).filter(Product.is_active == True, or_(*clauses)).all()
        if len(matched) == 1:
            return ResolutionStatus.MATCH, to_resolved_schema(matched[0]), []
        elif len(matched) > 1:
            return ResolutionStatus.MULTIPLE_MATCHES, None, [to_resolved_schema(p) for p in matched]

    # 3. Exact matching on SKU, name, or Tamil name
    exact_matches = db.query(Product).filter(
        Product.is_active == True,
        or_(
            Product.sku.ilike(cleaned),
            Product.name.ilike(cleaned),
            Product.name_ta.ilike(cleaned),
        )
    ).all()

    if len(exact_matches) == 1:
        return ResolutionStatus.MATCH, to_resolved_schema(exact_matches[0]), []
    elif len(exact_matches) > 1:
        return ResolutionStatus.MULTIPLE_MATCHES, None, [to_resolved_schema(p) for p in exact_matches]

    # 4. Partial substring matching on name and Tamil name
    term = f"%{cleaned}%"
    substring_matches = db.query(Product).filter(
        Product.is_active == True,
        or_(
            Product.name.ilike(term),
            Product.name_ta.ilike(term),
            Product.category.ilike(term),
        )
    ).all()

    if len(substring_matches) == 1:
        return ResolutionStatus.MATCH, to_resolved_schema(substring_matches[0]), []
    elif len(substring_matches) > 1:
        return ResolutionStatus.MULTIPLE_MATCHES, None, [to_resolved_schema(p) for p in substring_matches]

    # 5. Token split matching (check if any token matches synonym map)
    tokens = [t.strip() for t in cleaned.split() if len(t.strip()) > 2]
    for token in tokens:
        if token in GENERIC_MULTI_TERMS:
            keywords = GENERIC_MULTI_TERMS[token]
            clauses = [or_(Product.name.ilike(f"%{kw}%"), Product.name_ta.ilike(f"%{kw}%")) for kw in keywords]
            candidates = db.query(Product).filter(Product.is_active == True, or_(*clauses)).all()
            if len(candidates) > 1:
                return ResolutionStatus.MULTIPLE_MATCHES, None, [to_resolved_schema(p) for p in candidates]
            elif len(candidates) == 1:
                return ResolutionStatus.MATCH, to_resolved_schema(candidates[0]), []

        if token in SYNONYM_KEYWORDS:
            keywords = SYNONYM_KEYWORDS[token]
            clauses = []
            for kw in keywords:
                clauses.append(Product.name.ilike(f"%{kw}%"))
                clauses.append(Product.name_ta.ilike(f"%{kw}%"))
            matched = db.query(Product).filter(Product.is_active == True, or_(*clauses)).all()
            if len(matched) == 1:
                return ResolutionStatus.MATCH, to_resolved_schema(matched[0]), []
            elif len(matched) > 1:
                return ResolutionStatus.MULTIPLE_MATCHES, None, [to_resolved_schema(p) for p in matched]

    return ResolutionStatus.NO_MATCH, None, []
