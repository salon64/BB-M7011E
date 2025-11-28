# tests/test_main.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from app.main import app

client = TestClient(app)

# Mock Supabase responses
@pytest.fixture
def mock_supabase():
    with patch('app.main.supabase') as mock:
        yield mock

class TestHealthEndpoints:
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert "timestamp" in response.json()
    
    def test_readiness_check_success(self, mock_supabase):
        """Test readiness check when database is available"""
        mock_supabase.table.return_value.select.return_value.limit.return_value.execute.return_value = Mock(data=[{"id": "123"}])
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"
    
    def test_readiness_check_failure(self, mock_supabase):
        """Test readiness check when database is unavailable"""
        mock_supabase.table.return_value.select.return_value.limit.return_value.execute.side_effect = Exception("DB Error")
        response = client.get("/ready")
        assert response.status_code == 503
    
    def test_metrics_endpoint(self):
        """Test Prometheus metrics endpoint"""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "http_requests_total" in response.text

class TestCreateItem:
    def test_create_item_success(self, mock_supabase):
        """Test successful item creation"""
        mock_response = Mock()
        mock_response.data = [{
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "Test Product",
            "price": 1000,
            "barcode_id": 12345,
            "active": True
        }]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response
        
        response = client.post("/items", json={
            "name": "Test Product",
            "price": 1000,
            "barcode_id": 12345
        })
        
        assert response.status_code == 201
        assert response.json()["name"] == "Test Product"
        assert response.json()["price"] == 1000
        assert response.json()["active"] is True
    
    def test_create_item_missing_name(self):
        """Test item creation with missing name"""
        response = client.post("/items", json={
            "price": 1000
        })
        assert response.status_code == 422
    
    def test_create_item_empty_name(self):
        """Test item creation with empty name"""
        response = client.post("/items", json={
            "name": "   ",
            "price": 1000
        })
        assert response.status_code == 422
    
    def test_create_item_negative_price(self):
        """Test item creation with negative price"""
        response = client.post("/items", json={
            "name": "Test Product",
            "price": -100
        })
        assert response.status_code == 422
    
    def test_create_item_without_barcode(self, mock_supabase):
        """Test item creation without barcode_id"""
        mock_response = Mock()
        mock_response.data = [{
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "Test Product",
            "price": 1000,
            "barcode_id": None,
            "active": True
        }]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response
        
        response = client.post("/items", json={
            "name": "Test Product",
            "price": 1000
        })
        
        assert response.status_code == 201
        assert response.json()["barcode_id"] is None

class TestGetItems:
    def test_get_all_items(self, mock_supabase):
        """Test getting all items"""
        mock_response = Mock()
        mock_response.data = [
            {"id": "1", "name": "Item 1", "price": 100, "barcode_id": None, "active": True},
            {"id": "2", "name": "Item 2", "price": 200, "barcode_id": 123, "active": False}
        ]
        mock_supabase.table.return_value.select.return_value.order.return_value.execute.return_value = mock_response
        
        response = client.get("/items")
        
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert response.json()[0]["name"] == "Item 1"
    
    def test_get_items_filtered_active(self, mock_supabase):
        """Test getting items filtered by active status"""
        mock_response = Mock()
        mock_response.data = [
            {"id": "1", "name": "Item 1", "price": 100, "barcode_id": None, "active": True}
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
        
        response = client.get("/items?active=true")
        
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["active"] is True
    
    def test_get_items_empty(self, mock_supabase):
        """Test getting items when none exist"""
        mock_response = Mock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.order.return_value.execute.return_value = mock_response
        
        response = client.get("/items")
        
        assert response.status_code == 200
        assert response.json() == []

class TestGetItemById:
    def test_get_item_success(self, mock_supabase):
        """Test getting item by ID"""
        mock_response = Mock()
        mock_response.data = [{
            "id": "123",
            "name": "Test Item",
            "price": 500,
            "barcode_id": None,
            "active": True
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        response = client.get("/items/123")
        
        assert response.status_code == 200
        assert response.json()["id"] == "123"
        assert response.json()["name"] == "Test Item"
    
    def test_get_item_not_found(self, mock_supabase):
        """Test getting non-existent item"""
        mock_response = Mock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        response = client.get("/items/nonexistent")
        
        assert response.status_code == 404

class TestUpdateItem:
    def test_update_item_success(self, mock_supabase):
        """Test successful item update"""
        # Mock check for existence
        check_response = Mock()
        check_response.data = [{"id": "123"}]
        
        # Mock update response
        update_response = Mock()
        update_response.data = [{
            "id": "123",
            "name": "Updated Item",
            "price": 1500,
            "barcode_id": 999,
            "active": True
        }]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = check_response
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = update_response
        
        response = client.put("/items/123", json={
            "name": "Updated Item",
            "price": 1500,
            "barcode_id": 999
        })
        
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Item"
        assert response.json()["price"] == 1500
    
    def test_update_item_partial(self, mock_supabase):
        """Test partial item update"""
        check_response = Mock()
        check_response.data = [{"id": "123"}]
        
        update_response = Mock()
        update_response.data = [{
            "id": "123",
            "name": "Original Name",
            "price": 2000,
            "barcode_id": None,
            "active": True
        }]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = check_response
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = update_response
        
        response = client.put("/items/123", json={"price": 2000})
        
        assert response.status_code == 200
        assert response.json()["price"] == 2000
    
    def test_update_item_not_found(self, mock_supabase):
        """Test updating non-existent item"""
        mock_response = Mock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        response = client.put("/items/nonexistent", json={"name": "Test"})
        
        assert response.status_code == 404
    
    def test_update_item_no_fields(self, mock_supabase):
        """Test update with no fields provided"""
        check_response = Mock()
        check_response.data = [{"id": "123"}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = check_response
        
        response = client.put("/items/123", json={})
        
        assert response.status_code == 400

class TestDeleteItem:
    def test_soft_delete_item(self, mock_supabase):
        """Test soft delete of item"""
        check_response = Mock()
        check_response.data = [{"id": "123"}]
        
        delete_response = Mock()
        delete_response.data = [{"id": "123", "active": False}]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = check_response
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = delete_response
        
        response = client.delete("/items/123")
        
        assert response.status_code == 204
    
    def test_hard_delete_item(self, mock_supabase):
        """Test hard delete of item"""
        check_response = Mock()
        check_response.data = [{"id": "123"}]
        
        delete_response = Mock()
        delete_response.data = []
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = check_response
        mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = delete_response
        
        response = client.delete("/items/123?hard_delete=true")
        
        assert response.status_code == 204
    
    def test_delete_item_not_found(self, mock_supabase):
        """Test deleting non-existent item"""
        mock_response = Mock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        response = client.delete("/items/nonexistent")
        
        assert response.status_code == 404