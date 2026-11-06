"""AI and Natural Language Intent Processing Schemas."""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class IntentCategory(str, Enum):
    ADD_STOCK = "ADD_STOCK"
    SELL_PRODUCT = "SELL_PRODUCT"
    CHECK_STOCK = "CHECK_STOCK"
    LOW_STOCK_QUERY = "LOW_STOCK_QUERY"
    SALES_REPORT = "SALES_REPORT"
    PRODUCT_SALES_REPORT = "PRODUCT_SALES_REPORT"
    INVENTORY_REPORT = "INVENTORY_REPORT"
    CREATE_PRODUCT = "CREATE_PRODUCT"
    UNKNOWN = "UNKNOWN"


def normalize_unit_str(unit_str: Optional[str]) -> Optional[str]:
    """Normalize colloquial and plural unit strings into standard Kirana units."""
    if not unit_str:
        return None
    u = unit_str.lower().strip()
    # Map common variants
    if u in ("kg", "kgs", "kilo", "kilos", "kilogram", "kilograms", "கிலோ"):
        return "kg"
    if u in ("l", "ltr", "litre", "litres", "liter", "liters", "லிட்டர்"):
        return "litre"
    if u in ("packet", "packets", "pkt", "pkts", "பாக்கெட்"):
        return "packet"
    if u in ("pcs", "pc", "piece", "pieces", "count", "முட்டை", "எண்ணிக்கை"):
        return "pcs"
    if u in ("g", "gm", "gms", "gram", "grams", "கிராம்"):
        return "g"
    if u in ("ml", "millilitre", "மில்லி"):
        return "ml"
    if u in ("bag", "bags", "mootai", "மூட்டை"):
        return "bag"
    if u in ("box", "boxes", "பெட்டி"):
        return "box"
    return u


class CommandEntities(BaseModel):
    product_name: Optional[str] = Field(None, description="Extracted product name or synonym")
    quantity: Optional[float] = Field(None, description="Positive numeric quantity")
    unit: Optional[str] = Field(None, description="Standardized measurement unit")
    date: Optional[str] = Field(None, description="Time reference like today, yesterday, this_week")
    customer_name: Optional[str] = Field(None, description="Optional customer name if mentioned")
    payment_method: Optional[str] = Field(None, description="CASH, UPI, CREDIT, CARD")

    @field_validator("quantity")
    @classmethod
    def validate_positive_quantity(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Quantity must be greater than zero.")
        return round(v, 3) if v is not None else None

    @field_validator("unit")
    @classmethod
    def validate_and_normalize_unit(cls, v):
        return normalize_unit_str(v)


class CommandIntent(BaseModel):
    intent: IntentCategory = Field(..., description="Classified intent category")
    language: str = Field("Tanglish", description="Tamil, Tanglish, English, or Mixed")
    original_text: str = Field(..., description="Raw user input string")
    normalized_text: str = Field(..., description="Cleaned English representation of the request")
    entities: CommandEntities = Field(default_factory=CommandEntities)
    confidence: float = Field(0.9, ge=0.0, le=1.0, description="Model confidence score 0.0 to 1.0")
    requires_clarification: bool = Field(False, description="Flag indicating missing critical parameters")
    clarification_question: Optional[str] = Field(None, description="Question to prompt merchant for details")

    @model_validator(mode="after")
    def validate_business_constraints(self):
        # 1. Unknown intent always requires clarification
        if self.intent == IntentCategory.UNKNOWN:
            self.requires_clarification = True
            if not self.clarification_question:
                self.clarification_question = (
                    "I could not understand that command. Please specify if you want to "
                    "add stock, record a sale, or check inventory."
                )

        # 2. ADD_STOCK & SELL_PRODUCT require product_name and quantity
        if self.intent in (IntentCategory.ADD_STOCK, IntentCategory.SELL_PRODUCT):
            if not self.entities.product_name or not self.entities.product_name.strip():
                self.requires_clarification = True
                if not self.clarification_question:
                    self.clarification_question = "Which product would you like to update?"

            elif self.entities.quantity is None or self.entities.quantity <= 0:
                self.requires_clarification = True
                if not self.clarification_question:
                    action_word = "add" if self.intent == IntentCategory.ADD_STOCK else "sell"
                    self.clarification_question = f"How much {self.entities.product_name} would you like to {action_word}?"

        # 3. If requires_clarification is True, ensure a question exists
        if self.requires_clarification and not self.clarification_question:
            self.clarification_question = "Could you please provide more details for this request?"

        return self


class ResolvedProduct(BaseModel):
    id: int
    name: str
    name_ta: Optional[str] = None
    sku: str
    category: str
    current_stock: float
    unit: str
    selling_price: float
    purchase_price: float
    is_low_stock: bool
    is_out_of_stock: bool

    model_config = ConfigDict(from_attributes=True)


class ConfirmationPreview(BaseModel):
    action_id: str = Field(..., description="Temporary unique token for safe confirmation")
    action: str = Field(..., description="ADD_STOCK or SELL_PRODUCT")
    product_id: int
    product_name: str
    product_name_ta: Optional[str] = None
    quantity: float
    unit: str
    current_stock: float
    projected_stock: float
    unit_price: Optional[float] = None
    estimated_total: Optional[float] = None
    payment_method: str = "CASH"
    expires_at: datetime


class InterpretRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500, description="Spoken or typed command")


class InterpretResponse(BaseModel):
    success: bool
    intent: CommandIntent
    resolved_product: Optional[ResolvedProduct] = None
    candidate_products: List[ResolvedProduct] = Field(default_factory=list)
    requires_confirmation: bool = False
    confirmation_preview: Optional[ConfirmationPreview] = None
    query_result: Optional[Dict[str, Any]] = None
    message: str
    message_ta: Optional[str] = None


class ConfirmActionRequest(BaseModel):
    action_id: str = Field(..., description="Unique action token generated during interpret")


class ConfirmActionResponse(BaseModel):
    success: bool
    action: str
    transaction_id: Optional[str] = None
    product_name: str
    previous_stock: float
    new_stock: float
    total_amount: Optional[float] = None
    message: str
    message_ta: Optional[str] = None


class CancelActionRequest(BaseModel):
    action_id: str = Field(..., description="Unique action token to cancel")


class CancelActionResponse(BaseModel):
    success: bool
    message: str


class AIStatusResponse(BaseModel):
    configured: bool
    enabled: bool
    model: str
    provider: str = "Google Gemini"
    ready: bool

