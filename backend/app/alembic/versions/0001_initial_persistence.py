"""Initial jobs, events, findings, evidence, and stage metrics.

Revision ID: 0001_initial
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_jobs",
        sa.Column("job_id", sa.String(36), primary_key=True),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("input_records", sa.Integer(), nullable=False),
        sa.Column("parsed_events", sa.Integer(), nullable=False),
        sa.Column("issue_count", sa.Integer(), nullable=False),
        sa.Column("finding_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(64)),
        sa.Column("engine_version", sa.String(32), nullable=False),
    )
    op.create_index("ix_analysis_jobs_status_created", "analysis_jobs", ["status", "created_at"])

    op.create_table(
        "log_events",
        sa.Column("event_id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("analysis_jobs.job_id", ondelete="CASCADE"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("source_format", sa.String(32), nullable=False),
        sa.Column("host", sa.String(255)),
        sa.Column("client_ip", sa.String(64)),
        sa.Column("user", sa.String(256)),
        sa.Column("http_method", sa.String(32)),
        sa.Column("http_target", sa.Text()),
        sa.Column("http_status", sa.Integer()),
        sa.Column("auth_outcome", sa.String(16)),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.UniqueConstraint("job_id", "event_id", name="uq_log_events_job_event"),
    )
    op.create_index("ix_log_events_job_timestamp", "log_events", ["job_id", "timestamp"])
    op.create_index("ix_log_events_job_client_ip_timestamp", "log_events", ["job_id", "client_ip", "timestamp"])
    op.create_index("ix_log_events_job_event_type_timestamp", "log_events", ["job_id", "event_type", "timestamp"])
    op.create_index("ix_log_events_job_http_status", "log_events", ["job_id", "http_status"])

    op.create_table(
        "findings",
        sa.Column("finding_id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("analysis_jobs.job_id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_id", sa.String(128), nullable=False),
        sa.Column("rule_version", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("subject", sa.String(512), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False),
        sa.Column("observed_value", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_findings_job_severity", "findings", ["job_id", "severity"])
    op.create_index("ix_findings_job_created", "findings", ["job_id", "created_at"])

    op.create_table(
        "finding_evidence",
        sa.Column("evidence_id", sa.String(36), primary_key=True),
        sa.Column("finding_id", sa.String(36), sa.ForeignKey("findings.finding_id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", sa.String(36), sa.ForeignKey("log_events.event_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("finding_id", "ordinal", name="uq_finding_evidence_ordinal"),
    )
    op.create_index("ix_finding_evidence_event", "finding_evidence", ["event_id"])

    op.create_table(
        "job_stage_metrics",
        sa.Column("metric_id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("analysis_jobs.job_id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage", sa.String(64), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("spill_bytes", sa.Integer(), nullable=False),
    )
    op.create_index("ix_job_stage_metrics_job", "job_stage_metrics", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_job_stage_metrics_job", table_name="job_stage_metrics")
    op.drop_table("job_stage_metrics")
    op.drop_index("ix_finding_evidence_event", table_name="finding_evidence")
    op.drop_table("finding_evidence")
    op.drop_index("ix_findings_job_created", table_name="findings")
    op.drop_index("ix_findings_job_severity", table_name="findings")
    op.drop_table("findings")
    op.drop_index("ix_log_events_job_http_status", table_name="log_events")
    op.drop_index("ix_log_events_job_event_type_timestamp", table_name="log_events")
    op.drop_index("ix_log_events_job_client_ip_timestamp", table_name="log_events")
    op.drop_index("ix_log_events_job_timestamp", table_name="log_events")
    op.drop_table("log_events")
    op.drop_index("ix_analysis_jobs_status_created", table_name="analysis_jobs")
    op.drop_table("analysis_jobs")
