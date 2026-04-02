# default_cats.py

CATEGORY_TREE = {
    "Drinks (Alcoholic)": {
        "desc": "Alcoholic beverages",
        "icon": "bi-cup-straw",
        "children": [
            ("Beers", "Local and imported beers"),
            ("Ciders", "Fruit-based alcoholic drinks"),
            ("Wines", "Red, white, rosé, sparkling wines"),
            ("Spirits", "Whisky, vodka, gin, rum, tequila"),
            ("Cocktails", "Mixed alcoholic drinks"),
            ("Shots", "Small servings of spirits"),
            ("Liqueurs", "Sweet flavored alcoholic drinks"),
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
            ("Hot Beverages", "Tea, coffee, hot chocolate"),
            ("Mocktails", "Non-alcoholic mixed drinks"),
        ],
    },
    "Food": {
        "desc": "Meals and dishes",
        "icon": "bi-egg-fried",
        "children": [
            ("Starters", "Light appetizers"),
            ("Main Courses", "Full meals"),
            ("Local Dishes", "Traditional Kenyan meals"),
            ("Fast Food", "Quick meals"),
            ("Grills / BBQ", "Grilled meats"),
            ("Seafood", "Fish and seafood"),
            ("Vegetarian", "Plant-based meals"),
        ],
    },
    "Sides & Extras": {
        "desc": "Accompaniments",
        "icon": "bi-plus-square",
        "children": [
            ("Side Dishes", "Fries, rice, ugali, salads"),
            ("Sauces", "Dips and add-ons"),
        ],
    },
    "Desserts": {
        "desc": "Sweet dishes",
        "icon": "bi-cake",
        "children": [
            ("Desserts", "Cakes, ice cream, pastries"),
        ],
    },
    "Other": {
        "desc": "Other sellable items",
        "icon": "bi-box",
        "children": [
            ("Tobacco", "Cigarettes, cigars"),
            ("Shisha", "Hookah products"),
        ],
    },
    "Services": {
        "desc": "Service-related charges",
        "icon": "bi-receipt",
        "children": [
            ("Service Charge", "Service fees"),
            ("Cover Charge", "Entry fees"),
        ],
    },
}
