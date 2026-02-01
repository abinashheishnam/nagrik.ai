
import requests
import random
import string
import wave
import io
import struct

BASE_URL = "http://127.0.0.1:8000"

def random_str(n=10):
    return ''.join(random.choices(string.ascii_letters, k=n))

def generate_silent_wav():
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        # 1 sec of silence
        data = struct.pack('<h', 0) * 16000
        wav_file.writeframes(data)
    buffer.seek(0)
    return buffer.getvalue()

def run():
    # 1. Signup
    phone = "".join(random.choices(string.digits, k=10))
    email = f"{random_str()}@example.com"
    password = "password123"
    
    print(f"Registering user: {phone} / {email}")
    try:
        r = requests.post(f"{BASE_URL}/auth/user/signup", json={
            "full_name": "Audio Test User",
            "phone": phone,
            "email": email,
            "password": password
        })
        if r.status_code != 200:
            print("Signup failed:", r.text)
            return
        
        token = r.json()["access_token"]
        print("Got token:", token[:10] + "...")
        
        # 2. Upload Audio
        print("Uploading dummy silent audio...")
        wav_data = generate_silent_wav()
        
        files = {
            'file': ('test_audio.webm', wav_data, 'audio/webm;codecs=opus')
        }
        headers = {"Authorization": f"Bearer {token}"}
        
        r = requests.post(f"{BASE_URL}/api/v1/audio/transcribe", files=files, headers=headers)
        
        print(f"Status Code: {r.status_code}")
        print("Response:", r.text)
        
        if r.status_code == 200:
            print("Success! Transcript:", r.json())
        elif r.status_code == 422:
            print("Expected failure for silent audio (Validation Error or No Transcript). Backend is working.")
        else:
            print("Unexpected failure.")

    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    run()
