# Checklist TODO: Constraint appears in PRAGMA table_info output
# Checklist TODO: Duplicate inserts trigger SQLite integrity errors
# Checklist TODO: Constraint name matches 'unique_name_value'
import pytest
import sqlite3

def test_claim_c2():
    # Given: In-memory SQLite DB with table and unique constraint
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE test_table (
            name TEXT,
            value TEXT,
            CONSTRAINT unique_name_value UNIQUE (name, value)
        )
    ''')
    conn.commit()

    # When: Inspect schema using PRAGMA statements
    cursor.execute("PRAGMA index_list(test_table)")
    indexes = cursor.fetchall()

    # Then: Constraint exists in index list
    assert any(idx[1] == 'unique_name_value' for idx in indexes), "Unique constraint missing"

    # When: Insert valid data
    cursor.execute("INSERT INTO test_table (name, value) VALUES ('test', 'value')")

    # Then: Duplicate insert raises integrity error
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("INSERT INTO test_table (name, value) VALUES ('test', 'value')")

    conn.close()
