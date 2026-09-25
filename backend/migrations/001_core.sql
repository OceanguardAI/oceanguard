CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE og_events (
    id text PRIMARY KEY,
    source text NOT NULL,
    risk_level text NOT NULL,
    review_status text NOT NULL,
    payload jsonb NOT NULL,
    geom geometry(Point, 4326) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX og_events_geom_idx ON og_events USING gist (geom);
CREATE INDEX og_events_review_idx ON og_events (review_status, risk_level);

CREATE TABLE og_reviews (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id text NOT NULL REFERENCES og_events(id),
    previous_status text NOT NULL,
    review_status text NOT NULL,
    actor_ref text,
    reviewed_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX og_reviews_event_idx ON og_reviews (event_id, id);

CREATE TABLE og_activity (
    snapshot_id uuid NOT NULL,
    id text NOT NULL,
    dataset text NOT NULL,
    detection_count integer NOT NULL CHECK (detection_count >= 0),
    report_start date NOT NULL,
    report_end date NOT NULL,
    provider_time text,
    ingested_at timestamptz NOT NULL,
    geom geometry(Point, 4326) NOT NULL,
    PRIMARY KEY (snapshot_id, id)
);
CREATE INDEX og_activity_geom_idx ON og_activity USING gist (geom);
CREATE INDEX og_activity_period_idx ON og_activity (report_start, report_end);

CREATE TABLE og_source_state (
    source_key text PRIMARY KEY,
    last_attempt_at timestamptz,
    last_success_at timestamptz,
    error_category text,
    snapshot_id uuid,
    report_start date,
    report_end date
);
