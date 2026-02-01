
import requests
import random
import string

BASE_URL = "http://127.0.0.1:8000"

def random_str(n=10):
    return ''.join(random.choices(string.ascii_letters, k=n))

def run():
    # 1. Signup
    phone = "".join(random.choices(string.digits, k=10))
    email = f"{random_str()}@example.com"
    password = "password123"
    
    print(f"Registering user: {phone} / {email}")
    try:
        r = requests.post(f"{BASE_URL}/auth/user/signup", json={
            "full_name": "Test User",
            "phone": phone,
            "email": email,
            "password": password
        })
        if r.status_code != 200:
            print("Signup failed:", r.text)
            return
        
        token = r.json()["access_token"]
        print("Got token:", token[:10] + "...")
        
        # 2. Call AI Draft
        print("Calling AI Draft...")
        payload = {
            "title": "Broken streetlight details",
            "address": "123 Main St"
        }
        headers = {"Authorization": f"Bearer {token}"}
        
        r = requests.post(f"{BASE_URL}/api/v1/ai/draft", json=payload, headers=headers)
        
        if r.status_code == 200:
            print("AI Draft Primary Success!")
        else:
            print(f"AI Draft Primary Failed: {r.status_code}")

        # 3. Call Fallback explicitly
        print("Testing Fallback Route directly...")
        r = requests.post(f"{BASE_URL}/ai/draft", json=payload, headers=headers)
        if r.status_code == 200:
            print("AI Draft Fallback Success!")
            print(r.json())
        else:
            print(f"AI Draft Fallback Failed: {r.status_code}")
            print(r.text)
            
    except requests.exceptions.ConnectionError:
        print("Could not connect to backend. Is it running?")

if __name__ == "__main__":
    run()
