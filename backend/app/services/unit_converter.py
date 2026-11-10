"""Unit Converter & Validator Service for TamilVoice Kirana AI.
Handles safe metric conversions (kg <-> g <-> mg, litre <-> ml, dozen <-> piece)
and protects against incompatible retail conversions.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple

WEIGHT_UNITS = {"kg", "kilo", "kilos", "kilogram", "kilograms", "கிலோ", "g", "gm", "gms", "gram", "grams", "கிராம்", "mg", "milligram"}
VOLUME_UNITS = {"l", "ltr", "litre", "litres", "liter", "liters", "லிட்டர்", "ml", "millilitre", "மில்லி"}
RETAIL_PIECE = {"piece", "pieces", "pc", "pcs", "count", "எண்ணிக்கை", "முட்டை"}
RETAIL_PACKET = {"packet", "packets", "pkt", "pkts", "பாக்கெட்"}
RETAIL_BOTTLE = {"bottle", "bottles", "பாட்டில்"}
RETAIL_BOX = {"box", "boxes", "பெட்டி"}
RETAIL_BAG = {"bag", "bags", "mootai", "மூட்டை"}
RETAIL_DOZEN = {"dozen", "dozens", "டஜன்"}
NEUTRAL_UNITS = {"", "unit", "units", "item", "items", "none", "count"}


def canonical_unit(unit_str: Optional[str]) -> str:
    """Normalize any colloquial or language variant into standard canonical unit token."""
    if not unit_str:
        return "unit"
    u = unit_str.lower().strip()
    if u in WEIGHT_UNITS:
        if u in ("kg", "kilo", "kilos", "kilogram", "kilograms", "கிலோ"):
            return "kg"
        if u in ("g", "gm", "gms", "gram", "grams", "கிராம்"):
            return "g"
        if u in ("mg", "milligram"):
            return "mg"
    if u in VOLUME_UNITS:
        if u in ("l", "ltr", "litre", "litres", "liter", "liters", "லிட்டர்"):
            return "litre"
        if u in ("ml", "millilitre", "மில்லி"):
            return "ml"
    if u in RETAIL_PIECE:
        return "piece"
    if u in RETAIL_PACKET:
        return "packet"
    if u in RETAIL_BOTTLE:
        return "bottle"
    if u in RETAIL_BOX:
        return "box"
    if u in RETAIL_BAG:
        return "bag"
    if u in RETAIL_DOZEN:
        return "dozen"
    if u in NEUTRAL_UNITS:
        return "unit"
    return u


def are_units_compatible(from_unit: Optional[str], to_unit: Optional[str]) -> bool:
    """Check if two units can be legally converted without item-specific weight metadata."""
    c_from = canonical_unit(from_unit)
    c_to = canonical_unit(to_unit)

    if c_from == c_to or c_from == "unit" or c_to == "unit":
        return True

    # Weight compatibility
    if c_from in ("kg", "g", "mg") and c_to in ("kg", "g", "mg"):
        return True

    # Volume compatibility
    if c_from in ("litre", "ml") and c_to in ("litre", "ml"):
        return True

    # Dozen <-> Piece compatibility
    if (c_from == "dozen" and c_to == "piece") or (c_from == "piece" and c_to == "dozen"):
        return True

    # Retail package <-> Bulk unit compatibility (e.g. 1 packet of sugar / 1 packet of milk)
    RETAIL_COUNT_UNITS = {"piece", "packet", "bottle", "box", "bag", "unit"}
    if (c_from in RETAIL_COUNT_UNITS and c_to in ("kg", "litre", "g", "ml")) or (c_from in ("kg", "litre", "g", "ml") and c_to in RETAIL_COUNT_UNITS):
        return True

    # Between retail count units (packet <-> piece, etc.)
    if c_from in RETAIL_COUNT_UNITS and c_to in RETAIL_COUNT_UNITS:
        return True

    return False


def convert_quantity_to_base(
    quantity: Decimal,
    from_unit: Optional[str],
    to_unit: Optional[str],
    product_name: str = "product"
) -> Tuple[Decimal, Decimal]:
    """
    Safely converts a quantity from a requested unit into the product's database base unit.
    Returns: (converted_quantity, conversion_factor)
    Raises ValueError if conversion is physically or commercially incompatible.
    """
    c_from = canonical_unit(from_unit)
    c_to = canonical_unit(to_unit)

    # Identical or neutral unit
    if c_from == c_to or c_from == "unit" or c_to == "unit":
        return quantity, Decimal("1.0")

    # Weight conversions
    if c_from == "g" and c_to == "kg":
        factor = Decimal("0.001")
        return quantity * factor, factor
    if c_from == "kg" and c_to == "g":
        factor = Decimal("1000")
        return quantity * factor, factor
    if c_from == "mg" and c_to == "kg":
        factor = Decimal("0.000001")
        return quantity * factor, factor
    if c_from == "mg" and c_to == "g":
        factor = Decimal("0.001")
        return quantity * factor, factor

    # Volume conversions
    if c_from == "ml" and c_to == "litre":
        factor = Decimal("0.001")
        return quantity * factor, factor
    if c_from == "litre" and c_to == "ml":
        factor = Decimal("1000")
        return quantity * factor, factor

    # Dozen <-> Piece conversions
    if c_from == "dozen" and c_to == "piece":
        factor = Decimal("12")
        return quantity * factor, factor
    if c_from == "piece" and c_to == "dozen":
        factor = Decimal("1") / Decimal("12")
        return (quantity / Decimal("12")).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP), factor

    # Retail package <-> Bulk unit fallback for Kirana natural speech
    # (e.g. '2 packet sugar' where sugar base is kg -> 2 kg, '5 kg tea powder' where tea powder base is packet -> 5 packets)
    RETAIL_COUNT_UNITS = {"piece", "packet", "bottle", "box", "bag", "unit"}
    if (c_from in RETAIL_COUNT_UNITS and c_to in ("kg", "litre")) or (c_from in ("kg", "litre") and c_to in RETAIL_COUNT_UNITS):
        factor = Decimal("1.0")
        return quantity * factor, factor
    if c_from in RETAIL_COUNT_UNITS and c_to in RETAIL_COUNT_UNITS:
        factor = Decimal("1.0")
        return quantity * factor, factor
    if c_from in ("g", "ml") and c_to in RETAIL_COUNT_UNITS:
        factor = Decimal("0.001")
        return quantity * factor, factor
    if c_from in RETAIL_COUNT_UNITS and c_to in ("g", "ml"):
        factor = Decimal("1000")
        return quantity * factor, factor

    raise ValueError(
        f"Unit mismatch: Cannot convert '{from_unit}' to product base unit '{to_unit}' for '{product_name}'. "
        f"Please specify quantity in '{to_unit}'."
    )
