import streamlit as st
import pandas as pd
from anthropic import Anthropic
import json
from datetime import datetime
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Get credentials from environment or Streamlit secrets
spotify_client_id = os.getenv('SPOTIFY_CLIENT_ID') or st.secrets['SPOTIFY_CLIENT_ID']
spotify_client_secret = os.getenv('SPOTIFY_CLIENT_SECRET') or st.secrets['SPOTIFY_CLIENT_SECRET']
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY') or st.secrets['ANTHROPIC_API_KEY']

# Initialize clients
anthropic_client = Anthropic(api_key=anthropic_api_key)
spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(
    client_id=spotify_client_id,
    client_secret=spotify_client_secret
))

def get_spotify_link(song_name, artist):
    try:
        # Try exact match first
        query = f"track:\"{song_name}\" artist:\"{artist}\""
        results = spotify.search(q=query, type='track', limit=1)
        
        if not results['tracks']['items']:
            # Try more lenient search
            query = f"{song_name} {artist}"
            results = spotify.search(q=query, type='track', limit=1)
        
        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            return {
                'url': track['external_urls']['spotify'],
                'preview_url': track.get('preview_url'),
                'duration_ms': track['duration_ms'],
                'verified_name': track['name'],
                'verified_artist': track['artists'][0]['name'],
                'popularity': track['popularity']
            }
        return None
    except Exception as e:
        st.error(f"Error fetching Spotify data: {str(e)}")
        return None

def adjust_section_times(duration):
    if duration == "45":
        return {
            "Grounding & Warm Up": "5-7",
            "Sun Salutations": "2-3",
            "Movement Series 1": "6-8",
            "Movement Series 2": "8-10",
            "Integration Series": "6-8",
            "Savasana": "5-7"
        }
    elif duration == "75":
        return {
            "Grounding & Warm Up": "10-12",
            "Sun Salutations": "3-4",
            "Movement Series 1": "12-15",
            "Movement Series 2": "15-17",
            "Integration Series": "12-15",
            "Savasana": "10-12"
        }
    else:  # 60 minutes
        return {
            "Grounding & Warm Up": "8-10",
            "Sun Salutations": "2-3",
            "Movement Series 1": "8-10",
            "Movement Series 2": "10-12",
            "Integration Series": "8-10",
            "Savasana": "8-10"
        }

def get_claude_recommendations(theme, class_duration):
    section_times = adjust_section_times(class_duration)
    
    prompt = f"""Create a yoga playlist using ONLY REAL, POPULAR songs that definitely exist on Spotify for a {class_duration}-minute class with theme: {theme}. 
    
Return a JSON object with ALL of these exact sections, maintaining this exact structure:

{{
  "sections": {{
    "Grounding & Warm Up": {{
      "duration": "{section_times['Grounding & Warm Up']} minutes",
      "section_intensity": "1-2",
      "songs": [
        {{
          "name": "[Real Song Name]",
          "artist": "[Actual Artist]",
          "intensity": 1,
          "reason": "Brief reason for choice"
        }}
      ]
    }},
    "Sun Salutations": {{
      "duration": "{section_times['Sun Salutations']} minutes",
      "section_intensity": "2-3",
      "songs": [
        {{
          "name": "[Real Song Name]",
          "artist": "[Actual Artist]",
          "intensity": 2,
          "reason": "Brief reason for choice"
        }}
      ]
    }},
    "Movement Series 1": {{
      "duration": "{section_times['Movement Series 1']} minutes",
      "section_intensity": "2-3",
      "songs": [
        {{
          "name": "[Real Song Name]",
          "artist": "[Actual Artist]",
          "intensity": 2,
          "reason": "Brief reason for choice"
        }}
      ]
    }},
    "Movement Series 2": {{
      "duration": "{section_times['Movement Series 2']} minutes",
      "section_intensity": "3-4",
      "songs": [
        {{
          "name": "[Real Song Name]",
          "artist": "[Actual Artist]",
          "intensity": 3,
          "reason": "Brief reason for choice"
        }}
      ]
    }},
    "Integration Series": {{
      "duration": "{section_times['Integration Series']} minutes",
      "section_intensity": "2-3",
      "songs": [
        {{
          "name": "[Real Song Name]",
          "artist": "[Actual Artist]",
          "intensity": 2,
          "reason": "Brief reason for choice"
        }}
      ]
    }},
    "Savasana": {{
      "duration": "{section_times['Savasana']} minutes",
      "section_intensity": "1-2",
      "songs": [
        {{
          "name": "[Real Song Name]",
          "artist": "[Actual Artist]",
          "intensity": 1,
          "reason": "Brief reason for choice"
        }}
      ]
    }}
  }}
}}

Critical Requirements:
1. Include ALL sections exactly as shown above
2. Use ONLY well-known songs that definitely exist on Spotify
3. For each section, include 2-3 popular songs that match the intensity
4. Verify each song name and artist name is accurate
5. Double-check spelling of both song and artist names
6. Choose songs that are relatively popular and easy to find"""

    try:
        message = anthropic_client.beta.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1500,
            temperature=0.7,
            system="You are a yoga music expert. Recommend only popular, well-known songs that definitely exist on Spotify. Focus on songs with over 1 million plays.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse JSON response
        response_text = message.content[0].text.strip()
        response_text = response_text.replace('```json', '').replace('```', '').strip()
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            parsed_json = json.loads(json_str)
            
            # Verify all required sections are present
            required_sections = [
                "Grounding & Warm Up", "Sun Salutations", "Movement Series 1",
                "Movement Series 2", "Integration Series", "Savasana"
            ]
            
            for section in required_sections:
                if section not in parsed_json["sections"]:
                    st.error(f"Missing required section: {section}")
                    return None
            
            # Enhance the recommendations with Spotify data
            for section in parsed_json['sections'].values():
                for song in section['songs']:
                    spotify_data = get_spotify_link(song['name'], song['artist'])
                    if spotify_data:
                        song['spotify_url'] = spotify_data['url']
                        song['preview_url'] = spotify_data['preview_url']
                        song['length'] = f"{spotify_data['duration_ms'] // 60000}:{(spotify_data['duration_ms'] % 60000 // 1000):02d}"
                        song['verified_name'] = spotify_data['verified_name']
                        song['verified_artist'] = spotify_data['verified_artist']
                        song['popularity'] = spotify_data['popularity']
                    else:
                        st.warning(f"Couldn't find '{song['name']}' by {song['artist']} on Spotify")
            
            return parsed_json
            
        else:
            st.error("Could not find valid JSON in the response")
            return None
            
    except Exception as e:
        st.error(f"Error getting recommendations: {str(e)}")
        return None

def main():
    st.set_page_config(page_title="Yoga Playlist Creator", page_icon="🧘‍♀️", layout="wide")
    
    st.markdown("""
        <style>
        .stAlert {border-radius: 10px;}
        .stProgress .st-bp {background-color: #9DB5B2;}
        div[data-testid="stExpander"] {border-radius: 10px; border: 1px solid #ddd;}
        .spotify-button {
            background-color: #1DB954;
            color: white !important;
            padding: 4px 12px;
            border-radius: 20px;
            text-decoration: none;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            transition: all 0.2s ease;
        }
        .spotify-button:hover {
            opacity: 0.9;
            transform: translateY(-1px);
        }
        .stDataFrame {
            font-size: 14px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("🧘‍♀️ Yoga Playlist Creator with Spotify")
    
    if 'recommendations' not in st.session_state:
        st.session_state.recommendations = None
    if 'playlist_history' not in st.session_state:
        st.session_state.playlist_history = []
    
    with st.sidebar:
        st.header("🎵 Recent Playlists")
        for idx, playlist in enumerate(reversed(st.session_state.playlist_history[-5:])):
            with st.expander(f"🎵 {playlist['theme']} ({playlist['duration']})"):
                st.text(f"Created: {playlist['timestamp'].strftime('%Y-%m-%d %H:%M')}")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        theme = st.text_input("Enter your desired music theme:", 
                            placeholder="e.g., lo-fi, calm edm, country, rap")
        
        preferences = st.text_area("Additional preferences (optional):",
                                placeholder="e.g., female vocals, instrumental only, specific artists...")
        
        class_duration = st.selectbox("Class Duration:", 
                                    options=["45", "60", "75"],
                                    index=1,
                                    format_func=lambda x: f"{x} Minutes")
        
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
            with st.spinner("Creating your perfect yoga playlist with Spotify integration..."):
                st.session_state.recommendations = get_claude_recommendations(
                    f"{theme} {preferences}".strip(),
                    class_duration
                )
                if st.session_state.recommendations:
                    st.session_state.playlist_history.append({
                        'theme': theme,
                        'duration': f"{class_duration} minutes",
                        'timestamp': datetime.now(),
                        'recommendations': st.session_state.recommendations
                    })
    
    if st.session_state.recommendations:
        st.markdown(f"### 🎵 Your {class_duration}-Minute Yoga Playlist")
        
        total_duration = 0
        for section, details in st.session_state.recommendations['sections'].items():
            with st.expander(f"🎼 {section} ({details['duration']} | Intensity: {details['section_intensity']})"):
                # Create DataFrame with Spotify information
                display_df = pd.DataFrame([{
                    'name': song.get('verified_name', song['name']),
                    'artist': song.get('verified_artist', song['artist']),
                    'length': song.get('length', 'N/A'),
                    'intensity': song['intensity'],
                    'reason': song['reason'],
                    'spotify': song.get('spotify_url', '#')
                } for song in details['songs']])
                
                st.dataframe(
                    display_df,
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
                        "reason": st.column_config.TextColumn("Why This Song"),
                        "spotify": st.column_config.LinkColumn(
                            "Listen on Spotify",
                            help="Click to open in Spotify",
                            display_text="🎵 Play"
                        )
                    }
                )
                
                # Calculate section duration
                if all('length' in song for song in details['songs']):
                    section_duration = sum(int(song['length'].split(':')[0]) * 60 + 
                                        int(song['length'].split(':')[1]) 
                                        for song in details['songs'])
                    total_duration += section_duration
                    st.caption(f"Section duration: {section_duration//60}:{section_duration%60:02d}")
        
        if total_duration > 0:
            st.success(f"Total Playlist Duration: {total_duration//60} minutes {total_duration%60} seconds")
        
        col3, col4 = st.columns(2)
        with col3:
            st.download_button(
                "💾 Download Playlist",
                data=json.dumps(st.session_state.recommendations, indent=4),
                file_name=f"yoga_playlist_{theme}_{class_duration}min_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json",
                use_container_width=True
            )

if __name__ == "__main__":
    main()
