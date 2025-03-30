import requests
import json
import os
import sounddevice as sd
import soundfile as sf
from deepgram import DeepgramClient
from deepgram import PrerecordedOptions
import asyncio
import base64
import dotenv

dotenv.load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
GCP_API_KEY = os.getenv("GCP_API_KEY")
PROMPT = os.getenv("PROMPT")

deepgram = DeepgramClient(DEEPGRAM_API_KEY)

def record_audio(duration=5, sample_rate=16000):
    print("Recording... Speak now.")
    audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
    sd.wait()
    print("Recording finished.")
    return audio, sample_rate

def save_audio(audio, sample_rate, filename="input.wav"):
    sf.write(filename, audio, sample_rate)
    return filename

async def speech_to_text(audio_file):
    print("Converting speech to text...")
    
    try:
        with open(audio_file, "rb") as file:
            buffer_data = file.read()
        
        payload = {"buffer": buffer_data}
        options = PrerecordedOptions(
            smart_format=True,
            language="id",  
            model="nova-2", 
        )
        
        response = deepgram.listen.rest.v("1").transcribe_file(payload, options)
        
        json_str = response.to_json()
        print(f"Full Deepgram response: {json_str}")
        
        json_response = json.loads(json_str)
        
        if "results" in json_response and "channels" in json_response["results"]:
            text = json_response["results"]["channels"][0]["alternatives"][0]["transcript"]
            print(f"Transcription: {text}")
            
            if not text.strip():
                print("Empty transcript detected")
                return ""
                
            return text
        else:
            print("No transcription found in response")
            return ""
            
    except Exception as e:
        print(f"Error in speech-to-text: {e}")
        return ""

def get_ai_response(user_message):
    print("Getting AI response...")
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        },
        data=json.dumps({
            "model": "gpt-4o",
            "temperature": 0.7,
            "max_tokens": 150,
            "messages": [
                {
                    "role": "system",
                    "content": PROMPT
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        })
    )
    
    result = response.json()
    if "choices" in result and len(result["choices"]) > 0:
        ai_message = result["choices"][0]["message"]["content"]
        print(f"AI response: {ai_message}")
        return ai_message
    else:
        print("Error in AI response:", result)
        return "Maaf, saya tidak dapat merespons saat ini."

def text_to_speech(text, output_file="output.mp3"):
    print("Converting text to speech with Google Cloud...")
    
    try:
        url = "https://texttospeech.googleapis.com/v1/text:synthesize"
        api_key = GCP_API_KEY
        request_body = {
            "input": {"text": text},
            "voice": {
                "languageCode": "id-ID",  
                "name": "id-ID-Wavenet-A",  
                "ssmlGender": "FEMALE"
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": 1.0,
                "pitch": 0.0,
                "effectsProfileId": ["small-bluetooth-speaker-class-device"]
            }
        }
        
        # Make the API request
        response = requests.post(
            f"{url}?key={api_key}",
            json=request_body
        )
        
        if response.status_code == 200:
            audio_content = response.json().get("audioContent")
            
            if audio_content:
                audio_data = base64.b64decode(audio_content)
                with open(output_file, "wb") as f:
                    f.write(audio_data)
                print(f"Audio saved to {output_file}")
                return output_file
            else:
                print("No audio content in response")
        else:
            print(f"Error from Google Cloud TTS API: {response.status_code}")
            print(response.text)
        
        return None
    except Exception as e:
        print(f"Error in text-to-speech: {e}")
        return None

def play_audio(file_path):
    data, samplerate = sf.read(file_path)
    sd.play(data, samplerate)
    sd.wait()

async def main_async():
    try:
        # Step 1: Record user's speech
        audio, sample_rate = record_audio(duration=5)
        audio_file = save_audio(audio, sample_rate)
        
        # Step 2: Convert speech to text
        user_message = await speech_to_text(audio_file)
        if not user_message:
            print("No speech detected or transcription failed.")
            return
        
        # Step 3: Get AI response
        ai_response = get_ai_response(user_message)
        
        # Step 4: Convert AI response to speech
        output_file = text_to_speech(ai_response)
        
        # Step 5: Play the response
        if output_file:
            print("Playing response...")
            play_audio(output_file)
    
    except Exception as e:
        print(f"An error occurred: {e}")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()