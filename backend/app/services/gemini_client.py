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
1. Tamil (தமிழ் script, e.g., "5 கிலோ அரிசி இருப்பு சேர்க்க", "இன்னைக்கு rice add பண்ணு", "மசாலா bill போடு", "அரிசி stock எவ்வளவு?")
2. Tanglish (Tamil in English script, e.g., "Innaiku 5 kilo rice stock add pannunga", "Tomato one kg add பண்ணு", "Sugar stock evlo irukku?", "Innaiku sales evlo?")
3. English (e.g., "Add 10 packets of biscuits", "Sell 2 bottles of sunflower oil")
4. Mixed colloquial Kirana speech (e.g., "Customer-ku 2 oil bottle kuduthuten", "Sugar 20 kilo vandhirukku", "Rice 5 bag sel aachu")

SUPPORTED INTENTS:
- ADD_STOCK: Merchant received delivery or is adding inventory (e.g. "Rice add பண்ணு", "10 kg Wheat Flour add pannunga", "Five kg tea powder add பண்ணு").
- SELL_PRODUCT: Merchant sold items, creates a customer bill, or records a sale (e.g. "மசாலா bill போடு", "Tomato one kg", "Customer-ku 2 kg onion bill podu").
- CHECK_STOCK: Merchant asks about current stock level of a product (e.g. "அரிசி stock எவ்வளவு?", "தக்காளி stock இல்லையா?", "Sugar stock evlo?").
- LOW_STOCK_QUERY: Merchant asks which products are running low or out of stock (e.g. "Low stock sollu", "குறைந்த இருப்பு").
- SALES_REPORT: Merchant asks for sales revenue / bill count (e.g. "இன்னைக்கு sales எவ்வளவு?", "Today sales evlo?").
- PRODUCT_SALES_REPORT: Merchant asks for sales of a specific product or top selling product.
- INVENTORY_REPORT: Merchant asks for total inventory valuation or catalog overview.
- CREATE_PRODUCT: Merchant wants to register a new product item.
- UPDATE_PRICE: Merchant wants to update or change selling price of an item.
- CONFIRM_ACTION: Merchant affirms or confirms an operation ("Aama", "Seri", "Confirm", "Yes", "ஆமா", "சரி").
- CANCEL_ACTION: Merchant cancels or rejects an operation ("Cancel", "Vendaam", "வேண்டாம்", "ரத்து").
- GREETING: Conversational hello/vanakkam (e.g. "Vanakkam", "வணக்கம்", "Hello", "Hi").
- THANK_YOU: Merchant expressing gratitude (e.g. "Thank you", "நன்றி", "Thanks", "Nandri", "Thank you so much", "Okay thank you").
- GENERAL_QUERY: Conversational general acknowledgment or question (e.g. "Okay", "சரி" without pending action).
- UNKNOWN: Completely unintelligible speech or unrelated query.

TAMIL-FIRST LANGUAGE POLICY:
1. When input is Tamil, Tanglish, or Mixed Tamil-English, clarification_question MUST be in natural colloquial Tamil (தமிழ்).
2. NEVER return "I could not understand" or "I could not understand that command".
3. NEVER return an English question when the user speaks Tamil or Tanglish.
4. Examples of Tamil clarification questions:
   - Missing quantity for stock addition: "எவ்வளவு அரிசி சேர்க்க வேண்டும்?" / "எவ்வளவு அளவு சேர்க்க வேண்டும்?"
   - Missing quantity for sale / bill: "மசாலா எவ்வளவு வேண்டும்?" / "எவ்வளவு பில் போட வேண்டும்?"
   - Missing product: "மன்னிக்கவும், எந்தப் பொருளைப் பற்றி சொல்கிறீர்கள்?" / "எந்தப் பொருளுக்கு சேர்க்க வேண்டும்?"
   - Unrecognized speech: "மன்னிக்கவும், எந்தப் பொருளைப் பற்றி சொல்கிறீர்கள்?"

CRITICAL CONVERSATIONAL & KIRANA RULES:
1. Affirmation: "Aama", "Seri", "Confirm", "Yes", "Confirm pannunga", "ஆமா", "சரி" -> intent: "CONFIRM_ACTION".
2. Cancellation: "Cancel", "Cancel pannunga", "Vendaam", "Venaam", "வேண்டாம்", "ரத்து" -> intent: "CANCEL_ACTION".
3. Missing Quantity: If merchant says "Rice add பண்ணு", intent is ADD_STOCK, product_name: "Rice", quantity: null, requires_clarification: true, clarification_question: "எவ்வளவு அரிசி சேர்க்க வேண்டும்?".
4. Bill Creation: If merchant says "மசாலா bill போடு" or "bill podu", intent is SELL_PRODUCT. If quantity is missing, quantity: null, requires_clarification: true, clarification_question: "மசாலா எவ்வளவு வேண்டும்?".
5. Fragmented Retail Sales: If merchant says "Tomato one kg" or "தக்காளி ஒரு கிலோ", intent is SELL_PRODUCT (retail customer purchase), product_name: "Tomato", quantity: 1.0, unit: "kg", requires_clarification: false.
6. Contextual Relative Addition: "அந்த rice இன்னும் five kilo" or "Innum 5 kilo add pannu" -> intent: ADD_STOCK, quantity: 5.0, unit: "kg", product_name: null (or context product).
7. Pronoun Bill: "அதுக்கு bill போடு" -> intent: SELL_PRODUCT, product_name: null (to be filled from active product in context).
8. Context Product Correction: If merchant says "இல்ல, onion சொன்னேன்" or "அது இல்ல, tomato சொன்னேன்", they are correcting the product: return the corrected product_name ("Onion" / "Tomato") with previous operation intent.
9. Quantity Correction: If merchant says "இரண்டு கிலோ… இல்ல மூணு கிலோ", the corrected quantity is 3.0.
10. Tamil Number & Fraction Normalization:
    - அரை = 0.5, கால் = 0.25, முக்கால் = 0.75, ஒன்றரை = 1.5, இரண்டரை = 2.5
    - ஒன்று/ஒன்னு/one = 1, இரண்டு/ரெண்டு/two = 2, மூன்று/மூணு/three = 3, நான்கு/நாலு/four = 4, ஐந்து/அஞ்சு/five = 5
    - பத்து/ten = 10, நூறு/hundred = 100, ஆயிரம்/thousand = 1000
11. Multi-item customer orders: populate "items" array with individual objects: [{"product_name": "Tomato", "quantity": 1.0, "unit": "kg"}, ...].
12. Normalize units to standard codes: "kg", "litre", "packet", "pcs", "g", "ml", "bag", "box".
13. Return raw JSON matching this schema:
{
  "intent": "ADD_STOCK" | "SELL_PRODUCT" | "CHECK_STOCK" | "LOW_STOCK_QUERY" | "SALES_REPORT" | "PRODUCT_SALES_REPORT" | "INVENTORY_REPORT" | "CREATE_PRODUCT" | "UPDATE_PRICE" | "CONFIRM_ACTION" | "CANCEL_ACTION" | "GREETING" | "THANK_YOU" | "GENERAL_QUERY" | "UNKNOWN",
  "language": "Tamil" | "Tanglish" | "English" | "Mixed",
  "original_text": "<verbatim input>",
  "normalized_text": "<concise English description of action>",
  "entities": {
    "product_name": "<string or null>",
    "quantity": <float or null>,
    "unit": "<string or null>",
    "price": <float or null>,
    "date": "<string or null>",
    "customer_name": "<string or null>",
    "payment_method": "<string or null>",
    "items": [
      {
        "product_name": "<string>",
        "quantity": <float>,
        "unit": "<string>"
      }
    ]
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

    async def generate_intent_async(
        self,
        text: str,
        context: Optional[dict] = None
    ) -> CommandIntent:
        """Call Gemini asynchronously with prompt and parse structured CommandIntent."""
        client = self._get_client()

        prompt_parts = [f"Kirana Shopkeeper Command:\n\"{text.strip()}\""]
        if context:
            ctx_lines = []
            if context.get("active_product_name"):
                ctx_lines.append(f"- Active Product: {context['active_product_name']}")
            if context.get("last_action"):
                ctx_lines.append(f"- Last Operation: {context['last_action']}")
            if context.get("last_quantity"):
                ctx_lines.append(f"- Last Quantity: {context['last_quantity']} {context.get('last_unit', '')}")
            if context.get("pending_action_id"):
                ctx_lines.append(f"- Pending Action Awaiting Confirmation: {context.get('pending_action_type', 'YES')}")
            if ctx_lines:
                prompt_parts.append("\nActive Conversation Context:\n" + "\n".join(ctx_lines))
        prompt_parts.append("\nJSON Output:")
        prompt = "\n".join(prompt_parts)

        # Candidate models for fallback if a model is deprecated/unavailable
        models_to_try = [settings.GEMINI_MODEL, "gemini-3-flash-preview", "gemini-3.5-flash", "gemini-flash-latest", "gemini-3.8-flash"]
        unique_models = []
        for m in models_to_try:
            if m and m not in unique_models:
                unique_models.append(m)

        raw_json = None
        last_error = None

        # Primary Fast Execution: Direct Google Generative Language REST API
        import httpx
        for model_name in unique_models:
            clean_m = model_name.replace("models/", "")
            rest_url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_m}:generateContent?key={settings.GEMINI_API_KEY}"
            payload = {
                "systemInstruction": {"parts": [{"text": GEMINI_SYSTEM_INSTRUCTION}]},
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.1
                }
            }
            try:
                async with httpx.AsyncClient(timeout=min(settings.GEMINI_TIMEOUT_SECONDS, 5.0)) as http_client:
                    r = await http_client.post(rest_url, json=payload)
                    if r.status_code == 200:
                        res_data = r.json()
                        candidates = res_data.get("candidates", [])
                        if candidates and "content" in candidates[0]:
                            parts = candidates[0]["content"].get("parts", [])
                            if parts and "text" in parts[0]:
                                raw_json = parts[0]["text"]
                                settings.GEMINI_MODEL = clean_m
                                break
                    elif r.status_code == 429:
                        logger.warning("Gemini REST model %s quota exceeded (429). Fast failing to local Kirana NLP.", clean_m)
                        last_error = GeminiError(f"Model {clean_m} quota exceeded (429)")
                        break
                    elif r.status_code in (404, 503):
                        logger.warning("Gemini REST model %s returned status %d (%s), trying fallback...", clean_m, r.status_code, r.text[:120])
                        last_error = GeminiError(f"Model {clean_m} returned HTTP {r.status_code}: {r.text[:120]}")
                        continue
                    else:
                        logger.warning("Gemini REST model %s returned HTTP %d, trying fallback...", clean_m, r.status_code)
                        last_error = GeminiError(f"Model {clean_m} returned HTTP {r.status_code}")
                        continue
            except httpx.TimeoutException:
                logger.warning("Gemini REST request for model %s timed out, trying fallback...", clean_m)
                last_error = GeminiError(f"Model {clean_m} timed out")
                continue
            except httpx.RequestError as re:
                logger.warning("Gemini REST connection error for %s: %s", clean_m, re)
                last_error = re
                # Network disconnected / sandbox isolation, stop trying external REST
                break

        # Secondary Execution: GenAI SDK Fallback if REST was not populated and not quota exhausted
        if not raw_json and not (isinstance(last_error, GeminiError) and "429" in str(last_error)):
            try:
                if self._client_type == "genai":
                    from google.genai import types

                    config = types.GenerateContentConfig(
                        system_instruction=GEMINI_SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        temperature=0.1,
                    )

                    for model_name in unique_models:
                        try:
                            async def _call_api(m=model_name):
                                if hasattr(client, "aio") and hasattr(client.aio, "models"):
                                    response = await client.aio.models.generate_content(
                                        model=m,
                                        contents=prompt,
                                        config=config,
                                    )
                                else:
                                    loop = asyncio.get_running_loop()
                                    response = await loop.run_in_executor(
                                        None,
                                        lambda: client.models.generate_content(
                                            model=m,
                                            contents=prompt,
                                            config=config,
                                        )
                                    )
                                return response.text

                            raw_json = await asyncio.wait_for(_call_api(model_name), timeout=settings.GEMINI_TIMEOUT_SECONDS)
                            if raw_json:
                                settings.GEMINI_MODEL = model_name
                                break
                        except Exception as me:
                            err_str = str(me).lower()
                            if any(k in err_str for k in ("404", "not_found", "no longer available", "deprecated", "503", "unavailable")):
                                logger.warning("Gemini model %s not available (%s), trying fallback...", model_name, me)
                                last_error = me
                                continue
                            raise
                else:
                    # Legacy SDK
                    for model_name in unique_models:
                        try:
                            async def _call_legacy(m=model_name):
                                loop = asyncio.get_running_loop()
                                import google.generativeai as legacy_genai
                                m_instance = legacy_genai.GenerativeModel(
                                    model_name=m,
                                    system_instruction=GEMINI_SYSTEM_INSTRUCTION
                                )
                                resp = await loop.run_in_executor(
                                    None,
                                    lambda: m_instance.generate_content(
                                        prompt,
                                        generation_config={"response_mime_type": "application/json", "temperature": 0.1}
                                    )
                                )
                                return resp.text

                            raw_json = await asyncio.wait_for(_call_legacy(model_name), timeout=settings.GEMINI_TIMEOUT_SECONDS)
                            if raw_json:
                                settings.GEMINI_MODEL = model_name
                                break
                        except Exception as me:
                            err_str = str(me).lower()
                            if any(k in err_str for k in ("404", "not_found", "no longer available", "deprecated", "503", "unavailable")):
                                logger.warning("Gemini legacy model %s not available (%s), trying fallback...", model_name, me)
                                last_error = me
                                continue
                            raise
            except Exception as e:
                logger.warning("SDK fallback also encountered issue: %s", e)

        if not raw_json:
            if last_error:
                raise GeminiError(f"Gemini API error: {str(last_error)}")
            raise GeminiError("Gemini failed to return valid response across all models.")

        try:
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

        except json.JSONDecodeError as e:
            logger.error("Failed to parse Gemini JSON output: %s", e)
            raise GeminiError(f"Invalid JSON returned by Gemini: {e}")


gemini_client = GeminiClient()

