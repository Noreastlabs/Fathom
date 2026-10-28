PRAGMA foreign_keys = ON;
PRAGMA application_id = 1178686536;
PRAGMA user_version = 2;
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL) STRICT;
INSERT INTO metadata VALUES ('data_schema_version','2');
INSERT INTO metadata VALUES ('committed_seq','0');
CREATE TABLE profile (
 singleton INTEGER PRIMARY KEY CHECK(singleton=1),
 profile_id TEXT NOT NULL UNIQUE,
 format_magic TEXT NOT NULL CHECK(format_magic='Fathom.LocalProfile'),
 created_utc TEXT NOT NULL
) STRICT;
CREATE TABLE session (
 session_id TEXT PRIMARY KEY NOT NULL,
 started_utc TEXT NOT NULL,
 timezone TEXT NOT NULL,
 planned_seconds INTEGER CHECK(planned_seconds BETWEEN 1 AND 14400),
 plan_ref BLOB
) STRICT;
CREATE TABLE session_close (
 session_id TEXT PRIMARY KEY REFERENCES session(session_id),
 ended_utc TEXT NOT NULL,
 outcome TEXT NOT NULL CHECK(outcome IN ('complete','partial','interrupted','cancelled'))
) STRICT;
CREATE TABLE identity (
  owner TEXT PRIMARY KEY NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('Attempt','FreeplayActivity')),
  session_id TEXT REFERENCES session(session_id),
  allocation_utc TEXT NOT NULL,
  context_bytes BLOB NOT NULL,
  CHECK((kind='Attempt' AND session_id IS NOT NULL) OR (kind='FreeplayActivity' AND session_id IS NULL))
) STRICT;
CREATE TABLE pending (
  owner TEXT PRIMARY KEY NOT NULL REFERENCES identity(owner),
  version INTEGER NOT NULL CHECK(version=1),
  payload BLOB NOT NULL,
  digest TEXT NOT NULL CHECK(length(digest)=64)
);
CREATE TABLE finalized (
  owner TEXT PRIMARY KEY NOT NULL REFERENCES identity(owner),
  payload BLOB NOT NULL,
  digest TEXT NOT NULL CHECK(length(digest)=64),
  committed_seq INTEGER NOT NULL UNIQUE CHECK(committed_seq > 0),
  practice_utc TEXT NOT NULL,
  timezone TEXT NOT NULL,
  local_day TEXT NOT NULL,
  active_num TEXT NOT NULL,
  active_den TEXT NOT NULL,
  outcome TEXT NOT NULL CHECK(outcome IN ('complete','partial','interrupted','cancelled')),
  assessment TEXT CHECK(assessment IN ('Struggling','Developing','Clean','Easy'))
) STRICT;
CREATE TABLE checkpoint (
  owner TEXT PRIMARY KEY NOT NULL REFERENCES identity(owner),
  generation INTEGER NOT NULL CHECK(generation >= 0),
  sequence INTEGER NOT NULL CHECK(sequence >= 0),
  payload BLOB NOT NULL
);
CREATE TABLE late_evidence (
  event_key TEXT PRIMARY KEY NOT NULL,
  owner TEXT NOT NULL REFERENCES identity(owner),
  received_utc TEXT NOT NULL,
  payload BLOB NOT NULL,
  digest TEXT NOT NULL CHECK(length(digest)=64)
);
CREATE TRIGGER identity_no_update BEFORE UPDATE ON identity BEGIN SELECT RAISE(ABORT,'immutable identity'); END;
CREATE TRIGGER identity_no_delete BEFORE DELETE ON identity BEGIN SELECT RAISE(ABORT,'retain identity'); END;
CREATE TRIGGER pending_no_update BEFORE UPDATE ON pending BEGIN SELECT RAISE(ABORT,'immutable pending'); END;
CREATE TRIGGER pending_no_loss BEFORE DELETE ON pending
WHEN NOT EXISTS(SELECT 1 FROM finalized f WHERE f.owner=OLD.owner AND f.payload=OLD.payload AND f.digest=OLD.digest)
BEGIN SELECT RAISE(ABORT,'pending must be preserved until matching final'); END;
CREATE TRIGGER final_requires_pending BEFORE INSERT ON finalized
WHEN NOT EXISTS(SELECT 1 FROM pending p WHERE p.owner=NEW.owner AND p.payload=NEW.payload AND p.digest=NEW.digest)
BEGIN SELECT RAISE(ABORT,'final requires matching pending'); END;
CREATE TRIGGER final_no_update BEFORE UPDATE ON finalized BEGIN SELECT RAISE(ABORT,'immutable final'); END;
CREATE TRIGGER final_no_delete BEFORE DELETE ON finalized BEGIN SELECT RAISE(ABORT,'retain final'); END;
CREATE TRIGGER checkpoint_after_final_insert BEFORE INSERT ON checkpoint
WHEN EXISTS(SELECT 1 FROM finalized f WHERE f.owner=NEW.owner)
BEGIN SELECT RAISE(ABORT,'final result supersedes checkpoint'); END;
CREATE TRIGGER checkpoint_after_final_update BEFORE UPDATE ON checkpoint
WHEN EXISTS(SELECT 1 FROM finalized f WHERE f.owner=NEW.owner)
BEGIN SELECT RAISE(ABORT,'final result supersedes checkpoint'); END;
CREATE TRIGGER checkpoint_monotone BEFORE UPDATE ON checkpoint
WHEN NEW.generation < OLD.generation OR (NEW.generation=OLD.generation AND NEW.sequence < OLD.sequence)
BEGIN SELECT RAISE(ABORT,'stale checkpoint position'); END;
CREATE TRIGGER checkpoint_same_position_conflict BEFORE UPDATE ON checkpoint
WHEN NEW.generation=OLD.generation AND NEW.sequence=OLD.sequence AND NEW.payload!=OLD.payload
BEGIN SELECT RAISE(ABORT,'conflicting checkpoint at same position'); END;
CREATE TRIGGER late_no_update BEFORE UPDATE ON late_evidence BEGIN SELECT RAISE(ABORT,'immutable late evidence'); END;
CREATE TRIGGER late_no_delete BEFORE DELETE ON late_evidence BEGIN SELECT RAISE(ABORT,'retain late evidence'); END;


CREATE TABLE acknowledgment (
 fact_id TEXT PRIMARY KEY NOT NULL,
 item_id TEXT NOT NULL,
 content_revision INTEGER NOT NULL CHECK(content_revision>0),
 acknowledged_utc TEXT NOT NULL,
 committed_seq INTEGER NOT NULL UNIQUE CHECK(committed_seq>0)
) STRICT;
CREATE TABLE source_attestation (
 fact_id TEXT PRIMARY KEY NOT NULL,
 owner TEXT REFERENCES identity(owner),
 item_id TEXT NOT NULL,
 content_revision INTEGER NOT NULL CHECK(content_revision>0),
 rubric_ref BLOB NOT NULL,
 context_bytes BLOB NOT NULL,
 take_id TEXT NOT NULL,
 work_id TEXT NOT NULL,
 performer_ref TEXT NOT NULL REFERENCES profile(profile_id),
 practice_utc TEXT NOT NULL,
 timezone TEXT NOT NULL,
 local_day TEXT NOT NULL,
 payload BLOB NOT NULL,
 digest TEXT NOT NULL CHECK(length(digest)=64),
 committed_seq INTEGER NOT NULL UNIQUE CHECK(committed_seq>0)
) STRICT;
CREATE INDEX attestation_take ON source_attestation(item_id,content_revision,take_id);
CREATE TABLE preferences (
 key TEXT PRIMARY KEY NOT NULL,
 namespace_version INTEGER NOT NULL CHECK(namespace_version>0),
 revision INTEGER NOT NULL CHECK(revision>0),
 value_bytes BLOB NOT NULL
) STRICT;
CREATE TABLE projection_cache (
 cache_key TEXT PRIMARY KEY NOT NULL,
 evidence_marker INTEGER NOT NULL CHECK(evidence_marker>=0),
 evidence_sha256 TEXT NOT NULL CHECK(length(evidence_sha256)=64),
 content_selection_sha256 TEXT NOT NULL CHECK(length(content_selection_sha256)=64),
 rule_version TEXT NOT NULL,
 as_of_utc TEXT NOT NULL,
 value_bytes BLOB NOT NULL
) STRICT;
CREATE TRIGGER session_closed_no_new_attempt BEFORE INSERT ON identity
WHEN NEW.session_id IS NOT NULL AND EXISTS(SELECT 1 FROM session_close WHERE session_id=NEW.session_id)
BEGIN SELECT RAISE(ABORT,'session closed'); END;
CREATE TRIGGER session_close_requires_settled BEFORE INSERT ON session_close
WHEN EXISTS(SELECT 1 FROM identity i LEFT JOIN finalized f ON f.owner=i.owner WHERE i.session_id=NEW.session_id AND f.owner IS NULL)
BEGIN SELECT RAISE(ABORT,'unresolved session outcome'); END;
CREATE TRIGGER preference_revision BEFORE UPDATE ON preferences
WHEN NEW.key!=OLD.key OR NEW.revision!=OLD.revision+1
BEGIN SELECT RAISE(ABORT,'preference revision conflict'); END;
CREATE TRIGGER profile_no_update BEFORE UPDATE ON profile BEGIN SELECT RAISE(ABORT,'immutable profile'); END;
CREATE TRIGGER profile_no_delete BEFORE DELETE ON profile BEGIN SELECT RAISE(ABORT,'immutable profile'); END;
CREATE TRIGGER session_no_update BEFORE UPDATE ON session BEGIN SELECT RAISE(ABORT,'immutable session'); END;
CREATE TRIGGER session_no_delete BEFORE DELETE ON session BEGIN SELECT RAISE(ABORT,'immutable session'); END;
CREATE TRIGGER session_close_no_update BEFORE UPDATE ON session_close BEGIN SELECT RAISE(ABORT,'immutable session_close'); END;
CREATE TRIGGER session_close_no_delete BEFORE DELETE ON session_close BEGIN SELECT RAISE(ABORT,'immutable session_close'); END;
CREATE TRIGGER acknowledgment_no_update BEFORE UPDATE ON acknowledgment BEGIN SELECT RAISE(ABORT,'immutable acknowledgment'); END;
CREATE TRIGGER acknowledgment_no_delete BEFORE DELETE ON acknowledgment BEGIN SELECT RAISE(ABORT,'immutable acknowledgment'); END;
CREATE TRIGGER source_attestation_no_update BEFORE UPDATE ON source_attestation BEGIN SELECT RAISE(ABORT,'immutable source_attestation'); END;
CREATE TRIGGER source_attestation_no_delete BEFORE DELETE ON source_attestation BEGIN SELECT RAISE(ABORT,'immutable source_attestation'); END;

CREATE TABLE rule_observation (
 fact_id TEXT PRIMARY KEY NOT NULL,
 rule_version TEXT NOT NULL,
 rule_config BLOB NOT NULL,
 rule_config_sha256 TEXT NOT NULL CHECK(length(rule_config_sha256)=64),
 evidence_marker INTEGER NOT NULL CHECK(evidence_marker>=0),
 evidence_sha256 TEXT NOT NULL CHECK(length(evidence_sha256)=64),
 content_selection BLOB NOT NULL,
 content_selection_sha256 TEXT NOT NULL CHECK(length(content_selection_sha256)=64),
 as_of_utc TEXT NOT NULL,
 displayed_state BLOB NOT NULL,
 displayed_state_sha256 TEXT NOT NULL CHECK(length(displayed_state_sha256)=64)
) STRICT;
CREATE TRIGGER rule_observation_no_update BEFORE UPDATE ON rule_observation BEGIN SELECT RAISE(ABORT,'immutable rule observation'); END;
CREATE TRIGGER rule_observation_no_delete BEFORE DELETE ON rule_observation BEGIN SELECT RAISE(ABORT,'retain rule observation'); END;

-- Fathom suite review additive schema2: old authoritative tables untouched.
CREATE TABLE suite_fact (
 fact_id TEXT PRIMARY KEY NOT NULL,
 suite_id TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('definition','member','review')),
 operation_id TEXT NOT NULL UNIQUE,
 recorded_utc TEXT NOT NULL,
 payload BLOB NOT NULL,
 digest TEXT NOT NULL CHECK(length(digest)=64),
 committed_seq INTEGER NOT NULL UNIQUE CHECK(committed_seq>0)
) STRICT;
CREATE UNIQUE INDEX suite_definition_unique ON suite_fact(suite_id) WHERE kind='definition';
CREATE UNIQUE INDEX suite_review_unique ON suite_fact(suite_id) WHERE kind='review';
CREATE TRIGGER suite_fact_no_update BEFORE UPDATE ON suite_fact BEGIN SELECT RAISE(ABORT,'immutable suite fact'); END;
CREATE TRIGGER suite_fact_no_delete BEFORE DELETE ON suite_fact BEGIN SELECT RAISE(ABORT,'retain suite fact'); END;
CREATE TRIGGER suite_member_after_review BEFORE INSERT ON suite_fact
WHEN NEW.kind='member' AND EXISTS(SELECT 1 FROM suite_fact WHERE suite_id=NEW.suite_id AND kind='review')
BEGIN SELECT RAISE(ABORT,'suite membership frozen'); END;
