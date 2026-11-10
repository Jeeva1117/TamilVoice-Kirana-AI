"""Database Migration & Universal Catalog Seed:
Adds `aliases` and `reorder_level` columns and populates complete Kirana catalog across 8 categories.
"""
import logging
from sqlalchemy import text
from backend.app.database import engine, SessionLocal
from backend.app.models.product import Product

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CATALOG_SEED = [
    # 1. Groceries
    {
        "name": "Ponni Boiled Rice",
        "name_ta": "பொன்னி புழுங்கல் அரிசி",
        "sku": "SKU-RICE-001",
        "category": "Grains & Flours",
        "quantity": 26.0,
        "unit": "kg",
        "purchase_price": 42.0,
        "selling_price": 55.0,
        "minimum_stock_level": 10.0,
        "reorder_level": 20.0,
        "aliases": "rice, arisi, ponni, அரிசி, சாப்பாடு அரிசி, புழுங்கல் அரிசி, பொன்னி அரிசி",
        "description": "Premium South Indian Ponni Boiled Rice"
    },
    {
        "name": "Wheat Flour",
        "name_ta": "கோதுமை மாவு",
        "sku": "SKU-WHEAT-001",
        "category": "Grains & Flours",
        "quantity": 20.0,
        "unit": "kg",
        "purchase_price": 32.0,
        "selling_price": 45.0,
        "minimum_stock_level": 8.0,
        "reorder_level": 15.0,
        "aliases": "atta, wheat, godhumai, godhumai maavu, gothumai, கோதுமை, கோதுமை மாவு, மாவு",
        "description": "100% Whole Wheat Chakki Atta"
    },
    {
        "name": "Toor Dal",
        "name_ta": "துவரம் பருப்பு",
        "sku": "SKU-TOOR-001",
        "category": "Groceries",
        "quantity": 25.0,
        "unit": "kg",
        "purchase_price": 110.0,
        "selling_price": 140.0,
        "minimum_stock_level": 10.0,
        "reorder_level": 15.0,
        "aliases": "toor dal, tuvaram, tuvaram paruppu, துவரம் பருப்பு, துவரை, துவரம்",
        "description": "Unpolished Desi Toor Dal"
    },
    {
        "name": "Urad Dal",
        "name_ta": "உளுத்தம் பருப்பு",
        "sku": "SKU-URAD-001",
        "category": "Groceries",
        "quantity": 25.0,
        "unit": "kg",
        "purchase_price": 100.0,
        "selling_price": 130.0,
        "minimum_stock_level": 10.0,
        "reorder_level": 15.0,
        "aliases": "urad dal, ulundhu, ulunthu, உளுந்து, உளுத்தம் பருப்பு",
        "description": "Premium White Whole Urad Dal"
    },
    {
        "name": "Maida",
        "name_ta": "மைதா",
        "sku": "SKU-MAIDA-001",
        "category": "Groceries",
        "quantity": 20.0,
        "unit": "kg",
        "purchase_price": 30.0,
        "selling_price": 42.0,
        "minimum_stock_level": 5.0,
        "reorder_level": 10.0,
        "aliases": "maida, maida maavu, மைதா, மைதா மாவு, all purpose flour",
        "description": "Refined White Wheat Flour"
    },
    {
        "name": "Rava",
        "name_ta": "ரவை",
        "sku": "SKU-RAVA-001",
        "category": "Groceries",
        "quantity": 20.0,
        "unit": "kg",
        "purchase_price": 32.0,
        "selling_price": 44.0,
        "minimum_stock_level": 5.0,
        "reorder_level": 10.0,
        "aliases": "rava, sooji, semolina, ரவை, சூஜி",
        "description": "Roasted Fine Wheat Sooji Rava"
    },
    {
        "name": "Ghee",
        "name_ta": "நெய்",
        "sku": "SKU-GHEE-001",
        "category": "Groceries",
        "quantity": 15.0,
        "unit": "bottle",
        "purchase_price": 280.0,
        "selling_price": 350.0,
        "minimum_stock_level": 5.0,
        "reorder_level": 10.0,
        "aliases": "ghee, pure ghee, cow ghee, nei, நெய், பசு நெய்",
        "description": "Aromatic Cow Ghee 500ml"
    },
    {
        "name": "Gold Winner Oil",
        "name_ta": "சூரியகாந்தி எண்ணெய்",
        "sku": "SKU-OIL-001",
        "category": "Oils & Ghee",
        "quantity": 20.0,
        "unit": "litre",
        "purchase_price": 115.0,
        "selling_price": 135.0,
        "minimum_stock_level": 8.0,
        "reorder_level": 15.0,
        "aliases": "oil, gold winner, sunflower oil, ennai, enna, எண்ணெய், சூரியகாந்தி எண்ணெய்",
        "description": "Refined Sunflower Cooking Oil"
    },
    {
        "name": "Sugar",
        "name_ta": "சர்க்கரை",
        "sku": "SKU-SUGAR-001",
        "category": "Groceries",
        "quantity": 24.0,
        "unit": "kg",
        "purchase_price": 36.0,
        "selling_price": 45.0,
        "minimum_stock_level": 10.0,
        "reorder_level": 20.0,
        "aliases": "sugar, sakkarai, sarkarai, seeni, சர்க்கரை, சீனி",
        "description": "Crystal Refined White Sugar"
    },
    {
        "name": "Tata Salt",
        "name_ta": "உப்பு",
        "sku": "SKU-SALT-001",
        "category": "Groceries",
        "quantity": 50.0,
        "unit": "packet",
        "purchase_price": 18.0,
        "selling_price": 24.0,
        "minimum_stock_level": 15.0,
        "reorder_level": 25.0,
        "aliases": "salt, tata salt, uppu, உப்பு, கல் உப்பு, தூள் உப்பு",
        "description": "Vacuum Evaporated Iodized Salt 1kg"
    },
    {
        "name": "Tea Powder",
        "name_ta": "தேயிலை தூள்",
        "sku": "SKU-TEA-001",
        "category": "Beverages",
        "quantity": 19.0,
        "unit": "packet",
        "purchase_price": 30.0,
        "selling_price": 40.0,
        "minimum_stock_level": 8.0,
        "reorder_level": 15.0,
        "aliases": "tea, tea powder, 3 roses, chakra gold, டீ, டீ தூள், தேயிலை",
        "description": "Strong Leaf Tea Powder 250g"
    },
    {
        "name": "Coffee Powder",
        "name_ta": "காபி தூள்",
        "sku": "SKU-COFFEE-001",
        "category": "Groceries",
        "quantity": 30.0,
        "unit": "packet",
        "purchase_price": 38.0,
        "selling_price": 48.0,
        "minimum_stock_level": 8.0,
        "reorder_level": 15.0,
        "aliases": "coffee, coffee powder, bru, filter coffee, காபி, காபி தூள், ப்ரூ",
        "description": "Instant Filter Coffee Powder 100g"
    },
    {
        "name": "Pure Honey",
        "name_ta": "தேன்",
        "sku": "SKU-HONEY-001",
        "category": "Groceries",
        "quantity": 14.0,
        "unit": "bottle",
        "purchase_price": 140.0,
        "selling_price": 180.0,
        "minimum_stock_level": 5.0,
        "reorder_level": 10.0,
        "aliases": "honey, pure honey, dabur honey, thean, then, தேன்",
        "description": "Pure Natural Forest Honey 250g"
    },
    {
        "name": "Milk",
        "name_ta": "பால்",
        "sku": "SKU-MILK-001",
        "category": "Dairy",
        "quantity": 20.0,
        "unit": "litre",
        "purchase_price": 24.0,
        "selling_price": 28.0,
        "minimum_stock_level": 5.0,
        "reorder_level": 10.0,
        "aliases": "milk, paal, aavin, cow milk, பால், ஆவின் பால்",
        "description": "Fresh Toned Milk 500ml packet"
    },
    {
        "name": "Masala Powder",
        "name_ta": "மசாலா தூள்",
        "sku": "SKU-MASALA-001",
        "category": "Spices",
        "quantity": 15.0,
        "unit": "packet",
        "purchase_price": 26.0,
        "selling_price": 35.0,
        "minimum_stock_level": 5.0,
        "reorder_level": 10.0,
        "aliases": "masala, masala powder, garam masala, sambar masala, மசாலா, மசாலா தூள், கரம் மசாலா",
        "description": "Aromatic Garam Masala 100g"
    },
    {
        "name": "Turmeric Powder",
        "name_ta": "மஞ்சள் தூள்",
        "sku": "SKU-TURMERIC-001",
        "category": "Grocery",
        "quantity": 15.0,
        "unit": "kg",
        "purchase_price": 18.0,
        "selling_price": 25.0,
        "minimum_stock_level": 5.0,
        "reorder_level": 10.0,
        "aliases": "turmeric, turmeric powder, manjal, manjal thool, மஞ்சள் தூள், மஞ்சள்",
        "description": "Pure Organic Turmeric Powder"
    },

    # 2. Vegetables
    {
        "name": "Tomato",
        "name_ta": "தக்காளி",
        "sku": "SKU-VEG-TOMATO",
        "category": "Vegetables",
        "quantity": 16.0,
        "unit": "kg",
        "purchase_price": 28.0,
        "selling_price": 40.0,
        "minimum_stock_level": 10.0,
        "reorder_level": 20.0,
        "aliases": "tomato, tomatoes, thakkali, thakali, தக்காளி, நாட்டு தக்காளி",
        "description": "Fresh Country Tomatoes"
    },
    {
        "name": "Onion",
        "name_ta": "வெங்காயம்",
        "sku": "SKU-VEG-ONION",
        "category": "Vegetables",
        "quantity": 25.0,
        "unit": "kg",
        "purchase_price": 24.0,
        "selling_price": 35.0,
        "minimum_stock_level": 10.0,
        "reorder_level": 20.0,
        "aliases": "onion, onions, vengayam, periya vengayam, சின்ன வெங்காயம், வெங்காயம், ulli",
        "description": "Fresh Bellary Onion"
    },
    {
        "name": "Ginger",
        "name_ta": "இஞ்சி",
        "sku": "SKU-VEG-GINGER",
        "category": "Vegetables",
        "quantity": 15.0,
        "unit": "kg",
        "purchase_price": 80.0,
        "selling_price": 100.0,
        "minimum_stock_level": 5.0,
        "reorder_level": 10.0,
        "aliases": "ginger, inji, injii, country ginger, இஞ்சி, பச்சை இஞ்சி",
        "description": "Fresh Country Ginger"
    },
    {
        "name": "Country Garlic",
        "name_ta": "பூண்டு",
        "sku": "SKU-GARLIC-001",
        "category": "Groceries",
        "quantity": 25.0,
        "unit": "kg",
        "purchase_price": 110.0,
        "selling_price": 140.0,
        "minimum_stock_level": 5.0,
        "reorder_level": 10.0,
        "aliases": "garlic, country garlic, poondu, nattu poondu, பூண்டு, நாட்டு பூண்டு",
        "description": "Fresh Country Garlic"
    },
    {
        "name": "Potato",
        "name_ta": "உருளைக்கிழங்கு",
        "sku": "SKU-VEG-POTATO",
        "category": "Vegetables",
        "quantity": 30.0,
        "unit": "kg",
        "purchase_price": 25.0,
        "selling_price": 35.0,
        "minimum_stock_level": 10.0,
        "reorder_level": 20.0,
        "aliases": "potato, potatoes, urulaikilangu, urulai, உருளை, உருளைக்கிழங்கு, ஆலு",
        "description": "Fresh Ooty Potato"
    },
    {
        "name": "Carrot",
        "name_ta": "கேரட்",
        "sku": "SKU-VEG-CARROT",
        "category": "Vegetables",
        "quantity": 20.0,
        "unit": "kg",
        "purchase_price": 30.0,
        "selling_price": 45.0,
        "minimum_stock_level": 5.0,
        "reorder_level": 10.0,
        "aliases": "carrot, carrots, carrat, கேரட்",
        "description": "Fresh Red Ooty Carrots"
    },
    {
        "name": "Green Chilli",
        "name_ta": "பச்சை மிளகாய்",
        "sku": "SKU-VEG-CHILLI",
        "category": "Vegetables",
        "quantity": 10.0,
        "unit": "kg",
        "purchase_price": 40.0,
        "selling_price": 60.0,
        "minimum_stock_level": 3.0,
        "reorder_level": 5.0,
        "aliases": "green chilli, chilli, pachai milagai, milagai, பச்சை மிளகாய், மிளகாய்",
        "description": "Fresh Spicy Green Chillies"
    },

    # 3. Fruits
    {
        "name": "Apple",
        "name_ta": "ஆப்பிள்",
        "sku": "SKU-FRUIT-APPLE",
        "category": "Fruits",
        "quantity": 20.0,
        "unit": "kg",
        "purchase_price": 120.0,
        "selling_price": 160.0,
        "minimum_stock_level": 5.0,
        "reorder_level": 10.0,
        "aliases": "apple, apples, shimla apple, ஆப்பிள்",
        "description": "Crisp Royal Gala Apples"
    },
    {
        "name": "Banana",
        "name_ta": "வாழைப்பழம்",
        "sku": "SKU-FRUIT-BANANA",
        "category": "Fruits",
        "quantity": 30.0,
        "unit": "dozen",
        "purchase_price": 40.0,
        "selling_price": 60.0,
        "minimum_stock_level": 10.0,
        "reorder_level": 15.0,
        "aliases": "banana, bananas, vazhaipazham, vaazhai, வாழைப்பழம், பூவன் பழம்",
        "description": "Fresh Poovan Bananas"
    },

    # 4. Packaged Foods
    {
        "name": "Milk Bread",
        "name_ta": "பிரெட்",
        "sku": "SKU-BREAD-001",
        "category": "Snacks and Food",
        "quantity": 25.0,
        "unit": "packet",
        "purchase_price": 28.0,
        "selling_price": 38.0,
        "minimum_stock_level": 5.0,
        "reorder_level": 10.0,
        "aliases": "bread, milk bread, modern bread, பிரெட், ரொட்டி",
        "description": "Fresh Sweet Milk Bread 400g"
    },
    {
        "name": "Marie Gold Biscuits",
        "name_ta": "பிஸ்கட்",
        "sku": "SKU-BISCUIT-001",
        "category": "Snacks and Food",
        "quantity": 40.0,
        "unit": "packet",
        "purchase_price": 22.0,
        "selling_price": 30.0,
        "minimum_stock_level": 10.0,
        "reorder_level": 20.0,
        "aliases": "biscuit, biscuits, marie, marie gold, பிஸ்கட், மேரி பிஸ்கட்",
        "description": "Crispy Marie Gold Tea Biscuits"
    },
    {
        "name": "Dairy Milk Chocolate",
        "name_ta": "சாக்லேட்",
        "sku": "SKU-CHOC-001",
        "category": "Snacks and Food",
        "quantity": 50.0,
        "unit": "piece",
        "purchase_price": 15.0,
        "selling_price": 20.0,
        "minimum_stock_level": 15.0,
        "reorder_level": 25.0,
        "aliases": "chocolate, chocolates, dairy milk, cadbury, சாக்லேட்",
        "description": "Cadbury Dairy Milk 24g"
    },
    {
        "name": "Potato Chips Snacks",
        "name_ta": "ஸ்நாக்ஸ்",
        "sku": "SKU-CHIPS-001",
        "category": "Snacks and Food",
        "quantity": 35.0,
        "unit": "packet",
        "purchase_price": 10.0,
        "selling_price": 15.0,
        "minimum_stock_level": 10.0,
        "reorder_level": 20.0,
        "aliases": "chips, potato chips, snacks, lays, சிப்ஸ், ஸ்நாக்ஸ்",
        "description": "Crispy Salted Potato Chips"
    },

    # 5. Stationery
    {
        "name": "Classmate Notebook",
        "name_ta": "நோட்டுப் புத்தகம்",
        "sku": "SKU-NOTEBOOK-001",
        "category": "Stationery",
        "quantity": 40.0,
        "unit": "piece",
        "purchase_price": 32.0,
        "selling_price": 45.0,
        "minimum_stock_level": 10.0,
        "reorder_level": 20.0,
        "aliases": "notebook, classmate notebook, note, classmate note, நோட்டு, நோட்டுப் புத்தகம்",
        "description": "Long Ruled Notebook 192 Pages"
    },
    {
        "name": "Reynolds Ball Pen",
        "name_ta": "பேனா",
        "sku": "SKU-PEN-001",
        "category": "Stationery",
        "quantity": 60.0,
        "unit": "piece",
        "purchase_price": 7.0,
        "selling_price": 10.0,
        "minimum_stock_level": 15.0,
        "reorder_level": 30.0,
        "aliases": "pen, reynolds pen, ball pen, paena, பேனா, பால் பாயிண்ட் பேனா",
        "description": "Smooth Flow Blue Ball Pen"
    },
    {
        "name": "Plastic Scale 30cm",
        "name_ta": "ஸ்கேல்",
        "sku": "SKU-SCALE-001",
        "category": "Stationery",
        "quantity": 35.0,
        "unit": "piece",
        "purchase_price": 10.0,
        "selling_price": 15.0,
        "minimum_stock_level": 10.0,
        "reorder_level": 15.0,
        "aliases": "scale, ruler, plastic scale, camlin scale, அளவுகோல், ஸ்கேல்",
        "description": "Clear Transparent 30cm Metric Ruler"
    },
    {
        "name": "Apsara Pencil Box",
        "name_ta": "பென்சில்",
        "sku": "SKU-PENCIL-001",
        "category": "Stationery",
        "quantity": 25.0,
        "unit": "packet",
        "purchase_price": 42.0,
        "selling_price": 55.0,
        "minimum_stock_level": 5.0,
        "reorder_level": 10.0,
        "aliases": "pencil, pencil box, apsara pencil, பென்சில், பென்சில் பாக்ஸ்",
        "description": "Extra Dark HB Pencils Box of 10"
    },
    {
        "name": "Dust-Free Eraser",
        "name_ta": "அழிப்பான்",
        "sku": "SKU-ERASER-001",
        "category": "Stationery",
        "quantity": 50.0,
        "unit": "piece",
        "purchase_price": 3.0,
        "selling_price": 5.0,
        "minimum_stock_level": 15.0,
        "reorder_level": 25.0,
        "aliases": "eraser, rubber, non-dust eraser, அழிப்பான், ரப்பர்",
        "description": "Non-Dust Soft White Rubber Eraser"
    },
    {
        "name": "A4 Copier Paper",
        "name_ta": "பேப்பர்",
        "sku": "SKU-PAPER-001",
        "category": "Stationery",
        "quantity": 20.0,
        "unit": "packet",
        "purchase_price": 190.0,
        "selling_price": 240.0,
        "minimum_stock_level": 5.0,
        "reorder_level": 10.0,
        "aliases": "paper, a4 paper, copier paper, பேப்பர், தாள்",
        "description": "75 GSM Multipurpose Copier Paper Ream"
    },

    # 6. Personal Care
    {
        "name": "Clinic Plus Shampoo",
        "name_ta": "ஷாம்பு",
        "sku": "SKU-SHAMPOO-001",
        "category": "Personal Care",
        "quantity": 10.0,
        "unit": "bottle",
        "purchase_price": 52.0,
        "selling_price": 70.0,
        "minimum_stock_level": 5.0,
        "reorder_level": 10.0,
        "aliases": "shampoo, clinic plus, hair shampoo, ஷாம்பு",
        "description": "Strong & Long Milk Protein Shampoo 175ml"
    },
    {
        "name": "Hair Serum",
        "name_ta": "ஹேர் சீரம்",
        "sku": "SKU-SERUM-001",
        "category": "Personal Care",
        "quantity": 20.0,
        "unit": "bottle",
        "purchase_price": 160.0,
        "selling_price": 210.0,
        "minimum_stock_level": 5.0,
        "reorder_level": 10.0,
        "aliases": "serum, hair serum, livon serum, சீரம், ஹேர் சீரம்",
        "description": "Silky Shine Anti-Frizz Hair Serum 50ml"
    },
    {
        "name": "Hamam Soap",
        "name_ta": "சோப்பு",
        "sku": "SKU-SOAP-001",
        "category": "Personal Care",
        "quantity": 40.0,
        "unit": "piece",
        "purchase_price": 29.0,
        "selling_price": 38.0,
        "minimum_stock_level": 10.0,
        "reorder_level": 20.0,
        "aliases": "soap, hamam, bath soap, சோப்பு, ஹமாம் சோப்பு",
        "description": "Neem & Tulsi Herbal Bath Soap 100g"
    },
    {
        "name": "Colgate Toothpaste",
        "name_ta": "டூத்பேஸ்ட்",
        "sku": "SKU-PASTE-001",
        "category": "Personal Care",
        "quantity": 30.0,
        "unit": "piece",
        "purchase_price": 44.0,
        "selling_price": 58.0,
        "minimum_stock_level": 8.0,
        "reorder_level": 15.0,
        "aliases": "toothpaste, colgate, dental cream, டூத்பேஸ்ட், பற்பசை",
        "description": "Strong Teeth Cavity Protection 100g"
    },
    {
        "name": "Coconut Hair Oil",
        "name_ta": "தலைமுடி எண்ணெய்",
        "sku": "SKU-HAIROIL-001",
        "category": "Personal Care",
        "quantity": 25.0,
        "unit": "bottle",
        "purchase_price": 40.0,
        "selling_price": 52.0,
        "minimum_stock_level": 6.0,
        "reorder_level": 12.0,
        "aliases": "hair oil, coconut hair oil, parachute, தலைமுடி எண்ணெய், தேங்காய் எண்ணெய்",
        "description": "Pure Coconut Hair Oil 100ml"
    },

    # 7. Household
    {
        "name": "AA Battery",
        "name_ta": "பேட்டரி",
        "sku": "SKU-BATTERY-001",
        "category": "Household",
        "quantity": 40.0,
        "unit": "piece",
        "purchase_price": 12.0,
        "selling_price": 18.0,
        "minimum_stock_level": 10.0,
        "reorder_level": 20.0,
        "aliases": "battery, batteries, aa battery, cell, duracell, பேட்டரி",
        "description": "Alkaline AA 1.5V Power Cell"
    },
    {
        "name": "Surf Excel Detergent",
        "name_ta": "டிட்டர்ஜென்ட்",
        "sku": "SKU-DETERGENT-001",
        "category": "Household",
        "quantity": 25.0,
        "unit": "packet",
        "purchase_price": 45.0,
        "selling_price": 60.0,
        "minimum_stock_level": 8.0,
        "reorder_level": 15.0,
        "aliases": "detergent, surf excel, washing powder, சோப்புத்தூள், டிட்டர்ஜென்ட்",
        "description": "Quick Wash Detergent Powder 500g"
    },
    {
        "name": "Vim Dishwash Liquid",
        "name_ta": "டிஷ்வாஷ்",
        "sku": "SKU-DISHWASH-001",
        "category": "Household",
        "quantity": 20.0,
        "unit": "bottle",
        "purchase_price": 35.0,
        "selling_price": 50.0,
        "minimum_stock_level": 5.0,
        "reorder_level": 10.0,
        "aliases": "dishwash, vim, vim gel, பாத்திரம் கழுவும் திரவம், டிஷ்வாஷ்",
        "description": "Lemon Dishwash Gel 250ml"
    },
]


def run_migration():
    """Ensure columns exist and catalog seed is applied."""
    with engine.connect() as conn:
        # Check SQLite or PostgreSQL columns
        dialect = engine.dialect.name
        logger.info("Running schema migration for dialect: %s", dialect)
        try:
            conn.execute(text("ALTER TABLE products ADD COLUMN aliases TEXT"))
            conn.commit()
            logger.info("Added 'aliases' column to products table.")
        except Exception as e:
            logger.info("'aliases' column already exists or skipped: %s", e)

        try:
            conn.execute(text("ALTER TABLE products ADD COLUMN reorder_level FLOAT DEFAULT 15.0"))
            conn.commit()
            logger.info("Added 'reorder_level' column to products table.")
        except Exception as e:
            logger.info("'reorder_level' column already exists or skipped: %s", e)

    # Seed products into database
    db = SessionLocal()
    try:
        seeded_count = 0
        updated_count = 0
        for item in CATALOG_SEED:
            # Match by SKU or exact name
            existing = db.query(Product).filter(
                (Product.sku == item["sku"]) | (Product.name.ilike(item["name"]))
            ).first()

            if existing:
                # Update aliases, reorder level, and descriptions if not set
                existing.aliases = item["aliases"]
                existing.reorder_level = item["reorder_level"]
                if not existing.name_ta:
                    existing.name_ta = item["name_ta"]
                if not existing.description:
                    existing.description = item["description"]
                updated_count += 1
            else:
                new_prod = Product(
                    name=item["name"],
                    name_ta=item["name_ta"],
                    sku=item["sku"],
                    category=item["category"],
                    quantity=item["quantity"],
                    unit=item["unit"],
                    purchase_price=item["purchase_price"],
                    selling_price=item["selling_price"],
                    minimum_stock_level=item["minimum_stock_level"],
                    reorder_level=item["reorder_level"],
                    aliases=item["aliases"],
                    description=item["description"],
                    is_active=True
                )
                db.add(new_prod)
                seeded_count += 1

        db.commit()
        logger.info("Catalog migration complete! Seeded: %d, Updated: %d", seeded_count, updated_count)
    finally:
        db.close()


if __name__ == "__main__":
    run_migration()
