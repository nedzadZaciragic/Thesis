#!/usr/bin/env python3
"""
Test Email Send - Send a real welcome email with chatbot link
"""

import os
import sys
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

# Load environment
load_dotenv('/app/backend/.env')

SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')

def send_test_email():
    """Send test email to nedzadzaciragic7@gmail.com"""
    
    # Email content
    guest_email = "nedzadzaciragic7@gmail.com"
    guest_name = "Nedzad"
    apartment_name = "Test Apartment - MyHostIQ Demo"
    chatbot_link = "https://thesis-deployment.preview.emergentagent.com/guest/test-apartment-id"
    
    subject = f"🏠 Welcome to {apartment_name} - Your AI Assistant is Ready!"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
                border-radius: 10px 10px 0 0;
            }}
            .content {{
                background: #f9fafb;
                padding: 30px;
                border-radius: 0 0 10px 10px;
            }}
            .button {{
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 15px 30px;
                text-decoration: none;
                border-radius: 8px;
                margin: 20px 0;
                font-weight: 600;
            }}
            .feature {{
                background: white;
                padding: 15px;
                margin: 15px 0;
                border-radius: 8px;
                border-left: 4px solid #667eea;
            }}
            .footer {{
                text-align: center;
                padding: 20px;
                color: #666;
                font-size: 14px;
            }}
            .emoji {{
                font-size: 24px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎉 Welcome {guest_name}!</h1>
            <p>Your AI Assistant is Ready to Help</p>
        </div>
        
        <div class="content">
            <p>Hi {guest_name},</p>
            
            <p>Welcome to <strong>{apartment_name}</strong>! We're excited to have you as our guest.</p>
            
            <p><strong>📱 Your 24/7 AI Assistant is ready to help you with:</strong></p>
            
            <div class="feature">
                <span class="emoji">🔑</span>
                <strong>Check-in Instructions</strong> - Step-by-step guidance
            </div>
            
            <div class="feature">
                <span class="emoji">📶</span>
                <strong>WiFi & Amenities</strong> - Instant access info
            </div>
            
            <div class="feature">
                <span class="emoji">🍝</span>
                <strong>Restaurant Recommendations</strong> - Local favorites
            </div>
            
            <div class="feature">
                <span class="emoji">🚇</span>
                <strong>Transport Info</strong> - Getting around the city
            </div>
            
            <div class="feature">
                <span class="emoji">🆘</span>
                <strong>Emergency Contacts</strong> - Always available
            </div>
            
            <div class="feature">
                <span class="emoji">💎</span>
                <strong>Local Hidden Gems</strong> - Discover the best spots
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{chatbot_link}" class="button">
                    💬 Chat with Your AI Assistant
                </a>
            </div>
            
            <p style="background: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107;">
                <strong>💡 Pro Tip:</strong> Save this link! You can access your AI assistant anytime during your stay for instant answers to any questions.
            </p>
            
            <p style="margin-top: 30px;">
                <strong>📅 Your Stay:</strong><br>
                This is a <strong>TEST EMAIL</strong> to verify the email system is working correctly.
            </p>
            
            <p>Looking forward to making your stay amazing!</p>
            
            <p style="margin-top: 30px;">
                <strong>🏠 MyHostIQ Team</strong><br>
                <em>Your 24/7 AI-powered guest assistant</em>
            </p>
        </div>
        
        <div class="footer">
            <p>This is a test email from MyHostIQ email system</p>
            <p style="font-size: 12px; color: #999;">
                Sent via SendGrid • MyHostIQ Platform Test
            </p>
        </div>
    </body>
    </html>
    """
    
    try:
        print(f"📧 Sending test email to: {guest_email}")
        print(f"📨 Subject: {subject}")
        print(f"🔗 Chatbot Link: {chatbot_link}")
        
        message = Mail(
            from_email='noreply@myhostiq.com',
            to_emails=guest_email,
            subject=subject,
            html_content=html_content
        )
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        print(f"\n✅ EMAIL SENT SUCCESSFULLY!")
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Response Headers: {response.headers}")
        print(f"\n🎯 Check your email: {guest_email}")
        print(f"📬 Subject line: {subject}")
        print(f"\n💡 The email contains:")
        print(f"   - Welcome message")
        print(f"   - List of AI assistant features")
        print(f"   - Clickable chatbot link button")
        print(f"   - Professional HTML design")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR sending email: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 MyHostIQ Email System Test")
    print("=" * 60)
    print()
    
    success = send_test_email()
    
    print()
    print("=" * 60)
    if success:
        print("✅ TEST COMPLETED SUCCESSFULLY")
        print("📧 Email should arrive within 1-2 minutes")
    else:
        print("❌ TEST FAILED")
    print("=" * 60)
