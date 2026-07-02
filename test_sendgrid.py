#!/usr/bin/env python3
"""
Test SendGrid API key and email sending functionality
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

def test_sendgrid_api_key():
    """Test if SendGrid API key is valid"""
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        api_key = os.environ.get('SENDGRID_API_KEY')
        print(f"SendGrid API Key: {api_key[:10]}..." if api_key else "No API key found")
        
        if not api_key or api_key == 'your-sendgrid-api-key-here':
            print("❌ SendGrid API key not configured")
            return False
        
        # Test API key validity by creating a client
        sg = SendGridAPIClient(api_key)
        
        # Create a test email (won't be sent, just validates API key format)
        message = Mail(
            from_email='noreply@myhostiq.com',
            to_emails='test@example.com',
            subject='Test Email',
            html_content='<p>Test email content</p>'
        )
        
        # Try to send (this will fail if API key is invalid)
        response = sg.send(message)
        
        if response.status_code == 202:
            print("✅ SendGrid API key is valid and email sent successfully")
            return True
        else:
            print(f"⚠️  SendGrid returned status code: {response.status_code}")
            print(f"Response: {response.body}")
            return False
            
    except Exception as e:
        print(f"❌ SendGrid test failed: {str(e)}")
        if "403" in str(e) or "Forbidden" in str(e):
            print("   This indicates the API key is invalid or doesn't have permission")
        elif "401" in str(e) or "Unauthorized" in str(e):
            print("   This indicates the API key is invalid")
        return False

def test_forgot_password_endpoint():
    """Test the forgot password endpoint directly"""
    import requests
    
    try:
        # Test the endpoint
        url = "https://thesis-deployment.preview.emergentagent.com/api/auth/forgot-password"
        data = {"email": "test.sendgrid@example.com"}
        
        response = requests.post(url, json=data, timeout=30)
        
        print(f"Forgot password endpoint status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Forgot password endpoint working")
            return True
        else:
            print("❌ Forgot password endpoint failed")
            return False
            
    except Exception as e:
        print(f"❌ Endpoint test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔍 Testing SendGrid Configuration...")
    print("=" * 50)
    
    # Test 1: API Key validation
    print("\n1. Testing SendGrid API Key...")
    api_key_valid = test_sendgrid_api_key()
    
    # Test 2: Endpoint functionality
    print("\n2. Testing Forgot Password Endpoint...")
    endpoint_working = test_forgot_password_endpoint()
    
    print("\n" + "=" * 50)
    print("📊 SENDGRID TEST RESULTS")
    print("=" * 50)
    
    if api_key_valid and endpoint_working:
        print("✅ SendGrid is properly configured and working")
        sys.exit(0)
    elif endpoint_working:
        print("⚠️  Endpoint works but SendGrid may have issues")
        print("   Check SendGrid dashboard for delivery status")
        sys.exit(0)
    else:
        print("❌ SendGrid configuration has issues")
        print("\n🔧 Troubleshooting steps:")
        print("   1. Verify SendGrid API key is correct")
        print("   2. Check SendGrid account status")
        print("   3. Verify sender domain authentication")
        print("   4. Check SendGrid dashboard for errors")
        sys.exit(1)