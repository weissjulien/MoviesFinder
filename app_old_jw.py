import streamlit as st
import requests
import time
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

# ============================================================================
# CROWDSOURCED SENSITIVITY METRIC MAPPING
# ============================================================================
SENSITIVITY_MAP = {
    "The Matrix": {"sexual_content": "Mild", "violent_content": "High", "woke_content": "None", "source": "Reddit"},
    "Top Gun: Maverick": {"sexual_content": "Mild", "violent_content": "Mild", "woke_content": "None", "source": "Community"},
    "Dune": {"sexual_content": "None", "violent_content": "Mild", "woke_content": "Mild", "source": "Forum"},
    "Interstellar": {"sexual_content": "None", "violent_content": "None", "woke_content": "None", "source": "Community"},
    "Avatar": {"sexual_content": "None", "violent_content": "High", "woke_content": "High", "source": "Web forums"},
    "Oppenheimer": {"sexual_content": "Mild", "violent_content": "Mild", "woke_content": "None", "source": "Reddit"},
    "Barbie": {"sexual_content": "Mild", "violent_content": "None", "woke_content": "High", "source": "Community"},
    "Inception": {"sexual_content": "Mild", "violent_content": "Mild", "woke_content": "None", "source": "Forum"},
    "The Dark Knight": {"sexual_content": "Mild", "violent_content": "High", "woke_content": "None", "source": "Community"},
}

# ============================================================================
# PLATFORM AVAILABILITY MAPPING (Germany)
# ============================================================================
PLATFORM_MAPPING = {
    "The Matrix": {"netflix": True, "prime_video": True},
    "Inception": {"netflix": False, "prime_video": True},
    "Interstellar": {"netflix": True, "prime_video": False},
    "The Dark Knight": {"netflix": True, "prime_video": False},
    "Dune": {"netflix": False, "prime_video": True},
    "Dune: Part Two": {"netflix": False, "prime_video": True},
    "Avatar": {"netflix": False, "prime_video": True},
    "Avatar: The Way of Water": {"netflix": False, "prime_video": True},
    "Top Gun: Maverick": {"netflix": True, "prime_video": False},
    "Oppenheimer": {"netflix": False, "prime_video": True},
    "Barbie": {"netflix": False, "prime_video": True},
    "Killers of the Flower Moon": {"netflix": False, "prime_video": True},
    "Mission: Impossible – Dead Reckoning": {"netflix": False, "prime_video": True},
    "Guardians of the Galaxy Vol. 3": {"netflix": True, "prime_video": False},
    "Ant-Man: Quantumania": {"netflix": True, "prime_video": False},
    "The Flash": {"netflix": True, "prime_video": False},
    "Aquaman and the Lost Kingdom": {"netflix": False, "prime_video": True},
    "Renfield": {"netflix": True, "prime_video": False},
    "Scream VI": {"netflix": True, "prime_video": False},
    "Fast X": {"netflix": False, "prime_video": True},
    "Spider-Man: Across the Spider-Verse": {"netflix": True, "prime_video": False},
    "The Marvels": {"netflix": True, "prime_video": False},
    "Twisters": {"netflix": False, "prime_video": True},
    "Elemental": {"netflix": False, "prime_video": True},
    "Sound of Freedom": {"netflix": False, "prime_video": True},
    "Insidious: The Red Door": {"netflix": False, "prime_video": True},
    "Five Nights at Freddy's": {"netflix": False, "prime_video": True},
    "The Nun II": {"netflix": False, "prime_video": True},
    "M3GAN": {"netflix": True, "prime_video": False},
    "Talk to Me": {"netflix": True, "prime_video": False},
    "Knock at the Cabin": {"netflix": False, "prime_video": True},
    "A Thousand and One": {"netflix": False, "prime_video": True},
    "Napoleon": {"netflix": False, "prime_video": True},
    "The Iron Claw": {"netflix": False, "prime_video": True},
    "American Fiction": {"netflix": False, "prime_video": True},
    "Priscilla": {"netflix": False, "prime_video": True},
    "Saw X": {"netflix": False, "prime_video": True},
    "The Creator": {"netflix": False, "prime_video": True},
    "Hypnotic": {"netflix": True, "prime_video": False},
    "Pain Hustlers": {"netflix": True, "prime_video": False},
    "The Idea of You": {"netflix": True, "prime_video": False},
}

# ============================================================================
# TMDB API CLIENT
# ============================================================================
class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"
    POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        try:
            if params is None:
                params = {}
            params['api_key'] = self.api_key
            response = self.session.get(f"{self.BASE_URL}{endpoint}", params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except:
            return None
    
    def search_movie(self, title: str) -> Optional[Dict]:
        data = self._make_request("/search/movie", {"query": title})
        if data and data.get("results"):
            return data["results"][0]
        return None
    
    def get_popular_movies(self, page: int = 1) -> List[Dict]:
        data = self._make_request("/movie/popular", {"page": page})
        return data.get("results", []) if data else []
    
    def get_genres(self) -> Dict[int, str]:
        data = self._make_request("/genre/movie/list")
        if data:
            return {genre["id"]: genre["name"] for genre in data.get("genres", [])}
        return {}

# ============================================================================
# OMDB API CLIENT
# ============================================================================
class OMDBClient:
    BASE_URL = "https://www.omdbapi.com"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
    
    def get_imdb_rating(self, title: str) -> Optional[float]:
        try:
            response = self.session.get(
                self.BASE_URL,
                params={"apikey": self.api_key, "t": title, "type": "movie"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            if data.get("Response") == "True" and "imdbRating" in data and data["imdbRating"] != "N/A":
                return float(data["imdbRating"])
        except:
            pass
        return None

# ============================================================================
# JUSTWATCH API CLIENT (with proper rate limiting & fallback)
# ============================================================================
class JustWatchClient:
    BASE_URL = "https://api.justwatch.com"
    CACHE_DURATION = 3600  # 1 hour
    REQUEST_DELAY = 2.0   # 2 seconds between requests
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://www.justwatch.com/"
        })
        self.cache = {}
        self.last_request_time = {}
        self.rate_limited = False  # Track if we hit rate limit
    
    def _respect_rate_limit(self, endpoint: str):
        """Implement request delay to avoid rate limiting"""
        if endpoint in self.last_request_time:
            elapsed = time.time() - self.last_request_time[endpoint]
            if elapsed < self.REQUEST_DELAY:
                time.sleep(self.REQUEST_DELAY - elapsed)
        self.last_request_time[endpoint] = time.time()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        if cache_key not in self.cache:
            return False
        cached_data, timestamp = self.cache[cache_key]
        return (time.time() - timestamp) < self.CACHE_DURATION
    
    def get_streaming_providers(self, title: str, country: str = "DE") -> Optional[Dict[str, bool]]:
        """
        Fetch streaming availability with rate limiting and caching.
        If rate limited, returns None (allows fallback to PLATFORM_MAPPING).
        Returns: {"netflix": True/False, "prime_video": True/False, ...}
        """
        # If already rate limited this session, don't try again
        if self.rate_limited:
            return None
        
        cache_key = f"{title}:{country}"
        
        # Return cached result if valid
        if self._is_cache_valid(cache_key):
            cached_data, _ = self.cache[cache_key]
            return cached_data
        
        try:
            # Respect rate limit
            self._respect_rate_limit("autocomplete")
            
            # Step 1: Search for movie
            search_response = self.session.get(
                f"{self.BASE_URL}/v3/autocomplete",
                params={
                    "query": title,
                    "content_type": "MOVIE",
                    "country": country
                },
                timeout=10
            )
            search_response.raise_for_status()
            search_data = search_response.json()
            
            if not search_data.get("entries"):
                return None
            
            # Get the first movie result
            movie_entry = search_data["entries"][0]
            jw_id = movie_entry.get("id")
            
            if not jw_id:
                return None
            
            # Respect rate limit before next request
            self._respect_rate_limit("details")
            
            # Step 2: Get streaming offers for the movie
            offers_response = self.session.get(
                f"{self.BASE_URL}/v3/movies/{jw_id}",
                params={"country": country},
                timeout=10
            )
            offers_response.raise_for_status()
            offers_data = offers_response.json()
            
            # Extract provider information from "offers" array (correct field)
            providers = {}
            if "offers" in offers_data:
                for offer in offers_data["offers"]:
                    provider_name = offer.get("provider", {}).get("name", "").lower()
                    package_type = offer.get("package_type", "").lower()
                    
                    if package_type == "streaming":
                        if "netflix" in provider_name:
                            providers["netflix"] = True
                        elif "prime" in provider_name or "amazon" in provider_name:
                            providers["prime_video"] = True
                        elif "disney" in provider_name:
                            providers["disney_plus"] = True
            
            # Cache the result
            self.cache[cache_key] = (providers, time.time())
            return providers if providers else None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                self.rate_limited = True  # Mark as rate limited
                return None
            else:
                return None
        except Exception as e:
            return None

# ============================================================================
# PAGE SETUP
# ============================================================================
st.set_page_config(page_title="MoviesFinder", page_icon="🎬", layout="wide", initial_sidebar_state="expanded")
st.title("🎬 MoviesFinder - Popular Movies (Germany)")
st.markdown("Discover popular movies with ratings and community sensitivity insights.")

# Sidebar
st.sidebar.header("⚙️ Configuration")
tmdb_api_key = st.sidebar.text_input("🎬 TMDB API Key", type="password", placeholder="Required")

if not tmdb_api_key:
    st.sidebar.warning("⚠️ Enter TMDB API key to proceed")
    st.info("📌 **Setup:** Get free API key at https://www.themoviedb.org/settings/api")
    st.stop()

omdb_api_key = st.sidebar.text_input("⭐ OMDB API Key (Optional)", type="password", placeholder="Optional")

# JustWatch option
st.sidebar.markdown("---")
st.sidebar.markdown("### 🌐 Streaming Data Source")
use_justwatch = st.sidebar.checkbox("Try JustWatch (Real-time availability)", value=False, help="Attempts to use JustWatch API for real streaming data. Falls back to PLATFORM_MAPPING if unavailable.")
if use_justwatch:
    st.sidebar.info("ℹ️ JustWatch may take longer but provides real-time Netflix/Prime availability.")

# Initialize clients
tmdb_client = TMDBClient(tmdb_api_key)
omdb_client = OMDBClient(omdb_api_key) if omdb_api_key else None
justwatch_client = JustWatchClient() if use_justwatch else None
genres_dict = tmdb_client.get_genres()

if not genres_dict:
    st.error("❌ Failed to load from TMDB")
    st.stop()

st.sidebar.success("✅ Ready!")

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================
def get_sensitivity_data(movie_title: str) -> Dict[str, str]:
    if movie_title in SENSITIVITY_MAP:
        return SENSITIVITY_MAP[movie_title]
    return {
        "sexual_content": "Pending Review",
        "violent_content": "Pending Review",
        "woke_content": "Pending Review",
        "source": "Awaiting feedback"
    }

# ============================================================================
# LOAD DATA
# ============================================================================
with st.spinner("🔄 Loading popular movies..."):
    popular_movies = tmdb_client.get_popular_movies(page=1)
    
    netflix_movies = []
    prime_movies = []
    
    for movie in popular_movies:
        title = movie.get("title")
        if not title:
            continue
        
        # Determine platform availability
        platforms = None
        
        if justwatch_client:
            # Try JustWatch API first
            platforms = justwatch_client.get_streaming_providers(title, country="DE")
        
        if not platforms:
            # Fall back to PLATFORM_MAPPING
            platforms = PLATFORM_MAPPING.get(title)
        
        # Skip movies without platform mapping/API data
        if not platforms:
            continue
        
        poster_url = f"{TMDBClient.POSTER_BASE_URL}{movie['poster_path']}" if movie.get("poster_path") else None
        genres = [genres_dict.get(gid, "Unknown") for gid in movie.get("genre_ids", [])]
        
        imdb_rating = None
        if omdb_client:
            imdb_rating = omdb_client.get_imdb_rating(title)
        
        movie_data = {
            "title": title,
            "year": movie.get("release_date", "N/A")[:4] if movie.get("release_date") else "N/A",
            "synopsis": movie.get("overview", "No synopsis")[:300],
            "poster_url": poster_url,
            "tmdb_rating": round(movie.get("vote_average", 0), 1),
            "imdb_rating": imdb_rating,
            "genres": genres,
        }
        
        if platforms.get("netflix"):
            netflix_movies.append(movie_data)
        if platforms.get("prime_video"):
            prime_movies.append(movie_data)
    
    # Sort
    netflix_movies = sorted(netflix_movies, key=lambda x: x.get("imdb_rating") or x["tmdb_rating"], reverse=True)
    prime_movies = sorted(prime_movies, key=lambda x: x.get("imdb_rating") or x["tmdb_rating"], reverse=True)

# Show status
if netflix_movies or prime_movies:
    if justwatch_client and not justwatch_client.rate_limited:
        data_source = "✨ JustWatch (Real-time)"
    else:
        data_source = "📋 PLATFORM_MAPPING (Fallback)"
    st.success(f"✅ Found {len(netflix_movies)} Netflix & {len(prime_movies)} Prime Video movies! ({data_source})")
else:
    st.error("❌ No movies found")
    st.stop()

# ============================================================================
# NETFLIX SECTION
# ============================================================================
st.markdown("## 🎥 Netflix (Germany)")
st.markdown(f"**{len(netflix_movies)} movies available**")

if netflix_movies:
    tabs = st.tabs(["⭐ Top Rated", "🎬 Grid"])
    
    with tabs[0]:
        for idx, movie in enumerate(netflix_movies[:10], 1):
            with st.container(border=True):
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    if movie["poster_url"]:
                        st.image(movie["poster_url"], use_column_width=True)
                
                with col2:
                    st.markdown(f"### #{idx} - {movie['title']}")
                    
                    mcols = st.columns(3)
                    with mcols[0]:
                        st.markdown(f"**Year:** {movie['year']}")
                    with mcols[1]:
                        rating = f"⭐ {movie['imdb_rating']}/10" if movie['imdb_rating'] else f"TMDB: {movie['tmdb_rating']}/10"
                        st.markdown(f"**Rating:** {rating}")
                    with mcols[2]:
                        if movie['genres']:
                            st.markdown(f"**Genres:** {', '.join(movie['genres'][:2])}")
                    
                    st.markdown(f"**Plot:** {movie['synopsis']}...")
                    
                    sensitivity = get_sensitivity_data(movie['title'])
                    st.markdown("**🛡️ Sensitivity:**")
                    scols = st.columns(3)
                    with scols[0]:
                        st.markdown(f"🔞 {sensitivity['sexual_content']}")
                    with scols[1]:
                        st.markdown(f"💢 {sensitivity['violent_content']}")
                    with scols[2]:
                        st.markdown(f"📢 {sensitivity['woke_content']}")
                
                st.divider()
    
    with tabs[1]:
        cols = st.columns(3)
        for idx, movie in enumerate(netflix_movies):
            with cols[idx % 3]:
                with st.container(border=True):
                    if movie["poster_url"]:
                        st.image(movie["poster_url"], use_column_width=True)
                    st.markdown(f"**{movie['title']}**")
                    rating = f"⭐ {movie['imdb_rating']}/10" if movie['imdb_rating'] else f"{movie['tmdb_rating']}/10"
                    st.markdown(rating)

st.divider()

# ============================================================================
# PRIME VIDEO SECTION
# ============================================================================
st.markdown("## 🎬 Amazon Prime Video (Germany)")
st.markdown(f"**{len(prime_movies)} movies available**")

if prime_movies:
    tabs = st.tabs(["⭐ Top Rated", "🎬 Grid"])
    
    with tabs[0]:
        for idx, movie in enumerate(prime_movies[:10], 1):
            with st.container(border=True):
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    if movie["poster_url"]:
                        st.image(movie["poster_url"], use_column_width=True)
                
                with col2:
                    st.markdown(f"### #{idx} - {movie['title']}")
                    
                    mcols = st.columns(3)
                    with mcols[0]:
                        st.markdown(f"**Year:** {movie['year']}")
                    with mcols[1]:
                        rating = f"⭐ {movie['imdb_rating']}/10" if movie['imdb_rating'] else f"TMDB: {movie['tmdb_rating']}/10"
                        st.markdown(f"**Rating:** {rating}")
                    with mcols[2]:
                        if movie['genres']:
                            st.markdown(f"**Genres:** {', '.join(movie['genres'][:2])}")
                    
                    st.markdown(f"**Plot:** {movie['synopsis']}...")
                    
                    sensitivity = get_sensitivity_data(movie['title'])
                    st.markdown("**🛡️ Sensitivity:**")
                    scols = st.columns(3)
                    with scols[0]:
                        st.markdown(f"🔞 {sensitivity['sexual_content']}")
                    with scols[1]:
                        st.markdown(f"💢 {sensitivity['violent_content']}")
                    with scols[2]:
                        st.markdown(f"📢 {sensitivity['woke_content']}")
                
                st.divider()
    
    with tabs[1]:
        cols = st.columns(3)
        for idx, movie in enumerate(prime_movies):
            with cols[idx % 3]:
                with st.container(border=True):
                    if movie["poster_url"]:
                        st.image(movie["poster_url"], use_column_width=True)
                    st.markdown(f"**{movie['title']}**")
                    rating = f"⭐ {movie['imdb_rating']}/10" if movie['imdb_rating'] else f"{movie['tmdb_rating']}/10"
                    st.markdown(rating)

st.divider()

# ============================================================================
# AIRLINE SECTION
# ============================================================================
with st.expander("✈️ In-Flight Airline Entertainment (Coming Soon)", expanded=False):
    st.info("🚀 Coming soon! Integration with major airlines' entertainment catalogs.")

st.divider()
st.markdown("**MoviesFinder v3.0** | TMDB + OMDB | Germany (DE) | 📱 Streamlit")
