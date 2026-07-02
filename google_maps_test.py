import requests
import sys
import json
import re
from datetime import datetime

class GoogleMapsLinksTest:
    def __init__(self, base_url="https://thesis-deployment.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.apartment_id = "00a4b62a-9410-478f-a536-08628dc54df1"
        self.test_message = "Where should I eat tonight? Any local restaurant recommendations?"
        
    def test_google_maps_links_in_chatbot(self):
        """Test Google Maps links feature in chatbot response"""
        print("🔍 Testing Google Maps Links Feature in Chatbot")
        print(f"   Apartment ID: {self.apartment_id}")
        print(f"   Test Message: '{self.test_message}'")
        
        # Test the public guest chat endpoint (no authentication required)
        chat_url = f"{self.api_url}/guest-chat"
        
        chat_data = {
            "apartment_id": self.apartment_id,
            "message": self.test_message,
            "session_id": f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
        headers = {'Content-Type': 'application/json'}
        
        try:
            print("\n📤 Sending chat request...")
            response = requests.post(chat_url, json=chat_data, headers=headers, timeout=60)
            
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                print("✅ Chat request successful")
                
                # Extract the AI response
                ai_response = response_data.get('response', '')
                print(f"\n🤖 AI Response:")
                print(f"   {ai_response}")
                
                # Test 1: Check if response contains Google Maps links
                google_maps_pattern = r'https://www\.google\.com/maps/search/\?api=1&query=[^)\s]+'
                maps_links = re.findall(google_maps_pattern, ai_response)
                
                if maps_links:
                    print(f"\n✅ GOOGLE MAPS LINKS FOUND: {len(maps_links)} links detected")
                    
                    for i, link in enumerate(maps_links, 1):
                        print(f"   Link {i}: {link}")
                        
                        # Test 2: Verify link format
                        if self.validate_google_maps_link(link):
                            print(f"   ✅ Link {i} format is valid")
                        else:
                            print(f"   ❌ Link {i} format is invalid")
                    
                    # Test 3: Check if links are properly formatted with restaurant names
                    restaurant_recommendations = self.extract_restaurant_recommendations(ai_response)
                    
                    if restaurant_recommendations:
                        print(f"\n🍽️ RESTAURANT RECOMMENDATIONS FOUND: {len(restaurant_recommendations)}")
                        
                        for i, rec in enumerate(restaurant_recommendations, 1):
                            print(f"   Restaurant {i}: {rec['name']}")
                            if rec['maps_link']:
                                print(f"   ✅ Has Google Maps link: {rec['maps_link']}")
                            else:
                                print(f"   ❌ Missing Google Maps link")
                    
                    # Test 4: Verify links are clickable (contain proper URL encoding)
                    clickable_links = self.check_clickable_links(maps_links)
                    print(f"\n🔗 CLICKABLE LINKS: {clickable_links}/{len(maps_links)} links are properly formatted")
                    
                    # Test 5: Check if links contain location context (city/area)
                    contextual_links = self.check_contextual_links(maps_links)
                    print(f"📍 CONTEXTUAL LINKS: {contextual_links}/{len(maps_links)} links contain location context")
                    
                    # Overall assessment
                    if len(maps_links) > 0 and clickable_links == len(maps_links):
                        print("\n🎉 GOOGLE MAPS LINKS FEATURE: ✅ WORKING CORRECTLY")
                        print("   ✅ AI provides restaurant recommendations WITH Google Maps links")
                        print("   ✅ Links are properly formatted with https://www.google.com/maps/search/?api=1&query=...")
                        print("   ✅ Links are clickable and contain proper URL encoding")
                        return True
                    else:
                        print("\n⚠️ GOOGLE MAPS LINKS FEATURE: PARTIALLY WORKING")
                        print(f"   Found {len(maps_links)} links but some may have formatting issues")
                        return False
                        
                else:
                    print("\n❌ GOOGLE MAPS LINKS FEATURE: NOT WORKING")
                    print("   ❌ No Google Maps links found in AI response")
                    print("   ❌ Expected format: https://www.google.com/maps/search/?api=1&query=...")
                    
                    # Check if response contains restaurant recommendations without links
                    if any(word in ai_response.lower() for word in ['restaurant', 'eat', 'food', 'dining']):
                        print("   ⚠️ AI provided restaurant recommendations but WITHOUT Google Maps links")
                    else:
                        print("   ❌ AI did not provide restaurant recommendations at all")
                    
                    return False
                    
            else:
                print(f"❌ Chat request failed with status {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error during chat request: {str(e)}")
            return False
    
    def validate_google_maps_link(self, link):
        """Validate Google Maps link format"""
        # Check required components
        required_parts = [
            'https://www.google.com/maps/search/',
            'api=1',
            'query='
        ]
        
        return all(part in link for part in required_parts)
    
    def extract_restaurant_recommendations(self, response):
        """Extract restaurant recommendations from AI response"""
        recommendations = []
        
        # Look for restaurant names followed by Google Maps links
        # Pattern: Restaurant name followed by maps link
        lines = response.split('\n')
        
        current_restaurant = None
        for line in lines:
            line = line.strip()
            
            # Look for restaurant indicators
            if any(indicator in line.lower() for indicator in ['restaurant', '🍽️', '🍴', '🥘', '🍕', '🍝']):
                # Extract restaurant name (usually after bullet point or number)
                name_match = re.search(r'[•\-\d\.]\s*\*?\*?([^(]+?)(?:\(|$)', line)
                if name_match:
                    restaurant_name = name_match.group(1).strip('*').strip()
                    current_restaurant = {
                        'name': restaurant_name,
                        'maps_link': None,
                        'full_text': line
                    }
            
            # Look for Google Maps links
            maps_link = re.search(r'https://www\.google\.com/maps/search/\?api=1&query=[^)\s]+', line)
            if maps_link and current_restaurant:
                current_restaurant['maps_link'] = maps_link.group(0)
                recommendations.append(current_restaurant)
                current_restaurant = None
        
        return recommendations
    
    def check_clickable_links(self, links):
        """Check if links are properly URL encoded and clickable"""
        clickable_count = 0
        
        for link in links:
            # Check if query parameter is properly encoded
            if 'query=' in link:
                query_part = link.split('query=')[1]
                # Should contain + for spaces or %20 for URL encoding
                if '+' in query_part or '%20' in query_part:
                    clickable_count += 1
                elif ' ' not in query_part:  # No spaces means it's likely encoded
                    clickable_count += 1
        
        return clickable_count
    
    def check_contextual_links(self, links):
        """Check if links contain location context"""
        contextual_count = 0
        
        location_indicators = [
            'sarajevo', 'bosnia', 'bih', 'city', 'downtown', 'center', 'centre'
        ]
        
        for link in links:
            link_lower = link.lower()
            if any(indicator in link_lower for indicator in location_indicators):
                contextual_count += 1
        
        return contextual_count
    
    def test_apartment_data_access(self):
        """Test if apartment data is accessible for the given apartment ID"""
        print("\n🔍 Testing Apartment Data Access...")
        
        # Test public apartment endpoint
        apartment_url = f"{self.api_url}/public/apartment/{self.apartment_id}"
        
        try:
            response = requests.get(apartment_url, timeout=30)
            
            if response.status_code == 200:
                apartment_data = response.json()
                print("✅ Apartment data accessible")
                
                # Check if apartment has restaurant recommendations
                recommendations = apartment_data.get('recommendations', {})
                restaurants = recommendations.get('restaurants', [])
                
                if restaurants:
                    print(f"   ✅ Found {len(restaurants)} restaurant recommendations in apartment data")
                    for i, restaurant in enumerate(restaurants[:3], 1):
                        name = restaurant.get('name', 'Unknown')
                        location = restaurant.get('location', 'No location')
                        print(f"   Restaurant {i}: {name} - {location}")
                else:
                    print("   ⚠️ No restaurant recommendations found in apartment data")
                    print("   ⚠️ AI will need to provide general recommendations")
                
                # Check apartment location for context
                address = apartment_data.get('address', '')
                if address:
                    print(f"   📍 Apartment address: {address}")
                    
                    # Extract city for context
                    if 'sarajevo' in address.lower():
                        print("   ✅ Apartment is in Sarajevo - AI should provide Sarajevo recommendations")
                    else:
                        print(f"   ⚠️ City context may be unclear from address: {address}")
                
                return True
            else:
                print(f"❌ Cannot access apartment data: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error accessing apartment data: {str(e)}")
            return False

def main():
    """Run Google Maps links test"""
    print("=" * 80)
    print("🗺️ GOOGLE MAPS LINKS FEATURE TEST")
    print("=" * 80)
    
    tester = GoogleMapsLinksTest()
    
    # Test 1: Check apartment data access
    apartment_accessible = tester.test_apartment_data_access()
    
    # Test 2: Test Google Maps links in chatbot
    maps_links_working = tester.test_google_maps_links_in_chatbot()
    
    # Final summary
    print("\n" + "=" * 80)
    print("📊 GOOGLE MAPS LINKS TEST SUMMARY")
    print("=" * 80)
    
    if apartment_accessible and maps_links_working:
        print("🎉 OVERALL RESULT: ✅ GOOGLE MAPS LINKS FEATURE WORKING")
        print("   ✅ Apartment data accessible")
        print("   ✅ AI provides restaurant recommendations WITH Google Maps links")
        print("   ✅ Links are properly formatted and clickable")
        print("\n✨ Expected behavior confirmed:")
        print("   - AI responds to restaurant questions")
        print("   - Includes clickable Google Maps links")
        print("   - Links use format: https://www.google.com/maps/search/?api=1&query=...")
    elif apartment_accessible and not maps_links_working:
        print("⚠️ OVERALL RESULT: ❌ GOOGLE MAPS LINKS FEATURE NOT WORKING")
        print("   ✅ Apartment data accessible")
        print("   ❌ AI does NOT include Google Maps links in responses")
        print("\n🔧 Issue: AI system prompt may not be enforcing Google Maps links requirement")
    else:
        print("❌ OVERALL RESULT: ❌ CRITICAL ISSUES FOUND")
        print("   ❌ Cannot properly test due to apartment data access issues")
    
    print("=" * 80)

if __name__ == "__main__":
    main()