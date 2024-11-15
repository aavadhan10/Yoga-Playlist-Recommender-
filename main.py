import streamlit as st
import pandas as pd
from anthropic import Anthropic
import json
from datetime import datetime

# Initialize Anthropic client
anthropic_client = Anthropic(api_key='ANTHROPIC_API_KEY')  # Replace with your actual API key

def get_claude_recommendations(theme):
    prompt = f"""You are a yoga music expert. Create a playlist for a 60-minute yoga class with the theme: {theme}.
    
    The class has these sections:
    1. Grounding & Warm Up (8-10 min): Intensity 1-2
    2. Sun Salutations (2-3 min): Intensity 1-3
    3. Movement Series 1 (8-10 min): Intensity 2-3
    4. Movement Series 2 (10-12 min): Intensity 2-4
    5. Integration Series (8-10 min): Intensity 2-4
    6. Savasana (8-10 min): Intensity 1-2

    For each section, recommend 3 songs that fit the intensity and theme. Include:
    - Song name and artist
    - Duration (MM:SS format)
    - Intensity level (1-5)
    - Brief explanation why this song fits

    Return as JSON in this format:
    {{"sections": {{"section_name": {{"duration": "str", "intensity": "str", "songs": [{{"name": "str", "artist": "str", "length": "str", "intensity": int, "reason": "str"}}]}}}}}}
    """

    try:
        message = anthropic_client.beta.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1500,
            temperature=0.7,
            system="You are a yoga music expert who provides song recommendations.",
            messages=[{"role": "user", "content": prompt}]
        )
        return json.loads(message.content[0].text)
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

def calculate_duration(length_str):
    minutes, seconds = map(int, length_str.split(':'))
    return minutes * 60 + seconds

def main():
    st.set_page_config(page_title="Yoga Playlist Creator", page_icon="🧘‍♀️", layout="wide")
    
    st.markdown("""
        <style>
        .stAlert {border-radius: 10px;}
        .stProgress .st-bp {background-color: #9DB5B2;}
        div[data-testid="stExpander"] {border-radius: 10px; border: 1px solid #ddd;}
        </style>
    """, unsafe_allow_html=True)
    
    st.title("🧘‍♀️ Yoga Playlist Creator")
    
    if 'recommendations' not in st.session_state:
        st.session_state.recommendations = None
    if 'playlist_history' not in st.session_state:
        st.session_state.playlist_history = []
    
    with st.sidebar:
        st.header("🎵 Recent Playlists")
        for idx, playlist in enumerate(st.session_state.playlist_history[-5:]):
            st.text(f"{idx + 1}. {playlist['theme']}")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        theme = st.text_input("Enter your desired music theme:", 
                            placeholder="e.g., lo-fi, calm edm, country, rap")
        
        preferences = st.text_area("Additional preferences (optional):",
                                placeholder="e.g., female vocals, instrumental only, specific artists...")
        
        col1_1, col1_2 = st.columns(2)
        with col1_1:
            generate = st.button("🎵 Generate Playlist", type="primary", use_container_width=True)
        with col1_2:
            clear = st.button("🗑️ Clear", type="secondary", use_container_width=True)
            if clear:
                st.session_state.recommendations = None
    
    if generate:
        if not theme:
            st.error("Please enter a music theme.")
        else:
            with st.spinner("Creating your perfect yoga playlist..."):
                st.session_state.recommendations = get_claude_recommendations(
                    f"{theme} {preferences}".strip()
                )
                if st.session_state.recommendations:
                    st.session_state.playlist_history.append({
                        'theme': theme,
                        'timestamp': datetime.now(),
                        'recommendations': st.session_state.recommendations
                    })
    
    if st.session_state.recommendations:
        st.markdown("### 🎵 Your Customized Yoga Playlist")
        
        total_duration = 0
        for section, details in st.session_state.recommendations['sections'].items():
            with st.expander(f"🎼 {section} ({details['duration']} | Intensity: {details['intensity']})"):
                songs_df = pd.DataFrame(details['songs'])
                
                section_duration = sum(calculate_duration(song['length']) for song in details['songs'])
                total_duration += section_duration
                
                st.dataframe(
                    songs_df,
                    hide_index=True,
                    column_config={
                        "name": st.column_config.TextColumn("Song"),
                        "artist": st.column_config.TextColumn("Artist"),
                        "length": st.column_config.TextColumn("Duration"),
                        "intensity": st.column_config.NumberColumn(
                            "Intensity",
                            help="1 (very calm) to 5 (high energy)",
                            min_value=1,
                            max_value=5,
                            format="%d ⚡"
                        ),
                        "reason": st.column_config.TextColumn("Why This Song")
                    }
                )
                
                st.caption(f"Section duration: {section_duration//60}:{section_duration%60:02d}")
        
        st.success(f"Total Playlist Duration: {total_duration//60} minutes {total_duration%60} seconds")
        
        col3, col4 = st.columns(2)
        with col3:
            st.download_button(
                "💾 Download Playlist",
                data=json.dumps(st.session_state.recommendations, indent=4),
                file_name=f"yoga_playlist_{theme}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json",
                use_container_width=True
            )

if __name__ == "__main__":
    main()
