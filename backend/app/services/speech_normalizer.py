"""Speech and Natural Language Normalizer for Tamil, Tanglish, and English Kirana Commands."""
import re
from typing import Optional, List, Dict, Any, Tuple

# Tamil & Tanglish number mappings
TAMIL_NUMBERS: Dict[str, float] = {
    # Fractions
    "kaal": 0.25,
    "கால்": 0.25,
    "arai": 0.5,
    "அரை": 0.5,
    "mukkaal": 0.75,
    "முக்கால்": 0.75,
    "onnerai": 1.5,
    "ondrarai": 1.5,
    "ஒன்றரை": 1.5,
    "rendarai": 2.5,
    "irandarai": 2.5,
    "இரண்டரை": 2.5,
    "moonarai": 3.5,
    "moondrarai": 3.5,
    "மூன்றரை": 3.5,
    "மூணரை": 3.5,
    "naalarai": 4.5,
    "naangarai": 4.5,
    "நாலரை": 4.5,
    "aindharai": 5.5,
    "anjarai": 5.5,
    "ஐந்தரை": 5.5,

    # 1 - 10
    "oru": 1.0,
    "onnu": 1.0,
    "ondru": 1.0,
    "ஒன்று": 1.0,
    "ஒன்னு": 1.0,
    "ஒண்ணு": 1.0,
    "ஒரு": 1.0,
    "rendu": 2.0,
    "irandu": 2.0,
    "இரண்டு": 2.0,
    "ரெண்டு": 2.0,
    "moonu": 3.0,
    "moondru": 3.0,
    "மூன்று": 3.0,
    "மூணு": 3.0,
    "naalu": 4.0,
    "naangu": 4.0,
    "நான்கு": 4.0,
    "நாலு": 4.0,
    "anju": 5.0,
    "aindhu": 5.0,
    "ayndhu": 5.0,
    "ஐந்து": 5.0,
    "அஞ்சு": 5.0,
    "aaru": 6.0,
    "ஆறு": 6.0,
    "yezhu": 7.0,
    "ezhu": 7.0,
    "yelu": 7.0,
    "ஏழு": 7.0,
    "ettu": 8.0,
    "எட்டு": 8.0,
    "ombodhu": 9.0,
    "onbadhu": 9.0,
    "ஒன்பது": 9.0,
    "ஒம்போது": 9.0,
    "ஒம்பது": 9.0,
    "pathu": 10.0,
    "பத்து": 10.0,

    # 11 - 20
    "pathinonnu": 11.0,
    "பதினொன்று": 11.0,
    "பதினொன்னு": 11.0,
    "pannirendu": 12.0,
    "பன்னிரண்டு": 12.0,
    "பன்னிரெண்டு": 12.0,
    "pathimoonu": 13.0,
    "பதின்மூன்று": 13.0,
    "பத்திமூணு": 13.0,
    "pathinaalu": 14.0,
    "பதினான்கு": 14.0,
    "பத்தினாலு": 14.0,
    "padhinanju": 15.0,
    "pathinanju": 15.0,
    "பதினைந்து": 15.0,
    "பதினஞ்சு": 15.0,
    "pathinaaru": 16.0,
    "பதினாறு": 16.0,
    "pathinezhu": 17.0,
    "பதினேழு": 17.0,
    "pathinettu": 18.0,
    "பதினெட்டு": 18.0,
    "pathombadhu": 19.0,
    "paththombadhu": 19.0,
    "பத்தொன்பது": 19.0,
    "irubadhu": 20.0,
    "இருபது": 20.0,

    # Higher numbers
    "irubathi anju": 25.0,
    "இருபத்தைந்து": 25.0,
    "muppadhu": 30.0,
    "முப்பது": 30.0,
    "naappadhu": 40.0,
    "நாற்பது": 40.0,
    "aimbadhu": 50.0,
    "ஐம்பது": 50.0,
    "arubadhu": 60.0,
    "அறுபது": 60.0,
    "ezhubadhu": 70.0,
    "எழுபது": 70.0,
    "enbhadhu": 80.0,
    "எண்பது": 80.0,
    "thunnooru": 90.0,
    "nooru": 100.0,
    "நூறு": 100.0,
    "irunooru": 200.0,
    "இருநூறு": 200.0,
    "irunoothi aimbadhu": 250.0,
    "irunootri aimbadhu": 250.0,
    "irunootru aimbadhu": 250.0,
    "இருநூற்றைம்பது": 250.0,
    "munnooru": 300.0,
    "முந்நூறு": 300.0,
    "naanooru": 400.0,
    "நானூறு": 400.0,
    "ainnooru": 500.0,
    "ainooru": 500.0,
    "ஐந்நூறு": 500.0,
    "thollayiram": 900.0,
    "தொள்ளாயிரம்": 900.0,
    "ayiram": 1000.0,
    "aayiram": 1000.0,
    "ஆயிரம்": 1000.0,
}

# English spoken number words
ENGLISH_NUMBERS: Dict[str, float] = {
    "zero": 0.0,
    "one": 1.0,
    "two": 2.0,
    "three": 3.0,
    "four": 4.0,
    "five": 5.0,
    "six": 6.0,
    "seven": 7.0,
    "eight": 8.0,
    "nine": 9.0,
    "ten": 10.0,
    "eleven": 11.0,
    "twelve": 12.0,
    "thirteen": 13.0,
    "fourteen": 14.0,
    "fifteen": 15.0,
    "sixteen": 16.0,
    "seventeen": 17.0,
    "eighteen": 18.0,
    "nineteen": 19.0,
    "twenty": 20.0,
    "twenty five": 25.0,
    "thirty": 30.0,
    "forty": 40.0,
    "fifty": 50.0,
    "hundred": 100.0,
    "one hundred": 100.0,
    "two hundred": 200.0,
    "two fifty": 250.0,
    "two hundred fifty": 250.0,
    "two hundred and fifty": 250.0,
    "three hundred": 300.0,
    "four hundred": 400.0,
    "five hundred": 500.0,
    "thousand": 1000.0,
    "one thousand": 1000.0,
}

# Unit normalizations
UNIT_MAPPINGS: Dict[str, str] = {
    "kg": "kg",
    "kgs": "kg",
    "kilo": "kg",
    "kilos": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "கிலோ": "kg",
    "litre": "litre",
    "litres": "litre",
    "liter": "litre",
    "liters": "litre",
    "ltr": "litre",
    "l": "litre",
    "லிட்டர்": "litre",
    "packet": "packet",
    "packets": "packet",
    "pkt": "packet",
    "pkts": "packet",
    "பாக்கெட்": "packet",
    "bottle": "bottle",
    "bottles": "bottle",
    "பாட்டில்": "bottle",
    "bag": "bag",
    "bags": "bag",
    "mootai": "bag",
    "மூட்டை": "bag",
    "piece": "pcs",
    "pieces": "pcs",
    "pc": "pcs",
    "pcs": "pcs",
    "gram": "g",
    "grams": "g",
    "gm": "g",
    "gms": "g",
    "g": "g",
    "கிராம்": "g",
    "mg": "mg",
    "milligram": "mg",
    "ml": "ml",
    "millilitre": "ml",
    "மில்லி": "ml",
    "dozen": "dozen",
    "dozens": "dozen",
    "டஜன்": "dozen",
    "box": "box",
    "boxes": "box",
    "பெட்டி": "box",
    "bundle": "bundle",
    "bundles": "bundle",
}

# Known Kirana product canonical mappings for extraction
PRODUCT_CANONICAL_MAP: Dict[str, str] = {
    # Wheat Flour
    "godhumai maavu": "Wheat Flour",
    "gothumai maavu": "Wheat Flour",
    "godhumai": "Wheat Flour",
    "gothumai": "Wheat Flour",
    "wheat flour": "Wheat Flour",
    "wheat": "Wheat Flour",
    "atta": "Wheat Flour",
    "கோதுமை மாவு": "Wheat Flour",
    "கோதுமை": "Wheat Flour",

    # Gold Winner Oil
    "gold winner oil": "Gold Winner Oil",
    "gold winner": "Gold Winner Oil",
    "goldwinner": "Gold Winner Oil",
    "sunflower oil": "Gold Winner Oil",
    "oil": "Gold Winner Oil",
    "ennai": "Gold Winner Oil",
    "சூரியகாந்தி எண்ணெய்": "Gold Winner Oil",
    "எண்ணெய்": "Gold Winner Oil",

    # Tomato
    "thakkali": "Tomato",
    "tomato": "Tomato",
    "tomatoes": "Tomato",
    "தக்காளி": "Tomato",

    # Onion
    "vengayam": "Onion",
    "onion": "Onion",
    "onions": "Onion",
    "வெங்காயம்": "Onion",

    # Rice
    "ponni boiled rice": "Ponni Boiled Rice",
    "ponni rice": "Ponni Boiled Rice",
    "rice": "Ponni Boiled Rice",
    "arisi": "Ponni Boiled Rice",
    "பொன்னி புழுங்கல் அரிசி": "Ponni Boiled Rice",
    "பொன்னி அரிசி": "Ponni Boiled Rice",
    "அரிசி": "Ponni Boiled Rice",

    # Milk
    "milk": "Milk",
    "paal": "Milk",
    "aavin": "Milk",
    "பால்": "Milk",

    # Sugar
    "sugar": "Sugar",
    "sarkarai": "Sugar",
    "sakkarai": "Sugar",
    "seeni": "Sugar",
    "சர்க்கரை": "Sugar",
    "சீனி": "Sugar",

    # Tea Powder
    "tea powder": "Tea Powder",
    "tea": "Tea Powder",
    "டீ தூள்": "Tea Powder",
    "டீ": "Tea Powder",
    "தேயிலை தூள்": "Tea Powder",
    "தேயிலை": "Tea Powder",

    # Masala
    "masala powder": "Masala Powder",
    "masala": "Masala Powder",
    "garam masala": "Masala Powder",
    "மசாலா தூள்": "Masala Powder",
    "மசாலா": "Masala Powder",

    # Honey
    "honey": "Pure Honey",
    "pure honey": "Pure Honey",
    "thean": "Pure Honey",
    "then": "Pure Honey",
    "தேன்": "Pure Honey",

    # Country Garlic
    "country garlic": "Country Garlic",
    "garlic": "Country Garlic",
    "poondu": "Country Garlic",
    "பூண்டு": "Country Garlic",

    # Coffee Powder
    "filter coffee": "Coffee Powder",
    "coffee powder": "Coffee Powder",
    "coffee": "Coffee Powder",
    "bru": "Coffee Powder",
    "காபி தூள்": "Coffee Powder",
    "காபி": "Coffee Powder",

    # Tata Salt
    "tata salt": "Tata Salt",
    "salt": "Tata Salt",
    "uppu": "Tata Salt",
    "உப்பு": "Tata Salt",

    # Bakery: Milk Bread
    "milk bread": "Milk Bread",
    "bread": "Milk Bread",
    "பிரெட்": "Milk Bread",

    # Biscuits: Marie Gold
    "marie gold biscuits": "Marie Gold Biscuits",
    "marie gold": "Marie Gold Biscuits",
    "marie biscuit": "Marie Gold Biscuits",
    "marie biscuits": "Marie Gold Biscuits",
    "biscuits": "Marie Gold Biscuits",
    "biscuit": "Marie Gold Biscuits",
    "பிஸ்கட்": "Marie Gold Biscuits",

    # Snacks & Confectionery: Chocolates & Chips
    "dairy milk chocolate": "Dairy Milk Chocolate",
    "dairy milk": "Dairy Milk Chocolate",
    "chocolates": "Dairy Milk Chocolate",
    "chocolate": "Dairy Milk Chocolate",
    "சாக்லேட்": "Dairy Milk Chocolate",
    "potato chips snacks": "Potato Chips Snacks",
    "potato chips": "Potato Chips Snacks",
    "chips": "Potato Chips Snacks",
    "snacks": "Potato Chips Snacks",
    "சிப்ஸ்": "Potato Chips Snacks",
    "ஸ்நாக்ஸ்": "Potato Chips Snacks",

    # Personal Care: Shampoo, Serum, Soap, Toothpaste, Hair Oil
    "clinic plus shampoo": "Clinic Plus Shampoo",
    "clinic plus": "Clinic Plus Shampoo",
    "shampoo": "Clinic Plus Shampoo",
    "ஷாம்பு": "Clinic Plus Shampoo",

    "hair serum": "Hair Serum",
    "serum": "Hair Serum",
    "சீரம்": "Hair Serum",

    "hamam soap": "Hamam Soap",
    "hamam": "Hamam Soap",
    "soap": "Hamam Soap",
    "சோப்பு": "Hamam Soap",

    "colgate toothpaste": "Colgate Toothpaste",
    "toothpaste": "Colgate Toothpaste",
    "colgate": "Colgate Toothpaste",
    "டூத்பேஸ்ட்": "Colgate Toothpaste",

    "coconut hair oil": "Coconut Hair Oil",
    "hair oil": "Coconut Hair Oil",
    "தலைமுடி எண்ணெய்": "Coconut Hair Oil",

    # Stationery: Notebook, Pen, Scale, Pencil, Eraser, Paper
    "classmate notebook": "Classmate Notebook",
    "classmate note": "Classmate Notebook",
    "notebook": "Classmate Notebook",
    "note": "Classmate Notebook",
    "நோட்டுப் புத்தகம்": "Classmate Notebook",
    "நோட்டு": "Classmate Notebook",

    "reynolds ball pen": "Reynolds Ball Pen",
    "reynolds pen": "Reynolds Ball Pen",
    "cello ball pen": "Reynolds Ball Pen",
    "ball pen": "Reynolds Ball Pen",
    "pen": "Reynolds Ball Pen",
    "பேனா": "Reynolds Ball Pen",

    "plastic scale 30cm": "Plastic Scale 30cm",
    "plastic scale": "Plastic Scale 30cm",
    "camlin scale 30cm": "Plastic Scale 30cm",
    "camlin scale": "Plastic Scale 30cm",
    "scale 30cm": "Plastic Scale 30cm",
    "scale": "Plastic Scale 30cm",
    "அளவுகோல்": "Plastic Scale 30cm",
    "ஸ்கேல்": "Plastic Scale 30cm",

    "apsara pencil": "Apsara Pencil Box",
    "pencil box": "Apsara Pencil Box",
    "pencil": "Apsara Pencil Box",
    "பென்சில்": "Apsara Pencil Box",

    "dust-free eraser": "Dust-Free Eraser",
    "non-dust eraser": "Dust-Free Eraser",
    "eraser": "Dust-Free Eraser",
    "rubber": "Dust-Free Eraser",
    "ரப்பர்": "Dust-Free Eraser",
    "எரேசர்": "Dust-Free Eraser",

    "a4 copier paper": "A4 Copier Paper",
    "a4 paper": "A4 Copier Paper",
    "copier paper": "A4 Copier Paper",
    "paper": "A4 Copier Paper",
    "தாள்": "A4 Copier Paper",
    "பேப்பர்": "A4 Copier Paper",

    # Vegetables: Ginger, Potato, Carrot, Green Chilli
    "country ginger": "Ginger",
    "ginger": "Ginger",
    "inji": "Ginger",
    "injii": "Ginger",
    "இஞ்சி": "Ginger",
    "பச்சை இஞ்சி": "Ginger",

    "potato": "Potato",
    "potatoes": "Potato",
    "urulaikilangu": "Potato",
    "urulai": "Potato",
    "உருளைக்கிழங்கு": "Potato",
    "உருளை": "Potato",

    "carrot": "Carrot",
    "carrots": "Carrot",
    "carrat": "Carrot",
    "கேரட்": "Carrot",

    "green chilli": "Green Chilli",
    "pachai milagai": "Green Chilli",
    "பச்சை மிளகாய்": "Green Chilli",

    # Fruits: Apple & Banana
    "apple": "Apple",
    "apples": "Apple",
    "ஆப்பிள்": "Apple",

    "banana": "Banana",
    "bananas": "Banana",
    "vazhaipazham": "Banana",
    "vaazhai": "Banana",
    "வாழைப்பழம்": "Banana",

    # Dals & Flours: Toor Dal, Urad Dal, Ghee, Maida, Rava
    "toor dal": "Toor Dal",
    "tuvaram": "Toor Dal",
    "துவரம்": "Toor Dal",
    "துவரம் பருப்பு": "Toor Dal",

    "urad dal": "Urad Dal",
    "ulundhu": "Urad Dal",
    "உளுந்து": "Urad Dal",
    "உளுத்தம் பருப்பு": "Urad Dal",

    "ghee": "Ghee",
    "nei": "Ghee",
    "நெய்": "Ghee",

    "maida maavu": "Maida",
    "maida": "Maida",
    "மைதா": "Maida",

    "rava": "Rava",
    "sooji": "Rava",
    "ரவை": "Rava",

    # Household: Battery, Detergent, Dishwash
    "aa battery": "AA Battery",
    "battery": "AA Battery",
    "batteries": "AA Battery",
    "cell": "AA Battery",
    "பேட்டரி": "AA Battery",

    "surf excel detergent": "Surf Excel Detergent",
    "surf excel": "Surf Excel Detergent",
    "surf": "Surf Excel Detergent",
    "detergent": "Surf Excel Detergent",
    "washing powder": "Surf Excel Detergent",
    "சோப்புத்தூள்": "Surf Excel Detergent",
    "டிட்டர்ஜென்ட்": "Surf Excel Detergent",

    "vim dishwash liquid": "Vim Dishwash Liquid",
    "vim dishwash": "Vim Dishwash Liquid",
    "dishwash": "Vim Dishwash Liquid",
    "vim": "Vim Dishwash Liquid",
    "vim gel": "Vim Dishwash Liquid",
    "டிஷ்வாஷ்": "Vim Dishwash Liquid",
}

DEFAULT_PRODUCT_UNITS: Dict[str, str] = {
    "Ponni Boiled Rice": "kg",
    "Refined White Sugar": "kg",
    "Sugar": "kg",
    "Tomato": "kg",
    "Onion": "kg",
    "Country Garlic": "kg",
    "Wheat Flour": "kg",
    "Gold Winner Oil": "litre",
    "Milk": "litre",
    "Tea Powder": "packet",
    "Coffee Powder": "packet",
    "Masala Powder": "packet",
    "Tata Salt": "packet",
    "Milk Bread": "packet",
    "Marie Gold Biscuits": "packet",
    "Potato Chips Snacks": "packet",
    "Pure Honey": "bottle",
    "Clinic Plus Shampoo": "bottle",
    "Hair Serum": "bottle",
    "Coconut Hair Oil": "bottle",
    "Dairy Milk Chocolate": "piece",
    "Hamam Soap": "piece",
    "Colgate Toothpaste": "piece",
    "Classmate Notebook": "piece",
    "Reynolds Ball Pen": "piece",
    "Cello Ball Pen": "piece",
    "Plastic Scale 30cm": "piece",
    "Camlin Scale 30cm": "piece",
    "Apsara Pencil Box": "piece",
    "Apsara Pencil": "piece",
    "Dust-Free Eraser": "piece",
    "Non-Dust Eraser": "piece",
    "A4 Copier Paper": "packet",
    "Ginger": "kg",
    "Potato": "kg",
    "Carrot": "kg",
    "Green Chilli": "kg",
    "Apple": "kg",
    "Banana": "dozen",
    "Ghee": "bottle",
    "Maida": "kg",
    "Rava": "kg",
    "Toor Dal": "kg",
    "Urad Dal": "kg",
    "AA Battery": "piece",
    "Surf Excel Detergent": "packet",
    "Vim Dishwash Liquid": "bottle",
}


def detect_spoken_language(text: str) -> str:
    """
    Detect the language style of Kirana merchant voice speech:
    - 'Tamil': Contains Tamil Unicode script ([\u0B80-\u0BFF]).
    - 'English': Pure English grammar and interrogatives with no Tanglish verbs.
    - 'Tanglish': Tamil spoken words transliterated in Latin script (e.g. 'evlo irukku', 'add pannu').
    """
    if not text or not text.strip():
        return "Tamil"

    # 1. Tamil script detection
    if re.search(r"[\u0B80-\u0BFF]", text):
        return "Tamil"

    lower = text.lower()

    # 2. Tanglish markers & verbs
    tanglish_markers = {
        "evlo", "evvalavu", "irukku", "iruka", "innaiku", "innaikku", "iniku",
        "pannu", "pannunga", "pannalama", "panniyachu", "podu", "podunga",
        "korainga", "kodu", "kuduthuten", "venum", "sollu", "solla", "sonnen",
        "mattum", "illa", "illai", "adhula", "innum", "aama", "seri",
        "vengayam", "thakkali", "arisi", "maavu", "ennai", "thean", "then",
        "paal", "sarkkarai", "kooda", "aprom", "matrum", "ethana", "kaatu",
        "stock-la", "customer-ku", "rate-u", "vilai"
    }

    words = set(re.findall(r"\b[a-z\-]+\b", lower))
    for tm in tanglish_markers:
        if tm in words or any(tm in w for w in words):
            return "Tanglish"

    # Check for stem endings like '...pannu', '...podu', '...kora'
    if any(re.search(r"(?:pannu|podu|iruk|evlo|sollu)", w) for w in words):
        return "Tanglish"

    # 3. English indicators
    english_query_words = {
        "how", "what", "which", "where", "is", "are", "do", "we", "have", "current",
        "show", "tell", "much", "many", "stock", "give", "please", "can", "you",
        "create", "today", "todays", "sales", "report", "orders", "total", "price",
        "add", "sell", "record", "bill", "for", "customer", "want", "need", "items"
    }

    if words.intersection(english_query_words):
        return "English"

    return "Tanglish"


def normalize_spoken_numbers(text: str) -> str:
    """
    Replace Tamil/Tanglish and English number words with digits.
    Supports Unicode Indic script boundaries as well as ASCII.
    e.g. 'pathu kilo godhumai maavu' -> '10 kilo godhumai maavu'
         'one kilo tomato, two kilo onion' -> '1 kilo tomato, 2 kilo onion'
         'அரை கிலோ tomato' -> '0.5 கிலோ tomato'
         'ஆயிரம் கிலோ rice' -> '1000 கிலோ rice'
    """
    if not text:
        return ""

    normalized = text

    # Sort dictionary keys by descending length so multi-word numbers like 'irubathi anju' are replaced first
    all_numbers = {**TAMIL_NUMBERS, **ENGLISH_NUMBERS}
    sorted_keys = sorted(all_numbers.keys(), key=lambda k: len(k), reverse=True)

    for word in sorted_keys:
        val = all_numbers[word]
        # Match Indic & ASCII boundary safely with case-insensitivity
        pattern = r"(?:^|(?<=[\s\.,;!?()\"\'\—\-]))" + re.escape(word) + r"(?:$|(?=[\s\.,;!?()\"\'\—\-]))"
        val_str = str(int(val)) if val.is_integer() else str(val)
        normalized = re.sub(pattern, val_str, normalized, flags=re.IGNORECASE)

    return normalized


def extract_effective_quantity(text: str) -> Optional[float]:
    """
    Extract the intended numeric quantity from text.
    Handles corrections such as:
    - '2 kilo illa 3 kilo' -> 3.0
    - 'இரண்டு கிலோ… இல்ல மூணு கிலோ' -> 3.0
    - 'அரை கிலோ' -> 0.5
    - '1000 கிலோ' -> 1000.0
    """
    if not text:
        return None

    normalized = normalize_spoken_numbers(text)

    # 1. Check for correction pattern: <num1> ... (இல்ல|illa|illai|no) ... <num2>
    correction_match = re.search(
        r"(\d+(?:\.\d+)?).*?(?:இல்ல|illa|illai|no|வண்டாம்|வேண்டாம்|\.\.\.|\…|\—|\-).*?(\d+(?:\.\d+)?)",
        normalized,
        re.IGNORECASE
    )
    if correction_match:
        try:
            return float(correction_match.group(2))
        except (ValueError, TypeError):
            pass

    # 2. Match standard number in string
    matches = re.findall(r"(\d+(?:\.\d+)?)", normalized)
    if matches:
        try:
            return float(matches[0])
        except (ValueError, TypeError):
            pass

    return None


def extract_kirana_items_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Extract multiple grocery items with their quantities and units from colloquial Kirana text.
    Handles phrases like:
    - 'Customer-ku one kilo tomato, two kilo onion, three kilo rice, two litre milk, two packet sugar'
    - 'Customer-ku 2 kg rice, 1 kg sugar, 3 packet tea powder, one honey bottle, 2 tomato, garlic, coffee powder, masala, chocolates, shampoo, serum, bread, biscuits, notebook, pen, scale ellam bill podu'
    Returns list of dicts: [{'product_name': 'Ponni Boiled Rice', 'quantity': 2.0, 'unit': 'kg'}, ...]
    """
    if not text or not text.strip():
        return []

    normalized = normalize_spoken_numbers(text)

    # 1. First attempt: Split by commas, conjunctions, or 'and' / 'aprom' / 'matrum'
    split_parts = re.split(r"[,;]|(?:\band\b)|(?:\baprom\b)|(?:\bmatrum\b)", normalized, flags=re.IGNORECASE)
    candidate_phrases = [p.strip() for p in split_parts if p.strip()]

    items: List[Dict[str, Any]] = []

    filler_words = [
        "customer-ku", "customer", "ku", "oru", "sale", "sell", "pannunga", "panniten",
        "podunga", "podu", "add", "kuduthuten", "kudu", "kudunga", "venum", "stock",
        "innaiku", "please", "ellam", "bill", "ready", "pannidunga", "edunga"
    ]

    def parse_single_phrase(phrase: str) -> Optional[Dict[str, Any]]:
        # Check for number in phrase
        qty_match = re.search(r"(\d+(?:\.\d+)?)", phrase)
        has_number = bool(qty_match)
        qty = float(qty_match.group(1)) if has_number else 1.0

        lower_phrase = phrase.lower()

        # Check for unit
        unit = None
        for u_key, u_val in UNIT_MAPPINGS.items():
            if re.search(r"\b" + re.escape(u_key) + r"\b", lower_phrase):
                unit = u_val
                break

        # Remove quantity and unit to isolate product name
        cleaned_phrase = lower_phrase
        if has_number:
            cleaned_phrase = re.sub(r"(\d+(?:\.\d+)?)", "", cleaned_phrase)
        for u_key in UNIT_MAPPINGS.keys():
            cleaned_phrase = re.sub(r"\b" + re.escape(u_key) + r"\b", "", cleaned_phrase)

        for fw in filler_words:
            cleaned_phrase = re.sub(r"\b" + re.escape(fw) + r"\b", "", cleaned_phrase)

        cleaned_phrase = cleaned_phrase.strip()
        if not cleaned_phrase:
            return None

        # Match to canonical product name
        matched_canonical = None
        # Try exact or substring match in PRODUCT_CANONICAL_MAP
        for syn, canon in sorted(PRODUCT_CANONICAL_MAP.items(), key=lambda x: len(x[0]), reverse=True):
            if re.search(r"\b" + re.escape(syn) + r"\b", cleaned_phrase):
                matched_canonical = canon
                break
        if not matched_canonical:
            for syn, canon in PRODUCT_CANONICAL_MAP.items():
                if syn in cleaned_phrase or cleaned_phrase in syn:
                    matched_canonical = canon
                    break

        if not matched_canonical:
            # If no known canonical product matched AND no number was provided, this was likely just filler
            if not has_number:
                return None
            matched_canonical = cleaned_phrase.title()

        # Assign default unit if none was explicitly stated
        if not unit:
            unit = DEFAULT_PRODUCT_UNITS.get(matched_canonical, "kg")

        return {
            "product_name": matched_canonical,
            "quantity": qty,
            "unit": unit
        }

    # 1. Parse all candidate phrases from comma / conjunction split
    for phrase in candidate_phrases:
        parsed = parse_single_phrase(phrase)
        if parsed:
            # Deduplicate or accumulate if already exists
            existing = next((it for it in items if it["product_name"] == parsed["product_name"]), None)
            if existing:
                existing["quantity"] += parsed["quantity"]
            else:
                items.append(parsed)

    # 2. If comma-split was not used (single long phrase) and items <= 1, scan tokens sequentially
    if len(items) <= 1:
        tokens_items: List[Dict[str, Any]] = []
        # Sort synonyms by length descending to match multi-word names first
        sorted_synonyms = sorted(PRODUCT_CANONICAL_MAP.keys(), key=lambda s: len(s), reverse=True)
        # Find spans of all matched products in normalized text
        spans = []
        for syn in sorted_synonyms:
            for match in re.finditer(r"\b" + re.escape(syn) + r"\b", normalized, flags=re.IGNORECASE):
                # Ensure no overlapping spans
                if not any(s[0] <= match.start() < s[1] or s[0] < match.end() <= s[1] for s in spans):
                    spans.append((match.start(), match.end(), syn, PRODUCT_CANONICAL_MAP[syn]))

        spans.sort(key=lambda s: s[0])

        for idx, (start, end, syn, canon) in enumerate(spans):
            prev_end = spans[idx - 1][1] if idx > 0 else 0
            next_start = spans[idx + 1][0] if idx + 1 < len(spans) else len(normalized)
            preceding_text = normalized[prev_end:start].strip()
            following_text = normalized[end:next_start].strip()

            # Check for quantity in preceding text (e.g. '2 kg rice'), or following text (e.g. 'rice 2 kg')
            qty_matches_pre = re.findall(r"(\d+(?:\.\d+)?)", preceding_text)
            qty_matches_post = re.findall(r"(\d+(?:\.\d+)?)", following_text)
            if qty_matches_pre:
                qty = float(qty_matches_pre[-1])
            elif qty_matches_post:
                qty = float(qty_matches_post[0])
            else:
                qty = 1.0

            # Check for unit in preceding or following text
            context_window = preceding_text + " " + following_text
            unit = None
            for u_key, u_val in UNIT_MAPPINGS.items():
                if re.search(r"\b" + re.escape(u_key) + r"\b", context_window, flags=re.IGNORECASE):
                    unit = u_val
                    break
            if not unit:
                unit = DEFAULT_PRODUCT_UNITS.get(canon, "kg")

            existing = next((it for it in tokens_items if it["product_name"] == canon), None)
            if existing:
                existing["quantity"] += qty
            else:
                tokens_items.append({
                    "product_name": canon,
                    "quantity": qty,
                    "unit": unit
                })

        if len(tokens_items) > len(items):
            items = tokens_items

    return items

