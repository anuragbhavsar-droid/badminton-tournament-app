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

### Supabase + Streamlit secrets

The app reads **`SUPABASE_URL`** and **`SUPABASE_SERVICE_KEY`** (or **`SUPABASE_KEY`**) from:

1. **Environment variables** (e.g. `.env` when running locally with `load_dotenv()`), then  
2. **`st.secrets`** if env is empty — so the same keys work in **`.streamlit/secrets.toml`** and in **Streamlit Community Cloud → App → Settings → Secrets**.

Put this in **`secrets.toml` / Cloud Secrets** (with your real values):

```toml
SUPERUSER_PASSWORD = "..."
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_SERVICE_KEY = "eyJ..."   # service_role key from Supabase → Project Settings → API
```

You can keep using **`.env` for Supabase only** locally if you prefer; you do not need to duplicate keys if they are already in env.

### Superuser password (Streamlit secrets only)

The default superuser (`ritesha`) password is **not** read from `.env`. Set **`SUPERUSER_PASSWORD`** in:

- **Local:** copy `streamlit-secrets.example.toml` to **`.streamlit/secrets.toml`** next to `badminton.py` and edit the value.
- **Streamlit Community Cloud:** **App → Settings → Secrets** — add `SUPERUSER_PASSWORD = "..."` in TOML format.

Remove any `SUPERUSER_PASSWORD` line from `.env` if you had one.

4. **Migration**: If you have existing `tournament_players.json` and/or `tournament_data.json`, the app will migrate them into Supabase automatically on first load (when Supabase is configured).
5. **Standings table (full columns)**: New installs get all columns from `supabase_schema.sql`. If your project already has the old `standings` table (only `clash_wins` / `total_points`), run **`standings_migration.sql`** once in the SQL Editor so saves include matches played, clash won, points, sets, rally points, etc.

## Installation

```bash
pip install -r requirements.txt
streamlit run badminton.py
```

## Deploy on Streamlit Community Cloud

1. Push this repo to **GitHub** (the app file is **`badminton.py`** at the repository root).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → sign in with GitHub.
3. **Repository:** choose `your-username/badminton-tournament-app` (or your fork).
4. **Branch:** `main` (or `master` if that’s your default).
5. **Main file path** — use **one** of these (depends what the form asks for):
   - **Relative path (most common):** `badminton.py`
   - **If the UI says it must be a GitHub URL to a `.py` file**, paste the **blob** URL to your script, for example:
     - `https://github.com/anuragbhavsar-droid/badminton-tournament-app/blob/main/badminton.py`
     - If your default branch is `master`, use `/blob/master/badminton.py` instead of `/blob/main/`.
6. **Secrets (required):** **App → Settings → Secrets** and add at least:
   ```toml
   SUPERUSER_PASSWORD = "your-secure-password"
   SUPABASE_URL = "https://your-project.supabase.co"
   SUPABASE_SERVICE_KEY = "your-service-role-key"
   ```
   (On Cloud, `.env` is not used unless you add a custom mechanism; `load_dotenv()` still runs but won’t find secrets unless you commit `.env`, which you should not do.)

If deployment still fails, confirm **`badminton.py`** exists on GitHub at the branch you selected and the path matches exactly (case-sensitive).

## Contributing

Feel free to submit issues and enhancement requests!