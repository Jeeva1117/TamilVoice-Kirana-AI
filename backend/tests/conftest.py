"""Pytest Configuration and Test Fixtures with Isolated SQLite Database."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models.product import Product
from backend.app.models.customer import Customer
from backend.app.models.sale import Sale
from backend.app.models.sale_item import SaleItem
from backend.app.models.stock_movement import StockMovement

# Isolated in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def clean_db():
    """Create all tables before each test and drop them after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db():
    """Database session for test setup and verification."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        db_session = TestingSessionLocal()
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_product(db):
    """Seed a sample product for testing."""
    product = Product(
        name="Ponni Boiled Rice",
        name_ta="பொன்னி அரிசி",
        sku="TEST-RIC-001",
        category="Rice & Grains",
        quantity=50.0,
        unit="kg",
        purchase_price=50.0,
        selling_price=60.0,
        minimum_stock_level=10.0,
        description="Test Ponni Rice",
        is_active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@pytest.fixture
def sample_customer(db):
    """Seed a sample customer for testing."""
    customer = Customer(
        name="Karthik Rajan",
        phone="9876543210",
        address="Madurai, Tamil Nadu",
        credit_balance=0.0,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer
