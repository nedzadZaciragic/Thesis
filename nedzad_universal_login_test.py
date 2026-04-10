#!/usr/bin/env python3
"""
Nedzad Zaciragic Universal Login Feature Test Suite

This test suite specifically tests the new universal login feature for Nedzad Zaciragic
as requested in the review. Tests include:

1. Nedzad Universal Login Test - should succeed WITHOUT requiring a booking
2. Nedzad Token Validation Test - should allow chatting without date restrictions  
3. Case Insensitivity Test - different case variations should work
4. Regular Guest Login Still Works - ensure normal flow isn't broken

Admin credentials: username: myhomeiq_admin, password: Admin123!MyHomeIQ
"""

import requests
import sys
import json
from datetime import datetime, date, timedelta
import time

class NedzadUniversalLoginTester:
    def __init__(self, base_url="https://proximity-search-8.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_token = None
        self.apartment_id = None
        
        # Admin credentials from review request
        self.admin_credentials = {
            "username": "myhomeiq_admin",
            "password": "Admin123!MyHomeIQ"
        }
        
        print(f"🔧 Initializing Nedzad Universal Login Test Suite")
        print(f"🌐 Base URL: {base_url}")
        print(f"🔗 API URL: {self.api_url}")

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30, use_auth=True, auth_token=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'}
        
        # Add authentication header
        if use_auth:
            token = auth_token or self.admin_token
            if token:
                headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Test {self.tests_run}: {name}")
        print(f"   📍 URL: {url}")
        print(f"   📋 Method: {method}")
        if data:
            print(f"   📦 Data: {json.dumps(data, indent=2)}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=timeout)

            success = response.status_code == expected_status
            
            print(f"   📊 Status: {response.status_code} (Expected: {expected_status})")
            
            if success:
                self.tests_passed += 1
                print(f"   ✅ PASSED")
                try:
                    response_data = response.json()
                    print(f"   📄 Response: {json.dumps(response_data, indent=2)[:300]}...")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"   ❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   🚨 Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"   🚨 Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"   ❌ FAILED - Exception: {str(e)}")
            return False, {}

    def admin_login(self):
        """Login as admin to get access token"""
        print("\n🔐 STEP 1: Admin Authentication")
        print("=" * 50)
        
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "admin/login",
            200,
            data=self.admin_credentials,
            use_auth=False
        )
        
        if success and response.get('access_token'):
            self.admin_token = response['access_token']
            print(f"   🎫 Admin token obtained: {self.admin_token[:30]}...")
            return True
        else:
            print("   ❌ Failed to obtain admin token")
            return False

    def get_apartment_id(self):
        """Get any apartment ID from the database using admin token"""
        print("\n🏠 STEP 2: Get Apartment ID")
        print("=" * 50)
        
        success, response = self.run_test(
            "Get Admin Apartments",
            "GET",
            "admin/apartments",
            200,
            use_auth=True,
            auth_token=self.admin_token
        )
        
        if success and response and len(response) > 0:
            # Pick the first apartment
            apartment = response[0]
            self.apartment_id = apartment.get('id')
            apartment_name = apartment.get('name', 'Unknown')
            apartment_address = apartment.get('address', 'Unknown')
            
            print(f"   🏠 Selected apartment: {apartment_name}")
            print(f"   📍 Address: {apartment_address}")
            print(f"   🆔 ID: {self.apartment_id}")
            return True
        else:
            print("   ❌ No apartments found in database")
            return False

    def test_nedzad_universal_login(self):
        """
        CRITICAL TEST CASE 1: Nedzad Universal Login Test
        - Test guest login with first_name="Nedzad" and last_name="Zaciragic"
        - Should succeed WITHOUT requiring a booking in guest_bookings collection
        - Should return success=True with a welcome message about universal access
        - Should return a guest_token
        """
        print("\n🎯 CRITICAL TEST 1: Nedzad Universal Login")
        print("=" * 50)
        
        if not self.apartment_id:
            print("   ❌ No apartment ID available")
            return False
        
        nedzad_login_data = {
            "first_name": "Nedzad",
            "last_name": "Zaciragic",
            "apartment_id": self.apartment_id
        }
        
        success, response = self.run_test(
            "Nedzad Universal Login",
            "POST",
            "guest-login",
            200,
            data=nedzad_login_data,
            use_auth=False
        )
        
        if success:
            # Verify response structure
            success_flag = response.get('success')
            message = response.get('message', '')
            guest_token = response.get('guest_token', '')
            guest_data = response.get('guest_data', {})
            
            print(f"   📊 Success: {success_flag}")
            print(f"   💬 Message: {message}")
            print(f"   🎫 Token length: {len(guest_token)} chars")
            print(f"   👤 Guest data: {json.dumps(guest_data, indent=2)}")
            
            # Verify critical requirements
            checks_passed = 0
            total_checks = 5
            
            # Check 1: Success should be True
            if success_flag == True:
                print("   ✅ Check 1: Success = True")
                checks_passed += 1
            else:
                print("   ❌ Check 1: Success should be True")
            
            # Check 2: Should have welcome message about universal access
            if 'universal access' in message.lower() or 'welcome nedzad' in message.lower():
                print("   ✅ Check 2: Welcome message mentions universal access")
                checks_passed += 1
            else:
                print("   ❌ Check 2: Message should mention universal access")
            
            # Check 3: Should return a guest token
            if guest_token and len(guest_token) > 50:  # JWT tokens are typically long
                print("   ✅ Check 3: Guest token provided")
                checks_passed += 1
                # Store token for next test
                self.nedzad_token = guest_token
            else:
                print("   ❌ Check 3: Guest token missing or invalid")
            
            # Check 4: Guest data should contain Nedzad's info
            if (guest_data.get('first_name') == 'Nedzad' and 
                guest_data.get('last_name') == 'Zaciragic' and
                guest_data.get('apartment_id') == self.apartment_id):
                print("   ✅ Check 4: Guest data contains correct information")
                checks_passed += 1
            else:
                print("   ❌ Check 4: Guest data incorrect")
            
            # Check 5: Should have extended access dates (1 year)
            check_in = guest_data.get('check_in')
            check_out = guest_data.get('check_out')
            if check_in and check_out:
                try:
                    check_in_date = datetime.fromisoformat(check_in).date()
                    check_out_date = datetime.fromisoformat(check_out).date()
                    access_days = (check_out_date - check_in_date).days
                    
                    if access_days >= 360:  # Should be around 365 days
                        print(f"   ✅ Check 5: Extended access period ({access_days} days)")
                        checks_passed += 1
                    else:
                        print(f"   ❌ Check 5: Access period too short ({access_days} days)")
                except:
                    print("   ❌ Check 5: Invalid date format")
            else:
                print("   ❌ Check 5: Missing check-in/check-out dates")
            
            print(f"\n   📈 NEDZAD LOGIN RESULT: {checks_passed}/{total_checks} checks passed")
            
            if checks_passed == total_checks:
                print("   🎉 NEDZAD UNIVERSAL LOGIN: FULLY WORKING")
                return True
            else:
                print("   ⚠️  NEDZAD UNIVERSAL LOGIN: PARTIALLY WORKING")
                return False
        
        return False

    def test_nedzad_token_validation(self):
        """
        CRITICAL TEST CASE 2: Nedzad Token Validation Test
        - Use the guest_token from step 1
        - Send a chat message to /guest-chat endpoint with the token
        - Should successfully allow chatting without date restrictions
        """
        print("\n🎯 CRITICAL TEST 2: Nedzad Token Validation")
        print("=" * 50)
        
        if not hasattr(self, 'nedzad_token') or not self.nedzad_token:
            print("   ❌ No Nedzad token available from previous test")
            return False
        
        if not self.apartment_id:
            print("   ❌ No apartment ID available")
            return False
        
        # Test chat message with Nedzad's token
        chat_data = {
            "apartment_id": self.apartment_id,
            "message": "Hello, I'm Nedzad testing my universal access. What are the apartment rules?",
            "session_id": "nedzad_test_session"
        }
        
        # Use Bearer token authentication
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.nedzad_token}'
        }
        
        print(f"   🎫 Using Nedzad token: {self.nedzad_token[:30]}...")
        print(f"   💬 Test message: {chat_data['message']}")
        
        try:
            url = f"{self.api_url}/guest-chat"
            response = requests.post(url, json=chat_data, headers=headers, timeout=60)
            
            print(f"   📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    ai_response = response_data.get('response', '')
                    
                    print(f"   ✅ CHAT SUCCESS: Token validation working")
                    print(f"   🤖 AI Response: {ai_response[:200]}...")
                    
                    # Verify AI response quality
                    checks_passed = 0
                    total_checks = 3
                    
                    # Check 1: Should get a meaningful AI response
                    if ai_response and len(ai_response) > 20:
                        print("   ✅ Check 1: Meaningful AI response received")
                        checks_passed += 1
                    else:
                        print("   ❌ Check 1: AI response too short or missing")
                    
                    # Check 2: Response should be contextual (about apartment rules)
                    if any(word in ai_response.lower() for word in ['rule', 'policy', 'apartment', 'stay', 'guest']):
                        print("   ✅ Check 2: Response is contextual to apartment rules")
                        checks_passed += 1
                    else:
                        print("   ❌ Check 2: Response not contextual")
                    
                    # Check 3: Should acknowledge Nedzad by name (personalization)
                    if 'nedzad' in ai_response.lower():
                        print("   ✅ Check 3: AI acknowledges Nedzad by name")
                        checks_passed += 1
                    else:
                        print("   ⚠️  Check 3: AI doesn't use Nedzad's name (acceptable)")
                        checks_passed += 1  # This is acceptable
                    
                    print(f"\n   📈 TOKEN VALIDATION RESULT: {checks_passed}/{total_checks} checks passed")
                    
                    if checks_passed >= 2:  # At least 2/3 should pass
                        print("   🎉 NEDZAD TOKEN VALIDATION: WORKING")
                        return True
                    else:
                        print("   ⚠️  NEDZAD TOKEN VALIDATION: ISSUES DETECTED")
                        return False
                        
                except Exception as e:
                    print(f"   ❌ Error parsing response: {str(e)}")
                    print(f"   📄 Raw response: {response.text}")
                    return False
            else:
                print(f"   ❌ CHAT FAILED: Status {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   🚨 Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"   🚨 Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ CHAT EXCEPTION: {str(e)}")
            return False

    def test_case_insensitivity(self):
        """
        CRITICAL TEST CASE 3: Case Insensitivity Test
        - Test with different case variations: "NEDZAD zaciragic", "nedzad ZACIRAGIC", "Nedzad Zaciragic"
        - All should work
        """
        print("\n🎯 CRITICAL TEST 3: Case Insensitivity Test")
        print("=" * 50)
        
        if not self.apartment_id:
            print("   ❌ No apartment ID available")
            return False
        
        # Test different case variations
        test_cases = [
            {"first_name": "NEDZAD", "last_name": "zaciragic", "description": "UPPERCASE first, lowercase last"},
            {"first_name": "nedzad", "last_name": "ZACIRAGIC", "description": "lowercase first, UPPERCASE last"},
            {"first_name": "Nedzad", "last_name": "Zaciragic", "description": "Proper Case"},
            {"first_name": "nEdZaD", "last_name": "zAcIrAgIc", "description": "Mixed Case"}
        ]
        
        successful_cases = 0
        total_cases = len(test_cases)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n   🔤 Case Test {i}: {test_case['description']}")
            print(f"      First: '{test_case['first_name']}', Last: '{test_case['last_name']}'")
            
            login_data = {
                "first_name": test_case['first_name'],
                "last_name": test_case['last_name'],
                "apartment_id": self.apartment_id
            }
            
            success, response = self.run_test(
                f"Case Test {i} - {test_case['description']}",
                "POST",
                "guest-login",
                200,
                data=login_data,
                use_auth=False
            )
            
            if success:
                success_flag = response.get('success')
                message = response.get('message', '')
                guest_token = response.get('guest_token', '')
                
                if (success_flag == True and 
                    guest_token and 
                    ('universal access' in message.lower() or 'welcome nedzad' in message.lower())):
                    print(f"      ✅ Case {i}: SUCCESS - Universal access granted")
                    successful_cases += 1
                else:
                    print(f"      ❌ Case {i}: FAILED - Universal access not granted")
                    print(f"         Success: {success_flag}, Token: {bool(guest_token)}")
                    print(f"         Message: {message}")
            else:
                print(f"      ❌ Case {i}: FAILED - API error")
        
        print(f"\n   📈 CASE INSENSITIVITY RESULT: {successful_cases}/{total_cases} cases passed")
        
        if successful_cases == total_cases:
            print("   🎉 CASE INSENSITIVITY: FULLY WORKING")
            return True
        elif successful_cases > 0:
            print("   ⚠️  CASE INSENSITIVITY: PARTIALLY WORKING")
            return False
        else:
            print("   ❌ CASE INSENSITIVITY: NOT WORKING")
            return False

    def test_regular_guest_login_still_works(self):
        """
        CRITICAL TEST CASE 4: Regular Guest Login Still Works
        - Test regular guest login with a different name to ensure normal flow isn't broken
        - Should fail if no booking exists (expected behavior)
        """
        print("\n🎯 CRITICAL TEST 4: Regular Guest Login Still Works")
        print("=" * 50)
        
        if not self.apartment_id:
            print("   ❌ No apartment ID available")
            return False
        
        # Test with a regular guest name (not Nedzad)
        regular_guest_data = {
            "first_name": "John",
            "last_name": "Doe", 
            "apartment_id": self.apartment_id
        }
        
        print("   👤 Testing regular guest: John Doe")
        print("   📋 Expected: Should fail (no booking exists)")
        
        success, response = self.run_test(
            "Regular Guest Login (Should Fail)",
            "POST",
            "guest-login",
            200,  # API returns 200 but success=false
            data=regular_guest_data,
            use_auth=False
        )
        
        if success:
            success_flag = response.get('success')
            message = response.get('message', '')
            guest_token = response.get('guest_token', '')
            
            print(f"   📊 Success: {success_flag}")
            print(f"   💬 Message: {message}")
            print(f"   🎫 Token: {bool(guest_token)}")
            
            # For regular guests without bookings, should fail
            if (success_flag == False and 
                not guest_token and 
                ('no booking found' in message.lower() or 'check your name' in message.lower())):
                print("   ✅ REGULAR GUEST LOGIN: Working correctly (properly rejects without booking)")
                return True
            elif success_flag == True:
                print("   ❌ REGULAR GUEST LOGIN: ERROR - Should not grant access without booking")
                return False
            else:
                print("   ⚠️  REGULAR GUEST LOGIN: Unexpected response format")
                return False
        else:
            print("   ❌ REGULAR GUEST LOGIN: API error")
            return False

    def test_nedzad_with_wrong_apartment_id(self):
        """
        BONUS TEST: Test Nedzad login with non-existent apartment ID
        - Should handle gracefully
        """
        print("\n🎯 BONUS TEST: Nedzad with Invalid Apartment ID")
        print("=" * 50)
        
        nedzad_login_data = {
            "first_name": "Nedzad",
            "last_name": "Zaciragic",
            "apartment_id": "invalid-apartment-id-12345"
        }
        
        print("   🏠 Testing with invalid apartment ID")
        
        success, response = self.run_test(
            "Nedzad Login - Invalid Apartment",
            "POST",
            "guest-login",
            200,  # Should still return 200 but with success=false or handle gracefully
            data=nedzad_login_data,
            use_auth=False
        )
        
        if success:
            success_flag = response.get('success')
            message = response.get('message', '')
            
            print(f"   📊 Success: {success_flag}")
            print(f"   💬 Message: {message}")
            
            # Should either grant access (universal) or handle gracefully
            if success_flag == True:
                print("   ✅ BONUS TEST: Nedzad gets universal access even with invalid apartment")
                return True
            elif success_flag == False and 'apartment' in message.lower():
                print("   ✅ BONUS TEST: Properly handles invalid apartment ID")
                return True
            else:
                print("   ⚠️  BONUS TEST: Unexpected behavior")
                return False
        else:
            print("   ❌ BONUS TEST: API error")
            return False

    def run_all_tests(self):
        """Run all Nedzad universal login tests"""
        print("\n" + "="*80)
        print("🚀 NEDZAD ZACIRAGIC UNIVERSAL LOGIN TEST SUITE")
        print("="*80)
        print("Testing the new universal login feature as requested in review")
        print("Admin credentials: myhomeiq_admin / Admin123!MyHomeIQ")
        print("="*80)
        
        # Step 1: Admin login
        if not self.admin_login():
            print("\n❌ CRITICAL FAILURE: Cannot proceed without admin access")
            return False
        
        # Step 2: Get apartment ID
        if not self.get_apartment_id():
            print("\n❌ CRITICAL FAILURE: Cannot proceed without apartment ID")
            return False
        
        # Run all critical tests
        print("\n" + "="*60)
        print("🎯 RUNNING CRITICAL TEST CASES")
        print("="*60)
        
        test_results = []
        
        # Test 1: Nedzad Universal Login
        result1 = self.test_nedzad_universal_login()
        test_results.append(("Nedzad Universal Login", result1))
        
        # Test 2: Nedzad Token Validation (only if Test 1 passed)
        if result1:
            result2 = self.test_nedzad_token_validation()
            test_results.append(("Nedzad Token Validation", result2))
        else:
            print("\n⚠️  Skipping Token Validation test (Universal Login failed)")
            test_results.append(("Nedzad Token Validation", False))
        
        # Test 3: Case Insensitivity
        result3 = self.test_case_insensitivity()
        test_results.append(("Case Insensitivity", result3))
        
        # Test 4: Regular Guest Login Still Works
        result4 = self.test_regular_guest_login_still_works()
        test_results.append(("Regular Guest Login", result4))
        
        # Bonus Test: Invalid Apartment ID
        result5 = self.test_nedzad_with_wrong_apartment_id()
        test_results.append(("Invalid Apartment ID (Bonus)", result5))
        
        # Final Results
        print("\n" + "="*80)
        print("📊 FINAL TEST RESULTS")
        print("="*80)
        
        passed_tests = 0
        critical_tests = 4  # First 4 are critical
        
        for i, (test_name, result) in enumerate(test_results, 1):
            status = "✅ PASSED" if result else "❌ FAILED"
            critical = " (CRITICAL)" if i <= critical_tests else " (BONUS)"
            print(f"{i}. {test_name}: {status}{critical}")
            if result and i <= critical_tests:
                passed_tests += 1
        
        print(f"\n📈 CRITICAL TESTS PASSED: {passed_tests}/{critical_tests}")
        print(f"📈 TOTAL TESTS RUN: {self.tests_run}")
        print(f"📈 TOTAL TESTS PASSED: {self.tests_passed}")
        
        # Overall assessment
        if passed_tests == critical_tests:
            print("\n🎉 NEDZAD UNIVERSAL LOGIN FEATURE: FULLY WORKING")
            print("✅ All critical test cases passed")
            print("✅ Feature is ready for production")
            return True
        elif passed_tests >= 2:
            print("\n⚠️  NEDZAD UNIVERSAL LOGIN FEATURE: PARTIALLY WORKING")
            print(f"⚠️  {passed_tests}/{critical_tests} critical tests passed")
            print("⚠️  Some issues need to be addressed")
            return False
        else:
            print("\n❌ NEDZAD UNIVERSAL LOGIN FEATURE: NOT WORKING")
            print("❌ Major issues detected")
            print("❌ Feature needs significant fixes")
            return False

def main():
    """Main test execution"""
    print("🧪 Starting Nedzad Zaciragic Universal Login Test Suite...")
    
    tester = NedzadUniversalLoginTester()
    
    try:
        success = tester.run_all_tests()
        
        if success:
            print("\n🎯 TEST SUITE COMPLETED SUCCESSFULLY")
            sys.exit(0)
        else:
            print("\n⚠️  TEST SUITE COMPLETED WITH ISSUES")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Test suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test suite failed with exception: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()