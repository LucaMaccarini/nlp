import json

file_path = "nlp/recipes_10k.json"

with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

mapping = {
    "RecipeId": "recipe_id",
    "Name": "title",
    "RecipeCategory": "type",
    "RecipeIngredientParts": "ingredients",
    "RecipeInstructions": "instructions"
}

for recipe in data:
    for old_key, new_key in mapping.items():
        if old_key in recipe:
            recipe[new_key] = recipe.pop(old_key)

with open(file_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)