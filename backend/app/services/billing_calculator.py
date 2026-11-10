"""Authoritative Billing Calculation Service for TamilVoice Kirana AI.
Uses Python Decimal for monetary arithmetic to eliminate floating-point inaccuracies.
Formula:
    line_total = quantity × unit_price
    subtotal = sum(all line totals)
    grand_total = subtotal + configured_taxes - configured_discounts
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import List, Dict, Any, Optional, Union, Tuple
from pydantic import BaseModel, Field, ConfigDict
from backend.app.services.unit_converter import convert_quantity_to_base, canonical_unit


def to_decimal(val: Union[Decimal, float, int, str, None], default: str = "0.00") -> Decimal:
    """Safely convert any numeric or string representation into a quantized 2-decimal Decimal."""
    if val is None:
        return Decimal(default)
    try:
        # Strip currency symbols and whitespace if present
        clean_str = str(val).replace("₹", "").replace(",", "").strip()
        if not clean_str:
            return Decimal(default)
        return Decimal(clean_str)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


def quantize_currency(amount: Union[Decimal, float, int, str]) -> Decimal:
    """Quantize to 2 decimal places using standard ROUND_HALF_UP."""
    dec = to_decimal(amount)
    return dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_line_item(
    quantity: Union[Decimal, float, int, str],
    unit_price: Union[Decimal, float, int, str],
    unit: str = "unit",
    base_unit: Optional[str] = None,
    product_name: str = "product"
) -> Decimal:
    """
    Calculate line total for a single product line item:
        line_total = converted_quantity × unit_price
    Guarantees:
        2 kg @ ₹40/kg = ₹80.00
        1 kg @ ₹40/kg = ₹40.00
        200 g @ ₹100/kg = ₹20.00
        500 ml @ ₹140/litre = ₹70.00
    """
    qty_dec = to_decimal(quantity)
    price_dec = to_decimal(unit_price)

    if qty_dec <= Decimal("0"):
        raise ValueError(f"Quantity must be strictly positive (got {quantity} {unit}).")
    if price_dec < Decimal("0"):
        raise ValueError(f"Unit price cannot be negative (got ₹{unit_price}).")

    if base_unit and canonical_unit(unit) != canonical_unit(base_unit):
        converted_qty, _ = convert_quantity_to_base(qty_dec, from_unit=unit, to_unit=base_unit, product_name=product_name)
    else:
        converted_qty = qty_dec

    raw_total = converted_qty * price_dec
    return raw_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_line_item_with_conversion(
    quantity: Union[Decimal, float, int, str],
    unit_price: Union[Decimal, float, int, str],
    requested_unit: str = "unit",
    base_unit: Optional[str] = None,
    product_name: str = "product"
) -> Tuple[Decimal, Decimal]:
    """
    Calculate line total and converted quantity in product base units.
    Returns: (line_total_dec, converted_quantity_dec)
    """
    qty_dec = to_decimal(quantity)
    price_dec = to_decimal(unit_price)

    if qty_dec <= Decimal("0"):
        raise ValueError(f"Quantity must be strictly positive (got {quantity} {requested_unit}).")
    if price_dec < Decimal("0"):
        raise ValueError(f"Unit price cannot be negative (got ₹{unit_price}).")

    if base_unit and canonical_unit(requested_unit) != canonical_unit(base_unit):
        converted_qty, _ = convert_quantity_to_base(qty_dec, from_unit=requested_unit, to_unit=base_unit, product_name=product_name)
    else:
        converted_qty = qty_dec

    raw_total = converted_qty * price_dec
    return raw_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), converted_qty


class CalculatedLineItem(BaseModel):
    product_id: int
    product_name: str
    quantity: float
    unit: str
    unit_price: float
    line_total: float


class BillCalculationResult(BaseModel):
    items: List[CalculatedLineItem]
    total_quantity: float
    subtotal: float
    tax_rate: float
    tax_amount: float
    discount_amount: float
    grand_total: float

    # Exact decimal representations for audit
    subtotal_dec: Decimal
    grand_total_dec: Decimal

    model_config = ConfigDict(arbitrary_types_allowed=True)


def calculate_bill(
    items: List[Dict[str, Any]],
    tax_rate: Union[Decimal, float, int, str] = 0.0,
    discount_amount: Union[Decimal, float, int, str] = 0.0
) -> BillCalculationResult:
    """
    Authoritative backend billing calculation across all line items:
    1. Validates each product line (quantity > 0, price >= 0)
    2. Computes line_total = quantity * unit_price
    3. Computes subtotal = sum(line_totals)
    4. Computes tax_amount = (subtotal * tax_rate)
    5. Computes grand_total = subtotal + tax_amount - discount_amount
    6. Ensures strict consistency and rounding to 2 decimal places
    """
    if not items:
        raise ValueError("Cannot calculate bill for an empty items list.")

    tax_rate_dec = to_decimal(tax_rate)
    discount_dec = quantize_currency(discount_amount)

    if tax_rate_dec < Decimal("0"):
        raise ValueError("Tax rate cannot be negative.")
    if discount_dec < Decimal("0"):
        raise ValueError("Discount amount cannot be negative.")

    subtotal_dec = Decimal("0.00")
    total_qty_dec = Decimal("0.000")
    calculated_items: List[CalculatedLineItem] = []

    for idx, it in enumerate(items):
        prod_id = int(it.get("product_id") or (idx + 1))
        prod_name = str(it.get("product_name") or it.get("name") or f"Item #{prod_id}").strip()
        qty = it.get("quantity")
        price = it.get("unit_price")
        unit = str(it.get("unit") or "unit").strip()
        base_unit = str(it.get("base_unit") or unit).strip()

        if price is None:
            raise ValueError(f"Product '{prod_name}' has no configured selling price in database.")

        line_tot_dec, converted_qty_dec = calculate_line_item_with_conversion(
            quantity=qty,
            unit_price=price,
            requested_unit=unit,
            base_unit=base_unit,
            product_name=prod_name
        )
        subtotal_dec += line_tot_dec
        total_qty_dec += to_decimal(qty)

        calculated_items.append(
            CalculatedLineItem(
                product_id=prod_id,
                product_name=prod_name,
                quantity=float(to_decimal(qty)),
                unit=unit,
                unit_price=float(quantize_currency(price)),
                line_total=float(line_tot_dec)
            )
        )

    subtotal_dec = subtotal_dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    tax_amount_dec = (subtotal_dec * tax_rate_dec).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    # Grand total cannot be negative
    raw_grand_total = subtotal_dec + tax_amount_dec - discount_dec
    grand_total_dec = max(Decimal("0.00"), raw_grand_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    return BillCalculationResult(
        items=calculated_items,
        total_quantity=float(total_qty_dec),
        subtotal=float(subtotal_dec),
        tax_rate=float(tax_rate_dec),
        tax_amount=float(tax_amount_dec),
        discount_amount=float(discount_dec),
        grand_total=float(grand_total_dec),
        subtotal_dec=subtotal_dec,
        grand_total_dec=grand_total_dec
    )


def validate_bill_consistency(
    items: List[Dict[str, Any]],
    expected_grand_total: Union[Decimal, float, int, str],
    tax_rate: Union[Decimal, float, int, str] = 0.0,
    discount_amount: Union[Decimal, float, int, str] = 0.0,
    tolerance: Decimal = Decimal("0.02")
) -> bool:
    """
    Validate that an external or stored total matches authoritative backend calculation.
    Rejects any inconsistent bill before saving.
    """
    result = calculate_bill(items=items, tax_rate=tax_rate, discount_amount=discount_amount)
    exp_dec = quantize_currency(expected_grand_total)
    diff = abs(result.grand_total_dec - exp_dec)
    return diff <= tolerance
