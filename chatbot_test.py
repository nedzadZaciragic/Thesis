import requests
import sys
import json
from datetime import datetime
import time

class MyHostIQChatbotTester:
    def __init__(self, base_url="https://thesis-deployment.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.created_apartment_id = None
        self.token = None
        self.user_id = None
        
        # Test user data
        self.test_user = {
            "email": "chatbot.test@example.com",
            "full_name": "Chatbot Test User",
            "password": "testpass123"
        }
        
        # Test apartment data with comprehensive information for chatbot testing
        self.test_apartment = {
            "name": "Modern Sarajevo Apartment",
            "address": "Mis Irbina 7, Sarajevo, Bosnia and Herzegovina",
            "description": "Beautiful modern apartment in the heart of Sarajevo with stunning city views",
            "rules": ["No smoking", "No pets", "Check-in after 3 PM", "Check-out before 11 AM", "Quiet hours 10 PM - 8 AM"],
            "contact": {"phone": "+387 61 123 456", "email": "host@sarajevo-apartment.com"},
            "ical_url": "",
            "ai_tone": "friendly",
            "recommendations": {
                "restaurants": [
                    {"name": "Cevabdzinica Zeljo", "type": "Traditional", "location": "Kundurdžiluk 19, Sarajevo", "tip": "Best cevapi in the city"},
                    {"name": "Dveri", "type": "Fine Dining", "location": "Prote Bakovica 12, Sarajevo", "tip": "Excellent Bosnian cuisine with modern twist"}
                ],
                "hidden_gems": [
                    {"name": "Yellow Fortress", "location": "Jekovac, Sarajevo", "tip": "Best sunset views over the city"},
                    {"name": "Tunnel Museum", "location": "Tuneli 1, Sarajevo", "tip": "Historical war tunnel from 1990s"}
                ],
                "transport": "Use trams and buses for city transport. Taxi apps: Crveni Taxi, BiH Taxi"
            },
            # New fields for comprehensive chatbot testing
            "check_in_time": "15:00",
            "check_out_time": "11:00", 
            "check_in_instructions": "Keys are in the lockbox next to the main door. Code is 1234. Ring apartment 5 if you have issues.",
            "apartment_locations": {
                "keys": "Lockbox next to main door, code 1234",
                "towels": "Bathroom closet, top shelf",
                "kitchen_utensils": "Kitchen drawer next to the stove",
                "cleaning_supplies": "Under the kitchen sink",
                "first_aid": "Bathroom medicine cabinet",
                "other_items": "Extra blankets in bedroom wardrobe"
            },
            "wifi_network": "SarajevoApartment_5G",
            "wifi_password": "Welcome2024!",
            "wifi_instructions": "Connect to SarajevoApartment_5G network. Password is case-sensitive. Router is in the living room."
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
        if use_auth and self.token:
            print(f"   Using auth: Bearer {self.token[:20]}...")
        
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

    def setup_test_environment(self):
        """Set up test environment with user and apartment"""
        print("🔧 Setting up test environment...")
        
        # Try to register test user, if fails try login
        success, response = self.run_test(
            "User Registration for Chatbot Testing",
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
        else:
            print("   ⚠️ Registration failed, trying login...")
            # Try login instead
            login_data = {
                "email": self.test_user["email"],
                "password": self.test_user["password"]
            }
            
            success, response = self.run_test(
                "User Login for Chatbot Testing",
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
            else:
                print("   ❌ Failed to login user")
                return False
        
        # Create test apartment with comprehensive data
        success, response = self.run_test(
            "Create Test Apartment for Chatbot",
            "POST",
            "apartments",
            200,
            data=self.test_apartment
        )
        
        if success and response.get('id'):
            self.created_apartment_id = response['id']
            print(f"   ✅ Apartment created: {self.created_apartment_id}")
            return True
        else:
            print("   ❌ Failed to create apartment")
            return False

    def test_context_tracking(self):
        """Test context tracking - AI should remember previous questions"""
        print("\n🧠 TESTING CONTEXT TRACKING...")
        
        if not self.created_apartment_id:
            print("❌ No apartment ID available")
            return False
        
        # First message: "When is check-in?"
        first_message = {
            "apartment_id": self.created_apartment_id,
            "message": "When is check-in?",
            "session_id": "context_test_session_1"
        }
        
        success1, response1 = self.run_test(
            "Context Test - First Message (When is check-in?)",
            "POST",
            "chat",
            200,
            data=first_message,
            use_auth=False,
            timeout=60
        )
        
        if not success1:
            return False
        
        first_response = response1.get('response', '')
        print(f"   First response: {first_response[:200]}...")
        
        # Check if response contains check-in information
        if '15:00' in first_response or '3' in first_response:
            print("   ✅ First response contains check-in time")
        else:
            print("   ⚠️  First response may not contain check-in time")
        
        # Wait a moment between messages
        time.sleep(2)
        
        # Follow-up message: "How?" (should understand this refers to check-in instructions)
        followup_message = {
            "apartment_id": self.created_apartment_id,
            "message": "How?",
            "session_id": "context_test_session_1"  # Same session ID
        }
        
        success2, response2 = self.run_test(
            "Context Test - Follow-up Message (How?)",
            "POST",
            "chat",
            200,
            data=followup_message,
            use_auth=False,
            timeout=60
        )
        
        if not success2:
            return False
        
        followup_response = response2.get('response', '')
        print(f"   Follow-up response: {followup_response[:200]}...")
        
        # Check if AI understood context and provided check-in instructions
        context_indicators = [
            'lockbox', 'code', '1234', 'main door', 'apartment 5',
            'check-in', 'instructions', 'keys'
        ]
        
        context_understood = any(indicator.lower() in followup_response.lower() 
                               for indicator in context_indicators)
        
        if context_understood:
            print("   ✅ CONTEXT TRACKING WORKING: AI understood 'How?' refers to check-in instructions")
            return True
        else:
            print("   ❌ CONTEXT TRACKING FAILED: AI did not understand context")
            print(f"   Expected check-in instructions, got: {followup_response}")
            return False

    def test_scope_control_apartment_questions(self):
        """Test scope control - apartment-related questions should work"""
        print("\n🏠 TESTING SCOPE CONTROL - APARTMENT QUESTIONS...")
        
        if not self.created_apartment_id:
            print("❌ No apartment ID available")
            return False
        
        apartment_questions = [
            {
                "question": "What's the WiFi password?",
                "expected_keywords": ["Welcome2024!", "SarajevoApartment_5G", "wifi", "password"]
            },
            {
                "question": "Where are the towels?",
                "expected_keywords": ["bathroom", "closet", "top shelf", "towels"]
            },
            {
                "question": "What are the house rules?",
                "expected_keywords": ["smoking", "pets", "check-in", "check-out", "quiet"]
            },
            {
                "question": "How do I get the keys?",
                "expected_keywords": ["lockbox", "1234", "main door", "keys"]
            }
        ]
        
        all_passed = True
        
        for i, test_case in enumerate(apartment_questions):
            message_data = {
                "apartment_id": self.created_apartment_id,
                "message": test_case["question"],
                "session_id": f"scope_apartment_test_{i}"
            }
            
            success, response = self.run_test(
                f"Apartment Question: {test_case['question']}",
                "POST",
                "chat",
                200,
                data=message_data,
                use_auth=False,
                timeout=60
            )
            
            if success:
                ai_response = response.get('response', '')
                print(f"   Question: {test_case['question']}")
                print(f"   Response: {ai_response[:150]}...")
                
                # Check if response contains expected information
                keywords_found = [kw for kw in test_case["expected_keywords"] 
                                if kw.lower() in ai_response.lower()]
                
                if keywords_found:
                    print(f"   ✅ Contains expected info: {keywords_found}")
                else:
                    print(f"   ⚠️  May not contain expected keywords: {test_case['expected_keywords']}")
                    all_passed = False
            else:
                all_passed = False
                print(f"   ❌ Failed to get response for: {test_case['question']}")
            
            time.sleep(1)  # Brief pause between requests
        
        return all_passed

    def test_scope_control_local_city_questions(self):
        """Test scope control - local city questions should work"""
        print("\n🌆 TESTING SCOPE CONTROL - LOCAL CITY QUESTIONS...")
        
        if not self.created_apartment_id:
            print("❌ No apartment ID available")
            return False
        
        local_questions = [
            {
                "question": "Best restaurants in Sarajevo?",
                "expected_keywords": ["Cevabdzinica Zeljo", "Dveri", "cevapi", "restaurant", "Sarajevo"]
            },
            {
                "question": "What to see in Sarajevo?",
                "expected_keywords": ["Yellow Fortress", "Tunnel Museum", "sunset", "historical"]
            },
            {
                "question": "How to get around Sarajevo?",
                "expected_keywords": ["tram", "bus", "taxi", "transport", "Crveni Taxi"]
            }
        ]
        
        all_passed = True
        
        for i, test_case in enumerate(local_questions):
            message_data = {
                "apartment_id": self.created_apartment_id,
                "message": test_case["question"],
                "session_id": f"scope_local_test_{i}"
            }
            
            success, response = self.run_test(
                f"Local City Question: {test_case['question']}",
                "POST",
                "chat",
                200,
                data=message_data,
                use_auth=False,
                timeout=60
            )
            
            if success:
                ai_response = response.get('response', '')
                print(f"   Question: {test_case['question']}")
                print(f"   Response: {ai_response[:150]}...")
                
                # Check if response contains expected local information
                keywords_found = [kw for kw in test_case["expected_keywords"] 
                                if kw.lower() in ai_response.lower()]
                
                if keywords_found:
                    print(f"   ✅ Contains local info: {keywords_found}")
                elif "sarajevo" in ai_response.lower():
                    print("   ✅ Provides general Sarajevo recommendations")
                else:
                    print(f"   ⚠️  May not contain local information")
                    all_passed = False
            else:
                all_passed = False
                print(f"   ❌ Failed to get response for: {test_case['question']}")
            
            time.sleep(1)
        
        return all_passed

    def test_scope_control_out_of_scope_questions(self):
        """Test scope control - out-of-scope questions should trigger fallback"""
        print("\n🚫 TESTING SCOPE CONTROL - OUT-OF-SCOPE QUESTIONS...")
        
        if not self.created_apartment_id:
            print("❌ No apartment ID available")
            return False
        
        out_of_scope_questions = [
            {
                "question": "Best bars in Zagreb?",
                "other_city": "Zagreb"
            },
            {
                "question": "What to do in Belgrade?",
                "other_city": "Belgrade"
            },
            {
                "question": "Restaurants in Vienna?",
                "other_city": "Vienna"
            },
            {
                "question": "How to get around Paris?",
                "other_city": "Paris"
            }
        ]
        
        all_passed = True
        
        for i, test_case in enumerate(out_of_scope_questions):
            message_data = {
                "apartment_id": self.created_apartment_id,
                "message": test_case["question"],
                "session_id": f"scope_out_test_{i}"
            }
            
            success, response = self.run_test(
                f"Out-of-Scope Question: {test_case['question']}",
                "POST",
                "chat",
                200,
                data=message_data,
                use_auth=False,
                timeout=60
            )
            
            if success:
                ai_response = response.get('response', '')
                print(f"   Question: {test_case['question']}")
                print(f"   Response: {ai_response[:200]}...")
                
                # Check for fallback response indicators
                fallback_indicators = [
                    "specifically designed to help",
                    "recommendations in sarajevo",
                    "local tourism websites",
                    "travel guides",
                    "other cities",
                    "sarajevo apartment",
                    "local area"
                ]
                
                fallback_detected = any(indicator.lower() in ai_response.lower() 
                                      for indicator in fallback_indicators)
                
                # Should NOT contain information about the other city
                contains_other_city_info = test_case["other_city"].lower() in ai_response.lower()
                
                if fallback_detected and not contains_other_city_info:
                    print(f"   ✅ SCOPE CONTROL WORKING: Proper fallback for {test_case['other_city']}")
                elif fallback_detected:
                    print(f"   ⚠️  Fallback detected but may contain {test_case['other_city']} info")
                else:
                    print(f"   ❌ SCOPE CONTROL FAILED: No fallback for {test_case['other_city']} question")
                    all_passed = False
            else:
                all_passed = False
                print(f"   ❌ Failed to get response for: {test_case['question']}")
            
            time.sleep(1)
        
        return all_passed

    def test_multilingual_fallback(self):
        """Test multilingual fallback responses"""
        print("\n🌍 TESTING MULTILINGUAL FALLBACK RESPONSES...")
        
        if not self.created_apartment_id:
            print("❌ No apartment ID available")
            return False
        
        multilingual_questions = [
            {
                "question": "¿Mejores bares en Madrid?",
                "language": "Spanish",
                "expected_keywords": ["específicamente diseñado", "sarajevo", "otras ciudades", "zona local"]
            },
            {
                "question": "Meilleurs restaurants à Paris?",
                "language": "French", 
                "expected_keywords": ["spécialement conçu", "sarajevo", "autres villes", "région locale"]
            },
            {
                "question": "Beste Bars in Berlin?",
                "language": "German",
                "expected_keywords": ["speziell entwickelt", "sarajevo", "andere städte", "örtlichen gegend"]
            },
            {
                "question": "Migliori ristoranti a Roma?",
                "language": "Italian",
                "expected_keywords": ["specificamente progettato", "sarajevo", "altre città", "zona locale"]
            }
        ]
        
        all_passed = True
        
        for i, test_case in enumerate(multilingual_questions):
            message_data = {
                "apartment_id": self.created_apartment_id,
                "message": test_case["question"],
                "session_id": f"multilingual_test_{i}"
            }
            
            success, response = self.run_test(
                f"Multilingual Fallback ({test_case['language']}): {test_case['question']}",
                "POST",
                "chat",
                200,
                data=message_data,
                use_auth=False,
                timeout=60
            )
            
            if success:
                ai_response = response.get('response', '')
                print(f"   Question ({test_case['language']}): {test_case['question']}")
                print(f"   Response: {ai_response[:200]}...")
                
                # Check if response is in the same language
                keywords_found = [kw for kw in test_case["expected_keywords"] 
                                if kw.lower() in ai_response.lower()]
                
                if keywords_found:
                    print(f"   ✅ MULTILINGUAL FALLBACK WORKING: Response in {test_case['language']}")
                    print(f"   Found keywords: {keywords_found}")
                else:
                    print(f"   ⚠️  May not be responding in {test_case['language']}")
                    # Check if at least responding with fallback (even in English)
                    english_fallback = any(word in ai_response.lower() 
                                         for word in ["specifically designed", "other cities", "local area"])
                    if english_fallback:
                        print("   ⚠️  Using English fallback instead of native language")
                    else:
                        all_passed = False
            else:
                all_passed = False
                print(f"   ❌ Failed to get response for {test_case['language']} question")
            
            time.sleep(1)
        
        return all_passed

    def test_local_recommendations_no_host_data(self):
        """Test local recommendations when host hasn't provided data"""
        print("\n📍 TESTING LOCAL RECOMMENDATIONS WITHOUT HOST DATA...")
        
        # Create apartment with minimal data (no recommendations)
        minimal_apartment = {
            "name": "Minimal Test Apartment",
            "address": "Test Street 1, Sarajevo, Bosnia and Herzegovina",
            "description": "Basic apartment for testing",
            "rules": ["No smoking"],
            "contact": {"email": "test@example.com"},
            "ical_url": "",
            "recommendations": {}  # Empty recommendations
        }
        
        success, response = self.run_test(
            "Create Minimal Apartment",
            "POST",
            "apartments",
            200,
            data=minimal_apartment
        )
        
        if not success or not response.get('id'):
            print("❌ Failed to create minimal apartment")
            return False
        
        minimal_apartment_id = response['id']
        print(f"   Created minimal apartment: {minimal_apartment_id}")
        
        # Test local recommendation questions
        local_questions = [
            "What are good restaurants in Sarajevo?",
            "What should I visit in Sarajevo?",
            "Where can I go for drinks in Sarajevo?"
        ]
        
        all_passed = True
        
        for i, question in enumerate(local_questions):
            message_data = {
                "apartment_id": minimal_apartment_id,
                "message": question,
                "session_id": f"local_rec_test_{i}"
            }
            
            success, response = self.run_test(
                f"Local Recommendation: {question}",
                "POST",
                "chat",
                200,
                data=message_data,
                use_auth=False,
                timeout=60
            )
            
            if success:
                ai_response = response.get('response', '')
                print(f"   Question: {question}")
                print(f"   Response: {ai_response[:200]}...")
                
                # Should provide general Sarajevo recommendations
                sarajevo_mentioned = "sarajevo" in ai_response.lower()
                has_recommendations = any(word in ai_response.lower() 
                                        for word in ["restaurant", "visit", "recommend", "try", "go to"])
                
                # Should NOT recommend places in other cities
                other_cities = ["zagreb", "belgrade", "vienna", "paris", "berlin"]
                mentions_other_cities = any(city in ai_response.lower() for city in other_cities)
                
                if sarajevo_mentioned and has_recommendations and not mentions_other_cities:
                    print("   ✅ Provides general Sarajevo recommendations only")
                elif sarajevo_mentioned and has_recommendations:
                    print("   ⚠️  Provides recommendations but may mention other cities")
                elif sarajevo_mentioned:
                    print("   ⚠️  Mentions Sarajevo but may not provide specific recommendations")
                else:
                    print("   ❌ Does not provide local Sarajevo recommendations")
                    all_passed = False
            else:
                all_passed = False
                print(f"   ❌ Failed to get response for: {question}")
            
            time.sleep(1)
        
        return all_passed

    def test_improved_system_prompt(self):
        """Test improved system prompt with city extraction and apartment info access"""
        print("\n🤖 TESTING IMPROVED SYSTEM PROMPT...")
        
        if not self.created_apartment_id:
            print("❌ No apartment ID available")
            return False
        
        # Test comprehensive apartment information access
        comprehensive_questions = [
            {
                "question": "Tell me about this apartment",
                "expected_info": ["Modern Sarajevo Apartment", "Sarajevo", "beautiful", "city views"]
            },
            {
                "question": "What's the complete check-in process?",
                "expected_info": ["15:00", "3 PM", "lockbox", "1234", "main door", "apartment 5"]
            },
            {
                "question": "Give me all WiFi details",
                "expected_info": ["SarajevoApartment_5G", "Welcome2024!", "case-sensitive", "living room"]
            },
            {
                "question": "Where can I find everything I need?",
                "expected_info": ["towels", "bathroom closet", "kitchen utensils", "cleaning supplies", "first aid"]
            },
            {
                "question": "What are all the rules?",
                "expected_info": ["smoking", "pets", "3 PM", "11 AM", "quiet hours", "10 PM", "8 AM"]
            }
        ]
        
        all_passed = True
        
        for i, test_case in enumerate(comprehensive_questions):
            message_data = {
                "apartment_id": self.created_apartment_id,
                "message": test_case["question"],
                "session_id": f"system_prompt_test_{i}"
            }
            
            success, response = self.run_test(
                f"System Prompt Test: {test_case['question']}",
                "POST",
                "chat",
                200,
                data=message_data,
                use_auth=False,
                timeout=60
            )
            
            if success:
                ai_response = response.get('response', '')
                print(f"   Question: {test_case['question']}")
                print(f"   Response: {ai_response[:250]}...")
                
                # Check if response contains expected apartment information
                info_found = [info for info in test_case["expected_info"] 
                            if info.lower() in ai_response.lower()]
                
                coverage = len(info_found) / len(test_case["expected_info"])
                
                if coverage >= 0.7:  # At least 70% of expected info
                    print(f"   ✅ Comprehensive info provided: {info_found}")
                elif coverage >= 0.4:  # At least 40% of expected info
                    print(f"   ⚠️  Partial info provided: {info_found}")
                else:
                    print(f"   ❌ Insufficient info provided: {info_found}")
                    all_passed = False
            else:
                all_passed = False
                print(f"   ❌ Failed to get response for: {test_case['question']}")
            
            time.sleep(1)
        
        return all_passed

    def test_city_extraction_from_address(self):
        """Test that system prompt correctly extracts city from address for scope control"""
        print("\n🗺️  TESTING CITY EXTRACTION FROM ADDRESS...")
        
        if not self.created_apartment_id:
            print("❌ No apartment ID available")
            return False
        
        # Test questions about the apartment's city (Sarajevo) vs other cities
        city_test_questions = [
            {
                "question": "Tell me about Sarajevo attractions",
                "should_work": True,
                "description": "Should work - asking about apartment's city"
            },
            {
                "question": "What about Zagreb restaurants?",
                "should_work": False,
                "description": "Should trigger fallback - asking about different city"
            },
            {
                "question": "Best places in Bosnia?",
                "should_work": True,
                "description": "Should work - asking about apartment's country"
            }
        ]
        
        all_passed = True
        
        for i, test_case in enumerate(city_test_questions):
            message_data = {
                "apartment_id": self.created_apartment_id,
                "message": test_case["question"],
                "session_id": f"city_extraction_test_{i}"
            }
            
            success, response = self.run_test(
                f"City Extraction: {test_case['question']}",
                "POST",
                "chat",
                200,
                data=message_data,
                use_auth=False,
                timeout=60
            )
            
            if success:
                ai_response = response.get('response', '')
                print(f"   Question: {test_case['question']}")
                print(f"   Expected: {test_case['description']}")
                print(f"   Response: {ai_response[:200]}...")
                
                # Check for fallback indicators
                fallback_indicators = [
                    "specifically designed to help",
                    "other cities",
                    "local tourism websites",
                    "travel guides"
                ]
                
                has_fallback = any(indicator.lower() in ai_response.lower() 
                                 for indicator in fallback_indicators)
                
                if test_case["should_work"]:
                    # Should provide helpful response, not fallback
                    if not has_fallback:
                        print("   ✅ Correctly provides information (no fallback)")
                    else:
                        print("   ❌ Incorrectly triggered fallback for valid question")
                        all_passed = False
                else:
                    # Should trigger fallback
                    if has_fallback:
                        print("   ✅ Correctly triggered fallback for out-of-scope question")
                    else:
                        print("   ❌ Failed to trigger fallback for out-of-scope question")
                        all_passed = False
            else:
                all_passed = False
                print(f"   ❌ Failed to get response for: {test_case['question']}")
            
            time.sleep(1)
        
        return all_passed

    def run_all_chatbot_tests(self):
        """Run all chatbot improvement tests"""
        print("🚀 STARTING COMPREHENSIVE AI CHATBOT IMPROVEMENT TESTS")
        print("=" * 80)
        
        # Setup test environment
        if not self.setup_test_environment():
            print("❌ Failed to set up test environment")
            return False
        
        print(f"\n🏠 Using test apartment: {self.created_apartment_id}")
        print("=" * 80)
        
        # Run all test categories
        test_results = {
            "Context Tracking": self.test_context_tracking(),
            "Scope Control - Apartment Questions": self.test_scope_control_apartment_questions(),
            "Scope Control - Local City Questions": self.test_scope_control_local_city_questions(),
            "Scope Control - Out-of-Scope Questions": self.test_scope_control_out_of_scope_questions(),
            "Multilingual Fallback": self.test_multilingual_fallback(),
            "Local Recommendations (No Host Data)": self.test_local_recommendations_no_host_data(),
            "Improved System Prompt": self.test_improved_system_prompt(),
            "City Extraction from Address": self.test_city_extraction_from_address()
        }
        
        # Print final results
        print("\n" + "=" * 80)
        print("🏁 CHATBOT IMPROVEMENT TEST RESULTS")
        print("=" * 80)
        
        passed_tests = sum(1 for result in test_results.values() if result)
        total_tests = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status} - {test_name}")
        
        print(f"\n📊 OVERALL RESULTS:")
        print(f"   Tests Passed: {passed_tests}/{total_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print(f"   Individual API Calls: {self.tests_passed}/{self.tests_run}")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL CHATBOT IMPROVEMENT TESTS PASSED!")
            return True
        else:
            print(f"\n⚠️  {total_tests - passed_tests} TEST CATEGORIES FAILED")
            return False

if __name__ == "__main__":
    tester = MyHostIQChatbotTester()
    success = tester.run_all_chatbot_tests()
    sys.exit(0 if success else 1)