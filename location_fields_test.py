import requests
import sys
import json
from datetime import datetime
import time

class LocationFieldsTester:
    def __init__(self, base_url="https://sarajevo-finder.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.token = None
        self.user_id = None
        self.admin_token = None
        self.created_apartment_ids = []
        
        # Test user data
        self.test_user = {
            "email": "locationtest@example.com",
            "full_name": "Location Test User",
            "password": "testpass123"
        }
        
        # Admin credentials
        self.admin_credentials = {
            "username": "myhomeiq_admin",
            "password": "Admin123!MyHomeIQ"
        }

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30, use_auth=True, use_admin=False):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'}
        
        # Add authentication header
        if use_auth:
            if use_admin and self.admin_token:
                headers['Authorization'] = f'Bearer {self.admin_token}'
            elif self.token:
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
        print("\n🔧 Setting up authentication...")
        
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
        
        print("   ❌ Failed to authenticate")
        return False

    def setup_admin_authentication(self):
        """Setup admin authentication"""
        print("\n🔧 Setting up admin authentication...")
        
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
        
        print("   ❌ Failed to authenticate admin")
        return False

    def test_create_apartment_with_location_fields(self):
        """Test creating apartment with location fields in recommendations"""
        print("\n🏠 Testing apartment creation with location fields...")
        
        # Test apartment with restaurants including location field
        apartment_data = {
            "name": "Mario's Italian Villa",
            "address": "Via Roma 123, Rome, Italy",
            "description": "Beautiful apartment in the heart of Rome",
            "rules": ["No smoking", "No parties"],
            "contact": {"email": "host@example.com", "phone": "+39 123 456 789"},
            "ical_url": "",
            "ai_tone": "friendly",
            "recommendations": {
                "restaurants": [
                    {
                        "name": "Mario's Pizza",
                        "type": "Italian",
                        "location": "Via Roma 123",
                        "tip": "Best pizza in town"
                    },
                    {
                        "name": "Trattoria del Centro",
                        "type": "Traditional Italian",
                        "location": "Piazza Navona 45",
                        "tip": "Authentic Roman cuisine"
                    }
                ],
                "hidden_gems": [
                    {
                        "name": "Secret Garden",
                        "location": "Behind the old church",
                        "tip": "Beautiful sunset views"
                    },
                    {
                        "name": "Rooftop Terrace",
                        "location": "Via del Corso 100, 5th floor",
                        "tip": "Amazing city panorama"
                    }
                ],
                "transport": "Metro station 2 minutes walk"
            },
            "check_in_time": "15:00",
            "check_out_time": "11:00",
            "check_in_instructions": "Keys are under the blue mat",
            "apartment_locations": {
                "keys": "under the mat",
                "towels": "bathroom closet"
            },
            "wifi_network": "RomeWiFi",
            "wifi_password": "password123",
            "wifi_instructions": "Router is in living room"
        }
        
        success, response = self.run_test(
            "Create Apartment with Location Fields",
            "POST",
            "apartments",
            200,
            data=apartment_data
        )
        
        if success and response.get('id'):
            apartment_id = response['id']
            self.created_apartment_ids.append(apartment_id)
            print(f"   ✅ Created apartment: {apartment_id}")
            
            # Verify location fields are included in response
            recommendations = response.get('recommendations', {})
            restaurants = recommendations.get('restaurants', [])
            hidden_gems = recommendations.get('hidden_gems', [])
            
            # Check restaurants have location fields
            restaurants_with_location = [r for r in restaurants if 'location' in r]
            if len(restaurants_with_location) == 2:
                print("   ✅ All restaurants include location field")
                for restaurant in restaurants_with_location:
                    print(f"      - {restaurant['name']}: {restaurant['location']}")
            else:
                print(f"   ❌ Expected 2 restaurants with location, got {len(restaurants_with_location)}")
                return False
            
            # Check hidden gems have location fields
            gems_with_location = [g for g in hidden_gems if 'location' in g]
            if len(gems_with_location) == 2:
                print("   ✅ All hidden gems include location field")
                for gem in gems_with_location:
                    print(f"      - {gem['name']}: {gem['location']}")
            else:
                print(f"   ❌ Expected 2 hidden gems with location, got {len(gems_with_location)}")
                return False
            
            return True
        
        return False

    def test_retrieve_apartment_with_location_fields(self):
        """Test retrieving apartments with location fields"""
        if not self.created_apartment_ids:
            print("❌ No apartments available for testing")
            return False
        
        apartment_id = self.created_apartment_ids[0]
        print(f"\n📖 Testing apartment retrieval with location fields for {apartment_id}...")
        
        # Test GET /api/apartments/{id}
        success, response = self.run_test(
            "Get Apartment with Location Fields",
            "GET",
            f"apartments/{apartment_id}",
            200
        )
        
        if success:
            recommendations = response.get('recommendations', {})
            restaurants = recommendations.get('restaurants', [])
            hidden_gems = recommendations.get('hidden_gems', [])
            
            # Verify location fields are returned
            restaurants_with_location = [r for r in restaurants if 'location' in r and r['location']]
            gems_with_location = [g for g in hidden_gems if 'location' in g and g['location']]
            
            if restaurants_with_location and gems_with_location:
                print("   ✅ Location fields properly returned in GET response")
                print(f"      Restaurants with location: {len(restaurants_with_location)}")
                print(f"      Hidden gems with location: {len(gems_with_location)}")
                
                # Verify specific location data
                mario_pizza = next((r for r in restaurants if r['name'] == "Mario's Pizza"), None)
                if mario_pizza and mario_pizza.get('location') == "Via Roma 123":
                    print("   ✅ Mario's Pizza location correctly retrieved")
                else:
                    print("   ❌ Mario's Pizza location not found or incorrect")
                    return False
                
                secret_garden = next((g for g in hidden_gems if g['name'] == "Secret Garden"), None)
                if secret_garden and secret_garden.get('location') == "Behind the old church":
                    print("   ✅ Secret Garden location correctly retrieved")
                else:
                    print("   ❌ Secret Garden location not found or incorrect")
                    return False
                
                return True
            else:
                print("   ❌ Location fields missing in GET response")
                return False
        
        return False

    def test_admin_endpoints_with_location_fields(self):
        """Test admin endpoints return location fields"""
        if not self.admin_token:
            if not self.setup_admin_authentication():
                print("❌ Cannot test admin endpoints without authentication")
                return False
        
        print("\n👑 Testing admin endpoints with location fields...")
        
        # Test GET /api/admin/apartments
        success, response = self.run_test(
            "Admin Get All Apartments",
            "GET",
            "admin/apartments",
            200,
            use_admin=True
        )
        
        if success:
            apartments = response.get('apartments', [])
            if apartments:
                # Find our test apartment
                test_apartment = None
                for apt in apartments:
                    if apt.get('id') in self.created_apartment_ids:
                        test_apartment = apt
                        break
                
                if test_apartment:
                    recommendations = test_apartment.get('recommendations', {})
                    restaurants = recommendations.get('restaurants', [])
                    hidden_gems = recommendations.get('hidden_gems', [])
                    
                    # Check location fields are present
                    restaurants_with_location = [r for r in restaurants if 'location' in r and r['location']]
                    gems_with_location = [g for g in hidden_gems if 'location' in g and g['location']]
                    
                    if restaurants_with_location and gems_with_location:
                        print("   ✅ Admin endpoint returns location fields")
                        print(f"      Restaurants with location: {len(restaurants_with_location)}")
                        print(f"      Hidden gems with location: {len(gems_with_location)}")
                        return True
                    else:
                        print("   ❌ Admin endpoint missing location fields")
                        return False
                else:
                    print("   ❌ Test apartment not found in admin response")
                    return False
            else:
                print("   ❌ No apartments returned by admin endpoint")
                return False
        
        return False

    def test_update_apartment_with_location_fields(self):
        """Test updating apartments with location fields"""
        if not self.created_apartment_ids:
            print("❌ No apartments available for testing")
            return False
        
        apartment_id = self.created_apartment_ids[0]
        print(f"\n✏️ Testing apartment update with location fields for {apartment_id}...")
        
        # First get current apartment data
        success, current_data = self.run_test(
            "Get Current Apartment Data",
            "GET",
            f"apartments/{apartment_id}",
            200
        )
        
        if not success:
            print("   ❌ Failed to get current apartment data")
            return False
        
        # Update with new location fields
        updated_data = current_data.copy()
        updated_data['recommendations']['restaurants'].append({
            "name": "New Pizzeria",
            "type": "Pizza",
            "location": "Via Nuova 456",
            "tip": "Great late night option"
        })
        
        updated_data['recommendations']['hidden_gems'].append({
            "name": "Hidden Courtyard",
            "location": "Through the green door on Via Antica",
            "tip": "Peaceful spot for morning coffee"
        })
        
        # Remove fields that shouldn't be in update request
        for field in ['id', 'user_id', 'created_at', 'total_chats', 'total_sessions', 'last_chat', 'last_ical_sync']:
            updated_data.pop(field, None)
        
        success, response = self.run_test(
            "Update Apartment with New Location Fields",
            "PUT",
            f"apartments/{apartment_id}",
            200,
            data=updated_data
        )
        
        if success:
            recommendations = response.get('recommendations', {})
            restaurants = recommendations.get('restaurants', [])
            hidden_gems = recommendations.get('hidden_gems', [])
            
            # Check new restaurant with location
            new_pizzeria = next((r for r in restaurants if r['name'] == "New Pizzeria"), None)
            if new_pizzeria and new_pizzeria.get('location') == "Via Nuova 456":
                print("   ✅ New restaurant with location field added successfully")
            else:
                print("   ❌ New restaurant with location field not found")
                return False
            
            # Check new hidden gem with location
            hidden_courtyard = next((g for g in hidden_gems if g['name'] == "Hidden Courtyard"), None)
            if hidden_courtyard and hidden_courtyard.get('location') == "Through the green door on Via Antica":
                print("   ✅ New hidden gem with location field added successfully")
            else:
                print("   ❌ New hidden gem with location field not found")
                return False
            
            # Verify original location fields are still there
            mario_pizza = next((r for r in restaurants if r['name'] == "Mario's Pizza"), None)
            if mario_pizza and mario_pizza.get('location') == "Via Roma 123":
                print("   ✅ Original restaurant location field preserved")
            else:
                print("   ❌ Original restaurant location field lost")
                return False
            
            return True
        
        return False

    def test_backward_compatibility_without_location_fields(self):
        """Test backward compatibility - apartments without location fields"""
        print("\n🔄 Testing backward compatibility without location fields...")
        
        # Create apartment with recommendations but no location fields
        apartment_data = {
            "name": "Legacy Apartment",
            "address": "Old Street 123",
            "description": "Apartment without location fields",
            "rules": ["No smoking"],
            "contact": {"email": "legacy@example.com"},
            "ical_url": "",
            "recommendations": {
                "restaurants": [
                    {
                        "name": "Old Restaurant",
                        "type": "Traditional",
                        "tip": "Good food, no location specified"
                    }
                ],
                "hidden_gems": [
                    {
                        "name": "Old Gem",
                        "tip": "Nice place, no location specified"
                    }
                ],
                "transport": "Bus stop nearby"
            }
        }
        
        success, response = self.run_test(
            "Create Legacy Apartment (No Location Fields)",
            "POST",
            "apartments",
            200,
            data=apartment_data
        )
        
        if success and response.get('id'):
            legacy_apartment_id = response['id']
            self.created_apartment_ids.append(legacy_apartment_id)
            print(f"   ✅ Created legacy apartment: {legacy_apartment_id}")
            
            # Verify apartment works without location fields
            recommendations = response.get('recommendations', {})
            restaurants = recommendations.get('restaurants', [])
            hidden_gems = recommendations.get('hidden_gems', [])
            
            if restaurants and hidden_gems:
                print("   ✅ Apartment created successfully without location fields")
                
                # Verify no location fields are present (or they're empty)
                for restaurant in restaurants:
                    if 'location' in restaurant and restaurant['location']:
                        print("   ❌ Unexpected location field in legacy restaurant")
                        return False
                
                for gem in hidden_gems:
                    if 'location' in gem and gem['location']:
                        print("   ❌ Unexpected location field in legacy hidden gem")
                        return False
                
                print("   ✅ No location fields present in legacy recommendations")
                
                # Test retrieval
                success2, response2 = self.run_test(
                    "Get Legacy Apartment",
                    "GET",
                    f"apartments/{legacy_apartment_id}",
                    200
                )
                
                if success2:
                    print("   ✅ Legacy apartment retrieval works")
                    return True
                else:
                    print("   ❌ Legacy apartment retrieval failed")
                    return False
            else:
                print("   ❌ Legacy apartment missing recommendations")
                return False
        
        return False

    def test_mixed_recommendations_with_and_without_location(self):
        """Test recommendations with mixed location fields (some have, some don't)"""
        print("\n🔀 Testing mixed recommendations (with and without location fields)...")
        
        # Create apartment with mixed recommendations
        apartment_data = {
            "name": "Mixed Recommendations Apartment",
            "address": "Mixed Street 789",
            "description": "Apartment with mixed recommendation formats",
            "rules": ["No smoking"],
            "contact": {"email": "mixed@example.com"},
            "ical_url": "",
            "recommendations": {
                "restaurants": [
                    {
                        "name": "Restaurant with Location",
                        "type": "Modern",
                        "location": "Downtown Plaza 1",
                        "tip": "Has location field"
                    },
                    {
                        "name": "Restaurant without Location",
                        "type": "Traditional",
                        "tip": "No location field"
                    }
                ],
                "hidden_gems": [
                    {
                        "name": "Gem with Location",
                        "location": "Secret alley behind main street",
                        "tip": "Has location field"
                    },
                    {
                        "name": "Gem without Location",
                        "tip": "No location field"
                    }
                ]
            }
        }
        
        success, response = self.run_test(
            "Create Mixed Recommendations Apartment",
            "POST",
            "apartments",
            200,
            data=apartment_data
        )
        
        if success and response.get('id'):
            mixed_apartment_id = response['id']
            self.created_apartment_ids.append(mixed_apartment_id)
            print(f"   ✅ Created mixed apartment: {mixed_apartment_id}")
            
            # Verify mixed recommendations work
            recommendations = response.get('recommendations', {})
            restaurants = recommendations.get('restaurants', [])
            hidden_gems = recommendations.get('hidden_gems', [])
            
            # Check restaurants
            restaurant_with_location = next((r for r in restaurants if r['name'] == "Restaurant with Location"), None)
            restaurant_without_location = next((r for r in restaurants if r['name'] == "Restaurant without Location"), None)
            
            if restaurant_with_location and restaurant_with_location.get('location') == "Downtown Plaza 1":
                print("   ✅ Restaurant with location field works")
            else:
                print("   ❌ Restaurant with location field failed")
                return False
            
            if restaurant_without_location and ('location' not in restaurant_without_location or not restaurant_without_location.get('location')):
                print("   ✅ Restaurant without location field works")
            else:
                print("   ❌ Restaurant without location field has unexpected location")
                return False
            
            # Check hidden gems
            gem_with_location = next((g for g in hidden_gems if g['name'] == "Gem with Location"), None)
            gem_without_location = next((g for g in hidden_gems if g['name'] == "Gem without Location"), None)
            
            if gem_with_location and gem_with_location.get('location') == "Secret alley behind main street":
                print("   ✅ Hidden gem with location field works")
            else:
                print("   ❌ Hidden gem with location field failed")
                return False
            
            if gem_without_location and ('location' not in gem_without_location or not gem_without_location.get('location')):
                print("   ✅ Hidden gem without location field works")
            else:
                print("   ❌ Hidden gem without location field has unexpected location")
                return False
            
            # Test retrieval to ensure persistence
            success2, response2 = self.run_test(
                "Get Mixed Recommendations Apartment",
                "GET",
                f"apartments/{mixed_apartment_id}",
                200
            )
            
            if success2:
                print("   ✅ Mixed recommendations apartment retrieval works")
                
                # Verify data persistence
                recommendations2 = response2.get('recommendations', {})
                restaurants2 = recommendations2.get('restaurants', [])
                hidden_gems2 = recommendations2.get('hidden_gems', [])
                
                restaurants_with_location = [r for r in restaurants2 if 'location' in r and r['location']]
                restaurants_without_location = [r for r in restaurants2 if 'location' not in r or not r['location']]
                
                if len(restaurants_with_location) == 1 and len(restaurants_without_location) == 1:
                    print("   ✅ Mixed restaurant location fields persisted correctly")
                else:
                    print(f"   ❌ Mixed restaurant persistence failed: {len(restaurants_with_location)} with, {len(restaurants_without_location)} without")
                    return False
                
                gems_with_location = [g for g in hidden_gems2 if 'location' in g and g['location']]
                gems_without_location = [g for g in hidden_gems2 if 'location' not in g or not g['location']]
                
                if len(gems_with_location) == 1 and len(gems_without_location) == 1:
                    print("   ✅ Mixed hidden gem location fields persisted correctly")
                    return True
                else:
                    print(f"   ❌ Mixed hidden gem persistence failed: {len(gems_with_location)} with, {len(gems_without_location)} without")
                    return False
            else:
                print("   ❌ Mixed recommendations apartment retrieval failed")
                return False
        
        return False

    def test_location_fields_in_mongodb_storage(self):
        """Test that location fields are properly stored in MongoDB"""
        if not self.created_apartment_ids:
            print("❌ No apartments available for testing")
            return False
        
        apartment_id = self.created_apartment_ids[0]
        print(f"\n💾 Testing MongoDB storage of location fields for {apartment_id}...")
        
        # Get apartment data multiple times to ensure consistency
        success1, response1 = self.run_test(
            "Get Apartment Data - First Retrieval",
            "GET",
            f"apartments/{apartment_id}",
            200
        )
        
        time.sleep(1)  # Small delay
        
        success2, response2 = self.run_test(
            "Get Apartment Data - Second Retrieval",
            "GET",
            f"apartments/{apartment_id}",
            200
        )
        
        if success1 and success2:
            # Compare location fields between retrievals
            recs1 = response1.get('recommendations', {})
            recs2 = response2.get('recommendations', {})
            
            restaurants1 = recs1.get('restaurants', [])
            restaurants2 = recs2.get('restaurants', [])
            
            hidden_gems1 = recs1.get('hidden_gems', [])
            hidden_gems2 = recs2.get('hidden_gems', [])
            
            # Check consistency
            if restaurants1 == restaurants2 and hidden_gems1 == hidden_gems2:
                print("   ✅ Location fields consistently retrieved from MongoDB")
                
                # Verify specific location data is preserved
                mario_pizza1 = next((r for r in restaurants1 if r['name'] == "Mario's Pizza"), None)
                mario_pizza2 = next((r for r in restaurants2 if r['name'] == "Mario's Pizza"), None)
                
                if (mario_pizza1 and mario_pizza2 and 
                    mario_pizza1.get('location') == mario_pizza2.get('location') == "Via Roma 123"):
                    print("   ✅ Specific location data consistently stored")
                    return True
                else:
                    print("   ❌ Specific location data inconsistent")
                    return False
            else:
                print("   ❌ Location fields inconsistent between retrievals")
                return False
        
        return False

    def cleanup_test_data(self):
        """Clean up created test apartments"""
        print("\n🧹 Cleaning up test data...")
        
        for apartment_id in self.created_apartment_ids:
            success, response = self.run_test(
                f"Delete Test Apartment {apartment_id}",
                "DELETE",
                f"apartments/{apartment_id}",
                200
            )
            
            if success:
                print(f"   ✅ Deleted apartment {apartment_id}")
            else:
                print(f"   ⚠️ Failed to delete apartment {apartment_id}")

    def run_all_tests(self):
        """Run all location fields tests"""
        print("🚀 Starting Location Fields Testing for MyHostIQ")
        print("=" * 60)
        
        # Setup
        if not self.setup_authentication():
            print("❌ Authentication setup failed")
            return False
        
        # Run tests
        tests = [
            self.test_create_apartment_with_location_fields,
            self.test_retrieve_apartment_with_location_fields,
            self.test_admin_endpoints_with_location_fields,
            self.test_update_apartment_with_location_fields,
            self.test_backward_compatibility_without_location_fields,
            self.test_mixed_recommendations_with_and_without_location,
            self.test_location_fields_in_mongodb_storage
        ]
        
        failed_tests = []
        
        for test in tests:
            try:
                if not test():
                    failed_tests.append(test.__name__)
            except Exception as e:
                print(f"❌ Test {test.__name__} crashed: {str(e)}")
                failed_tests.append(test.__name__)
        
        # Cleanup
        self.cleanup_test_data()
        
        # Results
        print("\n" + "=" * 60)
        print("🏁 LOCATION FIELDS TESTING RESULTS")
        print("=" * 60)
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if failed_tests:
            print(f"\n❌ Failed Tests ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"   - {test}")
        else:
            print("\n✅ All location fields tests passed!")
        
        return len(failed_tests) == 0

if __name__ == "__main__":
    tester = LocationFieldsTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)