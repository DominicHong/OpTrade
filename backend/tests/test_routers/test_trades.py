"""Integration tests for Trade API routes using FastAPI TestClient."""

from datetime import date

from app.models import Trade


class TestTradeRoutes:
    def test_list_trades_empty(self, client):
        """GET /api/v1/trades returns empty list with pagination."""
        response = client.get("/api/v1/trades")
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["total"] == 0
        assert data["page"] == 1

    def test_list_trades_with_data(self, client, session, sample_trade_data):
        """GET /api/v1/trades returns trades when data exists."""
        trade = Trade(
            trade_id="TEST-001",
            ccy_pair="USD/CNY",
            trade_type="CALL",
            direction="买入",
            strike=7.12,
            notional1=10000000.0,
            expiry_date=date(2026, 6, 16),
        )
        session.add(trade)
        session.commit()

        response = client.get("/api/v1/trades")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["total"] == 1
        assert data["data"][0]["trade_id"] == "TEST-001"

    def test_get_trade_not_found(self, client):
        """GET /api/v1/trades/{id} returns 404 for missing trade."""
        response = client.get("/api/v1/trades/99999")
        assert response.status_code == 404

    def test_get_trade_found(self, client, session, sample_trade_data):
        """GET /api/v1/trades/{id} returns trade when it exists."""
        trade = Trade(**sample_trade_data)
        trade.trade_date = date(2026, 6, 8)
        trade.expiry_date = date(2026, 6, 16)
        trade.delivery_date = date(2026, 6, 16)
        session.add(trade)
        session.commit()
        session.refresh(trade)

        response = client.get(f"/api/v1/trades/{trade.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["trade_id"] == "TEST-001"
        assert data["ccy_pair"] == "USD/CNY"
        assert data["strike"] == 7.12

    def test_delete_trade(self, client, session):
        """DELETE /api/v1/trades/{id} removes the trade."""
        trade = Trade(trade_id="DEL-001")
        session.add(trade)
        session.commit()
        session.refresh(trade)

        response = client.delete(f"/api/v1/trades/{trade.id}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

        # Verify deleted
        response = client.get(f"/api/v1/trades/{trade.id}")
        assert response.status_code == 404

    def test_filter_by_ccy_pair(self, client, session):
        """Filter trades by ccy_pair."""
        t1 = Trade(trade_id="T1", ccy_pair="USD/CNY")
        t2 = Trade(trade_id="T2", ccy_pair="EUR/USD")
        session.add_all([t1, t2])
        session.commit()

        response = client.get("/api/v1/trades?ccy_pair=USD/CNY")
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["ccy_pair"] == "USD/CNY"

    def test_search(self, client, session):
        """Search should match trade_id, counterparty_name, etc."""
        t1 = Trade(trade_id="SEARCH-001", counterparty_name="TestBank")
        t2 = Trade(trade_id="OTHER-002", counterparty_name="OtherBank")
        session.add_all([t1, t2])
        session.commit()

        response = client.get("/api/v1/trades?search=SEARCH")
        data = response.json()
        assert len(data["data"]) >= 1

    def test_pagination(self, client, session):
        """Pagination should work correctly."""
        for i in range(5):
            session.add(Trade(trade_id=f"PAGE-{i:03d}"))
        session.commit()

        response = client.get("/api/v1/trades?page=1&page_size=2")
        data = response.json()
        assert len(data["data"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 2
