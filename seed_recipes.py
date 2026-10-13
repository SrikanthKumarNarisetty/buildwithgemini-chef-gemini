# Copyright 2026 Google LLC
"""Seed script for ChefGemini recipes in Firestore."""

from google.cloud import firestore

FIRESTORE_PROJECT = "qwiklabs-gcp-04-610bbf0144b0"

SAMPLE_RECIPES = [
    {
        "id": "lemon-herb-grilled-chicken",
        "title": "Lemon Herb Grilled Chicken",
        "cuisine": "Mediterranean",
        "difficulty": "Easy",
        "prep_time_minutes": 15,
        "cook_time_minutes": 20,
        "servings": 4,
        "calories_per_serving": 320,
        "macros": {"protein_g": 38, "carbs_g": 3, "fat_g": 16},
        "dietary_tags": ["high-protein", "gluten-free", "low-carb"],
        "ingredients": [
            "chicken breast",
            "olive oil",
            "lemon juice",
            "garlic",
            "oregano",
            "salt",
            "black pepper"
        ],
        "instructions": [
            "Whisk olive oil, lemon juice, minced garlic, oregano, salt, and pepper in a bowl.",
            "Marinate chicken breasts for at least 15 minutes.",
            "Preheat grill or grill pan to medium-high heat.",
            "Grill chicken 6-8 minutes per side until internal temperature reaches 165°F (74°C).",
            "Rest for 5 minutes before serving with fresh lemon wedges."
        ]
    },
    {
        "id": "creamy-tuscan-white-bean-skillet",
        "title": "Creamy Tuscan White Bean Skillet",
        "cuisine": "Italian",
        "difficulty": "Easy",
        "prep_time_minutes": 10,
        "cook_time_minutes": 15,
        "servings": 3,
        "calories_per_serving": 290,
        "macros": {"protein_g": 14, "carbs_g": 36, "fat_g": 11},
        "dietary_tags": ["vegetarian", "gluten-free"],
        "ingredients": [
            "cannellini beans",
            "spinach",
            "sun-dried tomatoes",
            "garlic",
            "heavy cream or coconut cream",
            "vegetable broth",
            "parmesan cheese",
            "olive oil"
        ],
        "instructions": [
            "Sauté minced garlic and chopped sun-dried tomatoes in olive oil for 2 minutes.",
            "Add rinsed cannellini beans and vegetable broth, bring to a gentle simmer for 5 minutes.",
            "Stir in cream and fresh spinach until spinach is wilted.",
            "Garnish with grated parmesan cheese and crushed red pepper flakes."
        ]
    },
    {
        "id": "quinoa-roasted-veggie-power-bowl",
        "title": "Quinoa & Roasted Veggie Power Bowl",
        "cuisine": "Modern Healthy",
        "difficulty": "Easy",
        "prep_time_minutes": 15,
        "cook_time_minutes": 25,
        "servings": 2,
        "calories_per_serving": 380,
        "macros": {"protein_g": 12, "carbs_g": 54, "fat_g": 14},
        "dietary_tags": ["vegan", "gluten-free", "dairy-free"],
        "ingredients": [
            "quinoa",
            "sweet potato",
            "broccoli florets",
            "chickpeas",
            "tahini",
            "lemon juice",
            "olive oil",
            "cumin"
        ],
        "instructions": [
            "Toss cubed sweet potato, broccoli, and drained chickpeas in olive oil, cumin, and salt.",
            "Roast on a baking sheet at 400°F (200°C) for 25 minutes until tender and caramelized.",
            "Cook quinoa according to package directions.",
            "Whisk tahini, lemon juice, warm water, and salt to make dressing.",
            "Assemble bowls with quinoa, roasted vegetables, and drizzle with tahini dressing."
        ]
    },
    {
        "id": "spicy-avocado-salmon-poke-bowl",
        "title": "Spicy Avocado Salmon Bowl",
        "cuisine": "Hawaiian / Fusion",
        "difficulty": "Medium",
        "prep_time_minutes": 20,
        "cook_time_minutes": 0,
        "servings": 2,
        "calories_per_serving": 460,
        "macros": {"protein_g": 34, "carbs_g": 38, "fat_g": 20},
        "dietary_tags": ["pescatarian", "dairy-free"],
        "ingredients": [
            "sushi-grade salmon",
            "avocado",
            "cucumber",
            "brown rice or sushi rice",
            "soy sauce or tamari",
            "sesame oil",
            "sriracha",
            "sesame seeds"
        ],
        "instructions": [
            "Cube salmon and toss with soy sauce, sesame oil, and sriracha.",
            "Slice cucumber and avocado.",
            "Layer cooked brown rice in bowls and arrange dressed salmon, avocado, and cucumber on top.",
            "Garnish with sesame seeds and green onions."
        ]
    }
]


def seed_recipes():
    print(f"Connecting to Firestore using project ID: {FIRESTORE_PROJECT}")
    db = firestore.Client(project=FIRESTORE_PROJECT)
    collection_ref = db.collection("recipes")

    for recipe in SAMPLE_RECIPES:
        doc_id = recipe["id"]
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(recipe)
        print(f"✓ Seeded recipe: '{recipe['title']}' ({doc_id})")

    print("\nAll sample recipes successfully seeded into Firestore collection 'recipes'!")


if __name__ == "__main__":
    seed_recipes()
