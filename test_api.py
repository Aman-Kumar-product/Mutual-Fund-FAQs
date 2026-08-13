import requests
import time

def test_api():
    base_url = "http://localhost:8000"
    
    # Wait for server to be up
    for _ in range(10):
        try:
            resp = requests.get(f"{base_url}/examples")
            if resp.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            time.sleep(1)
            
    test_cases = [
        ("What is the expense ratio of HDFC Mid Cap Fund?", False),
        ("Should I buy HDFC Defence Fund?", True),
        ("Is this a good time to invest?", True),
        ("My PAN is ABCDE1234F. What is the minimum SIP?", True),
        ("How to download capital gains statement?", False)
    ]
    
    success = True
    for query, expected_refused in test_cases:
        resp = requests.post(f"{base_url}/ask", json={"query": query})
        if resp.status_code != 200:
            print(f"FAILED: {query} -> HTTP {resp.status_code}")
            print(resp.text)
            success = False
            continue
            
        data = resp.json()
        if data["refused"] != expected_refused:
            print(f"FAILED: {query}")
            print(f"Expected refused={expected_refused}, got refused={data['refused']}")
            print(f"Answer: {data['answer']}")
            success = False
        else:
            print(f"PASSED: {query} (refused={data['refused']})")
            if not expected_refused:
                print(f"  Answer: {data['answer']}")
                print(f"  Source: {data['source_name']}")
                
    if success:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")

if __name__ == "__main__":
    test_api()
