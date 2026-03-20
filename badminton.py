import streamlit as st
import pandas as pd
import json
import random
import io
from collections import defaultdict
import hashlib
import base64
from datetime import datetime, timedelta
import os
from pathlib import Path
from dotenv import load_dotenv

import db
import fixtures as fixt
import player_stats as pstats

# Load environment variables
load_dotenv()

# Skill level and subgroup defaults
SKILL_LEVEL_MIN = 0
SKILL_LEVEL_MAX = 15
DEFAULT_SUBGROUP_NAMES = {'subgroup1': 'Deciders (0-5)', 'subgroup2': 'Chokers (6-15)'}
DEFAULT_DECIDERS_MIN, DEFAULT_DECIDERS_MAX = 0, 5   # subgroup1 (lower skills)
DEFAULT_CHOKERS_MIN, DEFAULT_CHOKERS_MAX = 6, 15   # subgroup2 (higher skills)

# Funky default group names with bracketed group letter (A–F)
DEFAULT_GROUP_NAMES = {
    "Group A": "Thunder Shuttles (A)",
    "Group B": "Phoenix Feathers (B)",
    "Group C": "Vortex Smashers (C)",
    "Group D": "Shadow Drops (D)",
    "Group E": "Lightning Rackets (E)",
    "Group F": "Cyclone Squad (F)",
}

# Page Configuration (mobile-first: collapsed sidebar on load; layout wide for desktop)
st.set_page_config(
    page_title="Amdocs Badminton Premier League",
    page_icon="🏸",
    layout="wide",
    initial_sidebar_state="auto",
)

# Amdocs + Premier League Canada theme (brand red ~#ED1C24, royal blue, gold, lime accents)
def _inject_custom_css():
    st.markdown(
        """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700;800&display=swap" rel="stylesheet">
    <style>
    :root {
        --amdocs-red: #ED1C24;
        --amdocs-red-dark: #c4161d;
        --royal-blue: #1e3a8a;
        --royal-blue-light: #3b82f6;
        --gold: #ca8a04;
        --gold-soft: #fef9c3;
        --lime: #65a30d;
        --navy-deep: #0c1222;
        --navy-mid: #1e1b4b;
    }
    /* ========== MOBILE FIRST ========== */
    .stApp {
        background: linear-gradient(180deg, #ffffff 0%, #f4f7fb 50%, #eef2f9 100%) !important;
        font-family: 'Montserrat', 'Segoe UI', system-ui, sans-serif !important;
    }
    .main .block-container {
        padding: 0.5rem 0.65rem 1.25rem !important;
        max-width: 100% !important;
        background: transparent !important;
    }
    /* Hero banner: mobile-first — cap height so layout stays usable on phones */
    .amdocs-hero-wrap {
        width: 100%;
        max-width: 100%;
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 0 0 0.15rem;
        box-sizing: border-box;
        margin: 0 auto;
    }
    .amdocs-hero-wrap img {
        display: block;
        width: auto;
        height: auto;
        max-width: 100%;
        max-height: clamp(56px, 14svh, 100px);
        object-fit: contain;
        object-position: center;
        border-radius: 6px;
    }
    @media (min-width: 480px) {
        .amdocs-hero-wrap img {
            max-height: clamp(72px, 16svh, 128px);
            max-width: min(100%, 520px);
        }
    }
    @media (min-width: 768px) {
        .main .block-container { padding-top: 0.75rem !important; }
        .amdocs-hero-wrap img {
            max-height: clamp(88px, 18svh, 160px);
            max-width: min(100%, 680px);
        }
    }
    @media (min-width: 1024px) {
        .amdocs-hero-wrap img {
            max-height: clamp(100px, 20svh, 200px);
            max-width: min(100%, 820px);
        }
    }
    .amdocs-hero-fallback {
        text-align: center;
        padding: 0.5rem 0.6rem;
        margin: 0 auto;
        max-width: 100%;
        background: linear-gradient(90deg, #1e3a8a, #ED1C24);
        border-radius: 8px;
        color: white;
        font-family: 'Montserrat', sans-serif;
        font-size: clamp(0.7rem, 3.2vw, 1rem);
        font-weight: 700;
        line-height: 1.3;
    }
    .stButton > button { min-height: 44px !important; padding: 0.5rem 1rem !important; font-family: 'Montserrat', sans-serif !important; }
    .stTextInput input, .stNumberInput input { min-height: 44px !important; font-size: 16px !important; }
    [data-testid="stRadio"] label { min-height: 44px !important; padding: 0.5rem 0 !important; display: flex !important; align-items: center !important; }
    h1 { font-size: 1.5rem !important; margin-bottom: 0.25rem !important; line-height: 1.3 !important; font-family: 'Montserrat', sans-serif !important; font-weight: 800 !important; color: var(--royal-blue) !important; }
    h2 { font-size: 1.2rem !important; margin-top: 1rem !important; padding-bottom: 0.35rem !important; font-family: 'Montserrat', sans-serif !important; font-weight: 700 !important; color: var(--navy-deep) !important; border-bottom: 2px solid var(--gold) !important; }
    h3 { font-size: 1.05rem !important; font-family: 'Montserrat', sans-serif !important; font-weight: 600 !important; color: var(--royal-blue) !important; }
    @media (max-width: 768px) {
        .main [data-testid="column"] { width: 100% !important; min-width: 100% !important; }
        .stTabs [data-baseweb="tab-list"] { flex-wrap: wrap !important; gap: 4px !important; }
        .stTabs [data-baseweb="tab"] { padding: 0.5rem 0.75rem !important; font-size: 0.85rem !important; }
        [data-testid="stMetric"] { padding: 0.75rem 1rem !important; }
        [data-testid="stDataFrame"] { overflow-x: auto !important; -webkit-overflow-scrolling: touch !important; }
    }
    .main p, .main span, .main label { color: #1e293b !important; font-family: 'Montserrat', sans-serif !important; }
    /* Sidebar — navy + Amdocs red accent */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--navy-mid) 0%, var(--navy-deep) 100%) !important;
        border-right: 4px solid var(--amdocs-red) !important;
    }
    [data-testid="stSidebar"] .stMarkdown { color: #f8fafc !important; }
    [data-testid="stSidebar"] .stMarkdown strong { color: #fef08a !important; }
    [data-testid="stSidebar"] label { color: #e2e8f0 !important; }
    [data-testid="stSidebar"] .stRadio label { color: #f1f5f9 !important; font-weight: 500 !important; min-height: 44px !important; padding: 0.5rem 0 !important; }
    [data-testid="stSidebar"] p { color: #e2e8f0 !important; }
    [data-testid="stSidebar"] hr { border-color: rgba(237, 28, 36, 0.35) !important; }
    [data-testid="stSidebar"] span { color: #e2e8f0 !important; }
    [data-testid="stSidebar"] div[data-testid="stRadio"] label { color: #f8fafc !important; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #ffffff !important; }
    [data-testid="stSidebar"] .stButton > button { min-height: 44px !important; }
    /* Primary = Amdocs red */
    .stButton > button[kind="primary"] {
        background: linear-gradient(180deg, var(--amdocs-red) 0%, var(--amdocs-red-dark) 100%) !important;
        color: white !important; border: none !important; box-shadow: 0 2px 8px rgba(237, 28, 36, 0.35) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: var(--amdocs-red-dark) !important; color: white !important;
    }
    .stButton > button {
        border-radius: 10px !important; font-weight: 600 !important;
        border: 1px solid #cbd5e1 !important; color: var(--navy-deep) !important; background-color: #fff !important;
    }
    .stButton > button:hover { background-color: var(--gold-soft) !important; border-color: var(--gold) !important; }
    /* Metrics — card with blue accent */
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%) !important;
        padding: 1rem 1.25rem !important; border-radius: 12px !important;
        box-shadow: 0 2px 12px rgba(30, 58, 138, 0.08) !important;
        border: 1px solid rgba(30, 58, 138, 0.15) !important;
    }
    [data-testid="stMetricValue"] { font-weight: 800 !important; color: var(--royal-blue-light) !important; }
    [data-testid="stMetricLabel"] { color: #64748b !important; font-weight: 600 !important; }
    .stTextInput > div > div input, .stNumberInput input { border-radius: 8px !important; border-color: #cbd5e1 !important; }
    [data-testid="stSelectbox"] label, .main [data-testid="stRadio"] label { color: #1e293b !important; }
    .streamlit-expanderHeader {
        border-radius: 8px !important; background: linear-gradient(90deg, #f1f5f9 0%, #fff 100%) !important;
        border-left: 4px solid var(--amdocs-red) !important; padding: 0.75rem 1rem !important; min-height: 44px !important;
    }
    div[data-baseweb="notification"][kind="info"] { background-color: #eff6ff !important; border-left: 4px solid var(--royal-blue-light) !important; }
    div[data-baseweb="notification"][kind="success"] { background-color: #ecfccb !important; border-left: 4px solid var(--lime) !important; }
    div[data-baseweb="notification"][kind="warning"] { background-color: var(--gold-soft) !important; border-left: 4px solid var(--gold) !important; }
    .stDataFrame { border-radius: 10px !important; overflow: auto !important; box-shadow: 0 2px 8px rgba(30, 58, 138, 0.06) !important; border: 1px solid #e2e8f0 !important; }
    .stTabs [data-baseweb="tab-list"] { background-color: #e0e7ff !important; border-radius: 10px !important; padding: 4px !important; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px !important; font-weight: 600 !important; }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(180deg, var(--amdocs-red) 0%, var(--amdocs-red-dark) 100%) !important;
        color: white !important;
    }
    @media (min-width: 640px) {
        .main .block-container { padding: 1.25rem 1rem 2.5rem !important; }
        h1 { font-size: 1.65rem !important; }
        h2 { font-size: 1.25rem !important; }
    }
    @media (min-width: 768px) {
        .main .block-container { padding: 1.5rem 1.5rem 3rem !important; max-width: 100% !important; }
        h1 { font-size: 1.85rem !important; }
        h2 { font-size: 1.35rem !important; margin-top: 1.5rem !important; }
    }
    @media (min-width: 1024px) {
        .main .block-container { max-width: 1400px !important; margin-left: auto !important; margin-right: auto !important; padding-top: 2rem !important; padding-bottom: 3rem !important; }
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


def _render_amdocs_header():
    """Show Premier League banner from assets/ if present (mobile-first sizing via .amdocs-hero-wrap)."""
    banner = Path(__file__).resolve().parent / "assets" / "amdocs_banner.png"
    if banner.is_file():
        try:
            b64 = base64.standard_b64encode(banner.read_bytes()).decode("ascii")
            st.markdown(
                f'<div class="amdocs-hero-wrap"><img src="data:image/png;base64,{b64}" alt="Amdocs Badminton Premier League" loading="lazy" /></div>',
                unsafe_allow_html=True,
            )
        except OSError:
            st.image(str(banner), width=280)
    else:
        st.markdown(
            '<div class="amdocs-hero-fallback">Amdocs Badminton Premier League 2026 · Canada</div>',
            unsafe_allow_html=True,
        )
    st.caption("Shuttles fly, spirits rise — balanced teams, fixtures, standings & leaderboard.")


_inject_custom_css()

# User Management System
def hash_password(password):
    """Hash password using SHA-256 with salt"""
    salt = "badminton_tournament_salt_2024"
    return hashlib.sha256((password + salt).encode()).hexdigest()

def verify_password(stored_password, provided_password):
    """Verify a stored password against provided password"""
    return stored_password == hash_password(provided_password)

def initialize_users():
    """Initialize default users if not exists"""
    if 'users' not in st.session_state:
        st.session_state.users = {}
    
    # Always ensure the default superuser exists (in case it was deleted)
    if 'ritesha' not in st.session_state.users:
        # Superuser password must come from Streamlit secrets only (not .env)
        superuser_password = None
        try:
            superuser_password = st.secrets["SUPERUSER_PASSWORD"]
        except (KeyError, FileNotFoundError, TypeError):
            pass

        if not superuser_password or not str(superuser_password).strip():
            st.error(
                "⚠️ **SUPERUSER_PASSWORD** is not set. Add it to **`.streamlit/secrets.toml`** "
                "(local) or **Streamlit Cloud → App → Settings → Secrets** (deployed). "
                "Do not use `.env` for this value."
            )
            st.stop()
            
        st.session_state.users['ritesha'] = {
            'password_hash': hash_password(superuser_password),
            'role': 'superuser',
            'created_by': 'system',
            'created_at': datetime.now().isoformat()
        }

def get_user_role(username):
    """Get user role, return None if user doesn't exist"""
    if username in st.session_state.users:
        return st.session_state.users[username]['role']
    return None

def is_authenticated():
    """Check if user is authenticated"""
    return st.session_state.get('authenticated', False)

def get_current_user():
    """Get current logged in user"""
    return st.session_state.get('current_user', None)

def get_current_user_role():
    """Get current user's role"""
    user = get_current_user()
    return get_user_role(user) if user else None

def can_access_page(page_name):
    """Check if current user can access a specific page"""
    # Public pages - accessible to everyone (including guests)
    public_pages = ['Team Details', 'Standings & Qualifiers', 'Fixtures & Results', 'Leaderboard']
    
    if page_name in public_pages:
        return True
    
    # Protected pages require authentication
    if not is_authenticated():
        return False
    
    user_role = get_current_user_role()
    
    # Superuser can access everything
    if user_role == 'superuser':
        return True
    
    # Admin can access clash recording
    if user_role == 'admin' and page_name == 'Record a Clash':
        return True
    
    # Other protected pages require superuser
    return False

def logout():
    """Logout current user"""
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.rerun()

def login_page():
    """Display login page"""
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        st.markdown("<h2 style='text-align:center; margin-top:2rem;'>🔐 Sign in</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#64748b; margin-bottom:1.5rem;'>Use your credentials to access full features.</p>", unsafe_allow_html=True)
        with st.form('login_form'):
            username = st.text_input('Username', placeholder='Enter username')
            password = st.text_input('Password', type='password', placeholder='Enter password')
            login_button = st.form_submit_button('Login', type='primary')
            if login_button:
                if username in st.session_state.users:
                    if verify_password(st.session_state.users[username]['password_hash'], (password or "").strip()):
                        st.session_state.authenticated = True
                        st.session_state.current_user = username
                        st.success(f'Welcome back, {username}!')
                        st.rerun()
                    else:
                        st.error('Invalid password')
                else:
                    st.error('User not found')
        st.markdown("---")
        st.caption("You can view Team Details (no skill levels), Standings, Fixtures & Results, and Leaderboard without logging in.")
        if st.button('🌐 Continue as Guest', use_container_width=True):
            st.session_state.public_access = True
            st.rerun()

# Data persistence functions
def save_tournament_data():
    """Save tournament data to the database. Returns True on success, False on error."""
    try:
        player_db = st.session_state.get('player_database', pd.DataFrame())
        standings = st.session_state.get('standings', pd.DataFrame())
        if standings.empty and 'standings' in st.session_state:
            standings = st.session_state.standings
        db.save_tournament_data(
            player_database=player_db,
            group_names=st.session_state.get('group_names', {}),
            subgroup_names=st.session_state.get('subgroup_names', {}),
            groups=st.session_state.get('groups', {}),
            detailed_groups=st.session_state.get('detailed_groups', {}),
            standings=standings,
            tournament_data=st.session_state.get('tournament_data', {}),
            users=st.session_state.get('users', {}),
            clash_edit_history=st.session_state.get('clash_edit_history', []),
        )
        return True
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")
        return False

def _apply_data_to_session(data):
    """Apply loaded or default data dict to session_state."""
    st.session_state.player_database = data['player_database']
    st.session_state.group_names = data['group_names']
    st.session_state.subgroup_names = data.get('subgroup_names', DEFAULT_SUBGROUP_NAMES.copy())
    st.session_state.groups = data['groups']
    st.session_state.detailed_groups = data.get('detailed_groups', {})
    st.session_state.standings = data['standings']
    st.session_state.tournament_data = data.get('tournament_data', {})
    st.session_state.clash_edit_history = data.get('clash_edit_history', [])
    st.session_state.clashes = data.get('clashes', [])
    saved_users = data.get('users', {})
    st.session_state.users = saved_users if saved_users else {}

def load_tournament_data():
    """Load tournament data from the database"""
    try:
        data = db.load_tournament_data()
        _apply_data_to_session(data)
        # Ensure subgroup names default if missing
        if not st.session_state.subgroup_names:
            st.session_state.subgroup_names = DEFAULT_SUBGROUP_NAMES.copy()
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        # Ensure session_state has required keys so the app doesn't crash
        _apply_data_to_session(db.get_default_state())

# Auto-save functionality
def auto_save():
    """Auto-save tournament data"""
    save_tournament_data()


def _push_full_state_to_supabase() -> tuple:
    """
    Persist entire session state to Supabase (same payload as auto_save).
    Returns (success: bool, detail: str | None).
    - (True, None) — saved to Supabase
    - (True, "local_only") — no Supabase URL/key in env or Streamlit secrets; session only
    - (False, error_message) — Supabase configured but save failed
    """
    url, key = db.get_supabase_credentials()
    if not url or not key:
        return True, "local_only"
    try:
        db.save_tournament_data(
            player_database=st.session_state.get("player_database", pd.DataFrame()),
            group_names=st.session_state.get("group_names", {}),
            subgroup_names=st.session_state.get("subgroup_names", {}),
            groups=st.session_state.get("groups", {}),
            detailed_groups=st.session_state.get("detailed_groups", {}),
            standings=st.session_state.get("standings", pd.DataFrame()),
            tournament_data=st.session_state.get("tournament_data", {}),
            users=st.session_state.get("users", {}),
            clash_edit_history=st.session_state.get("clash_edit_history", []),
        )
        return True, None
    except Exception as e:
        return False, str(e)

def generate_round_robin_schedule(groups, dates, start_time, end_time, num_courts, match_duration, break_duration):
    """
    Generate proper round-robin schedule where all groups play simultaneously in each round
    """
    from datetime import datetime, timedelta
    
    # Ensure we have at least 2 groups
    if len(groups) < 2:
        return []
    
    # Generate proper round-robin pairings
    def generate_round_robin_pairings(teams):
        """Generate round-robin pairings where each team plays every other team exactly once"""
        n = len(teams)
        if n % 2 == 1:
            teams = teams + ['BYE']  # Add dummy team for odd numbers
            n += 1
        
        rounds = []
        
        # Generate n-1 rounds for n teams
        for round_num in range(n - 1):
            round_pairings = []
            
            # Generate pairings for this round
            for i in range(n // 2):
                team1_idx = i
                team2_idx = n - 1 - i
                
                team1 = teams[team1_idx]
                team2 = teams[team2_idx]
                
                # Skip if either team is BYE
                if team1 != 'BYE' and team2 != 'BYE':
                    round_pairings.append((team1, team2))
            
            rounds.append(round_pairings)
            
            # Rotate teams for next round (keep first fixed, rotate rest)
            teams = [teams[0]] + [teams[-1]] + teams[1:-1]
        
        return rounds
    
    # Generate round-robin rounds
    tournament_rounds = generate_round_robin_pairings(groups.copy())
    
    # Calculate timing
    start_dt = datetime.strptime(start_time.strftime('%H:%M'), '%H:%M')
    end_dt = datetime.strptime(end_time.strftime('%H:%M'), '%H:%M')
    daily_minutes = int((end_dt - start_dt).total_seconds() / 60)
    
    slot_duration = match_duration + break_duration
    
    schedule = []
    current_date_idx = 0
    current_time_slot = 0
    
    for round_idx, round_pairings in enumerate(tournament_rounds):
        # Calculate start time for this round
        round_start_minutes = current_time_slot * slot_duration
        round_start_dt = start_dt + timedelta(minutes=round_start_minutes)
        
        # Check if we need to move to next day
        if round_start_minutes + slot_duration > daily_minutes:
            current_date_idx = (current_date_idx + 1) % len(dates)
            current_time_slot = 0
            round_start_minutes = 0
            round_start_dt = start_dt
        
        # Schedule all matches in this round
        court_assignments = {}  # Track which courts are used at which times
        
        for clash_idx, (group1, group2) in enumerate(round_pairings):
            # One row per meeting (Record a Clash covers all 5 games in one pairing)
            time_slot_key = f"{current_date_idx}_{current_time_slot}"
            if time_slot_key not in court_assignments:
                court_assignments[time_slot_key] = []
            court_num = len(court_assignments[time_slot_key]) + 1
            if court_num <= num_courts:
                match_start_time = round_start_dt
                court_assignments[time_slot_key].append(court_num)
            else:
                current_time_slot += 1
                if (current_time_slot * slot_duration) + slot_duration > daily_minutes:
                    current_date_idx = (current_date_idx + 1) % len(dates)
                    current_time_slot = 0
                match_start_time = start_dt + timedelta(minutes=current_time_slot * slot_duration)
                court_num = 1
                new_time_slot_key = f"{current_date_idx}_{current_time_slot}"
                court_assignments[new_time_slot_key] = [1]
            meeting_mins = 5 * match_duration + 4 * break_duration
            match_end_time = match_start_time + timedelta(minutes=meeting_mins)
            schedule.append({
                'date': dates[current_date_idx].strftime('%Y-%m-%d'),
                'round_number': round_idx + 1,
                'clash_number': clash_idx + 1,
                'court': f'Court {court_num}',
                'start_time': match_start_time.strftime('%H:%M'),
                'end_time': match_end_time.strftime('%H:%M'),
                'group1': group1,
                'group2': group2,
                'status': 'Scheduled',
                'format': '5 games (3 Deciders, 2 Chokers)',
            })
        
        # Move to next time slot for next round
        current_time_slot += 1
    
    return schedule

# Initialize State for Data Persistence
if 'initialized' not in st.session_state:
    # Load existing data first (including users)
    load_tournament_data()
    
    # Ensure required keys exist (e.g. if load failed without applying defaults)
    if 'groups' not in st.session_state:
        _apply_data_to_session(db.get_default_state())
    if 'subgroup_names' not in st.session_state or not st.session_state.subgroup_names:
        st.session_state.subgroup_names = DEFAULT_SUBGROUP_NAMES.copy()
    
    # Then initialize user system (will only add missing default users)
    initialize_users()
    
    # Ensure groups are populated from player database if they exist
    if not any(st.session_state.groups.values()) and not st.session_state.player_database.empty:
        assigned_players = st.session_state.player_database[st.session_state.player_database['assigned'] == True]
        for _, player in assigned_players.iterrows():
            if player['group'] in st.session_state.groups:
                if player['name'] not in st.session_state.groups[player['group']]:
                    st.session_state.groups[player['group']].append(player['name'])
    
    # Initialize tournament data if not exists
    if 'tournament_data' not in st.session_state:
        st.session_state.tournament_data = {}
    
    # Initialize edit history if not exists
    if 'clash_edit_history' not in st.session_state:
        st.session_state.clash_edit_history = []
    
    # Display option: show skill level in group/team views (default True)
    if 'show_skill_in_groups' not in st.session_state:
        st.session_state.show_skill_in_groups = True
    
    # Lock teams: when True, Create/Reshuffle are disabled
    if 'teams_locked' not in st.session_state:
        st.session_state.teams_locked = False
    
    st.session_state.initialized = True

# Hero: Amdocs Premier League banner + tagline
_render_amdocs_header()

# Check authentication and show login if needed
if not is_authenticated() and not st.session_state.get('public_access', False):
    login_page()
    st.stop()

# Build navigation menu based on user permissions
available_pages = []
all_pages = ["Player Import & Auto-Balance", "Setup Groups & Players", "Team Details", 
            "Match Schedule", "Fixtures & Results", "Standings & Qualifiers", "Leaderboard", "Record a Clash", "Manage Players", "User Management"]

for page in all_pages:
    if can_access_page(page):
        available_pages.append(page)

# Sidebar: user and nav
st.sidebar.markdown("### 🏸 **Tournament**")
st.sidebar.markdown("---")
if is_authenticated():
    current_user = get_current_user()
    user_role = get_current_user_role()
    st.sidebar.success(f'👤 Logged in as: **{current_user}** ({user_role})')
    if st.sidebar.button('🚪 Logout'):
        logout()
else:
    st.sidebar.info('👁️ **Guest Access** - Limited features available')
    if st.sidebar.button('🔐 Login'):
        st.session_state.public_access = False
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("**💾 Data**")
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("💾 Save", help="Save all tournament data", use_container_width=True):
        save_tournament_data()
        st.sidebar.success("Saved!")
with col2:
    if st.button("📂 Load", help="Load saved data", use_container_width=True):
        load_tournament_data()
        st.sidebar.success("Loaded!")
        st.rerun()

if st.sidebar.button("📤 Export CSV", help="Download players as CSV", use_container_width=True):
    csv_data = st.session_state.player_database.to_csv(index=False)
    st.sidebar.download_button(
        label="⬇️ Download",
        data=csv_data,
        file_name=f"tournament_players_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True
    )

st.sidebar.markdown("---")
st.sidebar.markdown("**📑 Navigate**")
menu = st.sidebar.radio("Choose a page", available_pages, label_visibility="collapsed")

# Auto-balancing algorithm
def auto_balance_groups(players_df, min_females_per_group=None, max_females_per_group=None):
    """
    Auto-balance players into 6 groups with optimized skill and gender distribution
    Uses iterative optimization to minimize skill variance between groups
    
    Args:
        players_df: DataFrame containing player data
        min_females_per_group: Minimum number of females per group (optional)
        max_females_per_group: Maximum number of females per group (optional)
    """
    import itertools
    
    # Separate male and female players
    male_players = players_df[players_df['gender'] == 'M'].copy()
    female_players = players_df[players_df['gender'] == 'F'].copy()
    
    # Sort by skill level (descending)
    male_players = male_players.sort_values('skill_level', ascending=False).reset_index(drop=True)
    female_players = female_players.sort_values('skill_level', ascending=False).reset_index(drop=True)
    
    # Initialize groups using configured custom names
    group_keys = [f"Group {chr(65+i)}" for i in range(6)]  # Default keys
    if 'group_names' in st.session_state:
        # Use the display names from configuration
        groups = {key: {'players': [], 'total_skill': 0, 'male_count': 0, 'female_count': 0} for key in group_keys}
    else:
        groups = {f"Group {chr(65+i)}": {'players': [], 'total_skill': 0, 'male_count': 0, 'female_count': 0} for i in range(6)}
        group_keys = list(groups.keys())
    
    # Step 1: Distribute females using user-defined constraints or default even distribution
    total_females = len(female_players)
    
    if min_females_per_group is not None and max_females_per_group is not None:
        # Validate constraints
        if min_females_per_group * 6 > total_females:
            raise ValueError(f"Not enough female players: need at least {min_females_per_group * 6}, have {total_females}")
        if max_females_per_group * 6 < total_females:
            raise ValueError(f"Too many female players for constraints: max capacity {max_females_per_group * 6}, have {total_females}")
        
        # Create optimized distribution within constraints
        female_distribution = [min_females_per_group] * 6
        remaining_females = total_females - (min_females_per_group * 6)
        
        # Distribute remaining females respecting max constraints
        for i in range(6):
            if remaining_females > 0 and female_distribution[i] < max_females_per_group:
                add_count = min(remaining_females, max_females_per_group - female_distribution[i])
                female_distribution[i] += add_count
                remaining_females -= add_count
    else:
        # Default: distribute females evenly
        female_count_per_group = total_females // 6
        female_remainder = total_females % 6
        
        female_distribution = []
        for i in range(6):
            group_females = female_count_per_group + (1 if i < female_remainder else 0)
            female_distribution.append(group_females)
    
    # Assign females using skill balancing
    female_idx = 0
    while female_idx < len(female_players):
        player = female_players.iloc[female_idx]
        candidates = [(i, groups[group_keys[i]]['total_skill']) for i in range(6) if female_distribution[i] > 0]
        if not candidates:
            break
        candidates.sort(key=lambda x: x[1])
        group_idx = candidates[0][0]
        groups[group_keys[group_idx]]['players'].append(player)
        groups[group_keys[group_idx]]['total_skill'] += player['skill_level']
        groups[group_keys[group_idx]]['female_count'] += 1
        female_distribution[group_idx] -= 1
        female_idx += 1
    
    # Step 2: Distribute males using skill-based optimization
    remaining_spots = [10 - len(groups[key]['players']) for key in group_keys]
    male_idx = 0
    while male_idx < len(male_players):
        player = male_players.iloc[male_idx]
        available_groups = [(i, groups[group_keys[i]]['total_skill']) for i in range(6) if remaining_spots[i] > 0]
        if not available_groups:
            break
        available_groups.sort(key=lambda x: x[1])
        target_group_idx = available_groups[0][0]
        groups[group_keys[target_group_idx]]['players'].append(player)
        groups[group_keys[target_group_idx]]['total_skill'] += player['skill_level']
        groups[group_keys[target_group_idx]]['male_count'] += 1
        remaining_spots[target_group_idx] -= 1
        male_idx += 1
    
    # Step 3: Simple redistribution for guaranteed 1-point difference
    def redistribute_for_perfect_balance():
        """Simple algorithm to achieve exactly 1-point max difference"""
        # Use the tested working algorithm
        for iteration in range(100):  # Limit iterations
            # Get current group totals
            totals = [groups[key]['total_skill'] for key in group_keys]
            max_total = max(totals)
            min_total = min(totals)
            
            # If balanced within 1 point, we're done
            if max_total - min_total <= 1:
                break
            
            # Find highest and lowest groups
            max_idx = totals.index(max_total)
            min_idx = totals.index(min_total)
            
            max_group = groups[group_keys[max_idx]]
            min_group = groups[group_keys[min_idx]]
            
            # Find best player swap
            best_swap = None
            best_improvement = 0
            
            for i, max_player in enumerate(max_group['players']):
                for j, min_player in enumerate(min_group['players']):
                    # Only swap same gender
                    if max_player['gender'] != min_player['gender']:
                        continue
                    
                    # Calculate skill difference
                    skill_diff = max_player['skill_level'] - min_player['skill_level']
                    
                    # Only swap if it reduces the gap
                    if skill_diff <= 0:
                        continue
                    
                    # Calculate new totals after swap
                    new_max_total = max_total - skill_diff
                    new_min_total = min_total + skill_diff
                    new_diff = abs(new_max_total - new_min_total)
                    
                    # If this improves balance, consider it
                    improvement = (max_total - min_total) - new_diff
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_swap = (i, j, max_player, min_player, skill_diff)
            
            # Make the best swap
            if best_swap:
                i, j, max_player, min_player, skill_diff = best_swap
                # Swap players
                max_group['players'][i] = min_player
                min_group['players'][j] = max_player
                # Update totals
                max_group['total_skill'] -= skill_diff
                min_group['total_skill'] += skill_diff
            else:
                break  # No beneficial swap found
    
    # Execute the redistribution
    redistribute_for_perfect_balance()
    
    # Convert to the expected format
    result_groups = {}
    for group_name, group_data in groups.items():
        result_groups[group_name] = group_data['players']
    
    return result_groups


def auto_balance_subgroups(players_df, subgroup1_min, subgroup1_max, subgroup2_min, subgroup2_max, subgroup1_count, subgroup2_count, num_groups=6, min_females_per_group=None, max_females_per_group=None):
    """
    Auto-balance players into specified number of groups with 2 skill-based subgroups each
    Ensures skill point balance at group level, subgroup 1 level, and subgroup 2 level
    
    Args:
        min_females_per_group: Minimum number of females per group (optional)
        max_females_per_group: Maximum number of females per group (optional)
    """
    import itertools
    import random
    
    # Filter players based on skill level ranges
    subgroup1_players = players_df[
        (players_df['skill_level'] >= subgroup1_min) & 
        (players_df['skill_level'] <= subgroup1_max)
    ].copy()
    
    subgroup2_players = players_df[
        (players_df['skill_level'] >= subgroup2_min) & 
        (players_df['skill_level'] <= subgroup2_max)
    ].copy()
    
    # Check if we have enough players
    needed_sg1 = subgroup1_count * num_groups
    needed_sg2 = subgroup2_count * num_groups
    
    if len(subgroup1_players) < needed_sg1:
        raise ValueError(f"Not enough players for Subgroup 1. Need {needed_sg1}, have {len(subgroup1_players)}")
    if len(subgroup2_players) < needed_sg2:
        raise ValueError(f"Not enough players for Subgroup 2. Need {needed_sg2}, have {len(subgroup2_players)}")
    
    # Validate gender constraints if specified
    if min_females_per_group is not None and max_females_per_group is not None:
        total_females_sg1 = len(subgroup1_players[subgroup1_players['gender'] == 'F'])
        total_females_sg2 = len(subgroup2_players[subgroup2_players['gender'] == 'F'])
        total_females = total_females_sg1 + total_females_sg2
        
        if min_females_per_group * num_groups > total_females:
            raise ValueError(f"Not enough female players: need at least {min_females_per_group * num_groups}, have {total_females}")
        if max_females_per_group * num_groups < total_females:
            raise ValueError(f"Too many female players for constraints: max capacity {max_females_per_group * num_groups}, have {total_females}")
    
    # Select players for each subgroup (take all available if we have more than needed)
    if len(subgroup1_players) > needed_sg1:
        subgroup1_selected = subgroup1_players.nlargest(needed_sg1, 'skill_level').reset_index(drop=True)
    else:
        subgroup1_selected = subgroup1_players.reset_index(drop=True)
        
    if len(subgroup2_players) > needed_sg2:
        subgroup2_selected = subgroup2_players.nlargest(needed_sg2, 'skill_level').reset_index(drop=True)
    else:
        subgroup2_selected = subgroup2_players.reset_index(drop=True)
    
    # Initialize groups dynamically using default keys
    groups = {}
    for i in range(num_groups):
        group_name = f"Group {chr(65+i)}"  # Use default keys internally
        groups[group_name] = {
            'subgroup1': {'players': [], 'total_skill': 0, 'male_count': 0, 'female_count': 0},
            'subgroup2': {'players': [], 'total_skill': 0, 'male_count': 0, 'female_count': 0}
        }
    
    group_keys = list(groups.keys())
    
    def balance_players_by_skill(players_list, subgroup_type, target_count_per_group):
        """Balance players across all groups to minimize skill variance while respecting gender constraints"""
        if len(players_list) == 0:
            return
        
        initial_assignments = None

        # Separate by gender first if constraints are specified
        if min_females_per_group is not None and max_females_per_group is not None:
            # If pair was extracted, pre-fill group 0 so we don't overfill it
            if initial_assignments is not None:
                for p in initial_assignments[0]:
                    groups[group_keys[0]][subgroup_type]['players'].append(p)
                    groups[group_keys[0]][subgroup_type]['total_skill'] += p['skill_level']
                    if p.get('gender') == 'M':
                        groups[group_keys[0]][subgroup_type]['male_count'] += 1
                    else:
                        groups[group_keys[0]][subgroup_type]['female_count'] += 1
                need_per_group = [target_count_per_group - len(initial_assignments[0])] + [target_count_per_group] * (num_groups - 1)
            else:
                need_per_group = None
            male_players = players_list[players_list['gender'] == 'M'].sort_values('skill_level', ascending=False).reset_index(drop=True)
            female_players = players_list[players_list['gender'] == 'F'].sort_values('skill_level', ascending=False).reset_index(drop=True)
            distribute_with_gender_constraints(female_players, male_players, subgroup_type, target_count_per_group, need_per_group=need_per_group)
        else:
            distribute_by_skill_only(players_list, subgroup_type, target_count_per_group, initial_assignments)
    
    def distribute_with_gender_constraints(female_players, male_players, subgroup_type, target_count_per_group, need_per_group=None):
        """Distribute players respecting gender constraints. need_per_group: optional list of max additional players per group (when e.g. pair pre-filled)."""
        if need_per_group is None:
            need_per_group = [target_count_per_group] * num_groups
        total_females = len(female_players)
        
        # Female distribution: at least min per group, cap by need_per_group and max_females_per_group
        female_distribution = [min(min_females_per_group, need_per_group[i]) for i in range(num_groups)]
        remaining_females = total_females - sum(female_distribution)
        if remaining_females < 0:
            # Scale down so sum = total_females while keeping each <= need_per_group
            for i in range(num_groups):
                if remaining_females >= 0:
                    break
                reduce_by = min(-remaining_females, female_distribution[i])
                female_distribution[i] -= reduce_by
                remaining_females += reduce_by
        
        # Distribute remaining females respecting max and need_per_group
        for i in range(num_groups):
            if remaining_females > 0 and female_distribution[i] < min(max_females_per_group, need_per_group[i]):
                add_count = min(remaining_females, max_females_per_group - female_distribution[i], need_per_group[i] - female_distribution[i])
                female_distribution[i] += add_count
                remaining_females -= add_count
        
        # Assign females using skill balancing within constraints
        female_idx = 0
        female_records = female_players.to_dict('records')
        while female_idx < len(female_records):
            player = female_records[female_idx]
            candidates = []
            for i in range(num_groups):
                if female_distribution[i] <= 0:
                    continue
                skill_total = groups[group_keys[i]][subgroup_type]['total_skill']
                candidates.append((skill_total, female_distribution[i], i))
            if not candidates:
                candidates = [(groups[group_keys[i]][subgroup_type]['total_skill'], female_distribution[i], i) for i in range(num_groups) if female_distribution[i] > 0]
            if not candidates:
                break
            candidates.sort(key=lambda x: (x[0], -x[1]))
            group_idx = candidates[0][2]
            group_name = group_keys[group_idx]
            groups[group_name][subgroup_type]['players'].append(player)
            groups[group_name][subgroup_type]['total_skill'] += player['skill_level']
            groups[group_name][subgroup_type]['female_count'] += 1
            female_distribution[group_idx] -= 1
            female_idx += 1
        
        # Assign males to fill remaining spots
        male_records = male_players.to_dict('records')
        male_idx = 0
        while male_idx < len(male_records):
            player = male_records[male_idx]
            available_groups = []
            for i in range(num_groups):
                current_count = len(groups[group_keys[i]][subgroup_type]['players'])
                if current_count < target_count_per_group:
                    skill_total = groups[group_keys[i]][subgroup_type]['total_skill']
                    available_groups.append((skill_total, current_count, i))
            if not available_groups:
                available_groups = [(groups[group_keys[i]][subgroup_type]['total_skill'], len(groups[group_keys[i]][subgroup_type]['players']), i) for i in range(num_groups) if len(groups[group_keys[i]][subgroup_type]['players']) < target_count_per_group]
            if not available_groups:
                break
            available_groups.sort(key=lambda x: (x[0], x[1]))
            target_group_idx = available_groups[0][2]
            group_name = group_keys[target_group_idx]
            groups[group_name][subgroup_type]['players'].append(player)
            groups[group_name][subgroup_type]['total_skill'] += player['skill_level']
            groups[group_name][subgroup_type]['male_count'] += 1
            male_idx += 1
    
    def distribute_by_skill_only(players_list, subgroup_type, target_count_per_group, initial_assignments=None):
        """Original skill-only distribution method. initial_assignments: optional list of list of player dicts to pre-fill (e.g. pair in same group)."""
        # Sort players by skill level (descending)
        sorted_players = players_list.sort_values('skill_level', ascending=False).reset_index(drop=True)
        player_records = sorted_players.to_dict('records')
        
        # Initialize group assignments (optional pre-fill per group)
        if initial_assignments is not None:
            group_assignments = [list(init) for init in initial_assignments]
        else:
            group_assignments = [[] for _ in range(num_groups)]

        # Distribute players using a skill-balancing algorithm
        for i, player in enumerate(player_records):
            # Find the group with the lowest current total skill for this subgroup
            group_skills = []
            for j in range(num_groups):
                current_skill = sum(p['skill_level'] for p in group_assignments[j])
                current_count = len(group_assignments[j])
                # Only consider groups that haven't reached their target count
                if current_count < target_count_per_group:
                    group_skills.append((current_skill, j))
            
            if group_skills:
                # Sort by current skill total (ascending) and assign to the group with lowest skill
                group_skills.sort(key=lambda x: x[0])
                target_group_idx = group_skills[0][1]
                group_assignments[target_group_idx].append(player)
        
        # Assign players to groups
        for group_idx, assigned_players in enumerate(group_assignments):
            group_name = group_keys[group_idx]
            for player in assigned_players:
                groups[group_name][subgroup_type]['players'].append(player)
                groups[group_name][subgroup_type]['total_skill'] += player['skill_level']
                if player['gender'] == 'M':
                    groups[group_name][subgroup_type]['male_count'] += 1
                else:
                    groups[group_name][subgroup_type]['female_count'] += 1
        
        # Optimize by swapping players to reduce variance
        optimize_skill_balance(subgroup_type, target_count_per_group)
    
    def optimize_skill_balance(subgroup_type, target_count_per_group):
        """Simple redistribution for subgroups using the proven algorithm"""
        
        for iteration in range(100):  # Limit iterations
            # Get current group totals for this subgroup
            current_skills = [groups[group_key][subgroup_type]['total_skill'] for group_key in group_keys]
            
            if not any(current_skills):
                break
                
            max_skill = max(current_skills)
            min_skill = min(current_skills)
            
            # Success: difference <= 1
            if max_skill - min_skill <= 1:
                break
            
            # Find max and min groups
            max_group_idx = current_skills.index(max_skill)
            min_group_idx = current_skills.index(min_skill)
            
            max_group = groups[group_keys[max_group_idx]][subgroup_type]
            min_group = groups[group_keys[min_group_idx]][subgroup_type]
            
            # Skip if either is empty
            if not max_group['players'] or not min_group['players']:
                break
            
            # Find best player swap using the simple proven algorithm
            best_swap = None
            best_improvement = 0
            
            for i, max_player in enumerate(max_group['players']):
                for j, min_player in enumerate(min_group['players']):
                    # Only swap same gender
                    if max_player['gender'] != min_player['gender']:
                        continue
                    
                    # Calculate skill difference
                    skill_diff = max_player['skill_level'] - min_player['skill_level']
                    
                    # Only swap if it reduces the gap
                    if skill_diff <= 0:
                        continue
                    
                    # Calculate new totals after swap
                    new_max_skill = max_skill - skill_diff
                    new_min_skill = min_skill + skill_diff
                    new_diff = abs(new_max_skill - new_min_skill)
                    
                    # If this improves balance, consider it
                    improvement = (max_skill - min_skill) - new_diff
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_swap = (i, j, max_player, min_player, skill_diff)
            
            # Make the best swap
            if best_swap:
                i, j, max_player, min_player, skill_diff = best_swap
                # Swap players
                max_group['players'][i] = min_player
                min_group['players'][j] = max_player
                # Update totals
                max_group['total_skill'] -= skill_diff
                min_group['total_skill'] += skill_diff
            else:
                break  # No beneficial swap found
    
    # Balance subgroup 1 players
    balance_players_by_skill(subgroup1_selected, 'subgroup1', subgroup1_count)
    
    # Balance subgroup 2 players  
    balance_players_by_skill(subgroup2_selected, 'subgroup2', subgroup2_count)
    
    # Final step: Balance overall combined totals across all groups
    def balance_overall_groups():
        """Balance the combined totals of subgroup1 + subgroup2 across all groups"""
        for iteration in range(100):
            # Calculate combined totals
            combined_totals = []
            for key in group_keys:
                sg1_total = groups[key]['subgroup1']['total_skill']
                sg2_total = groups[key]['subgroup2']['total_skill']
                combined_totals.append(sg1_total + sg2_total)
            
            max_total = max(combined_totals)
            min_total = min(combined_totals)
            
            # If balanced within 1 point, we're done
            if max_total - min_total <= 1:
                break
            
            # Find highest and lowest groups
            max_idx = combined_totals.index(max_total)
            min_idx = combined_totals.index(min_total)
            
            # Try swapping between subgroups of these groups
            best_swap = None
            best_improvement = 0
            
            # Try swaps within subgroup1
            max_sg1 = groups[group_keys[max_idx]]['subgroup1']
            min_sg1 = groups[group_keys[min_idx]]['subgroup1']
            
            for i, max_player in enumerate(max_sg1['players']):
                for j, min_player in enumerate(min_sg1['players']):
                    if max_player['gender'] != min_player['gender']:
                        continue
                    
                    skill_diff = max_player['skill_level'] - min_player['skill_level']
                    if skill_diff <= 0:
                        continue
                    
                    new_max_total = max_total - skill_diff
                    new_min_total = min_total + skill_diff
                    new_diff = abs(new_max_total - new_min_total)
                    
                    improvement = (max_total - min_total) - new_diff
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_swap = ('subgroup1', i, j, max_player, min_player, skill_diff)
            
            # Try swaps within subgroup2
            max_sg2 = groups[group_keys[max_idx]]['subgroup2']
            min_sg2 = groups[group_keys[min_idx]]['subgroup2']
            
            for i, max_player in enumerate(max_sg2['players']):
                for j, min_player in enumerate(min_sg2['players']):
                    if max_player['gender'] != min_player['gender']:
                        continue
                    
                    skill_diff = max_player['skill_level'] - min_player['skill_level']
                    if skill_diff <= 0:
                        continue
                    
                    new_max_total = max_total - skill_diff
                    new_min_total = min_total + skill_diff
                    new_diff = abs(new_max_total - new_min_total)
                    
                    improvement = (max_total - min_total) - new_diff
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_swap = ('subgroup2', i, j, max_player, min_player, skill_diff)
            
            # Execute the best swap
            if best_swap:
                subgroup_type, i, j, max_player, min_player, skill_diff = best_swap
                
                max_subgroup = groups[group_keys[max_idx]][subgroup_type]
                min_subgroup = groups[group_keys[min_idx]][subgroup_type]
                
                # Swap players
                max_subgroup['players'][i] = min_player
                min_subgroup['players'][j] = max_player
                # Update totals
                max_subgroup['total_skill'] -= skill_diff
                min_subgroup['total_skill'] += skill_diff
            else:
                break  # No beneficial swap found
    
    # Apply final overall balancing
    balance_overall_groups()
    
    # Convert to the expected format - combine subgroups into main groups
    result_groups = {}
    for group_name in group_keys:
        all_players = []
        all_players.extend(groups[group_name]['subgroup1']['players'])
        all_players.extend(groups[group_name]['subgroup2']['players'])
        result_groups[group_name] = all_players
    
    return result_groups, groups  # Return both formats for detailed analysis


def calculate_group_stats(group_players):
    """Calculate statistics for a group"""
    if not group_players:
        return {"avg_skill": 0, "male_count": 0, "female_count": 0, "total_skill": 0}
    
    avg_skill = sum(p['skill_level'] for p in group_players) / len(group_players)
    male_count = sum(1 for p in group_players if p['gender'] == 'M')
    female_count = sum(1 for p in group_players if p['gender'] == 'F')
    total_skill = sum(p['skill_level'] for p in group_players)
    
    return {
        "avg_skill": round(avg_skill, 2),
        "male_count": male_count,
        "female_count": female_count,
        "total_skill": total_skill
    }

def calculate_standings():
    """
    Standings: includes Match status (meetings with 1–4 games recorded).
    Sets/rally stats and Points (+2 per game win) update as each game is saved.
    Clash won = count of games (clashes) won — increments as soon as each game is recorded.
    """
    if 'tournament_data' not in st.session_state:
        st.session_state.tournament_data = {}
    groups = st.session_state.groups
    group_names = st.session_state.group_names
    gkeys = [k for k in groups.keys()]

    stats = {}
    for group_key in groups.keys():
        stats[group_key] = {
            'matches_played': 0,
            'clash_won': 0,
            'points': 0,
            'sets_won': 0,
            'sets_lost': 0,
            'points_won': 0,
            'points_lost': 0,
            'match_status': "—",
        }

    td = st.session_state.tournament_data or {}
    pair_best = {}
    for clash_key, matches in td.items():
        if "_vs_" not in clash_key:
            continue
        raw = fixt.coerce_five_match_slots(matches)
        if fixt.count_recorded_games(raw) == 0:
            continue
        g1_key, g2_key = fixt.resolve_clash_group_keys(clash_key, gkeys, group_names)
        if not g1_key or not g2_key or g1_key not in stats or g2_key not in stats:
            continue
        pair = frozenset({g1_key, g2_key})
        cand = (g1_key, g2_key, raw)
        if pair not in pair_best:
            pair_best[pair] = cand
        else:
            _o1, _o2, oldm = pair_best[pair]
            nf, of = fixt.is_clash_fully_recorded(raw), fixt.is_clash_fully_recorded(oldm)
            nc, oc = fixt.count_recorded_games(raw), fixt.count_recorded_games(oldm)
            if nf and not of:
                pair_best[pair] = cand
            elif of and not nf:
                pass
            elif nc > oc:
                pair_best[pair] = cand

    for _pair, (g1_key, g2_key, matches) in pair_best.items():
        # Live update: count every meeting that has at least one recorded game
        stats[g1_key]["matches_played"] += 1
        stats[g2_key]["matches_played"] += 1

        for m in matches:
            if fixt.normalize_match_winner(m) is None:
                continue
            w = fixt.normalize_match_winner(m)
            if w == "g1":
                stats[g1_key]["points"] += 2
                stats[g1_key]["clash_won"] += 1
            elif w == "g2":
                stats[g2_key]["points"] += 2
                stats[g2_key]["clash_won"] += 1
            set_scores = m.get("set_scores") or {}
            for set_name in ("set1", "set2", "set3"):
                s = set_scores.get(set_name)
                if not s or not isinstance(s, (list, tuple)) or len(s) < 2:
                    continue
                try:
                    a = int(s[0]) if s[0] is not None else 0
                    b = int(s[1]) if s[1] is not None else 0
                except (TypeError, ValueError):
                    continue
                stats[g1_key]["sets_won"] += 1 if a > b else 0
                stats[g1_key]["sets_lost"] += 1 if b > a else 0
                stats[g1_key]["points_won"] += a
                stats[g1_key]["points_lost"] += b
                stats[g2_key]["sets_won"] += 1 if b > a else 0
                stats[g2_key]["sets_lost"] += 1 if a > b else 0
                stats[g2_key]["points_won"] += b
                stats[g2_key]["points_lost"] += a

    # Match status: scheduled vs in-progress (completed clashes excluded)
    from itertools import combinations as _comb
    _gks = [k for k in groups.keys() if groups.get(k)]
    for gk in groups.keys():
        n_sched = 0
        n_ip = 0
        for ga, gb in _comb(sorted(_gks, key=str), 2):
            if gk not in (ga, gb):
                continue
            ck = fixt.canonical_clash_key(ga, gb)
            td = st.session_state.tournament_data or {}
            alt = fixt.find_clash_key(ga, gb, td)
            if alt:
                ck = alt
            mfive = fixt.coerce_five_match_slots(td.get(ck, []))
            if fixt.is_clash_fully_recorded(mfive):
                continue
            c = fixt.count_recorded_games(mfive)
            if c == 0:
                n_sched += 1
            else:
                n_ip += 1
        parts = []
        if n_sched:
            parts.append(f"{n_sched} scheduled")
        if n_ip:
            parts.append(f"{n_ip} in progress")
        stats[gk]["match_status"] = " · ".join(parts) if parts else "—"

    standings_data = []
    for group_key in groups.keys():
        s = stats[group_key]
        standings_data.append({
            'Team name': group_names.get(group_key, group_key),
            'Matches played': s['matches_played'],
            'Match status': s['match_status'],
            'Clash won': s['clash_won'],
            'Points': s['points'],
            'No of Sets won': s['sets_won'],
            'No of Sets lost': s['sets_lost'],
            'Set difference': s['sets_won'] - s['sets_lost'],
            'No of points won': s['points_won'],
            'No of points lost': s['points_lost'],
            'Points difference': s['points_won'] - s['points_lost'],
        })

    df = pd.DataFrame(standings_data)
    if not df.empty:
        df = df.sort_values(
            ['Points', 'Set difference', 'Points difference'],
            ascending=[False, False, False]
        ).reset_index(drop=True)
    return df

def record_new_clash():
    """Function to handle new clash recording"""
    col1, col2 = st.columns(2)
    with col1:
        # Display group names with their custom names
        group_options = [st.session_state.group_names.get(key, key) for key in st.session_state.groups.keys()]
        group_keys = list(st.session_state.groups.keys())
        g1_display = st.selectbox("Select Group 1", group_options, index=0, key="new_clash_g1")
        g1 = group_keys[group_options.index(g1_display)]
    with col2:
        g2_display = st.selectbox("Select Group 2", group_options, index=1 if len(group_options) > 1 else 0, key="new_clash_g2")
        g2 = group_keys[group_options.index(g2_display)]

    if g1 == g2:
        st.error("Please select two different groups.")
        return

    st.caption(
        "**Plan lineup & schedule** saves players + court/date/time to the **same clash slot** as recording. "
        "**Record scores** then only needs set scores and submit."
    )
    tab_rec, tab_plan = st.tabs(["📝 Record scores", "📋 Plan lineup & schedule"])
    with tab_rec:
        record_clash_matches(g1, g2, "new", show_intro=True)
    with tab_plan:
        plan_clash_meeting(g1, g2)

def edit_clash_results():
    """Function to handle editing existing clash results"""
    if not st.session_state.tournament_data:
        st.info("📝 No recorded clashes available to edit.")
        return
    
    td = st.session_state.tournament_data
    seen = set()
    for k in list(td.keys()):
        if "_vs_" not in k:
            continue
        pr = k.split("_vs_", 1)
        if len(pr) != 2:
            continue
        canon = fixt.canonical_clash_key(pr[0].strip(), pr[1].strip())
        if canon in seen:
            continue
        seen.add(canon)
        fixt.migrate_clash_pair_to_canonical(td, pr[0].strip(), pr[1].strip())

    gn = st.session_state.get("group_names", {})
    clash_options = []
    for clash_key in td.keys():
        if "_vs_" not in clash_key:
            continue
        parts = clash_key.split("_vs_", 1)
        if len(parts) != 2:
            continue
        lk, rk = parts[0].strip(), parts[1].strip()
        clash_options.append({
            "key": clash_key,
            "display": f"{gn.get(lk, lk)} vs {gn.get(rk, rk)}",
            "g1": lk,
            "g2": rk,
        })
    
    if not clash_options:
        st.info("📝 No recorded clashes available to edit.")
        return
    
    # Select clash to edit
    selected_clash = st.selectbox(
        "Select clash to edit:",
        clash_options,
        format_func=lambda x: x['display'],
        key="edit_clash_selector"
    )
    
    if selected_clash:
        st.subheader(f"Edit: {selected_clash['display']}")
        
        # Show current results (with match type and players)
        current_results = st.session_state.tournament_data.get(selected_clash['key'], [])
        subgroup_names = st.session_state.get("subgroup_names", DEFAULT_SUBGROUP_NAMES)
        dec_label = subgroup_names.get("subgroup1", "Decider")
        chok_label = subgroup_names.get("subgroup2", "Choker")
        match_pool_type = ["subgroup1", "subgroup2", "subgroup1", "subgroup2", "subgroup1"]
        if current_results:
            st.markdown("**Current Results:**")
            for i, result in enumerate(current_results[:5]):
                if not result or not result.get("winner"):
                    continue
                mt = dec_label if (i < len(match_pool_type) and match_pool_type[i] == "subgroup1") else chok_label
                pl = result.get("players") or {}
                _nm = lambda x: x.get("name", x) if isinstance(x, dict) else str(x)
                g1_n = ", ".join(_nm(p) for p in (pl.get("g1") or []))
                g2_n = ", ".join(_nm(p) for p in (pl.get("g2") or []))
                players_str = f"{g1_n} vs {g2_n}" if (g1_n or g2_n) else "—"
                st.write(f"**Match {i+1}** ({mt}): {result.get('winner_display', 'Unknown')} wins {result.get('score_display', '')} – {result.get('points', 0)} pts. Players: {players_str}")
        
        # Edit interface
        record_clash_matches(selected_clash['g1'], selected_clash['g2'], "edit", selected_clash['key'])

def view_clash_results():
    """Function for admins to view clash results (read-only)"""
    if not st.session_state.tournament_data:
        st.info("📝 No recorded clashes available.")
        return
    
    for clash_key, results in st.session_state.tournament_data.items():
        if '_vs_' in clash_key:
            parts = clash_key.split('_vs_')
            if len(parts) == 2:
                with st.expander(f"📊 {parts[0]} vs {parts[1]}"):
                    if results:
                        total_g1_points = 0
                        total_g2_points = 0
                        g1_wins = 0
                        g2_wins = 0
                        
                        for i, result in enumerate(results):
                            match_info = result.get('match_info', {})
                            winner = result.get('winner_display', 'Unknown')
                            score = result.get('score_display', '')
                            points = result.get('points', 0)
                            
                            st.write(f"**Match {i+1}:** {winner} wins {score} - {points} points")
                            
                            if result.get('winner') == 'g1':
                                total_g1_points += points
                                g1_wins += 1
                            elif result.get('winner') == 'g2':
                                total_g2_points += points
                                g2_wins += 1
                        
                        st.markdown("---")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric(f"{parts[0]}", f"{g1_wins} wins, {total_g1_points} points")
                        with col2:
                            st.metric(f"{parts[1]}", f"{g2_wins} wins, {total_g2_points} points")
                    else:
                        st.write("No match data available")

def show_edit_history():
    """Function to display clash edit history"""
    if not st.session_state.clash_edit_history:
        st.info("📝 No edit history available.")
        return
    
    st.markdown("**All Clash Edits:**")
    
    # Sort by timestamp (newest first)
    sorted_history = sorted(st.session_state.clash_edit_history, key=lambda x: x.get('timestamp', ''), reverse=True)
    
    for i, edit in enumerate(sorted_history):
        with st.expander(f"🔄 Edit #{i+1}: {edit.get('clash_key', 'Unknown')} - {edit.get('timestamp', 'Unknown time')}"):
            st.write(f"**Editor:** {edit.get('editor', 'Unknown')}")
            st.write(f"**Action:** {edit.get('action', 'Unknown')}")
            st.write(f"**Match:** {edit.get('match_number', 'Unknown')}")
            
            if edit.get('original_data'):
                st.markdown("**Original Data:**")
                st.json(edit.get('original_data'))
            
            if edit.get('new_data'):
                st.markdown("**New Data:**")
                st.json(edit.get('new_data'))
            
            if edit.get('reason'):
                st.write(f"**Reason:** {edit.get('reason')}")

def log_clash_edit(clash_key, match_number, action, original_data, new_data, reason=""):
    """Log clash edit to history"""
    edit_entry = {
        'timestamp': datetime.now().isoformat(),
        'editor': get_current_user(),
        'clash_key': clash_key,
        'match_number': match_number,
        'action': action,
        'original_data': original_data,
        'new_data': new_data,
        'reason': reason
    }
    
    st.session_state.clash_edit_history.append(edit_entry)
    auto_save()  # Save immediately after logging


def _pool_names_for_record_clash(group_key, pool_type):
    """
    Names eligible for a Decider (subgroup1) or Choker (subgroup2) match for one team.
    Uses detailed_groups when set; otherwise skill bands from player_database + last_balance_config defaults.
    """
    detailed = st.session_state.get("detailed_groups") or {}
    if detailed and group_key in detailed:
        sub = detailed[group_key].get(pool_type, {})
        players = sub.get("players") or []
        names = [p.get("name", p["name"]) if isinstance(p, dict) else str(p) for p in players if p]
        names = [n for n in names if n]
        if names:
            return names
    roster = list(st.session_state.groups.get(group_key, []))
    if not roster:
        return []
    cfg = st.session_state.get("last_balance_config") or {}
    if pool_type == "subgroup1":
        lo = int(cfg.get("subgroup1_min", DEFAULT_DECIDERS_MIN))
        hi = int(cfg.get("subgroup1_max", DEFAULT_DECIDERS_MAX))
    else:
        lo = int(cfg.get("subgroup2_min", DEFAULT_CHOKERS_MIN))
        hi = int(cfg.get("subgroup2_max", DEFAULT_CHOKERS_MAX))
    pd = st.session_state.get("player_database")
    if pd is None or pd.empty or "name" not in pd.columns or "skill_level" not in pd.columns:
        return []
    out = []
    for name in roster:
        row = pd[pd["name"].astype(str) == str(name)]
        if row.empty:
            continue
        try:
            sk = int(row.iloc[0]["skill_level"])
        except (TypeError, ValueError):
            continue
        if lo <= sk <= hi:
            out.append(name)
    return out


def _name_to_gender_map_for_random():
    m = {}
    pd = st.session_state.get("player_database")
    if pd is not None and not pd.empty and "name" in pd.columns:
        for _, row in pd.iterrows():
            m[str(row.get("name", row["name"]))] = str(row.get("gender", "M"))
    return m


def _pick_g2_pair_matching_female(g1_pair, pool2, name_to_gender, rng):
    """Return [p1, p2] from pool2 with same female count as g1_pair, or any two if impossible."""
    if len(pool2) < 2:
        return None
    fc = sum(1 for n in g1_pair if name_to_gender.get(str(n), "M") == "F")
    pool2 = list(pool2)
    rng.shuffle(pool2)
    for g2_p1 in pool2:
        rest = [n for n in pool2 if n != g2_p1]
        if fc == 0:
            rest = [n for n in rest if name_to_gender.get(str(n), "M") != "F"]
        elif fc == 1:
            g2f = name_to_gender.get(str(g2_p1), "M") == "F"
            rest = [n for n in rest if (name_to_gender.get(str(n), "M") == "F") == (not g2f)]
        else:
            rest = [n for n in rest if name_to_gender.get(str(n), "M") == "F"]
        if not rest:
            rest = [n for n in pool2 if n != g2_p1]
        if rest:
            return [g2_p1, rng.choice(rest)]
    a, b = pool2[0], pool2[1] if len(pool2) > 1 else pool2[0]
    return [a, b] if a != b else [a, pool2[-1]]


def _random_set_scores_for_winner(winner_side, rng):
    """Returns (set1, set2, set3, points) consistent with calculate_match_result logic."""
    if rng.random() < 0.5:
        lo = rng.randint(8, 19)
        if winner_side == "g1":
            s1, s2 = (21, lo), (21, min(lo + rng.randint(0, 4), 19))
            return s1, s2, (0, 0), 2
        s1, s2 = (lo, 21), (min(lo + rng.randint(0, 4), 19), 21)
        return s1, s2, (0, 0), 2
    if winner_side == "g1":
        lo = rng.randint(10, 18)
        return (21, lo), (rng.randint(11, 19), 21), (21, rng.randint(10, 18)), 1
    lo = rng.randint(10, 18)
    return (lo, 21), (21, rng.randint(11, 19)), (rng.randint(10, 18), 21), 1


def _generate_random_five_matches(g1, g2, rng):
    """Build 5 match dicts for g1 vs g2 (testing)."""
    match_pool_type = ["subgroup1", "subgroup2", "subgroup1", "subgroup2", "subgroup1"]
    name_to_gender = _name_to_gender_map_for_random()
    used_g1, used_g2 = set(), set()
    matches = []
    g1n, g2n = st.session_state.group_names.get(g1, g1), st.session_state.group_names.get(g2, g2)

    for i in range(5):
        pt = match_pool_type[i]
        pool1 = [n for n in _pool_names_for_record_clash(g1, pt) if str(n) not in used_g1]
        pool2 = [n for n in _pool_names_for_record_clash(g2, pt) if str(n) not in used_g2]
        roster1 = [n for n in st.session_state.groups.get(g1, []) if str(n) not in used_g1]
        roster2 = [n for n in st.session_state.groups.get(g2, []) if str(n) not in used_g2]
        if len(pool1) < 2:
            pool1 = roster1[:] if len(roster1) >= 2 else list(st.session_state.groups.get(g1, []))
        if len(pool2) < 2:
            pool2 = roster2[:] if len(roster2) >= 2 else list(st.session_state.groups.get(g2, []))
        rng.shuffle(pool1)
        rng.shuffle(pool2)
        if len(pool1) < 2 or len(pool2) < 2:
            return None
        p1 = [pool1[0], pool1[1]]
        p2 = _pick_g2_pair_matching_female(p1, pool2, name_to_gender, rng)
        if not p2 or len(set(p2)) < 2:
            if len(pool2) >= 2:
                p2 = [pool2[0], pool2[1]]
            else:
                return None
        if len(set(p1)) < 2:
            return None
        for n in p1:
            used_g1.add(str(n))
        for n in p2:
            used_g2.add(str(n))

        winner = rng.choice(["g1", "g2"])
        s1, s2, s3, pts = _random_set_scores_for_winner(winner, rng)
        sets_g1 = sum(1 for a, b in [(s1[0], s1[1]), (s2[0], s2[1]), (s3[0], s3[1])] if a > b)
        sets_g2 = sum(1 for a, b in [(s1[0], s1[1]), (s2[0], s2[1]), (s3[0], s3[1])] if b > a)
        if winner == "g1":
            score_disp = f"({sets_g1}-{sets_g2})"
        else:
            score_disp = f"({sets_g2}-{sets_g1})"
        matches.append({
            "winner": winner,
            "winner_display": g1n if winner == "g1" else g2n,
            "points": pts,
            "score_display": score_disp,
            "set_scores": {"set1": s1, "set2": s2, "set3": s3},
            "players": {"g1": p1, "g2": p2},
            "match_info": {
                "match_number": i + 1,
                "timestamp": datetime.now().isoformat(),
                "recorder": "random_test_generator",
            },
        })
    return matches


def _standings_row_for_group_key(group_key):
    """Standings index may be group key or display name from group_names."""
    standings = st.session_state.get("standings")
    if standings is None or standings.empty:
        return None
    if group_key in standings.index:
        return group_key
    disp = st.session_state.get("group_names", {}).get(group_key, group_key)
    if disp in standings.index:
        return disp
    return None


def _rebuild_standings_from_tournament_data():
    """Reset Clash Wins / Total Points from tournament_data."""
    standings = st.session_state.get("standings")
    if standings is None or standings.empty:
        return
    for idx in standings.index:
        try:
            standings.at[idx, "Clash Wins"] = 0
            standings.at[idx, "Total Points"] = 0
        except Exception:
            pass
    td = st.session_state.get("tournament_data") or {}
    rows = db.compute_standings_rows(
        st.session_state.groups,
        st.session_state.get("group_names", {}),
        td,
    )
    for r in rows:
        row_idx = _standings_row_for_group_key(r["group_name"])
        if row_idx is None:
            continue
        try:
            standings.at[row_idx, "Clash Wins"] = int(r["clash_won"])
            standings.at[row_idx, "Total Points"] = int(r["points"])
        except Exception:
            pass


def erase_all_clash_results():
    """
    Clear clash results and sync to Supabase (standings + tournament_matches).
    On DB failure, restores previous session so app and DB stay aligned.
    Returns (ok, user_message).
    """
    backup_td = dict(st.session_state.get("tournament_data") or {})
    st_stand = st.session_state.get("standings")
    backup_st = st_stand.copy() if st_stand is not None and not st_stand.empty else None

    st.session_state.tournament_data = {}
    standings = st.session_state.get("standings")
    if standings is not None and not standings.empty:
        for idx in standings.index:
            try:
                standings.at[idx, "Clash Wins"] = 0
                standings.at[idx, "Total Points"] = 0
            except Exception:
                pass

    db_ok, db_detail = _push_full_state_to_supabase()
    if not db_ok:
        st.session_state.tournament_data = backup_td
        if backup_st is not None:
            st.session_state.standings = backup_st
        return False, f"Could not update database: {db_detail}. Your clash data was left unchanged."

    for k in [
        x for x in list(st.session_state.keys())
        if isinstance(x, str) and (x.startswith("recorded_matches_") or x.startswith("edit_matches_"))
    ]:
        try:
            del st.session_state[k]
        except Exception:
            pass

    if db_detail == "local_only":
        return True, "Cleared locally. (Supabase not configured — nothing written to cloud.)"
    return True, "Cleared locally and **saved to Supabase** (standings + match results)."


def generate_random_clash_results_all_pairs():
    """Fill every group-vs-group pair with random 5-match clashes (testing)."""
    keys = [k for k in st.session_state.groups.keys() if st.session_state.groups.get(k)]
    if len(keys) < 2:
        return False, "Need at least two groups with players."
    rng = random.Random()
    new_td = {}
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            gi, gj = keys[i], keys[j]
            ls, rs = sorted([str(gi).strip(), str(gj).strip()], key=str)
            g_left = gi if str(gi).strip() == ls else gj
            g_right = gj if str(gj).strip() == rs else gi
            ck = f"{ls}_vs_{rs}"
            mlist = _generate_random_five_matches(g_left, g_right, rng)
            if not mlist:
                return False, f"Could not build random players for {ck}. Check team sizes."
            new_td[ck] = mlist

    backup_td = dict(st.session_state.get("tournament_data") or {})
    backup_st = st.session_state.standings.copy() if st.session_state.get("standings") is not None and not st.session_state.standings.empty else None

    st.session_state.tournament_data = new_td
    _rebuild_standings_from_tournament_data()

    db_ok, db_detail = _push_full_state_to_supabase()
    if not db_ok:
        st.session_state.tournament_data = backup_td
        if backup_st is not None:
            st.session_state.standings = backup_st
        return False, f"Random data was not applied: database save failed — {db_detail}"

    for k in [
        x for x in list(st.session_state.keys())
        if isinstance(x, str) and (x.startswith("recorded_matches_") or x.startswith("edit_matches_"))
    ]:
        try:
            del st.session_state[k]
        except Exception:
            pass

    n = len(new_td)
    if db_detail == "local_only":
        return True, f"Generated random results for {n} clash(es) (local session only; Supabase not configured)."
    return True, f"Generated random results for {n} clash(es) and **saved to Supabase**."


def _sync_session_clash_into_tournament_data(clash_key, session_key):
    """Merge recorded games from session into tournament_data (5 fixed slots)."""
    sess = st.session_state.get(session_key) or {}
    base = fixt.coerce_five_match_slots(st.session_state.tournament_data.get(clash_key))
    for i in range(5):
        if i in sess:
            base[i] = sess[i]
    st.session_state.tournament_data[clash_key] = base


def _clear_tournament_clash_game_slot(clash_key, game_index):
    base = fixt.coerce_five_match_slots(st.session_state.tournament_data.get(clash_key))
    base[game_index] = {}
    st.session_state.tournament_data[clash_key] = base


def _refresh_session_standings_from_tournament_data():
    """Align session standings DataFrame with computed tournament results."""
    try:
        rows = db.compute_standings_rows(
            st.session_state.groups,
            st.session_state.group_names,
            st.session_state.tournament_data,
        )
        st_df = st.session_state.standings
        for r in rows:
            gk = r["group_name"]
            if gk in st_df.index:
                st_df.at[gk, "Clash Wins"] = int(r["clash_won"])
                st_df.at[gk, "Total Points"] = int(r["points"])
    except Exception:
        pass


def _parse_fixture_datetime_iso(s: str):
    if not s or not str(s).strip():
        return None
    t = str(s).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(t)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt.replace(second=0, microsecond=0)
    except (TypeError, ValueError):
        return None


def _parse_date_text(s: str):
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_time_text(s: str):
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    return None


def _fixture_default_start_datetime(fx: dict) -> datetime:
    """Default for plan form: start from ISO or legacy date + start time only."""
    fx = fx or {}
    now = datetime.now().replace(second=0, microsecond=0)
    start = _parse_fixture_datetime_iso(fx.get("start_datetime") or "")
    if start is None:
        d = _parse_date_text(fx.get("date") or "")
        tm = _parse_time_text(fx.get("start_time") or "")
        if d is not None:
            start = datetime.combine(d, tm or datetime.min.time())
        else:
            start = now
    return start


def _fixture_schedule_display_line(fx: dict) -> str:
    """Single-line schedule for captions: start date & time only (ISO or legacy)."""
    fx = fx or {}
    s = _parse_fixture_datetime_iso(fx.get("start_datetime") or "")
    if s:
        return s.strftime("%Y-%m-%d %H:%M")
    d, a = fx.get("date"), fx.get("start_time")
    if d or a:
        return f"{d or '—'} {a or ''}".strip()
    return ""


def plan_clash_meeting(g1, g2):
    """
    Save per-game lineup + court/date/time into tournament_data (same 5 slots as Record a Clash).
    Uses the same Deciders/Chokers pools, no reuse, and female-matching rules.
    """
    td = st.session_state.tournament_data
    fixt.migrate_clash_pair_to_canonical(td, g1, g2)
    left_k, right_k = sorted([str(g1).strip(), str(g2).strip()], key=str)
    ck = f"{left_k}_vs_{right_k}"
    user_g1_is_left = str(g1).strip() == left_k
    subgroup_names = st.session_state.get("subgroup_names", DEFAULT_SUBGROUP_NAMES)
    match_pool_type = ["subgroup1", "subgroup2", "subgroup1", "subgroup2", "subgroup1"]
    dec_label = subgroup_names.get("subgroup1", "Decider")
    chok_label = subgroup_names.get("subgroup2", "Choker")
    name_to_gender = {}
    if not st.session_state.player_database.empty:
        for _, row in st.session_state.player_database.iterrows():
            name_to_gender[str(row.get("name", row["name"]))] = str(row.get("gender", "M"))

    st.subheader(f"📋 Plan meeting: {g1} vs {g2}")
    st.info(
        "Choose players and optional **court / date / time** for each game. This is stored in the **same clash object** "
        "as results. On **Record scores**, you only enter set scores for planned games."
    )

    slots = fixt.coerce_five_match_slots(td.get(ck, []))

    def _names_from_canonical_slot(slot, for_user_g1_team):
        pl = slot.get("players") or {}
        g1c, g2c = pl.get("g1") or [], pl.get("g2") or []
        if user_g1_is_left:
            u1, u2 = g1c, g2c
        else:
            u1, u2 = g2c, g1c
        side = u1 if for_user_g1_team else u2

        def nm(x):
            return x.get("name", x) if isinstance(x, dict) else str(x)

        return [nm(x) for x in side if nm(x)]

    for i in range(5):
        pool_type = match_pool_type[i]
        mt = dec_label if pool_type == "subgroup1" else chok_label
        cur = slots[i] if i < len(slots) else {}
        if fixt.normalize_match_winner(cur):
            with st.expander(f"✅ Game {i + 1} ({mt}) — already recorded", expanded=False):
                st.caption("Clear the result under **Record scores** (re-record) to change the plan.")
            continue

        used_g1, used_g2 = set(), set()
        for j in range(i):
            sj = slots[j]
            if not fixt.has_lineup(sj) and fixt.normalize_match_winner(sj) is None:
                continue
            pl = sj.get("players") or {}
            if user_g1_is_left:
                a, b = pl.get("g1") or [], pl.get("g2") or []
            else:
                a, b = pl.get("g2") or [], pl.get("g1") or []
            for x in a:
                used_g1.add((x.get("name", x) if isinstance(x, dict) else str(x)) or "")
            for x in b:
                used_g2.add((x.get("name", x) if isinstance(x, dict) else str(x)) or "")
        used_g1.discard("")
        used_g2.discard("")

        with st.expander(f"🏸 Game {i + 1} — {mt}", expanded=not fixt.is_planned_only(cur)):
            pool_g1 = _pool_names_for_record_clash(g1, pool_type)
            pool_g2 = _pool_names_for_record_clash(g2, pool_type)
            available_g1 = [n for n in pool_g1 if n and str(n) not in used_g1]
            available_g2 = [n for n in pool_g2 if n and str(n) not in used_g2]

            d1 = _names_from_canonical_slot(cur, True)
            d2 = _names_from_canonical_slot(cur, False)
            fx0 = (cur.get("fixture") or {}) if isinstance(cur, dict) else {}

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**{g1}** ({subgroup_names.get(pool_type, pool_type)})")
                i1 = (available_g1.index(d1[0]) + 1) if len(d1) > 0 and d1[0] in available_g1 else 0
                i2 = (available_g1.index(d1[1]) + 1) if len(d1) > 1 and d1[1] in available_g1 else 0
                g1_p1 = st.selectbox(f"{g1} – Player 1", [""] + available_g1, index=i1, key=f"plan_g1_p1_{ck}_{i}")
                g1_p2_opts = [""] + [n for n in available_g1 if n != g1_p1]
                i2b = g1_p2_opts.index(d1[1]) if len(d1) > 1 and d1[1] in g1_p2_opts else 0
                g1_p2 = st.selectbox(f"{g1} – Player 2", g1_p2_opts, index=i2b, key=f"plan_g1_p2_{ck}_{i}")
                p1 = [x for x in [g1_p1, g1_p2] if x]
            with c2:
                st.markdown(f"**{g2}** — female count must match")
                i3 = (available_g2.index(d2[0]) + 1) if len(d2) > 0 and d2[0] in available_g2 else 0
                g2_p1 = st.selectbox(f"{g2} – Player 1", [""] + available_g2, index=i3, key=f"plan_g2_p1_{ck}_{i}")
                g1_female_count = sum(1 for n in p1 if name_to_gender.get(str(n), "M") == "F") if len(p1) == 2 else None
                g2_p2_candidates = [n for n in available_g2 if n != g2_p1]
                if g2_p1 and g1_female_count is not None:
                    g2f = name_to_gender.get(str(g2_p1), "M") == "F"
                    if g1_female_count == 0:
                        g2_p2_candidates = [n for n in g2_p2_candidates if name_to_gender.get(str(n), "M") != "F"]
                    elif g1_female_count == 1:
                        g2_p2_candidates = [n for n in g2_p2_candidates if (name_to_gender.get(str(n), "M") == "F") == (not g2f)]
                    else:
                        g2_p2_candidates = [n for n in g2_p2_candidates if name_to_gender.get(str(n), "M") == "F"]
                g2_p2_opts = [""] + g2_p2_candidates
                i4 = g2_p2_opts.index(d2[1]) if len(d2) > 1 and d2[1] in g2_p2_opts else 0
                g2_p2 = st.selectbox(f"{g2} – Player 2", g2_p2_opts, index=i4, key=f"plan_g2_p2_{ck}_{i}")
                p2 = [x for x in [g2_p1, g2_p2] if x]

            st.markdown(
                "**Venue & when** (optional — shown to everyone preparing for the match). "
                "**When** is a single calendar + time picker."
            )
            start_def = _fixture_default_start_datetime(fx0)
            fv1, fv2 = st.columns([1, 2])
            with fv1:
                court_v = st.text_input("Court", value=str(fx0.get("court") or ""), key=f"plan_court_{ck}_{i}")
            with fv2:
                start_dt = st.datetime_input(
                    "Date & time",
                    value=start_def,
                    step=timedelta(minutes=15),
                    format="YYYY/MM/DD",
                    key=f"plan_start_dt_{ck}_{i}",
                )

            bc1, bc2 = st.columns(2)
            with bc1:
                if st.button(f"💾 Save plan — Game {i + 1}", key=f"plan_save_{ck}_{i}"):
                    if len(p1) != 2 or len(p2) != 2:
                        st.error("Select two players per team.")
                    elif start_dt is None:
                        st.error("Choose **Date & time** (or clear the widget to reset).")
                    else:
                        if user_g1_is_left:
                            canon = {"g1": list(p1), "g2": list(p2)}
                        else:
                            canon = {"g1": list(p2), "g2": list(p1)}
                        base = fixt.coerce_five_match_slots(td.get(ck, []))
                        base[i] = {
                            "planned": True,
                            "players": canon,
                            "fixture": {
                                "court": court_v.strip(),
                                "start_datetime": start_dt.isoformat(timespec="minutes"),
                                "date": start_dt.date().isoformat(),
                                "start_time": start_dt.strftime("%H:%M"),
                            },
                        }
                        td[ck] = base
                        st.session_state.tournament_data = td
                        auto_save()
                        st.success(f"Game {i + 1} plan saved (same slot as recording).")
                        st.rerun()
            with bc2:
                if fixt.is_planned_only(cur) and st.button(f"🗑️ Clear plan — Game {i + 1}", key=f"plan_clear_{ck}_{i}"):
                    base = fixt.coerce_five_match_slots(td.get(ck, []))
                    base[i] = {}
                    td[ck] = base
                    st.session_state.tournament_data = td
                    auto_save()
                    st.rerun()


def record_clash_matches(g1, g2, mode="new", clash_key=None, show_intro=True):
    """Function to record or edit clash matches"""
    td = st.session_state.tournament_data
    if mode == "new":
        st.subheader(f"Clash Details: {g1} vs {g2}")
        if show_intro:
            st.caption(
                "Same opponents always share one saved meeting — **Group 1 / Group 2 order does not matter**."
            )
            st.success(
                "Each **Submit Clash #n** saves that game immediately. **Standings** and **Leaderboard** update when the clash is **Completed** (all 5 games)."
            )
            st.caption(
                "💡 **Planned lineups** (from **Plan lineup & schedule**) appear here — you only add **set scores** and submit."
            )
        fixt.migrate_clash_pair_to_canonical(td, g1, g2)
        left_k, right_k = sorted([str(g1).strip(), str(g2).strip()], key=str)
        current_clash_key = f"{left_k}_vs_{right_k}"
        sk = f"recorded_matches_{current_clash_key}"
        for alt in (
            f"recorded_matches_{g1}_vs_{g2}",
            f"recorded_matches_{g2}_vs_{g1}",
        ):
            if alt != sk and alt in st.session_state:
                del st.session_state[alt]
        if sk not in st.session_state:
            st.session_state[sk] = {}
        existing = fixt.coerce_five_match_slots(td.get(current_clash_key))
        for i in range(5):
            if fixt.normalize_match_winner(existing[i]) and i not in st.session_state[sk]:
                st.session_state[sk][i] = existing[i]
    else:
        st.info("Edit clash results. Changes will be logged for audit purposes.")
        parts = (clash_key or "").split("_vs_", 1)
        if len(parts) == 2:
            fixt.migrate_clash_pair_to_canonical(td, parts[0].strip(), parts[1].strip())
        left_k, right_k = sorted([str(g1).strip(), str(g2).strip()], key=str)
        current_clash_key = f"{left_k}_vs_{right_k}"
        ek_old = f"edit_matches_{clash_key}" if clash_key else None
        if ek_old and ek_old != f"edit_matches_{current_clash_key}" and ek_old in st.session_state:
            del st.session_state[ek_old]
        if f"edit_matches_{current_clash_key}" not in st.session_state:
            existing_data = fixt.coerce_five_match_slots(td.get(current_clash_key, []))
            st.session_state[f"edit_matches_{current_clash_key}"] = {}
            for i in range(5):
                if fixt.normalize_match_winner(existing_data[i]):
                    st.session_state[f"edit_matches_{current_clash_key}"][i] = existing_data[i]

    def calculate_match_result(set1_g1, set1_g2, set2_g1, set2_g2, set3_g1, set3_g2):
        """Calculate match winner and points based on set scores"""
        sets_won_g1 = 0
        sets_won_g2 = 0
        
        # Count sets won
        if set1_g1 > set1_g2:
            sets_won_g1 += 1
        elif set1_g2 > set1_g1:
            sets_won_g2 += 1
            
        if set2_g1 > set2_g2:
            sets_won_g1 += 1
        elif set2_g2 > set2_g1:
            sets_won_g2 += 1
            
        if set3_g1 > set3_g2:
            sets_won_g1 += 1
        elif set3_g2 > set3_g1:
            sets_won_g2 += 1
        
        # Determine winner and points
        if sets_won_g1 == 2:
            winner = "g1"
            points = 2 if sets_won_g2 == 0 else 1  # 2 points for 2-0, 1 point for 2-1
        elif sets_won_g2 == 2:
            winner = "g2"
            points = 2 if sets_won_g1 == 0 else 1  # 2 points for 2-0, 1 point for 2-1
        else:
            winner = None
            points = 0
            
        return winner, points, sets_won_g1, sets_won_g2

    # Track current clash totals
    g1_clash_points = 0
    g2_clash_points = 0
    g1_match_wins = 0
    g2_match_wins = 0
    
    session_key = f"recorded_matches_{current_clash_key}" if mode == "new" else f"edit_matches_{current_clash_key}"
    user_g1_is_left = str(g1).strip() == left_k

    def _record_team_label(k):
        return st.session_state.group_names.get(k, k)

    subgroup_names = st.session_state.get("subgroup_names", DEFAULT_SUBGROUP_NAMES)
    # Match schedule: 1=Deciders, 2=Chokers, 3=Deciders, 4=Chokers, 5=Deciders
    match_pool_type = ["subgroup1", "subgroup2", "subgroup1", "subgroup2", "subgroup1"]
    # Gender lookup for female-matching constraint
    name_to_gender = {}
    if not st.session_state.player_database.empty:
        for _, row in st.session_state.player_database.iterrows():
            name_to_gender[str(row.get("name", row["name"]))] = str(row.get("gender", "M"))

    dec_label = subgroup_names.get("subgroup1", "Decider")
    chok_label = subgroup_names.get("subgroup2", "Choker")
    st.markdown("##### Match schedule (5 matches total)")
    st.success(
        f"**3 {dec_label} matches** (matches 1, 3, 5) — player lists show **{dec_label}** players only.  \n"
        f"**2 {chok_label} matches** (matches 2, 4) — player lists show **{chok_label}** players only."
    )
    
    for i in range(5):
        match_recorded = i in st.session_state[session_key]
        
        # Show different styling for recorded matches
        if match_recorded:
            _pool_type_i = match_pool_type[i]
            _match_type_i = dec_label if _pool_type_i == "subgroup1" else chok_label
            with st.expander(f"🏸 ✅ Clash #{i+1} – {_match_type_i} – {'RECORDED' if mode == 'new' else 'CURRENT'}", expanded=False):
                recorded_data = st.session_state[session_key][i]
                wst = fixt.normalize_match_winner(recorded_data)
                win_key = left_k if wst == "g1" else right_k if wst == "g2" else None
                st.success(f"**Winner**: {_record_team_label(win_key) if win_key else recorded_data.get('winner_display', '—')}")
                st.info(f"**Score**: {recorded_data['score_display']}")
                st.info(f"**Points**: {recorded_data['points']} points awarded")
                st.caption(f"**Match type**: {_match_type_i}")
                # Player details (storage: g1=left_k team, g2=right_k team)
                pl = recorded_data.get("players") or {}
                g1_names = pl.get("g1") or []
                g2_names = pl.get("g2") or []
                def _name(x):
                    return x.get("name", x) if isinstance(x, dict) else str(x)
                left_team_label = _record_team_label(left_k)
                right_team_label = _record_team_label(right_k)
                st.caption(f"**{left_team_label}**: {', '.join(_name(n) for n in g1_names) or '—'}")
                st.caption(f"**{right_team_label}**: {', '.join(_name(n) for n in g2_names) or '—'}")
                st.divider()
                if mode == "edit" and get_current_user_role() == 'superuser':
                    if st.button(f"✏️ Edit Clash #{i+1}", key=f"edit_match_{mode}_{current_clash_key}_{i}"):
                        st.session_state[f"original_match_{current_clash_key}_{i}"] = recorded_data.copy()
                        if i in st.session_state[session_key]:
                            del st.session_state[session_key][i]
                        _clear_tournament_clash_game_slot(current_clash_key, i)
                        _refresh_session_standings_from_tournament_data()
                        auto_save()
                        st.rerun()
                elif mode == "new":
                    if st.button(f"🔄 Re-record Clash #{i+1}", key=f"rerecord_{mode}_{current_clash_key}_{i}"):
                        if i in st.session_state[session_key]:
                            del st.session_state[session_key][i]
                        _clear_tournament_clash_game_slot(current_clash_key, i)
                        _refresh_session_standings_from_tournament_data()
                        auto_save()
                        st.rerun()
                        
                # Add to totals (storage winner → user's Group 1 / Group 2)
                wst = fixt.normalize_match_winner(recorded_data)
                won_side = left_k if wst == "g1" else right_k if wst == "g2" else None
                if won_side is not None:
                    if str(won_side) == str(g1):
                        g1_clash_points += recorded_data['points']
                        g1_match_wins += 1
                    else:
                        g2_clash_points += recorded_data['points']
                        g2_match_wins += 1
        else:
            td_slots = fixt.coerce_five_match_slots(td.get(current_clash_key, []))
            slot_pre = td_slots[i] if i < len(td_slots) else {}
            with st.expander(f"🏸 Clash #{i+1} – {subgroup_names.get(match_pool_type[i], match_pool_type[i])}", expanded=True):
                # Used players in previous matches (session or saved plan/result in tournament_data)
                used_g1, used_g2 = set(), set()
                for j in range(i):
                    rec = None
                    if j in st.session_state.get(session_key, {}):
                        rec = st.session_state[session_key][j]
                    elif j < len(td_slots):
                        sj = td_slots[j]
                        if fixt.has_lineup(sj) or fixt.normalize_match_winner(sj) is not None:
                            rec = sj
                    if not rec:
                        continue
                    pl = rec.get("players") or {}
                    if user_g1_is_left:
                        prev_u1, prev_u2 = pl.get("g1") or [], pl.get("g2") or []
                    else:
                        prev_u1, prev_u2 = pl.get("g2") or [], pl.get("g1") or []
                    for name in prev_u1:
                        if isinstance(name, dict):
                            used_g1.add(name.get("name", "") or "")
                        else:
                            used_g1.add(str(name))
                    for name in prev_u2:
                        if isinstance(name, dict):
                            used_g2.add(name.get("name", "") or "")
                        else:
                            used_g2.add(str(name))
                used_g1.discard("")
                used_g2.discard("")

                # Pool: Deciders-only or Chokers-only per match; never full roster
                pool_type = match_pool_type[i]
                pool_g1 = _pool_names_for_record_clash(g1, pool_type)
                pool_g2 = _pool_names_for_record_clash(g2, pool_type)
                available_g1 = [n for n in pool_g1 if n and str(n) not in used_g1]
                available_g2 = [n for n in pool_g2 if n and str(n) not in used_g2]
                if not pool_g1 or not pool_g2:
                    pool_kind = dec_label if pool_type == "subgroup1" else chok_label
                    st.warning(
                        f"**{pool_kind} pool is empty** for one or both teams. "
                        f"Create teams with **Skill-Level Subgroups** (or ensure player **skill_level** matches "
                        f"Deciders {DEFAULT_DECIDERS_MIN}–{DEFAULT_DECIDERS_MAX} / Chokers {DEFAULT_CHOKERS_MIN}–{DEFAULT_CHOKERS_MAX})."
                    )

                def _names_for_user_teams_from_canonical(slot: dict):
                    pls = slot.get("players") or {}
                    g1c, g2c = pls.get("g1") or [], pls.get("g2") or []

                    def _nm(x):
                        return (x.get("name", x) if isinstance(x, dict) else str(x) or "").strip()

                    if user_g1_is_left:
                        u1, u2 = g1c, g2c
                    else:
                        u1, u2 = g2c, g1c
                    return [_nm(x) for x in u1 if _nm(x)], [_nm(x) for x in u2 if _nm(x)]

                planned_full = False
                p1, p2 = [], []
                if fixt.is_planned_only(slot_pre):
                    p1, p2 = _names_for_user_teams_from_canonical(slot_pre)
                    planned_full = len(p1) == 2 and len(p2) == 2
                    if not planned_full:
                        st.warning(
                            "Planned lineup for this game is incomplete — select all four players below "
                            "(or finish the plan under **Plan lineup & schedule**)."
                        )

                if planned_full:
                    st.success("📋 **Lineup from plan** — add **set scores** and submit.")
                    fx = slot_pre.get("fixture") or {}
                    court_s = str(fx.get("court") or "").strip()
                    when_s = _fixture_schedule_display_line(fx).strip()
                    if court_s or when_s:
                        fc1, fc2 = st.columns(2)
                        with fc1:
                            st.caption(f"**Court:** {court_s or '—'}")
                        with fc2:
                            st.caption(f"**When:** {when_s or '—'}")
                    st.caption(f"**{g1}**: {', '.join(p1)}")
                    st.caption(f"**{g2}**: {', '.join(p2)}")
                else:
                    # Player selection: two selectboxes per team (for female-matching constraint)
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**{g1} Team** ({subgroup_names.get(pool_type, pool_type)})")
                        g1_p1_options = [""] + available_g1
                        g1_p1 = st.selectbox(f"{g1} – Player 1", g1_p1_options, key=f"{mode}_g1_p1_m{i}")
                        g1_p2_options = [""] + [n for n in available_g1 if n != g1_p1]
                        g1_p2 = st.selectbox(f"{g1} – Player 2", g1_p2_options, key=f"{mode}_g1_p2_m{i}")
                        p1 = [x for x in [g1_p1, g1_p2] if x]
                    with col2:
                        st.markdown(f"**{g2} Team** ({subgroup_names.get(pool_type, pool_type)}) – must match female count")
                        g2_p1_options = [""] + available_g2
                        g2_p1 = st.selectbox(f"{g2} – Player 1", g2_p1_options, key=f"{mode}_g2_p1_m{i}")
                        g1_female_count = sum(1 for n in p1 if name_to_gender.get(str(n), "M") == "F") if len(p1) == 2 else None
                        g2_p2_candidates = [n for n in available_g2 if n != g2_p1]
                        if g2_p1 and g1_female_count is not None:
                            g2_p1_is_f = name_to_gender.get(str(g2_p1), "M") == "F"
                            if g1_female_count == 0:
                                g2_p2_candidates = [n for n in g2_p2_candidates if name_to_gender.get(str(n), "M") != "F"]
                            elif g1_female_count == 1:
                                g2_p2_candidates = [
                                    n
                                    for n in g2_p2_candidates
                                    if (name_to_gender.get(str(n), "M") == "F") == (not g2_p1_is_f)
                                ]
                            else:
                                g2_p2_candidates = [n for n in g2_p2_candidates if name_to_gender.get(str(n), "M") == "F"]
                        g2_p2_options = [""] + g2_p2_candidates
                        g2_p2 = st.selectbox(f"{g2} – Player 2 (match female count)", g2_p2_options, key=f"{mode}_g2_p2_m{i}")
                        p2 = [x for x in [g2_p1, g2_p2] if x]

                st.divider()
                
                # Set scores input
                st.markdown("**Set Scores** (Enter points for each set)")
                
                # Set 1
                set1_col1, set1_col2, set1_col3 = st.columns([1, 1, 2])
                with set1_col1:
                    set1_g1 = st.number_input(f"Set 1 - {g1}", min_value=0, max_value=30, value=0, key=f"{mode}_set1_g1_{i}")
                with set1_col2:
                    set1_g2 = st.number_input(f"Set 1 - {g2}", min_value=0, max_value=30, value=0, key=f"{mode}_set1_g2_{i}")
                with set1_col3:
                    if set1_g1 > set1_g2:
                        st.success(f"✅ {g1} wins Set 1")
                    elif set1_g2 > set1_g1:
                        st.success(f"✅ {g2} wins Set 1")
                    else:
                        st.info("Set 1: Tie or not played")
                
                # Set 2
                set2_col1, set2_col2, set2_col3 = st.columns([1, 1, 2])
                with set2_col1:
                    set2_g1 = st.number_input(f"Set 2 - {g1}", min_value=0, max_value=30, value=0, key=f"{mode}_set2_g1_{i}")
                with set2_col2:
                    set2_g2 = st.number_input(f"Set 2 - {g2}", min_value=0, max_value=30, value=0, key=f"{mode}_set2_g2_{i}")
                with set2_col3:
                    if set2_g1 > set2_g2:
                        st.success(f"✅ {g1} wins Set 2")
                    elif set2_g2 > set2_g1:
                        st.success(f"✅ {g2} wins Set 2")
                    else:
                        st.info("Set 2: Tie or not played")
                
                # Check if match is already decided (someone won 2 sets)
                sets_won_g1_so_far = sum([1 for s1, s2 in [(set1_g1, set1_g2), (set2_g1, set2_g2)] if s1 > s2])
                sets_won_g2_so_far = sum([1 for s1, s2 in [(set1_g1, set1_g2), (set2_g1, set2_g2)] if s2 > s1])
                
                match_decided = sets_won_g1_so_far == 2 or sets_won_g2_so_far == 2
                
                # Set 3 (conditionally disabled)
                set3_col1, set3_col2, set3_col3 = st.columns([1, 1, 2])
                with set3_col1:
                    set3_g1 = st.number_input(f"Set 3 - {g1}", 
                                            min_value=0, max_value=30, value=0, 
                                            disabled=match_decided,
                                            key=f"{mode}_set3_g1_{i}")
                with set3_col2:
                    set3_g2 = st.number_input(f"Set 3 - {g2}", 
                                            min_value=0, max_value=30, value=0, 
                                            disabled=match_decided,
                                            key=f"{mode}_set3_g2_{i}")
                with set3_col3:
                    if match_decided:
                        st.info("🚫 Set 3 not needed - clash already decided")
                    elif set3_g1 > set3_g2:
                        st.success(f"✅ {g1} wins Set 3")
                    elif set3_g2 > set3_g1:
                        st.success(f"✅ {g2} wins Set 3")
                    else:
                        st.info("Set 3: Tie or not played")
                
                # Calculate and display match result
                winner, points, total_sets_g1, total_sets_g2 = calculate_match_result(
                    set1_g1, set1_g2, set2_g1, set2_g2, set3_g1, set3_g2
                )
                
                # Match result preview
                st.divider()
                if winner == "g1":
                    st.success(f"🏆 **Preview**: {g1} wins this clash! ({total_sets_g1}-{total_sets_g2}) - {points} points")
                elif winner == "g2":
                    st.success(f"🏆 **Preview**: {g2} wins this clash! ({total_sets_g2}-{total_sets_g1}) - {points} points")
                else:
                    st.warning("⏳ Clash incomplete or tied - cannot submit yet")
                
                # Individual match submit button
                col1, col2 = st.columns([1, 3])
                with col1:
                    submit_enabled = winner is not None and len(p1) == 2 and len(p2) == 2
                    
                    # Edit reason field for edit mode
                    edit_reason = ""
                    if mode == "edit":
                        edit_reason = st.text_input(f"Reason for edit (Clash {i+1})", key=f"edit_reason_{i}", 
                                                  placeholder="e.g., Score correction, Player change")
                    
                    if st.button(f"✅ {'Update' if mode == 'edit' else 'Submit'} Clash #{i+1}", 
                               type="primary", 
                               disabled=not submit_enabled,
                               key=f"submit_{mode}_{current_clash_key}_{i}"):
                        match_info_base = {
                            'match_number': i + 1,
                            'timestamp': datetime.now().isoformat(),
                            'recorder': get_current_user(),
                        }
                        if fixt.is_planned_only(slot_pre):
                            f0 = slot_pre.get("fixture") or {}
                            _fk = ("court", "start_datetime", "date", "start_time")
                            fx_trim = {k: v for k, v in f0.items() if k in _fk and str(v).strip()}
                            if fx_trim:
                                match_info_base["fixture"] = fx_trim

                        # Persist in canonical orientation (left_k vs right_k in storage key)
                        if user_g1_is_left:
                            w_store = winner
                            ts_l, ts_r = total_sets_g1, total_sets_g2
                            match_data = {
                                'winner': w_store,
                                'winner_display': _record_team_label(left_k if w_store == 'g1' else right_k),
                                'points': points,
                                'score_display': f"({ts_l}-{ts_r})" if w_store == 'g1' else f"({ts_r}-{ts_l})",
                                'set_scores': {
                                    'set1': (set1_g1, set1_g2),
                                    'set2': (set2_g1, set2_g2),
                                    'set3': (set3_g1, set3_g2) if not match_decided else (0, 0),
                                },
                                'players': {'g1': list(p1), 'g2': list(p2)},
                                'match_info': dict(match_info_base),
                            }
                        else:
                            w_store = 'g2' if winner == 'g1' else 'g1'
                            ts_l, ts_r = total_sets_g2, total_sets_g1
                            match_data = {
                                'winner': w_store,
                                'winner_display': _record_team_label(left_k if w_store == 'g1' else right_k),
                                'points': points,
                                'score_display': f"({ts_l}-{ts_r})" if w_store == 'g1' else f"({ts_r}-{ts_l})",
                                'set_scores': {
                                    'set1': (set1_g2, set1_g1),
                                    'set2': (set2_g2, set2_g1),
                                    'set3': (set3_g2, set3_g1) if not match_decided else (0, 0),
                                },
                                'players': {'g1': list(p2), 'g2': list(p1)},
                                'match_info': dict(match_info_base),
                            }
                        
                        # For edit mode, log the change
                        if mode == "edit":
                            original_data = st.session_state.get(f"original_match_{current_clash_key}_{i}", {})
                            log_clash_edit(
                                current_clash_key, 
                                i+1, 
                                "match_edit", 
                                original_data, 
                                match_data,
                                edit_reason
                            )
                        
                        st.session_state[session_key][i] = match_data
                        _sync_session_clash_into_tournament_data(current_clash_key, session_key)
                        _refresh_session_standings_from_tournament_data()
                        auto_save()
                        st.success(
                            f"✅ Clash #{i+1} {'updated' if mode == 'edit' else 'recorded'} — saved. **Standings** updated."
                        )
                        st.rerun()
                
                with col2:
                    if not submit_enabled:
                        missing_items = []
                        if len(p1) != 2:
                            missing_items.append(f"{g1} needs 2 players")
                        if len(p2) != 2:
                            missing_items.append(f"{g2} needs 2 players")
                        if winner is None:
                            missing_items.append("Complete clash scoring")
                        st.warning(f"⚠️ To submit: {', '.join(missing_items)}")
    
    # Display current clash summary
    st.divider()
    st.subheader("📊 Current Clash Summary")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(f"{g1} Clash Wins", g1_match_wins)
        st.metric(f"{g1} Points", g1_clash_points)
    with col2:
        st.metric("Clashes Recorded", len(st.session_state[session_key]), "out of 5")
    with col3:
        st.metric(f"{g2} Clash Wins", g2_match_wins)
        st.metric(f"{g2} Points", g2_clash_points)
    
    if g1_match_wins > g2_match_wins:
        st.success(f"🏆 **{g1} is currently leading the clash!**")
    elif g2_match_wins > g1_match_wins:
        st.success(f"🏆 **{g2} is currently leading the clash!**")
    else:
        st.info("🤝 Clash is currently tied!")

    num_recorded = len(st.session_state[session_key])
    # Final submission button (only appears when all matches are recorded)
    if num_recorded == 5:
        button_text = "🏆 Finalize Clash Changes" if mode == "edit" else "🏆 Finalize Clash Results"
        
        if mode == "edit":
            final_edit_reason = st.text_input("Overall reason for clash edit:", 
                                            placeholder="e.g., Multiple score corrections needed")
        
        if st.button(
            button_text,
            type="primary",
            key=f"finalize_clash_{mode}_{current_clash_key}",
            help="Clears this form. All games are already saved to standings after each submit.",
        ):
            if mode == "edit":
                _sync_session_clash_into_tournament_data(current_clash_key, session_key)
                new_clash_data = fixt.coerce_five_match_slots(st.session_state.tournament_data.get(current_clash_key))
                log_clash_edit(
                    current_clash_key,
                    "all",
                    "clash_finalize_edit",
                    st.session_state.tournament_data.get(current_clash_key, []),
                    new_clash_data,
                    final_edit_reason if "final_edit_reason" in locals() else "",
                )
                st.session_state.tournament_data[current_clash_key] = new_clash_data
                del st.session_state[session_key]
            else:
                _sync_session_clash_into_tournament_data(current_clash_key, session_key)
                del st.session_state[session_key]
            _refresh_session_standings_from_tournament_data()
            auto_save()
            st.balloons()
            st.success(
                f"🎉 Meeting closed. Summary: {g1} {g1_match_wins}–{g2_match_wins} {g2} (game points). "
                f"Standings were updated after each game."
            )
            st.rerun()
    else:
        remaining = 5 - num_recorded
        st.info(
            f"📝 **{remaining}** game(s) not yet recorded. Submit each game to save; standings update after each game."
        )

# --- MAIN MENU STRUCTURE ---
if menu == "Player Import & Auto-Balance":
    st.header("📊 Player Import & Team Auto-Balancing")
    st.markdown("Import players with detailed information and automatically create balanced groups.")
    
    # Display option: show skill level in this section's balance view and in Team Details
    st.subheader("🖥️ Display options")
    show_skill_check = st.checkbox(
        "Show skill levels in group/team views",
        value=st.session_state.get("show_skill_in_groups", True),
        key="show_skill_in_groups_check",
        help="When off, skill level and skill-based metrics are hidden in the balance results below and in Team Details."
    )
    st.session_state.show_skill_in_groups = show_skill_check
    st.markdown("---")
    
    # Import Methods
    st.subheader("📥 Import Players")
    
    import_method = st.radio("Choose import method:", ["Manual Entry", "CSV/Excel Upload", "Bulk Text Import"])
    
    if import_method == "CSV/Excel Upload":
        st.info("Upload a CSV or Excel file with columns: name, gender (M/F), email, skill_level (0-15)")
        
        # Template download options
        template_data = {
            'name': ['John Doe', 'Jane Smith', 'Mike Johnson'],
            'gender': ['M', 'F', 'M'],
            'email': ['john@example.com', 'jane@example.com', 'mike@example.com'],
            'skill_level': [7, 8, 6]
        }
        template_df = pd.DataFrame(template_data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # CSV template
            csv_template = template_df.to_csv(index=False)
            st.download_button(
                label="📄 Download CSV Template",
                data=csv_template,
                file_name="player_template.csv",
                mime="text/csv"
            )
        
        with col2:
            # Excel template
            try:
                excel_buffer = io.BytesIO()
                template_df.to_excel(excel_buffer, index=False, engine='openpyxl')
                excel_template = excel_buffer.getvalue()
                
                st.download_button(
                    label="📊 Download Excel Template",
                    data=excel_template,
                    file_name="player_template.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except ImportError:
                st.info("📊 Excel template: Install openpyxl to enable Excel template download")
        
        uploaded_file = st.file_uploader(
            "Choose file", 
            type=["csv", "xlsx", "xls"],
            help="Upload CSV or Excel file with player data"
        )
        
        if uploaded_file is not None:
            try:
                file_extension = uploaded_file.name.split('.')[-1].lower()
                
                # Read file based on extension
                if file_extension == 'csv':
                    new_players_df = pd.read_csv(uploaded_file)
                elif file_extension in ['xlsx', 'xls']:
                    try:
                        # Try with openpyxl first (for .xlsx)
                        new_players_df = pd.read_excel(uploaded_file, engine='openpyxl')
                    except ImportError:
                        try:
                            # Fallback to xlrd (for .xls)
                            new_players_df = pd.read_excel(uploaded_file, engine='xlrd')
                        except ImportError:
                            st.error("❌ Excel support not available. Please install openpyxl: `pip install openpyxl`")
                            st.stop()
                    except Exception as e:
                        # Try with different engines
                        try:
                            new_players_df = pd.read_excel(uploaded_file)
                        except Exception as e2:
                            st.error(f"❌ Error reading Excel file: {str(e2)}")
                            st.stop()
                else:
                    st.error("❌ Unsupported file format")
                    st.stop()
                
                # Validate columns
                required_cols = ['name', 'gender', 'email', 'skill_level']
                if all(col in new_players_df.columns for col in required_cols):
                    # Validate data
                    new_players_df['gender'] = new_players_df['gender'].str.upper()
                    new_players_df['skill_level'] = pd.to_numeric(new_players_df['skill_level'], errors='coerce')
                    
                    # Filter valid rows
                    valid_rows = (
                        new_players_df['gender'].isin(['M', 'F']) &
                        new_players_df['skill_level'].between(SKILL_LEVEL_MIN, SKILL_LEVEL_MAX) &
                        new_players_df['name'].notna() &
                        new_players_df['email'].notna()
                    )
                    
                    valid_players = new_players_df[valid_rows].copy()
                    invalid_count = len(new_players_df) - len(valid_players)
                    
                    if len(valid_players) > 0:
                        st.success(f"✅ Found {len(valid_players)} valid players in {file_extension.upper()} file")
                        if invalid_count > 0:
                            st.warning(f"⚠️ Skipped {invalid_count} invalid rows")
                        
                        # Preview data
                        st.dataframe(valid_players, use_container_width=True)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            replace_existing = st.checkbox("Replace all existing players", value=True)
                        
                        if st.button("Import These Players", type="primary"):
                            # Add missing columns
                            valid_players['group'] = None
                            valid_players['assigned'] = False
                            
                            if replace_existing:
                                st.session_state.player_database = valid_players
                            else:
                                st.session_state.player_database = pd.concat([st.session_state.player_database, valid_players], ignore_index=True)
                            
                            auto_save()  # Auto-save after import
                            st.success(f"🎉 Players imported successfully from {file_extension.upper()} file!")
                            st.rerun()
                    else:
                        st.error("❌ No valid players found in the uploaded file")
                else:
                    st.error(f"❌ Missing required columns. Expected: {required_cols}")
                    st.info(f"Found columns: {list(new_players_df.columns)}")
                    
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")
                st.info("💡 Tip: Make sure your file has the correct format and required columns")
    
    elif import_method == "Bulk Text Import":
        st.info("Enter players in format: Name, Gender(M/F), Email, Skill(0-15) - one per line")
        
        bulk_input = st.text_area(
            "Enter player data:",
            height=300,
            placeholder="John Doe, M, john@example.com, 7\nJane Smith, F, jane@example.com, 8\nMike Johnson, M, mike@example.com, 6"
        )
        
        if st.button("Parse and Import", type="primary") and bulk_input.strip():
            players_data = []
            lines = bulk_input.strip().split('\n')
            
            for line_num, line in enumerate(lines, 1):
                try:
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 4:
                        name, gender, email, skill = parts[0], parts[1].upper(), parts[2], int(parts[3])
                        if gender in ['M', 'F'] and SKILL_LEVEL_MIN <= skill <= SKILL_LEVEL_MAX:
                            players_data.append({
                                'name': name,
                                'gender': gender,
                                'email': email,
                                'skill_level': skill,
                                'group': None,
                                'assigned': False
                            })
                        else:
                            st.warning(f"⚠️ Line {line_num}: Invalid gender or skill level")
                    else:
                        st.warning(f"⚠️ Line {line_num}: Not enough data fields")
                except:
                    st.warning(f"⚠️ Line {line_num}: Error parsing data")
            
            if players_data:
                new_df = pd.DataFrame(players_data)
                st.session_state.player_database = new_df
                auto_save()  # Auto-save after bulk import
                st.success(f"✅ Imported {len(players_data)} players!")
                st.rerun()
    
    elif import_method == "Manual Entry":
        st.info("Add players one by one")
        
        with st.form("manual_player_entry"):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                player_name = st.text_input("Player Name")
            with col2:
                player_gender = st.selectbox("Gender", ["M", "F"])
            with col3:
                player_email = st.text_input("Email")
            with col4:
                player_skill = st.number_input("Skill Level", min_value=SKILL_LEVEL_MIN, max_value=SKILL_LEVEL_MAX, value=7)
            
            if st.form_submit_button("Add Player"):
                if player_name.strip() and player_email.strip():
                    new_player = pd.DataFrame({
                        'name': [player_name.strip()],
                        'gender': [player_gender],
                        'email': [player_email.strip()],
                        'skill_level': [player_skill],
                        'group': [None],
                        'assigned': [False]
                    })
                    
                    st.session_state.player_database = pd.concat([st.session_state.player_database, new_player], ignore_index=True)
                    auto_save()  # Auto-save after manual entry
                    st.success(f"✅ Added {player_name}!")
                    st.rerun()
                else:
                    st.error("Please enter both name and email")
    
    st.divider()
    
    # Current Player Database
    st.subheader("👥 Current Player Database")
    
    if not st.session_state.player_database.empty:
        # Display statistics
        total_players = len(st.session_state.player_database)
        male_players = len(st.session_state.player_database[st.session_state.player_database['gender'] == 'M'])
        female_players = len(st.session_state.player_database[st.session_state.player_database['gender'] == 'F'])
        avg_skill = st.session_state.player_database['skill_level'].mean()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Players", total_players)
        with col2:
            st.metric("Male Players", male_players)
        with col3:
            st.metric("Female Players", female_players)
        with col4:
            st.metric("Avg Skill Level", f"{avg_skill:.1f}")
        
        # Editable dataframe
        edited_df = st.data_editor(
            st.session_state.player_database,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "skill_level": st.column_config.NumberColumn(
                    "Skill Level",
                    min_value=SKILL_LEVEL_MIN,
                    max_value=SKILL_LEVEL_MAX,
                    step=1,
                ),
                "gender": st.column_config.SelectboxColumn(
                    "Gender",
                    options=["M", "F"],
                ),
            },
            key="player_database_editor"
        )
        
        # Update the database
        st.session_state.player_database = edited_df
        
        st.divider()
        
        # Auto-Balance Groups
        st.subheader("⚖️ Auto-Balance Groups")
        st.info("Automatically create balanced groups based on skill level and gender distribution")
        
        if len(st.session_state.player_database) >= 60:
            # Balance strategy selection
            balance_strategy = st.selectbox(
                "Balancing Strategy:",
                ["Optimized Balance (Recommended)", "Skill-Level Subgroups", "Snake Draft", "Random"],
                help="Choose how to balance players across groups"
            )
            
            # Gender distribution constraints (for Optimized Balance strategy)
            if balance_strategy == "Optimized Balance (Recommended)":
                st.markdown("#### 👥 Gender Distribution Settings")
                
                # Get current female player count
                total_females = len(st.session_state.player_database[st.session_state.player_database['gender'] == 'F'])
                total_males = len(st.session_state.player_database[st.session_state.player_database['gender'] == 'M'])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Female Players", total_females)
                with col2:
                    st.metric("Total Male Players", total_males)
                with col3:
                    st.metric("Total Players", total_females + total_males)
                
                # Min/Max females per group settings
                col1, col2 = st.columns(2)
                with col1:
                    min_females = st.number_input(
                        "Minimum females per group:",
                        min_value=0,
                        max_value=total_females // 6 if total_females > 0 else 0,
                        value=max(0, total_females // 6 if total_females > 0 else 0),
                        help="Minimum number of female players in each group"
                    )
                with col2:
                    max_females = st.number_input(
                        "Maximum females per group:",
                        min_value=min_females,
                        max_value=10,
                        value=min(10, (total_females + 5) // 6 if total_females > 0 else 0),
                        help="Maximum number of female players in each group"
                    )
                
                # Validation and preview
                if total_females > 0:
                    min_total_needed = min_females * 6
                    max_total_capacity = max_females * 6
                    
                    if min_total_needed > total_females:
                        st.error(f"❌ Minimum constraint too high: need {min_total_needed} females, but only have {total_females}")
                    elif max_total_capacity < total_females:
                        st.error(f"❌ Maximum constraint too low: can fit {max_total_capacity} females, but have {total_females}")
                    else:
                        # Show distribution preview
                        avg_females = total_females / 6
                        st.success(f"✅ Valid constraints. Average females per group: {avg_females:.1f}")
                        
                        if st.checkbox("Show detailed distribution preview"):
                            # Calculate expected distribution
                            base_females = [min_females] * 6
                            remaining = total_females - (min_females * 6)
                            for i in range(6):
                                if remaining > 0 and base_females[i] < max_females:
                                    add_count = min(remaining, max_females - base_females[i])
                                    base_females[i] += add_count
                                    remaining -= add_count
                            
                            preview_df = pd.DataFrame({
                                'Group': [f'Group {chr(65+i)}' for i in range(6)],
                                'Expected Females': base_females,
                                'Expected Males': [10 - f for f in base_females]
                            })
                            st.dataframe(preview_df, use_container_width=True)
            
            # Show subgroup options if selected
            if balance_strategy == "Skill-Level Subgroups":
                st.markdown("#### 🎯 Tournament Configuration")
                st.info("Configure the tournament structure, skill level ranges, and player counts")
                
                # Number of groups configuration
                num_groups = st.number_input(
                    "Number of Main Groups:", 
                    min_value=2, max_value=12, value=6, 
                    key="num_groups",
                    help="Total number of main groups to create (e.g., 6 creates Groups A-F)"
                )
                
                # Generate group labels dynamically
                group_labels = [f"Group {chr(65+i)}" for i in range(num_groups)]
                st.info(f"Will create: {', '.join(group_labels)}")
                
                # Gender distribution constraints
                st.markdown("#### 👥 Gender Distribution Settings")
                
                # Get current female player count
                total_females = len(st.session_state.player_database[st.session_state.player_database['gender'] == 'F'])
                total_males = len(st.session_state.player_database[st.session_state.player_database['gender'] == 'M'])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Female Players", total_females)
                with col2:
                    st.metric("Total Male Players", total_males)
                with col3:
                    st.metric("Total Players", total_females + total_males)
                
                # Gender constraint toggle
                use_gender_constraints = st.checkbox(
                    "Enable gender distribution constraints",
                    help="Control the number of female players per group"
                )
                
                if use_gender_constraints:
                    col1, col2 = st.columns(2)
                    with col1:
                        min_females_sg = st.number_input(
                            "Minimum females per group:",
                            min_value=0,
                            max_value=total_females // num_groups if total_females > 0 else 0,
                            value=max(0, total_females // num_groups if total_females > 0 else 0),
                            key="min_females_sg",
                            help="Minimum number of female players in each group"
                        )
                    with col2:
                        max_females_sg = st.number_input(
                            "Maximum females per group:",
                            min_value=min_females_sg,
                            max_value=15,
                            value=min(15, (total_females + num_groups-1) // num_groups if total_females > 0 else 0),
                            key="max_females_sg",
                            help="Maximum number of female players in each group"
                        )
                    
                    # Validation for gender constraints
                    if total_females > 0:
                        min_total_needed = min_females_sg * num_groups
                        max_total_capacity = max_females_sg * num_groups
                        
                        if min_total_needed > total_females:
                            st.error(f"❌ Minimum constraint too high: need {min_total_needed} females, but only have {total_females}")
                        elif max_total_capacity < total_females:
                            st.error(f"❌ Maximum constraint too low: can fit {max_total_capacity} females, but have {total_females}")
                        else:
                            st.success(f"✅ Valid gender constraints. Average females per group: {total_females/num_groups:.1f}")
                
                # Skill level ranges
                col1, col2 = st.columns(2)
                with col1:
                    subgroup1_name = st.session_state.subgroup_names.get('subgroup1', DEFAULT_SUBGROUP_NAMES['subgroup1'])
                    st.markdown(f"**{subgroup1_name}**")
                    subgroup1_min = st.number_input("Min Skill Level:", min_value=SKILL_LEVEL_MIN, max_value=SKILL_LEVEL_MAX, value=DEFAULT_DECIDERS_MIN, key="sg1_min")
                    subgroup1_max = st.number_input("Max Skill Level:", min_value=SKILL_LEVEL_MIN, max_value=SKILL_LEVEL_MAX, value=DEFAULT_DECIDERS_MAX, key="sg1_max")
                    
                with col2:
                    subgroup2_name = st.session_state.subgroup_names.get('subgroup2', DEFAULT_SUBGROUP_NAMES['subgroup2'])
                    st.markdown(f"**{subgroup2_name}**")
                    subgroup2_min = st.number_input("Min Skill Level:", min_value=SKILL_LEVEL_MIN, max_value=SKILL_LEVEL_MAX, value=DEFAULT_CHOKERS_MIN, key="sg2_min")
                    subgroup2_max = st.number_input("Max Skill Level:", min_value=SKILL_LEVEL_MIN, max_value=SKILL_LEVEL_MAX, value=DEFAULT_CHOKERS_MAX, key="sg2_max")
                
                # Player count configuration
                st.markdown("#### 📊 Player Count Configuration")
                st.info("Specify how many players should be in each subgroup across all groups")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    subgroup1_count = st.number_input(
                        f"Players per {subgroup1_name}:", 
                        min_value=1, max_value=15, value=5, 
                        key="sg1_count",
                        help=f"Number of players in each {subgroup1_name.lower()} across {num_groups} groups"
                    )
                with col2:
                    subgroup2_count = st.number_input(
                        f"Players per {subgroup2_name}:", 
                        min_value=1, max_value=15, value=5, 
                        key="sg2_count",
                        help=f"Number of players in each {subgroup2_name.lower()} across {num_groups} groups"
                    )
                with col3:
                    total_per_group = subgroup1_count + subgroup2_count
                    st.metric("Total per Group", total_per_group)
                    st.metric("Tournament Total", total_per_group * num_groups)
                
                # Validate ranges
                if subgroup1_max >= subgroup2_min:
                    st.warning(f"⚠️ Subgroup ranges should not overlap. Adjust the ranges so {subgroup1_name} max is less than {subgroup2_name} min.")
                
                # Show preview of player distribution
                if st.button("🔍 Preview Player Distribution"):
                    available_sg1 = len(st.session_state.player_database[
                        (st.session_state.player_database['skill_level'] >= subgroup1_min) & 
                        (st.session_state.player_database['skill_level'] <= subgroup1_max)
                    ])
                    available_sg2 = len(st.session_state.player_database[
                        (st.session_state.player_database['skill_level'] >= subgroup2_min) & 
                        (st.session_state.player_database['skill_level'] <= subgroup2_max)
                    ])
                    
                    needed_sg1 = subgroup1_count * num_groups
                    needed_sg2 = subgroup2_count * num_groups
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Available SG1", available_sg1)
                        if available_sg1 < needed_sg1:
                            st.error(f"Need {needed_sg1}, short by {needed_sg1 - available_sg1}")
                        else:
                            st.success(f"Sufficient (need {needed_sg1})")
                    
                    with col2:
                        st.metric("Available SG2", available_sg2)
                        if available_sg2 < needed_sg2:
                            st.error(f"Need {needed_sg2}, short by {needed_sg2 - available_sg2}")
                        else:
                            st.success(f"Sufficient (need {needed_sg2})")
                    
                    with col3:
                        total_available = available_sg1 + available_sg2
                        total_needed = needed_sg1 + needed_sg2
                        st.metric("Total Available", total_available)
                        
                    with col4:
                        st.metric("Total Needed", total_needed)
                        if total_available >= total_needed:
                            st.success("✓ Feasible")
                        else:
                            st.error(f"❌ Short by {total_needed - total_available}")
                    
                    if total_available > total_needed:
                        excess = total_available - total_needed
                        st.info(f"📈 {excess} players will not be assigned (excess players)")
            
            # Create balanced groups button (disabled when teams are locked)
            create_disabled = st.session_state.get("teams_locked", False)
            if create_disabled:
                st.warning("🔒 Teams are locked. Unlock on the **Team Details** page to create or reshuffle groups.")
            if st.button("🎯 Create Balanced Groups", type="primary", help="This will redistribute all players into balanced groups", disabled=create_disabled):
                with st.spinner("Creating balanced groups... This may take a moment."):
                    # Shuffle so each run produces different team assignments (balance algo is deterministic)
                    shuffled_players = st.session_state.player_database.sample(frac=1, random_state=None).reset_index(drop=True)
                    if balance_strategy == "Skill-Level Subgroups":
                        # Validate subgroup ranges
                        if subgroup1_max >= subgroup2_min:
                            st.error("❌ Please fix the subgroup ranges before proceeding.")
                            st.stop()
                        
                        try:
                            # Auto-balance with subgroups and gender constraints
                            gender_constraints = {}
                            if 'use_gender_constraints' in locals() and use_gender_constraints:
                                gender_constraints = {
                                    'min_females_per_group': min_females_sg,
                                    'max_females_per_group': max_females_sg
                                }
                            
                            balanced_groups, detailed_groups = auto_balance_subgroups(
                                shuffled_players, 
                                subgroup1_min, subgroup1_max, 
                                subgroup2_min, subgroup2_max,
                                subgroup1_count, subgroup2_count, num_groups,
                                **gender_constraints
                            )
                            
                            # Store detailed subgroup information for display
                            st.session_state.detailed_groups = detailed_groups
                            
                        except ValueError as e:
                            st.error(f"❌ {str(e)}")
                            st.info("💡 Use the 'Preview Player Distribution' button to check availability before balancing.")
                            st.stop()
                        
                    else:
                        # Use traditional auto-balance with gender constraints if specified
                        if balance_strategy == "Optimized Balance (Recommended)":
                            balanced_groups = auto_balance_groups(
                                shuffled_players,
                                min_females_per_group=min_females if 'min_females' in locals() else None,
                                max_females_per_group=max_females if 'max_females' in locals() else None
                            )
                        else:
                            balanced_groups = auto_balance_groups(shuffled_players)
                    
                    # Update session state for both strategies
                    st.session_state.groups = {}
                    updated_players = st.session_state.player_database.copy()
                    
                    for group_name, players_list in balanced_groups.items():
                        player_names = []
                        for player in players_list:
                            player_names.append(player['name'])
                            # Update player database with group assignment
                            mask = updated_players['name'] == player['name']
                            updated_players.loc[mask, 'group'] = group_name
                            updated_players.loc[mask, 'assigned'] = True
                        
                        st.session_state.groups[group_name] = player_names
                    
                    st.session_state.player_database = updated_players
                    
                    # Update standings to include new groups
                    st.session_state.standings = pd.DataFrame({
                        "Clash Wins": [0] * len(st.session_state.groups),
                        "Total Points": [0] * len(st.session_state.groups),
                    }, index=list(st.session_state.groups.keys()))
                    
                    # Store config so Reshuffle can reuse the same strategy and params
                    cfg = {"strategy": balance_strategy}
                    if balance_strategy == "Skill-Level Subgroups":
                        cfg.update({
                            "subgroup1_min": subgroup1_min, "subgroup1_max": subgroup1_max,
                            "subgroup2_min": subgroup2_min, "subgroup2_max": subgroup2_max,
                            "subgroup1_count": subgroup1_count, "subgroup2_count": subgroup2_count,
                            "num_groups": num_groups,
                            "use_gender_constraints": gender_constraints != {},
                            "min_females_sg": gender_constraints.get("min_females_per_group"),
                            "max_females_sg": gender_constraints.get("max_females_per_group"),
                        })
                    elif balance_strategy == "Optimized Balance (Recommended)":
                        cfg["min_females"] = min_females if 'min_females' in locals() else None
                        cfg["max_females"] = max_females if 'max_females' in locals() else None
                    st.session_state.last_balance_config = cfg
                    
                    auto_save()  # Auto-save after group balancing
                    st.success("🎉 Groups have been auto-balanced!")
                    st.balloons()
                    st.rerun()
        else:
            st.warning(f"⚠️ Need at least 60 players for auto-balancing. Currently have {len(st.session_state.player_database)} players.")
        
        # Show current group balance if groups exist
        if st.session_state.groups and any(st.session_state.groups.values()):
            st.divider()
            st.subheader("📊 Current Group Balance & Player Distribution")
            
            # Reshuffle option: re-run balance with last used config (disabled when teams are locked)
            reshuffle_disabled = st.session_state.get("teams_locked", False)
            cfg = st.session_state.get("last_balance_config")
            if st.button("🔀 Reshuffle teams", help="Redistribute players into new balanced groups using the same strategy as when teams were created", disabled=reshuffle_disabled):
                if not cfg:
                    st.warning("Reshuffle uses the last balance strategy. Create teams once with your preferred strategy, then use Reshuffle.")
                else:
                    with st.spinner("Reshuffling teams..."):
                        try:
                            # Shuffle player order so reshuffle produces different team assignments (balance algo is deterministic)
                            shuffled_players = st.session_state.player_database.sample(frac=1, random_state=None).reset_index(drop=True)
                            strategy = cfg.get("strategy", "Optimized Balance (Recommended)")
                            if strategy == "Skill-Level Subgroups":
                                gender_constraints = {}
                                if cfg.get("use_gender_constraints") and cfg.get("min_females_sg") is not None:
                                    gender_constraints = {
                                        "min_females_per_group": cfg["min_females_sg"],
                                        "max_females_per_group": cfg["max_females_sg"],
                                    }
                                balanced_groups, detailed_groups = auto_balance_subgroups(
                                    shuffled_players,
                                    cfg["subgroup1_min"], cfg["subgroup1_max"],
                                    cfg["subgroup2_min"], cfg["subgroup2_max"],
                                    cfg["subgroup1_count"], cfg["subgroup2_count"],
                                    cfg.get("num_groups", 6), **gender_constraints
                                )
                                st.session_state.detailed_groups = detailed_groups
                            else:
                                balanced_groups = auto_balance_groups(
                                    shuffled_players,
                                    min_females_per_group=cfg.get("min_females"),
                                    max_females_per_group=cfg.get("max_females")
                                )
                            
                            st.session_state.groups = {}
                            updated_players = st.session_state.player_database.copy()
                            for group_name, players_list in balanced_groups.items():
                                player_names = []
                                for player in players_list:
                                    player_names.append(player['name'])
                                    mask = updated_players['name'] == player['name']
                                    updated_players.loc[mask, 'group'] = group_name
                                    updated_players.loc[mask, 'assigned'] = True
                                st.session_state.groups[group_name] = player_names
                            
                            st.session_state.player_database = updated_players
                            st.session_state.standings = pd.DataFrame({
                                "Clash Wins": [0] * len(st.session_state.groups),
                                "Total Points": [0] * len(st.session_state.groups),
                            }, index=list(st.session_state.groups.keys()))
                            auto_save()
                            st.success("Teams reshuffled.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Reshuffle failed: {e}")
            
            # Collect balance data and player lists
            balance_data = []
            group_player_details = {}
            
            for group_name, player_names in st.session_state.groups.items():
                if player_names:
                    # Get player details for this group
                    group_players_df = st.session_state.player_database[
                        st.session_state.player_database['name'].isin(player_names)
                    ]
                    
                    if not group_players_df.empty:
                        # Store detailed player info for display
                        group_player_details[group_name] = group_players_df.sort_values('skill_level', ascending=False)
                        
                        stats = {
                            'Group': st.session_state.group_names.get(group_name, group_name),
                            'Players': len(group_players_df),
                            'Males': len(group_players_df[group_players_df['gender'] == 'M']),
                            'Females': len(group_players_df[group_players_df['gender'] == 'F']),
                            'Avg Skill': round(group_players_df['skill_level'].mean(), 2),
                            'Total Skill': group_players_df['skill_level'].sum(),
                            'Skill Range': f"{group_players_df['skill_level'].min()}-{group_players_df['skill_level'].max()}"
                        }
                        balance_data.append(stats)
            
            if balance_data:
                show_skill = st.session_state.get("show_skill_in_groups", True)
                # Display balance summary table
                balance_df = pd.DataFrame(balance_data)
                display_balance = balance_df.drop(columns=[c for c in ['Avg Skill', 'Total Skill', 'Skill Range'] if c in balance_df.columns], errors='ignore') if not show_skill else balance_df
                st.dataframe(display_balance, use_container_width=True)
                
                # Export all groups to Excel (one sheet per team, Deciders/Chokers separated)
                def _sanitize_sheet_name(name):
                    for c in r'\/:*?[]':
                        name = name.replace(c, " ")
                    return (name.strip() or "Sheet")[:31]
                
                if st.button("📗 Export all groups to Excel", key="export_excel_balance_page"):
                    try:
                        import io
                        buf = io.BytesIO()
                        has_subgroups = hasattr(st.session_state, 'detailed_groups') and st.session_state.detailed_groups
                        subgroup1_name = st.session_state.subgroup_names.get('subgroup1', DEFAULT_SUBGROUP_NAMES['subgroup1'])
                        subgroup2_name = st.session_state.subgroup_names.get('subgroup2', DEFAULT_SUBGROUP_NAMES['subgroup2'])
                        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                            if has_subgroups:
                                for group_name, subgroups in st.session_state.detailed_groups.items():
                                    sheet_name = _sanitize_sheet_name(st.session_state.group_names.get(group_name, group_name))
                                    rows = []
                                    rows.append([subgroup1_name])
                                    rows.append(["Name", "Gender", "Email", "Skill Level"])
                                    for p in subgroups["subgroup1"]["players"]:
                                        rows.append([p.get("name", ""), p.get("gender", ""), p.get("email", ""), p.get("skill_level", "")])
                                    rows.append([])
                                    rows.append([subgroup2_name])
                                    rows.append(["Name", "Gender", "Email", "Skill Level"])
                                    for p in subgroups["subgroup2"]["players"]:
                                        rows.append([p.get("name", ""), p.get("gender", ""), p.get("email", ""), p.get("skill_level", "")])
                                    pd.DataFrame(rows).to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                            else:
                                for group_name, player_names in st.session_state.groups.items():
                                    sheet_name = _sanitize_sheet_name(st.session_state.group_names.get(group_name, group_name))
                                    group_players_df = st.session_state.player_database[
                                        st.session_state.player_database["name"].isin(player_names)
                                    ]
                                    if not group_players_df.empty:
                                        cols = ["name", "gender", "email", "skill_level"]
                                        df = group_players_df[[c for c in cols if c in group_players_df.columns]].copy()
                                        df.columns = [c.replace("_", " ").title() for c in df.columns]
                                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                                    else:
                                        pd.DataFrame([["No player details"]]).to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                        buf.seek(0)
                        st.download_button(
                            label="💾 Download Excel",
                            data=buf.getvalue(),
                            file_name="teams_by_group.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_excel_balance"
                        )
                    except Exception as e:
                        st.error(f"Export failed: {e}")
                
                # Balance quality metrics
                if len(balance_data) > 1:
                    gender_balance = balance_df['Females'].std()
                    if show_skill:
                        skill_variance = balance_df['Total Skill'].var()
                        avg_variance = balance_df['Avg Skill'].var()
                        skill_range_val = balance_df['Total Skill'].max() - balance_df['Total Skill'].min()
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        if show_skill:
                            st.metric("Total Skill Variance", f"{skill_variance:.2f}", help="Lower is better (0 = perfectly balanced)")
                        else:
                            st.metric("Gender Balance Quality", f"{gender_balance:.2f}", help="Lower is better (more even distribution)")
                    with col2:
                        if show_skill:
                            st.metric("Avg Skill Variance", f"{avg_variance:.3f}", help="Lower is better")
                        else:
                            st.empty()
                    with col3:
                        if show_skill:
                            st.metric("Gender Balance Quality", f"{gender_balance:.2f}", help="Lower is better (more even distribution)")
                        else:
                            st.empty()
                    with col4:
                        if show_skill:
                            st.metric("Skill Point Range", f"{skill_range_val}", help="Difference between strongest and weakest group")
                        else:
                            st.empty()
                
                # Show subgroup breakdown if detailed groups exist
                if hasattr(st.session_state, 'detailed_groups') and st.session_state.detailed_groups:
                    st.divider()
                    st.subheader("🎯 Subgroup Distribution Analysis")
                    subgroup1_name = st.session_state.subgroup_names.get('subgroup1', DEFAULT_SUBGROUP_NAMES['subgroup1'])
                    subgroup2_name = st.session_state.subgroup_names.get('subgroup2', DEFAULT_SUBGROUP_NAMES['subgroup2'])
                    st.info(f"Breakdown of players by skill-level subgroups ({subgroup1_name} & {subgroup2_name}) within each group")
                    
                    subgroup_data = []
                    for group_name, subgroups in st.session_state.detailed_groups.items():
                        # Subgroup 1 stats
                        sg1_players = subgroups['subgroup1']['players']
                        if sg1_players:
                            sg1_stats = {
                                'Group': f"{st.session_state.group_names.get(group_name, group_name)} - {st.session_state.subgroup_names.get('subgroup1', DEFAULT_SUBGROUP_NAMES['subgroup1'])}",
                                'Subgroup': st.session_state.subgroup_names.get('subgroup1', DEFAULT_SUBGROUP_NAMES['subgroup1']),
                                'Players': len(sg1_players),
                                'Males': subgroups['subgroup1']['male_count'],
                                'Females': subgroups['subgroup1']['female_count'],
                                'Avg Skill': round(sum(p['skill_level'] for p in sg1_players) / len(sg1_players), 2),
                                'Total Skill': subgroups['subgroup1']['total_skill'],
                                'Skill Range': f"{min(p['skill_level'] for p in sg1_players)}-{max(p['skill_level'] for p in sg1_players)}"
                            }
                            subgroup_data.append(sg1_stats)
                        
                        # Subgroup 2 stats  
                        sg2_players = subgroups['subgroup2']['players']
                        if sg2_players:
                            sg2_stats = {
                                'Group': f"{st.session_state.group_names.get(group_name, group_name)} - {st.session_state.subgroup_names.get('subgroup2', DEFAULT_SUBGROUP_NAMES['subgroup2'])}",
                                'Subgroup': st.session_state.subgroup_names.get('subgroup2', DEFAULT_SUBGROUP_NAMES['subgroup2']),
                                'Players': len(sg2_players),
                                'Males': subgroups['subgroup2']['male_count'],
                                'Females': subgroups['subgroup2']['female_count'],
                                'Avg Skill': round(sum(p['skill_level'] for p in sg2_players) / len(sg2_players), 2),
                                'Total Skill': subgroups['subgroup2']['total_skill'],
                                'Skill Range': f"{min(p['skill_level'] for p in sg2_players)}-{max(p['skill_level'] for p in sg2_players)}"
                            }
                            subgroup_data.append(sg2_stats)
                    
                    if subgroup_data:
                        subgroup_df = pd.DataFrame(subgroup_data)
                        skill_cols = [c for c in ['Avg Skill', 'Total Skill', 'Skill Range'] if c in subgroup_df.columns]
                        display_subgroup = subgroup_df.drop(columns=skill_cols, errors='ignore') if not show_skill else subgroup_df
                        st.dataframe(display_subgroup, use_container_width=True)
                        
                        # Subgroup balance metrics (only when showing skill)
                        if show_skill:
                            subgroup1_name = st.session_state.subgroup_names.get('subgroup1', DEFAULT_SUBGROUP_NAMES['subgroup1'])
                            subgroup2_name = st.session_state.subgroup_names.get('subgroup2', DEFAULT_SUBGROUP_NAMES['subgroup2'])
                            sg1_data = [row for row in subgroup_data if subgroup1_name in row['Subgroup']]
                            sg2_data = [row for row in subgroup_data if subgroup2_name in row['Subgroup']]
                            if sg1_data and sg2_data:
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown(f"**{subgroup1_name} Balance**")
                                    sg1_df = pd.DataFrame(sg1_data)
                                    sg1_variance = sg1_df['Total Skill'].var()
                                    sg1_range = sg1_df['Total Skill'].max() - sg1_df['Total Skill'].min()
                                    st.metric("Skill Variance", f"{sg1_variance:.2f}")
                                    st.metric("Skill Range", f"{sg1_range}")
                                with col2:
                                    st.markdown(f"**{subgroup2_name} Balance**")
                                    sg2_df = pd.DataFrame(sg2_data)
                                    sg2_variance = sg2_df['Total Skill'].var()
                                    sg2_range = sg2_df['Total Skill'].max() - sg2_df['Total Skill'].min()
                                    st.metric("Skill Variance", f"{sg2_variance:.2f}")
                                    st.metric("Skill Range", f"{sg2_range}")
                
                # Detailed Player Distribution
                st.subheader("👥 Detailed Player Distribution")
                st.info("Players in each group, sorted by skill level (highest to lowest)")
                
                # Create tabs for each group
                if group_player_details:
                    # Create tabs with group display names (and skill points when showing skill)
                    tab_labels = []
                    for group_name in group_player_details.keys():
                        display_name = st.session_state.group_names.get(group_name, group_name)
                        if show_skill:
                            matching_balance = balance_df[balance_df['Group'] == display_name]
                            if not matching_balance.empty:
                                total_skill = matching_balance['Total Skill'].iloc[0]
                                tab_labels.append(f"{display_name} ({total_skill} pts)")
                            else:
                                tab_labels.append(display_name)
                        else:
                            tab_labels.append(display_name)
                    
                    group_tabs = st.tabs(tab_labels)
                    
                    for tab, (group_name, players_df) in zip(group_tabs, group_player_details.items()):
                        with tab:
                            # Group statistics - use display name to find balance data
                            display_name = st.session_state.group_names.get(group_name, group_name)
                            group_stats = next((x for x in balance_data if x['Group'] == display_name), None)
                            
                            if group_stats:
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Total Players", group_stats['Players'])
                                with col2:
                                    st.metric("Males/Females", f"{group_stats['Males']}/{group_stats['Females']}")
                                if show_skill:
                                    with col3:
                                        st.metric("Average Skill", group_stats['Avg Skill'])
                                    with col4:
                                        st.metric("Total Skill Points", group_stats['Total Skill'])
                                
                                # Player list with details
                                st.markdown("**Players:**")
                                
                                def _player_line(player, idx, show_skill_level):
                                    gender_icon = "👨" if player['gender'] == 'M' else "👩"
                                    if show_skill_level:
                                        skill_stars = "⭐" * min(player.get('skill_level', 0), 15)
                                        return f"  {idx}. {gender_icon} **{player['name']}** (Skill: {player.get('skill_level', '')} {skill_stars}) - {player['email']}"
                                    return f"  {idx}. {gender_icon} **{player['name']}** - {player['email']}"
                                
                                # Show subgroup breakdown if available
                                if hasattr(st.session_state, 'detailed_groups') and st.session_state.detailed_groups and group_name in st.session_state.detailed_groups:
                                    subgroups = st.session_state.detailed_groups[group_name]
                                    
                                    # Subgroup 1
                                    if subgroups['subgroup1']['players']:
                                        subgroup1_name = st.session_state.subgroup_names.get('subgroup1', DEFAULT_SUBGROUP_NAMES['subgroup1'])
                                        st.markdown(f"***🔽 {subgroup1_name} ({len(subgroups['subgroup1']['players'])} players)***")
                                        for idx, player in enumerate(subgroups['subgroup1']['players'], 1):
                                            st.write(_player_line(player, idx, show_skill))
                                    
                                    # Subgroup 2
                                    if subgroups['subgroup2']['players']:
                                        subgroup2_name = st.session_state.subgroup_names.get('subgroup2', DEFAULT_SUBGROUP_NAMES['subgroup2'])
                                        st.markdown(f"***🔼 {subgroup2_name} ({len(subgroups['subgroup2']['players'])} players)***")
                                        for idx, player in enumerate(subgroups['subgroup2']['players'], 1):
                                            st.write(_player_line(player, idx, show_skill))
                                else:
                                    # Regular display without subgroups
                                    for idx, (_, player) in enumerate(players_df.iterrows(), 1):
                                        p = player.to_dict()
                                        gender_icon = "👨" if p.get('gender') == 'M' else "👩"
                                        if show_skill:
                                            skill_stars = "⭐" * min(p.get('skill_level', 0), 15)
                                            st.write(f"{idx}. {gender_icon} **{p['name']}** (Skill: {p['skill_level']} {skill_stars}) - {p['email']}")
                                        else:
                                            st.write(f"{idx}. {gender_icon} **{p['name']}** - {p['email']}")
                            else:
                                st.warning(f"No balance data found for {display_name}")
                
                # Summary statistics
                st.divider()
                st.subheader("📈 Balance Summary")
                
                if len(balance_data) >= 6:
                    total_players = sum(stats['Players'] for stats in balance_data)
                    total_males = sum(stats['Males'] for stats in balance_data)
                    total_females = sum(stats['Females'] for stats in balance_data)
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Tournament Players", total_players, "Target: 60")
                    with col2:
                        st.metric("Gender Distribution", f"{total_males}M / {total_females}F")
                    if show_skill:
                        total_skill = sum(stats['Total Skill'] for stats in balance_data)
                        avg_group_skill = total_skill / 6
                        with col3:
                            st.metric("Target Group Skill", f"{avg_group_skill:.1f}", "All groups should be close to this")
                        max_skill_diff = max(stats['Total Skill'] for stats in balance_data) - min(stats['Total Skill'] for stats in balance_data)
                    else:
                        with col3:
                            st.empty()
                    
                    # Balance quality assessment (only when showing skill)
                    if show_skill:
                        max_skill_diff = max(stats['Total Skill'] for stats in balance_data) - min(stats['Total Skill'] for stats in balance_data)
                        if max_skill_diff <= 5:
                            st.success("✅ Excellent balance! Groups are very evenly matched.")
                        elif max_skill_diff <= 10:
                            st.info("ℹ️ Good balance. Groups are reasonably matched.")
                        elif max_skill_diff <= 15:
                            st.warning("⚠️ Fair balance. Consider re-balancing for better competition.")
                        else:
                            st.error("❌ Poor balance. Re-balancing strongly recommended.")
    else:
        st.info("No players in database. Import some players to get started!")

# --- TAB 2: SETUP GROUPS & PLAYERS ---
elif menu == "Setup Groups & Players":
    st.header("🎯 Tournament Setup")
    st.markdown("Configure your tournament groups and add all participants.")
    
    # Group Names Setup
    st.subheader("🏷️ Group Names Configuration")
    st.info("Give meaningful names to your groups (e.g., 'Team Thunder', 'Eagles Squad', etc.)")
    
    col1, col2, col3 = st.columns(3)
    
    # Display group name inputs in columns
    for i, (group_key, current_name) in enumerate(st.session_state.group_names.items()):
        col = [col1, col2, col3][i % 3]
        with col:
            new_name = st.text_input(f"Group {chr(65+i)} Name:", value=current_name, key=f"group_name_{i}")
            if new_name.strip() and new_name != current_name:
                # Update group name and transfer data
                old_key = group_key
                st.session_state.group_names[old_key] = new_name
                
                # Update groups dictionary with new name if it exists
                if hasattr(st.session_state, 'groups') and st.session_state.groups is not None:
                    if old_key in st.session_state.groups:
                        st.session_state.groups[new_name] = st.session_state.groups.pop(old_key)
                
                # Update standings dataframe if it exists
                if hasattr(st.session_state, 'standings') and st.session_state.standings is not None:
                    if old_key in st.session_state.standings.index:
                        st.session_state.standings = st.session_state.standings.rename(index={old_key: new_name})
                
                # Auto-save configuration changes
                auto_save()
    
    # Subgroup Names Configuration
    st.subheader("🏷️ Subgroup Names Configuration")
    st.info("Define names for subgroups used in 'Skill-Level Subgroups' balance strategy (e.g., 'Defenders', 'Attackers' or 'Juniors', 'Seniors')")
    
    # Initialize subgroup names if not exists
    if 'subgroup_names' not in st.session_state:
        st.session_state.subgroup_names = DEFAULT_SUBGROUP_NAMES.copy()
    
    col1, col2 = st.columns(2)
    with col1:
        subgroup1_name = st.text_input(
            "Subgroup 1 Name (Deciders):", 
            value=st.session_state.subgroup_names['subgroup1'], 
            key="subgroup1_name",
            help="Default: Deciders (0-5). Used for the lower skill subgroup across all groups."
        )
        if subgroup1_name.strip() and subgroup1_name != st.session_state.subgroup_names['subgroup1']:
            st.session_state.subgroup_names['subgroup1'] = subgroup1_name.strip()
            auto_save()  # Auto-save subgroup name changes
    
    with col2:
        subgroup2_name = st.text_input(
            "Subgroup 2 Name (Chokers):", 
            value=st.session_state.subgroup_names['subgroup2'], 
            key="subgroup2_name",
            help="Default: Chokers (6-15). Used for the higher skill subgroup across all groups."
        )
        if subgroup2_name.strip() and subgroup2_name != st.session_state.subgroup_names['subgroup2']:
            st.session_state.subgroup_names['subgroup2'] = subgroup2_name.strip()
            auto_save()  # Auto-save subgroup name changes

    # Save confirmation section
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("💾 Save All Names Configuration", type="primary", use_container_width=True):
            auto_save()
            st.success("✅ All group and subgroup names saved successfully!")
            st.balloons()

    st.divider()
    
    # Players Setup
    st.subheader("👥 Players Configuration")
    st.info("Add 10 players to each group. You can copy-paste names or enter them manually.")
    
    # Create tabs for each group
    group_tabs = st.tabs([st.session_state.group_names[f"Group {chr(65+i)}"] for i in range(6)])
    
    for i, tab in enumerate(group_tabs):
        group_key = f"Group {chr(65+i)}"
        group_name = st.session_state.group_names[group_key]
        
        with tab:
            st.markdown(f"### Players for {group_name}")
            
            # Option 1: Bulk input
            with st.expander("📋 Bulk Add Players (Recommended)"):
                bulk_text = st.text_area(
                    "Enter all 10 players (one per line or comma-separated):",
                    value="\n".join(st.session_state.groups.get(group_name, [])),
                    height=200,
                    key=f"bulk_{i}"
                )
                
                if st.button(f"Update {group_name} Players", key=f"bulk_btn_{i}"):
                    # Parse input - handle both newline and comma separation
                    if "\n" in bulk_text:
                        players = [p.strip() for p in bulk_text.split("\n") if p.strip()]
                    else:
                        players = [p.strip() for p in bulk_text.split(",") if p.strip()]
                    
                    # Ensure exactly 10 players
                    players = players[:10]  # Take first 10
                    while len(players) < 10:
                        players.append(f"Player {len(players)+1}")
                    
                    st.session_state.groups[group_name] = players
                    st.success(f"Updated {len(players)} players for {group_name}!")
                    st.rerun()
            
            # Option 2: Individual input fields
            with st.expander("✏️ Edit Individual Players"):
                current_players = st.session_state.groups.get(group_name, [f"Player {j+1}" for j in range(10)])
                updated_players = []
                
                col_a, col_b = st.columns(2)
                for j in range(10):
                    col = col_a if j < 5 else col_b
                    with col:
                        player_name = st.text_input(
                            f"Player {j+1}:",
                            value=current_players[j] if j < len(current_players) else f"Player {j+1}",
                            key=f"player_{i}_{j}"
                        )
                        updated_players.append(player_name.strip() or f"Player {j+1}")
                
                if st.button(f"Save Individual Changes for {group_name}", key=f"individual_btn_{i}"):
                    st.session_state.groups[group_name] = updated_players
                    st.success(f"Saved individual player changes for {group_name}!")
                    st.rerun()
            
            # Current players preview
            st.markdown("**Current Players:**")
            current_list = st.session_state.groups.get(group_name, [])
            if current_list:
                for idx, player in enumerate(current_list, 1):
                    st.write(f"{idx}. {player}")
            else:
                st.write("No players added yet.")
    
    # Tournament Status
    st.divider()
    st.subheader("📊 Tournament Status")
    total_players = sum(len(players) for players in st.session_state.groups.values())
    st.metric("Total Players Registered", total_players, f"Target: 60")
    
    if total_players == 60:
        st.success("✅ Tournament setup complete! All groups have 10 players each.")
        st.balloons()
    elif total_players < 60:
        st.warning(f"⚠️ Need {60-total_players} more players to complete setup.")
    else:
        st.error(f"❌ Too many players! Remove {total_players-60} players.")

# --- TAB 3: TEAM DETAILS ---
elif menu == "Team Details":
    st.header("👥 Team Details & Subgroup Breakdown")
    st.markdown("Detailed view of all teams with player distribution")
    
    # Debug info at top (can be hidden with expander)
    with st.expander("🔧 Debug Info", expanded=False):
        st.write("**Groups exist:**", bool(st.session_state.groups))
        st.write("**Groups have players:**", any(st.session_state.groups.values()) if st.session_state.groups else False)
        st.write("**Detailed groups exist:**", hasattr(st.session_state, 'detailed_groups'))
        if hasattr(st.session_state, 'detailed_groups'):
            st.write("**Detailed groups populated:**", bool(st.session_state.detailed_groups))
            if st.session_state.detailed_groups:
                st.write("**Detailed groups keys:**", list(st.session_state.detailed_groups.keys()))
    
    if not st.session_state.groups or not any(st.session_state.groups.values()):
        st.info("📝 No teams have been created yet. Please go to 'Player Import & Auto-Balance' to create teams first.")
    else:
        # Guest: hide skill level in team details
        _guest_hide_skill = not is_authenticated()
        # Check if subgroup data exists
        has_subgroups = hasattr(st.session_state, 'detailed_groups') and st.session_state.detailed_groups
        
        if has_subgroups:
            st.success("🎯 **Skill-Level Subgroups Active** - Teams are organized by skill ranges")
            
            # More prominent subgroup info
            subgroup1_name = st.session_state.subgroup_names.get('subgroup1', DEFAULT_SUBGROUP_NAMES['subgroup1'])
            subgroup2_name = st.session_state.subgroup_names.get('subgroup2', DEFAULT_SUBGROUP_NAMES['subgroup2'])
            
            st.info(f"📋 **Your Subgroups:** {subgroup1_name} and {subgroup2_name}")
            
            # Subgroup summary
            st.subheader("📊 Subgroup Overview")
            subgroup_summary = []
            
            for group_name, subgroups in st.session_state.detailed_groups.items():
                sg1_data = subgroups['subgroup1']
                sg2_data = subgroups['subgroup2']
                
                # Use custom group name for display
                display_group_name = st.session_state.group_names.get(group_name, group_name)
                
                summary = {
                    'Group': display_group_name,
                    f'{subgroup1_name} Players': len(sg1_data['players']),
                    f'{subgroup1_name} Males': sg1_data['male_count'],
                    f'{subgroup1_name} Females': sg1_data['female_count'],
                    f'{subgroup2_name} Players': len(sg2_data['players']),
                    f'{subgroup2_name} Males': sg2_data['male_count'], 
                    f'{subgroup2_name} Females': sg2_data['female_count'],
                    'Total Players': len(sg1_data['players']) + len(sg2_data['players'])
                }
                subgroup_summary.append(summary)
            
            # Display subgroup summary table
            summary_df = pd.DataFrame(subgroup_summary)
            st.dataframe(summary_df, use_container_width=True)
            
            # Detailed team breakdown
            st.subheader("🔍 Detailed Team Breakdown by Subgroups")
            st.info(f"Click on each team tab to see players organized by {subgroup1_name} and {subgroup2_name}")
            
            # Create tabs for each group using custom names
            group_display_names = [st.session_state.group_names.get(group_name, group_name) for group_name in st.session_state.detailed_groups.keys()]
            group_tabs = st.tabs(group_display_names)
            
            for tab, (group_name, subgroups) in zip(group_tabs, st.session_state.detailed_groups.items()):
                with tab:
                    display_group_name = st.session_state.group_names.get(group_name, group_name)
                    st.markdown(f"### {display_group_name} - Complete Roster")
                    
                    # Group statistics
                    total_players = len(subgroups['subgroup1']['players']) + len(subgroups['subgroup2']['players'])
                    total_males = subgroups['subgroup1']['male_count'] + subgroups['subgroup2']['male_count']
                    total_females = subgroups['subgroup1']['female_count'] + subgroups['subgroup2']['female_count']
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Players", total_players)
                    with col2:
                        st.metric("Males", total_males)
                    with col3:
                        st.metric("Females", total_females)
                    
                    # Subgroup breakdown with enhanced display
                    st.markdown("---")
                    st.markdown(f"### 🎯 Subgroup Organization")
                    show_skill_team = False if _guest_hide_skill else st.session_state.get("show_skill_in_groups", True)
                    col1, col2 = st.columns(2)
                    
                    # Subgroup 1
                    with col1:
                        st.markdown(f"#### 🔽 {subgroup1_name}")
                        sg1_players = subgroups['subgroup1']['players']
                        if sg1_players:
                            sg1_metrics_col1, sg1_metrics_col2 = st.columns(2)
                            with sg1_metrics_col1:
                                st.metric("Players", len(sg1_players))
                                st.metric("Males", subgroups['subgroup1']['male_count'])
                            with sg1_metrics_col2:
                                st.metric("Females", subgroups['subgroup1']['female_count'])
                            
                            st.markdown("**🏸 Players:**")
                            for i, player in enumerate(sg1_players, 1):
                                gender_icon = "👨" if player['gender'] == 'M' else "👩"
                                if show_skill_team:
                                    skill_stars = "⭐" * min(player.get('skill_level', 0), 15)
                                    st.write(f"{i}. {gender_icon} **{player['name']}** (Skill: {player.get('skill_level', '')} {skill_stars})")
                                else:
                                    st.write(f"{i}. {gender_icon} **{player['name']}**")
                        else:
                            st.info(f"No players in {subgroup1_name}")
                    
                    # Subgroup 2
                    with col2:
                        st.markdown(f"#### 🔼 {subgroup2_name}")
                        sg2_players = subgroups['subgroup2']['players']
                        if sg2_players:
                            sg2_metrics_col1, sg2_metrics_col2 = st.columns(2)
                            with sg2_metrics_col1:
                                st.metric("Players", len(sg2_players))
                                st.metric("Males", subgroups['subgroup2']['male_count'])
                            with sg2_metrics_col2:
                                st.metric("Females", subgroups['subgroup2']['female_count'])
                            
                            st.markdown("**🏸 Players:**")
                            for i, player in enumerate(sg2_players, 1):
                                gender_icon = "👨" if player['gender'] == 'M' else "👩"
                                if show_skill_team:
                                    skill_stars = "⭐" * min(player.get('skill_level', 0), 15)
                                    st.write(f"{i}. {gender_icon} **{player['name']}** (Skill: {player.get('skill_level', '')} {skill_stars})")
                                else:
                                    st.write(f"{i}. {gender_icon} **{player['name']}**")
                        else:
                            st.info(f"No players in {subgroup2_name}")
        
        else:
            st.info("🎯 **Standard Groups** - Teams created without skill-level subgroups")
            
            # Add instructions for getting subgroups
            with st.expander("💡 Want to see teams organized by skill subgroups?", expanded=False):
                st.markdown("""
                To see players organized by skill subgroups:
                1. Go to **'Player Import & Auto-Balance'** tab
                2. Select **'Skill-Level Subgroups'** balance strategy
                3. Configure your skill ranges and subgroup names
                4. Create balanced groups
                5. Return to this page to see subgroup organization
                """)
            
            # Standard group display
            st.subheader("👥 Team Roster")
            
            # Group summary
            group_summary = []
            for group_name, players in st.session_state.groups.items():
                if players:
                    # Get player details from database
                    group_players_df = st.session_state.player_database[
                        st.session_state.player_database['name'].isin(players)
                    ]
                    
                    if not group_players_df.empty:
                        summary = {
                            'Group': st.session_state.group_names.get(group_name, group_name),
                            'Total Players': len(group_players_df),
                            'Males': len(group_players_df[group_players_df['gender'] == 'M']),
                            'Females': len(group_players_df[group_players_df['gender'] == 'F'])
                        }
                        group_summary.append(summary)
            
            if group_summary:
                summary_df = pd.DataFrame(group_summary)
                st.dataframe(summary_df, use_container_width=True)
            
            # Detailed team breakdown
            st.subheader("🔍 Detailed Team Breakdown")
            
            group_tabs = st.tabs([st.session_state.group_names.get(group_name, group_name) for group_name in st.session_state.groups.keys()])
            
            for tab, (group_name, players) in zip(group_tabs, st.session_state.groups.items()):
                with tab:
                    display_group_name = st.session_state.group_names.get(group_name, group_name)
                    st.markdown(f"### {display_group_name} - Complete Roster")
                    
                    if players:
                        # Get player details
                        group_players_df = st.session_state.player_database[
                            st.session_state.player_database['name'].isin(players)
                        ]
                        
                        if not group_players_df.empty:
                            # Group statistics
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Total Players", len(group_players_df))
                            with col2:
                                males = len(group_players_df[group_players_df['gender'] == 'M'])
                                st.metric("Males", males)
                            with col3:
                                females = len(group_players_df[group_players_df['gender'] == 'F'])
                                st.metric("Females", females)
                            
                            # Player list
                            st.markdown("#### 📋 Players")
                            show_skill_team = False if _guest_hide_skill else st.session_state.get("show_skill_in_groups", True)
                            for i, (_, player) in enumerate(group_players_df.iterrows(), 1):
                                gender_icon = "👨" if player['gender'] == 'M' else "👩"
                                if show_skill_team and 'skill_level' in group_players_df.columns:
                                    skill_stars = "⭐" * min(int(player.get('skill_level', 0)), 15)
                                    st.write(f"{i}. {gender_icon} **{player['name']}** (Skill: {player['skill_level']} {skill_stars}) - {player['email']}")
                                else:
                                    st.write(f"{i}. {gender_icon} **{player['name']}** - {player['email']}")
                        else:
                            st.warning("No player details found in database")
                    else:
                        st.info("No players assigned to this group")
        
        # Lock teams and Export functionality
        st.divider()
        st.subheader("🔒 Lock & Export")
        
        # Lock / Unlock teams
        teams_locked = st.session_state.get("teams_locked", False)
        lock_col, msg_col = st.columns([1, 3])
        with lock_col:
            if teams_locked:
                if st.button("🔓 Unlock teams", key="unlock_teams_btn"):
                    st.session_state.teams_locked = False
                    st.rerun()
                st.success("Teams are **locked**. Create/Reshuffle disabled on Player Import.")
            else:
                if st.button("🔒 Lock teams", key="lock_teams_btn"):
                    st.session_state.teams_locked = True
                    st.rerun()
                st.info("Lock teams to prevent changes, then export to Excel.")
        
        st.markdown("---")
        st.markdown("**Export options**")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📊 Export Team Summary"):
                if has_subgroups and subgroup_summary:
                    summary_csv = pd.DataFrame(subgroup_summary).to_csv(index=False)
                    st.download_button(
                        label="💾 Download Subgroup Summary CSV",
                        data=summary_csv,
                        file_name="team_subgroup_summary.csv",
                        mime="text/csv"
                    )
                elif group_summary:
                    summary_csv = pd.DataFrame(group_summary).to_csv(index=False)
                    st.download_button(
                        label="💾 Download Team Summary CSV",
                        data=summary_csv,
                        file_name="team_summary.csv",
                        mime="text/csv"
                    )
        
        with col2:
            # Export to Excel: one sheet per team, Deciders then Chokers
            def _sanitize_sheet_name(name):
                for c in r'\/:*?[]':
                    name = name.replace(c, " ")
                return (name.strip() or "Sheet")[:31]
            
            if st.button("📗 Export to Excel (teams + subgroups)"):
                try:
                    import io
                    buf = io.BytesIO()
                    subgroup1_name = st.session_state.subgroup_names.get('subgroup1', DEFAULT_SUBGROUP_NAMES['subgroup1'])
                    subgroup2_name = st.session_state.subgroup_names.get('subgroup2', DEFAULT_SUBGROUP_NAMES['subgroup2'])
                    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                        if has_subgroups and st.session_state.detailed_groups:
                            for group_name, subgroups in st.session_state.detailed_groups.items():
                                sheet_name = _sanitize_sheet_name(st.session_state.group_names.get(group_name, group_name))
                                rows = []
                                # Deciders section
                                rows.append([subgroup1_name])
                                rows.append(["Name", "Gender", "Email", "Skill Level"])
                                for p in subgroups["subgroup1"]["players"]:
                                    rows.append([p.get("name", ""), p.get("gender", ""), p.get("email", ""), p.get("skill_level", "")])
                                rows.append([])
                                # Chokers section
                                rows.append([subgroup2_name])
                                rows.append(["Name", "Gender", "Email", "Skill Level"])
                                for p in subgroups["subgroup2"]["players"]:
                                    rows.append([p.get("name", ""), p.get("gender", ""), p.get("email", ""), p.get("skill_level", "")])
                                pd.DataFrame(rows).to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                        else:
                            for group_name, players in st.session_state.groups.items():
                                sheet_name = _sanitize_sheet_name(st.session_state.group_names.get(group_name, group_name))
                                group_players_df = st.session_state.player_database[
                                    st.session_state.player_database["name"].isin(players)
                                ]
                                if not group_players_df.empty:
                                    cols = ["name", "gender", "email", "skill_level"]
                                    df = group_players_df[[c for c in cols if c in group_players_df.columns]].copy()
                                    df.columns = [c.replace("_", " ").title() for c in df.columns]
                                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                                else:
                                    pd.DataFrame([["No player details"]]).to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                    buf.seek(0)
                    st.download_button(
                        label="💾 Download Excel",
                        data=buf.getvalue(),
                        file_name="teams_by_group.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.error(f"Export failed: {e}")
        
        with col3:
            if st.button("👥 Export Detailed Roster"):
                detailed_roster = []
                
                if has_subgroups:
                    subgroup1_name = st.session_state.subgroup_names.get('subgroup1', DEFAULT_SUBGROUP_NAMES['subgroup1'])
                    subgroup2_name = st.session_state.subgroup_names.get('subgroup2', DEFAULT_SUBGROUP_NAMES['subgroup2'])
                    
                    for group_name, subgroups in st.session_state.detailed_groups.items():
                        display_group_name = st.session_state.group_names.get(group_name, group_name)
                        for sg_type, sg_data, sg_name in [('subgroup1', subgroups['subgroup1'], subgroup1_name), ('subgroup2', subgroups['subgroup2'], subgroup2_name)]:
                            for player in sg_data['players']:
                                detailed_roster.append({
                                    'Group': display_group_name,
                                    'Subgroup': sg_name,
                                    'Player': player['name'],
                                    'Gender': player['gender'],
                                    'Email': player.get('email', '')
                                })
                else:
                    for group_name, players in st.session_state.groups.items():
                        group_players_df = st.session_state.player_database[
                            st.session_state.player_database['name'].isin(players)
                        ]
                        for _, player in group_players_df.iterrows():
                            detailed_roster.append({
                                'Group': group_name,
                                'Subgroup': 'All',
                                'Player': player['name'],
                                'Gender': player['gender'],
                                'Email': player['email']
                            })
                
                if detailed_roster:
                    roster_csv = pd.DataFrame(detailed_roster).to_csv(index=False)
                    st.download_button(
                        label="💾 Download Detailed Roster CSV",
                        data=roster_csv,
                        file_name="detailed_team_roster.csv",
                        mime="text/csv"
                    )

# --- TAB 4: MATCH SCHEDULE ---
elif menu == "Match Schedule":
    st.header("📅 Match Schedule Generator")
    st.markdown("Create optimized tournament schedule based on available courts and time slots.")
    
    # Initialize schedule state
    if 'tournament_schedule' not in st.session_state:
        st.session_state.tournament_schedule = []
    if 'schedule_config' not in st.session_state:
        st.session_state.schedule_config = {
            'courts': 4,
            'match_duration': 25,
            'break_duration': 5,
            'start_time': '09:00',
            'end_time': '18:00',
            'dates': []
        }
    
    # Check if groups are set up
    if not st.session_state.groups or not any(st.session_state.groups.values()):
        st.warning("⚠️ Please set up groups first in the 'Setup Groups & Players' tab before creating schedules.")
        st.stop()
    
    # Schedule Configuration
    st.subheader("⚙️ Tournament Configuration")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        num_courts = st.number_input(
            "Number of Courts Available:",
            min_value=1,
            max_value=20,
            value=st.session_state.schedule_config['courts'],
            help="Total badminton courts available for the tournament"
        )
        st.session_state.schedule_config['courts'] = num_courts
    
    with col2:
        match_duration = st.number_input(
            "Match Duration (minutes):",
            min_value=15,
            max_value=60,
            value=st.session_state.schedule_config['match_duration'],
            help="Duration of each doubles match including setup"
        )
        st.session_state.schedule_config['match_duration'] = match_duration
    
    with col3:
        break_duration = st.number_input(
            "Break Between Matches (minutes):",
            min_value=0,
            max_value=30,
            value=st.session_state.schedule_config['break_duration'],
            help="Rest time between consecutive matches"
        )
        st.session_state.schedule_config['break_duration'] = break_duration
    
    # Time Configuration
    col1, col2 = st.columns(2)
    
    with col1:
        start_time = st.time_input(
            "Tournament Start Time:",
            value=pd.to_datetime(st.session_state.schedule_config['start_time']).time(),
            help="Daily tournament start time"
        )
        st.session_state.schedule_config['start_time'] = start_time.strftime('%H:%M')
    
    with col2:
        end_time = st.time_input(
            "Tournament End Time:",
            value=pd.to_datetime(st.session_state.schedule_config['end_time']).time(),
            help="Daily tournament end time"
        )
        st.session_state.schedule_config['end_time'] = end_time.strftime('%H:%M')
    
    # Date Configuration
    st.subheader("📅 Tournament Dates")
    
    col1, col2 = st.columns(2)
    
    with col1:
        tournament_start_date = st.date_input(
            "Tournament Start Date:",
            value=pd.Timestamp.now().date(),
            help="First day of the tournament"
        )
    
    with col2:
        tournament_days = st.number_input(
            "Number of Tournament Days:",
            min_value=1,
            max_value=14,
            value=3,
            help="Total days for the tournament"
        )
    
    # Generate date list
    tournament_dates = [tournament_start_date + pd.Timedelta(days=i) for i in range(tournament_days)]
    st.session_state.schedule_config['dates'] = [date.strftime('%Y-%m-%d') for date in tournament_dates]
    
    # Display tournament overview
    st.subheader("📊 Tournament Overview")
    
    # Calculate match requirements for round-based scheduling
    num_groups = len([g for g in st.session_state.groups.values() if g])
    
    if num_groups < 2:
        st.warning("⚠️ Need at least 2 groups to generate schedule.")
        st.stop()
    
    # In round-robin, each group plays every other group once
    total_rounds = num_groups - 1 if num_groups % 2 == 0 else num_groups
    matches_per_round = (num_groups // 2) if num_groups % 2 == 0 else ((num_groups - 1) // 2)
    # One schedule row per group-vs-group meeting (5 games played in Record a Clash)
    meetings_per_round = matches_per_round
    meeting_block_mins = 5 * match_duration + 4 * break_duration
    total_meetings = total_rounds * meetings_per_round
    
    # Time per round: each meeting occupies a court for the full block
    total_match_time = meeting_block_mins
    
    # Convert time objects to datetime for calculation
    from datetime import datetime, timedelta
    
    # Create datetime objects for today with the specified times
    today = pd.Timestamp.now().date()
    start_datetime = pd.to_datetime(f"{today} {start_time}")
    end_datetime = pd.to_datetime(f"{today} {end_time}")
    
    daily_duration = end_datetime - start_datetime
    daily_minutes = daily_duration.total_seconds() / 60
    
    # Calculate capacity based on available courts and simultaneous play
    courts_needed_per_round = meetings_per_round
    
    if num_courts >= courts_needed_per_round:
        round_duration = total_match_time
        rounds_per_day = int(daily_minutes // round_duration) if round_duration else 0
        total_tournament_capacity = rounds_per_day * tournament_days * meetings_per_round
    else:
        batches_per_round = (courts_needed_per_round + num_courts - 1) // num_courts
        round_duration = batches_per_round * total_match_time
        rounds_per_day = int(daily_minutes // round_duration) if round_duration else 0
        total_tournament_capacity = rounds_per_day * tournament_days * meetings_per_round
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Groups", num_groups)
    with col2:
        st.metric("Tournament Rounds", total_rounds)
    with col3:
        st.metric("Total meetings", total_meetings)
    with col4:
        st.metric("Tournament Capacity", total_tournament_capacity)
    
    # Add detailed calculation breakdown for round-based scheduling
    with st.expander("📊 Detailed Round-Based Capacity Breakdown"):
        col1, col2, col3 = st.columns(3)
        
        # Calculate derived values for display
        rounds_per_day = int(daily_minutes // (total_match_time if num_courts >= courts_needed_per_round else 
                                               ((courts_needed_per_round + num_courts - 1) // num_courts) * total_match_time))
        batches_per_round = (courts_needed_per_round + num_courts - 1) // num_courts if num_courts < courts_needed_per_round else 1
        
        with col1:
            st.metric("Daily Hours", f"{daily_minutes/60:.1f}")
            st.metric("Meeting block (5 games)", f"{total_match_time} min")
            st.metric("Rounds per Day", rounds_per_day)
        
        with col2:
            st.metric("Courts Available", num_courts)
            st.metric("Courts Needed per Round", courts_needed_per_round)
            st.metric("Tournament Days", tournament_days)
        
        with col3:
            st.metric("Meetings per round", meetings_per_round)
            st.metric("Batches per Round", batches_per_round)
            st.metric("Court Utilization", f"{min(100, (courts_needed_per_round/num_courts)*100):.1f}%")
        
        # Capacity breakdown explanation
        if num_courts >= courts_needed_per_round:
            st.success(f"""
            ✅ **Optimal Scheduling**: All {courts_needed_per_round} meetings in each round can run in parallel!
            - Round duration: {total_match_time} min per meeting block (5 games each)
            - Rounds per day: {rounds_per_day}
            - Total capacity: {rounds_per_day * tournament_days * meetings_per_round} meetings
            """)
        else:
            st.info(f"""
            ℹ️ **Sequential Scheduling**: {courts_needed_per_round} meetings split into {batches_per_round} batches.
            - Each round takes {batches_per_round * total_match_time} minutes ({batches_per_round} batches)
            - Rounds per day: {rounds_per_day}
            - Total capacity: {rounds_per_day * tournament_days * meetings_per_round} meetings
            """)
    
    # Capacity analysis
    if total_meetings <= total_tournament_capacity:
        st.success(f"✅ Schedule feasible! {total_tournament_capacity - total_meetings} extra meeting slots available.")
    else:
        shortage = total_meetings - total_tournament_capacity
        st.error(f"❌ Schedule not feasible! Need {shortage} more match slots. Consider adding courts, days, or extending hours.")
    
    st.divider()
    
    # Schedule Generation
    st.subheader("🎯 Generate Schedule")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        schedule_type = st.selectbox(
            "Schedule Type:",
            ["Round Robin (All groups play each other)", "Swiss System", "Custom Bracket"],
            help="Round Robin ensures all groups play each other once"
        )
    
    with col2:
        if st.button("🚀 Generate Schedule", type="primary", disabled=total_meetings > total_tournament_capacity):
            if schedule_type == "Round Robin (All groups play each other)":
                with st.spinner("Generating optimized schedule..."):
                    schedule = generate_round_robin_schedule(
                        [st.session_state.group_names.get(key, key) for key in st.session_state.groups.keys()],
                        tournament_dates,
                        start_time,
                        end_time,
                        num_courts,
                        match_duration,
                        break_duration
                    )
                    st.session_state.tournament_schedule = schedule
                    auto_save()
                    st.success("🎉 Schedule generated successfully!")
                    st.rerun()
    
    # Display Generated Schedule
    if st.session_state.tournament_schedule:
        st.divider()
        st.subheader("📋 Generated Tournament Schedule")
        
        # Schedule overview
        schedule_df = pd.DataFrame(st.session_state.tournament_schedule)
        
        # Filter and display options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            selected_date = st.selectbox(
                "View Date:",
                ["All Dates"] + st.session_state.schedule_config['dates'],
                help="Filter schedule by specific date"
            )
        
        with col2:
            selected_court = st.selectbox(
                "View Court:",
                ["All Courts"] + [f"Court {i+1}" for i in range(num_courts)],
                help="Filter schedule by specific court"
            )
        
        with col3:
            view_format = st.selectbox(
                "View Format:",
                ["Table View", "Timeline View", "Court Schedule"],
                help="Different ways to display the schedule"
            )
        
        # Filter schedule
        filtered_schedule = schedule_df.copy()
        
        if selected_date != "All Dates":
            filtered_schedule = filtered_schedule[filtered_schedule['date'] == selected_date]
        
        if selected_court != "All Courts":
            filtered_schedule = filtered_schedule[filtered_schedule['court'] == selected_court]
        
        # Display schedule based on selected format
        if view_format == "Table View":
            if not filtered_schedule.empty:
                # Format for better display
                display_df = filtered_schedule.copy()
                display_df['Match Time'] = display_df['start_time'] + " - " + display_df['end_time']
                if 'format' in display_df.columns:
                    display_df = display_df[
                        ['date', 'round_number', 'court', 'Match Time', 'group1', 'group2', 'format']
                    ]
                    display_df.columns = ['Date', 'Round', 'Court', 'Time', 'Group 1', 'Group 2', 'Meeting']
                elif 'match_number' in display_df.columns:
                    display_df = display_df[
                        ['date', 'round_number', 'court', 'Match Time', 'group1', 'group2', 'match_number']
                    ]
                    display_df.columns = ['Date', 'Round', 'Court', 'Time', 'Group 1', 'Group 2', 'Match #']
                else:
                    display_df = display_df[
                        ['date', 'round_number', 'court', 'Match Time', 'group1', 'group2']
                    ]
                    display_df.columns = ['Date', 'Round', 'Court', 'Time', 'Group 1', 'Group 2']
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.info("No matches found for the selected filters.")
        
        elif view_format == "Timeline View":
            # Group by date and show timeline
            for date in sorted(filtered_schedule['date'].unique()):
                st.markdown(f"### 📅 {date}")
                date_matches = filtered_schedule[filtered_schedule['date'] == date].sort_values('start_time')
                
                for _, match in date_matches.iterrows():
                    col1, col2, col3, col4 = st.columns([2, 3, 2, 1])
                    
                    with col1:
                        st.write(f"**{match['start_time']}**")
                    with col2:
                        st.write(f"{match['group1']} vs {match['group2']}")
                    with col3:
                        st.write(f"*{match['court']}*")
                    with col4:
                        st.write(match.get('format') or f"Match {match.get('match_number', '')}")
        
        elif view_format == "Court Schedule":
            # Show schedule organized by court
            for court in sorted(filtered_schedule['court'].unique()):
                st.markdown(f"### 🏟️ {court}")
                court_matches = filtered_schedule[filtered_schedule['court'] == court].sort_values(['date', 'start_time'])
                
                for _, match in court_matches.iterrows():
                    col1, col2, col3, col4 = st.columns([2, 2, 3, 1])
                    
                    with col1:
                        st.write(f"**{match['date']}**")
                    with col2:
                        st.write(f"{match['start_time']}")
                    with col3:
                        st.write(f"{match['group1']} vs {match['group2']}")
                    with col4:
                        st.write(match.get('format') or f"#{match.get('match_number', '')}")
        
        # Export functionality
        st.divider()
        st.subheader("📤 Export Schedule")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📄 Export as CSV"):
                csv_data = schedule_df.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download Schedule CSV",
                    data=csv_data,
                    file_name=f"tournament_schedule_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            if st.button("📋 Copy to Clipboard"):
                schedule_text = schedule_df.to_string(index=False)
                st.code(schedule_text, language="text")
                st.info("Schedule formatted for copying above ☝️")

# --- TAB 4: STANDINGS ---
elif menu == "Fixtures & Results":
    st.header("📋 Fixtures & Results")
    st.markdown(
        "**Clash lifecycle:** **Scheduled** (not started) → **In progress** (1–4 games recorded) → **Completed** (all 5 games). "
        "**Fixtures** lists every pairing that is **Scheduled** or **In progress**. "
        "**Completed clashes** lists meetings that are fully done (all 5 games). "
        "Standings and Leaderboard update live as each game is recorded. Dates/rounds use **Match Schedule** when generated."
    )
    if not st.session_state.groups or not any(st.session_state.groups.values()):
        st.info("Create teams in **Player Import** or **Setup Groups** to see fixtures.")
    else:
        sched = st.session_state.get("tournament_schedule") or []
        cdf, udf = fixt.build_completed_and_upcoming(
            st.session_state.groups,
            st.session_state.get("group_names", {}),
            st.session_state.get("tournament_data") or {},
            sched,
        )

        st.subheader("✅ Results — completed clashes")
        if cdf.empty:
            st.caption("No completed clashes yet. Finalize a clash under **Record a Clash** (all 5 games) to appear here.")
        else:
            _drop = [c for c in ("_g1", "_g2", "_ck") if c in cdf.columns]
            st.dataframe(cdf.drop(columns=_drop, errors="ignore"), use_container_width=True, hide_index=True)
            st.subheader("📋 Clash details")
            st.caption("First level: result summary. Second level: player names and set-by-set game points from match data.")
            _gn = st.session_state.get("group_names", {})
            _subgroup = st.session_state.get("subgroup_names", DEFAULT_SUBGROUP_NAMES)
            _dec_label = _subgroup.get("subgroup1", "Decider")
            _chok_label = _subgroup.get("subgroup2", "Choker")
            _match_pool_type = ["subgroup1", "subgroup2", "subgroup1", "subgroup2", "subgroup1"]

            def _team_label(k):
                return _gn.get(k, k)

            def _player_name(x):
                return x.get("name", x) if isinstance(x, dict) else str(x)

            def _format_set_score(ss_val):
                if isinstance(ss_val, (list, tuple)) and len(ss_val) >= 2:
                    a, b = int(ss_val[0]) if ss_val[0] is not None else 0, int(ss_val[1]) if ss_val[1] is not None else 0
                    return f"{a}–{b}" if (a or b) else "—"
                return "—"

            for _idx in range(len(cdf)):
                _row = cdf.iloc[_idx]
                _g1k = str(_row["_g1"])
                _g2k = str(_row["_g2"])
                _ck = _row.get("_ck") or fixt.find_clash_key(_g1k, _g2k, st.session_state.get("tournament_data") or {})
                _matches = fixt.coerce_five_match_slots(
                    (st.session_state.get("tournament_data") or {}).get(_ck, [])
                )
                _title = f"{_row['Team A']} vs {_row['Team B']}"
                with st.expander(f"🏸 {_title}", expanded=False):
                    # Clash-level: player details and result for each game (visible without opening game expanders)
                    st.markdown("**Player details by game**")
                    for _i in range(5):
                        _m = _matches[_i]
                        if fixt.normalize_match_winner(_m) is None:
                            continue
                        _mt = _dec_label if _match_pool_type[_i] == "subgroup1" else _chok_label
                        _w = fixt.normalize_match_winner(_m)
                        _win_team = _g1k if _w == "g1" else _g2k
                        _pl = _m.get("players") or {}
                        _g1_names = _pl.get("g1") or []
                        _g2_names = _pl.get("g2") or []
                        _p1_str = ", ".join(_player_name(n) for n in _g1_names) or "—"
                        _p2_str = ", ".join(_player_name(n) for n in _g2_names) or "—"
                        st.caption(
                            f"**Game {_i + 1}** ({_mt}): **{_team_label(_g1k)}** ({_p1_str}) vs **{_team_label(_g2k)}** ({_p2_str}) → Winner: **{_team_label(_win_team)}** {_m.get('score_display', '')} ({_m.get('points', 0)} pts)"
                        )
                    st.divider()
                    st.markdown("**Per-game detail** *(expand for set scores)*")
                    for _i in range(5):
                        _m = _matches[_i]
                        if fixt.normalize_match_winner(_m) is None:
                            continue
                        _mt = _dec_label if _match_pool_type[_i] == "subgroup1" else _chok_label
                        _w = fixt.normalize_match_winner(_m)
                        _win_team = _g1k if _w == "g1" else _g2k
                        with st.expander(f"✅ Game {_i + 1} – {_mt}", expanded=False):
                            # First level: result summary
                            st.success(f"**Winner**: {_team_label(_win_team)}")
                            st.info(f"**Score**: {_m.get('score_display', '—')} · **Points**: {_m.get('points', 0)} awarded")
                            st.caption(f"**Match type**: {_mt}")
                            # Second level: player details and game points (from tournament_matches / match data)
                            st.divider()
                            st.markdown("**Player details & set scores** *(from match data)*")
                            _pl = _m.get("players") or {}
                            _g1_names = _pl.get("g1") or []
                            _g2_names = _pl.get("g2") or []
                            st.caption(f"**{_team_label(_g1k)}**: {', '.join(_player_name(n) for n in _g1_names) or '—'}")
                            st.caption(f"**{_team_label(_g2k)}**: {', '.join(_player_name(n) for n in _g2_names) or '—'}")
                            _ss = _m.get("set_scores") or {}
                            _s1 = _format_set_score(_ss.get("set1"))
                            _s2 = _format_set_score(_ss.get("set2"))
                            _s3 = _format_set_score(_ss.get("set3"))
                            st.caption(f"**Game points**: Set 1: {_s1} · Set 2: {_s2} · Set 3: {_s3}")

        st.subheader("📅 Fixtures (Scheduled & In progress)")
        if udf.empty:
            st.caption("No pairings to show (need at least two groups with players).")
        else:
            _udrop = [c for c in ("_g1", "_g2", "_ck") if c in udf.columns]
            st.dataframe(udf.drop(columns=_udrop, errors="ignore"), use_container_width=True, hide_index=True)

        if not sched:
            st.info("💡 Generate a **Match Schedule** to attach dates, times, and rounds to each fixture.")

elif menu == "Standings & Qualifiers":
    st.header("🏆 Tournament Standings & Qualification")
    
    if not st.session_state.tournament_data and st.session_state.standings.sum().sum() == 0:
        st.info("📝 No tournament matches recorded yet. Please record some clashes first!")
    else:
        standings_df = calculate_standings()
        
        if not standings_df.empty:
            st.subheader("📊 Current Standings")
            st.caption(
                "**Standings** (Points, Clash won, Sets, rally points) update only when a clash is **Completed** (all 5 games). "
                "**Match status** = how many of your meetings are **Scheduled** vs **In progress**."
            )
            standings_display = standings_df.copy()
            st.dataframe(standings_display, use_container_width=True, hide_index=True)
            
            # Qualification analysis — only when every team has played full schedule (round-robin: n-1 matches each)
            st.subheader("🎯 Qualification Analysis")
            
            total_teams = len(standings_df)
            expected_matches_per_team = (total_teams - 1) if total_teams >= 2 else 0
            mp_col = standings_display.get("Matches played")
            all_played_full = (
                total_teams >= 4
                and expected_matches_per_team > 0
                and mp_col is not None
                and (mp_col >= expected_matches_per_team).all()
            )

            if total_teams < 4:
                st.warning("⚠️ Need at least 4 teams for qualification analysis")
            elif not all_played_full:
                st.info(
                    f"📋 Qualification will be decided **after all matches are played**. "
                    f"Each team plays **{expected_matches_per_team}** match(es) in the round-robin. "
                    f"Complete remaining clashes in **Record a Clash**."
                )
            else:
                qualified_teams = standings_display.head(2)
                eliminated_teams = standings_display.tail(total_teams - 2)
                team_col = 'Team name'
                pts_col = 'Points'

                col1, col2 = st.columns(2)
                with col1:
                    st.success("✅ **QUALIFIED TEAMS**")
                    for idx, team in qualified_teams.iterrows():
                        st.write(f"🥇 **{team[team_col]}** - {team[pts_col]} pts (Set diff: {team.get('Set difference', 0)}, Pt diff: {team.get('Points difference', 0)})")
                with col2:
                    st.error("❌ **ELIMINATED TEAMS**")
                    for idx, team in eliminated_teams.iterrows():
                        st.write(f"💔 **{team[team_col]}** - {team[pts_col]} pts (Set diff: {team.get('Set difference', 0)}, Pt diff: {team.get('Points difference', 0)})")

                num_clashes = len([k for k in (st.session_state.tournament_data or {}) if '_vs_' in k])
                total_possible_clashes = len(st.session_state.groups) * (len(st.session_state.groups) - 1) // 2
                if num_clashes >= total_possible_clashes and total_possible_clashes > 0:
                    st.balloons()
                    st.success(f"🎉 **TOURNAMENT COMPLETE!** All {total_possible_clashes} clashes played!")

                    st.subheader("🏆 Final Tournament Rankings")
                    for idx, team in standings_display.iterrows():
                        if idx == 0:
                            st.write(f"🥇 **CHAMPION: {team[team_col]}** - {team[pts_col]} points")
                        elif idx == 1:
                            st.write(f"🥈 **RUNNER-UP: {team[team_col]}** - {team[pts_col]} points")
                        else:
                            st.write(f"#{idx+1} **{team[team_col]}** - {team[pts_col]} points")
        else:
            st.warning("⚠️ No valid tournament data available for standings calculation")


# --- LEADERBOARD (Deciders / Chokers / Female standings; points, matches, form) ---
elif menu == "Leaderboard":
    st.header("🏆 Leaderboard")
    st.markdown(
        "Updates live with **Standings** — each recorded game counts. "
        "**Deciders** = games 1, 3 & 5; **Chokers** = games 2 & 4. **Female** = all games. "
        "Points **+2** per game win."
    )

    if not st.session_state.groups or not any(st.session_state.groups.values()):
        st.info("📝 No teams have been created yet. Create teams in **Player Import & Auto-Balance** to see the leaderboard.")
    else:
        group_names = st.session_state.get("group_names", {})
        subgroup_names = st.session_state.get("subgroup_names", DEFAULT_SUBGROUP_NAMES)
        detailed_groups = st.session_state.get("detailed_groups") or {}
        player_database = st.session_state.get("player_database", pd.DataFrame())
        groups = st.session_state.groups
        tournament_data = st.session_state.get("tournament_data") or {}
        cfg = st.session_state.get("last_balance_config") or {}
        deciders_min = int(cfg.get("subgroup1_min", DEFAULT_DECIDERS_MIN))
        deciders_max = int(cfg.get("subgroup1_max", DEFAULT_DECIDERS_MAX))
        chokers_min = int(cfg.get("subgroup2_min", DEFAULT_CHOKERS_MIN))
        chokers_max = int(cfg.get("subgroup2_max", DEFAULT_CHOKERS_MAX))

        summary = pstats.get_player_stats_summary(
            detailed_groups,
            group_names,
            subgroup_names,
            tournament_data,
            groups,
            player_database,
            deciders_min=deciders_min,
            deciders_max=deciders_max,
            chokers_min=chokers_min,
            chokers_max=chokers_max,
        )

        tab1_label = f"🔽 {subgroup_names.get('subgroup1', DEFAULT_SUBGROUP_NAMES['subgroup1'])}"
        tab2_label = f"🔼 {subgroup_names.get('subgroup2', DEFAULT_SUBGROUP_NAMES['subgroup2'])}"
        tab3_label = "👩 Female standings"

        st.caption("Deciders = skill 0–5 only; Chokers = skill 6–15 only. Ranges follow **Skill-Level Subgroups** config.")
        tab1, tab2, tab3 = st.tabs([tab1_label, tab2_label, tab3_label])
        with tab1:
            st.subheader(tab1_label)
            if not summary["deciders_df"].empty:
                st.dataframe(summary["deciders_df"], use_container_width=True, hide_index=True)
            else:
                st.info("No Deciders (skill 0–5) in current teams. Add players with skill 0–5 and run **Skill-Level Subgroups** or ensure teams have Deciders.")
        with tab2:
            st.subheader(tab2_label)
            if not summary["chokers_df"].empty:
                st.dataframe(summary["chokers_df"], use_container_width=True, hide_index=True)
            else:
                st.info("No Chokers (skill 6–15) in current teams. Add players with skill 6–15 and run **Skill-Level Subgroups** or ensure teams have Chokers.")
        with tab3:
            st.subheader(tab3_label)
            if not summary["female_df"].empty:
                st.dataframe(summary["female_df"], use_container_width=True, hide_index=True)
            else:
                st.info("No female players in the current teams.")


# --- TAB 5: RECORD A CLASH ---
elif menu == "Record a Clash":
    # Check if user has permission to record clashes
    if not is_authenticated():
        st.error("🚫 Access Denied. Please login to record clashes.")
        st.stop()
    
    user_role = get_current_user_role()
    if user_role not in ['superuser', 'admin']:
        st.error("🚫 Access Denied. Only administrators can record clashes.")
        st.stop()
    
    st.header("⚔️ Record & Manage Group Clashes")

    if "_test_gen_msg" in st.session_state:
        _kind, _msg = st.session_state.pop("_test_gen_msg")
        if _kind == "success":
            st.success(_msg)
        else:
            st.error(_msg)
    if "_test_erase_feedback" in st.session_state:
        _eo, _em = st.session_state.pop("_test_erase_feedback")
        if _eo:
            st.success(_em)
        else:
            st.error(_em)

    with st.expander("🧪 Testing tools", expanded=False):
        st.caption("**Generate results** / **Erase** update the app and, when Supabase is configured, **`tournament_matches`** and **`standings`** in the database. If the DB save fails, changes are rolled back and an error is shown.")
        tc1, tc2 = st.columns(2)
        with tc1:
            if st.button("Generate results", key="test_generate_random_clashes", help="Random matches & scores for all group pairs"):
                ok, msg = generate_random_clash_results_all_pairs()
                if ok:
                    st.session_state["_test_gen_msg"] = ("success", msg)
                else:
                    st.session_state["_test_gen_msg"] = ("error", msg)
                st.rerun()
        with tc2:
            confirm = st.checkbox("Confirm erase", key="confirm_erase_all_clashes")
            if st.button("Erase all clash results", key="test_erase_all_clashes", disabled=not confirm):
                _ok_e, _msg_e = erase_all_clash_results()
                st.session_state["_test_erase_feedback"] = (_ok_e, _msg_e)
                st.rerun()
    
    # Tabs for different actions
    if user_role == 'superuser':
        tab1, tab2, tab3 = st.tabs(["🆕 Record New Clash", "✏️ Edit Clash Results", "📜 Edit History"])
    else:
        tab1, tab2, tab3 = st.tabs(["🆕 Record New Clash", "👁️ View Results", "🚫 Admin Only"])
    
    with tab1:
        st.subheader("Record New Clash")
        record_new_clash()
    
    with tab2:
        if user_role == 'superuser':
            st.subheader("Edit Clash Results")
            edit_clash_results()
        else:
            st.subheader("View Recorded Results")
            view_clash_results()
    
    with tab3:
        if user_role == 'superuser':
            st.subheader("Clash Edit History")
            show_edit_history()
        else:
            st.error("🚫 Only superusers can view edit history")

# --- TAB 6: MANAGE PLAYERS ---
elif menu == "Manage Players":
    st.header("👥 Quick Player Management")
    st.info("Use this for quick edits. For comprehensive setup, use the 'Setup Groups & Players' tab.")
    
    for group_name, players in st.session_state.groups.items():
        st.subheader(f"📋 {group_name}")
        new_list = st.text_area(
            f"Edit Players (comma-separated):", 
            value=", ".join(players),
            key=f"quick_edit_{group_name}"
        )
        
        if st.button(f"Update {group_name}", key=f"quick_update_{group_name}"):
            updated_players = [p.strip() for p in new_list.split(",") if p.strip()]
            # Ensure exactly 10 players
            updated_players = updated_players[:10]  # Take first 10
            while len(updated_players) < 10:
                updated_players.append(f"Player {len(updated_players)+1}")
            
            st.session_state.groups[group_name] = updated_players
            st.success(f"Updated {group_name}!")
            st.rerun()

    # Data Export Section
    st.divider()
    st.subheader("📥 Export Tournament Data")
    st.info("Export your tournament data to CSV files for external analysis")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Export Standings"):
            if not st.session_state.standings.empty:
                standings_csv = st.session_state.standings.to_csv()
                st.download_button(
                    label="💾 Download Standings CSV",
                    data=standings_csv,
                    file_name="tournament_standings.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No standings data to export")
    
    with col2:
        if st.button("👥 Export Players"):
            if not st.session_state.player_database.empty:
                players_csv = st.session_state.player_database.to_csv(index=False)
                st.download_button(
                    label="💾 Download Players CSV",
                    data=players_csv,
                    file_name="tournament_players.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No player data to export")
    
    with col3:
        if st.button("🏆 Export Groups"):
            if st.session_state.groups:
                # Create a CSV with group assignments
                group_data = []
                for group_name, players in st.session_state.groups.items():
                    for i, player in enumerate(players, 1):
                        group_data.append({
                            'Group': st.session_state.group_names.get(group_name, group_name),
                            'Position': i,
                            'Player': player
                        })
                
                groups_df = pd.DataFrame(group_data)
                groups_csv = groups_df.to_csv(index=False)
                st.download_button(
                    label="💾 Download Groups CSV",
                    data=groups_csv,
                    file_name="tournament_groups.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No group data to export")

# --- TAB 8: USER MANAGEMENT ---
elif menu == "User Management":
    st.header("👥 User Management")
    
    # Only superuser can access this page
    if get_current_user_role() != 'superuser':
        st.error("🚫 Access Denied. Only superusers can manage users.")
        st.stop()
    
    tab1, tab2 = st.tabs(["👤 View Users", "➕ Create Admin User"])
    
    with tab1:
        st.subheader("📋 Current Users")
        
        if st.session_state.users:
            users_data = []
            for username, user_info in st.session_state.users.items():
                users_data.append({
                    'Username': username,
                    'Role': user_info['role'].title(),
                    'Created By': user_info.get('created_by', 'Unknown'),
                    'Created At': user_info.get('created_at', 'Unknown')[:19] if user_info.get('created_at') else 'Unknown'
                })
            
            users_df = pd.DataFrame(users_data)
            st.dataframe(users_df, use_container_width=True, hide_index=True)
            
            # Delete user section (only non-superusers can be deleted)
            st.subheader("🗑️ Delete User")
            deletable_users = [user for user, info in st.session_state.users.items() 
                             if info['role'] != 'superuser']
            
            if deletable_users:
                user_to_delete = st.selectbox("Select user to delete:", deletable_users)
                if st.button(f"🗑️ Delete User: {user_to_delete}", type="secondary"):
                    if st.session_state.get('confirm_delete', False):
                        del st.session_state.users[user_to_delete]
                        auto_save()  # Save after user deletion
                        st.success(f"User '{user_to_delete}' has been deleted.")
                        st.session_state.confirm_delete = False
                        st.rerun()
                    else:
                        st.session_state.confirm_delete = True
                        st.warning(f"⚠️ Click again to confirm deletion of user '{user_to_delete}'")
            else:
                st.info("No deletable users (only admin users can be deleted, not superusers)")
        else:
            st.info("No users found")
    
    with tab2:
        st.subheader("➕ Create New Admin User")
        
        with st.form("create_admin_form"):
            new_username = st.text_input("Username", help="Choose a unique username")
            new_password = st.text_input("Password", type="password", help="Choose a secure password")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            create_admin = st.form_submit_button("👑 Create Admin User")
            
            if create_admin:
                # Validation
                if not new_username or not new_password:
                    st.error("❌ Username and password are required")
                elif new_username in st.session_state.users:
                    st.error(f"❌ Username '{new_username}' already exists")
                elif new_password != confirm_password:
                    st.error("❌ Passwords do not match")
                elif len(new_password) < 4:
                    st.error("❌ Password must be at least 4 characters long")
                else:
                    # Create new admin user
                    st.session_state.users[new_username] = {
                        'password_hash': hash_password(new_password),
                        'role': 'admin',
                        'created_by': get_current_user(),
                        'created_at': datetime.now().isoformat()
                    }
                    auto_save()  # Save user data immediately
                    st.success(f"✅ Admin user '{new_username}' created successfully!")
                    st.info(f"👤 **Username:** {new_username}\\n🔑 **Role:** Admin\\n🎯 **Permissions:** Can record clashes")
                    st.rerun()
        
        # Instructions
        st.markdown("---")
        st.subheader("ℹ️ User Roles & Permissions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **🌟 Superuser (You)**
            - Full access to all features
            - Can create/delete admin users
            - Can import players & create teams
            - Can record clashes
            - Can view all reports
            """)
        
        with col2:
            st.markdown("""
            **👑 Admin User**
            - Can record clashes only
            - Cannot create teams or import players
            - Cannot manage other users
            - Can view team details & standings
            """)
        
        st.info("🌐 **Guest/Public Access:** Anyone can view Team Details (skill levels hidden), Standings & Qualifiers, Fixtures & Results, and Leaderboard without logging in.")
