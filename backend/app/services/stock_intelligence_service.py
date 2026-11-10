"""Stock Intelligence & Predictive Reorder Service for TamilVoice Kirana AI.
Uses actual database stock, minimum thresholds, and recent sales velocity.
Calculates days remaining: days_remaining = current_stock / avg_daily_sales.
Clearly explains estimates and handles insufficient sales history gracefully.
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.models.product import Product
from backend.app.models.sale import Sale
from backend.app.models.sale_item import SaleItem


class ProductStockRisk:
    def __init__(
        self,
        product_id: int,
        name: str,
        name_ta: Optional[str],
        current_stock: float,
        unit: str,
        minimum_stock_level: float,
        reorder_level: float,
        avg_daily_sales: float,
        days_remaining: Optional[float],
        risk_level: str,  # "OUT_OF_STOCK", "CRITICAL_RISK", "MODERATE_RISK", "SAFE"
        suggested_reorder: float,
        has_sufficient_history: bool,
    ):
        self.product_id = product_id
        self.name = name
        self.name_ta = name_ta
        self.current_stock = current_stock
        self.unit = unit
        self.minimum_stock_level = minimum_stock_level
        self.reorder_level = reorder_level
        self.avg_daily_sales = avg_daily_sales
        self.days_remaining = days_remaining
        self.risk_level = risk_level
        self.suggested_reorder = suggested_reorder
        self.has_sufficient_history = has_sufficient_history

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "name": self.name,
            "name_ta": self.name_ta,
            "current_stock": self.current_stock,
            "unit": self.unit,
            "minimum_stock_level": self.minimum_stock_level,
            "reorder_level": self.reorder_level,
            "avg_daily_sales": round(self.avg_daily_sales, 2),
            "days_remaining": self.days_remaining,
            "risk_level": self.risk_level,
            "suggested_reorder": round(self.suggested_reorder, 2),
            "has_sufficient_history": self.has_sufficient_history,
        }


def analyze_stock_intelligence(
    db: Session,
    days_window: int = 7
) -> Dict[str, Any]:
    """
    Perform rigorous stock risk and reorder analysis using real database records.
    Returns:
        dict with:
            - out_of_stock_items: List[ProductStockRisk]
            - critical_risk_items: List[ProductStockRisk] (at risk within 1.5 days or <= min stock)
            - moderate_risk_items: List[ProductStockRisk] (1.5 < days <= 3.5)
            - suggested_reorders: List[ProductStockRisk]
            - summary_en: English natural explanation
            - summary_ta: Tamil natural explanation
            - summary_tanglish: Tanglish natural explanation
    """
    active_products = db.query(Product).filter(Product.is_active == True).all()

    now = datetime.now(timezone.utc)
    since_date = now - timedelta(days=days_window)

    # Calculate actual sales velocity in past N days
    sales_data = (
        db.query(
            SaleItem.product_id,
            func.sum(SaleItem.quantity).label("total_sold"),
            func.count(SaleItem.id).label("sale_count"),
        )
        .join(Sale, SaleItem.sale_id == Sale.id)
        .filter(Sale.created_at >= since_date)
        .group_by(SaleItem.product_id)
        .all()
    )

    sales_map = {row.product_id: (float(row.total_sold or 0.0), int(row.sale_count or 0)) for row in sales_data}

    # Also check if any older sales exist for store to evaluate general history
    total_sales_count = db.query(func.count(Sale.id)).scalar() or 0
    store_has_history = total_sales_count >= 5

    out_of_stock: List[ProductStockRisk] = []
    critical_risk: List[ProductStockRisk] = []
    moderate_risk: List[ProductStockRisk] = []
    safe_items: List[ProductStockRisk] = []

    for p in active_products:
        sold_qty, sale_events = sales_map.get(p.id, (0.0, 0))
        avg_daily = sold_qty / float(days_window) if days_window > 0 else 0.0
        min_thresh = float(p.minimum_stock_level or 10.0)
        reorder_target = float(getattr(p, "reorder_level", None) or (min_thresh * 1.5))

        has_history = store_has_history and (sale_events >= 2 or sold_qty > 0)

        if avg_daily > 0:
            days_rem = round(p.quantity / avg_daily, 1)
        else:
            days_rem = None

        curr_stock = float(p.quantity)

        # Categorize
        if curr_stock <= 0:
            risk = "OUT_OF_STOCK"
            reorder_qty = max(reorder_target, min_thresh * 2)
            out_of_stock.append(ProductStockRisk(
                product_id=p.id,
                name=p.name,
                name_ta=p.name_ta,
                current_stock=curr_stock,
                unit=p.unit,
                minimum_stock_level=min_thresh,
                reorder_level=reorder_target,
                avg_daily_sales=avg_daily,
                days_remaining=0.0,
                risk_level=risk,
                suggested_reorder=reorder_qty,
                has_sufficient_history=has_history
            ))
        elif (days_rem is not None and days_rem <= 1.5) or curr_stock <= min_thresh:
            risk = "CRITICAL_RISK"
            reorder_qty = max(0.0, (reorder_target * 2) - curr_stock)
            critical_risk.append(ProductStockRisk(
                product_id=p.id,
                name=p.name,
                name_ta=p.name_ta,
                current_stock=curr_stock,
                unit=p.unit,
                minimum_stock_level=min_thresh,
                reorder_level=reorder_target,
                avg_daily_sales=avg_daily,
                days_remaining=days_rem,
                risk_level=risk,
                suggested_reorder=reorder_qty,
                has_sufficient_history=has_history
            ))
        elif days_rem is not None and days_rem <= 3.5:
            risk = "MODERATE_RISK"
            reorder_qty = max(0.0, reorder_target - curr_stock)
            moderate_risk.append(ProductStockRisk(
                product_id=p.id,
                name=p.name,
                name_ta=p.name_ta,
                current_stock=curr_stock,
                unit=p.unit,
                minimum_stock_level=min_thresh,
                reorder_level=reorder_target,
                avg_daily_sales=avg_daily,
                days_remaining=days_rem,
                risk_level=risk,
                suggested_reorder=reorder_qty,
                has_sufficient_history=has_history
            ))
        else:
            safe_items.append(ProductStockRisk(
                product_id=p.id,
                name=p.name,
                name_ta=p.name_ta,
                current_stock=curr_stock,
                unit=p.unit,
                minimum_stock_level=min_thresh,
                reorder_level=reorder_target,
                avg_daily_sales=avg_daily,
                days_remaining=days_rem,
                risk_level="SAFE",
                suggested_reorder=0.0,
                has_sufficient_history=has_history
            ))

    # Build natural multilingual responses
    if out_of_stock or critical_risk:
        # Construct predictive risk narrative
        parts_en = []
        parts_ta = []
        parts_tanglish = []

        if out_of_stock:
            names_en = ", ".join(f"{it.name} (0 {it.unit})" for it in out_of_stock[:3])
            names_ta = ", ".join(f"{it.name_ta or it.name} (0 {it.unit})" for it in out_of_stock[:3])
            parts_en.append(f"Currently out of stock: {names_en}")
            parts_ta.append(f"இருப்பு முற்றிலும் இல்லாத பொருட்கள்: {names_ta}")
            parts_tanglish.append(f"Ippo out of stock: {names_en}")

        if critical_risk:
            detail_en = []
            detail_ta = []
            detail_tang = []
            for it in critical_risk[:4]:
                q_disp = int(it.current_stock) if it.current_stock.is_integer() else it.current_stock
                if it.days_remaining is not None:
                    detail_en.append(f"{it.name} ({q_disp} {it.unit} left, ~{it.days_remaining} days remaining)")
                    detail_ta.append(f"{it.name_ta or it.name} (மீதம் {q_disp} {it.unit}, ~{it.days_remaining} நாள்)")
                    detail_tang.append(f"{it.name} (stock {q_disp} {it.unit}, ~{it.days_remaining} days)")
                else:
                    detail_en.append(f"{it.name} ({q_disp} {it.unit} left, below minimum threshold {it.minimum_stock_level})")
                    detail_ta.append(f"{it.name_ta or it.name} (மீதம் {q_disp} {it.unit}, குறைந்தபட்ச இருப்புக்கு கீழ்)")
                    detail_tang.append(f"{it.name} (stock {q_disp} {it.unit}, min stock-ku keela)")

            parts_en.append(f"Products at high risk of running out tomorrow: {', '.join(detail_en)}.")
            parts_ta.append(f"நாளை தீர்ந்துபோகும் அபாயத்தில் உள்ள பொருட்கள்: {', '.join(detail_ta)}.")
            parts_tanglish.append(f"Naalaikku stock out aagum risk ulla items: {', '.join(detail_tang)}.")

        parts_en.append("This is an estimate based on recent daily sales velocity and minimum stock thresholds.")
        parts_ta.append("இது சமீபத்திய தினசரி விற்பனை வேகம் மற்றும் குறைந்தபட்ச இருப்பு அளவின் அடிப்படையில் கணக்கிடப்பட்ட மதிப்பீடு மட்டுமே.")
        parts_tanglish.append("Idhu recent sales velocity and minimum stock based panna estimate mattum dhaan.")

        summary_en = " ".join(parts_en)
        summary_ta = " ".join(parts_ta)
        summary_tanglish = " ".join(parts_tanglish)
    else:
        summary_en = "All products have adequate stock levels. No products are at immediate risk of running out tomorrow."
        summary_ta = "எல்லா பொருட்களும் போதுமான அளவில் உள்ளன. நாளை தீர்ந்துபோகும் அபாயத்தில் எந்த பொருளும் இல்லை."
        summary_tanglish = "Ella items-um safe-ah irukku. Naalaikku endha product-um stock out aaga chance illa."

    return {
        "out_of_stock_items": [it.to_dict() for it in out_of_stock],
        "critical_risk_items": [it.to_dict() for it in critical_risk],
        "moderate_risk_items": [it.to_dict() for it in moderate_risk],
        "suggested_reorders": [it.to_dict() for it in (out_of_stock + critical_risk + moderate_risk)],
        "summary_en": summary_en,
        "summary_ta": summary_ta,
        "summary_tanglish": summary_tanglish,
    }
