# Test API Endpoint

import requests
import json

# Your deployed endpoint
API_URL = "https://your-project-name.vercel.app/hackrx/run"

# Test data
test_data = {
    "documents": "https://www.irdai.gov.in/ADMINCMS/cms/whatsNew_Layout.aspx?page=PageNo4846",
    "questions": [
        "Does this policy cover hospitalization expenses?",
        "What are the waiting periods?",
        "Are pre-existing conditions covered?"
    ]
}

headers = {
    "Authorization": "Bearer test-token",
    "Content-Type": "application/json"
}

def test_api():
    print("🧪 Testing PolicyGenius X API...")
    print(f"📡 Endpoint: {API_URL}")
    
    try:
        response = requests.post(API_URL, 
                               json=test_data, 
                               headers=headers, 
                               timeout=30)
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API Response:")
            print(f"⏱️  Processing Time: {result.get('processing_time', 'N/A')} seconds")
            print(f"💬 Answers: {len(result.get('answers', []))} received")
            print(f"📄 Source Chunks: {len(result.get('source_chunks', []))} found")
            
            for i, answer in enumerate(result.get('answers', []), 1):
                print(f"\n🔍 Question {i}: {test_data['questions'][i-1]}")
                print(f"💡 Answer: {answer}")
        else:
            print(f"❌ Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"🚨 Connection Error: {e}")
    except Exception as e:
        print(f"🚨 Unexpected Error: {e}")

if __name__ == "__main__":
    test_api()
