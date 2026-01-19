import urllib.request
import json
import ssl
import sys

URL = "https://raw.githubusercontent.com/KevinAwesomeCoding/mods-folder/main/modpacks.json"

print(f"--- STARTING MAC NETWORK TEST ---")
print(f"Testing URL: {URL}")

try:
    # 1. Test Standard SSL (Simulates a normal browser)
    print("\nAttempt 1: Standard SSL Context")
    req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as response:
        data = response.read().decode('utf-8')
        json_data = json.loads(data)
        print("SUCCESS! Standard SSL worked.")
        print(f"Found {len(json_data)} categories.")

except Exception as e1:
    print(f"FAILED Attempt 1: {e1}")
    
    # 2. Test Unverified SSL (The fix we added)
    try:
        print("\nAttempt 2: Unverified SSL Context (The Fix)")
        context = ssl._create_unverified_context()
        req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=context, timeout=10) as response:
            data = response.read().decode('utf-8')
            json_data = json.loads(data)
            print("SUCCESS! Unverified SSL worked.")
            print(f"Found {len(json_data)} categories.")
            sys.exit(0) # Exit with success code
            
    except Exception as e2:
        print(f"FAILED Attempt 2: {e2}")
        print("CRITICAL: Both methods failed. The Mac server cannot reach the URL.")
        sys.exit(1) # Exit with error code to fail the build
