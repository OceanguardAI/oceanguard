CREATE TABLE og_acquisitions (
    id text PRIMARY KEY,
    source_id text NOT NULL,
    sensor text NOT NULL,
    external_id text,
    started_at timestamptz NOT NULL,
    ended_at timestamptz,
    footprint geometry(Geometry, 4326),
    resolution_m double precision CHECK (resolution_m IS NULL OR resolution_m > 0),
    evidence_uri text,
    UNIQUE (source_id, external_id)
);
CREATE INDEX og_acquisitions_time_idx ON og_acquisitions (started_at, ended_at);

CREATE TABLE og_evidence (
    id text PRIMARY KEY,
    kind text NOT NULL CHECK (kind IN ('sar_image', 'video_frame', 'model_output', 'ais_export', 'report')),
    object_uri text NOT NULL,
    sha256 text NOT NULL,
    acquisition_id text REFERENCES og_acquisitions(id),
    model_version text,
    captured_at timestamptz
);
CREATE UNIQUE INDEX og_evidence_digest_idx ON og_evidence (sha256, object_uri);

CREATE TABLE og_observations (
    id text PRIMARY KEY,
    source_id text NOT NULL,
    acquisition_id text REFERENCES og_acquisitions(id),
    observed_at timestamptz NOT NULL,
    ingested_at timestamptz NOT NULL DEFAULT now(),
    geom geometry(Point, 4326) NOT NULL,
    uncertainty_m double precision CHECK (uncertainty_m IS NULL OR uncertainty_m >= 0),
    model_version text,
    status text NOT NULL CHECK (status IN ('candidate', 'accepted', 'rejected')),
    evidence_id text REFERENCES og_evidence(id)
);
CREATE INDEX og_observations_geom_idx ON og_observations USING gist (geom);
CREATE INDEX og_observations_time_idx ON og_observations (observed_at, source_id);

CREATE TABLE og_ais_messages (
    id text PRIMARY KEY,
    mmsi text NOT NULL,
    message_at timestamptz NOT NULL,
    received_at timestamptz NOT NULL,
    geom geometry(Point, 4326) NOT NULL,
    sog_knots double precision CHECK (sog_knots IS NULL OR sog_knots >= 0),
    cog_degrees double precision CHECK (cog_degrees IS NULL OR cog_degrees BETWEEN 0 AND 360),
    heading_degrees double precision CHECK (heading_degrees IS NULL OR heading_degrees BETWEEN 0 AND 360),
    navigation_status text,
    quality text
);
CREATE INDEX og_ais_messages_geom_idx ON og_ais_messages USING gist (geom);
CREATE INDEX og_ais_messages_time_idx ON og_ais_messages (message_at, mmsi);

CREATE TABLE og_tracks (
    id text PRIMARY KEY,
    source_id text NOT NULL,
    state text NOT NULL CHECK (state IN ('tentative', 'confirmed', 'predicted', 'lost', 'ended')),
    first_observed_at timestamptz NOT NULL,
    last_observed_at timestamptz NOT NULL,
    identity_hypothesis text,
    identity_confidence double precision CHECK (identity_confidence IS NULL OR identity_confidence BETWEEN 0 AND 1)
);
CREATE INDEX og_tracks_state_idx ON og_tracks (state, last_observed_at);

CREATE TABLE og_track_points (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    track_id text NOT NULL REFERENCES og_tracks(id),
    observed_at timestamptz NOT NULL,
    geom geometry(Point, 4326) NOT NULL,
    is_predicted boolean NOT NULL DEFAULT false,
    uncertainty_m double precision CHECK (uncertainty_m IS NULL OR uncertainty_m >= 0),
    observation_id text REFERENCES og_observations(id),
    UNIQUE (track_id, observed_at)
);
CREATE INDEX og_track_points_geom_idx ON og_track_points USING gist (geom);
CREATE INDEX og_track_points_time_idx ON og_track_points (track_id, observed_at);

CREATE TABLE og_associations (
    id text PRIMARY KEY,
    observation_id text NOT NULL REFERENCES og_observations(id),
    track_id text REFERENCES og_tracks(id),
    ais_message_id text REFERENCES og_ais_messages(id),
    score double precision NOT NULL CHECK (score BETWEEN 0 AND 1),
    decision text NOT NULL CHECK (decision IN ('matched', 'unmatched', 'ambiguous', 'unavailable')),
    method_version text NOT NULL,
    rejection_reasons jsonb NOT NULL DEFAULT '[]'::jsonb
);
CREATE INDEX og_associations_observation_idx ON og_associations (observation_id);

CREATE TABLE og_alerts (
    id text PRIMARY KEY,
    rule_version text NOT NULL,
    severity text NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    status text NOT NULL CHECK (status IN ('open', 'acknowledged', 'resolved', 'dismissed')),
    starts_at timestamptz NOT NULL,
    ends_at timestamptz,
    uncertainty text NOT NULL,
    dedupe_key text NOT NULL UNIQUE,
    observation_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
    association_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
    evidence_ids jsonb NOT NULL DEFAULT '[]'::jsonb
);
CREATE INDEX og_alerts_status_idx ON og_alerts (status, severity, starts_at);
