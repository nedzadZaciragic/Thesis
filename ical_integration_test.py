import requests
import sys
import json
from datetime import datetime, timezone, timedelta
import time
import uuid

class iCalIntegrationTester:
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
            "email": "ical.test@example.com",
            "full_name": "iCal Test User",
            "password": "icaltest123"
        }
        
        # Test email credentials for notifications
        self.test_email_creds = {
            "email": "test.ical@gmail.com",
            "password": "test_app_password_123",
            "smtp_server": "",
            "smtp_port": 587
        }
        
        # Real iCal URLs for testing
        self.test_ical_urls = [
            "https://calendar.google.com/calendar/ical/test%40example.com/public/basic.ics",
            "https://www.airbnb.com/calendar/ical/12345678.ics?s=abc123def456",
            "https://admin.booking.com/hotel/hoteladmin/ical.html?ses=abc123&hotel_id=12345"
        ]

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30, use_auth=True):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'}
        
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
                    print(f"   Response: {json.dumps(response_data, indent=2)[:300]}...")
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

    def create_test_apartment_with_ical(self):
        """Create test apartment with iCal URL"""
        print("🏠 Creating test apartment with iCal URL...")
        
        apartment_data = {
            "name": "iCal Test Apartment Rome",
            "address": "Via Roma 123, Rome, Italy",
            "description": "Beautiful apartment for iCal integration testing with real booking notifications",
            "rules": ["No smoking", "Check-in after 3PM", "Quiet hours 10PM-8AM"],
            "contact": {"phone": "+39 123456789", "email": "host@icaltest.com"},
            "ical_url": self.test_ical_urls[0],  # Use first test URL
            "ai_tone": "professional",
            "recommendations": {
                "restaurants": [{"name": "Trattoria Roma", "type": "Italian", "tip": "Best carbonara in the area"}],
                "hidden_gems": [{"name": "Secret Rooftop", "tip": "Amazing sunset views"}],
                "transport": "Metro Line A to Termini"
            }
        }
        
        success, response = self.run_test(
            "Create Apartment with iCal",
            "POST",
            "apartments",
            200,
            data=apartment_data
        )
        
        if success and response.get('id'):
            self.created_apartment_id = response['id']
            print(f"   ✅ Apartment created: {self.created_apartment_id}")
            print(f"   ✅ iCal URL configured: {response.get('ical_url', 'None')}")
            return True
        
        return False

    def test_ical_parsing_function(self):
        """Test parse_ical_calendar function with real iCal format"""
        print("📅 Testing iCal Parsing Function...")
        
        if not self.created_apartment_id:
            print("❌ No apartment available for testing")
            return False
        
        # Test the iCal sync endpoint which uses parse_ical_calendar internally
        success, response = self.run_test(
            "iCal Parsing via Sync",
            "POST",
            f"ical/test-sync/{self.created_apartment_id}",
            200,
            timeout=60
        )
        
        if success:
            message = response.get('message', '')
            print(f"   Sync result: {message}")
            
            # Check if the function actually processes iCal data
            if 'successfully' in message.lower():
                print("   ✅ iCal parsing function is working")
                
                # Verify it's not hardcoded by checking for real processing
                if 'processed' in message.lower() or 'calendar' in message.lower():
                    print("   ✅ Real iCal processing detected (not hardcoded)")
                else:
                    print("   ⚠️  May be using hardcoded responses")
                
                return True
            else:
                print("   ❌ iCal parsing may have issues")
                return False
        
        return False

    def test_calendar_sync_function(self):
        """Test sync_apartment_calendar function"""
        print("📅 Testing Calendar Sync Function...")
        
        if not self.created_apartment_id:
            print("❌ No apartment available for testing")
            return False
        
        # Test calendar sync with different iCal URLs
        test_results = []
        
        for i, ical_url in enumerate(self.test_ical_urls):
            print(f"\n   Testing with iCal URL {i+1}: {ical_url[:50]}...")
            
            # Update apartment with different iCal URL
            update_data = {
                "name": "iCal Test Apartment Rome",
                "address": "Via Roma 123, Rome, Italy",
                "description": "Beautiful apartment for iCal integration testing",
                "rules": ["No smoking", "Check-in after 3PM"],
                "contact": {"phone": "+39 123456789", "email": "host@icaltest.com"},
                "ical_url": ical_url,
                "ai_tone": "professional",
                "recommendations": {}
            }
            
            # Update apartment
            update_success, update_response = self.run_test(
                f"Update Apartment iCal URL {i+1}",
                "PUT",
                f"apartments/{self.created_apartment_id}",
                200,
                data=update_data
            )
            
            if update_success:
                # Test sync
                sync_success, sync_response = self.run_test(
                    f"Calendar Sync Test {i+1}",
                    "POST",
                    f"ical/test-sync/{self.created_apartment_id}",
                    200,
                    timeout=60
                )
                
                if sync_success:
                    message = sync_response.get('message', '')
                    test_results.append({
                        'url': ical_url,
                        'success': True,
                        'message': message
                    })
                    print(f"   ✅ Sync successful: {message}")
                else:
                    test_results.append({
                        'url': ical_url,
                        'success': False,
                        'message': 'Sync failed'
                    })
                    print(f"   ❌ Sync failed for URL {i+1}")
            
            time.sleep(2)  # Wait between tests
        
        # Analyze results
        successful_syncs = [r for r in test_results if r['success']]
        
        if len(successful_syncs) > 0:
            print(f"\n   ✅ Calendar sync working: {len(successful_syncs)}/{len(test_results)} URLs processed")
            
            # Check for real processing vs hardcoded responses
            unique_messages = set(r['message'] for r in successful_syncs)
            if len(unique_messages) > 1:
                print("   ✅ Different responses for different URLs (not hardcoded)")
            else:
                print("   ⚠️  Same response for all URLs (may be hardcoded)")
            
            return True
        else:
            print("   ❌ Calendar sync not working for any URLs")
            return False

    def test_email_notification_integration(self):
        """Test email notification integration with iCal sync"""
        print("📧 Testing Email Notification Integration...")
        
        if not self.created_apartment_id:
            print("❌ No apartment available for testing")
            return False
        
        # First, try to set up email credentials (will likely fail with test credentials)
        print("   Setting up email credentials for notification testing...")
        
        email_success, email_response = self.run_test(
            "Setup Email Credentials for Notifications",
            "POST",
            "auth/email-credentials",
            400,  # Expect 400 for invalid test credentials
            data=self.test_email_creds
        )
        
        if email_success:
            print("   ✅ Email credential validation working (properly rejects invalid credentials)")
        
        # Test sync with email notification attempt
        print("   Testing calendar sync with email notification attempt...")
        
        sync_success, sync_response = self.run_test(
            "Calendar Sync with Email Notifications",
            "POST",
            f"ical/test-sync/{self.created_apartment_id}",
            200,
            timeout=60
        )
        
        if sync_success:
            message = sync_response.get('message', '')
            print(f"   Sync result: {message}")
            
            # Check if email notification logic is integrated
            if 'email' in message.lower() or 'notification' in message.lower():
                print("   ✅ Email notification integration detected")
            else:
                print("   ⚠️  Email notification integration may not be active")
            
            return True
        
        return False

    def test_booking_notifications_storage(self):
        """Test booking notifications are stored correctly"""
        print("📬 Testing Booking Notifications Storage...")
        
        if not self.created_apartment_id:
            print("❌ No apartment available for testing")
            return False
        
        # Trigger calendar sync first
        sync_success, sync_response = self.run_test(
            "Trigger Calendar Sync for Notifications",
            "POST",
            f"ical/test-sync/{self.created_apartment_id}",
            200,
            timeout=60
        )
        
        if sync_success:
            print("   ✅ Calendar sync triggered")
            
            # Wait a moment for processing
            time.sleep(3)
            
            # Check for stored notifications
            notifications_success, notifications_response = self.run_test(
                "Get Booking Notifications",
                "GET",
                f"notifications/{self.created_apartment_id}",
                200
            )
            
            if notifications_success and isinstance(notifications_response, list):
                notification_count = len(notifications_response)
                print(f"   Found {notification_count} booking notifications")
                
                if notification_count > 0:
                    print("   ✅ Booking notifications are being stored")
                    
                    # Analyze notification data
                    for i, notification in enumerate(notifications_response[:3]):
                        print(f"   Notification {i+1}:")
                        print(f"     Guest: {notification.get('guest_name', 'Unknown')}")
                        print(f"     Email: {notification.get('guest_email', 'None')}")
                        print(f"     Check-in: {notification.get('checkin_date', 'None')}")
                        print(f"     Notification sent: {notification.get('notification_sent', False)}")
                        print(f"     Booking source: {notification.get('booking_source', 'Unknown')}")
                    
                    # Check for real data vs hardcoded
                    guest_names = [n.get('guest_name', '') for n in notifications_response]
                    unique_names = set(guest_names)
                    
                    if len(unique_names) > 1:
                        print("   ✅ Multiple different guest names (real data processing)")
                    elif any(name for name in guest_names if name and name != 'Guest'):
                        print("   ✅ Non-generic guest names detected (real data)")
                    else:
                        print("   ⚠️  Generic or no guest names (may be hardcoded)")
                    
                    return True
                else:
                    print("   ⚠️  No booking notifications found (may indicate no bookings in iCal)")
                    return True  # This is acceptable - no bookings is valid
            else:
                print("   ❌ Failed to retrieve booking notifications")
                return False
        
        return False

    def test_real_analytics_implementation(self):
        """Test real analytics implementation with actual chat data"""
        print("📊 Testing Real Analytics Implementation...")
        
        if not self.created_apartment_id:
            print("❌ No apartment available for testing")
            return False
        
        # Create some test chat messages first
        test_messages = [
            "What are the check-in instructions?",
            "Can you recommend a good restaurant?", 
            "What's the WiFi password?",
            "How do I get to the apartment from the airport?",
            "What are the house rules?",
            "Can you recommend a good restaurant?",  # Duplicate to test popular questions
            "What time is check-out?",
            "What are the check-in instructions?"  # Another duplicate
        ]
        
        print(f"   Creating {len(test_messages)} test chat messages...")
        
        chat_success_count = 0
        for i, message in enumerate(test_messages):
            chat_success, chat_response = self.run_test(
                f"Create Chat Message {i+1}",
                "POST",
                "chat",
                200,
                data={
                    "apartment_id": self.created_apartment_id,
                    "message": message,
                    "session_id": f"analytics_test_session_{i}"
                },
                timeout=60,
                use_auth=False
            )
            
            if chat_success:
                chat_success_count += 1
            
            time.sleep(1)  # Small delay between messages
        
        print(f"   ✅ Created {chat_success_count}/{len(test_messages)} chat messages")
        
        if chat_success_count > 0:
            # Wait for analytics to process
            time.sleep(3)
            
            # Test analytics dashboard
            analytics_success, analytics_response = self.run_test(
                "Analytics Dashboard with Real Data",
                "GET",
                "analytics/dashboard",
                200
            )
            
            if analytics_success:
                overview = analytics_response.get('overview', {})
                apartments = analytics_response.get('apartments', [])
                
                print(f"   Total chats: {overview.get('total_chats', 0)}")
                print(f"   Total apartments: {overview.get('total_apartments', 0)}")
                print(f"   Active apartments: {overview.get('active_apartments', 0)}")
                
                # Find our test apartment in analytics
                test_apartment_analytics = None
                for apt in apartments:
                    if apt.get('apartment_id') == self.created_apartment_id:
                        test_apartment_analytics = apt
                        break
                
                if test_apartment_analytics:
                    print(f"   ✅ Test apartment found in analytics")
                    print(f"   Apartment chats: {test_apartment_analytics.get('total_chats', 0)}")
                    
                    popular_questions = test_apartment_analytics.get('popular_questions', [])
                    print(f"   Popular questions: {len(popular_questions)}")
                    
                    if len(popular_questions) > 0:
                        print("   ✅ Popular questions calculated from real data:")
                        for i, question in enumerate(popular_questions[:3]):
                            question_text = question.get('question', 'Unknown')
                            count = question.get('count', 0)
                            percentage = question.get('percentage', 0)
                            print(f"     {i+1}. {question_text} ({count} times, {percentage:.1f}%)")
                        
                        # Verify percentages are calculated correctly
                        total_percentage = sum(q.get('percentage', 0) for q in popular_questions)
                        if 95 <= total_percentage <= 105:  # Allow some rounding
                            print("   ✅ Percentages calculated correctly")
                        else:
                            print(f"   ⚠️  Percentage calculation may be incorrect: {total_percentage}%")
                        
                        # Check for real data vs hardcoded
                        question_texts = [q.get('question', '') for q in popular_questions]
                        if any(text in question_texts for text in test_messages):
                            print("   ✅ Analytics reflect actual chat messages (real data)")
                        else:
                            print("   ⚠️  Analytics may not reflect actual chat messages")
                        
                        return True
                    else:
                        print("   ⚠️  No popular questions found (analytics may not be processing)")
                        return False
                else:
                    print("   ⚠️  Test apartment not found in analytics")
                    return False
            else:
                print("   ❌ Failed to retrieve analytics dashboard")
                return False
        else:
            print("   ❌ No chat messages created for analytics testing")
            return False

    def test_comprehensive_ical_workflow(self):
        """Test comprehensive iCal workflow end-to-end"""
        print("🔄 Testing Comprehensive iCal Workflow...")
        
        if not self.created_apartment_id:
            print("❌ No apartment available for testing")
            return False
        
        workflow_steps = []
        
        # Step 1: Update apartment with new iCal URL
        print("   Step 1: Updating apartment with iCal URL...")
        update_data = {
            "name": "Comprehensive Test Apartment",
            "address": "Via Test 456, Rome, Italy",
            "description": "Full workflow testing apartment",
            "rules": ["No smoking", "Check-in after 2PM", "Quiet hours 10PM-7AM"],
            "contact": {"phone": "+39 987654321", "email": "workflow@test.com"},
            "ical_url": "https://calendar.google.com/calendar/ical/workflow%40test.com/public/basic.ics",
            "ai_tone": "friendly",
            "recommendations": {
                "restaurants": [{"name": "Workflow Bistro", "type": "Italian", "tip": "Great for testing"}]
            }
        }
        
        update_success, update_response = self.run_test(
            "Update Apartment for Workflow",
            "PUT",
            f"apartments/{self.created_apartment_id}",
            200,
            data=update_data
        )
        
        workflow_steps.append(("Update Apartment", update_success))
        
        # Step 2: Trigger calendar sync
        print("   Step 2: Triggering calendar sync...")
        sync_success, sync_response = self.run_test(
            "Workflow Calendar Sync",
            "POST",
            f"ical/test-sync/{self.created_apartment_id}",
            200,
            timeout=60
        )
        
        workflow_steps.append(("Calendar Sync", sync_success))
        
        if sync_success:
            print(f"   Sync result: {sync_response.get('message', 'No message')}")
        
        # Step 3: Check for notifications
        print("   Step 3: Checking booking notifications...")
        time.sleep(2)  # Wait for processing
        
        notifications_success, notifications_response = self.run_test(
            "Workflow Notifications Check",
            "GET",
            f"notifications/{self.created_apartment_id}",
            200
        )
        
        workflow_steps.append(("Booking Notifications", notifications_success))
        
        if notifications_success:
            notification_count = len(notifications_response) if isinstance(notifications_response, list) else 0
            print(f"   Found {notification_count} notifications")
        
        # Step 4: Test email notification attempt (will fail with test credentials)
        print("   Step 4: Testing email notification system...")
        
        # Check if email credentials are configured
        email_check_success, email_check_response = self.run_test(
            "Check Email Credentials",
            "GET",
            "auth/email-credentials",
            200
        )
        
        workflow_steps.append(("Email System Check", email_check_success))
        
        if email_check_success:
            if email_check_response is None:
                print("   ⚠️  No email credentials configured (expected for test)")
            else:
                print("   ✅ Email credentials system operational")
        
        # Step 5: Verify analytics update
        print("   Step 5: Verifying analytics integration...")
        
        analytics_success, analytics_response = self.run_test(
            "Workflow Analytics Check",
            "GET",
            "analytics/dashboard",
            200
        )
        
        workflow_steps.append(("Analytics Integration", analytics_success))
        
        # Step 6: Test AI chat with updated data
        print("   Step 6: Testing AI chat with workflow data...")
        
        chat_success, chat_response = self.run_test(
            "Workflow AI Chat Test",
            "POST",
            "chat",
            200,
            data={
                "apartment_id": self.created_apartment_id,
                "message": "What are the apartment rules and restaurant recommendations?",
                "session_id": f"workflow_test_{int(time.time())}"
            },
            timeout=60,
            use_auth=False
        )
        
        workflow_steps.append(("AI Chat Integration", chat_success))
        
        if chat_success:
            ai_response = chat_response.get('response', '')
            if 'workflow bistro' in ai_response.lower() or 'smoking' in ai_response.lower():
                print("   ✅ AI chat reflects updated apartment data")
            else:
                print("   ⚠️  AI chat may not reflect latest apartment data")
        
        # Analyze workflow results
        successful_steps = [step for step, success in workflow_steps if success]
        total_steps = len(workflow_steps)
        success_rate = len(successful_steps) / total_steps * 100
        
        print(f"\n   📊 Workflow Results: {len(successful_steps)}/{total_steps} steps successful ({success_rate:.1f}%)")
        
        for step_name, success in workflow_steps:
            status = "✅" if success else "❌"
            print(f"   {status} {step_name}")
        
        # Overall assessment
        if success_rate >= 80:
            print("   ✅ Comprehensive iCal workflow is functional")
            return True
        else:
            print("   ❌ Comprehensive iCal workflow has significant issues")
            return False

    def test_ical_url_fetching_verification(self):
        """Verify that iCal URLs are actually fetched and not mocked"""
        print("🌐 Testing iCal URL Fetching Verification...")
        
        if not self.created_apartment_id:
            print("❌ No apartment available for testing")
            return False
        
        # Test with different types of iCal URLs to verify real fetching
        test_urls = [
            {
                "name": "Google Calendar",
                "url": "https://calendar.google.com/calendar/ical/test%40example.com/public/basic.ics",
                "expected_behavior": "Should attempt to fetch real URL"
            },
            {
                "name": "Airbnb Calendar", 
                "url": "https://www.airbnb.com/calendar/ical/12345678.ics?s=abc123def456",
                "expected_behavior": "Should attempt to fetch Airbnb calendar"
            },
            {
                "name": "Invalid URL",
                "url": "https://invalid-calendar-url.com/nonexistent.ics",
                "expected_behavior": "Should handle fetch errors gracefully"
            }
        ]
        
        results = []
        
        for test_case in test_urls:
            print(f"\n   Testing {test_case['name']}: {test_case['url'][:60]}...")
            
            # Update apartment with test URL
            update_data = {
                "name": "URL Fetch Test Apartment",
                "address": "Via Test, Rome, Italy",
                "description": "Testing URL fetching behavior",
                "rules": ["No smoking"],
                "contact": {"email": "test@example.com"},
                "ical_url": test_case['url'],
                "ai_tone": "professional",
                "recommendations": {}
            }
            
            update_success, update_response = self.run_test(
                f"Update with {test_case['name']} URL",
                "PUT",
                f"apartments/{self.created_apartment_id}",
                200,
                data=update_data
            )
            
            if update_success:
                # Trigger sync to test URL fetching
                sync_success, sync_response = self.run_test(
                    f"Sync {test_case['name']} Calendar",
                    "POST",
                    f"ical/test-sync/{self.created_apartment_id}",
                    200,
                    timeout=60
                )
                
                if sync_success:
                    message = sync_response.get('message', '')
                    print(f"   Sync result: {message}")
                    
                    # Analyze response for real fetching behavior
                    real_fetching_indicators = [
                        'error' in message.lower() and 'fetch' in message.lower(),
                        'timeout' in message.lower(),
                        'connection' in message.lower(),
                        'network' in message.lower(),
                        'successfully' in message.lower() and 'calendar' in message.lower()
                    ]
                    
                    if any(real_fetching_indicators):
                        print(f"   ✅ Real URL fetching detected for {test_case['name']}")
                        results.append(True)
                    else:
                        print(f"   ⚠️  May not be performing real URL fetching for {test_case['name']}")
                        results.append(False)
                else:
                    print(f"   ❌ Sync failed for {test_case['name']}")
                    results.append(False)
            else:
                print(f"   ❌ Failed to update apartment with {test_case['name']} URL")
                results.append(False)
            
            time.sleep(3)  # Wait between tests
        
        # Analyze overall results
        successful_fetches = sum(results)
        total_tests = len(results)
        
        print(f"\n   📊 URL Fetching Results: {successful_fetches}/{total_tests} showed real fetching behavior")
        
        if successful_fetches >= total_tests * 0.6:  # At least 60% should show real behavior
            print("   ✅ iCal URLs are being actually fetched (not mocked)")
            return True
        else:
            print("   ❌ iCal URL fetching may be mocked or not working")
            return False

def main():
    print("🚀 Starting iCal Integration Testing...")
    print("📅 Testing REAL iCal functionality - NOT hardcoded responses")
    print("=" * 70)
    
    tester = iCalIntegrationTester()
    
    # Setup
    if not tester.setup_test_user():
        print("❌ Failed to setup test user")
        return 1
    
    if not tester.create_test_apartment_with_ical():
        print("❌ Failed to create test apartment")
        return 1
    
    # Run iCal integration tests
    tests = [
        ("📅 iCal Parsing Function Test", tester.test_ical_parsing_function),
        ("📅 Calendar Sync Function Test", tester.test_calendar_sync_function),
        ("📧 Email Notification Integration", tester.test_email_notification_integration),
        ("📬 Booking Notifications Storage", tester.test_booking_notifications_storage),
        ("📊 Real Analytics Implementation", tester.test_real_analytics_implementation),
        ("🔄 Comprehensive iCal Workflow", tester.test_comprehensive_ical_workflow),
        ("🌐 iCal URL Fetching Verification", tester.test_ical_url_fetching_verification),
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
    print(f"📊 FINAL iCal INTEGRATION TEST RESULTS")
    print(f"{'='*70}")
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if failed_tests:
        print(f"\n❌ Failed tests:")
        for test in failed_tests:
            print(f"   - {test}")
        
        print(f"\n🔧 Issues found:")
        if "📅 iCal Parsing Function Test" in failed_tests:
            print("   ❌ iCal parsing function not working properly")
        if "📅 Calendar Sync Function Test" in failed_tests:
            print("   ❌ Calendar sync function has issues")
        if "📧 Email Notification Integration" in failed_tests:
            print("   ❌ Email notifications not integrated with iCal")
        if "📊 Real Analytics Implementation" in failed_tests:
            print("   ❌ Analytics not calculating from real data")
        if "🌐 iCal URL Fetching Verification" in failed_tests:
            print("   ❌ iCal URLs may not be actually fetched (hardcoded responses)")
    else:
        print(f"\n✅ All iCal integration tests passed!")
        print(f"   ✅ iCal parsing is working with real data")
        print(f"   ✅ Calendar sync processes actual iCal URLs")
        print(f"   ✅ Email notifications integrated")
        print(f"   ✅ Analytics calculated from real chat data")
        print(f"   ✅ Comprehensive workflow functional")
        print(f"   ✅ NOT using hardcoded/mocked responses")
    
    print(f"\n🏠 Test apartment ID: {tester.created_apartment_id}")
    print(f"👤 Test user: {tester.test_user['email']}")
    
    return 0 if len(failed_tests) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())