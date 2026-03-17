import requests

BASE_URL = "http://127.0.0.1:8000"

def test_all():
    print("=" * 60)
    print("TESTING HEALTH CHATBOT API")
    print("=" * 60)
    
    # Test 1: List symptoms (GET)
    print("\n1. Testing GET /symptoms/")
    try:
        response = requests.get(f"{BASE_URL}/symptoms/")
        print(f"   Status: {response.status_code}")
        symptoms = response.json()
        print(f"   Found {len(symptoms)} symptoms")
        if symptoms:
            print(f"   First symptom: {symptoms[0]['name']}")
    except Exception as e:
        print(f"   ERROR: {e}")
        return
    
    # Test 2: Start chat (POST)
    print("\n2. Testing POST /start/")
    try:
        response = requests.post(f"{BASE_URL}/start/")
        print(f"   Status: {response.status_code}")
        data = response.json()
        session_id = data.get('session_id')
        print(f"   Session ID: {session_id}")
        print(f"   Bot says: {data.get('message')[:50]}...")
    except Exception as e:
        print(f"   ERROR: {e}")
        return
    
    # Test 3: Send message (POST)
    print("\n3. Testing POST /message/")
    try:
        payload = {
            "session_id": session_id,
            "message": "I have cough and fatigue"
        }
        response = requests.post(f"{BASE_URL}/message/", json=payload)
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   Found symptoms: {data.get('found_symptoms')}")
        print(f"   Urgency: {data.get('current_urgency')}")
        print(f"   Bot says: {data.get('response')[:60]}...")
    except Exception as e:
        print(f"   ERROR: {e}")
        return
    
    # Test 4: Get history (GET)
    print("\n4. Testing GET /history/{session_id}/")
    try:
        response = requests.get(f"{BASE_URL}/history/{session_id}/")
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   Session has {len(data.get('messages', []))} messages")
    except Exception as e:
        print(f"   ERROR: {e}")
        return
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! ✅")
    print("=" * 60)

if __name__ == "__main__":
    test_all()

# Add these tests at the bottom of test_all()

def test_scenario(name, message):
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    
    # Start new session
    response = requests.post(f"{BASE_URL}/start/")
    session_id = response.json()['session_id']
    
    # Send message
    result = requests.post(f"{BASE_URL}/message/", json={
        "session_id": session_id,
        "message": message
    }).json()
    
    print(f"Message: '{message}'")
    print(f"Symptoms: {result.get('found_symptoms')}")
    print(f"Urgency: {result.get('current_urgency')}")
    print(f"Response: {result.get('response')[:80]}...")

# Run tests
test_scenario("Emergency", "chest pain and shortness of breath")
test_scenario("Flu-like", "fever body pain and cough")
test_scenario("Stomach issues", "vomiting and diarrhea")
test_scenario("Simple cold", "runny nose and sneezing")