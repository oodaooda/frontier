"""Tests for table ground truth CRUD, import/export."""

import json
import pytest

from frontier.database import get_db, init_db
from frontier.models.document import insert_document
from frontier.models.table_gt import (
    add_row,
    create_table_gt,
    delete_table_gt,
    export_json,
    get_row,
    get_rows,
    get_table_gt,
    get_table_gt_stats,
    import_json,
    list_table_gts,
    toggle_row_verified,
    update_cell,
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
    return insert_document(conn, "a.pdf", "A-701.pdf", 100, 1, "schedule")


class TestTableGTCRUD:
    def test_create_and_get(self, conn, doc_id):
        tgt_id = create_table_gt(conn, doc_id, "Door Schedule", ["door_no", "material", "width"])
        tgt = get_table_gt(conn, tgt_id)
        assert tgt is not None
        assert tgt.table_name == "Door Schedule"
        assert tgt.columns == ["door_no", "material", "width"]

    def test_list(self, conn, doc_id):
        create_table_gt(conn, doc_id, "Table A", ["col1"])
        create_table_gt(conn, doc_id, "Table B", ["col1", "col2"])
        tables = list_table_gts(conn, doc_id)
        assert len(tables) == 2

    def test_delete(self, conn, doc_id):
        tgt_id = create_table_gt(conn, doc_id, "Test", ["c1"])
        add_row(conn, tgt_id, 0, {"c1": "val"})
        delete_table_gt(conn, tgt_id)
        assert get_table_gt(conn, tgt_id) is None
        assert get_rows(conn, tgt_id) == []


class TestRowCRUD:
    def test_add_and_get_rows(self, conn, doc_id):
        tgt_id = create_table_gt(conn, doc_id, "Test", ["door_no", "material"])
        add_row(conn, tgt_id, 0, {"door_no": "X-01", "material": "H.M."})
        add_row(conn, tgt_id, 1, {"door_no": "X-02", "material": "WOOD"})
        rows = get_rows(conn, tgt_id)
        assert len(rows) == 2
        assert rows[0].data["door_no"] == "X-01"
        assert rows[1].data["material"] == "WOOD"

    def test_update_cell(self, conn, doc_id):
        tgt_id = create_table_gt(conn, doc_id, "Test", ["door_no", "material"])
        row_id = add_row(conn, tgt_id, 0, {"door_no": "X-01", "material": "H.M."})
        update_cell(conn, row_id, "material", "HOLLOW METAL")
        row = get_row(conn, row_id)
        assert row.data["material"] == "HOLLOW METAL"
        # Other fields unchanged
        assert row.data["door_no"] == "X-01"

    def test_toggle_verified(self, conn, doc_id):
        tgt_id = create_table_gt(conn, doc_id, "Test", ["c1"])
        row_id = add_row(conn, tgt_id, 0, {"c1": "val"})
        assert get_row(conn, row_id).verified == 0
        toggle_row_verified(conn, row_id)
        assert get_row(conn, row_id).verified == 1
        toggle_row_verified(conn, row_id)
        assert get_row(conn, row_id).verified == 0

    def test_stats(self, conn, doc_id):
        tgt_id = create_table_gt(conn, doc_id, "Test", ["c1"])
        r1 = add_row(conn, tgt_id, 0, {"c1": "a"})
        add_row(conn, tgt_id, 1, {"c1": "b"})
        add_row(conn, tgt_id, 2, {"c1": "c"})
        toggle_row_verified(conn, r1)
        stats = get_table_gt_stats(conn, tgt_id)
        assert stats["total"] == 3
        assert stats["verified"] == 1


class TestImportExport:
    def test_import_flat_array(self, conn, doc_id):
        data = json.dumps([
            {"door_no": "X-01", "material": "H.M."},
            {"door_no": "X-02", "material": "WOOD"},
        ])
        tgt_id = import_json(conn, doc_id, data, table_name="Doors")
        tgt = get_table_gt(conn, tgt_id)
        assert tgt.table_name == "Doors"
        rows = get_rows(conn, tgt_id)
        assert len(rows) == 2
        assert rows[0].data["door_no"] == "X-01"

    def test_import_structured(self, conn, doc_id):
        data = json.dumps({
            "_meta": {"sheet_title": "Door Schedule", "source": "GPT-5.4"},
            "columns": ["door_no", "material", "qty"],
            "entries": [
                {"door_no": "X-01", "material": "H.M.", "qty": "1"},
                {"door_no": "X-02", "material": "WOOD", "qty": "2"},
            ]
        })
        tgt_id = import_json(conn, doc_id, data)
        tgt = get_table_gt(conn, tgt_id)
        assert tgt.table_name == "Door Schedule"
        assert tgt.source == "GPT-5.4"
        assert tgt.columns == ["door_no", "material", "qty"]
        rows = get_rows(conn, tgt_id)
        assert len(rows) == 2

    def test_export(self, conn, doc_id):
        tgt_id = create_table_gt(conn, doc_id, "Test", ["c1", "c2"])
        add_row(conn, tgt_id, 0, {"c1": "a", "c2": "b"})
        add_row(conn, tgt_id, 1, {"c1": "c", "c2": "d"})
        json_str = export_json(conn, tgt_id)
        data = json.loads(json_str)
        assert data["_meta"]["sheet_title"] == "Test"
        assert data["columns"] == ["c1", "c2"]
        assert len(data["entries"]) == 2
        assert data["entries"][0]["c1"] == "a"

    def test_roundtrip(self, conn, doc_id):
        original = json.dumps([
            {"door_no": "PH-01", "material": "H.M.", "notes": "FPSC"},
            {"door_no": "PH-02", "material": "WOOD", "notes": "PRIVACY LOCK"},
        ])
        tgt_id = import_json(conn, doc_id, original, table_name="Roundtrip")
        exported = export_json(conn, tgt_id)
        data = json.loads(exported)
        assert data["entries"][0]["door_no"] == "PH-01"
        assert data["entries"][1]["notes"] == "PRIVACY LOCK"

    def test_import_empty_raises(self, conn, doc_id):
        with pytest.raises(ValueError):
            import_json(conn, doc_id, "[]")

    def test_import_hierarchical_schedule(self, conn, doc_id):
        """Test importing a construction schedule with nested headers/subheaders."""
        data = json.dumps({
            "project": {"title": "Demo Project Schedule"},
            "columns": ["Activity ID", "Activity Name", "Original Duration",
                        "Early Start", "Early Finish", "Total Float"],
            "structure": [
                {
                    "header": "MILESTONES",
                    "activities": [
                        {"id": "A1000", "name": "Notice to Proceed",
                         "original_duration": 0, "early_start": "9/23/24",
                         "early_finish": "9/23/24", "total_float": 0}
                    ]
                },
                {
                    "header": "PRE-CONSTRUCTION",
                    "subheaders": [
                        {
                            "subheader": "PERMITS",
                            "activities": [
                                {"id": "A3020", "name": "Submit Safety Plan",
                                 "original_duration": 10, "early_start": "9/23/24",
                                 "early_finish": "10/4/24", "total_float": 0}
                            ]
                        },
                        {
                            "subheader": "SURVEYS",
                            "activities": [
                                {"id": "A3350", "name": "Perform Soil Sampling",
                                 "original_duration": 3, "early_start": "9/25/24",
                                 "early_finish": "9/27/24", "total_float": 20}
                            ]
                        }
                    ]
                }
            ]
        })
        tgt_id = import_json(conn, doc_id, data)
        tgt = get_table_gt(conn, tgt_id)
        assert tgt.table_name == "Demo Project Schedule"
        assert "header" in tgt.columns
        assert "path" in tgt.columns
        assert "Activity ID" in tgt.columns

        rows = get_rows(conn, tgt_id)
        assert len(rows) == 3  # 1 milestone + 1 permit + 1 survey

        # Check hierarchy is preserved
        assert rows[0].data["header"] == "MILESTONES"
        assert rows[0].data["Activity ID"] == "A1000"
        assert rows[1].data["header"] == "PERMITS"
        assert rows[1].data["path"] == "PRE-CONSTRUCTION > PERMITS"
        assert rows[2].data["Activity ID"] == "A3350"
