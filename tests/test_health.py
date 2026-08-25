import os
import sys

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from server import app

def test_health_routes():
    print("=" * 80)
    print("  TESTING HEALTH CHECK & KEEP-ALIVE UPTIME ROUTES")
    print("=" * 80)

    client = TestClient(app)

    # 1. Test /health
    print("\n--- Testing GET /health ---")
    res1 = client.get("/health")
    print(f"Status Code: {res1.status_code}")
    print(f"Payload:     {res1.json()}")
    assert res1.status_code == 200
    assert res1.json()["status"] == "healthy"
    assert res1.json()["database"] == "connected"

    # 2. Test /api/health
    print("\n--- Testing GET /api/health ---")
    res2 = client.get("/api/health")
    print(f"Status Code: {res2.status_code}")
    print(f"Payload:     {res2.json()}")
    assert res2.status_code == 200
    assert res2.json()["status"] == "healthy"

    print("\n" + "=" * 80)
    print("[SUCCESS] ALL HEALTH CHECK & UPTIME KEEP-ALIVE TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    test_health_routes()
