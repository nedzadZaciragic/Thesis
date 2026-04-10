import requests
import json
import re
import time

def test_markdown_consistency():
    """Test consistency of markdown removal across multiple requests"""
    
    base_url = "https://proximity-search-8.preview.emergentagent.com/api"
    apartment_id = "00a4b62a-9410-478f-a536-08628dc54df1"
    
    # Test queries that might trigger markdown
    test_queries = [
        "Where can I go for drinks tonight?",
        "Can you recommend some bars?", 
        "What are the best nightlife spots?",
        "Where should I eat dinner?",
        "Can you recommend restaurants?",
        "What are some good coffee places?",
        "What attractions are nearby?",
        "What are some hidden gems?",
        "Where can I go shopping?",
        "What's the best way to get around?"
    ]
    
    results = []
    
    print("🔍 Testing Markdown Consistency Across Multiple Requests")
    print("=" * 60)
    
    for i, query in enumerate(test_queries):
        print(f"\nTest {i+1}/10: {query}")
        
        chat_data = {
            "apartment_id": apartment_id,
            "message": query,
            "session_id": f"consistency_test_{i}"
        }
        
        try:
            response = requests.post(
                f"{base_url}/guest-chat",
                json=chat_data,
                headers={'Content-Type': 'application/json'},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                ai_response = data.get('response', '')
                
                # Check for markdown patterns
                markdown_patterns = [
                    (r'\*\*[^*]+\*\*', 'Bold (**text**)'),
                    (r'\*[^*\s][^*]*\*', 'Italic (*text*)'),
                    (r'#{1,6}\s', 'Headers (# text)'),
                    (r'\[[^\]]+\]\([^)]+\)', 'Markdown links ([text](url))')
                ]
                
                markdown_found = False
                markdown_details = []
                
                for pattern, description in markdown_patterns:
                    matches = re.findall(pattern, ai_response)
                    if matches:
                        markdown_found = True
                        markdown_details.append(f"{description}: {len(matches)} matches")
                        for match in matches[:2]:  # Show first 2 matches
                            markdown_details.append(f"  - {match}")
                
                # Check for Google Maps links
                maps_pattern = r'https://www\.google\.com/maps/search/\?api=1&query=[^\s]+'
                maps_links = re.findall(maps_pattern, ai_response)
                
                result = {
                    'query': query,
                    'has_markdown': markdown_found,
                    'markdown_details': markdown_details,
                    'maps_links_count': len(maps_links),
                    'response_length': len(ai_response),
                    'response_preview': ai_response[:150] + '...' if len(ai_response) > 150 else ai_response
                }
                
                results.append(result)
                
                status = "❌ MARKDOWN FOUND" if markdown_found else "✅ NO MARKDOWN"
                print(f"   {status} | Maps links: {len(maps_links)} | Length: {len(ai_response)}")
                
                if markdown_found:
                    for detail in markdown_details[:3]:  # Show first 3 details
                        print(f"   {detail}")
                
            else:
                print(f"   ❌ API Error: {response.status_code}")
                results.append({
                    'query': query,
                    'error': f"HTTP {response.status_code}",
                    'has_markdown': None
                })
        
        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")
            results.append({
                'query': query,
                'error': str(e),
                'has_markdown': None
            })
        
        # Small delay between requests
        time.sleep(2)
    
    # Analysis
    print("\n" + "=" * 60)
    print("📊 CONSISTENCY ANALYSIS")
    print("=" * 60)
    
    successful_tests = [r for r in results if 'error' not in r]
    markdown_found_count = sum(1 for r in successful_tests if r['has_markdown'])
    clean_responses_count = sum(1 for r in successful_tests if not r['has_markdown'])
    
    print(f"Total tests: {len(test_queries)}")
    print(f"Successful responses: {len(successful_tests)}")
    print(f"Responses with markdown: {markdown_found_count}")
    print(f"Clean responses (no markdown): {clean_responses_count}")
    
    if len(successful_tests) > 0:
        consistency_rate = (clean_responses_count / len(successful_tests)) * 100
        print(f"Markdown removal consistency: {consistency_rate:.1f}%")
        
        # Google Maps links analysis
        total_maps_links = sum(r.get('maps_links_count', 0) for r in successful_tests)
        avg_maps_links = total_maps_links / len(successful_tests) if successful_tests else 0
        print(f"Total Google Maps links found: {total_maps_links}")
        print(f"Average links per response: {avg_maps_links:.1f}")
        
        # Detailed breakdown
        print("\n📋 DETAILED BREAKDOWN:")
        for i, result in enumerate(successful_tests):
            status = "❌" if result['has_markdown'] else "✅"
            query = result['query'][:40] + "..." if len(result['query']) > 40 else result['query']
            maps = result.get('maps_links_count', 0)
            print(f"   {status} {query:<45} | Maps: {maps}")
        
        # Critical assessment
        print("\n🎯 CRITICAL ASSESSMENT:")
        if consistency_rate >= 90:
            print("   ✅ EXCELLENT: Markdown removal is highly consistent")
        elif consistency_rate >= 70:
            print("   ⚠️  GOOD: Markdown removal is mostly consistent but needs improvement")
        elif consistency_rate >= 50:
            print("   ❌ POOR: Markdown removal is inconsistent - major issue")
        else:
            print("   ❌ CRITICAL: Markdown removal is failing - system prompt not working")
        
        if avg_maps_links >= 1.5:
            print("   ✅ EXCELLENT: Google Maps links are consistently included")
        elif avg_maps_links >= 1.0:
            print("   ✅ GOOD: Google Maps links are usually included")
        else:
            print("   ❌ POOR: Google Maps links are inconsistently included")
        
        return consistency_rate >= 80 and avg_maps_links >= 1.0
    
    return False

if __name__ == "__main__":
    success = test_markdown_consistency()
    if success:
        print("\n✅ CONSISTENCY TEST PASSED")
    else:
        print("\n❌ CONSISTENCY TEST FAILED")