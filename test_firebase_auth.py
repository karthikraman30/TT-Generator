#!/usr/bin/env python3
"""
Firebase Authentication Testing Script
Run this to verify your Firebase setup and password policy
"""

import re
import secrets
import string


def test_password_policy(password):
    """Test if a password meets the policy requirements."""
    policy = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$'
    
    checks = {
        'length': len(password) >= 8,
        'uppercase': bool(re.search(r'[A-Z]', password)),
        'lowercase': bool(re.search(r'[a-z]', password)),
        'digit': bool(re.search(r'\d', password)),
        'special': bool(re.search(r'[^A-Za-z0-9]', password)),
        'overall': bool(re.match(policy, password))
    }
    
    return checks


def generate_temp_password(length=12):
    """Generate a temporary password meeting policy."""
    if length < 8:
        length = 8
    upper = secrets.choice(string.ascii_uppercase)
    lower = secrets.choice(string.ascii_lowercase)
    digit = secrets.choice(string.digits)
    special = secrets.choice("!@#$%^&*")
    remaining = [
        secrets.choice(string.ascii_letters + string.digits + "!@#$%^&*")
        for _ in range(length - 4)
    ]
    chars = [upper, lower, digit, special] + remaining
    secrets.SystemRandom().shuffle(chars)
    return ''.join(chars)


def print_test_result(password, checks):
    """Pretty print test results."""
    print(f"\n{'='*60}")
    print(f"Testing password: {password}")
    print(f"{'='*60}")
    print(f"✓ Length (8+):        {'✅ PASS' if checks['length'] else '❌ FAIL'}")
    print(f"✓ Uppercase (A-Z):    {'✅ PASS' if checks['uppercase'] else '❌ FAIL'}")
    print(f"✓ Lowercase (a-z):    {'✅ PASS' if checks['lowercase'] else '❌ FAIL'}")
    print(f"✓ Digit (0-9):        {'✅ PASS' if checks['digit'] else '❌ FAIL'}")
    print(f"✓ Special (!@#$...):  {'✅ PASS' if checks['special'] else '❌ FAIL'}")
    print(f"{'='*60}")
    print(f"Overall: {'✅ VALID PASSWORD' if checks['overall'] else '❌ INVALID PASSWORD'}")
    print(f"{'='*60}\n")


def main():
    print("\n" + "="*60)
    print("🔐 FIREBASE AUTHENTICATION TESTING TOOL")
    print("="*60)
    
    # Test 1: Generate temporary passwords
    print("\n📝 Test 1: Generating Temporary Passwords")
    print("-" * 60)
    for i in range(3):
        temp_pass = generate_temp_password()
        checks = test_password_policy(temp_pass)
        print(f"Generated #{i+1}: {temp_pass} - {'✅ Valid' if checks['overall'] else '❌ Invalid'}")
    
    # Test 2: Test invalid passwords
    print("\n📝 Test 2: Testing Invalid Passwords (Should Fail)")
    print("-" * 60)
    invalid_passwords = [
        ("short", "Too short"),
        ("alllowercase123!", "No uppercase"),
        ("ALLUPPERCASE123!", "No lowercase"),
        ("NoDigitsHere!", "No digit"),
        ("NoSpecial123", "No special character"),
        ("abc123", "Too short + no uppercase + no special"),
    ]
    
    for pwd, reason in invalid_passwords:
        checks = test_password_policy(pwd)
        status = "❌ Correctly Rejected" if not checks['overall'] else "⚠️ ERROR: Accepted"
        print(f"{pwd:20} → {status:25} ({reason})")
    
    # Test 3: Test valid passwords
    print("\n📝 Test 3: Testing Valid Passwords (Should Pass)")
    print("-" * 60)
    valid_passwords = [
        "ValidPass123!",
        "MyP@ssw0rd",
        "Secure#2024",
        "Test!ng123",
        "Admin@Pass1",
    ]
    
    for pwd in valid_passwords:
        checks = test_password_policy(pwd)
        status = "✅ Correctly Accepted" if checks['overall'] else "⚠️ ERROR: Rejected"
        print(f"{pwd:20} → {status}")
    
    # Test 4: Interactive testing
    print("\n📝 Test 4: Interactive Password Testing")
    print("-" * 60)
    print("Enter passwords to test (or press Enter to skip):")
    
    while True:
        try:
            user_input = input("\nPassword to test (or Enter to finish): ").strip()
            if not user_input:
                break
            checks = test_password_policy(user_input)
            print_test_result(user_input, checks)
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
    
    # Summary
    print("\n" + "="*60)
    print("✅ TESTING COMPLETE")
    print("="*60)
    print("\n📋 Password Policy Summary:")
    print("   • Minimum 8 characters")
    print("   • At least 1 uppercase letter (A-Z)")
    print("   • At least 1 lowercase letter (a-z)")
    print("   • At least 1 digit (0-9)")
    print("   • At least 1 special character (!@#$%^&*)")
    print("\n💡 Tip: Use the generated passwords for testing faculty accounts")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
