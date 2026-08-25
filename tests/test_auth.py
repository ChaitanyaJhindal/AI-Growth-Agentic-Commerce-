import os
import sys
import uuid

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.auth import UserManager, hash_password, verify_password

def run_auth_tests():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 80)
    print("  RUNNING MONGODB USER AUTHENTICATION & DATA SYNC TESTS")
    print("=" * 80)

    # 1. Test Password Hashing
    print("\n--- 1. Testing PBKDF2 Password Hashing ---")
    raw_password = "SecretPassword123!"
    salt, hashed = hash_password(raw_password)
    assert salt and hashed, "Salt or Hash generation failed"
    assert verify_password(raw_password, salt, hashed), "Password verification failed for valid password"
    assert not verify_password("WrongPassword!", salt, hashed), "Password verification succeeded for invalid password"
    print("✓ Cryptographic hashing & verification verified successfully.")

    # 2. Test UserManager with MongoDB
    print("\n--- 2. Testing MongoDB User Management ---")
    user_mgr = UserManager()

    test_email = f"test_user_{uuid.uuid4().hex[:6]}@example.com"
    test_name = "Test Fashionista"
    test_password = "SecurePassword2026"

    # 2a. Signup
    print(f"Creating account for {test_email}...")
    signup_res = user_mgr.signup(name=test_name, email=test_email, password=test_password)
    assert signup_res["success"] is True, f"Signup failed: {signup_res}"
    user_data = signup_res["user"]
    print(f"✓ User created successfully with ID: {user_data['id']}")

    # 2b. Reject duplicate signup
    dup_res = user_mgr.signup(name=test_name, email=test_email, password=test_password)
    assert dup_res["success"] is False, "Duplicate email check failed"
    print("✓ Duplicate email registration rejected as expected.")

    # 2c. Successful Login
    print("Testing login with valid credentials...")
    login_res = user_mgr.login(email=test_email, password=test_password)
    assert login_res["success"] is True, f"Login failed: {login_res}"
    assert login_res["user"]["email"] == test_email
    print(f"✓ Logged in successfully as {login_res['user']['name']}")

    # 2d. Invalid Login
    print("Testing login with invalid password...")
    bad_login = user_mgr.login(email=test_email, password="BadPassword999")
    assert bad_login["success"] is False, "Invalid password login should fail"
    print("✓ Invalid password rejected.")

    # 2e. Sync Wardrobe & Bag to MongoDB
    print("\n--- 3. Testing MongoDB Wardrobe & Bag Synchronization ---")
    mock_wardrobe = [
        {"product_id": "PROD-101", "name": "Classic Linen Shirt", "price": 48.00}
    ]
    mock_bag = [
        {"product_id": "PROD-202", "name": "Minimalist Leather Loafers", "price": 120.00}
    ]
    sync_res = user_mgr.sync_user_data(email=test_email, wardrobe=mock_wardrobe, bag=mock_bag)
    assert sync_res["success"] is True, f"Sync failed: {sync_res}"

    # Verify data in MongoDB profile
    profile = user_mgr.get_user_profile(test_email)
    assert len(profile["wardrobe"]) == 1 and profile["wardrobe"][0]["product_id"] == "PROD-101"
    assert len(profile["bag"]) == 1 and profile["bag"][0]["product_id"] == "PROD-202"
    print(f"✓ Wardrobe & Bag synchronized and verified in MongoDB! (Items: {len(profile['wardrobe'])} wardrobe, {len(profile['bag'])} bag)")

    # Cleanup test user
    user_mgr.users_collection.delete_one({"email": test_email})
    print(f"✓ Cleaned up test user document.")

    print("\n" + "=" * 80)
    print("🎉 ALL MONGODB AUTH & PERSISTENCE TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_auth_tests()
