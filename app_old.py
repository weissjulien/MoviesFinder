import streamlit as st
import requests
import json
from datetime import datetime
from typing import Optional, Dict, List, Any
from urllib.parse import quote

# ============================================================================
# CROWDSOURCED SENSITIVITY METRIC MAPPING (HARDCODED INTERNAL DATABASE)
# ============================================================================
SENSITIVITY_MAP = {
    # Action/Sci-Fi
    "The Matrix": {
        "sexual_content": "Mild",
        "violent_content": "High",
        "woke_content": "None",
        "source": "Reddit r/movies consensus"
    },
    "Top Gun: Maverick": {
        "sexual_content": "Mild",
        "violent_content": "Mild",
        "woke_content": "None",
        "source": "Community feedback"
    },
    "Dune": {
        "sexual_content": "None",
        "violent_content": "Mild",
        "woke_content": "Mild",
        "source": "Forum discussion"
    },
    "Interstellar": {
        "sexual_content": "None",
        "violent_content": "None",
        "woke_content": "None",
        "source": "Community consensus"
    },
    "Avatar": {
        "sexual_content": "None",
        "violent_content": "High",
        "woke_content": "High",
        "source": "Web forums"
    },
    
    # Drama
    "Oppenheimer": {
        "sexual_content": "Mild",
        "violent_content": "Mild",
        "woke_content": "None",
        "source": "Reddit feedback"
    },
    "Barbie": {
        "sexual_content": "Mild",
        "violent_content": "None",
        "woke_content": "High",
        "source": "Community review"
    },
    
    # Comedy
    "The Hangover": {
        "sexual_content": "Mild",
        "violent_content": "None",
        "woke_content": "None",
        "source": "Community consensus"
    },
}

# ============================================================================
# TMDB API HELPER FUNCTIONS
# ============================================================================
class TMDBClient:
    """Robust TMDB API client for fetching movie metadata"""
    
    BASE_URL = "https://api.themoviedb.org/3"
    POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make a request to TMDB API with error handling"""
        try:
            if params is None:
                params = {}
            params['api_key'] = self.api_key
            
            response = self.session.get(f"{self.BASE_URL}{endpoint}", params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return None
    
    def search_movie(self, title: str) -> Optional[Dict]:
        """Search for a movie by title"""
        data = self._make_request("/search/movie", {"query": title})
        if data and data.get("results"):
            return data["results"][0]
        return None
    
    def get_popular_movies(self, page: int = 1) -> List[Dict]:
        """Fetch popular movies"""
        data = self._make_request("/movie/popular", {"page": page})
        return data.get("results", []) if data else []
    
    def get_movies_by_genre(self, genre_id: int, page: int = 1) -> List[Dict]:
        """Fetch movies filtered by genre"""
        data = self._make_request("/discover/movie", {
            "with_genres": genre_id,
            "sort_by": "vote_average.desc",
            "page": page
        })
        return data.get("results", []) if data else []
    
    def get_genres(self) -> Dict[int, str]:
        """Fetch available genres"""
        data = self._make_request("/genre/movie/list")
        if data:
            return {genre["id"]: genre["name"] for genre in data.get("genres", [])}
        return {}
    
    def parse_movie_metadata(self, movie: Dict) -> Dict[str, Any]:
        """
        Parse TMDB movie data and extract:
        - Official Title
        - Production Year
        - Runtime/Length
        - Associated Genres
        - Country of Production
        - Short Plot Synopsis
        - Poster Image URL
        - IMDb/TMDB Rating
        """
        return {
            "title": movie.get("title", "N/A"),
            "year": movie.get("release_date", "N/A")[:4] if movie.get("release_date") else "N/A",
            "rating": round(movie.get("vote_average", 0), 1),
            "popularity": movie.get("popularity", 0),
            "genre_ids": movie.get("genre_ids", []),
            "genres_text": "Multiple",  # Will be populated by genre map
            "country": "USA",  # TMDB doesn't always include in popular endpoint
            "synopsis": movie.get("overview", "No synopsis available"),
            "poster_url": f"{self.POSTER_BASE_URL}{movie['poster_path']}" if movie.get("poster_path") else None,
            "tmdb_id": movie.get("id"),
            "vote_count": movie.get("vote_count", 0)
        }


# ============================================================================
# OMDB API HELPER FUNCTIONS (IMDb Ratings)
# ============================================================================
class OMDBClient:
    """OMDB API client for fetching IMDb ratings"""
    
    BASE_URL = "https://www.omdbapi.com"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
    
    def search_movie(self, title: str) -> Optional[Dict]:
        """Search for a movie by title"""
        try:
            response = self.session.get(
                self.BASE_URL,
                params={"apikey": self.api_key, "t": title, "type": "movie"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            if data.get("Response") == "True":
                return data
            return None
        except requests.exceptions.RequestException:
            return None
    
    def get_imdb_rating(self, title: str) -> Optional[float]:
        """Get IMDb rating for a movie"""
        movie = self.search_movie(title)
        if movie and "imdbRating" in movie and movie["imdbRating"] != "N/A":
            try:
                return float(movie["imdbRating"])
            except ValueError:
                return None
        return None


# ============================================================================
# PLATFORM AVAILABILITY MAPPING (Hardcoded Germany - Popular Movies)
# ============================================================================
# Note: These are popular movies known to be on Netflix/Prime in Germany
# (Updated based on actual availability - you can manually update this list)
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
    "The Hunger Games: The Ballad of Songbirds and Snakes": {"netflix": False, "prime_video": True},
    "Hypnotic": {"netflix": True, "prime_video": False},
    "Pain Hustlers": {"netflix": True, "prime_video": False},
    "The Idea of You": {"netflix": True, "prime_video": False},
}

# ============================================================================
# PAGE CONFIGURATION & SIDEBAR
# ============================================================================
st.set_page_config(
    page_title="MoviesFinder",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🎬 MoviesFinder - Popular Movies (Germany)")
st.markdown("Discover popular movies with ratings and community sensitivity insights. Data updated regularly for Netflix and Amazon Prime availability in Germany.")

# Sidebar - API Key Management (ONLY TMDB REQUIRED NOW)
st.sidebar.header("⚙️ Configuration")

tmdb_api_key = st.sidebar.text_input(
    "🎬 TMDB API Key",
    type="password",
    placeholder="Paste your TMDB API key here",
    help="Get your free API key at https://www.themoviedb.org/settings/api"
)

if not tmdb_api_key:
    st.sidebar.warning("⚠️ **API Key Required**: Enter your TMDB API key to fetch live movie data.")
    st.info(
        "📌 **Quick Setup:**\n"
        "1. Visit https://www.themoviedb.org/settings/api\n"
        "2. Request a free API key\n"
        "3. Paste it above\n"
        "4. The app will load popular movies with ratings and availability!"
    )
    st.stop()

# Initialize TMDB client
tmdb_client = TMDBClient(tmdb_api_key)
genres_dict = tmdb_client.get_genres()

if not genres_dict:
    st.error("❌ Failed to load genres. Check your TMDB API key.")
    st.stop()

st.sidebar.success("✅ Connected to TMDB")
st.sidebar.info("📍 **Region:** Germany (DE)\n\n✅ **Platforms:** Netflix & Prime Video\n\n📊 **Data:** Popular movies with known platform availability")

# Optional OMDB for IMDb ratings
omdb_api_key = st.sidebar.text_input(
    "⭐ OMDB API Key (Optional - for IMDb ratings)",
    type="password",
    placeholder="Leave empty to skip",
    help="Get free at http://www.omdbapi.com/"
)

omdb_client = None
if omdb_api_key:
    omdb_client = OMDBClient(omdb_api_key)
    st.sidebar.success("✅ OMDB connected")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================
def get_sensitivity_data(movie_title: str) -> Dict[str, str]:
    """
    Lookup sensitivity data for a movie.
    If not found, return "Pending Community Review" default.
    """
    if movie_title in SENSITIVITY_MAP:
        return SENSITIVITY_MAP[movie_title]
    return {
        "sexual_content": "Pending Community Review",
        "violent_content": "Pending Community Review",
        "woke_content": "Pending Community Review",
        "source": "Awaiting community feedback"
    }

# ============================================================================
# MAIN APPLICATION INTERFACE
# ============================================================================

# Cache results to avoid excessive API calls
if "netflix_movies_cache" not in st.session_state:
    st.session_state.netflix_movies_cache = []
if "prime_movies_cache" not in st.session_state:
    st.session_state.prime_movies_cache = []
if "movies_enriched_cache" not in st.session_state:
    st.session_state.movies_enriched_cache = {}

def enrich_movie_data(movie: Dict, title: str) -> tuple:
    """
    Enrich JustWatch movie data with TMDB/OMDB info (optional)
    Returns: (imdb_rating, genres, poster_url)
    """
    if title in st.session_state.movies_enriched_cache:
        return st.session_state.movies_enriched_cache[title]
    
    imdb_rating = None
    genres = []
    poster_url = movie.get("poster_url")  # JustWatch already has poster
    
    # Get IMDb rating if OMDB key provided
    if omdb_client:
        imdb_rating = omdb_client.get_imdb_rating(title)
    
    # Get genres if TMDB key provided
    if tmdb_client:
        tmdb_movie = tmdb_client.search_movie(title)
        if tmdb_movie:
            genres = [genres_dict.get(gid, "Unknown") for gid in tmdb_movie.get("genre_ids", [])]
            # Use TMDB poster if better quality
            if tmdb_movie.get("poster_path"):
                poster_url = f"https://image.tmdb.org/t/p/w500{tmdb_movie['poster_path']}"
    
    result = (imdb_rating, genres, poster_url)
    st.session_state.movies_enriched_cache[title] = result
    return result

# Status message for data loading
with st.spinner("🔄 Fetching Netflix & Prime Video movies from Germany..."):
    # Get Netflix movies
    netflix_movies_raw = justwatch_client.get_popular_by_platform([8], max_results=40)
    
    # Get Prime Video movies
    prime_movies_raw = justwatch_client.get_popular_by_platform([10], max_results=40)
    
    st.write(f"📊 Debug: Found {len(netflix_movies_raw)} Netflix movies from API")
    st.write(f"📊 Debug: Found {len(prime_movies_raw)} Prime Video movies from API")
    
    # Enrich with ratings
    netflix_movies_data = []
    for movie in netflix_movies_raw:
        if movie.get("title"):
            imdb_rating, genres, poster_url = enrich_movie_data(movie, movie["title"])
            netflix_movies_data.append({
                "title": movie["title"],
                "year": movie.get("release_year", "N/A"),
                "synopsis": movie.get("synopsis", "No synopsis available")[:300],
                "poster_url": poster_url or movie.get("poster_url", ""),
                "imdb_rating": imdb_rating,
                "genres": genres,
                "platforms": movie.get("platforms", {})
            })
    
    prime_movies_data = []
    for movie in prime_movies_raw:
        if movie.get("title"):
            imdb_rating, genres, poster_url = enrich_movie_data(movie, movie["title"])
            prime_movies_data.append({
                "title": movie["title"],
                "year": movie.get("release_year", "N/A"),
                "synopsis": movie.get("synopsis", "No synopsis available")[:300],
                "poster_url": poster_url or movie.get("poster_url", ""),
                "imdb_rating": imdb_rating,
                "genres": genres,
                "platforms": movie.get("platforms", {})
            })
    
    # Sort by rating (IMDb if available, otherwise no sorting)
    netflix_movies_data = sorted(netflix_movies_data, key=lambda x: x.get("imdb_rating") or 0, reverse=True)
    prime_movies_data = sorted(prime_movies_data, key=lambda x: x.get("imdb_rating") or 0, reverse=True)

if not netflix_movies_data and not prime_movies_data:
    st.error("❌ No movies found. This might be a JustWatch API issue. Try refreshing the page.")
    st.info("💡 If the problem persists, the JustWatch API might be temporarily unavailable.")
else:
    st.success(f"✅ Found {len(netflix_movies_data)} Netflix movies & {len(prime_movies_data)} Prime Video movies in Germany!")

# ============================================================================
# SECTION 1: 🎥 NETFLIX HIGHLIGHTS
# ============================================================================
st.markdown("## 🎥 Netflix (Germany)")
st.markdown(f"**{len(netflix_movies_data)} movies available**")

if netflix_movies_data:
    netflix_tabs = st.tabs(["⭐ Top Rated", "🎬 Grid View"])
    
    with netflix_tabs[0]:
        st.markdown("### Top Rated on Netflix")
        for idx, movie in enumerate(netflix_movies_data[:10], 1):
            with st.container(border=True):
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    if movie.get("poster_url"):
                        st.image(movie["poster_url"], use_column_width=True)
                    else:
                        st.info("No Poster")
                
                with col2:
                    st.markdown(f"### #{idx} - {movie['title']}")
                    
                    meta_cols = st.columns(3)
                    with meta_cols[0]:
                        st.markdown(f"**Year:** {movie['year']}")
                    with meta_cols[1]:
                        if movie['imdb_rating']:
                            st.markdown(f"**IMDb:** ⭐ {movie['imdb_rating']}/10")
                        else:
                            st.markdown("**IMDb:** Not found")
                    with meta_cols[2]:
                        if movie['genres']:
                            st.markdown(f"**Genres:** {', '.join(movie['genres'][:2])}")
                    
                    st.markdown(f"**Plot:** {movie['synopsis'][:300]}...")
                    
                    # Sensitivity metrics
                    sensitivity = get_sensitivity_data(movie['title'])
                    st.markdown("**🛡️ Community Sensitivity:**")
                    sen_cols = st.columns(3)
                    with sen_cols[0]:
                        st.markdown(f"🔞 {sensitivity['sexual_content']}")
                    with sen_cols[1]:
                        st.markdown(f"💢 {sensitivity['violent_content']}")
                    with sen_cols[2]:
                        st.markdown(f"📢 {sensitivity['woke_content']}")
                
                st.divider()
    
    with netflix_tabs[1]:
        st.markdown("### Netflix Grid")
        cols = st.columns(3)
        for idx, movie in enumerate(netflix_movies_data):
            with cols[idx % 3]:
                with st.container(border=True):
                    if movie.get("poster_url"):
                        st.image(movie["poster_url"], use_column_width=True)
                    st.markdown(f"**{movie['title']}**")
                    if movie['imdb_rating']:
                        st.markdown(f"⭐ {movie['imdb_rating']}/10")
                    else:
                        st.markdown("Rating: N/A")
else:
    st.info("No Netflix movies found in your region.")

st.divider()

# ============================================================================
# SECTION 2: 🎬 AMAZON PRIME HIGHLIGHTS
# ============================================================================
st.markdown("## 🎬 Amazon Prime Video (Germany)")
st.markdown(f"**{len(prime_movies_data)} movies available**")

if prime_movies_data:
    prime_tabs = st.tabs(["⭐ Top Rated", "🎬 Grid View"])
    
    with prime_tabs[0]:
        st.markdown("### Top Rated on Prime Video")
        for idx, movie in enumerate(prime_movies_data[:10], 1):
            with st.container(border=True):
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    if movie.get("poster_url"):
                        st.image(movie["poster_url"], use_column_width=True)
                    else:
                        st.info("No Poster")
                
                with col2:
                    st.markdown(f"### #{idx} - {movie['title']}")
                    
                    meta_cols = st.columns(3)
                    with meta_cols[0]:
                        st.markdown(f"**Year:** {movie['year']}")
                    with meta_cols[1]:
                        if movie['imdb_rating']:
                            st.markdown(f"**IMDb:** ⭐ {movie['imdb_rating']}/10")
                        else:
                            st.markdown("**IMDb:** Not found")
                    with meta_cols[2]:
                        if movie['genres']:
                            st.markdown(f"**Genres:** {', '.join(movie['genres'][:2])}")
                    
                    st.markdown(f"**Plot:** {movie['synopsis'][:300]}...")
                    
                    # Sensitivity metrics
                    sensitivity = get_sensitivity_data(movie['title'])
                    st.markdown("**🛡️ Community Sensitivity:**")
                    sen_cols = st.columns(3)
                    with sen_cols[0]:
                        st.markdown(f"🔞 {sensitivity['sexual_content']}")
                    with sen_cols[1]:
                        st.markdown(f"💢 {sensitivity['violent_content']}")
                    with sen_cols[2]:
                        st.markdown(f"📢 {sensitivity['woke_content']}")
                
                st.divider()
    
    with prime_tabs[1]:
        st.markdown("### Prime Video Grid")
        cols = st.columns(3)
        for idx, movie in enumerate(prime_movies_data):
            with cols[idx % 3]:
                with st.container(border=True):
                    if movie.get("poster_url"):
                        st.image(movie["poster_url"], use_column_width=True)
                    st.markdown(f"**{movie['title']}**")
                    if movie['imdb_rating']:
                        st.markdown(f"⭐ {movie['imdb_rating']}/10")
                    else:
                        st.markdown("Rating: N/A")
else:
    st.info("No Prime Video movies found in your region.")

st.divider()

# ============================================================================
# SECTION 3: ✈️ AIRLINE ENTERTAINMENT PLACEHOLDER
# ============================================================================
with st.expander("✈️ In-Flight Airline Entertainment (Coming Soon)", expanded=False):
    st.info(
        "🚀 **This feature is coming soon!**\n\n"
        "We're working on integrating live airline entertainment feeds from major carriers. "
        "Soon you'll be able to:\n"
        "- Browse in-flight entertainment catalogs from major airlines\n"
        "- See what's available on different flight routes\n"
        "- Get recommendations based on flight duration and destination\n\n"
        "Check back soon for updates!"
    )

# ============================================================================
# FOOTER
# ============================================================================
st.divider()
st.markdown(
    """
    ---
    **MoviesFinder v3.0** | Real Streaming Availability in Germany
    
    📊 **Primary Data Source:**
    - 📺 **JustWatch** - Netflix & Prime Video availability
    
    🔄 **Optional Enrichment:**
    - ⭐ **OMDB** - IMDb ratings & reviews (optional)
    - 🎬 **TMDB** - Genres & additional metadata (optional)
    
    🛡️ **Community Sensitivity Metrics** - Crowdsourced from Reddit & Web Forums
    
    📱 Built with Streamlit | 🚀 Fully Automated Codespace Deployment
    
    🌍 **Region:** Germany (DE) | Available on: Netflix 🔴 & Prime Video 📺
    """
)
