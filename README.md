# Badminton Tournament Management System

A comprehensive web application built with Streamlit for managing badminton tournaments with advanced auto-balancing capabilities.

**UI:** Amdocs-inspired theme (brand red `#ED1C24`, royal blue, gold & lime accents, Montserrat typography). Place the event banner at `assets/amdocs_banner.png` for the header (included for Amdocs Badminton Premier League).

## Features

- **Player Import & Management**: Import players via CSV/Excel, bulk text, or manual entry
- **Advanced Auto-Balance**: Create balanced groups with skill-level subgroups
- **Flexible Tournament Structure**: Configure 2-12 groups with custom player counts
- **Match Scheduling**: Generate round-robin schedules with court management
- **Standings & Qualifiers**: Track wins, points, and qualification progress
- **Fixtures & Results**: Completed clashes and upcoming pairings (with schedule dates when generated)
- **Clash Recording**: Record match results and update standings
- **Data Persistence**: Supabase (PostgreSQL) database with automatic save/load and optional JSON migration

## Live Demo

🎯 [Try the Application](https://your-app-name.streamlit.app)

## Key Capabilities

### Auto-Balance Groups
- **Skill-Level Subgroups**: Configure two skill ranges (default: Deciders 0-5, Chokers 6-15; skill levels 0-15)
- **Exact Player Counts**: Specify exact number of players per subgroup
- **Multi-Level Balance**: Ensures skill point balance at group, subgroup1, and subgroup2 levels
- **Dynamic Group Count**: Create 2-12 groups based on tournament size

### Tournament Management
- Support for 16-180+ players
- Gender balance considerations
- Skill variance minimization
- Real-time balance quality metrics

## Usage

1. **Import Players**: Add player data with names, emails, skill levels (0-15), and gender
2. **Configure Tournament**: Set number of groups and skill level ranges
3. **Auto-Balance**: Create perfectly balanced groups with optimized skill distribution
4. **Generate Schedule**: Create match schedules with court assignments
5. **Record Results**: Track match outcomes and update standings

## Technical Details

- Built with Streamlit and Pandas
- Advanced algorithms for skill-based player distribution
- Iterative optimization to minimize skill variance
- **Supabase (PostgreSQL)** for persistence
- Responsive web interface

## Database (Supabase)

1. **Create a Supabase project** at [supabase.com](https://supabase.com) and get your project URL and API keys (Project Settings → API).
2. **Create tables**: In the Supabase Dashboard, open the SQL Editor and run the script in `supabase_schema.sql` to create the required tables.
3. **Configure `.env`** with:
   - `SUPABASE_URL` – your project URL (e.g. `https://xxxxx.supabase.co`)
   - `SUPABASE_SERVICE_KEY` – the **service_role** key (not the anon key) so the app can read/write all data.
4. **Migration**: If you have existing `tournament_players.json` and/or `tournament_data.json`, the app will migrate them into Supabase automatically on first load (when Supabase is configured).
5. **Standings table (full columns)**: New installs get all columns from `supabase_schema.sql`. If your project already has the old `standings` table (only `clash_wins` / `total_points`), run **`standings_migration.sql`** once in the SQL Editor so saves include matches played, clash won, points, sets, rally points, etc.

## Installation

```bash
pip install -r requirements.txt
streamlit run badminton.py
```

## Contributing

Feel free to submit issues and enhancement requests!