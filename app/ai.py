import json
import os
from typing import Optional

try:
    from google import genai
except Exception:
    genai = None


def _fallback(planner: str, data: dict):
    budget = float(data.get("budget", 0) or 0)

    if planner == "home":
        items = [
            ("LED Lighting", "Lighting", budget * 0.12),
            ("Ceiling Fan", "Appliance", budget * 0.15),
            ("Storage Unit", "Furniture", budget * 0.28),
            ("Curtains & Decor", "Decor", budget * 0.15),
            ("Table / Seating", "Furniture", budget * 0.30),
        ]

    elif planner == "party":
        items = [
            ("Catering", "Food", budget * 0.45),
            ("Decoration", "Decor", budget * 0.20),
            ("Venue", "Venue", budget * 0.20),
            ("Entertainment", "Entertainment", budget * 0.10),
            ("Contingency", "Other", budget * 0.05),
        ]

    else:
        items = [
            ("Earrings", "Jewelry", budget * 0.25),
            ("Necklace", "Jewelry", budget * 0.45),
            ("Bracelet", "Jewelry", budget * 0.20),
            ("Hair accessory", "Accessory", budget * 0.10),
        ]

    return {
        "planner": planner,
        "budget": budget,
        "source": "Demo fallback recommendation engine",
        "items": [
            {
                "name": name,
                "category": category,
                "estimated_price": round(price, 2),
                "platform": ["Amazon", "Flipkart", "IKEA"][i % 3],
                "reason": "Budget-aware example recommendation"
            }
            for i, (name, category, price) in enumerate(items)
        ],
        "note": ""
    }


def generate_recommendation(
    planner: str,
    data: dict,
    image_path: Optional[str] = None
):
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    print("=== GEMINI CONFIG ===")
    print("Running on Render:", os.getenv("RENDER"))
    print("API key exists:", bool(api_key))
    print("Model:", model)
    print("=====================")

    if not api_key:
        print("GEMINI_API_KEY is not configured.")
        return _fallback(planner, data)

    if genai is None:
        print("google-genai package is not available.")
        return _fallback(planner, data)

    prompt = f"""
You are PocketSmart AI, a smart budget recommendation assistant.

Planner type:
{planner}

User requirements:
{json.dumps(data, indent=2)}

Create practical recommendations based on the user's budget
and requirements.

Return ONLY valid JSON.

The JSON MUST follow exactly this structure:

{{
    "planner": "{planner}",
    "budget": {data.get("budget", 0)},
    "source": "Gemini AI",
    "items": [
        {{
            "name": "Item name",
            "category": "Category",
            "estimated_price": 10000,
            "platform": "Platform or Store",
            "reason": "Why this item is recommended"
        }}
    ],
    "note": "Short useful recommendation note"
}}

Rules:

1. The total estimated_price of all items must not exceed the budget.
2. estimated_price must be a number.
3. Give realistic estimated prices, not guaranteed live prices.
4. Consider the user's requirements carefully.
5. Provide 4 to 8 useful recommendations.
6. Do not include markdown.
7. Do not include code fences.
8. Return JSON only.
"""

    try:
        client = genai.Client(api_key=api_key)

        contents = [prompt]

        if image_path and os.path.exists(image_path):
            from PIL import Image

            image = Image.open(image_path)
            contents.append(image)

        print(f"Calling Gemini model: {model}")

        response = client.models.generate_content(
            model=model,
            contents=contents
        )

        print("Gemini response received.")

        text = response.text.strip()

        if text.startswith("```"):
            text = text.replace("```json", "")
            text = text.replace("```", "")
            text = text.strip()

        result = json.loads(text)

        print("Gemini JSON parsed successfully.")

        return result

    except Exception as e:
        print("Gemini API error:")
        print(type(e).__name__, str(e))

        return _fallback(planner, data)