-- Run once in Supabase SQL Editor if you already have the old `standings` table (3 columns only).

ALTER TABLE standings ADD COLUMN IF NOT EXISTS team_display_name TEXT NOT NULL DEFAULT '';
ALTER TABLE standings ADD COLUMN IF NOT EXISTS matches_played INT NOT NULL DEFAULT 0;
ALTER TABLE standings ADD COLUMN IF NOT EXISTS clash_won INT NOT NULL DEFAULT 0;
ALTER TABLE standings ADD COLUMN IF NOT EXISTS points INT NOT NULL DEFAULT 0;
ALTER TABLE standings ADD COLUMN IF NOT EXISTS sets_won INT NOT NULL DEFAULT 0;
ALTER TABLE standings ADD COLUMN IF NOT EXISTS sets_lost INT NOT NULL DEFAULT 0;
ALTER TABLE standings ADD COLUMN IF NOT EXISTS set_difference INT NOT NULL DEFAULT 0;
ALTER TABLE standings ADD COLUMN IF NOT EXISTS rally_points_won INT NOT NULL DEFAULT 0;
ALTER TABLE standings ADD COLUMN IF NOT EXISTS rally_points_lost INT NOT NULL DEFAULT 0;
ALTER TABLE standings ADD COLUMN IF NOT EXISTS rally_points_difference INT NOT NULL DEFAULT 0;

UPDATE standings SET clash_won = COALESCE(clash_wins, 0) WHERE clash_won = 0 AND COALESCE(clash_wins, 0) > 0;
UPDATE standings SET points = clash_won WHERE points = 0 AND clash_won > 0;
