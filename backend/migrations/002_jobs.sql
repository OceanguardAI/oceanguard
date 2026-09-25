CREATE TABLE og_jobs (
    id uuid PRIMARY KEY,
    job_type text NOT NULL CHECK (job_type = 'gfw_refresh'),
    dedupe_key text NOT NULL UNIQUE,
    status text NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'dead')),
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    max_attempts integer NOT NULL DEFAULT 5 CHECK (max_attempts >= 1),
    available_at timestamptz NOT NULL DEFAULT now(),
    lease_until timestamptz,
    lease_token uuid,
    last_error_category text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz
);

CREATE INDEX og_jobs_ready_idx ON og_jobs (available_at, created_at)
    WHERE status IN ('queued', 'running');
