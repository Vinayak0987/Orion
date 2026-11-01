"""Test signup and login flow."""
import requests
import time

base_url = "http://localhost:8081"

# Test signup
print("=== Test 1: Signup ===")
start = time.time()
try:
    response = requests.post(
        f"{base_url}/auth/signup",
        json={"email": "testuser@example.com", "password": "testpass123", "full_name": "Test User"},
        timeout=10
    )
    elapsed = time.time() - start
    print(f"Status: {response.status_code}")
    print(f"Time: {elapsed:.2f}s")
    if response.status_code == 200:
        print(f"Response: {response.text[:500]}")
    else:
        print(f"Response: {response.text[:200]}")
except Exception as e:
    elapsed = time.time() - start
    print(f"Error after {elapsed:.2f}s: {e}")

# Test login
print("\n=== Test 2: Login ===")
start = time.time()
try:
    response = requests.post(
        f"{base_url}/auth/login",
        json={"email": "testuser@example.com", "password": "testpass123"},
        timeout=10
    )
    elapsed = time.time() - start
    print(f"Status: {response.status_code}")
    print(f"Time: {elapsed:.2f}s")
    if response.status_code == 200:
        print(f"Response: {response.text[:500]}")
    else:
        print(f"Response: {response.text[:200]}")
except Exception as e:
    elapsed = time.time() - start
    print(f"Error after {elapsed:.2f}s: {e}")
