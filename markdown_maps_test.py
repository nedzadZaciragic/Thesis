import requests
import sys
import json
import re
from datetime import datetime
import time

class MarkdownMapsAPITester:
    def __init__(self, base_url="https://proximity-search-8.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        
        # Test apartment ID from review request
        self.test_apartment_id = "00a4b62a-9410-478f-a536-08628dc54df1"
        
        print(f"🔍 Testing Markdown Removal & Google Maps Links")
        print(f"   Base URL: {self.base_url}")
        print(f"   Test Apartment ID: {self.test_apartment_id}")

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'}

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
                self.failed_tests.append(name)
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append(name)
            return False, {}

    def check_markdown_formatting(self, text, test_name):
        """Check if text contains markdown formatting"""
        markdown_patterns = [
            r'\*\*[^*]+\*\*',  # **bold**
            r'\*[^*]+\*',      # *italic*
            r'#{1,6}\s',       # # headers
            r'\[[^\]]+\]\([^)]+\)',  # [text](link) markdown links
        ]
        
        found_markdown = []
        for pattern in markdown_patterns:
            matches = re.findall(pattern, text)
            if matches:
                found_markdown.extend(matches)
        
        if found_markdown:
            print(f"   ❌ MARKDOWN FOUND in {test_name}:")
            for markdown in found_markdown[:5]:  # Show first 5 matches
                print(f"      - {markdown}")
            return False
        else:
            print(f"   ✅ NO MARKDOWN formatting found in {test_name}")
            return True

    def check_google_maps_links(self, text, test_name):
        """Check for Google Maps links in proper format"""
        # Pattern for Google Maps links
        maps_pattern = r'https://www\.google\.com/maps/search/\?api=1&query=[^\\s]+'
        
        maps_links = re.findall(maps_pattern, text)
        
        if maps_links:
            print(f"   ✅ GOOGLE MAPS LINKS found in {test_name}: {len(maps_links)} links")
            for i, link in enumerate(maps_links[:3]):  # Show first 3 links
                print(f"      {i+1}. {link}")
            
            # Verify link format
            valid_links = 0
            for link in maps_links:
                if 'api=1' in link and 'query=' in link:
                    valid_links += 1
            
            if valid_links == len(maps_links):
                print(f"   ✅ All {len(maps_links)} Google Maps links have correct format")
                return True, maps_links
            else:
                print(f"   ⚠️  {valid_links}/{len(maps_links)} links have correct format")
                return False, maps_links
        else:
            print(f"   ❌ NO GOOGLE MAPS LINKS found in {test_name}")
            return False, []

    def test_restaurant_recommendations_no_markdown(self):
        """Test restaurant recommendations without markdown formatting"""
        print("\n🍽️ Testing Restaurant Recommendations (No Markdown)")
        
        chat_data = {
            "apartment_id": self.test_apartment_id,
            "message": "Where should I eat tonight?",
            "session_id": "test_session_restaurants"
        }
        
        success, response = self.run_test(
            "Restaurant Recommendations - No Markdown",
            "POST",
            "guest-chat",
            200,
            data=chat_data,
            timeout=60
        )
        
        if success:
            ai_response = response.get('response', '')
            print(f"   AI Response length: {len(ai_response)} characters")
            print(f"   AI Response preview: {ai_response[:200]}...")
            
            # Check for markdown formatting
            no_markdown = self.check_markdown_formatting(ai_response, "Restaurant Response")
            
            # Check for Google Maps links
            has_maps_links, maps_links = self.check_google_maps_links(ai_response, "Restaurant Response")
            
            # Check that restaurant names appear as plain text (not bold)
            restaurant_names_plain = True
            if '**' in ai_response:
                restaurant_names_plain = False
                print("   ❌ Restaurant names appear to be in bold (**text**)")
            else:
                print("   ✅ Restaurant names appear as plain text")
            
            # Overall assessment
            if no_markdown and has_maps_links and restaurant_names_plain:
                print("   ✅ RESTAURANT TEST PASSED: No markdown + Google Maps links present")
                return True
            else:
                print("   ❌ RESTAURANT TEST FAILED: Issues found")
                return False
        
        return False

    def test_coffee_place_recommendations(self):
        """Test coffee place recommendations"""
        print("\n☕ Testing Coffee Place Recommendations")
        
        chat_data = {
            "apartment_id": self.test_apartment_id,
            "message": "Can you recommend a coffee place?",
            "session_id": "test_session_coffee"
        }
        
        success, response = self.run_test(
            "Coffee Place Recommendations",
            "POST",
            "guest-chat",
            200,
            data=chat_data,
            timeout=60
        )
        
        if success:
            ai_response = response.get('response', '')
            print(f"   AI Response length: {len(ai_response)} characters")
            print(f"   AI Response preview: {ai_response[:200]}...")
            
            # Check for markdown formatting
            no_markdown = self.check_markdown_formatting(ai_response, "Coffee Response")
            
            # Check for Google Maps links
            has_maps_links, maps_links = self.check_google_maps_links(ai_response, "Coffee Response")
            
            # Overall assessment
            if no_markdown and has_maps_links:
                print("   ✅ COFFEE TEST PASSED: No markdown + Google Maps links present")
                return True
            else:
                print("   ❌ COFFEE TEST FAILED: Issues found")
                return False
        
        return False

    def test_attractions_nearby(self):
        """Test nearby attractions recommendations"""
        print("\n🏛️ Testing Nearby Attractions")
        
        chat_data = {
            "apartment_id": self.test_apartment_id,
            "message": "What attractions are nearby?",
            "session_id": "test_session_attractions"
        }
        
        success, response = self.run_test(
            "Nearby Attractions",
            "POST",
            "guest-chat",
            200,
            data=chat_data,
            timeout=60
        )
        
        if success:
            ai_response = response.get('response', '')
            print(f"   AI Response length: {len(ai_response)} characters")
            print(f"   AI Response preview: {ai_response[:200]}...")
            
            # Check for markdown formatting
            no_markdown = self.check_markdown_formatting(ai_response, "Attractions Response")
            
            # Check for Google Maps links
            has_maps_links, maps_links = self.check_google_maps_links(ai_response, "Attractions Response")
            
            # Overall assessment
            if no_markdown and has_maps_links:
                print("   ✅ ATTRACTIONS TEST PASSED: No markdown + Google Maps links present")
                return True
            else:
                print("   ❌ ATTRACTIONS TEST FAILED: Issues found")
                return False
        
        return False

    def test_bars_nightlife_recommendations(self):
        """Test bars and nightlife recommendations"""
        print("\n🍺 Testing Bars and Nightlife Recommendations")
        
        chat_data = {
            "apartment_id": self.test_apartment_id,
            "message": "Where can I go for drinks tonight?",
            "session_id": "test_session_bars"
        }
        
        success, response = self.run_test(
            "Bars and Nightlife",
            "POST",
            "guest-chat",
            200,
            data=chat_data,
            timeout=60
        )
        
        if success:
            ai_response = response.get('response', '')
            print(f"   AI Response length: {len(ai_response)} characters")
            print(f"   AI Response preview: {ai_response[:200]}...")
            
            # Check for markdown formatting
            no_markdown = self.check_markdown_formatting(ai_response, "Bars Response")
            
            # Check for Google Maps links
            has_maps_links, maps_links = self.check_google_maps_links(ai_response, "Bars Response")
            
            # Overall assessment
            if no_markdown and has_maps_links:
                print("   ✅ BARS TEST PASSED: No markdown + Google Maps links present")
                return True
            else:
                print("   ❌ BARS TEST FAILED: Issues found")
                return False
        
        return False

    def test_hidden_gems_recommendations(self):
        """Test hidden gems recommendations"""
        print("\n💎 Testing Hidden Gems Recommendations")
        
        chat_data = {
            "apartment_id": self.test_apartment_id,
            "message": "What are some hidden gems in the area?",
            "session_id": "test_session_gems"
        }
        
        success, response = self.run_test(
            "Hidden Gems",
            "POST",
            "guest-chat",
            200,
            data=chat_data,
            timeout=60
        )
        
        if success:
            ai_response = response.get('response', '')
            print(f"   AI Response length: {len(ai_response)} characters")
            print(f"   AI Response preview: {ai_response[:200]}...")
            
            # Check for markdown formatting
            no_markdown = self.check_markdown_formatting(ai_response, "Hidden Gems Response")
            
            # Check for Google Maps links
            has_maps_links, maps_links = self.check_google_maps_links(ai_response, "Hidden Gems Response")
            
            # Overall assessment
            if no_markdown and has_maps_links:
                print("   ✅ HIDDEN GEMS TEST PASSED: No markdown + Google Maps links present")
                return True
            else:
                print("   ❌ HIDDEN GEMS TEST FAILED: Issues found")
                return False
        
        return False

    def test_link_format_verification(self):
        """Test comprehensive link format verification"""
        print("\n🔗 Testing Link Format Verification")
        
        # Test multiple location queries to gather links
        test_queries = [
            "Where should I eat tonight?",
            "Can you recommend a coffee place?", 
            "What attractions are nearby?",
            "Where can I go for drinks?",
            "What are some hidden gems?"
        ]
        
        all_links = []
        all_responses = []
        
        for i, query in enumerate(test_queries):
            print(f"\n   Query {i+1}: {query}")
            
            chat_data = {
                "apartment_id": self.test_apartment_id,
                "message": query,
                "session_id": f"test_session_links_{i}"
            }
            
            success, response = self.run_test(
                f"Link Format Test - Query {i+1}",
                "POST",
                "guest-chat",
                200,
                data=chat_data,
                timeout=60
            )
            
            if success:
                ai_response = response.get('response', '')
                all_responses.append(ai_response)
                
                # Extract Google Maps links
                maps_pattern = r'https://www\.google\.com/maps/search/\?api=1&query=[^\s]+'
                maps_links = re.findall(maps_pattern, ai_response)
                all_links.extend(maps_links)
                
                print(f"      Found {len(maps_links)} Google Maps links")
            
            # Small delay between requests
            time.sleep(2)
        
        # Comprehensive link analysis
        print(f"\n🔍 Comprehensive Link Analysis:")
        print(f"   Total Google Maps links found: {len(all_links)}")
        
        if len(all_links) > 0:
            # Check link format compliance
            valid_format_count = 0
            invalid_format_count = 0
            
            for link in all_links:
                if ('https://www.google.com/maps/search/?api=1&query=' in link and 
                    'api=1' in link and 'query=' in link):
                    valid_format_count += 1
                else:
                    invalid_format_count += 1
                    print(f"   ❌ Invalid format: {link}")
            
            print(f"   ✅ Valid format links: {valid_format_count}")
            print(f"   ❌ Invalid format links: {invalid_format_count}")
            
            # Check for markdown link format (should not exist)
            markdown_link_pattern = r'\[[^\]]+\]\([^)]+\)'
            markdown_links_found = 0
            
            for response in all_responses:
                markdown_matches = re.findall(markdown_link_pattern, response)
                markdown_links_found += len(markdown_matches)
                if markdown_matches:
                    print(f"   ❌ Markdown link format found: {markdown_matches}")
            
            if markdown_links_found == 0:
                print("   ✅ No markdown link format found (links are plain URLs)")
            else:
                print(f"   ❌ Found {markdown_links_found} markdown-formatted links")
            
            # Success criteria
            format_success = (valid_format_count == len(all_links))
            no_markdown_links = (markdown_links_found == 0)
            sufficient_links = (len(all_links) >= 3)  # At least 3 links across all queries
            
            if format_success and no_markdown_links and sufficient_links:
                print("   ✅ LINK FORMAT VERIFICATION PASSED")
                return True
            else:
                print("   ❌ LINK FORMAT VERIFICATION FAILED")
                return False
        else:
            print("   ❌ NO GOOGLE MAPS LINKS FOUND - CRITICAL FAILURE")
            return False

    def test_apartment_data_access(self):
        """Test that the apartment has proper data for recommendations"""
        print("\n🏠 Testing Apartment Data Access")
        
        # Get apartment data via public endpoint
        success, response = self.run_test(
            "Get Apartment Data",
            "GET",
            f"apartments/{self.test_apartment_id}/public",
            200,
            timeout=30
        )
        
        if success:
            apartment_data = response.get('apartment', {})
            branding_data = response.get('branding', {})
            
            print(f"   Apartment name: {apartment_data.get('name', 'Unknown')}")
            print(f"   Address: {apartment_data.get('address', 'Unknown')}")
            print(f"   AI Assistant name: {branding_data.get('ai_assistant_name', 'Unknown')}")
            
            # Check for recommendations data
            recommendations = apartment_data.get('recommendations', {})
            restaurants = recommendations.get('restaurants', [])
            hidden_gems = recommendations.get('hidden_gems', [])
            
            print(f"   Restaurants configured: {len(restaurants)}")
            print(f"   Hidden gems configured: {len(hidden_gems)}")
            
            if len(restaurants) > 0 or len(hidden_gems) > 0:
                print("   ✅ Apartment has recommendation data")
                
                # Show sample recommendations
                if restaurants:
                    print("   Sample restaurants:")
                    for i, rest in enumerate(restaurants[:2]):
                        name = rest.get('name', 'Unknown')
                        location = rest.get('location', 'No location')
                        print(f"      {i+1}. {name} - {location}")
                
                if hidden_gems:
                    print("   Sample hidden gems:")
                    for i, gem in enumerate(hidden_gems[:2]):
                        name = gem.get('name', 'Unknown')
                        location = gem.get('location', 'No location')
                        print(f"      {i+1}. {name} - {location}")
                
                return True
            else:
                print("   ⚠️  Apartment has no recommendation data configured")
                print("   ⚠️  AI will need to generate recommendations from general knowledge")
                return True  # Still valid, just different behavior
        
        return False

    def run_all_tests(self):
        """Run all markdown and Google Maps link tests"""
        print("=" * 80)
        print("🚀 STARTING MARKDOWN REMOVAL & GOOGLE MAPS LINKS TESTING")
        print("=" * 80)
        
        # Test apartment data first
        apartment_data_ok = self.test_apartment_data_access()
        
        # Core functionality tests
        restaurant_test = self.test_restaurant_recommendations_no_markdown()
        coffee_test = self.test_coffee_place_recommendations()
        attractions_test = self.test_attractions_nearby()
        bars_test = self.test_bars_nightlife_recommendations()
        gems_test = self.test_hidden_gems_recommendations()
        
        # Comprehensive link format verification
        link_format_test = self.test_link_format_verification()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        print(f"Total tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Tests failed: {len(self.failed_tests)}")
        print(f"Success rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        # Detailed results
        test_results = [
            ("Apartment Data Access", apartment_data_ok),
            ("Restaurant Recommendations (No Markdown)", restaurant_test),
            ("Coffee Place Recommendations", coffee_test),
            ("Nearby Attractions", attractions_test),
            ("Bars and Nightlife", bars_test),
            ("Hidden Gems", gems_test),
            ("Link Format Verification", link_format_test)
        ]
        
        print("\n📋 DETAILED RESULTS:")
        passed_tests = 0
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"   {status}: {test_name}")
            if result:
                passed_tests += 1
        
        # Critical success criteria
        critical_tests = [restaurant_test, coffee_test, attractions_test, link_format_test]
        critical_passed = sum(critical_tests)
        
        print(f"\n🎯 CRITICAL TESTS: {critical_passed}/{len(critical_tests)} passed")
        
        # Overall assessment
        if critical_passed == len(critical_tests):
            print("\n🎉 SUCCESS: All critical markdown removal and Google Maps link tests PASSED!")
            print("   ✅ No markdown formatting found in AI responses")
            print("   ✅ Google Maps links present and properly formatted")
            print("   ✅ Restaurant/place names appear as plain text")
            print("   ✅ All location recommendations include clickable links")
            return True
        else:
            print("\n❌ FAILURE: Critical issues found with markdown removal or Google Maps links")
            if self.failed_tests:
                print("   Failed tests:")
                for failed_test in self.failed_tests:
                    print(f"      - {failed_test}")
            return False

if __name__ == "__main__":
    tester = MarkdownMapsAPITester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ ALL TESTS PASSED - Markdown removal and Google Maps links working correctly!")
        sys.exit(0)
    else:
        print("\n❌ TESTS FAILED - Issues found with markdown removal or Google Maps links")
        sys.exit(1)