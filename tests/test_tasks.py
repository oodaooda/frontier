"""Tests for ground truth task CRUD, versioning, and YAML import/export."""

import pytest

from frontier.database import get_db, init_db
from frontier.models.document import insert_document
from frontier.models.task import (
    bulk_verify,
    delete_task,
    export_to_yaml,
    get_gt_version,
    get_task,
    get_task_stats,
    import_from_yaml,
    insert_task,
    list_tasks,
    snapshot_gt,
    toggle_verified,
    update_task,
)


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.db"
    init_db(path)
    return path


@pytest.fixture
def conn(db_path):
    c = get_db(db_path)
    yield c
    c.close()


@pytest.fixture
def doc_id(conn):
    return insert_document(conn, "a.pdf", "A700_door_schedule.pdf", 100, 1, "schedule")


class TestTaskCRUD:
    def test_insert_and_get(self, conn, doc_id):
        task_id = insert_task(
            conn, doc_id, "door-t1-001", 1, 1, "schedule",
            "How many doors?", "42", "exact",
        )
        task = get_task(conn, task_id)
        assert task is not None
        assert task.question == "How many doors?"
        assert task.expected_answer == "42"
        assert task.tier == 1
        assert task.verified == 0

    def test_list_tasks(self, conn, doc_id):
        insert_task(conn, doc_id, "t1", 1, 1, "table", "Q1", "A1")
        insert_task(conn, doc_id, "t2", 1, 2, "schedule", "Q2", "A2")
        insert_task(conn, doc_id, "t3", 2, 1, "table", "Q3", "A3")

        all_tasks = list_tasks(conn, doc_id)
        assert len(all_tasks) == 3

        page1_tasks = list_tasks(conn, doc_id, page_number=1)
        assert len(page1_tasks) == 2

        page2_tasks = list_tasks(conn, doc_id, page_number=2)
        assert len(page2_tasks) == 1

    def test_update_task(self, conn, doc_id):
        task_id = insert_task(conn, doc_id, "t1", 1, 1, "table", "Q?", "A")
        update_task(conn, task_id, expected_answer="B", tier=2)
        task = get_task(conn, task_id)
        assert task.expected_answer == "B"
        assert task.tier == 2

    def test_update_ignores_invalid_fields(self, conn, doc_id):
        task_id = insert_task(conn, doc_id, "t1", 1, 1, "table", "Q?", "A")
        update_task(conn, task_id, evil="DROP TABLE")
        task = get_task(conn, task_id)
        assert task.question == "Q?"

    def test_delete_task(self, conn, doc_id):
        task_id = insert_task(conn, doc_id, "t1", 1, 1, "table", "Q?", "A")
        delete_task(conn, task_id)
        assert get_task(conn, task_id) is None

    def test_toggle_verified(self, conn, doc_id):
        task_id = insert_task(conn, doc_id, "t1", 1, 1, "table", "Q?", "A")
        assert get_task(conn, task_id).verified == 0
        toggle_verified(conn, task_id)
        assert get_task(conn, task_id).verified == 1
        toggle_verified(conn, task_id)
        assert get_task(conn, task_id).verified == 0

    def test_bulk_verify(self, conn, doc_id):
        insert_task(conn, doc_id, "t1", 1, 1, "table", "Q1", "A1")
        insert_task(conn, doc_id, "t2", 1, 1, "table", "Q2", "A2")
        insert_task(conn, doc_id, "t3", 2, 1, "table", "Q3", "A3")
        count = bulk_verify(conn, doc_id, page_number=1)
        assert count == 2

        tasks = list_tasks(conn, doc_id, page_number=1)
        assert all(t.verified == 1 for t in tasks)
        # Page 2 unaffected
        tasks_p2 = list_tasks(conn, doc_id, page_number=2)
        assert tasks_p2[0].verified == 0

    def test_task_stats(self, conn, doc_id):
        insert_task(conn, doc_id, "t1", 1, 1, "table", "Q1", "A1", verified=1)
        insert_task(conn, doc_id, "t2", 1, 1, "table", "Q2", "A2", verified=0)
        insert_task(conn, doc_id, "t3", 1, 1, "table", "Q3", "A3", verified=1)
        stats = get_task_stats(conn, doc_id)
        assert stats["total"] == 3
        assert stats["verified"] == 2
        assert stats["unverified"] == 1


class TestVersioning:
    def test_version_starts_at_zero(self, conn, doc_id):
        assert get_gt_version(conn, doc_id) == 0

    def test_insert_bumps_version(self, conn, doc_id):
        insert_task(conn, doc_id, "t1", 1, 1, "table", "Q?", "A")
        assert get_gt_version(conn, doc_id) == 1

    def test_update_bumps_version(self, conn, doc_id):
        task_id = insert_task(conn, doc_id, "t1", 1, 1, "table", "Q?", "A")
        v1 = get_gt_version(conn, doc_id)
        update_task(conn, task_id, expected_answer="B")
        v2 = get_gt_version(conn, doc_id)
        assert v2 > v1

    def test_delete_bumps_version(self, conn, doc_id):
        task_id = insert_task(conn, doc_id, "t1", 1, 1, "table", "Q?", "A")
        v1 = get_gt_version(conn, doc_id)
        delete_task(conn, task_id)
        v2 = get_gt_version(conn, doc_id)
        assert v2 > v1

    def test_snapshot(self, conn, doc_id):
        insert_task(conn, doc_id, "t1", 1, 1, "table", "Q?", "A")
        version_id = snapshot_gt(conn, doc_id)
        assert version_id is not None

        row = conn.execute(
            "SELECT snapshot FROM gt_versions WHERE id = ?", (version_id,)
        ).fetchone()
        assert row["snapshot"] is not None
        import json
        tasks = json.loads(row["snapshot"])
        assert len(tasks) == 1
        assert tasks[0]["question"] == "Q?"


class TestYAMLImportExport:
    def test_export(self, conn, doc_id):
        insert_task(conn, doc_id, "door-t1-001", 1, 1, "schedule",
                    "How many doors?", "42", "exact", notes="Count all rows")
        yaml_str = export_to_yaml(conn, doc_id)
        assert "door-t1-001" in yaml_str
        assert "How many doors?" in yaml_str
        assert "42" in yaml_str

    def test_import(self, conn, doc_id):
        yaml_content = """
document: A700_door_schedule.pdf
tasks:
  - id: imported-001
    page: 1
    tier: 1
    category: schedule
    question: "What is the sheet title?"
    expected: "DOOR SCHEDULE"
    scoring: exact
    verified: true
  - id: imported-002
    page: 1
    tier: 2
    category: schedule
    question: "How many floors?"
    expected: "5"
    scoring: exact
"""
        count = import_from_yaml(conn, doc_id, yaml_content)
        assert count == 2

        tasks = list_tasks(conn, doc_id)
        assert len(tasks) == 2
        assert tasks[0].task_key == "imported-001"
        assert tasks[0].verified == 1

    def test_import_skips_duplicates(self, conn, doc_id):
        insert_task(conn, doc_id, "existing-001", 1, 1, "table", "Q?", "A")
        yaml_content = """
document: test.pdf
tasks:
  - id: existing-001
    page: 1
    tier: 1
    category: table
    question: "Duplicate"
    expected: "Dup"
    scoring: exact
  - id: new-001
    page: 1
    tier: 1
    category: table
    question: "New question"
    expected: "New answer"
    scoring: exact
"""
        count = import_from_yaml(conn, doc_id, yaml_content)
        assert count == 1  # Only new-001 imported

    def test_roundtrip(self, conn, doc_id):
        insert_task(conn, doc_id, "rt-001", 1, 1, "schedule",
                    "Test question?", "Test answer", "contains",
                    tolerance=None, notes="A note", verified=1)
        yaml_str = export_to_yaml(conn, doc_id)

        # Import into a different document
        doc_id2 = insert_document(conn, "b.pdf", "b.pdf", 100, 1)
        count = import_from_yaml(conn, doc_id2, yaml_str)
        assert count == 1
        tasks = list_tasks(conn, doc_id2)
        assert tasks[0].question == "Test question?"
        assert tasks[0].verified == 1
