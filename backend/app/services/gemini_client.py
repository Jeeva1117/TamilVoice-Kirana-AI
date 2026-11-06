"""Gemini API Integration: Speech-to-Intent Extraction using Google GenAI SDK."""
import json
import logging
import asyncio
from typing import Optional
from backend.app.config import settings
from backend.app.schemas.ai import CommandIntent, IntentCategory, CommandEntities

logger = logging.getLogger(__name__)

GEMINI_SYSTEM_INSTRUCTION = """You are an expert Tamil, Tanglish, and Indian English Voice Intelligence Engine for Kirana (grocery) shopkeepers.
Your job is to analyze the merchant's spoken command and extract a strictly structured JSON intent.

SUPPORTED LANGUAGES:
1. Tamil (தமிழ் script, e.g., "5 கிலோ அரிசி இருப்பு சேர்க்க", "2 லிட்டர் எண்ணெய் விற்றுட்டேன்", "இன்றைய விற்பனை எவ்வளவு?")
2. Tanglish (Tamil in English script, e.g., "Innaiku 5 kilo rice stock add pannunga", "3 kilo rice sale panniten", "Sugar stock evlo irukku?", "Innaiku sales evlo?")
3. English (e.g., "Add 10 packets of biscuits", "Sell 2 bottles of sunflower oil")
4. Mixed colloquial Kirana speech (e.g., "Customer-ku 2 oil bottle kuduthuten", "Sugar 20 kilo vandhirukku", "Rice 5 bag sel aachu")

SUPPORTED INTENTS:
- ADD_STOCK: Merchant received delivery or is adding inventory.
- SELL_PRODUCT: Merchant sold items to a customer.
- CHECK_STOCK: Merchant asks about current stock level of a product.
- LOW_STOCK_QUERY: Merchant asks which products are running low or out of stock.
- SALES_REPORT: Merchant asks for sales revenue / bill count (today, yesterday, this week).
- PRODUCT_SALES_REPORT: Merchant asks for sales of a specific product or top selling product.
- INVENTORY_REPORT: Merchant asks for total inventory valuation or catalog overview.
- CREATE_PRODUCT: Merchant wants to register a new product item.
- UNKNOWN: Unintelligible speech, greetings without request, or unrelated commands.

CRITICAL RULES:
1. NEVER invent or fabricate missing numbers or quantities. If the shopkeeper says "Rice add pannunga", set quantity: null and requires_clarification: true with clarification_question: "How much rice stock should I add?".
2. NEVER invent product names. If the shopkeeper says "Stock add pannu", set product_name: null and requires_clarification: true with clarification_question: "Which product would you like to update?".
3. Normalize units to standard codes: "kg", "litre", "packet", "pcs", "g", "ml", "bag", "box".
4. Determine language as "Tamil", "Tanglish", "English", or "Mixed".
5. Provide confidence as a float between 0.0 and 1.0.
6. Return raw JSON matching this schema:
{
  "intent": "ADD_STOCK" | "SELL_PRODUCT" | "CHECK_STOCK" | "LOW_STOCK_QUERY" | "SALES_REPORT" | "PRODUCT_SALES_REPORT" | "INVENTORY_REPORT" | "CREATE_PRODUCT" | "UNKNOWN",
  "language": "Tamil" | "Tanglish" | "English" | "Mixed",
  "original_text": "<verbatim input>",
  "normalized_text": "<concise English description of action>",
  "entities": {
    "product_name": "<string or null>",
    "quantity": <float or null>,
    "unit": "<string or null>",
    "date": "<string or null>",
    "customer_name": "<string or null>",
    "payment_method": "<string or null>"
  },
  "confidence": <float>,
  "requires_clarification": <boolean>,
  "clarification_question": "<string or null>"
}
"""


class GeminiError(Exception):
    """Base Gemini API error."""
    pass


class GeminiNotConfiguredError(GeminiError):
    """Raised when Gemini API key is missing or service is disabled."""
    pass


class GeminiClient:
    """Singleton-style wrapper for Google GenAI SDK."""

    def __init__(self):
        self._client = None
        self._client_type = None

    def _get_client(self):
        if not settings.is_gemini_ready:
            raise GeminiNotConfiguredError(
                "Gemini API is not configured. Please set GEMINI_API_KEY in your .env file "
                "or enable it by setting GEMINI_ENABLED=true."
            )

        if self._client is None:
            try:
                # Try official google.genai unified SDK
                from google import genai
                self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
                self._client_type = "genai"
                logger.info("Initialized Google GenAI unified client.")
            except ImportError:
                # Fallback to google.generativeai
                try:
                    import google.generativeai as legacy_genai
                    legacy_genai.configure(api_key=settings.GEMINI_API_KEY)
                    self._client = legacy_genai.GenerativeModel(
                        model_name=settings.GEMINI_MODEL,
                        system_instruction=GEMINI_SYSTEM_INSTRUCTION
                    )
                    self._client_type = "legacy"
                    logger.info("Initialized google.generativeai legacy client.")
                except ImportError as e:
                    raise GeminiError(f"No Google GenAI SDK installed: {e}")

        return self._client

    async def generate_intent_async(self, text: str) -> CommandIntent:
        """Call Gemini asynchronously with prompt and parse structured CommandIntent."""
        client = self._get_client()

        prompt = f"Kirana Shopkeeper Command:\n\"{text.strip()}\"\n\nJSON Output:"

        try:
            if self._client_type == "genai":
                from google.genai import types

                config = types.GenerateContentConfig(
                    system_instruction=GEMINI_SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    temperature=0.1,
                )

                # Use asyncio timeout with client.aio or client
                async def _call_api():
                    if hasattr(client, "aio") and hasattr(client.aio, "models"):
                        response = await client.aio.models.generate_content(
                            model=settings.GEMINI_MODEL,
                            contents=prompt,
                            config=config,
                        )
                    else:
                        # Fallback to run in executor
                        loop = asyncio.get_running_loop()
                        response = await loop.run_in_executor(
                            None,
                            lambda: client.models.generate_content(
                                model=settings.GEMINI_MODEL,
                                contents=prompt,
                                config=config,
                            )
                        )
                    return response.text

                raw_json = await asyncio.wait_for(_call_api(), timeout=settings.GEMINI_TIMEOUT_SECONDS)

            else:
                # Legacy SDK
                async def _call_legacy():
                    loop = asyncio.get_running_loop()
                    resp = await loop.run_in_executor(
                        None,
                        lambda: client.generate_content(
                            prompt,
                            generation_config={"response_mime_type": "application/json", "temperature": 0.1}
                        )
                    )
                    return resp.text

                raw_json = await asyncio.wait_for(_call_legacy(), timeout=settings.GEMINI_TIMEOUT_SECONDS)

            # Clean and parse JSON
            cleaned_text = raw_json.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            parsed = json.loads(cleaned_text)

            # Inject original_text if model omitted it
            if "original_text" not in parsed or not parsed["original_text"]:
                parsed["original_text"] = text

            return CommandIntent(**parsed)

        except asyncio.TimeoutError:
            logger.error("Gemini API call timed out after %s seconds.", settings.GEMINI_TIMEOUT_SECONDS)
            raise GeminiError(f"Gemini API request timed out after {settings.GEMINI_TIMEOUT_SECONDS}s.")
        except json.JSONDecodeError as e:
            logger.error("Failed to parse Gemini JSON output: %s", e)
            raise GeminiError(f"Invalid JSON returned by Gemini: {e}")
        except Exception as e:
            if isinstance(e, (GeminiError, GeminiNotConfiguredError)):
                raise
            logger.error("Unexpected error in Gemini client: %s", e)
            raise GeminiError(f"Gemini API error: {str(e)}")


gemini_client = GeminiClient()
