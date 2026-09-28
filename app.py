import streamlit as st
import os
import json
import re
import requests
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
MODEL = "openai/gpt-oss-120b"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if GROQ_API_KEY:
    client = Groq(api_key=GROQ_API_KEY)
else:
    client = None


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="ExploreGenie",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>

    .main {
        background-color: #f8fafc;
    }

    .block-container {
        padding-top: 2rem;
        padding-left: 4rem;
        padding-right: 4rem;
        max-width: 1400px;
    }

    .hero {
        padding: 35px;
        border-radius: 22px;
        background: linear-gradient(135deg, #eef7ff, #f8fbff);
        border: 1px solid #dbeafe;
        margin-bottom: 30px;
    }

    .hero-title {
        font-size: 48px;
        font-weight: 800;
        color: #12355b;
        margin-bottom: 5px;
    }

    .hero-subtitle {
        font-size: 19px;
        color: #64748b;
    }

    .section-title {
        font-size: 30px;
        font-weight: 750;
        color: #12355b;
        margin-top: 25px;
        margin-bottom: 15px;
    }

    .card {
        padding: 20px;
        border-radius: 18px;
        background: white;
        border: 1px solid #e2e8f0;
        box-shadow: 0 5px 18px rgba(15, 23, 42, 0.05);
        margin-bottom: 18px;
    }

    .card-title {
        font-size: 21px;
        font-weight: 700;
        color: #12355b;
    }

    .card-text {
        color: #64748b;
        font-size: 15px;
        line-height: 1.6;
    }

    .tag {
        display: inline-block;
        background: #e0f2fe;
        color: #0369a1;
        padding: 5px 10px;
        border-radius: 20px;
        margin: 3px;
        font-size: 13px;
    }

    .hotel-box {
        padding: 18px;
        border-radius: 16px;
        background: #fff;
        border: 1px solid #e2e8f0;
        margin-bottom: 15px;
    }

    .small-note {
        color: #64748b;
        font-size: 13px;
    }

    div[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }

</style>
""", unsafe_allow_html=True)


# ============================================================
# SESSION STATE
# ============================================================

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "last_trip" not in st.session_state:
    st.session_state.last_trip = None

if "last_hotels" not in st.session_state:
    st.session_state.last_hotels = []


# ============================================================
# LOAD DESTINATIONS
# ============================================================

@st.cache_data
def load_destinations():

    possible_paths = [
        BASE_DIR / "data" / "destinations.json",
        BASE_DIR / "destinations.json"
    ]

    file_path = None

    for path in possible_paths:
        if path.exists():
            file_path = path
            break

    if file_path is None:
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data

    except Exception as e:
        st.error(f"Could not load destinations.json: {e}")
        return []


destinations = load_destinations()


# ============================================================
# GROQ FUNCTION
# ============================================================

def generate_groq_response(
    prompt,
    system_prompt="You are ExploreGenie, a helpful AI tourism assistant."
):

    if not client:
        return "⚠️ GROQ_API_KEY is missing. Please check your .env file."

    try:

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_completion_tokens=3000
        )

        return response.choices[0].message.content

    except Exception as e:

        return f"⚠️ Groq API error: {str(e)}"


# ============================================================
# IMAGE SEARCH USING WIKIMEDIA COMMONS
# ============================================================

@st.cache_data(show_spinner=False)
def get_wikimedia_image(search_term):

    try:

        url = "https://commons.wikimedia.org/w/api.php"

        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": search_term,
            "gsrnamespace": 6,
            "gsrlimit": 1,
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": 900,
            "format": "json"
        }

        response = requests.get(
            url,
            params=params,
            timeout=10,
            headers={
                "User-Agent": "ExploreGenie/1.0"
            }
        )

        data = response.json()

        pages = data.get("query", {}).get("pages", {})

        for page in pages.values():

            image_info = page.get("imageinfo", [])

            if image_info:

                return (
                    image_info[0].get("thumburl")
                    or image_info[0].get("url")
                )

    except Exception:
        pass

    return None


# ============================================================
# IMAGE CARD
# ============================================================

def show_image(search_term, caption=None):

    image_url = get_wikimedia_image(search_term)

    if image_url:

        st.image(
            image_url,
            caption=caption if caption else search_term,
            use_container_width=True
        )

    else:

        st.info(
            f"📷 Image unavailable for {caption or search_term}"
        )


# ============================================================
# DESTINATION HELPERS
# ============================================================

def get_destination(name):

    for destination in destinations:

        if destination.get("name", "").lower() == name.lower():
            return destination

    return None


def get_place_name(place):

    if isinstance(place, str):
        return place

    if isinstance(place, dict):
        return (
            place.get("name")
            or place.get("title")
            or place.get("place")
            or "Tourist Place"
        )

    return str(place)


def get_restaurant_name(restaurant):

    if isinstance(restaurant, str):
        return restaurant

    if isinstance(restaurant, dict):
        return (
            restaurant.get("name")
            or restaurant.get("restaurant")
            or restaurant.get("title")
            or "Restaurant"
        )

    return str(restaurant)


# ============================================================
# AI HOTEL SUGGESTIONS
# ============================================================

def get_ai_hotels(destination, budget):

    prompt = f"""
You are helping a tourism application.

Destination: {destination}
Budget level: {budget}

Suggest 4 real and well-known hotels in {destination} suitable for the
given budget level.

Return ONLY valid JSON in this exact format:

[
  {{
    "name": "Hotel name",
    "reason": "Short reason why it is suitable"
  }}
]

Do not include:
- prices
- ratings
- fake hotels
- booking links

Prefer established hotels that are likely to actually exist.
"""

    if not client:
        return []

    try:

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You provide tourism recommendations in structured JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_completion_tokens=1000,
            response_format={
                "type": "json_object"
            }
        )

        raw = response.choices[0].message.content

        data = json.loads(raw)

        if isinstance(data, list):
            return data

        if isinstance(data, dict):

            for value in data.values():

                if isinstance(value, list):
                    return value

    except Exception:
        pass

    return []


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("## 🌍 ExploreGenie")

    st.caption("AI-Powered Smart Tourism Assistant")

    st.divider()

    page = st.radio(
        "Navigate",
        [
            "🏠 Home",
            "✈️ AI Trip Planner",
            "💬 Travel Assistant",
            "🗺️ Explore Destinations"
        ]
    )

    st.divider()

    st.markdown("### ✨ Powered by")

    st.write("🤖 Groq AI")
    st.write("🐍 Python")
    st.write("🎨 Streamlit")
    st.write("📸 Wikimedia Commons")


# ============================================================
# HOME PAGE
# ============================================================

if page == "🏠 Home":

    st.markdown("""
    <div class="hero">

        <div class="hero-title">
            🌍 ExploreGenie
        </div>

        <div class="hero-subtitle">
            Your AI-powered smart tourism assistant
        </div>

        <p>
        Plan personalized trips, discover destinations,
        find places to visit, explore food and restaurants,
        and get AI-powered travel suggestions.
        </p>

    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div class="section-title">✨ What can ExploreGenie do?</div>',
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.markdown("""
        <div class="card">

        <div class="card-title">
        ✈️ AI Trip Planner
        </div>

        <div class="card-text">
        Generate personalized day-by-day itineraries
        according to your destination, budget,
        interests and travel style.
        </div>

        </div>
        """, unsafe_allow_html=True)

    with col2:

        st.markdown("""
        <div class="card">

        <div class="card-title">
        🗺️ Destination Explorer
        </div>

        <div class="card-text">
        Explore tourist attractions, restaurants,
        food recommendations and destination details
        with visual information.
        </div>

        </div>
        """, unsafe_allow_html=True)

    with col3:

        st.markdown("""
        <div class="card">

        <div class="card-title">
        🤖 AI Travel Assistant
        </div>

        <div class="card-text">
        Ask travel questions and receive
        personalized AI-generated answers
        using natural language.
        </div>

        </div>
        """, unsafe_allow_html=True)

    st.markdown(
        '<div class="section-title">🌎 Popular Destinations</div>',
        unsafe_allow_html=True
    )

    if destinations:

        cols = st.columns(4)

        for index, destination in enumerate(destinations[:8]):

            with cols[index % 4]:

                name = destination.get("name", "Destination")

                image = get_wikimedia_image(
                    destination.get(
                        "cover_wiki",
                        name
                    )
                )

                if image:
                    st.image(
                        image,
                        use_container_width=True
                    )

                st.markdown(f"### {name}")

                st.caption(
                    destination.get(
                        "tagline",
                        "Explore this destination"
                    )
                )


# ============================================================
# AI TRIP PLANNER
# ============================================================

elif page == "✈️ AI Trip Planner":

    st.markdown(
        '<div class="section-title">✈️ AI Trip Planner</div>',
        unsafe_allow_html=True
    )

    st.write(
        "Tell ExploreGenie what kind of trip you want and let AI build your itinerary."
    )

    if not destinations:

        st.error("No destinations found. Check destinations.json.")

    else:

        destination_names = [
            d.get("name")
            for d in destinations
            if d.get("name")
        ]

        col1, col2 = st.columns(2)

        with col1:

            destination = st.selectbox(
                "📍 Choose destination",
                destination_names
            )

            days = st.slider(
                "📅 Number of days",
                1,
                15,
                3
            )

            budget = st.selectbox(
                "💰 Budget",
                [
                    "Budget",
                    "Moderate",
                    "Luxury"
                ]
            )

        with col2:

            interests = st.multiselect(
                "❤️ Your interests",
                [
                    "History",
                    "Nature",
                    "Adventure",
                    "Food",
                    "Shopping",
                    "Culture",
                    "Photography",
                    "Nightlife",
                    "Beaches",
                    "Spirituality"
                ]
            )

            travel_style = st.selectbox(
                "🎒 Travel style",
                [
                    "Relaxed",
                    "Balanced",
                    "Adventure-packed",
                    "Family-friendly",
                    "Romantic",
                    "Solo"
                ]
            )

        preferences = st.text_area(
            "📝 Additional preferences",
            placeholder="Example: I love local food and photography. Avoid very crowded places."
        )

        generate_button = st.button(
            "✨ Generate My AI Trip",
            type="primary",
            use_container_width=True
        )

        if generate_button:

            if not interests:
                interests_text = "General sightseeing and local experiences"
            else:
                interests_text = ", ".join(interests)

            prompt = f"""
Create a personalized travel itinerary.

Destination:
{destination}

Trip duration:
{days} days

Budget:
{budget}

Interests:
{interests_text}

Travel style:
{travel_style}

Additional preferences:
{preferences if preferences else "None"}

Create a practical itinerary.

Include:

1. Trip overview
2. Day-by-day itinerary
3. Tourist attractions
4. Food experiences
5. Restaurant suggestions
6. Approximate budget categories
7. Travel tips
8. Packing suggestions

Use clear headings and bullet points.

Do not invent exact hotel prices, ticket prices,
opening hours or live availability.
"""

            with st.spinner("🤖 ExploreGenie is planning your trip..."):

                result = generate_groq_response(
                    prompt,
                    """
                    You are ExploreGenie, an expert AI tourism planner.
                    Create useful, realistic and personalized travel itineraries.
                    Avoid presenting uncertain live information as fact.
                    """
                )

            st.session_state.last_trip = {
                "destination": destination,
                "budget": budget,
                "days": days,
                "result": result
            }

            # Generate hotel recommendations once
            with st.spinner("🏨 Finding AI-suggested hotel options..."):

                st.session_state.last_hotels = get_ai_hotels(
                    destination,
                    budget
                )

        # ----------------------------------------------------
        # DISPLAY GENERATED TRIP
        # ----------------------------------------------------

        if st.session_state.last_trip:

            trip = st.session_state.last_trip

            st.divider()

            st.markdown(
                f"""
                <div class="hero">

                <div class="hero-title">
                ✈️ Your {trip["days"]}-Day Trip to {trip["destination"]}
                </div>

                <div class="hero-subtitle">
                Budget: {trip["budget"]}
                </div>

                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown(trip["result"])

            st.divider()

            # ==================================================
            # TOURIST PLACES
            # ==================================================

            selected_destination = get_destination(
                trip["destination"]
            )

            if selected_destination:

                st.markdown(
                    '<div class="section-title">📍 Places to Visit</div>',
                    unsafe_allow_html=True
                )

                places = selected_destination.get(
                    "places",
                    []
                )

                place_cols = st.columns(3)

                for index, place in enumerate(places[:6]):

                    place_name = get_place_name(place)

                    with place_cols[index % 3]:

                        image_url = get_wikimedia_image(
                            f"{place_name} {trip['destination']}"
                        )

                        if image_url:

                            st.image(
                                image_url,
                                use_container_width=True
                            )

                        st.markdown(
                            f"### 📍 {place_name}"
                        )

                # ==================================================
                # RESTAURANTS
                # ==================================================

                st.markdown(
                    '<div class="section-title">🍛 Food & Restaurants</div>',
                    unsafe_allow_html=True
                )

                restaurants = selected_destination.get(
                    "restaurants",
                    []
                )

                restaurant_cols = st.columns(3)

                for index, restaurant in enumerate(
                    restaurants[:6]
                ):

                    restaurant_name = get_restaurant_name(
                        restaurant
                    )

                    with restaurant_cols[index % 3]:

                        image_url = get_wikimedia_image(
                            f"{restaurant_name} {trip['destination']}"
                        )

                        if image_url:

                            st.image(
                                image_url,
                                use_container_width=True
                            )

                        st.markdown(
                            f"### 🍛 {restaurant_name}"
                        )

                # ==================================================
                # HOTELS
                # ==================================================

                st.markdown(
                    '<div class="section-title">🏨 Suggested Hotels</div>',
                    unsafe_allow_html=True
                )

                st.caption(
                    "These are AI-suggested hotel options. "
                    "Verify current availability and prices before booking."
                )

                hotels = st.session_state.last_hotels

                if hotels:

                    hotel_cols = st.columns(2)

                    for index, hotel in enumerate(hotels[:4]):

                        hotel_name = hotel.get(
                            "name",
                            "Hotel"
                        )

                        reason = hotel.get(
                            "reason",
                            ""
                        )

                        with hotel_cols[index % 2]:

                            st.markdown(
                                '<div class="hotel-box">',
                                unsafe_allow_html=True
                            )

                            image_url = get_wikimedia_image(
                                f"{hotel_name} {trip['destination']}"
                            )

                            if image_url:

                                st.image(
                                    image_url,
                                    use_container_width=True
                                )

                            st.markdown(
                                f"### 🏨 {hotel_name}"
                            )

                            st.write(reason)

                            st.markdown(
                                '</div>',
                                unsafe_allow_html=True
                            )

                else:

                    st.info(
                        "Hotel suggestions could not be generated. "
                        "You can still use the itinerary and destination recommendations."
                    )


# ============================================================
# TRAVEL ASSISTANT
# ============================================================

elif page == "💬 Travel Assistant":

    st.markdown(
        '<div class="section-title">💬 AI Travel Assistant</div>',
        unsafe_allow_html=True
    )

    st.write(
        "Ask ExploreGenie anything about your travel plans."
    )

    # Display previous messages

    for message in st.session_state.chat_history:

        with st.chat_message(message["role"]):

            st.markdown(
                message["content"]
            )

    user_question = st.chat_input(
        "Ask something like: What should I eat in Hyderabad?"
    )

    if user_question:

        st.session_state.chat_history.append(
            {
                "role": "user",
                "content": user_question
            }
        )

        with st.chat_message("user"):
            st.markdown(user_question)

        context = ""

        if st.session_state.last_trip:

            context = f"""
The user recently planned a trip to
{st.session_state.last_trip["destination"]}
for {st.session_state.last_trip["days"]} days.

Budget:
{st.session_state.last_trip["budget"]}
"""

        prompt = f"""
{context}

User question:
{user_question}

Answer as a friendly AI tourism assistant.

Give practical and clear information.
If something depends on current prices,
availability or opening hours, tell the user
to verify the latest information.
"""

        with st.chat_message("assistant"):

            with st.spinner("Thinking..."):

                answer = generate_groq_response(
                    prompt,
                    """
                    You are ExploreGenie, a friendly AI travel assistant.
                    Give concise but useful tourism advice.
                    """
                )

            st.markdown(answer)

        st.session_state.chat_history.append(
            {
                "role": "assistant",
                "content": answer
            }
        )

    if st.button("🗑️ Clear Chat"):

        st.session_state.chat_history = []

        st.rerun()


# ============================================================
# EXPLORE DESTINATIONS
# ============================================================

elif page == "🗺️ Explore Destinations":

    st.markdown(
        '<div class="section-title">🗺️ Explore Destinations</div>',
        unsafe_allow_html=True
    )

    st.write(
        "Browse destinations and discover places, food and travel information."
    )

    if destinations:

        destination_names = [
            d.get("name")
            for d in destinations
            if d.get("name")
        ]

        selected_name = st.selectbox(
            "🔎 Select a destination",
            destination_names
        )

        selected = get_destination(
            selected_name
        )

        if selected:

            st.divider()

            # ==================================================
            # COVER
            # ==================================================

            cover_term = selected.get(
                "cover_wiki",
                selected_name
            )

            cover_image = get_wikimedia_image(
                cover_term
            )

            if cover_image:

                st.image(
                    cover_image,
                    use_container_width=True
                )

            st.markdown(
                f"# 🌍 {selected_name}"
            )

            st.write(
                selected.get(
                    "description",
                    ""
                )
            )

            # ==================================================
            # QUICK INFO
            # ==================================================

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Best Time",
                    selected.get(
                        "best_time",
                        "Varies"
                    )
                )

            with col2:
                st.metric(
                    "Budget",
                    selected.get(
                        "budget_level",
                        "Varies"
                    )
                )

            with col3:
                st.metric(
                    "Ideal Days",
                    selected.get(
                        "ideal_days",
                        "Varies"
                    )
                )

            with col4:
                st.metric(
                    "Country",
                    selected.get(
                        "country",
                        ""
                    )
                )

            # ==================================================
            # PLACES
            # ==================================================

            st.markdown(
                '<div class="section-title">📍 Tourist Places</div>',
                unsafe_allow_html=True
            )

            places = selected.get(
                "places",
                []
            )

            cols = st.columns(3)

            for index, place in enumerate(places):

                place_name = get_place_name(place)

                with cols[index % 3]:

                    image_url = get_wikimedia_image(
                        f"{place_name} {selected_name}"
                    )

                    if image_url:

                        st.image(
                            image_url,
                            use_container_width=True
                        )

                    st.markdown(
                        f"### {place_name}"
                    )

            # ==================================================
            # RESTAURANTS
            # ==================================================

            st.markdown(
                '<div class="section-title">🍛 Restaurants & Food</div>',
                unsafe_allow_html=True
            )

            restaurants = selected.get(
                "restaurants",
                []
            )

            cols = st.columns(3)

            for index, restaurant in enumerate(
                restaurants
            ):

                restaurant_name = get_restaurant_name(
                    restaurant
                )

                with cols[index % 3]:

                    image_url = get_wikimedia_image(
                        f"{restaurant_name} {selected_name}"
                    )

                    if image_url:

                        st.image(
                            image_url,
                            use_container_width=True
                        )

                    st.markdown(
                        f"### 🍛 {restaurant_name}"
                    )

            # ==================================================
            # AI DESTINATION GUIDE
            # ==================================================

            st.markdown(
                '<div class="section-title">🤖 Ask AI About This Destination</div>',
                unsafe_allow_html=True
            )

            question = st.text_input(
                f"Ask something about {selected_name}",
                placeholder="Example: Plan a 2-day food and culture trip"
            )

            if st.button(
                "✨ Generate AI Guide"
            ):

                prompt = f"""
Destination:
{selected_name}

Destination information:
{json.dumps(selected, indent=2)}

User request:
{question}

Create a useful personalized tourism guide.
"""

                with st.spinner(
                    "🤖 Generating your guide..."
                ):

                    guide = generate_groq_response(
                        prompt
                    )

                st.markdown(guide)


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.markdown(
    """
    <div style="text-align:center;color:#94a3b8;padding:15px;">
        🌍 ExploreGenie — AI-Powered Smart Tourism Assistant
        <br>
        Built with Python + Streamlit + Groq
    </div>
    """,
    unsafe_allow_html=True
)