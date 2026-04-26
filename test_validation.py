#!/usr/bin/env python3
"""
Test script to demonstrate input validation.
Run this to see validation in action.
"""

from utils.validators import Validators, ValidationError


def test_validation(test_name, validator_func, test_cases):
    """Run validation tests and print results."""
    print(f"\n{'='*60}")
    print(f"Testing: {test_name}")
    print('='*60)
    
    for value, expected_result in test_cases:
        try:
            result = validator_func(value)
            status = "✅ PASS" if expected_result == "pass" else "❌ FAIL (should have failed)"
            print(f"{status}: '{value}' → '{result}'")
        except ValidationError as e:
            status = "✅ PASS" if expected_result == "fail" else "❌ FAIL (should have passed)"
            print(f"{status}: '{value}' → Error: {e}")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("INPUT VALIDATION TEST SUITE")
    print("="*60)
    
    # Test 1: Name Validation
    test_validation(
        "Name Validation",
        lambda v: Validators.validate_name(v, "Name"),
        [
            ("Dr. John Smith", "pass"),
            ("Mary O'Brien-Jones", "pass"),
            ("A", "fail"),  # Too short
            (".", "fail"),  # Just special character
            ("123456", "fail"),  # No letters
            ("", "fail"),  # Empty
        ]
    )
    
    # Test 2: Abbreviation Validation
    test_validation(
        "Abbreviation Validation",
        lambda v: Validators.validate_abbreviation(v, "Abbreviation"),
        [
            ("PMJ", "pass"),
            ("dr-smith", "pass"),  # Will be uppercased
            ("JD123", "pass"),
            ("P M J", "fail"),  # Contains spaces
            ("---", "fail"),  # Just special characters
            ("", "fail"),  # Empty
        ]
    )
    
    # Test 3: Email Validation
    test_validation(
        "Email Validation",
        lambda v: Validators.validate_email(v, "Email"),
        [
            ("john.smith@dau.ac.in", "pass"),
            ("faculty123@university.edu", "pass"),
            ("john.smith", "fail"),  # Missing @domain
            ("john@", "fail"),  # Incomplete domain
            ("@domain.com", "fail"),  # Missing username
            ("", "fail"),  # Empty
        ]
    )
    
    # Test 4: Integer Validation
    test_validation(
        "Positive Integer Validation",
        lambda v: Validators.validate_positive_integer(v, "Count"),
        [
            ("50", "pass"),
            ("120", "pass"),
            ("0", "fail"),  # Must be at least 1
            ("-10", "fail"),  # Negative
            ("fifty", "fail"),  # Not a number
            ("", "fail"),  # Empty
        ]
    )
    
    # Test 5: Capacity Validation
    test_validation(
        "Capacity Validation",
        lambda v: Validators.validate_capacity(v, "Capacity"),
        [
            ("50", "pass"),
            ("1", "pass"),
            ("10000", "pass"),
            ("0", "fail"),  # Must be at least 1
            ("10001", "fail"),  # Exceeds max
            ("-5", "fail"),  # Negative
        ]
    )
    
    # Test 6: Date Validation
    test_validation(
        "Date Validation",
        lambda v: Validators.validate_date(v, "Date"),
        [
            ("2025-01-15", "pass"),
            ("2025-12-31", "pass"),
            ("2025-13-01", "fail"),  # Invalid month
            ("2025/01/15", "fail"),  # Wrong format
            ("15-01-2025", "fail"),  # Wrong format
            ("", "fail"),  # Empty
        ]
    )
    
    # Test 7: Choice Validation
    test_validation(
        "Role Validation",
        lambda v: Validators.validate_role(v),
        [
            ("admin", "pass"),
            ("faculty", "pass"),
            ("teacher", "fail"),  # Not in allowed list
            ("", "fail"),  # Empty
        ]
    )
    
    # Test 8: Credits Validation
    test_validation(
        "Credits Validation",
        lambda v: Validators.validate_credits(v, "Credits"),
        [
            ("3", "pass"),
            ("3.5", "pass"),
            ("4.0", "pass"),
            ("-1", "fail"),  # Negative
            ("25", "fail"),  # Exceeds max
            ("abc", "fail"),  # Not a number
        ]
    )
    
    print("\n" + "="*60)
    print("TEST SUITE COMPLETE")
    print("="*60 + "\n")
