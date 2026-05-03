# ==============================================================================
# BOOK2VISION VOICE CLONING SERVER (Colab Notebook)
# ==============================================================================
# INSTRUCTIONS:
# 1. Open Google Colab (https://colab.research.google.com/)
# 2. Create a new notebook
# 3. Change Runtime -> T4 GPU
# 4. Paste these cells into the notebook and run them in order
# 5. Copy the final ngrok URL and paste it into the Book2Vision web interface
# ==============================================================================

# --- CELL 1: Installation ---
# RUN THIS CELL FIRST. It takes about 2-3 minutes.
!pip install -q f5-tts
!pip install -q flask flask-cors pyngrok

# --- CELL 2: Setup Server & Model ---
from f5_tts.api import F5TTS
import torch
import base64
import os
import uuid
import warnings
from flask import Flask, request, send_file
from flask_cors import CORS
from pyngrok import ngrok

warnings.filterwarnings('ignore')

# 1. Load the model on GPU
print("Loading F5-TTS model... (This may take a minute)")
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")
f5 = F5TTS()  # This downloads and initializes the default F5 model
print("Model loaded successfully!")

# 2. Setup Flask App
app = Flask(__name__)
CORS(app)

# Ensure temp directory exists
os.makedirs('/tmp/book2vision_audio', exist_ok=True)

@app.route('/clone', methods=['POST'])
def clone_voice():
    try:
        data = request.json
        text = data.get('text')
        speaker_wav_base64 = data.get('speaker_wav_base64')
        language = data.get('language', 'en')  # F5 is primarily English/Chinese, but we accept param
        
        if not text or not speaker_wav_base64:
            return {"error": "Missing 'text' or 'speaker_wav_base64'"}, 400
            
        print(f"Received request: {len(text)} characters")
        
        # Save the reference audio
        ref_id = str(uuid.uuid4())
        ref_path = f"/tmp/book2vision_audio/ref_{ref_id}.wav"
        
        with open(ref_path, "wb") as fh:
            fh.write(base64.b64decode(speaker_wav_base64))
            
        # Generate cloned audio
        out_path = f"/tmp/book2vision_audio/out_{ref_id}.wav"
        
        print("Starting F5-TTS generation...")
        
        # F5-TTS Inference
        # It takes the reference audio, reference text (optional/empty means auto-transcribe), and target text
        wav, sr, _ = f5.infer(
            ref_file=ref_path,
            ref_text="",  # Let F5 automatically transcribe the reference audio
            gen_text=text,
        )
        
        # Save output using soundfile
        import soundfile as sf
        sf.write(out_path, wav, sr)
        
        print(f"Generation complete! Saved to {out_path}")
        
        # Clean up reference file
        os.remove(ref_path)
        
        # Return the generated audio file
        return send_file(out_path, mimetype="audio/wav")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}, 500

@app.route('/health', methods=['GET'])
def health():
    return {"status": "cloning_server_active", "model": "f5-tts", "device": device}

# --- CELL 3: Start Server & Tunnel ---
# Get your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken
# If you don't have one, the tunnel will time out after 2 hours
import getpass
print("Optional: Enter your ngrok authtoken (press Enter to skip):")
authtoken = getpass.getpass()

if authtoken.strip():
    ngrok.set_auth_token(authtoken.strip())

# Start ngrok tunnel
public_url = ngrok.connect(5000).public_url
print("\n" + "="*60)
print(f"🚀 YOUR BOOK2VISION VOICE CLONING URL:")
print(f"👉 {public_url} 👈")
print("Copy this URL and paste it into the Book2Vision 'Colab URL' field.")
print("="*60 + "\n")

# Run Flask app (this cell will run continuously)
app.run(port=5000, host="0.0.0.0")
