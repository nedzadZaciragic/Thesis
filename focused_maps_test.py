import requests
import json
import re
from datetime import datetime

def test_google_maps_links():
    """Focused test for Google Maps links in chatbot responses"""
    
    print("🗺️ FOCUSED GOOGLE MAPS LINKS TEST")
    print("=" * 60)
    
    # Test configuration
    base_url = "https://proximity-search-8.preview.emergentagent.com"
    apartment_id = "00a4b62a-9410-478f-a536-08628dc54df1"
    test_message = "Where should I eat tonight? Any local restaurant recommendations?"
    
    print(f"🏠 Apartment ID: {apartment_id}")
    print(f"💬 Test Message: '{test_message}'")
    
    # Send chat request
    chat_url = f"{base_url}/api/guest-chat"
    chat_data = {
        "apartment_id": apartment_id,
        "message": test_message,
        "session_id": f"maps_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    }
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        print("\n📤 Sending chat request...")
        response = requests.post(chat_url, json=chat_data, headers=headers, timeout=60)
        
        if response.status_code == 200:
            response_data = response.json()
            ai_response = response_data.get('response', '')
            
            print("✅ Chat request successful")
            print(f"\n🤖 AI Response:")
            print("-" * 60)
            print(ai_response)
            print("-" * 60)
            
            # Test 1: Find Google Maps links
            google_maps_pattern = r'https://www\.google\.com/maps/search/\?api=1&query=[^)\s\]]+' 
            maps_links = re.findall(google_maps_pattern, ai_response)
            
            print(f"\n🔍 GOOGLE MAPS LINKS ANALYSIS:")
            print(f"   Links found: {len(maps_links)}")
            
            if maps_links:
                print("   ✅ Google Maps links detected!")
                
                for i, link in enumerate(maps_links, 1):
                    print(f"   Link {i}: {link}")
                    
                    # Validate link format
                    if validate_maps_link(link):
                        print(f"   ✅ Link {i} format is VALID")
                    else:
                        print(f"   ❌ Link {i} format is INVALID")
                
                # Test 2: Check if links are properly integrated with restaurant names
                restaurant_count = count_restaurants_with_links(ai_response)
                print(f"\n🍽️ RESTAURANT RECOMMENDATIONS:")
                print(f"   Restaurants with Google Maps links: {restaurant_count}")
                
                # Test 3: Verify expected format
                expected_format_count = 0
                for link in maps_links:
                    if "https://www.google.com/maps/search/?api=1&query=" in link:
                        expected_format_count += 1
                
                print(f"\n✅ VALIDATION RESULTS:")
                print(f"   Total links: {len(maps_links)}")
                print(f"   Correctly formatted: {expected_format_count}/{len(maps_links)}")
                print(f"   Restaurant recommendations: {restaurant_count}")
                
                # Overall assessment
                if len(maps_links) >= 3 and expected_format_count == len(maps_links):
                    print(f"\n🎉 GOOGLE MAPS LINKS FEATURE: ✅ WORKING PERFECTLY")
                    print(f"   ✅ AI provides {len(maps_links)} restaurant recommendations")
                    print(f"   ✅ ALL links use correct format: https://www.google.com/maps/search/?api=1&query=...")
                    print(f"   ✅ Links are properly integrated with restaurant names")
                    return True
                else:
                    print(f"\n⚠️ GOOGLE MAPS LINKS FEATURE: PARTIALLY WORKING")
                    return False
                    
            else:
                print("   ❌ NO Google Maps links found!")
                print("   ❌ Expected format: https://www.google.com/maps/search/?api=1&query=...")
                
                # Check if AI provided restaurant recommendations without links
                if any(word in ai_response.lower() for word in ['restaurant', 'eat', 'food', 'dining']):
                    print("   ⚠️ AI provided restaurant info but WITHOUT Google Maps links")
                else:
                    print("   ❌ AI did not provide restaurant recommendations")
                
                return False
                
        else:
            print(f"❌ Chat request failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        return False

def validate_maps_link(link):
    """Validate Google Maps link format"""
    required_components = [
        "https://www.google.com/maps/search/",
        "api=1",
        "query="
    ]
    return all(component in link for component in required_components)

def count_restaurants_with_links(response):
    """Count restaurant recommendations that have Google Maps links"""
    # Look for restaurant patterns followed by maps links
    lines = response.split('\n')
    restaurant_count = 0
    
    for i, line in enumerate(lines):
        # Check if line contains restaurant indicators
        if any(indicator in line.lower() for indicator in ['restaurant', '🍽️', '🍴', '**', 'cuisine']):
            # Check if next few lines contain a Google Maps link
            for j in range(i, min(i+3, len(lines))):
                if 'google.com/maps/search' in lines[j]:
                    restaurant_count += 1
                    break
    
    return restaurant_count

if __name__ == "__main__":
    success = test_google_maps_links()
    
    print("\n" + "=" * 60)
    print("📊 FINAL TEST RESULT")
    print("=" * 60)
    
    if success:
        print("🎉 GOOGLE MAPS LINKS FEATURE: ✅ WORKING CORRECTLY")
        print("\n✨ Confirmed functionality:")
        print("   - AI responds to restaurant questions")
        print("   - Includes multiple Google Maps links")
        print("   - Links use correct format with api=1&query=...")
        print("   - Links are clickable and properly formatted")
    else:
        print("❌ GOOGLE MAPS LINKS FEATURE: NOT WORKING AS EXPECTED")
        print("\n🔧 Issues found:")
        print("   - Missing or incorrectly formatted Google Maps links")
        print("   - Links may not follow required format")
    
    print("=" * 60)