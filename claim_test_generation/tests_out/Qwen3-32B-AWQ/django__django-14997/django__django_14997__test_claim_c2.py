# Checklist TODO: Constraint exists in SQLite schema metadata
# Checklist TODO: Enforces uniqueness across (name,value) pairs
# Checklist TODO: Verified via PRAGMA statements and insertion tests
import pytest
import sqlite3

def test_claim_c2(tmp_path):
    # GIVEN: Temporary SQLite database with table having unique constraint
    db_path = tmp_path / "test.sqlite"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE mymodel (
            id INTEGER PRIMARY KEY,
            name TEXT,
            value TEXT,
            UNIQUE(name, value)
        )
    """)
    conn.commit()

    # WHEN: Inspecting schema with PRAGMA statements
    cursor.execute("PRAGMA index_list(mymodel)")
    indexes = cursor.fetchall()
    conn.close()

    # THEN: Unique constraint index exists
    assert any(idx[1] == 'sqlite_autoindex_mymodel_1' for idx in indexes), "Unique constraint index missing"

    # GIVEN: Reconnect to database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("INSERT INTO mymodel (name, value) VALUES (?, ?)", ("test", "value"))
    conn.commit()

    # WHEN: Inserting duplicate (name, value)
    # THEN: IntegrityError raised
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("INSERT INTO mymodel (name, value) VALUES (?, ?)", ("test", "value"))
    conn.rollback()
    conn.close()
