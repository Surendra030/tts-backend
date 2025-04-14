from flask import Flask, request, jsonify
from flask_cors import CORS
import edge_tts
import asyncio
import io
import base64
import re

app = Flask(__name__)
CORS(app)

# Async TTS function
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

# ✅ Root route (for Vercel test or health check)
@app.route("/",methods=["GET"])
async def root():
    return {"message": "🎉 FastAPI TTS server is running on Vercel!"}



@app.route("/tts", methods=["POST"])
def tts():
    try:
        data_list = request.get_json()
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

            # Clean the text
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

        # Run all TTS tasks concurrently
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_results = loop.run_until_complete(asyncio.gather(*tasks))

        # Build response
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
        return jsonify(response_data)

    except Exception as e:
        print(f"🔥 Error: {e}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
