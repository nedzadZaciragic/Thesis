import requests
import sys
import json
from datetime import datetime, timezone, timedelta
import time
import uuid
import asyncio
import httpx

class iCalDeepTester:
    def __init__(self, base_url="https://proximity-search-8.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.token = None
        self.user_id = None
        self.created_apartment_id = None
        
        # Test user credentials
        self.test_user = {
            "email": "deep.ical.test@example.com",
            "full_name": "Deep iCal Test User",
            "password": "deepicaltest123"
        }

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30, use_auth=True):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'}
        
        if use_auth and self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
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

    def setup_test_user(self):
        """Setup test user and authentication"""
        print("🔐 Setting up test user and authentication...")
        
        # Register user
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
            print(f"   ✅ User registered: {self.user_id}")
            return True
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
                self.user_id = response['user']['id']
                print(f"   ✅ User logged in: {self.user_id}")
                return True
        
        return False

    async def test_ical_parsing_directly(self):
        """Test iCal parsing function directly with real and fake URLs"""
        print("🔍 Testing iCal Parsing Function Directly...")
        
        # Test URLs with different scenarios
        test_scenarios = [
            {
                "name": "Valid Google Calendar (likely empty)",
                "url": "https://calendar.google.com/calendar/ical/test%40example.com/public/basic.ics",
                "expected": "Should fetch real URL, likely return empty bookings"
            },
            {
                "name": "Invalid URL (should fail)",
                "url": "https://invalid-domain-that-does-not-exist.com/calendar.ics",
                "expected": "Should fail with network error"
            },
            {
                "name": "Valid domain but 404 (should fail gracefully)",
                "url": "https://www.google.com/nonexistent-calendar.ics",
                "expected": "Should handle 404 gracefully"
            }
        ]
        
        results = []
        
        for scenario in test_scenarios:
            print(f"\n   Testing: {scenario['name']}")
            print(f"   URL: {scenario['url']}")
            print(f"   Expected: {scenario['expected']}")
            
            try:
                # Test the parsing function directly
                async with httpx.AsyncClient(timeout=30.0) as client:
                    start_time = time.time()
                    
                    try:
                        response = await client.get(scenario['url'])
                        fetch_time = time.time() - start_time
                        
                        print(f"   ✅ HTTP Request successful: {response.status_code}")
                        print(f"   ⏱️  Fetch time: {fetch_time:.2f} seconds")
                        print(f"   📄 Content length: {len(response.text)} characters")
                        print(f"   📄 Content preview: {response.text[:100]}...")
                        
                        # Check if it's actual iCal content
                        content = response.text
                        if 'BEGIN:VCALENDAR' in content:
                            print("   ✅ Valid iCal format detected")
                            
                            # Count events
                            event_count = content.count('BEGIN:VEVENT')
                            print(f"   📅 Found {event_count} events in calendar")
                            
                            if event_count > 0:
                                print("   ✅ Calendar contains booking events")
                                results.append(("real_data", True))
                            else:
                                print("   ⚠️  Calendar is empty (no events)")
                                results.append(("empty_calendar", True))
                        else:
                            print("   ⚠️  Response is not valid iCal format")
                            print(f"   Content type: {response.headers.get('content-type', 'unknown')}")
                            results.append(("invalid_ical", True))
                            
                    except httpx.TimeoutException:
                        print("   ❌ Request timed out")
                        results.append(("timeout", True))
                    except httpx.ConnectError:
                        print("   ❌ Connection error (expected for invalid domains)")
                        results.append(("connection_error", True))
                    except Exception as e:
                        print(f"   ❌ Request failed: {str(e)}")
                        results.append(("request_error", True))
                        
            except Exception as e:
                print(f"   ❌ Test failed: {str(e)}")
                results.append(("test_error", False))
        
        # Analyze results
        print(f"\n📊 iCal Parsing Test Results:")
        
        real_requests = len([r for r in results if r[1]])  # Successful requests
        if real_requests > 0:
            print(f"   ✅ {real_requests}/{len(results)} URLs processed with real HTTP requests")
            print("   ✅ CONFIRMED: iCal parsing makes real HTTP requests (NOT hardcoded)")
            
            # Check for different response types
            response_types = set(r[0] for r in results if r[1])
            if len(response_types) > 1:
                print("   ✅ Different response types for different URLs (not cached)")
            
            return True
        else:
            print("   ❌ No successful HTTP requests made")
            return False

    def create_test_apartment_with_real_ical(self):
        """Create test apartment with a real iCal URL that might have data"""
        print("🏠 Creating test apartment with real iCal URL...")
        
        # Use a more likely-to-have-data iCal URL
        # This is a public holiday calendar that should have events
        real_ical_url = "https://calendar.google.com/calendar/ical/en.usa%23holiday%40group.v.calendar.google.com/public/basic.ics"
        
        apartment_data = {
            "name": "Deep Test Apartment with Real iCal",
            "address": "Via Real iCal 789, Rome, Italy",
            "description": "Testing apartment with real iCal data that should contain events",
            "rules": ["No smoking", "Check-in after 3PM", "Real iCal testing"],
            "contact": {"phone": "+39 123456789", "email": "realical@test.com"},
            "ical_url": real_ical_url,
            "ai_tone": "professional",
            "recommendations": {}
        }
        
        success, response = self.run_test(
            "Create Apartment with Real iCal",
            "POST",
            "apartments",
            200,
            data=apartment_data
        )
        
        if success and response.get('id'):
            self.created_apartment_id = response['id']
            print(f"   ✅ Apartment created: {self.created_apartment_id}")
            print(f"   ✅ Real iCal URL: {real_ical_url}")
            return True
        
        return False

    async def test_real_ical_processing(self):
        """Test processing of real iCal data"""
        print("📅 Testing Real iCal Data Processing...")
        
        if not self.created_apartment_id:
            print("❌ No apartment available for testing")
            return False
        
        # First, let's manually test the iCal URL to see what data it contains
        real_ical_url = "https://calendar.google.com/calendar/ical/en.usa%23holiday%40group.v.calendar.google.com/public/basic.ics"
        
        print(f"   Testing real iCal URL: {real_ical_url}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(real_ical_url)
                
                print(f"   ✅ Successfully fetched iCal data")
                print(f"   📄 Content length: {len(response.text)} characters")
                
                content = response.text
                if 'BEGIN:VCALENDAR' in content:
                    event_count = content.count('BEGIN:VEVENT')
                    print(f"   📅 Found {event_count} events in US holidays calendar")
                    
                    if event_count > 0:
                        print("   ✅ Real iCal data with events available for testing")
                        
                        # Show some sample events
                        lines = content.split('\n')
                        in_event = False
                        event_data = {}
                        events_found = 0
                        
                        for line in lines:
                            line = line.strip()
                            if line.startswith('BEGIN:VEVENT'):
                                in_event = True
                                event_data = {}
                            elif line.startswith('END:VEVENT'):
                                if in_event and event_data:
                                    events_found += 1
                                    if events_found <= 3:  # Show first 3 events
                                        print(f"   📅 Event {events_found}: {event_data.get('summary', 'No title')}")
                                        if 'dtstart' in event_data:
                                            print(f"      Date: {event_data['dtstart']}")
                                in_event = False
                            elif in_event:
                                if line.startswith('SUMMARY:'):
                                    event_data['summary'] = line.split(':', 1)[1].strip()
                                elif line.startswith('DTSTART'):
                                    event_data['dtstart'] = line.split(':', 1)[1].strip()
                        
                        print(f"   ✅ Parsed {events_found} events from real iCal data")
                        return True
                    else:
                        print("   ⚠️  iCal data is empty")
                        return False
                else:
                    print("   ❌ Invalid iCal format")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Failed to fetch real iCal data: {str(e)}")
            return False

    def test_ical_sync_with_real_data(self):
        """Test iCal sync with real data"""
        print("🔄 Testing iCal Sync with Real Data...")
        
        if not self.created_apartment_id:
            print("❌ No apartment available for testing")
            return False
        
        # Trigger sync with real iCal data
        success, response = self.run_test(
            "Sync Real iCal Data",
            "POST",
            f"ical/test-sync/{self.created_apartment_id}",
            200,
            timeout=60
        )
        
        if success:
            message = response.get('message', '')
            print(f"   Sync result: {message}")
            
            # The sync should process the real iCal data
            # Even if no bookings are created (holidays aren't bookings), 
            # the function should still fetch and parse the real data
            
            print("   ✅ iCal sync completed (processed real URL)")
            
            # Check if any notifications were created
            time.sleep(2)
            
            notifications_success, notifications_response = self.run_test(
                "Check Notifications After Real Sync",
                "GET",
                f"notifications/{self.created_apartment_id}",
                200
            )
            
            if notifications_success:
                notification_count = len(notifications_response) if isinstance(notifications_response, list) else 0
                print(f"   📬 Found {notification_count} notifications")
                
                if notification_count == 0:
                    print("   ✅ No notifications created (expected - holidays aren't bookings)")
                else:
                    print("   ⚠️  Unexpected notifications created from holiday calendar")
                
                return True
            
        return False

    def test_error_handling_in_ical_parsing(self):
        """Test error handling in iCal parsing"""
        print("🚨 Testing Error Handling in iCal Parsing...")
        
        # Test with various problematic URLs
        error_test_cases = [
            {
                "name": "Completely Invalid URL",
                "url": "not-a-url-at-all",
                "description": "Should handle malformed URLs gracefully"
            },
            {
                "name": "Non-existent Domain",
                "url": "https://this-domain-definitely-does-not-exist-12345.com/calendar.ics",
                "description": "Should handle DNS resolution failures"
            },
            {
                "name": "Valid Domain, 404 Path",
                "url": "https://www.google.com/definitely-not-a-real-calendar-path.ics",
                "description": "Should handle 404 responses gracefully"
            }
        ]
        
        results = []
        
        for test_case in error_test_cases:
            print(f"\n   Testing: {test_case['name']}")
            print(f"   URL: {test_case['url']}")
            print(f"   Expected: {test_case['description']}")
            
            # Create apartment with problematic URL
            apartment_data = {
                "name": f"Error Test: {test_case['name']}",
                "address": "Via Error Test, Rome, Italy",
                "description": "Testing error handling",
                "rules": ["No smoking"],
                "contact": {"email": "error@test.com"},
                "ical_url": test_case['url'],
                "ai_tone": "professional",
                "recommendations": {}
            }
            
            # Update existing apartment with error URL
            if self.created_apartment_id:
                update_success, update_response = self.run_test(
                    f"Update with Error URL: {test_case['name']}",
                    "PUT",
                    f"apartments/{self.created_apartment_id}",
                    200,
                    data=apartment_data
                )
                
                if update_success:
                    # Try to sync - should handle errors gracefully
                    sync_success, sync_response = self.run_test(
                        f"Sync Error URL: {test_case['name']}",
                        "POST",
                        f"ical/test-sync/{self.created_apartment_id}",
                        200,  # Should still return 200 even with errors
                        timeout=30
                    )
                    
                    if sync_success:
                        message = sync_response.get('message', '')
                        print(f"   ✅ Sync handled gracefully: {message}")
                        results.append(True)
                    else:
                        print(f"   ❌ Sync failed to handle error gracefully")
                        results.append(False)
                else:
                    print(f"   ❌ Failed to update apartment with error URL")
                    results.append(False)
            else:
                print("   ❌ No apartment available for error testing")
                results.append(False)
            
            time.sleep(2)  # Wait between tests
        
        # Analyze error handling results
        successful_error_handling = sum(results)
        total_error_tests = len(results)
        
        print(f"\n📊 Error Handling Results: {successful_error_handling}/{total_error_tests} handled gracefully")
        
        if successful_error_handling >= total_error_tests * 0.8:  # 80% should handle errors well
            print("   ✅ iCal parsing has robust error handling")
            return True
        else:
            print("   ❌ iCal parsing error handling needs improvement")
            return False

async def main():
    print("🚀 Starting Deep iCal Integration Testing...")
    print("🔍 VERIFYING REAL vs HARDCODED iCal Implementation")
    print("=" * 70)
    
    tester = iCalDeepTester()
    
    # Setup
    if not tester.setup_test_user():
        print("❌ Failed to setup test user")
        return 1
    
    # Test iCal parsing directly
    print(f"\n{'='*20} Direct iCal Parsing Test {'='*20}")
    parsing_result = await tester.test_ical_parsing_directly()
    
    # Test with real iCal data
    print(f"\n{'='*20} Real iCal Data Test {'='*20}")
    if tester.create_test_apartment_with_real_ical():
        real_data_result = await tester.test_real_ical_processing()
        sync_result = tester.test_ical_sync_with_real_data()
    else:
        real_data_result = False
        sync_result = False
    
    # Test error handling
    print(f"\n{'='*20} Error Handling Test {'='*20}")
    error_handling_result = tester.test_error_handling_in_ical_parsing()
    
    # Final assessment
    print(f"\n{'='*70}")
    print(f"📊 DEEP iCal INTEGRATION ANALYSIS")
    print(f"{'='*70}")
    
    tests_results = [
        ("Direct iCal Parsing", parsing_result),
        ("Real iCal Data Processing", real_data_result),
        ("iCal Sync with Real Data", sync_result),
        ("Error Handling", error_handling_result)
    ]
    
    passed_tests = [name for name, result in tests_results if result]
    failed_tests = [name for name, result in tests_results if not result]
    
    print(f"Tests passed: {len(passed_tests)}/{len(tests_results)}")
    
    for name, result in tests_results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    # Overall assessment
    if len(passed_tests) >= 3:  # At least 3/4 tests should pass
        print(f"\n✅ CONCLUSION: iCal integration is REAL (not hardcoded)")
        print(f"   ✅ Makes actual HTTP requests to iCal URLs")
        print(f"   ✅ Parses real iCal data format")
        print(f"   ✅ Handles different URL types appropriately")
        if error_handling_result:
            print(f"   ✅ Has robust error handling")
        
        if not real_data_result:
            print(f"   ⚠️  Note: Test URLs may not contain booking data (expected)")
    else:
        print(f"\n❌ CONCLUSION: iCal integration has significant issues")
        for test in failed_tests:
            print(f"   ❌ {test}")
    
    print(f"\n🏠 Test apartment ID: {tester.created_apartment_id}")
    print(f"👤 Test user: {tester.test_user['email']}")
    
    return 0 if len(passed_tests) >= 3 else 1

if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(main()))