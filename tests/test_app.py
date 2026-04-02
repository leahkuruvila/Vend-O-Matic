"""Integration tests for the Flask HTTP endpoints."""

import unittest
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as flask_app
from vending_machine import VendingMachine


class TestBase(unittest.TestCase):
    """Base class that resets the vending machine before each test."""

    def setUp(self):
        flask_app.machine = VendingMachine()
        self.app = flask_app.app.test_client()
        flask_app.app.config["JSON_SORT_KEYS"] = False


class TestInsertCoin(TestBase):
    """PUT / — inserting coins into the machine."""

    def test_insert_one_coin(self):
        """Insert a single quarter → 204, X-Coins: 1."""
        res = self.app.put("/", json={"coin": 1})
        self.assertEqual(res.status_code, 204)
        self.assertEqual(res.headers["X-Coins"], "1")
        self.assertEqual(res.headers["Content-Type"], "application/json")

    def test_insert_multiple_coins(self):
        """Insert 3 quarters sequentially → X-Coins should increment each time."""
        self.app.put("/", json={"coin": 1})
        self.app.put("/", json={"coin": 1})
        res = self.app.put("/", json={"coin": 1})
        self.assertEqual(res.headers["X-Coins"], "3")

    def test_reject_invalid_coin(self):
        """Non-quarter values should be rejected with 400."""
        res = self.app.put("/", json={"coin": 2})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.headers["Content-Type"], "application/json")

    def test_reject_boolean_coin(self):
        """Boolean JSON values should not be treated as integer quarters."""
        res = self.app.put("/", json={"coin": True})
        self.assertEqual(res.status_code, 400)

    def test_reject_float_coin(self):
        """Float JSON values should not be treated as integer quarters."""
        res = self.app.put("/", json={"coin": 1.0})
        self.assertEqual(res.status_code, 400)

    def test_reject_missing_coin(self):
        """Missing 'coin' field in body → 400."""
        res = self.app.put("/", json={})
        self.assertEqual(res.status_code, 400)

    def test_invalid_coin_does_not_clear_existing_balance(self):
        """Invalid coin input returns 400, but already-inserted coins stay."""
        self.app.put("/", json={"coin": 1})
        res = self.app.put("/", json={"coin": 2})
        self.assertEqual(res.status_code, 400)

        res = self.app.delete("/")
        self.assertEqual(res.headers["X-Coins"], "1")


class TestReturnCoins(TestBase):
    """DELETE / — pressing the coin-return lever."""

    def test_return_inserted_coins(self):
        """Insert 2, return → should get 2 back and 204."""
        self.app.put("/", json={"coin": 1})
        self.app.put("/", json={"coin": 1})
        res = self.app.delete("/")
        self.assertEqual(res.status_code, 204)
        self.assertEqual(res.headers["X-Coins"], "2")

    def test_return_zero_coins(self):
        """Return with nothing inserted → 204, X-Coins: 0."""
        res = self.app.delete("/")
        self.assertEqual(res.status_code, 204)
        self.assertEqual(res.headers["X-Coins"], "0")

    def test_return_resets_balance(self):
        """After returning, the coin balance should be 0."""
        self.app.put("/", json={"coin": 1})
        self.app.delete("/")
        # Insert again — should start from 1, not 2
        res = self.app.put("/", json={"coin": 1})
        self.assertEqual(res.headers["X-Coins"], "1")


class TestGetInventory(TestBase):
    """GET /inventory — checking what's in stock."""

    def test_full_inventory(self):
        """Fresh machine should have [5, 5, 5]."""
        res = self.app.get("/inventory")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(json.loads(res.data), [5, 5, 5])

    def test_inventory_after_purchase(self):
        """After buying item 1, inventory should reflect the decrease."""
        self.app.put("/", json={"coin": 1})
        self.app.put("/", json={"coin": 1})
        self.app.put("/inventory/1")
        res = self.app.get("/inventory")
        self.assertEqual(json.loads(res.data), [4, 5, 5])


class TestGetItem(TestBase):
    """GET /inventory/<id> — checking a single item's stock."""

    def test_get_valid_item(self):
        """Each item starts at quantity 5."""
        for item_id in [1, 2, 3]:
            res = self.app.get(f"/inventory/{item_id}")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(json.loads(res.data), 5)

    def test_get_invalid_item(self):
        """Requesting an item that doesn't exist → 404."""
        res = self.app.get("/inventory/0")
        self.assertEqual(res.status_code, 404)
        res = self.app.get("/inventory/4")
        self.assertEqual(res.status_code, 404)


class TestPurchase(TestBase):
    """PUT /inventory/<id> — buying a beverage (the main event)."""

    def test_successful_purchase(self):
        """Insert 2 coins, buy item 1 → 200, quantity=1, 0 change, 4 remaining."""
        self.app.put("/", json={"coin": 1})
        self.app.put("/", json={"coin": 1})
        res = self.app.put("/inventory/1")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["X-Coins"], "0")               # no change
        self.assertEqual(res.headers["X-Inventory-Remaining"], "4")  # 5 → 4
        self.assertEqual(json.loads(res.data), {"quantity": 1})

    def test_purchase_with_change(self):
        """Insert 3 coins, buy → should get 1 coin back as change."""
        self.app.put("/", json={"coin": 1})
        self.app.put("/", json={"coin": 1})
        self.app.put("/", json={"coin": 1})
        res = self.app.put("/inventory/1")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["X-Coins"], "1")  # 3 - 2 = 1 change

    def test_insufficient_coins_zero(self):
        """Buy with 0 coins → 403, X-Coins: 0."""
        res = self.app.put("/inventory/1")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.headers["X-Coins"], "0")

    def test_insufficient_coins_one(self):
        """Buy with 1 coin → 403, X-Coins: 1. Coins stay in machine."""
        self.app.put("/", json={"coin": 1})
        res = self.app.put("/inventory/1")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.headers["X-Coins"], "1")

    def test_out_of_stock(self):
        """Buy all 5 of item 1, then try again → 404."""
        for _ in range(5):
            self.app.put("/", json={"coin": 1})
            self.app.put("/", json={"coin": 1})
            res = self.app.put("/inventory/1")
            self.assertEqual(res.status_code, 200)

        # Item 1 is now sold out — try to buy with enough coins
        self.app.put("/", json={"coin": 1})
        self.app.put("/", json={"coin": 1})
        res = self.app.put("/inventory/1")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.headers["X-Coins"], "2")  # coins still accepted

    def test_out_of_stock_takes_priority_over_insufficient_coins(self):
        """A sold-out item should return 404 even if fewer than 2 coins are inserted."""
        for _ in range(5):
            self.app.put("/", json={"coin": 1})
            self.app.put("/", json={"coin": 1})
            self.app.put("/inventory/1")

        res = self.app.put("/inventory/1")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.headers["X-Coins"], "0")

        self.app.put("/", json={"coin": 1})
        res = self.app.put("/inventory/1")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.headers["X-Coins"], "1")

    def test_out_of_stock_coins_retained(self):
        """When item is out of stock, coins stay in machine for another purchase."""
        # Empty item 1
        for _ in range(5):
            self.app.put("/", json={"coin": 1})
            self.app.put("/", json={"coin": 1})
            self.app.put("/inventory/1")

        # Try item 1 (sold out) — coins stay
        self.app.put("/", json={"coin": 1})
        self.app.put("/", json={"coin": 1})
        res = self.app.put("/inventory/1")
        self.assertEqual(res.status_code, 404)

        # Use those same coins to buy item 2 instead
        res = self.app.put("/inventory/2")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(json.loads(res.data), {"quantity": 1})

    def test_invalid_item_id(self):
        """Purchasing a nonexistent item → 404."""
        self.app.put("/", json={"coin": 1})
        self.app.put("/", json={"coin": 1})
        res = self.app.put("/inventory/99")
        self.assertEqual(res.status_code, 404)

    def test_invalid_item_id_keeps_inserted_coins(self):
        """
        Invalid item ids return 404, but coins remain available for another
        purchase or DELETE /.
        """
        self.app.put("/", json={"coin": 1})
        self.app.put("/", json={"coin": 1})

        res = self.app.put("/inventory/99")
        self.assertEqual(res.status_code, 404)

        res = self.app.delete("/")
        self.assertEqual(res.headers["X-Coins"], "2")


class TestFullWorkflow(TestBase):
    """End-to-end scenarios that combine multiple operations."""

    def test_insert_purchase_return_cycle(self):
        """
        Full customer flow:
        1. Insert 3 coins
        2. Buy item 2 (costs 2) → get 1 coin change
        3. Verify inventory updated
        4. Verify coin balance reset
        """
        # Step 1: Insert coins
        self.app.put("/", json={"coin": 1})
        self.app.put("/", json={"coin": 1})
        self.app.put("/", json={"coin": 1})

        # Step 2: Purchase
        res = self.app.put("/inventory/2")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["X-Coins"], "1")               # 1 coin change
        self.assertEqual(res.headers["X-Inventory-Remaining"], "4")

        # Step 3: Verify inventory
        res = self.app.get("/inventory")
        self.assertEqual(json.loads(res.data), [5, 4, 5])

        # Step 4: Coins should be reset — delete returns 0
        res = self.app.delete("/")
        self.assertEqual(res.headers["X-Coins"], "0")

    def test_cancel_and_retry(self):
        """
        Customer inserts coins, changes their mind, gets coins back,
        then starts over and completes a purchase.
        """
        # Insert 1 coin, then cancel
        self.app.put("/", json={"coin": 1})
        res = self.app.delete("/")
        self.assertEqual(res.headers["X-Coins"], "1")

        # Start over — insert 2 coins and buy
        self.app.put("/", json={"coin": 1})
        self.app.put("/", json={"coin": 1})
        res = self.app.put("/inventory/3")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(json.loads(res.data), {"quantity": 1})


class TestFrameworkErrors(TestBase):
    """Framework-level errors should still return JSON for API consistency."""

    def test_not_found_returns_json(self):
        """
        Unknown paths should hit Flask's global 404 handler rather than one of
        the app's explicit route-level 404 responses, and still preserve the
        API's JSON response format.
        """
        res = self.app.get("/does-not-exist")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.headers["Content-Type"], "application/json")
        self.assertEqual(json.loads(res.data), {})

    def test_method_not_allowed_returns_json(self):
        """
        Known paths with an unsupported HTTP verb should hit Flask's global 405
        handler and still preserve the API's JSON response format.
        """
        res = self.app.post("/inventory")
        self.assertEqual(res.status_code, 405)
        self.assertEqual(res.headers["Content-Type"], "application/json")
        self.assertEqual(json.loads(res.data), {})


if __name__ == "__main__":
    unittest.main()
