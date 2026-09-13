import streamlit as st
import requests
from typing import Optional, Dict, List, Any

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
# TMDB API CLIENT with Watch/Providers Support
# ============================================================================
class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"
    POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make a request to TMDB API"""
        try:
            if params is None:
                params = {}
            params['api_key'] = self.api_key
            response = self.session.get(f"{self.BASE_URL}{endpoint}", params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except:
            return None
    
    def get_popular_movies(self, page: int = 1) -> List[Dict]:
        """Get popular movies"""
        data = self._make_request("/movie/popular", {"page": page})
        return data.get("results", []) if data else []
    
    def get_watch_providers(self, movie_id: int) -> Optional[Dict[str, Any]]:
        """
        Get streaming availability for a movie by country (includes subscription, buy, rent)
        Returns: {
            "netflix": True/False,
            "prime_video": True/False,
            "disney_plus": True/False,
            "providers_list": [provider names]
        }
        """
        data = self._make_request(f"/movie/{movie_id}/watch/providers")
        if not data or "results" not in data:
            return None
        
        # Get Germany data (DE)
        germany_data = data["results"].get("DE")
        if not germany_data:
            return None
        
        # Parse ALL types of availability (flatrate, buy, rent)
        providers = {}
        providers_list = []
        
        for offer_type in ["flatrate", "buy", "rent"]:
            if offer_type in germany_data:
                for provider in germany_data[offer_type]:
                    provider_name = provider.get("provider_name", "")
                    if provider_name and provider_name not in providers_list:
                        providers_list.append(provider_name)
                    
                    provider_name_lower = provider_name.lower()
                    if "netflix" in provider_name_lower:
                        providers["netflix"] = True
                    elif "prime" in provider_name_lower or "amazon" in provider_name_lower:
                        providers["prime_video"] = True
                    elif "disney" in provider_name_lower:
                        providers["disney_plus"] = True
        
        if providers:
            providers["providers_list"] = providers_list
            return providers
        
        return None
    
    def get_genres(self) -> Dict[int, str]:
        """Get all movie genres"""
        data = self._make_request("/genre/movie/list")
        if data:
            return {genre["id"]: genre["name"] for genre in data.get("genres", [])}
        return {}

# ============================================================================
# OMDB API CLIENT (Optional)
# ============================================================================
class OMDBClient:
    BASE_URL = "https://www.omdbapi.com"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
    
    def get_imdb_rating(self, title: str) -> Optional[float]:
        """Get IMDb rating for a movie"""
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
# PAGE SETUP
# ============================================================================
st.set_page_config(page_title="MoviesFinder", page_icon="🎬", layout="wide", initial_sidebar_state="expanded")
st.title("🎬 MoviesFinder - Streaming Availability (Germany)")
st.markdown("Discover popular movies on Netflix & Prime Video with ratings and community insights.")

# Sidebar Configuration
st.sidebar.header("⚙️ Configuration")
tmdb_api_key = st.sidebar.text_input("🎬 TMDB API Key", type="password", placeholder="Required for streaming data")

if not tmdb_api_key:
    st.sidebar.warning("⚠️ TMDB API key required")
    st.info("📌 **Get your free API key:** https://www.themoviedb.org/settings/api")
    st.stop()

omdb_api_key = st.sidebar.text_input("⭐ OMDB API Key (Optional)", type="password", placeholder="Optional for IMDb ratings")

# Initialize clients
tmdb_client = TMDBClient(tmdb_api_key)
omdb_client = OMDBClient(omdb_api_key) if omdb_api_key else None
genres_dict = tmdb_client.get_genres()

if not genres_dict:
    st.error("❌ Failed to connect to TMDB. Check your API key.")
    st.stop()

st.sidebar.success("✅ Connected to TMDB!")

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================
def get_sensitivity_data(movie_title: str) -> Dict[str, str]:
    """Get sensitivity metrics for a movie"""
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
with st.spinner("🔄 Loading popular movies and checking streaming availability..."):
    popular_movies = tmdb_client.get_popular_movies(page=1)
    
    netflix_movies = []
    prime_movies = []
    
    for movie in popular_movies:
        movie_id = movie.get("id")
        title = movie.get("title")
        
        if not movie_id or not title:
            continue
        
        # Get streaming availability from TMDB watch/providers endpoint
        watch_providers = tmdb_client.get_watch_providers(movie_id)
        
        # Skip movies without streaming availability in Germany
        if not watch_providers:
            continue
        
        # Extract movie data
        poster_url = f"{TMDBClient.POSTER_BASE_URL}{movie['poster_path']}" if movie.get("poster_path") else None
        genres = [genres_dict.get(gid, "Unknown") for gid in movie.get("genre_ids", [])]
        
        # Try to get IMDb rating if OMDB key provided
        imdb_rating = None
        if omdb_client:
            imdb_rating = omdb_client.get_imdb_rating(title)
        
        movie_data = {
            "title": title,
            "year": movie.get("release_date", "N/A")[:4] if movie.get("release_date") else "N/A",
            "synopsis": movie.get("overview", "No synopsis available")[:250],
            "poster_url": poster_url,
            "tmdb_rating": round(movie.get("vote_average", 0), 1),
            "imdb_rating": imdb_rating,
            "genres": genres,
        }
        
        # Categorize by streaming platform
        if watch_providers.get("netflix"):
            netflix_movies.append(movie_data)
        if watch_providers.get("prime_video"):
            prime_movies.append(movie_data)
    
    # Sort by rating (IMDb if available, else TMDB)
    netflix_movies = sorted(netflix_movies, key=lambda x: x.get("imdb_rating") or x["tmdb_rating"], reverse=True)
    prime_movies = sorted(prime_movies, key=lambda x: x.get("imdb_rating") or x["tmdb_rating"], reverse=True)

# Show results
if netflix_movies or prime_movies:
    st.success(f"✅ Found {len(netflix_movies)} Netflix & {len(prime_movies)} Prime Video movies in Germany!")
else:
    st.warning("⚠️ No streaming data found. This might mean:")
    st.info("""
    - TMDB watch/providers data is limited in some regions
    - Your TMDB API key might not have watch/providers permission
    - No popular movies are currently available on Netflix/Prime in Germany
    """)
    st.stop()

# ============================================================================
# NETFLIX SECTION
# ============================================================================
if netflix_movies:
    st.markdown("## 🎥 Netflix (Germany)")
    st.markdown(f"**{len(netflix_movies)} movies available**")
    
    tabs = st.tabs(["⭐ Top Rated", "🎬 Grid View"])
    
    # Top Rated Tab
    with tabs[0]:
        for idx, movie in enumerate(netflix_movies[:10], 1):
            with st.container(border=True):
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    if movie["poster_url"]:
                        st.image(movie["poster_url"], use_column_width=True)
                    else:
                        st.info("No poster")
                
                with col2:
                    st.markdown(f"### #{idx} - {movie['title']}")
                    
                    rating_col = st.columns(3)
                    with rating_col[0]:
                        if movie["imdb_rating"]:
                            st.metric("IMDb", f"{movie['imdb_rating']}/10")
                        else:
                            st.metric("TMDB", f"{movie['tmdb_rating']}/10")
                    
                    with rating_col[1]:
                        st.markdown(f"**Year:** {movie['year']}")
                    
                    with rating_col[2]:
                        if movie['genres']:
                            st.markdown(f"**Genres:** {', '.join(movie['genres'][:2])}")
                    
                    st.markdown(f"**Plot:** {movie['synopsis']}...")
                    
                    sensitivity = get_sensitivity_data(movie['title'])
                    st.markdown("**🛡️ Content Sensitivity:**")
                    sens_cols = st.columns(3)
                    with sens_cols[0]:
                        st.markdown(f"🔞 Sexual: {sensitivity['sexual_content']}")
                    with sens_cols[1]:
                        st.markdown(f"💢 Violence: {sensitivity['violent_content']}")
                    with sens_cols[2]:
                        st.markdown(f"📢 Woke: {sensitivity['woke_content']}")
                
                st.divider()
    
    # Grid View Tab
    with tabs[1]:
        cols = st.columns(3)
        for idx, movie in enumerate(netflix_movies):
            with cols[idx % 3]:
                with st.container(border=True):
                    if movie["poster_url"]:
                        st.image(movie["poster_url"], use_column_width=True)
                    st.markdown(f"**{movie['title']}**")
                    if movie["imdb_rating"]:
                        st.markdown(f"⭐ {movie['imdb_rating']}/10 (IMDb)")
                    else:
                        st.markdown(f"⭐ {movie['tmdb_rating']}/10 (TMDB)")

st.divider()

# ============================================================================
# PRIME VIDEO SECTION
# ============================================================================
if prime_movies:
    st.markdown("## 🎬 Amazon Prime Video (Germany)")
    st.markdown(f"**{len(prime_movies)} movies available**")
    
    tabs = st.tabs(["⭐ Top Rated", "🎬 Grid View"])
    
    # Top Rated Tab
    with tabs[0]:
        for idx, movie in enumerate(prime_movies[:10], 1):
            with st.container(border=True):
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    if movie["poster_url"]:
                        st.image(movie["poster_url"], use_column_width=True)
                    else:
                        st.info("No poster")
                
                with col2:
                    st.markdown(f"### #{idx} - {movie['title']}")
                    
                    rating_col = st.columns(3)
                    with rating_col[0]:
                        if movie["imdb_rating"]:
                            st.metric("IMDb", f"{movie['imdb_rating']}/10")
                        else:
                            st.metric("TMDB", f"{movie['tmdb_rating']}/10")
                    
                    with rating_col[1]:
                        st.markdown(f"**Year:** {movie['year']}")
                    
                    with rating_col[2]:
                        if movie['genres']:
                            st.markdown(f"**Genres:** {', '.join(movie['genres'][:2])}")
                    
                    st.markdown(f"**Plot:** {movie['synopsis']}...")
                    
                    sensitivity = get_sensitivity_data(movie['title'])
                    st.markdown("**🛡️ Content Sensitivity:**")
                    sens_cols = st.columns(3)
                    with sens_cols[0]:
                        st.markdown(f"🔞 Sexual: {sensitivity['sexual_content']}")
                    with sens_cols[1]:
                        st.markdown(f"💢 Violence: {sensitivity['violent_content']}")
                    with sens_cols[2]:
                        st.markdown(f"📢 Woke: {sensitivity['woke_content']}")
                
                st.divider()
    
    # Grid View Tab
    with tabs[1]:
        cols = st.columns(3)
        for idx, movie in enumerate(prime_movies):
            with cols[idx % 3]:
                with st.container(border=True):
                    if movie["poster_url"]:
                        st.image(movie["poster_url"], use_column_width=True)
                    st.markdown(f"**{movie['title']}**")
                    if movie["imdb_rating"]:
                        st.markdown(f"⭐ {movie['imdb_rating']}/10 (IMDb)")
                    else:
                        st.markdown(f"⭐ {movie['tmdb_rating']}/10 (TMDB)")

st.divider()

# ============================================================================
# AIRLINE SECTION
# ============================================================================
with st.expander("✈️ In-Flight Airline Entertainment (Coming Soon)", expanded=False):
    st.info("🚀 Coming soon! Browse in-flight entertainment catalogs from major airlines.")

st.divider()
st.markdown("**MoviesFinder v4.0** | Streaming Data: TMDB | Germany (DE) | 📱 Streamlit")
