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

    # Oil & Gold Winner
    "oil": ["gold winner", "sunflower", "எண்ணெய்"],
    "sunflower": ["sunflower", "gold winner", "எண்ணெய்"],
    "gold winner": ["gold winner", "goldwinner"],
    "gold winner oil": ["gold winner", "goldwinner"],
    "goldwinner": ["gold winner", "goldwinner"],
    "ennai": ["gold winner", "sunflower", "எண்ணெய்"],
    "enna": ["gold winner", "sunflower", "எண்ணெய்"],
    "எண்ணெய்": ["gold winner", "sunflower", "எண்ணெய்"],
    "சூரியகாந்தி": ["gold winner", "sunflower", "எண்ணெய்"],

    # Atta / Wheat Flour
    "atta": ["atta", "wheat", "godhumai", "கோதுமை", "flour"],
    "wheat": ["atta", "wheat", "godhumai", "கோதுமை", "flour"],
    "wheat flour": ["atta", "wheat", "godhumai", "கோதுமை", "flour"],
    "godhumai": ["atta", "wheat", "godhumai", "கோதுமை", "flour"],
    "godhumai maavu": ["atta", "wheat", "godhumai", "கோதுமை", "flour"],
    "gothumai": ["atta", "wheat", "godhumai", "கோதுமை", "flour"],
    "gothumai maavu": ["atta", "wheat", "godhumai", "கோதுமை", "flour"],
    "கோதுமை": ["atta", "wheat", "godhumai", "கோதுமை", "flour"],
    "கோதுமை மாவு": ["atta", "wheat", "godhumai", "கோதுமை", "flour"],
    "மாவு": ["atta", "wheat", "godhumai", "கோதுமை", "flour"],

    # Vegetables: Tomato & Onion
    "tomato": ["tomato", "thakkali", "தக்காளி"],
    "tomatoes": ["tomato", "thakkali", "தக்காளி"],
    "thakkali": ["tomato", "thakkali", "தக்காளி"],
    "தக்காளி": ["tomato", "thakkali", "தக்காளி"],

    "onion": ["onion", "vengayam", "வெங்காயம்"],
    "onions": ["onion", "vengayam", "வெங்காயம்"],
    "vengayam": ["onion", "vengayam", "வெங்காயம்"],
    "வெங்காயம்": ["onion", "vengayam", "வெங்காயம்"],

    # Tea Powder
    "tea": ["tea", "tea powder", "டீ", "டீ தூள்", "தேயிலை"],
    "tea powder": ["tea", "tea powder", "டீ", "டீ தூள்", "தேயிலை"],
    "டீ": ["tea", "tea powder", "டீ", "டீ தூள்", "தேயிலை"],
    "டீ தூள்": ["tea", "tea powder", "டீ", "டீ தூள்", "தேயிலை"],
    "தேயிலை": ["tea", "tea powder", "டீ", "டீ தூள்", "தேயிலை"],
    "தேயிலை தூள்": ["tea", "tea powder", "டீ", "டீ தூள்", "தேயிலை"],

    # Masala
    "masala": ["masala", "மசாலா", "garam masala", "masala powder"],
    "masala powder": ["masala", "மசாலா", "garam masala", "masala powder"],
    "மசாலா": ["masala", "மசாலா", "garam masala", "masala powder"],
    "மசாலா தூள்": ["masala", "மசாலா", "garam masala", "masala powder"],

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

    # Honey
    "honey": ["honey", "pure honey", "தேன்"],
    "pure honey": ["honey", "pure honey", "தேன்"],
    "thean": ["honey", "pure honey", "தேன்"],
    "then": ["honey", "pure honey", "தேன்"],
    "தேன்": ["honey", "pure honey", "தேன்"],
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
    "coffee powder": ["coffee", "bru", "காபி"],
    "காபி தூள்": ["coffee", "bru", "காபி"],

    # Garlic
    "garlic": ["garlic", "பூண்டு"],
    "poondu": ["garlic", "பூண்டு"],
    "பூண்டு": ["garlic", "பூண்டு"],

    # Salt
    "salt": ["salt", "tata salt", "உப்பு"],
    "uppu": ["salt", "tata salt", "உப்பு"],
    "உப்பு": ["salt", "tata salt", "உப்பு"],

    # Bread & Bakery
    "bread": ["bread", "milk bread", "பிரெட்"],
    "பிரெட்": ["bread", "milk bread", "பிரெட்"],

    # Biscuits
    "biscuit": ["biscuit", "biscuits", "marie", "marie gold", "பிஸ்கட்"],
    "biscuits": ["biscuit", "biscuits", "marie", "marie gold", "பிஸ்கட்"],
    "marie gold": ["biscuit", "biscuits", "marie", "marie gold", "பிஸ்கட்"],
    "பிஸ்கட்": ["biscuit", "biscuits", "marie", "marie gold", "பிஸ்கட்"],

    # Chocolates & Snacks
    "chocolate": ["chocolate", "chocolates", "dairy milk", "சாக்லேட்"],
    "chocolates": ["chocolate", "chocolates", "dairy milk", "சாக்லேட்"],
    "dairy milk": ["chocolate", "chocolates", "dairy milk", "சாக்லேட்"],
    "சாக்லேட்": ["chocolate", "chocolates", "dairy milk", "சாக்லேட்"],
    "chips": ["chips", "snacks", "சிப்ஸ்", "ஸ்நாக்ஸ்"],
    "snacks": ["chips", "snacks", "சிப்ஸ்", "ஸ்நாக்ஸ்"],
    "ஸ்நாக்ஸ்": ["chips", "snacks", "சிப்ஸ்", "ஸ்நாக்ஸ்"],

    # Personal Care: Shampoo, Serum, Toothpaste, Hair Oil
    "shampoo": ["shampoo", "clinic plus", "ஷாம்பு"],
    "ஷாம்பு": ["shampoo", "clinic plus", "ஷாம்பு"],
    "serum": ["serum", "hair serum", "சீரம்"],
    "hair serum": ["serum", "hair serum", "சீரம்"],
    "சீரம்": ["serum", "hair serum", "சீரம்"],
    "toothpaste": ["toothpaste", "colgate", "டூத்பேஸ்ட்", "பற்பசை"],
    "colgate": ["toothpaste", "colgate", "டூத்பேஸ்ட்"],
    "டூத்பேஸ்ட்": ["toothpaste", "colgate", "டூத்பேஸ்ட்"],
    "hair oil": ["hair oil", "coconut hair oil", "தலைமுடி எண்ணெய்"],
    "தலைமுடி எண்ணெய்": ["hair oil", "coconut hair oil", "தலைமுடி எண்ணெய்"],

    # Stationery: Notebook, Pen, Scale, Pencil, Eraser, Paper
    "notebook": ["notebook", "classmate", "நோட்டு", "நோட்டுப் புத்தகம்"],
    "note": ["notebook", "classmate", "நோட்டு", "நோட்டுப் புத்தகம்"],
    "நோட்டு": ["notebook", "classmate", "நோட்டு", "நோட்டுப் புத்தகம்"],
    "நோட்டுப் புத்தகம்": ["notebook", "classmate", "நோட்டு", "நோட்டுப் புத்தகம்"],
    "pen": ["pen", "reynolds", "பேனா"],
    "paena": ["pen", "reynolds", "பேனா"],
    "பேனா": ["pen", "reynolds", "பேனா"],
    "scale": ["scale", "ruler", "ஸ்கேல்", "அளவுகோல்"],
    "ஸ்கேல்": ["scale", "ruler", "ஸ்கேல்", "அளவுகோல்"],
    "அளவுகோல்": ["scale", "ruler", "ஸ்கேல்", "அளவுகோல்"],
    "pencil": ["pencil", "apsara", "பென்சில்"],
    "பென்சில்": ["pencil", "apsara", "பென்சில்"],
    "eraser": ["eraser", "rubber", "அழிப்பான்", "ரப்பர்"],
    "rubber": ["eraser", "rubber", "அழிப்பான்", "ரப்பர்"],
    "அழிப்பான்": ["eraser", "rubber", "அழிப்பான்", "ரப்பர்"],
    "paper": ["paper", "copier", "பேப்பர்"],
    "பேப்பர்": ["paper", "copier", "பேப்பர்"],

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

    # Ginger / Inji
    "ginger": ["ginger", "inji", "இஞ்சி"],
    "inji": ["ginger", "inji", "இஞ்சி"],
    "injii": ["ginger", "inji", "இஞ்சி"],
    "இஞ்சி": ["ginger", "inji", "இஞ்சி"],
    "பச்சை இஞ்சி": ["ginger", "inji", "இஞ்சி"],

    # Potato / Urulaikilangu
    "potato": ["potato", "urulaikilangu", "உருளைக்கிழங்கு"],
    "potatoes": ["potato", "urulaikilangu", "உருளைக்கிழங்கு"],
    "urulaikilangu": ["potato", "urulaikilangu", "உருளைக்கிழங்கு"],
    "urulai": ["potato", "urulaikilangu", "உருளைக்கிழங்கு"],
    "உருளைக்கிழங்கு": ["potato", "urulaikilangu", "உருளைக்கிழங்கு"],
    "உருளை": ["potato", "urulaikilangu", "உருளைக்கிழங்கு"],

    # Carrot
    "carrot": ["carrot", "கேரட்"],
    "carrots": ["carrot", "கேரட்"],
    "carrat": ["carrot", "கேரட்"],
    "கேரட்": ["carrot", "கேரட்"],

    # Green Chilli
    "green chilli": ["green chilli", "pachai milagai", "பச்சை மிளகாய்"],
    "pachai milagai": ["green chilli", "pachai milagai", "பச்சை மிளகாய்"],
    "பச்சை மிளகாய்": ["green chilli", "pachai milagai", "பச்சை மிளகாய்"],

    # Fruits: Apple & Banana
    "apple": ["apple", "ஆப்பிள்"],
    "apples": ["apple", "ஆப்பிள்"],
    "ஆப்பிள்": ["apple", "ஆப்பிள்"],
    "banana": ["banana", "vazhaipazham", "வாழைப்பழம்"],
    "bananas": ["banana", "vazhaipazham", "வாழைப்பழம்"],
    "vazhaipazham": ["banana", "vazhaipazham", "வாழைப்பழம்"],
    "வாழைப்பழம்": ["banana", "vazhaipazham", "வாழைப்பழம்"],

    # Ghee
    "ghee": ["ghee", "nei", "நெய்"],
    "nei": ["ghee", "nei", "நெய்"],
    "நெய்": ["ghee", "nei", "நெய்"],

    # Maida & Rava
    "maida": ["maida", "மைதா"],
    "maida maavu": ["maida", "மைதா"],
    "மைதா": ["maida", "மைதா"],
    "rava": ["rava", "sooji", "ரவை"],
    "sooji": ["rava", "sooji", "ரவை"],
    "ரவை": ["rava", "sooji", "ரவை"],

    # Household: Battery, Detergent, Dishwash
    "battery": ["battery", "பேட்டரி"],
    "batteries": ["battery", "பேட்டரி"],
    "aa battery": ["battery", "பேட்டரி"],
    "cell": ["battery", "பேட்டரி"],
    "பேட்டரி": ["battery", "பேட்டரி"],

    "detergent": ["detergent", "surf excel", "சோப்புத்தூள்", "டிட்டர்ஜென்ட்"],
    "surf excel": ["detergent", "surf excel", "சோப்புத்தூள்", "டிட்டர்ஜென்ட்"],
    "surf": ["detergent", "surf excel", "சோப்புத்தூள்", "டிட்டர்ஜென்ட்"],
    "washing powder": ["detergent", "surf excel", "சோப்புத்தூள்", "டிட்டர்ஜென்ட்"],
    "சோப்புத்தூள்": ["detergent", "surf excel", "சோப்புத்தூள்", "டிட்டர்ஜென்ட்"],
    "டிட்டர்ஜென்ட்": ["detergent", "surf excel", "சோப்புத்தூள்", "டிட்டர்ஜென்ட்"],

    "dishwash": ["dishwash", "vim", "டிஷ்வாஷ்"],
    "vim": ["dishwash", "vim", "டிஷ்வாஷ்"],
    "vim liquid": ["dishwash", "vim", "டிஷ்வாஷ்"],
    "டிஷ்வாஷ்": ["dishwash", "vim", "டிஷ்வாஷ்"],
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

    import re
    raw_cleaned = query_text.strip().lower()

    # Step 0: Check exact match on raw query text first (e.g. "Masala Powder", "Ponni Boiled Rice")
    raw_exact = db.query(Product).filter(
        Product.is_active == True,
        or_(
            Product.sku.ilike(raw_cleaned),
            Product.name.ilike(raw_cleaned),
            Product.name_ta.ilike(raw_cleaned),
        )
    ).all()
    if len(raw_exact) == 1:
        return ResolutionStatus.MATCH, to_resolved_schema(raw_exact[0]), []
    elif len(raw_exact) > 1:
        return ResolutionStatus.MULTIPLE_MATCHES, None, [to_resolved_schema(p) for p in raw_exact]

    # Normalize hyphens and attached Tanglish suffixes (-la, -le, -kku, -ku, -oda, -a)
    cleaned = re.sub(r"-(?:la|le|kku|ku|oda|a)\b", "", raw_cleaned, flags=re.I)
    # Only strip attached suffixes from known root patterns (rice-la -> ricela, oil-la -> oilla, stock-la -> stockla)
    cleaned = re.sub(r"\b(rice|oil|stock|dal|arisi|ennai|atta|wheat|sugar|seeni|milk|paal|tea)(?:la|le|kku|ku|oda)\b", r"\1", cleaned, flags=re.I)
    # Strip common command, direction, and unit filler words
    for w in [
        "stock", "add", "pannunga", "pannu", "sale", "sell", "kuduthuten", "kilo",
        "litres", "litre", "packet", "bottle", "vandhirukku", "increase", "decrease",
        "remove", "kammi", "korainga", "eduthukonga", "adhula", "innum"
    ]:
        cleaned = re.sub(r"\b" + re.escape(w) + r"\b", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        cleaned = raw_cleaned

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
        if cleaned in ("pen", "பேனா"):
            matched = [p for p in matched if "pencil" not in p.name.lower()]
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

    # 3B. Database Configured Aliases Matching (Dynamic custom aliases configured in catalog)
    try:
        alias_matches = db.query(Product).filter(
            Product.is_active == True,
            or_(
                Product.aliases.ilike(f"%{cleaned}%"),
                Product.aliases.ilike(f"{cleaned}%"),
                Product.aliases.ilike(f"%, {cleaned},%"),
                Product.aliases.ilike(f"%, {cleaned}%"),
            )
        ).all()
        if cleaned in ("pen", "பேனா"):
            alias_matches = [p for p in alias_matches if "pencil" not in p.name.lower()]
        if len(alias_matches) == 1:
            return ResolutionStatus.MATCH, to_resolved_schema(alias_matches[0]), []
        elif len(alias_matches) > 1:
            return ResolutionStatus.MULTIPLE_MATCHES, None, [to_resolved_schema(p) for p in alias_matches]
    except Exception:
        # Fallback if aliases column is not yet populated
        pass

    # 4. Partial substring matching on name and Tamil name
    if cleaned == "oil":
        substring_matches = db.query(Product).filter(
            Product.is_active == True,
            or_(
                Product.category.ilike("oil"),
                Product.name.ilike("% oil%"),
                Product.name.ilike("oil %"),
                Product.name.ilike("oil"),
                Product.name_ta.ilike("%எண்ணெய்%"),
            )
        ).all()
    else:
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

    # 6. Fuzzy matching fallback using difflib across active catalog
    import difflib
    all_prods = db.query(Product).filter(Product.is_active == True).all()
    candidate_tokens_map = {}
    for p in all_prods:
        candidate_tokens_map[p.name.lower()] = p
        if p.name_ta:
            candidate_tokens_map[p.name_ta.lower()] = p
        if getattr(p, "aliases", None):
            for al in p.aliases.split(","):
                al_clean = al.strip().lower()
                if al_clean and len(al_clean) > 2:
                    candidate_tokens_map[al_clean] = p

    close_keys = difflib.get_close_matches(cleaned, candidate_tokens_map.keys(), n=3, cutoff=0.78)
    if close_keys:
        matched_dict = {candidate_tokens_map[k].id: candidate_tokens_map[k] for k in close_keys}
        matched_prods = list(matched_dict.values())
        if cleaned in ("pen", "பேனா"):
            matched_prods = [p for p in matched_prods if "pencil" not in p.name.lower()]
        if len(matched_prods) == 1:
            return ResolutionStatus.MATCH, to_resolved_schema(matched_prods[0]), []
        elif len(matched_prods) > 1:
            return ResolutionStatus.MULTIPLE_MATCHES, None, [to_resolved_schema(p) for p in matched_prods]

    return ResolutionStatus.NO_MATCH, None, []
