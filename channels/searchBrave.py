import requests
import json

def search_brave(query, api_key, num_results=5):
    # Endpoint for web search
    url = "https://api.search.brave.com/res/v1/web/search"
    
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key
    }
    
    # Query parameters
    params = {
        "q": query,
        "count": num_results
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        # Check for HTTP errors
        if response.status_code == 200:
            data = response.json()
            
            # Brave nests results under 'web' -> 'results'
            results = data.get('web', {}).get('results', [])
            
            if not results:
                return None

            arrRes = []

            #print(f"--- Brave Search Results for: '{query}' ---\n")
            for i, item in enumerate(results, 1):
                title = item.get('title', 'No Title')
                url = item.get('url', 'No URL')
                # Description might be in 'description' or 'page_age' depending on result type
                desc = item.get('description', 'No description available.')
                
                #print(f"{i}. {title}")
                #print(f"   url : {url}")
                #print(f"   Desc: {desc}\n")
                
                itemRes = {'title':title,'url':url,'desc':desc}
                arrRes.append(itemRes)
            
            return arrRes
        elif response.status_code == 429:
            print("Error: Rate limit exceeded. (Free tier limit: 1 request/second)")
        elif response.status_code == 401:
            print("Error: Invalid API Key.")
        else:
            print(f"Error: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"An exception occurred: {e}")
    
    return None

if __name__ == "__main__":
    import os
    import sys
    
    API_KEY_BRAVE = os.getenv("API_KEY_BRAVE")
    query = sys.argv[1]
    searchResults = search_brave(query, API_KEY_BRAVE, int(sys.argv[2]))
    
    if not searchResults:
        print("No results found.")
        exit(1)
    
    for idx, searchResultItem in enumerate(searchResults, 1):
        print(f"--- Brave Search Results for: '{query}' ---\n")
        
        print(f"{idx}. {searchResultItem['title']}")
        print(f"   decription : {searchResultItem['desc']}")
        print(f"   URL : {searchResultItem['url']}\n")
