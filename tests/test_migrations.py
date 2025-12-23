import pytest
import os

# Note: Migration tests require a PostgreSQL database with pgvector extension.
# For CI, use GitHub Actions PostgreSQL service or a test container.
# These tests are skipped by default if no TEST_DATABASE_URL is set.

TEST_DB_URL = os.getenv("TEST_DATABASE_URL", "")


@pytest.fixture(scope="module")
def migration_db():
    """
    Fixture to provide the test database URL.
    Skips tests if no PostgreSQL test database is configured.
    """
    if not TEST_DB_URL:
        pytest.skip("TEST_DATABASE_URL not set - skipping migration tests")
    
    yield TEST_DB_URL


def test_migrations_require_postgresql():
    """
    Placeholder test to document that migrations require PostgreSQL.
    
    To run migration tests:
    1. Set TEST_DATABASE_URL to a PostgreSQL connection string
    2. The database should have pgvector extension available
    
    Example:
        TEST_DATABASE_URL=postgresql://user:pass@localhost/test_db uv run pytest tests/test_migrations.py
    """
    # This test always passes - it's just documentation
    assert True


@pytest.mark.skipif(not TEST_DB_URL, reason="TEST_DATABASE_URL not set")
def test_migrations_up_and_down(migration_db):
    """
    Verifies that the Alembic migrations can:
    1. Upgrade to the latest revision (head).
    2. Downgrade back to the beginning (base).
    This ensures the migration scripts are valid and reversible.
    """
    from tests.utils.migrations import run_migrations_up, run_migrations_down
    
    try:
        # 1. Test Upgrade
        run_migrations_up(migration_db)
        
        # 2. Test Downgrade
        run_migrations_down(migration_db)
        
        # 3. Optional: Test Upgrade again to ensure idempotency/stability
        run_migrations_up(migration_db)
        
    except Exception as e:
        pytest.fail(f"Migration test failed: {e}")
