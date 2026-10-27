import os
os.environ["DATABASE_URL"] = "sqlite:///./test_documents.db"
os.environ["JWT_SECRET_KEY"] = "test_secret_key_that_is_long_enough_for_tests"
from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.db.session import Base, engine
from app.models import User, Document, DocumentShare, AuditLog

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
