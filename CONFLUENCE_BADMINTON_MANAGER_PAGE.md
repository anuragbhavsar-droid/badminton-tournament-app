# Badminton Manager – Content for Confluence

Copy one of the sections below into your Confluence page **[Badminton Manager](https://confluence/spaces/DEP/pages/757474661/Badminton+Manager)**.

---

## Option A: Copy this (recommended for Confluence editor)

Paste this into the Confluence page body. Confluence often keeps headings and lists when you paste.

---

**Badminton Tournament Management System**

A comprehensive web application built with Streamlit for managing badminton tournaments with advanced auto-balancing capabilities.

**Features**

- **Player Import & Management**: Import players via CSV/Excel, bulk text, or manual entry
- **Advanced Auto-Balance**: Create balanced groups with skill-level subgroups
- **Flexible Tournament Structure**: Configure 2-12 groups with custom player counts
- **Match Scheduling**: Generate round-robin schedules with court management
- **Standings & Qualifiers**: Track wins, points, and qualification progress
- **Clash Recording**: Record match results and update standings
- **Data Persistence**: Automatic saving to JSON files

**Tech Stack**

| Area | Choice |
|------|--------|
| UI | Streamlit (wide layout) |
| Data | Pandas, JSON files |
| Auth | Session-based; password hashing (SHA-256 + salt) |
| Config | python-dotenv, Streamlit secrets |
| Python | ^3.8 |

**Key Capabilities**

*Auto-Balance Groups*
- **Skill-Level Subgroups**: Configure two skill ranges (e.g., 1-5 and 6-10)
- **Exact Player Counts**: Specify exact number of players per subgroup
- **Multi-Level Balance**: Ensures skill point balance at group, subgroup1, and subgroup2 levels
- **Dynamic Group Count**: Create 2-12 groups based on tournament size

*Tournament Management*
- Support for 16-180+ players
- Gender balance considerations
- Skill variance minimization
- Real-time balance quality metrics

**Application Structure**

Single-file app `badminton.py` (~3,325 lines) includes:

- **Auth & users**: Default superuser; roles (superuser, admin); guest access for Team Details and Standings
- **Data persistence**: `tournament_players.json`, `tournament_data.json`
- **Core logic**: Auto-balance (skill 1-10, gender, subgroups, 2-12 groups), round-robin scheduling, standings and clash recording
- **Navigation**: Player Import & Auto-Balance, Setup Groups & Players, Team Details, Match Schedule, Standings & Qualifiers, Record a Clash, Manage Players, User Management

**Usage**

1. **Import Players**: Add player data with names, emails, skill levels (1-10), and gender
2. **Configure Tournament**: Set number of groups and skill level ranges
3. **Auto-Balance**: Create perfectly balanced groups with optimized skill distribution
4. **Generate Schedule**: Create match schedules with court assignments
5. **Record Results**: Track match outcomes and update standings

**Installation**

```
pip install -r requirements.txt
streamlit run badminton.py
```

Set `SUPERUSER_PASSWORD` in Streamlit secrets only (`.streamlit/secrets.toml` or Cloud Secrets), not in `.env`.

**Technical Details**

- Built with Streamlit and Pandas
- Advanced algorithms for skill-based player distribution
- Iterative optimization to minimize skill variance
- JSON-based data persistence
- Responsive web interface

**Summary**

Working Streamlit badminton tournament manager with auth, auto-balance, scheduling, and JSON persistence. Main improvement areas: splitting the monolith into modules, running tests in CI, and tightening security (e.g. stronger password hashing).

Feel free to submit issues and enhancement requests!

---

## Option B: Confluence Storage Format (HTML)

Use this if your Confluence has **Insert → Markup** (or similar) and you can paste **HTML** or **Confluence storage**. Paste only the block below (from `<h1>` to `</p>`).

```html
<h1>Badminton Tournament Management System</h1>
<p>A comprehensive web application built with Streamlit for managing badminton tournaments with advanced auto-balancing capabilities.</p>

<h2>Features</h2>
<ul>
<li><strong>Player Import &amp; Management</strong>: Import players via CSV/Excel, bulk text, or manual entry</li>
<li><strong>Advanced Auto-Balance</strong>: Create balanced groups with skill-level subgroups</li>
<li><strong>Flexible Tournament Structure</strong>: Configure 2-12 groups with custom player counts</li>
<li><strong>Match Scheduling</strong>: Generate round-robin schedules with court management</li>
<li><strong>Standings &amp; Qualifiers</strong>: Track wins, points, and qualification progress</li>
<li><strong>Clash Recording</strong>: Record match results and update standings</li>
<li><strong>Data Persistence</strong>: Automatic saving to JSON files</li>
</ul>

<h2>Tech Stack</h2>
<table>
<tr><th>Area</th><th>Choice</th></tr>
<tr><td>UI</td><td>Streamlit (wide layout)</td></tr>
<tr><td>Data</td><td>Pandas, JSON files</td></tr>
<tr><td>Auth</td><td>Session-based; password hashing (SHA-256 + salt)</td></tr>
<tr><td>Config</td><td>python-dotenv, Streamlit secrets</td></tr>
<tr><td>Python</td><td>^3.8</td></tr>
</table>

<h2>Key Capabilities</h2>
<h3>Auto-Balance Groups</h3>
<ul>
<li><strong>Skill-Level Subgroups</strong>: Configure two skill ranges (e.g. 1-5 and 6-10)</li>
<li><strong>Exact Player Counts</strong>: Specify exact number of players per subgroup</li>
<li><strong>Multi-Level Balance</strong>: Ensures skill point balance at group, subgroup1, and subgroup2 levels</li>
<li><strong>Dynamic Group Count</strong>: Create 2-12 groups based on tournament size</li>
</ul>
<h3>Tournament Management</h3>
<ul>
<li>Support for 16-180+ players</li>
<li>Gender balance considerations</li>
<li>Skill variance minimization</li>
<li>Real-time balance quality metrics</li>
</ul>

<h2>Application Structure</h2>
<p>Single-file app <code>badminton.py</code> (~3,325 lines) includes:</p>
<ul>
<li><strong>Auth &amp; users</strong>: Default superuser; roles (superuser, admin); guest access for Team Details and Standings</li>
<li><strong>Data persistence</strong>: <code>tournament_players.json</code>, <code>tournament_data.json</code></li>
<li><strong>Core logic</strong>: Auto-balance (skill 1-10, gender, subgroups, 2-12 groups), round-robin scheduling, standings and clash recording</li>
<li><strong>Navigation</strong>: Player Import &amp; Auto-Balance, Setup Groups &amp; Players, Team Details, Match Schedule, Standings &amp; Qualifiers, Record a Clash, Manage Players, User Management</li>
</ul>

<h2>Usage</h2>
<ol>
<li><strong>Import Players</strong>: Add player data with names, emails, skill levels (1-10), and gender</li>
<li><strong>Configure Tournament</strong>: Set number of groups and skill level ranges</li>
<li><strong>Auto-Balance</strong>: Create perfectly balanced groups with optimized skill distribution</li>
<li><strong>Generate Schedule</strong>: Create match schedules with court assignments</li>
<li><strong>Record Results</strong>: Track match outcomes and update standings</li>
</ol>

<h2>Installation</h2>
<pre>pip install -r requirements.txt
streamlit run badminton.py</pre>
<p>Set <code>SUPERUSER_PASSWORD</code> in Streamlit secrets only (not <code>.env</code>).</p>

<h2>Technical Details</h2>
<ul>
<li>Built with Streamlit and Pandas</li>
<li>Advanced algorithms for skill-based player distribution</li>
<li>Iterative optimization to minimize skill variance</li>
<li>JSON-based data persistence</li>
<li>Responsive web interface</li>
</ul>

<h2>Summary</h2>
<p>Working Streamlit badminton tournament manager with auth, auto-balance, scheduling, and JSON persistence. Main improvement areas: splitting the monolith into modules, running tests in CI, and tightening security (e.g. stronger password hashing).</p>
<p>Feel free to submit issues and enhancement requests!</p>
```

---

*Page: [Badminton Manager](https://confluence/spaces/DEP/pages/757474661/Badminton+Manager)*
