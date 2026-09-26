"""PostGIS repository for observations, tracks, associations, evidence, and alerts."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.models.schemas import (
    AISMessageRecord,
    AcquisitionRecord,
    AlertRecord,
    AssociationRecord,
    EvidenceRecord,
    ObservationRecord,
    TrackPointRecord,
    TrackRecord,
)


class PostgresOperationalStore:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _connect(self):
        return psycopg.connect(self._dsn, row_factory=dict_row, connect_timeout=10)

    def insert_acquisition(self, record: AcquisitionRecord) -> AcquisitionRecord:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO og_acquisitions
                   (id, source_id, sensor, external_id, started_at, ended_at,
                    footprint, resolution_m, evidence_uri)
                   VALUES (%s, %s, %s, %s, %s, %s,
                           CASE WHEN %s IS NULL THEN NULL
                                ELSE ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326) END,
                           %s, %s)
                   ON CONFLICT (id) DO NOTHING""",
                (
                    record.id, record.source_id, record.sensor, record.external_id,
                    record.started_at, record.ended_at,
                    Jsonb(record.footprint_geojson) if record.footprint_geojson else None,
                    record.footprint_geojson, record.resolution_m, record.evidence_uri,
                ),
            )
        return record

    def insert_evidence(self, record: EvidenceRecord) -> EvidenceRecord:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO og_evidence
                   (id, kind, object_uri, sha256, acquisition_id, model_version, captured_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (id) DO NOTHING""",
                (
                    record.id, record.kind, record.object_uri, record.sha256,
                    record.acquisition_id, record.model_version, record.captured_at,
                ),
            )
        return record

    def insert_observation(self, record: ObservationRecord) -> ObservationRecord:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO og_observations
                   (id, source_id, acquisition_id, observed_at, ingested_at, geom,
                    uncertainty_m, model_version, status, evidence_id)
                   VALUES (%s, %s, %s, %s, %s,
                           ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                           %s, %s, %s, %s)
                   ON CONFLICT (id) DO NOTHING""",
                (
                    record.id, record.source_id, record.acquisition_id,
                    record.observed_at, record.ingested_at, record.lon, record.lat,
                    record.uncertainty_m, record.model_version, record.status,
                    record.evidence_id,
                ),
            )
        return record

    def insert_ais(self, record: AISMessageRecord) -> AISMessageRecord:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO og_ais_messages
                   (id, mmsi, message_at, received_at, geom, sog_knots,
                    cog_degrees, heading_degrees, navigation_status, quality)
                   VALUES (%s, %s, %s, %s,
                           ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                           %s, %s, %s, %s, %s)
                   ON CONFLICT (id) DO NOTHING""",
                (
                    record.id, record.mmsi, record.message_at, record.received_at,
                    record.lon, record.lat, record.sog_knots, record.cog_degrees,
                    record.heading_degrees, record.navigation_status, record.quality,
                ),
            )
        return record

    def insert_track(self, record: TrackRecord) -> TrackRecord:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO og_tracks
                   (id, source_id, state, first_observed_at, last_observed_at,
                    identity_hypothesis, identity_confidence)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (id) DO NOTHING""",
                (
                    record.id, record.source_id, record.state,
                    record.first_observed_at, record.last_observed_at,
                    record.identity_hypothesis, record.identity_confidence,
                ),
            )
        return record

    def insert_track_point(self, record: TrackPointRecord) -> TrackPointRecord:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO og_track_points
                   (track_id, observed_at, geom, is_predicted, uncertainty_m, observation_id)
                   VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                           %s, %s, %s)
                   ON CONFLICT (track_id, observed_at) DO NOTHING""",
                (
                    record.track_id, record.observed_at, record.lon, record.lat,
                    record.is_predicted, record.uncertainty_m, record.observation_id,
                ),
            )
        return record

    def insert_association(self, record: AssociationRecord) -> AssociationRecord:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO og_associations
                   (id, observation_id, track_id, ais_message_id, score,
                    decision, method_version, rejection_reasons)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (id) DO NOTHING""",
                (
                    record.id, record.observation_id, record.track_id,
                    record.ais_message_id, record.score, record.decision,
                    record.method_version, Jsonb(record.rejection_reasons),
                ),
            )
        return record

    def insert_alert(self, record: AlertRecord) -> AlertRecord:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO og_alerts
                   (id, rule_version, severity, status, starts_at, ends_at,
                    uncertainty, dedupe_key, observation_ids, association_ids, evidence_ids)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (dedupe_key) DO NOTHING""",
                (
                    record.id, record.rule_version, record.severity, record.status,
                    record.starts_at, record.ends_at, record.uncertainty,
                    record.dedupe_key, Jsonb(record.observation_ids),
                    Jsonb(record.association_ids), Jsonb(record.evidence_ids),
                ),
            )
        return record

    def observations(
        self,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ObservationRecord]:
        clauses: list[str] = []
        params: list[Any] = []
        if start:
            clauses.append("observed_at >= %s")
            params.append(start)
        if end:
            clauses.append("observed_at <= %s")
            params.append(end)
        if bbox:
            clauses.append("ST_Intersects(geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326))")
            params.extend(bbox)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT id, source_id, acquisition_id, observed_at, ingested_at,
                          ST_Y(geom) AS lat, ST_X(geom) AS lon, uncertainty_m,
                          model_version, status, evidence_id
                   FROM og_observations"""
                + where
                + " ORDER BY observed_at DESC, id LIMIT %s OFFSET %s",
                [*params, limit, offset],
            ).fetchall()
        return [ObservationRecord.model_validate(row) for row in rows]

    def tracks(self, limit: int = 100, offset: int = 0) -> list[TrackRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT id, source_id, state, first_observed_at, last_observed_at,
                          identity_hypothesis, identity_confidence
                   FROM og_tracks ORDER BY last_observed_at DESC, id LIMIT %s OFFSET %s""",
                (limit, offset),
            ).fetchall()
        return [TrackRecord.model_validate(row) for row in rows]

    def track_points(self, track_id: str, limit: int = 1000) -> list[TrackPointRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT track_id, observed_at, ST_Y(geom) AS lat, ST_X(geom) AS lon,
                          is_predicted, uncertainty_m, observation_id
                   FROM og_track_points WHERE track_id = %s
                   ORDER BY observed_at LIMIT %s""",
                (track_id, limit),
            ).fetchall()
        return [TrackPointRecord.model_validate(row) for row in rows]

    def alerts(self, status: str | None = None, limit: int = 100) -> list[AlertRecord]:
        params: list[Any] = []
        where = ""
        if status:
            where = " WHERE status = %s"
            params.append(status)
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT id, rule_version, severity, status, starts_at, ends_at,
                          uncertainty, dedupe_key, observation_ids, association_ids,
                          evidence_ids
                   FROM og_alerts"""
                + where
                + " ORDER BY starts_at DESC, id LIMIT %s",
                [*params, limit],
            ).fetchall()
        return [AlertRecord.model_validate(row) for row in rows]
