#!/usr/bin/env python3
"""
Comprehensive Backend Testing for MyHostIQ
Based on test_result.md requirements and review request
"""

import requests
import json
import time
import sys
from datetime import datetime

class ComprehensiveBackendTester:
    def __init__(self):
        self.base_url = "https://thesis-deployment.preview.emergentagent.com"
        self.api_url = f"{self.base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.token = None
        self.admin_token = None
        self.apartment_id = None
        
        # Test credentials
        self.test_user = {
            "email": "comprehensive.test@example.com",
            "full_name": "Comprehensive Tester",
            "password": "testpass123"
        }
        
        self.admin_credentials = {
            "username": "myhomeiq_admin",
            "password": "Admin123!MyHomeIQ"
        }

    def log(self, message, level="INFO"):
        """Log messages with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30, use_auth=True, use_admin_auth=False):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'}
        
        if use_admin_auth and self.admin_token:
            headers['Authorization'] = f'Bearer {self.admin_token}'
        elif use_auth and self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        self.log(f"Testing {name}...")
        
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
                self.log(f"✅ {name} - Status: {response.status_code}", "PASS")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                self.log(f"❌ {name} - Expected {expected_status}, got {response.status_code}", "FAIL")
                try:
                    error_data = response.json()
                    self.log(f"   Error: {error_data}", "ERROR")
                except:
                    self.log(f"   Error: {response.text}", "ERROR")
                return False, {}

        except Exception as e:
            self.log(f"❌ {name} - Exception: {str(e)}", "FAIL")
            return False, {}

    def setup_authentication(self):
        """Setup user and admin authentication"""
        self.log("Setting up authentication...")
        
        # User authentication
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
            self.log(f"✅ User registered with token: {self.token[:20]}...")
        else:
            # Try login if user already exists
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
                self.log(f"✅ User logged in with token: {self.token[:20]}...")
        
        # Admin authentication
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
            self.log(f"✅ Admin logged in with token: {self.admin_token[:20]}...")
        
        return self.token is not None and self.admin_token is not None

    def test_authentication_flows(self):
        """Test authentication and session management"""
        self.log("🔐 Testing Authentication Flows...")
        
        tests_passed = 0
        total_tests = 0
        
        # Test user registration with validation
        total_tests += 1
        test_user_invalid = {
            "email": "invalid-email",
            "full_name": "",
            "password": "123"
        }
        
        success, response = self.run_test(
            "User Registration - Invalid Data",
            "POST",
            "auth/register",
            422,
            data=test_user_invalid,
            use_auth=False
        )
        if success:
            tests_passed += 1
        
        # Test login with incorrect credentials
        total_tests += 1
        invalid_login = {
            "email": self.test_user["email"],
            "password": "wrongpassword"
        }
        
        success, response = self.run_test(
            "User Login - Invalid Credentials",
            "POST",
            "auth/login",
            401,
            data=invalid_login,
            use_auth=False
        )
        if success:
            tests_passed += 1
        
        # Test JWT token validation
        total_tests += 1
        success, response = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200
        )
        if success and response.get('email') == self.test_user['email']:
            tests_passed += 1
            self.log(f"   User profile: {response.get('email')}")
        
        # Test admin login
        total_tests += 1
        success, response = self.run_test(
            "Admin Login - Correct Credentials",
            "POST",
            "admin/login",
            200,
            data=self.admin_credentials,
            use_auth=False
        )
        if success and response.get('access_token'):
            tests_passed += 1
        
        # Test admin login with wrong credentials
        total_tests += 1
        wrong_admin = {
            "username": "wrong_admin",
            "password": "wrongpass"
        }
        
        success, response = self.run_test(
            "Admin Login - Wrong Credentials",
            "POST",
            "admin/login",
            401,
            data=wrong_admin,
            use_auth=False
        )
        if success:
            tests_passed += 1
        
        self.log(f"Authentication Tests: {tests_passed}/{total_tests} passed")
        return tests_passed, total_tests

    def test_apartment_management(self):
        """Test apartment CRUD operations"""
        self.log("🏠 Testing Apartment Management...")
        
        tests_passed = 0
        total_tests = 0
        
        # Create apartment with comprehensive data
        total_tests += 1
        apartment_data = {
            "name": "Test Comprehensive Apartment",
            "address": "Test Street 123, Sarajevo, Bosnia and Herzegovina",
            "description": "Comprehensive test apartment with all features",
            "rules": [
                "No smoking",
                "Check-in after 3 PM",
                "Check-out before 11 AM"
            ],
            "contact": {
                "phone": "+387 61 123 456",
                "email": "host@test.com"
            },
            "check_in_time": "15:00",
            "check_out_time": "11:00",
            "check_in_instructions": "Use lockbox code 1234",
            "wifi_network": "TestWiFi",
            "wifi_password": "TestPass123",
            "wifi_instructions": "Connect and enter password",
            "apartment_locations": {
                "keys": "Lockbox by door",
                "towels": "Bathroom closet",
                "kitchen_utensils": "Kitchen drawers"
            },
            "recommendations": {
                "restaurants": [
                    {
                        "name": "Test Restaurant",
                        "type": "Local",
                        "location": "Test Location",
                        "tip": "Great food"
                    }
                ],
                "hidden_gems": [
                    {
                        "name": "Test Attraction",
                        "location": "Test Location",
                        "tip": "Must see"
                    }
                ]
            }
        }
        
        success, response = self.run_test(
            "Create Apartment",
            "POST",
            "apartments",
            200,
            data=apartment_data
        )
        
        if success and response.get('id'):
            self.apartment_id = response['id']
            tests_passed += 1
            self.log(f"   Created apartment: {self.apartment_id}")
        
        # Get apartment
        total_tests += 1
        if self.apartment_id:
            success, response = self.run_test(
                "Get Apartment",
                "GET",
                f"apartments/{self.apartment_id}",
                200
            )
            
            if success:
                # Check if all new fields are present
                required_fields = [
                    'check_in_time', 'check_out_time', 'check_in_instructions',
                    'wifi_network', 'wifi_password', 'apartment_locations'
                ]
                
                missing_fields = [field for field in required_fields if field not in response]
                if not missing_fields:
                    tests_passed += 1
                    self.log("   ✅ All new apartment fields present")
                else:
                    self.log(f"   ❌ Missing fields: {missing_fields}")
        
        # Update apartment
        total_tests += 1
        if self.apartment_id:
            update_data = apartment_data.copy()
            update_data['name'] = "Updated Test Apartment"
            update_data['wifi_password'] = "UpdatedPass456"
            
            success, response = self.run_test(
                "Update Apartment",
                "PUT",
                f"apartments/{self.apartment_id}",
                200,
                data=update_data
            )
            
            if success and response.get('name') == "Updated Test Apartment":
                tests_passed += 1
        
        # Test public apartment endpoint
        total_tests += 1
        if self.apartment_id:
            success, response = self.run_test(
                "Public Apartment Endpoint",
                "GET",
                f"public/apartments/{self.apartment_id}",
                200,
                use_auth=False
            )
            
            if success:
                # Check if branding data includes ai_assistant_name
                branding = response.get('branding', {})
                if 'ai_assistant_name' in branding:
                    tests_passed += 1
                    self.log(f"   ✅ AI assistant name: {branding['ai_assistant_name']}")
                else:
                    self.log("   ❌ AI assistant name missing from branding")
        
        self.log(f"Apartment Management Tests: {tests_passed}/{total_tests} passed")
        return tests_passed, total_tests

    def test_ai_chat_functionality(self):
        """Test AI chat functionality - CRITICAL"""
        self.log("🤖 Testing AI Chat Functionality...")
        
        if not self.apartment_id:
            self.log("❌ No apartment ID available for chat testing")
            return 0, 1
        
        tests_passed = 0
        total_tests = 0
        
        # Test basic chat
        total_tests += 1
        success, response = self.run_test(
            "AI Chat - Basic Question",
            "POST",
            "chat",
            200,
            data={
                "apartment_id": self.apartment_id,
                "message": "What's the WiFi password?",
                "session_id": f"test_{int(time.time())}"
            },
            timeout=60,
            use_auth=False
        )
        
        if success:
            ai_response = response.get('response', '')
            if 'TestPass123' in ai_response or 'wifi' in ai_response.lower():
                tests_passed += 1
                self.log(f"   ✅ AI provided WiFi info: {ai_response[:100]}...")
            else:
                self.log(f"   ❌ AI didn't provide WiFi info: {ai_response[:100]}...")
        
        # Test context tracking
        total_tests += 1
        session_id = f"context_test_{int(time.time())}"
        
        # First message
        success1, response1 = self.run_test(
            "Context Test - First Message",
            "POST",
            "chat",
            200,
            data={
                "apartment_id": self.apartment_id,
                "message": "When is check-in?",
                "session_id": session_id
            },
            timeout=60,
            use_auth=False
        )
        
        time.sleep(2)
        
        # Follow-up message
        success2, response2 = self.run_test(
            "Context Test - Follow-up",
            "POST",
            "chat",
            200,
            data={
                "apartment_id": self.apartment_id,
                "message": "How?",
                "session_id": session_id
            },
            timeout=60,
            use_auth=False
        )
        
        if success1 and success2:
            ai_response2 = response2.get('response', '')
            context_indicators = ['lockbox', 'code', '1234', 'check-in', 'instructions']
            
            if any(indicator.lower() in ai_response2.lower() for indicator in context_indicators):
                tests_passed += 1
                self.log("   ✅ Context tracking working")
            else:
                self.log("   ❌ Context tracking failed")
        
        # Test scope control - local city
        total_tests += 1
        success, response = self.run_test(
            "Scope Test - Local City",
            "POST",
            "chat",
            200,
            data={
                "apartment_id": self.apartment_id,
                "message": "Best restaurants in Sarajevo?",
                "session_id": f"scope_test_{int(time.time())}"
            },
            timeout=60,
            use_auth=False
        )
        
        if success:
            ai_response = response.get('response', '')
            # Should NOT be a fallback for Sarajevo
            fallback_indicators = ['specifically designed', 'other cities', 'tourism websites']
            is_fallback = any(indicator.lower() in ai_response.lower() for indicator in fallback_indicators)
            
            if not is_fallback:
                tests_passed += 1
                self.log("   ✅ Local city questions working")
            else:
                self.log("   ❌ Local city questions triggering fallback")
        
        # Test scope control - other cities
        total_tests += 1
        success, response = self.run_test(
            "Scope Test - Other City",
            "POST",
            "chat",
            200,
            data={
                "apartment_id": self.apartment_id,
                "message": "Best restaurants in Zagreb?",
                "session_id": f"scope_test2_{int(time.time())}"
            },
            timeout=60,
            use_auth=False
        )
        
        if success:
            ai_response = response.get('response', '')
            # Should be a fallback for Zagreb
            fallback_indicators = ['specifically designed', 'other cities', 'tourism websites']
            is_fallback = any(indicator.lower() in ai_response.lower() for indicator in fallback_indicators)
            
            if is_fallback:
                tests_passed += 1
                self.log("   ✅ Out-of-scope questions triggering fallback")
            else:
                self.log("   ❌ Out-of-scope questions not triggering fallback")
        
        # Test multilingual fallback
        total_tests += 1
        success, response = self.run_test(
            "Multilingual Fallback Test",
            "POST",
            "chat",
            200,
            data={
                "apartment_id": self.apartment_id,
                "message": "¿Mejores restaurantes en Madrid?",
                "session_id": f"multilingual_test_{int(time.time())}"
            },
            timeout=60,
            use_auth=False
        )
        
        if success:
            ai_response = response.get('response', '')
            spanish_indicators = ['específicamente diseñado', 'sarajevo', 'otras ciudades']
            
            if any(indicator.lower() in ai_response.lower() for indicator in spanish_indicators):
                tests_passed += 1
                self.log("   ✅ Multilingual fallback working")
            else:
                self.log("   ❌ Multilingual fallback not working")
        
        self.log(f"AI Chat Tests: {tests_passed}/{total_tests} passed")
        return tests_passed, total_tests

    def test_admin_functionality(self):
        """Test admin protected endpoints"""
        self.log("👑 Testing Admin Functionality...")
        
        tests_passed = 0
        total_tests = 0
        
        # Test admin users endpoint
        total_tests += 1
        success, response = self.run_test(
            "Admin - Get Users",
            "GET",
            "admin/users",
            200,
            use_admin_auth=True
        )
        
        if success and isinstance(response, list):
            tests_passed += 1
            self.log(f"   ✅ Found {len(response)} users")
        
        # Test admin apartments endpoint
        total_tests += 1
        success, response = self.run_test(
            "Admin - Get Apartments",
            "GET",
            "admin/apartments",
            200,
            use_admin_auth=True
        )
        
        if success and isinstance(response, list):
            tests_passed += 1
            self.log(f"   ✅ Found {len(response)} apartments")
        
        # Test admin stats endpoint
        total_tests += 1
        success, response = self.run_test(
            "Admin - Get Stats",
            "GET",
            "admin/stats",
            200,
            use_admin_auth=True
        )
        
        if success and 'users' in response and 'apartments' in response:
            tests_passed += 1
            self.log(f"   ✅ Stats: {response.get('users', 0)} users, {response.get('apartments', 0)} apartments")
        
        # Test non-admin access to admin endpoints
        total_tests += 1
        success, response = self.run_test(
            "Non-Admin Access Test",
            "GET",
            "admin/users",
            403,
            use_auth=True,
            use_admin_auth=False
        )
        
        if success:
            tests_passed += 1
            self.log("   ✅ Non-admin properly blocked from admin endpoints")
        
        self.log(f"Admin Tests: {tests_passed}/{total_tests} passed")
        return tests_passed, total_tests

    def test_property_import(self):
        """Test property import functionality"""
        self.log("🏗️ Testing Property Import...")
        
        tests_passed = 0
        total_tests = 0
        
        # Test Airbnb import
        total_tests += 1
        airbnb_url = "https://www.airbnb.com/rooms/44732428"
        
        success, response = self.run_test(
            "Property Import - Airbnb",
            "POST",
            "apartments/import-from-url",
            200,
            data={"url": airbnb_url},
            timeout=60
        )
        
        if success:
            data = response.get('data', {})
            if data.get('name') and data.get('rules'):
                tests_passed += 1
                self.log(f"   ✅ Airbnb import: {data.get('name', 'Unknown')}")
            else:
                self.log("   ❌ Airbnb import missing data")
        
        # Test Booking.com import
        total_tests += 1
        booking_url = "https://www.booking.com/hotel/ba/test-property.html"
        
        success, response = self.run_test(
            "Property Import - Booking.com",
            "POST",
            "apartments/import-from-url",
            200,
            data={"url": booking_url},
            timeout=60
        )
        
        if success:
            data = response.get('data', {})
            if data.get('name') and 'Booking.com' in data.get('name', ''):
                tests_passed += 1
                self.log(f"   ✅ Booking.com import: {data.get('name', 'Unknown')}")
            else:
                self.log("   ❌ Booking.com import failed")
        
        # Test invalid URL
        total_tests += 1
        success, response = self.run_test(
            "Property Import - Invalid URL",
            "POST",
            "apartments/import-from-url",
            400,
            data={"url": "invalid-url"}
        )
        
        if success:
            tests_passed += 1
            self.log("   ✅ Invalid URL properly rejected")
        
        self.log(f"Property Import Tests: {tests_passed}/{total_tests} passed")
        return tests_passed, total_tests

    def test_email_functionality(self):
        """Test email credentials and functionality"""
        self.log("📧 Testing Email Functionality...")
        
        tests_passed = 0
        total_tests = 0
        
        # Test get email credentials (should be empty initially)
        total_tests += 1
        success, response = self.run_test(
            "Get Email Credentials",
            "GET",
            "auth/email-credentials",
            200
        )
        
        if success and response is None:
            tests_passed += 1
            self.log("   ✅ No email credentials configured (expected)")
        
        # Test create email credentials with invalid data
        total_tests += 1
        invalid_creds = {
            "email": "test@gmail.com",
            "password": "fake_password",
            "smtp_server": "",
            "smtp_port": 587
        }
        
        success, response = self.run_test(
            "Create Email Credentials - Invalid",
            "POST",
            "auth/email-credentials",
            400,
            data=invalid_creds
        )
        
        if success:
            tests_passed += 1
            self.log("   ✅ Invalid email credentials properly rejected")
        
        # Test email test functionality
        total_tests += 1
        success, response = self.run_test(
            "Test Email - No Credentials",
            "POST",
            "auth/test-email",
            404
        )
        
        if success:
            tests_passed += 1
            self.log("   ✅ Email test properly requires credentials")
        
        self.log(f"Email Tests: {tests_passed}/{total_tests} passed")
        return tests_passed, total_tests

    def test_payment_simulation(self):
        """Test payment simulation"""
        self.log("💳 Testing Payment Simulation...")
        
        tests_passed = 0
        total_tests = 0
        
        # Test get payment plans
        total_tests += 1
        success, response = self.run_test(
            "Get Payment Plans",
            "GET",
            "payments/plans",
            200,
            use_auth=False
        )
        
        if success and response.get('plans'):
            plans = response['plans']
            if len(plans) >= 3:
                tests_passed += 1
                self.log(f"   ✅ Found {len(plans)} payment plans")
            else:
                self.log(f"   ❌ Expected at least 3 plans, found {len(plans)}")
        
        # Test payment simulation
        total_tests += 1
        payment_data = {
            "amount": 29.0,
            "currency": "USD",
            "plan_name": "Starter",
            "apartment_count": 2
        }
        
        success, response = self.run_test(
            "Simulate Payment",
            "POST",
            "payments/simulate",
            200,
            data=payment_data
        )
        
        if success and response.get('transaction_id', '').startswith('sim_'):
            tests_passed += 1
            self.log(f"   ✅ Payment simulation: {response.get('transaction_id')}")
        
        self.log(f"Payment Tests: {tests_passed}/{total_tests} passed")
        return tests_passed, total_tests

    def test_ai_powered_endpoints(self):
        """Test AI-powered analytics endpoints"""
        self.log("🧠 Testing AI-Powered Endpoints...")
        
        if not self.apartment_id:
            self.log("❌ No apartment ID available for AI testing")
            return 0, 1
        
        tests_passed = 0
        total_tests = 0
        
        # Test AI insights endpoint
        total_tests += 1
        success, response = self.run_test(
            "AI Insights",
            "GET",
            f"analytics/insights/{self.apartment_id}",
            200,
            timeout=60
        )
        
        if success:
            required_fields = ['insights', 'recommendations', 'performance_score', 'apartment_id']
            missing_fields = [field for field in required_fields if field not in response]
            
            if not missing_fields:
                tests_passed += 1
                self.log(f"   ✅ AI insights generated with score: {response.get('performance_score')}")
            else:
                self.log(f"   ❌ Missing fields: {missing_fields}")
        
        # Test question normalization endpoint
        total_tests += 1
        success, response = self.run_test(
            "Question Normalization",
            "GET",
            f"analytics/normalized-questions/{self.apartment_id}",
            200,
            timeout=60
        )
        
        if success:
            required_fields = ['normalized_questions', 'total_questions', 'groups_created']
            missing_fields = [field for field in required_fields if field not in response]
            
            if not missing_fields:
                tests_passed += 1
                self.log(f"   ✅ Question normalization: {response.get('groups_created')} groups")
            else:
                self.log(f"   ❌ Missing fields: {missing_fields}")
        
        # Test detailed iCal test endpoint
        total_tests += 1
        success, response = self.run_test(
            "Detailed iCal Test",
            "POST",
            f"ical/detailed-test/{self.apartment_id}",
            200,
            timeout=60
        )
        
        if success:
            required_fields = ['test_status', 'apartment_id', 'steps', 'summary']
            missing_fields = [field for field in required_fields if field not in response]
            
            if not missing_fields:
                tests_passed += 1
                self.log(f"   ✅ iCal test: {response.get('test_status')}")
            else:
                self.log(f"   ❌ Missing fields: {missing_fields}")
        
        self.log(f"AI-Powered Tests: {tests_passed}/{total_tests} passed")
        return tests_passed, total_tests

    def run_comprehensive_tests(self):
        """Run all comprehensive backend tests"""
        self.log("🚀 Starting Comprehensive Backend Testing...")
        self.log("=" * 80)
        
        # Setup authentication
        if not self.setup_authentication():
            self.log("❌ Failed to setup authentication", "ERROR")
            return False
        
        # Run all test categories
        test_categories = [
            ("Authentication Flows", self.test_authentication_flows),
            ("Apartment Management", self.test_apartment_management),
            ("AI Chat Functionality", self.test_ai_chat_functionality),
            ("Admin Functionality", self.test_admin_functionality),
            ("Property Import", self.test_property_import),
            ("Email Functionality", self.test_email_functionality),
            ("Payment Simulation", self.test_payment_simulation),
            ("AI-Powered Endpoints", self.test_ai_powered_endpoints),
        ]
        
        all_results = {}
        total_passed = 0
        total_tests = 0
        
        for category_name, test_func in test_categories:
            self.log(f"\n{'='*20} {category_name} {'='*20}")
            try:
                passed, tests = test_func()
                all_results[category_name] = (passed, tests)
                total_passed += passed
                total_tests += tests
                
                success_rate = (passed / tests) * 100 if tests > 0 else 0
                status = "✅ PASS" if success_rate >= 80 else "⚠️ PARTIAL" if success_rate >= 50 else "❌ FAIL"
                self.log(f"{status} {category_name}: {passed}/{tests} ({success_rate:.1f}%)")
                
            except Exception as e:
                self.log(f"❌ {category_name} ERROR: {str(e)}", "ERROR")
                all_results[category_name] = (0, 1)
                total_tests += 1
        
        # Final summary
        self.log("\n" + "="*80)
        self.log("🏁 COMPREHENSIVE BACKEND TEST SUMMARY")
        self.log("="*80)
        
        overall_success_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0
        api_success_rate = (self.tests_passed / self.tests_run) * 100 if self.tests_run > 0 else 0
        
        self.log(f"Total API Calls: {self.tests_run}")
        self.log(f"API Calls Passed: {self.tests_passed}")
        self.log(f"API Success Rate: {api_success_rate:.1f}%")
        self.log(f"Feature Tests: {total_passed}/{total_tests}")
        self.log(f"Feature Success Rate: {overall_success_rate:.1f}%")
        
        # Detailed results by category
        self.log("\nDetailed Results:")
        for category, (passed, tests) in all_results.items():
            success_rate = (passed / tests) * 100 if tests > 0 else 0
            status = "✅" if success_rate >= 80 else "⚠️" if success_rate >= 50 else "❌"
            self.log(f"  {status} {category}: {passed}/{tests} ({success_rate:.1f}%)")
        
        # Critical issues
        critical_issues = []
        
        # Check AI chat functionality
        ai_chat_passed, ai_chat_total = all_results.get("AI Chat Functionality", (0, 1))
        if (ai_chat_passed / ai_chat_total) < 0.8:
            critical_issues.append("AI Chat functionality not working properly")
        
        # Check authentication
        auth_passed, auth_total = all_results.get("Authentication Flows", (0, 1))
        if (auth_passed / auth_total) < 0.8:
            critical_issues.append("Authentication flows have issues")
        
        # Check admin functionality
        admin_passed, admin_total = all_results.get("Admin Functionality", (0, 1))
        if (admin_passed / admin_total) < 0.8:
            critical_issues.append("Admin functionality not working properly")
        
        if critical_issues:
            self.log("\n🚨 CRITICAL ISSUES FOUND:")
            for issue in critical_issues:
                self.log(f"  ❌ {issue}")
        else:
            self.log("\n🎉 All critical backend functionality working!")
        
        return overall_success_rate >= 80.0

def main():
    tester = ComprehensiveBackendTester()
    success = tester.run_comprehensive_tests()
    
    if success:
        print("\n🎉 COMPREHENSIVE BACKEND TESTING COMPLETED SUCCESSFULLY")
        sys.exit(0)
    else:
        print("\n❌ COMPREHENSIVE BACKEND TESTING FAILED - ISSUES FOUND")
        sys.exit(1)

if __name__ == "__main__":
    main()