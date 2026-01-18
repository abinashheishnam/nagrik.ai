import random

OTP_STORE = {}

def generate_otp(phone: str):
    otp = str(random.randint(100000, 999999))
    OTP_STORE[phone] = otp
    print(f"[OTP DEMO] OTP for {phone}: {otp}")
    return otp

def verify_otp(phone: str, otp: str):
    return OTP_STORE.get(phone) == otp
