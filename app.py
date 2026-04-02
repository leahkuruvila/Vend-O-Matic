"""
Vend-O-Matic — HTTP service for a beverage vending machine.

Maps HTTP endpoints to VendingMachine business logic. See README for API details.
"""

from flask import Flask, request, jsonify, make_response
from vending_machine import VendingMachine

app = Flask(__name__)

machine = VendingMachine()


# Override Flask's default HTML error pages with JSON responses.

@app.errorhandler(404)
def not_found(_error):
    return jsonify({}), 404


@app.errorhandler(405)
def method_not_allowed(_error):
    return jsonify({}), 405


@app.route("/", methods=["PUT"])
def insert_coin():
    data = request.get_json(silent=True) or {}
    coin = data.get("coin")

    total = machine.insert_coin(coin)
    if total is None:
        return jsonify({}), 400

    response = make_response("", 204)
    response.headers["X-Coins"] = total
    response.headers["Content-Type"] = "application/json"
    return response


@app.route("/", methods=["DELETE"])
def return_coins():
    returned = machine.return_coins()
    response = make_response("", 204)
    response.headers["X-Coins"] = returned
    response.headers["Content-Type"] = "application/json"
    return response


@app.route("/inventory", methods=["GET"])
def get_inventory():
    return jsonify(machine.get_inventory())


@app.route("/inventory/<int:item_id>", methods=["GET"])
def get_item(item_id):
    quantity = machine.get_item_quantity(item_id)
    if quantity is None:
        return jsonify({}), 404
    return jsonify(quantity)


@app.route("/inventory/<int:item_id>", methods=["PUT"])
def purchase_item(item_id):
    result = machine.purchase(item_id)

    if result["status"] == "invalid":
        return jsonify({}), 404

    if result["status"] == "insufficient":
        response = make_response(jsonify({}), 403)
        response.headers["X-Coins"] = result["coins"]
        return response

    if result["status"] == "out_of_stock":
        response = make_response(jsonify({}), 404)
        response.headers["X-Coins"] = result["coins"]
        return response

    response = make_response(jsonify({"quantity": result["quantity"]}), 200)
    response.headers["X-Coins"] = result["change"]
    response.headers["X-Inventory-Remaining"] = result["remaining"]
    return response


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host="0.0.0.0", port=port, debug=debug)
