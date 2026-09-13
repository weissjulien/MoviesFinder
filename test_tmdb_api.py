#!/usr/bin/env python3
"""
Test script to verify TMDB API key works and has watch/providers access
"""
import requests
import sys

def test_tmdb_api(api_key):
    print("=" * 70)
    print("TMDB API Test Suite")
    print("=" * 70)
    print()
    
    # Test 1: Basic API access
    print("TEST 1: Basic API Access")
    print("-" * 70)
    try:
        response = requests.get(
            "https://api.themoviedb.org/3/movie/popular",
            params={"api_key": api_key, "page": 1},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if "results" in data:
            print("✅ SUCCESS: Can access TMDB popular movies")
            print(f"   Found {len(data['results'])} popular movies")
            
            # Get first movie for next test
            first_movie = data['results'][0]
            movie_id = first_movie['id']
            movie_title = first_movie['title']
            print(f"   First movie: {movie_title} (ID: {movie_id})")
            return movie_id, movie_title
        else:
            print("❌ FAILED: No results in response")
            return None, None
    except requests.exceptions.HTTPError as e:
        print(f"❌ FAILED: HTTP Error {e.response.status_code}")
        if e.response.status_code == 401:
            print("   → Invalid API key")
        elif e.response.status_code == 429:
            print("   → Rate limited")
        return None, None
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return None, None
    
    print()

def test_watch_providers(api_key, movie_id, movie_title):
    print("TEST 2: Watch/Providers Endpoint")
    print("-" * 70)
    try:
        response = requests.get(
            f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers",
            params={"api_key": api_key},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ SUCCESS: Can access watch/providers for '{movie_title}'")
        
        if "results" not in data:
            print("   ⚠️  WARNING: No 'results' field in response")
            print(f"   Response keys: {list(data.keys())}")
            return False
        
        results = data.get("results", {})
        print(f"   Countries with data: {list(results.keys())}")
        
        # Check Germany specifically
        if "DE" in results:
            germany = results["DE"]
            print(f"   ✅ Germany (DE) has streaming data!")
            print(f"      Available providers:")
            if "flatrate" in germany:
                for provider in germany["flatrate"]:
                    print(f"         - {provider.get('provider_name')} (ID: {provider.get('provider_id')})")
            if "buy" in germany:
                print(f"      (Also available for purchase)")
            if "rent" in germany:
                print(f"      (Also available for rent)")
            return True
        else:
            print(f"   ❌ Germany (DE) not in results")
            print(f"   Available countries: {list(results.keys())[:5]}...")
            return False
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ FAILED: HTTP Error {e.response.status_code}")
        if e.response.status_code == 401:
            print("   → Invalid API key")
        elif e.response.status_code == 404:
            print("   → Movie not found or endpoint doesn't exist")
        return False
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False
    
    print()

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_tmdb_api.py YOUR_TMDB_API_KEY")
        print()
        print("Get your free TMDB API key at: https://www.themoviedb.org/settings/api")
        sys.exit(1)
    
    api_key = sys.argv[1]
    
    print()
    print(f"Testing with API key: {api_key[:10]}...")
    print()
    
    # Test 1
    movie_id, movie_title = test_tmdb_api(api_key)
    
    if movie_id:
        # Test 2
        test_watch_providers(api_key, movie_id, movie_title)
    
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    if movie_id:
        print("✅ Your TMDB API key is VALID")
        print("✅ App should be able to load popular movies")
        print("✅ App can query streaming availability for Germany")
        print()
        print("Next step: Open https://vigilant-goldfish-ppx9pp647gjh96pw-8501.app.github.dev")
        print("           and paste your API key into the sidebar")
    else:
        print("❌ TMDB API test failed")
        print("Check your API key and try again")
    print()

if __name__ == "__main__":
    main()
