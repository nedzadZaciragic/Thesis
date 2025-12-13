#!/usr/bin/env python3
"""
Quick test to get a valid apartment ID for guest chat testing.
This script logs in as admin and returns the first apartment ID.
"""

import requests
import json
import sys

def get_apartment_id():
    """Get a valid apartment ID for testing guest chat"""
    
    base_url = "https://sarajevo-finder.preview.emergentagent.com"
    api_url = f"{base_url}/api"
    
    print("🔍 Getting apartment ID for guest chat testing...")
    
    # Step 1: Login as admin
    print("\n1. Logging in as admin...")
    admin_credentials = {
        "username": "myhomeiq_admin",
        "password": "Admin123!MyHomeIQ"
    }
    
    try:
        login_response = requests.post(
            f"{api_url}/admin/login",
            json=admin_credentials,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if login_response.status_code == 200:
            login_data = login_response.json()
            admin_token = login_data.get('access_token')
            print(f"✅ Admin login successful")
            print(f"   Token: {admin_token[:20]}...")
        else:
            print(f"❌ Admin login failed: {login_response.status_code}")
            print(f"   Response: {login_response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Admin login error: {str(e)}")
        return None
    
    # Step 2: Get list of apartments
    print("\n2. Getting list of apartments...")
    
    try:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {admin_token}'
        }
        
        apartments_response = requests.get(
            f"{api_url}/admin/apartments",
            headers=headers,
            timeout=30
        )
        
        if apartments_response.status_code == 200:
            apartments_data = apartments_response.json()
            apartments = apartments_data if isinstance(apartments_data, list) else apartments_data.get('apartments', [])
            
            print(f"✅ Found {len(apartments)} apartments")
            
            if apartments:
                # Get the first apartment
                first_apartment = apartments[0]
                apartment_id = first_apartment.get('id')
                apartment_name = first_apartment.get('name', 'Unknown')
                apartment_address = first_apartment.get('address', 'Unknown')
                
                print(f"\n🎯 APARTMENT ID FOR TESTING: {apartment_id}")
                print(f"   Name: {apartment_name}")
                print(f"   Address: {apartment_address}")
                
                # Show guest chat URL
                guest_chat_url = f"{base_url}/guest/{apartment_id}"
                print(f"\n🔗 Guest Chat URL: {guest_chat_url}")
                
                # Show a few more apartments for options
                print(f"\n📋 Available apartments (first 5):")
                for i, apt in enumerate(apartments[:5]):
                    print(f"   {i+1}. ID: {apt.get('id')} - {apt.get('name', 'Unknown')}")
                
                return apartment_id
            else:
                print("❌ No apartments found")
                return None
                
        else:
            print(f"❌ Failed to get apartments: {apartments_response.status_code}")
            print(f"   Response: {apartments_response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting apartments: {str(e)}")
        return None

if __name__ == "__main__":
    apartment_id = get_apartment_id()
    
    if apartment_id:
        print(f"\n✅ SUCCESS: Use apartment ID '{apartment_id}' for guest chat testing")
        print(f"🔗 Test URL: https://sarajevo-finder.preview.emergentagent.com/guest/{apartment_id}")
        sys.exit(0)
    else:
        print(f"\n❌ FAILED: Could not get apartment ID")
        sys.exit(1)