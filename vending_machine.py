"""
VendingMachine — core business logic, separated from the HTTP layer.
"""


class VendingMachine:
    """
    Models a beverage vending machine with three product slots.

    Constraints (from spec):
      - Only accepts US quarters (coin value = 1 per insertion).
      - Purchase price is 2 quarters.
      - 3 beverages, 5 of each at start.
      - Max 1 beverage dispensed per transaction.
      - Unused quarters returned after a successful purchase.
    """

    PRICE = 2          # Cost in quarters to buy one beverage
    NUM_ITEMS = 3      # Number of distinct beverages
    INITIAL_STOCK = 5  # Starting quantity for each beverage

    def __init__(self):
        self._coins = 0
        self._inventory = [self.INITIAL_STOCK] * self.NUM_ITEMS

    # ── Coin operations ──────────────────────────────────────────

    def insert_coin(self, coin):
        """Accept a single quarter. Returns the new coin total, or None if invalid."""
        # type() instead of isinstance() so True and 1.0 are rejected.
        if type(coin) is not int or coin != 1:
            return None

        self._coins += 1
        return self._coins

    def return_coins(self):
        """Return all inserted coins and reset the counter to 0."""
        returned = self._coins
        self._coins = 0
        return returned

    # ── Inventory queries ────────────────────────────────────────

    def get_inventory(self):
        """Return a copy of the full inventory list."""
        return list(self._inventory)

    def get_item_quantity(self, item_id):
        """Return remaining stock for a single item (1-indexed), or None if invalid."""
        if not self._valid_id(item_id):
            return None
        return self._inventory[item_id - 1]

    # ── Purchase ─────────────────────────────────────────────────

    def purchase(self, item_id):
        """
        Attempt to purchase one beverage.

        Returns a dict with a 'status' key: 'success', 'insufficient',
        'out_of_stock', or 'invalid'.

        Out-of-stock is checked before insufficient coins so that a sold-out
        item always reports 404 regardless of how many coins are inserted.
        """
        if not self._valid_id(item_id):
            return {"status": "invalid"}

        if self._inventory[item_id - 1] == 0:
            return {"status": "out_of_stock", "coins": self._coins}

        if self._coins < self.PRICE:
            return {"status": "insufficient", "coins": self._coins}

        self._inventory[item_id - 1] -= 1
        change = self._coins - self.PRICE
        self._coins = 0

        return {
            "status": "success",
            "change": change,
            "remaining": self._inventory[item_id - 1],
            "quantity": 1,
        }

    # ── Helpers ──────────────────────────────────────────────────

    def _valid_id(self, item_id):
        """Check that an item id falls within the valid range (1..NUM_ITEMS)."""
        return isinstance(item_id, int) and 1 <= item_id <= self.NUM_ITEMS
