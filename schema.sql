-- Locked schema (deployment skeleton).
-- Safe to run more than once: tables are created only if they do not exist.

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    operating_system TEXT NOT NULL
        CHECK (operating_system IN ('Android', 'iOS')),
    age SMALLINT NOT NULL
        CHECK (age BETWEEN 18 AND 120)
);

CREATE TABLE IF NOT EXISTS screen_time_observations (
    observation_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL
        REFERENCES users (user_id) ON DELETE CASCADE,
    app_usage_time_min INTEGER NOT NULL
        CHECK (app_usage_time_min >= 0),
    screen_on_time_hours NUMERIC(4, 1) NOT NULL
        CHECK (screen_on_time_hours >= 0),
    number_of_apps_installed SMALLINT NOT NULL
        CHECK (number_of_apps_installed >= 0),
    user_behavior_class SMALLINT NOT NULL
        CHECK (user_behavior_class BETWEEN 1 AND 5)
);
