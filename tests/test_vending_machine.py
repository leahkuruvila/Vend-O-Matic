"""Unit tests for the VendingMachine class."""

import unittest
import sys
import os

# Add the project root to the path so we can import vending_machine
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vending_machine import VendingMachine


class TestCoinOperations(unittest.TestCase):
    """Tests for inserting and returning coins."""

    def setUp(self):
        self.machine = VendingMachine()

    def test_insert_one_coin(self):
        """Inserting a valid quarter should return a total of 1."""
        result = self.machine.insert_coin(1)
        self.assertEqual(result, 1)

    def test_insert_multiple_coins(self):
        """Coins accumulate — inserting 3 quarters should give a running total."""
        self.machine.insert_coin(1)
        self.machine.insert_coin(1)
        result = self.machine.insert_coin(1)
        self.assertEqual(result, 3)

    def test_reject_invalid_coin(self):
        """Machine only accepts quarters (coin=1). Anything else returns None."""
        self.assertIsNone(self.machine.insert_coin(2))
        self.assertIsNone(self.machine.insert_coin(0))
        self.assertIsNone(self.machine.insert_coin(-1))
        self.assertIsNone(self.machine.insert_coin(True))
        self.assertIsNone(self.machine.insert_coin(1.0))
        self.assertIsNone(self.machine.insert_coin("nickel"))
        # Invalid coins should not create a balance that can be returned later.
        self.assertEqual(self.machine.return_coins(), 0)

    def test_return_coins(self):
        """Returning coins gives back everything inserted and resets to 0."""
        self.machine.insert_coin(1)
        self.machine.insert_coin(1)
        returned = self.machine.return_coins()
        self.assertEqual(returned, 2)
        # After return, the next inserted quarter should start a new balance.
        self.assertEqual(self.machine.insert_coin(1), 1)

    def test_return_coins_when_empty(self):
        """Returning with no coins inserted should return 0 (not an error)."""
        returned = self.machine.return_coins()
        self.assertEqual(returned, 0)


class TestInventoryQueries(unittest.TestCase):
    """Tests for checking inventory levels."""

    def setUp(self):
        self.machine = VendingMachine()

    def test_initial_inventory(self):
        """Machine starts fully stocked: 5 of each of the 3 beverages."""
        self.assertEqual(self.machine.get_inventory(), [5, 5, 5])

    def test_get_item_quantity(self):
        """Can query individual items by 1-based id."""
        self.assertEqual(self.machine.get_item_quantity(1), 5)
        self.assertEqual(self.machine.get_item_quantity(2), 5)
        self.assertEqual(self.machine.get_item_quantity(3), 5)

    def test_invalid_item_id(self):
        """Out-of-range ids return None (so the HTTP layer can 404)."""
        self.assertIsNone(self.machine.get_item_quantity(0))
        self.assertIsNone(self.machine.get_item_quantity(4))
        self.assertIsNone(self.machine.get_item_quantity(-1))


class TestPurchase(unittest.TestCase):
    """Tests for the purchase flow — the core of the vending machine."""

    def setUp(self):
        self.machine = VendingMachine()

    def test_successful_purchase(self):
        """Insert exact price (2 quarters), buy item 1 → success, 0 change."""
        self.machine.insert_coin(1)
        self.machine.insert_coin(1)
        result = self.machine.purchase(1)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["quantity"], 1)     # 1 beverage dispensed
        self.assertEqual(result["change"], 0)       # exact change, nothing back
        self.assertEqual(result["remaining"], 4)    # was 5, now 4

    def test_purchase_with_change(self):
        """Insert 3 quarters, buy at price of 2 → 1 quarter change."""
        self.machine.insert_coin(1)
        self.machine.insert_coin(1)
        self.machine.insert_coin(1)
        result = self.machine.purchase(2)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["change"], 1)
        # A successful purchase completes the transaction and clears the balance.
        self.assertEqual(self.machine.return_coins(), 0)

    def test_insufficient_coins(self):
        """Trying to buy with less than 2 quarters → insufficient."""
        self.machine.insert_coin(1)
        result = self.machine.purchase(1)

        self.assertEqual(result["status"], "insufficient")
        self.assertEqual(result["coins"], 1)
        # Coins should still be in the machine (not lost).
        self.assertEqual(self.machine.insert_coin(1), 2)

    def test_insufficient_coins_zero(self):
        """Trying to buy with 0 coins → insufficient with 0."""
        result = self.machine.purchase(1)
        self.assertEqual(result["status"], "insufficient")
        self.assertEqual(result["coins"], 0)

    def test_out_of_stock(self):
        """Buying all 5 of an item, then trying again → out_of_stock."""
        # Buy all 5 of item 1
        for _ in range(5):
            self.machine.insert_coin(1)
            self.machine.insert_coin(1)
            result = self.machine.purchase(1)
            self.assertEqual(result["status"], "success")

        # Item 1 should now be empty
        self.assertEqual(self.machine.get_item_quantity(1), 0)

        # Try to buy one more — should be out of stock
        self.machine.insert_coin(1)
        self.machine.insert_coin(1)
        result = self.machine.purchase(1)
        self.assertEqual(result["status"], "out_of_stock")
        self.assertEqual(result["coins"], 2)
        # Coins are still in the machine — customer can pick another item.
        self.assertEqual(self.machine.purchase(2)["status"], "success")

    def test_out_of_stock_takes_priority_over_insufficient_coins(self):
        """A sold-out item should still report out_of_stock with 0 or 1 coins inserted."""
        for _ in range(5):
            self.machine.insert_coin(1)
            self.machine.insert_coin(1)
            self.machine.purchase(1)

        result = self.machine.purchase(1)
        self.assertEqual(result["status"], "out_of_stock")
        self.assertEqual(result["coins"], 0)

        self.machine.insert_coin(1)
        result = self.machine.purchase(1)
        self.assertEqual(result["status"], "out_of_stock")
        self.assertEqual(result["coins"], 1)

    def test_invalid_item_id(self):
        """Purchasing an invalid item id returns 'invalid' status."""
        self.machine.insert_coin(1)
        self.machine.insert_coin(1)
        self.assertEqual(self.machine.purchase(0)["status"], "invalid")
        self.assertEqual(self.machine.purchase(4)["status"], "invalid")

    def test_purchase_does_not_affect_other_items(self):
        """Buying item 1 should not change the stock of items 2 and 3."""
        self.machine.insert_coin(1)
        self.machine.insert_coin(1)
        self.machine.purchase(1)

        self.assertEqual(self.machine.get_item_quantity(1), 4)
        self.assertEqual(self.machine.get_item_quantity(2), 5)  # untouched
        self.assertEqual(self.machine.get_item_quantity(3), 5)  # untouched

    def test_coins_reset_after_purchase(self):
        """After a successful purchase, the coin counter resets to 0."""
        self.machine.insert_coin(1)
        self.machine.insert_coin(1)
        self.machine.insert_coin(1)
        self.machine.purchase(1)
        self.assertEqual(self.machine.return_coins(), 0)


if __name__ == "__main__":
    unittest.main()
