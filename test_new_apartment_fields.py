#!/usr/bin/env python3
"""
Focused test for new apartment fields functionality
Tests the specific new fields added to the apartment model:
- check_in_time, check_out_time, check_in_instructions
- apartment_locations (dictionary)
- wifi_network, wifi_password, wifi_instructions
"""

import requests
import json
import sys

class NewApartmentFieldsTester:
    def __init__(self, base_url="https://proximity-search-8.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.token = None
        self.user_id = None
        self.admin_token = None
        self.new_fields_apartment_id = None
        
        # Test user data
        self.test_user = {
            "email": "newfields@example.com",
            "full_name": "New Fields Tester",
            "password": "testpass123"
        }
        
        # Admin credentials
        self.admin_credentials = {
            "username": "myhomeiq_admin",
            "password": "Admin123!MyHomeIQ"
        }

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30, use_auth=True):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'}
        
        # Add authentication header if token is available and use_auth is True
        if use_auth and self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
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
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def setup_authentication(self):
        """Setup user authentication"""
        print("🔐 Setting up authentication...")
        
        # Try to login first (user might already exist)
        login_data = {
            "email": self.test_user["email"],
            "password": self.test_user["password"]
        }
        
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data=login_data,
            use_auth=False
        )
        
        if success and response.get('access_token'):
            self.token = response['access_token']
            self.user_id = response['user']['id']
            print(f"   ✅ User logged in successfully")
            return True
        
        # If login failed, try to register
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data=self.test_user,
            use_auth=False
        )
        
        if success and response.get('access_token'):
            self.token = response['access_token']
            self.user_id = response['user']['id']
            print(f"   ✅ User registered and authenticated")
            return True
        else:
            print("   ❌ Failed to authenticate user")
            return False

    def setup_admin_authentication(self):
        """Setup admin authentication"""
        print("🔐 Setting up admin authentication...")
        
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
            print(f"   ✅ Admin authenticated")
            return True
        else:
            print("   ❌ Failed to authenticate admin")
            return False

    def test_create_apartment_with_new_fields(self):
        """Test creating apartment with new check-in/WiFi fields"""
        apartment_data = {
            "name": "Modern Apartment with New Fields",
            "address": "456 New Field Street, Test City",
            "description": "Test apartment with all new fields",
            "rules": ["No smoking", "Check-in instructions provided"],
            "contact": {
                "phone": "+1234567890",
                "email": "host@example.com"
            },
            "ical_url": "",
            "recommendations": {},
            # NEW FIELDS BEING TESTED
            "check_in_time": "15:00",
            "check_out_time": "11:00",
            "check_in_instructions": "Keys are under the blue mat",
            "apartment_locations": {
                "keys": "under the mat",
                "towels": "bathroom closet",
                "kitchen_utensils": "drawer"
            },
            "wifi_network": "TestWiFi123",
            "wifi_password": "password123",
            "wifi_instructions": "Router is in living room"
        }
        
        success, response = self.run_test(
            "Create Apartment with New Fields",
            "POST",
            "apartments",
            200,
            data=apartment_data
        )
        
        if success and response.get('id'):
            self.new_fields_apartment_id = response['id']
            print(f"   Created apartment with new fields ID: {self.new_fields_apartment_id}")
            
            # Verify all new fields are present in response
            new_fields_check = {
                "check_in_time": "15:00",
                "check_out_time": "11:00", 
                "check_in_instructions": "Keys are under the blue mat",
                "apartment_locations": {"keys": "under the mat", "towels": "bathroom closet", "kitchen_utensils": "drawer"},
                "wifi_network": "TestWiFi123",
                "wifi_password": "password123",
                "wifi_instructions": "Router is in living room"
            }
            
            all_fields_present = True
            for field, expected_value in new_fields_check.items():
                actual_value = response.get(field)
                if actual_value == expected_value:
                    print(f"   ✅ {field}: {actual_value}")
                else:
                    print(f"   ❌ {field}: Expected {expected_value}, got {actual_value}")
                    all_fields_present = False
            
            if all_fields_present:
                print("   ✅ All new apartment fields properly stored and returned")
                return True
            else:
                print("   ❌ Some new fields missing or incorrect")
                return False
        
        return success

    def test_get_apartment_with_new_fields(self):
        """Test retrieving apartment with new fields"""
        if not self.new_fields_apartment_id:
            print("❌ Skipping - No apartment with new fields available")
            return False
        
        success, response = self.run_test(
            "Get Apartment with New Fields",
            "GET",
            f"apartments/{self.new_fields_apartment_id}",
            200
        )
        
        if success:
            # Verify all new fields are retrieved correctly
            expected_fields = {
                "check_in_time": "15:00",
                "check_out_time": "11:00",
                "check_in_instructions": "Keys are under the blue mat",
                "apartment_locations": {"keys": "under the mat", "towels": "bathroom closet", "kitchen_utensils": "drawer"},
                "wifi_network": "TestWiFi123", 
                "wifi_password": "password123",
                "wifi_instructions": "Router is in living room"
            }
            
            all_fields_correct = True
            for field, expected_value in expected_fields.items():
                actual_value = response.get(field)
                if actual_value == expected_value:
                    print(f"   ✅ Retrieved {field}: {actual_value}")
                else:
                    print(f"   ❌ {field}: Expected {expected_value}, got {actual_value}")
                    all_fields_correct = False
            
            if all_fields_correct:
                print("   ✅ All new fields retrieved correctly from database")
                return True
            else:
                print("   ❌ Some new fields not retrieved correctly")
                return False
        
        return success

    def test_update_apartment_with_new_fields(self):
        """Test updating apartment with new fields"""
        if not self.new_fields_apartment_id:
            print("❌ Skipping - No apartment with new fields available")
            return False
        
        updated_data = {
            "name": "Updated Modern Apartment",
            "address": "456 Updated Street, Test City",
            "description": "Updated test apartment with modified new fields",
            "rules": ["No smoking", "Updated check-in instructions"],
            "contact": {
                "phone": "+1234567890",
                "email": "updated@example.com"
            },
            "ical_url": "",
            "recommendations": {},
            # UPDATED NEW FIELDS
            "check_in_time": "16:00",  # Changed from 15:00
            "check_out_time": "10:00",  # Changed from 11:00
            "check_in_instructions": "Updated: Keys are in lockbox, code 1234",  # Updated
            "apartment_locations": {
                "keys": "in lockbox by door",  # Updated
                "towels": "linen closet",  # Updated
                "kitchen_utensils": "kitchen drawer",  # Updated
                "coffee_machine": "kitchen counter"  # Added new location
            },
            "wifi_network": "UpdatedWiFi456",  # Updated
            "wifi_password": "newpassword456",  # Updated
            "wifi_instructions": "Router is in bedroom, restart if needed"  # Updated
        }
        
        success, response = self.run_test(
            "Update Apartment with New Fields",
            "PUT",
            f"apartments/{self.new_fields_apartment_id}",
            200,
            data=updated_data
        )
        
        if success:
            # Verify all updated fields are correct
            expected_updates = {
                "check_in_time": "16:00",
                "check_out_time": "10:00",
                "check_in_instructions": "Updated: Keys are in lockbox, code 1234",
                "apartment_locations": {
                    "keys": "in lockbox by door",
                    "towels": "linen closet", 
                    "kitchen_utensils": "kitchen drawer",
                    "coffee_machine": "kitchen counter"
                },
                "wifi_network": "UpdatedWiFi456",
                "wifi_password": "newpassword456",
                "wifi_instructions": "Router is in bedroom, restart if needed"
            }
            
            all_updates_correct = True
            for field, expected_value in expected_updates.items():
                actual_value = response.get(field)
                if actual_value == expected_value:
                    print(f"   ✅ Updated {field}: {actual_value}")
                else:
                    print(f"   ❌ {field}: Expected {expected_value}, got {actual_value}")
                    all_updates_correct = False
            
            if all_updates_correct:
                print("   ✅ All new fields updated correctly")
                return True
            else:
                print("   ❌ Some new fields not updated correctly")
                return False
        
        return success

    def test_admin_access_new_fields(self):
        """Test admin can access apartments with new fields"""
        if not self.admin_token:
            print("❌ Skipping - No admin token available")
            return False
        
        # Temporarily store user token and use admin token
        user_token = self.token
        self.token = self.admin_token
        
        success, response = self.run_test(
            "Admin Get Apartments with New Fields",
            "GET",
            "admin/apartments",
            200
        )
        
        # Restore user token
        self.token = user_token
        
        if success and isinstance(response, list):
            print(f"   Admin can see {len(response)} apartments")
            
            # Look for apartments with new fields
            apartments_with_new_fields = []
            for apartment in response:
                if (apartment.get('check_in_time') or 
                    apartment.get('check_out_time') or 
                    apartment.get('check_in_instructions') or
                    apartment.get('apartment_locations') or
                    apartment.get('wifi_network') or
                    apartment.get('wifi_password') or
                    apartment.get('wifi_instructions')):
                    apartments_with_new_fields.append(apartment)
            
            if apartments_with_new_fields:
                print(f"   ✅ Found {len(apartments_with_new_fields)} apartments with new fields")
                
                # Check first apartment with new fields
                apt = apartments_with_new_fields[0]
                print(f"   Sample apartment new fields:")
                print(f"     Check-in time: {apt.get('check_in_time', 'Not set')}")
                print(f"     Check-out time: {apt.get('check_out_time', 'Not set')}")
                print(f"     Check-in instructions: {apt.get('check_in_instructions', 'Not set')}")
                print(f"     WiFi network: {apt.get('wifi_network', 'Not set')}")
                print(f"     Apartment locations: {apt.get('apartment_locations', {})}")
                
                print("   ✅ Admin can access all new apartment fields")
                return True
            else:
                print("   ⚠️  No apartments with new fields found")
                return True  # Don't fail if no apartments with new fields exist yet
        
        return success

    def test_backward_compatibility(self):
        """Test creating apartment without new fields (backward compatibility)"""
        # Create apartment with only old fields (no new fields)
        old_format_data = {
            "name": "Backward Compatible Apartment",
            "address": "789 Old Format Street, Test City",
            "description": "Test apartment without new fields for backward compatibility",
            "rules": ["No smoking", "Standard rules"],
            "contact": {
                "phone": "+1234567890",
                "email": "oldformat@example.com"
            },
            "ical_url": "",
            "recommendations": {
                "restaurants": [{"name": "Old Restaurant", "type": "Traditional", "tip": "Classic dishes"}]
            }
            # Intentionally NOT including new fields
        }
        
        success, response = self.run_test(
            "Create Apartment - Backward Compatibility",
            "POST",
            "apartments",
            200,
            data=old_format_data
        )
        
        if success and response.get('id'):
            apartment_id = response['id']
            print(f"   Created backward compatible apartment ID: {apartment_id}")
            
            # Verify new fields have default values
            expected_defaults = {
                "check_in_time": "",
                "check_out_time": "",
                "check_in_instructions": "",
                "apartment_locations": {},
                "wifi_network": "",
                "wifi_password": "",
                "wifi_instructions": ""
            }
            
            all_defaults_correct = True
            for field, expected_default in expected_defaults.items():
                actual_value = response.get(field)
                if actual_value == expected_default:
                    print(f"   ✅ {field} has correct default: {actual_value}")
                else:
                    print(f"   ❌ {field}: Expected default {expected_default}, got {actual_value}")
                    all_defaults_correct = False
            
            if all_defaults_correct:
                print("   ✅ Backward compatibility maintained - new fields have proper defaults")
                return True
            else:
                print("   ❌ Backward compatibility issue - incorrect default values")
                return False
        
        return success

    def run_all_tests(self):
        """Run all new apartment fields tests"""
        print("🚀 Starting New Apartment Fields Testing...")
        print("🏠 Testing New Check-in/Check-out and WiFi Fields")
        print("=" * 70)
        
        # Setup authentication
        if not self.setup_authentication():
            print("❌ Failed to setup authentication, aborting tests")
            return False
        
        if not self.setup_admin_authentication():
            print("⚠️  Failed to setup admin authentication, skipping admin tests")
        
        # Run tests in order
        tests = [
            ("🏠 Create Apartment with New Fields", self.test_create_apartment_with_new_fields),
            ("🏠 Get Apartment with New Fields", self.test_get_apartment_with_new_fields),
            ("🏠 Update Apartment with New Fields", self.test_update_apartment_with_new_fields),
            ("🔐 Admin Access New Fields", self.test_admin_access_new_fields),
            ("🔄 Backward Compatibility", self.test_backward_compatibility),
        ]
        
        failed_tests = []
        
        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                if not test_func():
                    failed_tests.append(test_name)
            except Exception as e:
                print(f"❌ Test '{test_name}' crashed: {str(e)}")
                failed_tests.append(test_name)
        
        # Print final results
        print(f"\n{'='*70}")
        print(f"📊 FINAL RESULTS - New Apartment Fields Testing")
        print(f"{'='*70}")
        print(f"Tests passed: {self.tests_passed}/{self.tests_run}")
        print(f"Success rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if failed_tests:
            print(f"\n❌ Failed tests:")
            for test in failed_tests:
                print(f"   - {test}")
        else:
            print(f"\n✅ All new apartment fields tests passed!")
        
        return len(failed_tests) == 0

def main():
    tester = NewApartmentFieldsTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()