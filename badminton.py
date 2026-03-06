import streamlit as st
import pandas as pd
import json
import random
import io
from collections import defaultdict

# Page Configuration
st.set_page_config(page_title="Badminton Tournament Pro", layout="wide")

# Data persistence functions
def save_tournament_data():
    """Save tournament data to JSON files"""
    try:
        # Save player database
        if 'player_database' in st.session_state:
            st.session_state.player_database.to_json('tournament_players.json', orient='records')
        
        # Save other data
        tournament_data = {
            'group_names': st.session_state.get('group_names', {}),
            'groups': st.session_state.get('groups', {}),
            'standings': st.session_state.get('standings', pd.DataFrame()).to_dict() if 'standings' in st.session_state else {}
        }
        
        with open('tournament_data.json', 'w') as f:
            json.dump(tournament_data, f)
            
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")

def load_tournament_data():
    """Load tournament data from JSON files"""
    try:
        # Load player database
        try:
            st.session_state.player_database = pd.read_json('tournament_players.json', orient='records')
        except:
            # Initialize with sample data if file doesn't exist
            st.session_state.player_database = pd.DataFrame({
                'name': [f'Player {i+1}' for i in range(60)],
                'gender': ['M' if i % 3 != 0 else 'F' for i in range(60)],
                'email': [f'player{i+1}@example.com' for i in range(60)],
                'skill_level': [random.randint(1, 10) for _ in range(60)],
                'group': [f"Group {chr(65+(i//10))}" for i in range(60)],
                'assigned': [True] * 60
            })
        
        # Load other data
        try:
            with open('tournament_data.json', 'r') as f:
                tournament_data = json.load(f)
                st.session_state.group_names = tournament_data.get('group_names', {f"Group {chr(65+i)}": f"Group {chr(65+i)}" for i in range(6)})
                st.session_state.groups = tournament_data.get('groups', {})
                
                # Restore standings
                standings_data = tournament_data.get('standings', {})
                if standings_data:
                    st.session_state.standings = pd.DataFrame.from_dict(standings_data)
                    if 'Group' in st.session_state.standings.columns:
                        st.session_state.standings = st.session_state.standings.set_index('Group')
        except:
            # Initialize defaults if file doesn't exist
            st.session_state.group_names = {f"Group {chr(65+i)}": f"Group {chr(65+i)}" for i in range(6)}
            st.session_state.groups = {f"Group {chr(65+i)}": [] for i in range(6)}
            st.session_state.standings = pd.DataFrame({
                "Group": [f"Group {chr(65+i)}" for i in range(6)],
                "Clash Wins": [0]*6,
                "Total Points": [0]*6
            }).set_index("Group")
            
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")

# Auto-save functionality
def auto_save():
    """Auto-save tournament data"""
    save_tournament_data()

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
            # Schedule 5 matches for this clash
            for match_num in range(1, 6):
                # Find available court for this time slot
                time_slot_key = f"{current_date_idx}_{current_time_slot}"
                
                if time_slot_key not in court_assignments:
                    court_assignments[time_slot_key] = []
                
                # Find next available court
                court_num = len(court_assignments[time_slot_key]) + 1
                
                if court_num <= num_courts:
                    # Court is available at this time
                    match_start_time = round_start_dt
                    match_end_time = match_start_time + timedelta(minutes=match_duration)
                    
                    court_assignments[time_slot_key].append(court_num)
                else:
                    # Need to use next time slot
                    current_time_slot += 1
                    
                    # Check if day overflows
                    if (current_time_slot * slot_duration) + slot_duration > daily_minutes:
                        current_date_idx = (current_date_idx + 1) % len(dates)
                        current_time_slot = 0
                    
                    match_start_time = start_dt + timedelta(minutes=current_time_slot * slot_duration)
                    match_end_time = match_start_time + timedelta(minutes=match_duration)
                    
                    court_num = 1
                    new_time_slot_key = f"{current_date_idx}_{current_time_slot}"
                    court_assignments[new_time_slot_key] = [1]
                
                # Add match to schedule
                schedule.append({
                    'date': dates[current_date_idx].strftime('%Y-%m-%d'),
                    'round_number': round_idx + 1,
                    'clash_number': clash_idx + 1,
                    'match_number': match_num,
                    'court': f'Court {court_num}',
                    'start_time': match_start_time.strftime('%H:%M'),
                    'end_time': match_end_time.strftime('%H:%M'),
                    'group1': group1,
                    'group2': group2,
                    'status': 'Scheduled'
                })
        
        # Move to next time slot for next round
        current_time_slot += 1
    
    return schedule

# Initialize State for Data Persistence
if 'initialized' not in st.session_state:
    # Load existing data or initialize defaults
    load_tournament_data()
    
    # Ensure groups are populated from player database if they exist
    if not any(st.session_state.groups.values()) and not st.session_state.player_database.empty:
        assigned_players = st.session_state.player_database[st.session_state.player_database['assigned'] == True]
        for _, player in assigned_players.iterrows():
            if player['group'] in st.session_state.groups:
                if player['name'] not in st.session_state.groups[player['group']]:
                    st.session_state.groups[player['group']].append(player['name'])
    
    st.session_state.initialized = True

st.title("🏸 Badminton Group Tournament Manager")
st.sidebar.header("Tournament Controls")

# Save/Load functionality in sidebar
st.sidebar.subheader("💾 Data Management")
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("💾 Save Data", help="Save all tournament data"):
        save_tournament_data()
        st.sidebar.success("Data saved!")
with col2:
    if st.button("📂 Load Data", help="Load saved tournament data"):
        load_tournament_data()
        st.sidebar.success("Data loaded!")
        st.rerun()

# Export functionality
if st.sidebar.button("📤 Export Player Data", help="Download player database as CSV"):
    csv_data = st.session_state.player_database.to_csv(index=False)
    st.sidebar.download_button(
        label="⬇️ Download CSV",
        data=csv_data,
        file_name=f"tournament_players_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )

st.sidebar.divider()

menu = st.sidebar.radio("Navigate", ["Player Import & Auto-Balance", "Setup Groups & Players", "Match Schedule", "Standings & Qualifiers", "Record a Clash", "Manage Players"])

# Auto-balancing algorithm
def auto_balance_groups(players_df):
    """
    Auto-balance players into 6 groups with optimized skill and gender distribution
    Uses iterative optimization to minimize skill variance between groups
    """
    import itertools
    
    # Separate male and female players
    male_players = players_df[players_df['gender'] == 'M'].copy()
    female_players = players_df[players_df['gender'] == 'F'].copy()
    
    # Sort by skill level (descending)
    male_players = male_players.sort_values('skill_level', ascending=False).reset_index(drop=True)
    female_players = female_players.sort_values('skill_level', ascending=False).reset_index(drop=True)
    
    # Initialize groups
    groups = {f"Group {chr(65+i)}": {'players': [], 'total_skill': 0, 'male_count': 0, 'female_count': 0} for i in range(6)}
    group_keys = list(groups.keys())
    
    # Step 1: Distribute females evenly using optimized assignment
    female_count_per_group = len(female_players) // 6
    female_remainder = len(female_players) % 6
    
    # Create female distribution plan
    female_distribution = []
    for i in range(6):
        group_females = female_count_per_group + (1 if i < female_remainder else 0)
        female_distribution.append(group_females)
    
    # Assign females using skill balancing
    female_idx = 0
    for round_num in range(max(female_distribution)):
        # Alternate direction each round for better balance
        group_order = list(range(6)) if round_num % 2 == 0 else list(range(5, -1, -1))
        
        for group_idx in group_order:
            if female_distribution[group_idx] > 0 and female_idx < len(female_players):
                player = female_players.iloc[female_idx]
                groups[group_keys[group_idx]]['players'].append(player)
                groups[group_keys[group_idx]]['total_skill'] += player['skill_level']
                groups[group_keys[group_idx]]['female_count'] += 1
                female_distribution[group_idx] -= 1
                female_idx += 1
    
    # Step 2: Distribute males using skill-based optimization
    remaining_spots = [10 - len(groups[key]['players']) for key in group_keys]
    
    # Use iterative assignment for better balance
    male_idx = 0
    while male_idx < len(male_players):
        # Find the group with lowest total skill that has remaining spots
        available_groups = [(i, groups[group_keys[i]]['total_skill']) for i in range(6) if remaining_spots[i] > 0]
        
        if not available_groups:
            break
            
        # Sort by total skill (ascending) to assign to weakest group
        available_groups.sort(key=lambda x: x[1])
        target_group_idx = available_groups[0][0]
        
        player = male_players.iloc[male_idx]
        groups[group_keys[target_group_idx]]['players'].append(player)
        groups[group_keys[target_group_idx]]['total_skill'] += player['skill_level']
        groups[group_keys[target_group_idx]]['male_count'] += 1
        remaining_spots[target_group_idx] -= 1
        male_idx += 1
    
    # Step 3: Optimization phase - swap players to minimize variance
    max_iterations = 50
    for iteration in range(max_iterations):
        improved = False
        current_skills = [groups[key]['total_skill'] for key in group_keys]
        current_variance = sum((skill - sum(current_skills)/6)**2 for skill in current_skills)
        
        # Try swapping players between groups
        for i in range(6):
            for j in range(i+1, 6):
                group_i = groups[group_keys[i]]
                group_j = groups[group_keys[j]]
                
                # Try swapping each player from group i with each player from group j
                for player_i_idx, player_i in enumerate(group_i['players']):
                    for player_j_idx, player_j in enumerate(group_j['players']):
                        # Only swap if same gender to maintain gender balance
                        if player_i['gender'] == player_j['gender']:
                            # Calculate new skills after swap
                            new_skill_i = group_i['total_skill'] - player_i['skill_level'] + player_j['skill_level']
                            new_skill_j = group_j['total_skill'] - player_j['skill_level'] + player_i['skill_level']
                            
                            new_skills = current_skills.copy()
                            new_skills[i] = new_skill_i
                            new_skills[j] = new_skill_j
                            
                            new_variance = sum((skill - sum(new_skills)/6)**2 for skill in new_skills)
                            
                            # If this swap improves balance, do it
                            if new_variance < current_variance:
                                # Perform the swap
                                group_i['players'][player_i_idx] = player_j
                                group_j['players'][player_j_idx] = player_i
                                group_i['total_skill'] = new_skill_i
                                group_j['total_skill'] = new_skill_j
                                improved = True
                                break
                    if improved:
                        break
                if improved:
                    break
            if improved:
                break
        
        if not improved:
            break
    
    # Convert to the expected format
    result_groups = {}
    for group_name, group_data in groups.items():
        result_groups[group_name] = group_data['players']
    
    return result_groups


def auto_balance_subgroups(players_df, subgroup1_min, subgroup1_max, subgroup2_min, subgroup2_max, subgroup1_count, subgroup2_count, num_groups=6):
    """
    Auto-balance players into specified number of groups with 2 skill-based subgroups each
    Ensures skill point balance at group level, subgroup 1 level, and subgroup 2 level
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
    
    # Select players for each subgroup (take all available if we have more than needed)
    if len(subgroup1_players) > needed_sg1:
        subgroup1_selected = subgroup1_players.nlargest(needed_sg1, 'skill_level').reset_index(drop=True)
    else:
        subgroup1_selected = subgroup1_players.reset_index(drop=True)
        
    if len(subgroup2_players) > needed_sg2:
        subgroup2_selected = subgroup2_players.nlargest(needed_sg2, 'skill_level').reset_index(drop=True)
    else:
        subgroup2_selected = subgroup2_players.reset_index(drop=True)
    
    # Initialize groups dynamically
    groups = {}
    for i in range(num_groups):
        group_name = f"Group {chr(65+i)}"
        groups[group_name] = {
            'subgroup1': {'players': [], 'total_skill': 0, 'male_count': 0, 'female_count': 0},
            'subgroup2': {'players': [], 'total_skill': 0, 'male_count': 0, 'female_count': 0}
        }
    
    group_keys = list(groups.keys())
    
    def balance_players_by_skill(players_list, subgroup_type, target_count_per_group):
        """Balance players across all groups to minimize skill variance"""
        if len(players_list) == 0:
            return
            
        # Sort players by skill level (descending)
        sorted_players = players_list.sort_values('skill_level', ascending=False).reset_index(drop=True)
        
        # Convert to list of dictionaries for easier manipulation
        player_records = sorted_players.to_dict('records')
        
        # Initialize group assignments
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
        """Optimize skill balance by swapping players between groups"""
        max_iterations = 100
        
        for iteration in range(max_iterations):
            improved = False
            
            # Calculate current skill totals for this subgroup
            current_skills = [groups[group_key][subgroup_type]['total_skill'] for group_key in group_keys]
            current_variance = sum((skill - sum(current_skills)/num_groups)**2 for skill in current_skills)
            
            # Try swapping players between groups
            for i in range(num_groups):
                for j in range(i+1, num_groups):
                    group_i = groups[group_keys[i]][subgroup_type]
                    group_j = groups[group_keys[j]][subgroup_type]
                    
                    # Skip if either group is empty
                    if not group_i['players'] or not group_j['players']:
                        continue
                    
                    # Try swapping each player from group i with each player from group j
                    for player_i_idx, player_i in enumerate(group_i['players']):
                        for player_j_idx, player_j in enumerate(group_j['players']):
                            # Only swap if same gender to maintain gender balance
                            if player_i['gender'] == player_j['gender']:
                                # Calculate new skills after swap
                                new_skill_i = group_i['total_skill'] - player_i['skill_level'] + player_j['skill_level']
                                new_skill_j = group_j['total_skill'] - player_j['skill_level'] + player_i['skill_level']
                                
                                new_skills = current_skills.copy()
                                new_skills[i] = new_skill_i
                                new_skills[j] = new_skill_j
                                
                                new_variance = sum((skill - sum(new_skills)/num_groups)**2 for skill in new_skills)
                                
                                # If this swap improves balance, do it
                                if new_variance < current_variance - 0.01:  # Small threshold to avoid endless swapping
                                    # Perform the swap
                                    group_i['players'][player_i_idx] = player_j
                                    group_j['players'][player_j_idx] = player_i
                                    group_i['total_skill'] = new_skill_i
                                    group_j['total_skill'] = new_skill_j
                                    improved = True
                                    current_variance = new_variance
                                    current_skills = new_skills
                                    break
                        if improved:
                            break
                    if improved:
                        break
                if improved:
                    break
            
            if not improved:
                break
    
    # Balance subgroup 1 players
    balance_players_by_skill(subgroup1_selected, 'subgroup1', subgroup1_count)
    
    # Balance subgroup 2 players  
    balance_players_by_skill(subgroup2_selected, 'subgroup2', subgroup2_count)
    
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

# --- TAB 1: PLAYER IMPORT & AUTO-BALANCE ---
if menu == "Player Import & Auto-Balance":
    st.header("📊 Player Import & Team Auto-Balancing")
    st.markdown("Import players with detailed information and automatically create balanced groups.")
    
    # Import Methods
    st.subheader("📥 Import Players")
    
    import_method = st.radio("Choose import method:", ["Manual Entry", "CSV/Excel Upload", "Bulk Text Import"])
    
    if import_method == "CSV/Excel Upload":
        st.info("Upload a CSV or Excel file with columns: name, gender (M/F), email, skill_level (1-10)")
        
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
                        new_players_df['skill_level'].between(1, 10) &
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
        st.info("Enter players in format: Name, Gender(M/F), Email, Skill(1-10) - one per line")
        
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
                        if gender in ['M', 'F'] and 1 <= skill <= 10:
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
                player_skill = st.number_input("Skill Level", min_value=1, max_value=10, value=5)
            
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
                    min_value=1,
                    max_value=10,
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
                
                # Skill level ranges
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Subgroup 1 (Lower Skills)**")
                    subgroup1_min = st.number_input("Min Skill Level:", min_value=1, max_value=10, value=1, key="sg1_min")
                    subgroup1_max = st.number_input("Max Skill Level:", min_value=1, max_value=10, value=5, key="sg1_max")
                    
                with col2:
                    st.markdown("**Subgroup 2 (Higher Skills)**")
                    subgroup2_min = st.number_input("Min Skill Level:", min_value=1, max_value=10, value=6, key="sg2_min")
                    subgroup2_max = st.number_input("Max Skill Level:", min_value=1, max_value=10, value=10, key="sg2_max")
                
                # Player count configuration
                st.markdown("#### 📊 Player Count Configuration")
                st.info("Specify how many players should be in each subgroup across all groups")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    subgroup1_count = st.number_input(
                        "Players per Subgroup 1:", 
                        min_value=1, max_value=15, value=5, 
                        key="sg1_count",
                        help=f"Number of players in each subgroup 1 across {num_groups} groups"
                    )
                with col2:
                    subgroup2_count = st.number_input(
                        "Players per Subgroup 2:", 
                        min_value=1, max_value=15, value=5, 
                        key="sg2_count",
                        help=f"Number of players in each subgroup 2 across {num_groups} groups"
                    )
                with col3:
                    total_per_group = subgroup1_count + subgroup2_count
                    st.metric("Total per Group", total_per_group)
                    st.metric("Tournament Total", total_per_group * num_groups)
                
                # Validate ranges
                if subgroup1_max >= subgroup2_min:
                    st.warning("⚠️ Subgroup ranges should not overlap. Adjust the ranges so Subgroup 1 max is less than Subgroup 2 min.")
                
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
            
            # Create balanced groups button
            if st.button("🎯 Create Balanced Groups", type="primary", help="This will redistribute all players into balanced groups"):
                with st.spinner("Creating balanced groups... This may take a moment."):
                    if balance_strategy == "Skill-Level Subgroups":
                        # Validate subgroup ranges
                        if subgroup1_max >= subgroup2_min:
                            st.error("❌ Please fix the subgroup ranges before proceeding.")
                            st.stop()
                        
                        try:
                            # Auto-balance with subgroups
                            balanced_groups, detailed_groups = auto_balance_subgroups(
                                st.session_state.player_database, 
                                subgroup1_min, subgroup1_max, 
                                subgroup2_min, subgroup2_max,
                                subgroup1_count, subgroup2_count, num_groups
                            )
                            
                            # Store detailed subgroup information for display
                            st.session_state.detailed_groups = detailed_groups
                            
                        except ValueError as e:
                            st.error(f"❌ {str(e)}")
                            st.info("💡 Use the 'Preview Player Distribution' button to check availability before balancing.")
                            st.stop()
                        
                    else:
                        # Use traditional auto-balance
                        balanced_groups = auto_balance_groups(st.session_state.player_database)
                    
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
                        "Group": list(st.session_state.groups.keys()),
                        "Clash Wins": [0] * len(st.session_state.groups),
                        "Total Points": [0] * len(st.session_state.groups)
                    }).set_index("Group")
                    
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
                            'Group': group_name,
                            'Players': len(group_players_df),
                            'Males': len(group_players_df[group_players_df['gender'] == 'M']),
                            'Females': len(group_players_df[group_players_df['gender'] == 'F']),
                            'Avg Skill': round(group_players_df['skill_level'].mean(), 2),
                            'Total Skill': group_players_df['skill_level'].sum(),
                            'Skill Range': f"{group_players_df['skill_level'].min()}-{group_players_df['skill_level'].max()}"
                        }
                        balance_data.append(stats)
            
            if balance_data:
                # Display balance summary table
                balance_df = pd.DataFrame(balance_data)
                st.dataframe(balance_df, use_container_width=True)
                
                # Balance quality metrics
                if len(balance_data) > 1:
                    skill_variance = balance_df['Total Skill'].var()
                    avg_variance = balance_df['Avg Skill'].var()
                    gender_balance = balance_df['Females'].std()
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Skill Variance", f"{skill_variance:.2f}", help="Lower is better (0 = perfectly balanced)")
                    with col2:
                        st.metric("Avg Skill Variance", f"{avg_variance:.3f}", help="Lower is better")
                    with col3:
                        st.metric("Gender Balance Quality", f"{gender_balance:.2f}", help="Lower is better (more even distribution)")
                    with col4:
                        skill_range = balance_df['Total Skill'].max() - balance_df['Total Skill'].min()
                        st.metric("Skill Point Range", f"{skill_range}", help="Difference between strongest and weakest group")
                
                # Show subgroup breakdown if detailed groups exist
                if hasattr(st.session_state, 'detailed_groups') and st.session_state.detailed_groups:
                    st.divider()
                    st.subheader("🎯 Subgroup Distribution Analysis")
                    st.info("Breakdown of players by skill-level subgroups within each group")
                    
                    subgroup_data = []
                    for group_name, subgroups in st.session_state.detailed_groups.items():
                        # Subgroup 1 stats
                        sg1_players = subgroups['subgroup1']['players']
                        if sg1_players:
                            sg1_stats = {
                                'Group': f"{group_name}-1",
                                'Subgroup': '1 (Lower)',
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
                                'Group': f"{group_name}-2",
                                'Subgroup': '2 (Higher)',
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
                        st.dataframe(subgroup_df, use_container_width=True)
                        
                        # Subgroup balance metrics
                        sg1_data = [row for row in subgroup_data if '1 (Lower)' in row['Subgroup']]
                        sg2_data = [row for row in subgroup_data if '2 (Higher)' in row['Subgroup']]
                        
                        if sg1_data and sg2_data:
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("**Subgroup 1 Balance**")
                                sg1_df = pd.DataFrame(sg1_data)
                                sg1_variance = sg1_df['Total Skill'].var()
                                sg1_range = sg1_df['Total Skill'].max() - sg1_df['Total Skill'].min()
                                st.metric("Skill Variance", f"{sg1_variance:.2f}")
                                st.metric("Skill Range", f"{sg1_range}")
                                
                            with col2:
                                st.markdown("**Subgroup 2 Balance**")
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
                    group_tabs = st.tabs([f"{group_name} ({balance_df[balance_df['Group']==group_name]['Total Skill'].iloc[0]} pts)" for group_name in group_player_details.keys()])
                    
                    for tab, (group_name, players_df) in zip(group_tabs, group_player_details.items()):
                        with tab:
                            # Group statistics
                            group_stats = balance_data[next(i for i, x in enumerate(balance_data) if x['Group'] == group_name)]
                            
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Total Players", group_stats['Players'])
                            with col2:
                                st.metric("Males/Females", f"{group_stats['Males']}/{group_stats['Females']}")
                            with col3:
                                st.metric("Average Skill", group_stats['Avg Skill'])
                            with col4:
                                st.metric("Total Skill Points", group_stats['Total Skill'])
                            
                            # Player list with details
                            st.markdown("**Players:**")
                            
                            # Show subgroup breakdown if available
                            if hasattr(st.session_state, 'detailed_groups') and st.session_state.detailed_groups and group_name in st.session_state.detailed_groups:
                                subgroups = st.session_state.detailed_groups[group_name]
                                
                                # Subgroup 1
                                if subgroups['subgroup1']['players']:
                                    st.markdown(f"***🔽 Subgroup 1 - Lower Skills ({len(subgroups['subgroup1']['players'])} players)***")
                                    for idx, player in enumerate(subgroups['subgroup1']['players'], 1):
                                        gender_icon = "👨" if player['gender'] == 'M' else "👩"
                                        skill_stars = "⭐" * min(player['skill_level'], 5)
                                        st.write(f"  {idx}. {gender_icon} **{player['name']}** (Skill: {player['skill_level']} {skill_stars}) - {player['email']}")
                                
                                # Subgroup 2
                                if subgroups['subgroup2']['players']:
                                    st.markdown(f"***🔼 Subgroup 2 - Higher Skills ({len(subgroups['subgroup2']['players'])} players)***")
                                    for idx, player in enumerate(subgroups['subgroup2']['players'], 1):
                                        gender_icon = "👨" if player['gender'] == 'M' else "👩"
                                        skill_stars = "⭐" * min(player['skill_level'], 10)
                                        st.write(f"  {idx}. {gender_icon} **{player['name']}** (Skill: {player['skill_level']} {skill_stars}) - {player['email']}")
                            else:
                                # Regular display without subgroups
                                for idx, (_, player) in enumerate(players_df.iterrows(), 1):
                                    gender_icon = "👨" if player['gender'] == 'M' else "👩"
                                    skill_stars = "⭐" * min(player['skill_level'], 10)
                                    st.write(f"{idx}. {gender_icon} **{player['name']}** (Skill: {player['skill_level']} {skill_stars}) - {player['email']}")
                
                # Summary statistics
                st.divider()
                st.subheader("📈 Balance Summary")
                
                if len(balance_data) >= 6:
                    total_players = sum(stats['Players'] for stats in balance_data)
                    total_males = sum(stats['Males'] for stats in balance_data)
                    total_females = sum(stats['Females'] for stats in balance_data)
                    total_skill = sum(stats['Total Skill'] for stats in balance_data)
                    avg_group_skill = total_skill / 6
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Tournament Players", total_players, "Target: 60")
                    with col2:
                        st.metric("Gender Distribution", f"{total_males}M / {total_females}F")
                    with col3:
                        st.metric("Target Group Skill", f"{avg_group_skill:.1f}", "All groups should be close to this")
                    
                    # Balance quality assessment
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
                
                # Update groups dictionary with new name
                if old_key in st.session_state.groups:
                    st.session_state.groups[new_name] = st.session_state.groups.pop(old_key)
                
                # Update standings dataframe
                if old_key in st.session_state.standings.index:
                    st.session_state.standings = st.session_state.standings.rename(index={old_key: new_name})
    
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

# --- TAB 3: MATCH SCHEDULE ---
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
    matches_per_clash = 5  # 5 doubles matches per group clash
    total_matches = total_rounds * matches_per_round * matches_per_clash
    
    # Calculate time requirements for round-based scheduling
    total_match_time = match_duration + break_duration
    
    # Convert time objects to datetime for calculation
    from datetime import datetime, timedelta
    
    # Create datetime objects for today with the specified times
    today = pd.Timestamp.now().date()
    start_datetime = pd.to_datetime(f"{today} {start_time}")
    end_datetime = pd.to_datetime(f"{today} {end_time}")
    
    daily_duration = end_datetime - start_datetime
    daily_minutes = daily_duration.total_seconds() / 60
    
    # Calculate capacity based on available courts and simultaneous play
    courts_needed_per_round = matches_per_round * matches_per_clash  # Total matches in a round
    
    if num_courts >= courts_needed_per_round:
        # All matches in a round can be played simultaneously
        round_duration = total_match_time  # Just one match duration since all are parallel
        rounds_per_day = int(daily_minutes // round_duration)
        total_tournament_capacity = rounds_per_day * tournament_days * matches_per_round * matches_per_clash
    else:
        # Not enough courts - some matches will be sequential
        # Calculate how many parallel "batches" we can run
        batches_per_round = (courts_needed_per_round + num_courts - 1) // num_courts  # Ceiling division
        round_duration = batches_per_round * total_match_time
        rounds_per_day = int(daily_minutes // round_duration)
        total_tournament_capacity = rounds_per_day * tournament_days * matches_per_round * matches_per_clash
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Groups", num_groups)
    with col2:
        st.metric("Tournament Rounds", total_rounds)
    with col3:
        st.metric("Total Matches", total_matches)
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
            st.metric("Match + Break Time", f"{total_match_time} min")
            st.metric("Rounds per Day", rounds_per_day)
        
        with col2:
            st.metric("Courts Available", num_courts)
            st.metric("Courts Needed per Round", courts_needed_per_round)
            st.metric("Tournament Days", tournament_days)
        
        with col3:
            st.metric("Matches per Round", matches_per_round * matches_per_clash)
            st.metric("Batches per Round", batches_per_round)
            st.metric("Court Utilization", f"{min(100, (courts_needed_per_round/num_courts)*100):.1f}%")
        
        # Capacity breakdown explanation
        if num_courts >= courts_needed_per_round:
            st.success(f"""
            ✅ **Optimal Scheduling**: All {courts_needed_per_round} matches in each round can play simultaneously!
            - Round duration: {total_match_time} minutes (all matches parallel)
            - Rounds per day: {rounds_per_day}
            - Total capacity: {rounds_per_day * tournament_days * matches_per_round * matches_per_clash} matches
            """)
        else:
            st.info(f"""
            ℹ️ **Sequential Scheduling**: {courts_needed_per_round} matches need to be split into {batches_per_round} batches.
            - Each round takes {batches_per_round * total_match_time} minutes ({batches_per_round} batches)
            - Rounds per day: {rounds_per_day}
            - Total capacity: {rounds_per_day * tournament_days * matches_per_round * matches_per_clash} matches
            """)
    
    # Capacity analysis
    if total_matches <= total_tournament_capacity:
        st.success(f"✅ Schedule feasible! {total_tournament_capacity - total_matches} extra slots available.")
    else:
        shortage = total_matches - total_tournament_capacity
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
        if st.button("🚀 Generate Schedule", type="primary", disabled=total_matches > total_tournament_capacity):
            if schedule_type == "Round Robin (All groups play each other)":
                with st.spinner("Generating optimized schedule..."):
                    schedule = generate_round_robin_schedule(
                        list(st.session_state.groups.keys()),
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
                display_df = display_df[['date', 'round_number', 'court', 'Match Time', 'group1', 'group2', 'match_number']]
                display_df.columns = ['Date', 'Round', 'Court', 'Time', 'Group 1', 'Group 2', 'Match #']
                
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
                        st.write(f"Match {match['match_number']}")
        
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
                        st.write(f"#{match['match_number']}")
        
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
elif menu == "Standings & Qualifiers":
    st.header("🏆 Current Standings")
    
    # Sort logic: Most Wins, then most Points
    sorted_df = st.session_state.standings.sort_values(by=["Clash Wins", "Total Points"], ascending=False)
    
    # Display Table
    st.table(sorted_df)

    # Qualification Logic
    top_4 = sorted_df.head(4).index.tolist()
    st.success(f"**Current Semi-Finalists:** {', '.join(top_4)}")
    
    

# --- TAB 5: RECORD A CLASH ---
elif menu == "Record a Clash":
    st.header("⚔️ Record Group vs Group Clash")
    
    col1, col2 = st.columns(2)
    with col1:
        # Display group names with their proper names
        group_options = list(st.session_state.groups.keys())
        g1 = st.selectbox("Select Group 1", group_options, index=0)
    with col2:
        g2 = st.selectbox("Select Group 2", group_options, index=1 if len(group_options) > 1 else 0)

    if g1 == g2:
        st.error("Please select two different groups.")
    else:
        st.subheader(f"Match Details: {g1} vs {g2}")
        st.info("Each group plays 5 doubles matches. A player can only play once. Enter scores for each set.")
        
        clash_data = []
        g1_clash_points = 0
        g2_clash_points = 0
        g1_match_wins = 0
        g2_match_wins = 0

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

        for i in range(5):
            with st.expander(f"🏸 Doubles Match #{i+1}", expanded=True):
                # Player selection
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**{g1} Team**")
                    p1 = st.multiselect(f"Select 2 players from {g1}", 
                                       st.session_state.groups[g1], 
                                       max_selections=2, 
                                       key=f"g1_m{i}")
                with col2:
                    st.markdown(f"**{g2} Team**")
                    p2 = st.multiselect(f"Select 2 players from {g2}", 
                                       st.session_state.groups[g2], 
                                       max_selections=2, 
                                       key=f"g2_m{i}")
                
                st.divider()
                
                # Set scores input
                st.markdown("**Set Scores** (Enter points for each set)")
                
                # Set 1
                set1_col1, set1_col2, set1_col3 = st.columns([1, 1, 2])
                with set1_col1:
                    set1_g1 = st.number_input(f"Set 1 - {g1}", min_value=0, max_value=30, value=0, key=f"set1_g1_{i}")
                with set1_col2:
                    set1_g2 = st.number_input(f"Set 1 - {g2}", min_value=0, max_value=30, value=0, key=f"set1_g2_{i}")
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
                    set2_g1 = st.number_input(f"Set 2 - {g1}", min_value=0, max_value=30, value=0, key=f"set2_g1_{i}")
                with set2_col2:
                    set2_g2 = st.number_input(f"Set 2 - {g2}", min_value=0, max_value=30, value=0, key=f"set2_g2_{i}")
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
                                            key=f"set3_g1_{i}")
                with set3_col2:
                    set3_g2 = st.number_input(f"Set 3 - {g2}", 
                                            min_value=0, max_value=30, value=0, 
                                            disabled=match_decided,
                                            key=f"set3_g2_{i}")
                with set3_col3:
                    if match_decided:
                        st.info("🚫 Set 3 not needed - match already decided")
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
                
                if winner == "g1":
                    st.success(f"🏆 **{g1} wins this match!** ({total_sets_g1}-{total_sets_g2}) - {points} points")
                    g1_clash_points += points
                    g1_match_wins += 1
                elif winner == "g2":
                    st.success(f"🏆 **{g2} wins this match!** ({total_sets_g2}-{total_sets_g1}) - {points} points")
                    g2_clash_points += points
                    g2_match_wins += 1
                else:
                    st.warning("⏳ Match incomplete or tied")
        
        # Display current clash summary
        st.divider()
        st.subheader("📊 Current Clash Summary")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(f"{g1} Match Wins", g1_match_wins)
            st.metric(f"{g1} Points", g1_clash_points)
        with col2:
            st.metric("vs", "-")
        with col3:
            st.metric(f"{g2} Match Wins", g2_match_wins)
            st.metric(f"{g2} Points", g2_clash_points)
        
        if g1_match_wins > g2_match_wins:
            st.success(f"🏆 **{g1} is currently leading the clash!**")
        elif g2_match_wins > g1_match_wins:
            st.success(f"🏆 **{g2} is currently leading the clash!**")
        else:
            st.info("🤝 Clash is currently tied!")

        if st.button("Submit Clash Results", type="primary"):
            # Update Standings
            if g1_match_wins > g2_match_wins:
                st.session_state.standings.at[g1, "Clash Wins"] += 1
            elif g2_match_wins > g1_match_wins:
                st.session_state.standings.at[g2, "Clash Wins"] += 1
            
            st.session_state.standings.at[g1, "Total Points"] += g1_clash_points
            st.session_state.standings.at[g2, "Total Points"] += g2_clash_points
            
            st.balloons()
            st.success(f"🎉 Clash recorded! {g1}: {g1_clash_points} points | {g2}: {g2_clash_points} points")

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