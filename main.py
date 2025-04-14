from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import edge_tts
import io
import base64
import re
import asyncio

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Async TTS generation
async def generate_tts_async(clean_text: str):
    communicate = edge_tts.Communicate(clean_text, "en-US-AriaNeural")
    stream = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            stream.write(chunk["data"])
    stream.seek(0)
    audio_bytes = stream.read()
    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
    return audio_base64

# POST /tts endpoint
@app.post("/")
async def tts(request: Request):
    try:
        data_list = await request.json()
        print(f"\n{'='*60}")
        print(f"📥 Received {len(data_list)} items for TTS processing.")

        clean_items = []
        tasks = []

        for item in data_list:
            text_id = item.get('id')
            raw_text = item.get('text', '').strip()
            x = item.get('x')
            y = item.get('y')
            width = item.get('width')
            height = item.get('height')

            # Clean text
            clean_text = re.sub(r"[^\w\s.,?!'-]", '', raw_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            clean_text = clean_text.replace(".", " ")
            if not clean_text:
                print(f"❌ Skipping ID {text_id}: Empty/Invalid after cleaning.")
                continue

            clean_items.append({
                "id": text_id,
                "x": x,
                "y": y,
                "width": width,
                "height": height
            })
            tasks.append(generate_tts_async(clean_text))

        audio_results = await asyncio.gather(*tasks)

        response_data = []
        for i in range(len(audio_results)):
            response_data.append({
                "id": clean_items[i]["id"],
                "audio_base64": audio_results[i],
                "x": clean_items[i]["x"],
                "y": clean_items[i]["y"],
                "width": clean_items[i]["width"],
                "height": clean_items[i]["height"]
            })

        print(f"📤 Sending TTS response with {len(response_data)} audio items.")
        print(f"{'='*60}\n")
        return JSONResponse(content=response_data)

    except Exception as e:
        print(f"🔥 Error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Server error: {str(e)}"}
        )

# 👇 Vercel looks for this object as the entry point
# Export `app` object as `handler` for Vercel
handler = app
