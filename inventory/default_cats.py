# default_cats.py

CATEGORY_TREE_BY_BUSINESS = {

    # ------------------ BAR ------------------
    "bar": {
        "Drinks (Alcoholic)": {
            "desc": "Alcoholic beverages",
            "icon": "bi-cup-straw",
            "children": [
                ("Beers", "Local and imported beers"),
                ("Ciders", "Fruit-based alcoholic drinks"),
                ("Wines", "Red, white, rosé, sparkling wines"),
                ("Spirits", "Whisky, vodka, gin, rum, tequila"),
                ("Liqueurs", "Sweet flavored alcoholic drinks"),
                ("Cocktails", "Mixed alcoholic drinks"),
                ("Shots", "Small servings of spirits"),
            ],
        },
        "Drinks (Non-Alcoholic)": {
            "desc": "Non-alcoholic beverages",
            "icon": "bi-droplet",
            "children": [
                ("Soft Drinks", "Carbonated beverages"),
                ("Juices", "Fresh or packaged juices"),
                ("Water", "Still or sparkling water"),
                ("Energy Drinks", "Caffeinated beverages"),
            ],
        },
        "Other": {
            "desc": "Other sale items",
            "icon": "bi-box",
            "children": [
                ("Tobacco", "Cigarettes and cigars"),
                ("Shisha", "Hookah products"),
            ],
        },
        "Services": {
            "desc": "Charges",
            "icon": "bi-receipt",
            "children": [
                ("Cover Charge", "Entry fees"),
                ("Table Charges", "Reserved seating fees"),
            ],
        },
    },

    # ------------------ RESTAURANT ------------------
    "restaurant": {
        "Food": {
            "desc": "Meals and dishes",
            "icon": "bi-egg-fried",
            "children": [
                ("Starters", "Light appetizers"),
                ("Main Courses", "Full meals"),
                ("Local Dishes", "Traditional meals"),
                ("Rice Dishes", "Pilau, biryani style meals"),
                ("Grills / BBQ", "Grilled meats"),
                ("Seafood", "Fish and seafood"),
                ("Vegetarian", "Plant-based meals"),
                ("Fast Food", "Quick meals"),
            ],
        },
        "Drinks": {
            "desc": "Beverages",
            "icon": "bi-cup",
            "children": [
                ("Soft Drinks", "Carbonated beverages"),
                ("Fresh Juices", "Freshly prepared juices"),
                ("Hot Beverages", "Tea, coffee, chocolate"),
                ("Water", "Drinking water"),
            ],
        },
        "Desserts": {
            "desc": "Sweet foods",
            "icon": "bi-cake",
            "children": [
                ("Cakes & Pastries", "Baked desserts"),
                ("Ice Cream", "Frozen desserts"),
                ("Traditional Desserts", "Local sweet dishes"),
            ],
        },
        "Services": {
            "desc": "Service-related charges",
            "icon": "bi-receipt",
            "children": [
                ("Service Charge", "Service fees"),
                ("Delivery Fees", "Food delivery charges"),
            ],
        },
    },

    # ------------------ SUPERMARKET / GROCERY ------------------
    "supermarket": {
        "Food Staples": {
            "desc": "Basic food items",
            "icon": "bi-basket",
            "children": [
                ("Grains & Flour", "Maize flour, wheat flour, rice"),
                ("Sugar & Salt", "Sweeteners and salt"),
                ("Cooking Oils", "Edible oils and fats"),
                ("Canned Foods", "Processed and preserved foods"),
            ],
        },
        "Beverages": {
            "desc": "All drinks",
            "icon": "bi-cup",
            "children": [
                ("Soft Drinks", "Carbonated beverages"),
                ("Juices", "Packaged juices"),
                ("Water", "Bottled water"),
                ("Dairy Drinks", "Milk and milk products"),
            ],
        },
        "Household Items": {
            "desc": "Home use products",
            "icon": "bi-house",
            "children": [
                ("Cleaning Supplies", "Detergents and disinfectants"),
                ("Paper Products", "Tissue, paper towels"),
                ("Kitchen Supplies", "Utensils and consumables"),
            ],
        },
        "Personal Care": {
            "desc": "Body care products",
            "icon": "bi-heart",
            "children": [
                ("Toiletries", "Soap, toothpaste"),
                ("Hair Care", "Shampoo, conditioners"),
                ("Baby Products", "Infant care items"),
            ],
        },
    },

    # ------------------ PHARMACY ------------------
    "pharmacy": {
        "Medication": {
            "desc": "Medicinal products",
            "icon": "bi-capsule",
            "children": [
                ("Over-the-Counter Drugs", "Non-prescription medicine"),
                ("Prescription Drugs", "Doctor-prescribed medicine"),
                ("Supplements", "Vitamins and minerals"),
            ],
        },
        "Health Products": {
            "desc": "Health-related items",
            "icon": "bi-heart",
            "children": [
                ("First Aid", "Bandages and antiseptics"),
                ("Medical Devices", "Thermometers, BP machines"),
                ("Personal Protective Equipment", "Masks, gloves"),
            ],
        },
        "Personal Care": {
            "desc": "Hygiene items",
            "icon": "bi-droplet",
            "children": [
                ("Oral Care", "Toothpaste, toothbrushes"),
                ("Skin Care", "Lotions and creams"),
                ("Feminine Care", "Sanitary products"),
            ],
        },
    },

    # ------------------ ELECTRONICS ------------------
    "electronics": {
        "Devices": {
            "desc": "Electronic devices",
            "icon": "bi-phone",
            "children": [
                ("Mobile Phones", "Smart and feature phones"),
                ("Computers", "Laptops and desktops"),
                ("TV & Audio", "Televisions and sound systems"),
            ],
        },
        "Accessories": {
            "desc": "Device accessories",
            "icon": "bi-headphones",
            "children": [
                ("Chargers & Cables", "Power accessories"),
                ("Audio Accessories", "Headphones and speakers"),
                ("Storage Devices", "Flash disks and memory cards"),
            ],
        },
        "Services": {
            "desc": "Technical services",
            "icon": "bi-tools",
            "children": [
                ("Repairs", "Device repair services"),
                ("Software Services", "Installation and updates"),
            ],
        },
    },

    # ------------------ SALON / BARBERSHOP ------------------
    "salon": {
        "Hair Services": {
            "desc": "Hair-related services",
            "icon": "bi-scissors",
            "children": [
                ("Haircuts", "Cutting services"),
                ("Hair Styling", "Braiding and styling"),
                ("Hair Treatment", "Conditioning and care"),
            ],
        },
        "Beauty Services": {
            "desc": "Beauty treatments",
            "icon": "bi-brush",
            "children": [
                ("Makeup", "Application services"),
                ("Nail Services", "Manicure and pedicure"),
                ("Skin Care", "Facials and treatments"),
            ],
        },
        "Products": {
            "desc": "Beauty products",
            "icon": "bi-bag",
            "children": [
                ("Hair Products", "Oils and treatments"),
                ("Cosmetics", "Makeup products"),
            ],
        },
    },

    # ------------------ HARDWARE ------------------
    "hardware": {
        "Building Materials": {
            "desc": "Construction materials",
            "icon": "bi-hammer",
            "children": [
                ("Cement & Aggregates", "Cement, sand, ballast"),
                ("Steel & Metals", "Reinforcement materials"),
                ("Wood & Timber", "Construction wood"),
            ],
        },
        "Tools": {
            "desc": "Construction tools",
            "icon": "bi-tools",
            "children": [
                ("Hand Tools", "Manual tools"),
                ("Power Tools", "Electric tools"),
            ],
        },
        "Finishing Materials": {
            "desc": "Finishing products",
            "icon": "bi-paint-bucket",
            "children": [
                ("Paints", "Wall and surface paints"),
                ("Tiles", "Floor and wall tiles"),
            ],
        },
    },

    # ------------------ AGROVET ------------------
    "agrovet": {
        "Farm Inputs": {
            "desc": "Crop production supplies",
            "icon": "bi-flower1",
            "children": [
                ("Fertilizers", "Soil nutrients"),
                ("Seeds", "Crop seeds"),
                ("Pesticides", "Crop protection chemicals"),
            ],
        },
        "Animal Products": {
            "desc": "Livestock supplies",
            "icon": "bi-egg",
            "children": [
                ("Animal Feeds", "Livestock feeds"),
                ("Veterinary Drugs", "Animal medicine"),
            ],
        },
    },

    # ------------------ CAR WASH ------------------
    "car_wash": {
        "Services": {
            "desc": "Cleaning services",
            "icon": "bi-droplet",
            "children": [
                ("Exterior Wash", "Body cleaning"),
                ("Interior Cleaning", "Inside cleaning"),
                ("Detailing", "Advanced cleaning"),
            ],
        },
        "Add-ons": {
            "desc": "Extra services",
            "icon": "bi-plus-square",
            "children": [
                ("Waxing", "Protective coating"),
                ("Engine Cleaning", "Engine wash"),
            ],
        },
    },

    # ------------------ WINES & SPIRITS ------------------
    "wines_and_spirits": {
        "Spirits": {
            "desc": "Distilled alcoholic beverages",
            "icon": "bi-cup",
            "children": [
                ("Spirits", "Whisky, vodka, gin, rum, local spirits"),
                ("Liqueurs", "Sweet flavored alcoholic drinks"),
            ],
        },
        "Wines": {
            "desc": "Fermented grape beverages",
            "icon": "bi-droplet-half",
            "children": [
                ("Wines", "Red, white, rosé, sparkling wines"),
            ],
        },
        "Beers & Ciders": {
            "desc": "Fermented grain and fruit beverages",
            "icon": "bi-cup-straw",
            "children": [
                ("Beers", "Local and imported beers"),
                ("Ciders", "Fruit-based alcoholic drinks"),
            ],
        },
        "Non-Alcoholic": {
            "desc": "Soft drinks and mixers",
            "icon": "bi-droplet",
            "children": [
                ("Soft Drinks", "Carbonated beverages"),
                ("Juices", "Packaged juices"),
                ("Water", "Bottled water"),
                ("Energy Drinks", "Caffeinated beverages"),
            ],
        },
        "Tobacco": {
            "desc": "Tobacco products",
            "icon": "bi-slash-circle",
            "children": [
                ("Tobacco", "Cigarettes and cigars"),
            ],
        },
    },

    # ------------------ DEFAULT ------------------
    "default": {
        "General": {
            "desc": "General items",
            "icon": "bi-box",
            "children": [
                ("Products", "General goods"),
                ("Services", "General services"),
            ],
        },
    },
}
