import pytest
from app.core.config import settings
from tests.utils.migrations import run_migrations_up, run_migrations_down
import os

# We use a separate synchronous test database for migration testing
# to avoid conflicts with the main async application database logic.
# SQLite is fine for schema validation in this context.
TEST_DB_URL = "sqlite:///./test_migrations.db"

@pytest.fixture(scope="module")
def migration_db():
    """
    Fixture to manage the lifecycle of the test database.
    It creates a fresh DB for tests and cleans it up afterwards.
    """
    # Setup: ensure we start fresh
    if os.path.exists("./test_migrations.db"):
        os.remove("./test_migrations.db")
    
    yield TEST_DB_URL
    
    # Teardown: cleanup
    if os.path.exists("./test_migrations.db"):
        os.remove("./test_migrations.db")

def test_migrations_up_and_down(migration_db):
    """
    Verifies that the Alembic migrations can:
    1. Upgrade to the latest revision (head).
    2. Downgrade back to the beginning (base).
    This ensures the migration scripts are valid and reversible.
    """
    try:
        # 1. Test Upgrade
        run_migrations_up(migration_db)
        
        # 2. Test Downgrade
        run_migrations_down(migration_db)
        
        # 3. Optional: Test Upgrade again to ensure idempotency/stability
        run_migrations_up(migration_db)
        
    except Exception as e:
        pytest.fail(f"Migration test failed: {e}")
