# Vend-O-Matic

A RESTful HTTP service for a beverage vending machine, built with Python and Flask.

## Clone the Repository

```bash
git clone https://github.com/leahkuruvila/Vend-O-Matic.git
cd Vend-O-Matic
```

## Prerequisites

- **Python 3.9+**
- **pip**

## macOS Setup

**First terminal** — from the repository root:

1. Create a virtual environment:

```bash
python3 -m venv venv
```

2. Activate the virtual environment:

```bash
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

**Second terminal** — open a second terminal window, navigate to the project folder, and activate the virtual environment:

```bash
cd Vend-O-Matic
source venv/bin/activate
```

## Running the Server

Run this in the first terminal:

```bash
python3 app.py
```

The server starts at **http://localhost:8000**.

To use a different port:

```bash
PORT=3000 python3 app.py
```

To enable debug mode (off by default):

```bash
FLASK_DEBUG=1 python3 app.py
```

## Running Tests

Run this in the second terminal:

```bash
python3 -m unittest discover tests -v
```

This runs both the unit tests (vending machine logic) and integration tests (HTTP endpoints).

The curl examples below should also be run in the second terminal while the server is running.

## API Reference

All endpoints accept and return `application/json`.

## Spec Interpretation Notes

The project spec leaves a few invalid-request cases undefined. In those spots,
this implementation adds explicit response codes and keeps the response body
minimal (`{}`) rather than inventing new payload shapes.

- `PUT /` with a missing or invalid `coin` field returns `400 Bad Request`.
- `GET /inventory/:id` with an invalid item id returns `404 Not Found`.
- `PUT /inventory/:id` with an invalid item id returns `404 Not Found`.
- unknown routes (e.g., `GET /foo`) return `404 Not Found` with an empty JSON body.
- unsupported HTTP methods on valid routes (e.g., `POST /inventory`) return `405 Method Not Allowed` with an empty JSON body.

When one of these unspecified error cases happens, any coins already inserted
remain in the machine until a successful purchase or `DELETE /`.

### Insert a Coin

```
PUT /
Body: {"coin": 1}
```

Inserts one US quarter. Returns `204` with an `X-Coins` header showing the total coins accepted.

Implementation note: the spec only defines the valid body `{"coin": 1}`. This
service additionally returns `400 Bad Request` for missing or invalid coin
payloads.

```bash
curl -i -X PUT http://localhost:8000/ -H "Content-Type: application/json" -d '{"coin": 1}'
```

### Return Coins

```
DELETE /
```

Returns all inserted coins. Returns `204` with an `X-Coins` header showing the number of coins returned.

```bash
curl -i -X DELETE http://localhost:8000/
```

### View Inventory

```
GET /inventory
```

Returns `200` with a JSON array of remaining quantities (e.g., `[5, 5, 5]`).

```bash
curl -i http://localhost:8000/inventory
```

### View Single Item

```
GET /inventory/:id
```

Returns `200` with the remaining quantity for that item (e.g., `5`). Item IDs are `1`, `2`, or `3`.

Implementation note: the spec does not define behavior for invalid ids. This
service returns `404 Not Found` when the requested slot does not exist.

```bash
curl -i http://localhost:8000/inventory/1
```

### Purchase a Beverage

```
PUT /inventory/:id
```

Attempts to purchase one beverage from the specified slot.

| Scenario              | Status | X-Coins                | X-Inventory-Remaining | Body               |
|-----------------------|--------|------------------------|-----------------------|--------------------|
| Success               | 200    | Coins returned (change)| Remaining stock       | `{"quantity": 1}`  |
| Insufficient coins    | 403    | Current coin count     | —                     | —                  |
| Out of stock          | 404    | Current coin count     | —                     | —                  |

Implementation note: the spec defines `403` for insufficient coins and `404`
for out-of-stock items. This service also returns `404 Not Found` when the item
id itself is invalid.

```bash
# Insert 2 coins, then purchase item 1
curl -i -X PUT http://localhost:8000/ -H "Content-Type: application/json" -d '{"coin": 1}'
curl -i -X PUT http://localhost:8000/ -H "Content-Type: application/json" -d '{"coin": 1}'
curl -i -X PUT http://localhost:8000/inventory/1
```

## Design Decisions

- **Python + Flask**: Lightweight, minimal dependencies, widely supported on macOS.
- **Separation of concerns**: `vending_machine.py` holds all business logic; `app.py` handles HTTP routing. This makes the core logic testable without HTTP.
- **In-memory state**: Appropriate for a single vending machine demo. State resets when the server restarts.

## Project Structure

```
Vend-O-Matic/
├── app.py                  # Flask HTTP server and route handlers
├── vending_machine.py      # Core vending machine business logic
├── requirements.txt        # Python dependencies (Flask only)
├── README.md
└── tests/
    ├── test_vending_machine.py  # Unit tests for business logic
    └── test_app.py              # Integration tests for HTTP endpoints
```
