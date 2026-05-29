import json
import os

import google.generativeai as genai
from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter(tags=["demo"])


@router.post("/api/upload/invoice")
async def upload_invoice(file: UploadFile = File(...)):
    """Gemini demo parser for Suppliers page — not persisted to the database."""
    file_bytes = await file.read()
    try:
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = """
        You are an AI simulating an invoice parser for a restaurant MVP.
        Extract the line items from this invoice/receipt image and their current prices (which is the newPrice).
        Since this is an MVP demo, invent a plausible `oldPrice` (slightly lower) for each item and calculate the `pctChange`.
        Categorize `severity` as "warning" if pctChange < 8 else "destructive".
        Output strictly valid JSON matching this exact schema:
        [
          {
            "item": "string",
            "unit": "string",
            "oldPrice": 0.0,
            "newPrice": 0.0,
            "pctChange": 0.0,
            "severity": "warning" | "destructive",
            "affectedDishes": [
              {
                "name": "string",
                "currentCost": 0.0,
                "newCost": 0.0,
                "currentMargin": 0.0,
                "newMargin": 0.0,
                "currentMenuPrice": 0.0
              }
            ]
          }
        ]
        """
        response = model.generate_content(
            [
                prompt,
                {"mime_type": file.content_type or "image/jpeg", "data": file_bytes},
            ],
            generation_config={"response_mime_type": "application/json"},
        )
        return json.loads(response.text)
    except Exception as exc:
        print(f"Gemini API error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to parse invoice with AI") from exc
