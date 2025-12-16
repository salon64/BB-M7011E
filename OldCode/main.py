from typing import List, Optional
from fastapi import FastAPI, HTTPException, Header
import sqlite3
from pathlib import Path
from gotrue import BaseModel
from datetime import datetime


DB_PATH = Path("./windows_database/mydb.sqlite3")

app = FastAPI(title="BBL API", version="1.0")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # enables dict-style rows
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def confirm_user_from_xpel_db(card_id: str) -> bool:
    """
    Confirm user existence from external XPEL database.
    Connect to the external XPEL database
        see if user exists and is active
        if user exists and is active return True
        if user exists and is not active return False and update our local db to set active = 0
        if user does not exist return False
    """

    # Connect to the external XPEL database
    # see if user exists and is active
    # if user exists and is active return True
    # if user exists and is not active return False and update our local db to set active = 0
    # if user does not exist return False
    query = "SELECT * FROM users WHERE carduid = ?"

    # if notfound:
    #     return False
    # if inactive:
    #     update_local_user(card_id, name, 0)
    #     return False
    # update_local_user(card_id, name, 1)
    # return True


def update_local_user(
    card_id: str, status: int, name: str, conn: sqlite3.Connection = None
) -> None:
    """
    Update user status in local database. Creates the user if they don't exist.
    Args:
        card_id: The card ID of the user
        status: The status to set (0 for inactive, 1 for active)
        name: The name of the user
        conn: Optional database connection. If not provided, a new connection will be created
    """
    should_close = conn is None
    if should_close:
        conn = get_db_connection()

    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO users (card_id, name, balance, active) VALUES (?, ?, ?, ?);",
            (card_id, name, 0, 0),
        )
        cur.execute(
            "UPDATE users SET active = ?, name = ? WHERE card_id = ?",
            (status, name, card_id),
        )
        conn.commit()
    finally:
        if should_close:
            conn.close()


# API endpoint for updating user status and name
@app.put("/user/{card_id}/data", status_code=204)
def update_local_user_endpoint(card_id: str, data: dict):
    """
    PUT /user/123/data
    Body: { "status": 1, "name": "alice" }
    """
    if data["status"] not in (0, 1):
        raise HTTPException(status_code=400, detail="Invalid status value")
    update_local_user(card_id, data["status"], data["name"])


class LineItem(BaseModel):
    item_id: str
    quantity: int = 1


class PurchaseRequest(BaseModel):
    card_id: str
    items: List[LineItem]
    mode: Optional[str] = "all_or_nothing"


# {
#   "card_id": "uuid-of-user",
#   "items": [
#     {"item_id": "uuid-of-item", "quantity": 2},
#     {"item_id": "uuid-of-item-2", "quantity": 1}
#   ],
#   "mode": "all_or_nothing"   // optional: "all_or_nothing" (recommended) or "partial"
# }


# idempotency_key is saved as: userid-path-idempotencykey
# they are saved with an expiration time of 24 hours
# when the data is saved to xp-el database it will also clear the idempotency keys that have expired
@app.post("/purchases", status_code=201)
def purchase_items(req: PurchaseRequest, idempotency_key: str = Header(None)):
    """
    Endpoint to handle item purchases.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    if idempotency_key:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS idempotency (
                key TEXT PRIMARY KEY,
                result_json TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
            );
        """
        )
        cur.execute(
            "SELECT result_json FROM idempotency WHERE key = ?", (idempotency_key,)
        )
        row = cur.fetchone()
        if row:
            return {"idempotent_replay": True, "result": row["result_json"]}

    conn.close()

    # TODO: idempotency might be useful here
    if not confirm_user_from_xpel_db(req.card_id):
        raise HTTPException(
            status_code=403, detail="User not found or inactive in xp-el database"
        )

    conn = get_db_connection()
    cur = conn.cursor()

    item_ids = [li.item_id for li in req.items]
    placeholders = ",".join("?" for _ in item_ids)
    cur.execute(
        f"SELECT id, price, active FROM items WHERE id IN ({placeholders})", item_ids
    )
    items_map = {r["id"]: r for r in cur.fetchall()}

    total = 0
    for li in req.items:
        if li.item_id not in items_map or items_map[li.item_id]["active"] == 0:
            if req.mode == "all_or_nothing":
                conn.close()
                raise HTTPException(
                    status_code=400, detail=f"Item {li.item_id} not found or inactive"
                )
            else:
                continue
        total += items_map[li.item_id]["price"] * li.quantity

    try:
        cur.execute("BEGIN")
        # Atomic deduction
        cur.execute(
            "UPDATE users SET balance = balance - ? WHERE card_id = ? AND balance >= ?",
            (total, req.card_id, total),
        )
        if cur.rowcount == 0:
            cur.execute("ROLLBACK")
            raise HTTPException(status_code=402, detail="insufficient funds")

        now = datetime.utcnow().isoformat()
        for li in req.items:
            for _ in range(li.quantity):
                cur.execute(
                    "INSERT INTO transaction_history (user_card_id, item_id, time) VALUES (?, ?, ?)",
                    (req.card_id, li.item_id, now),
                )

        # optionally persist idempotency result
        result_summary = {"total": total, "timestamp": now}
        if idempotency_key:
            cur.execute(
                "INSERT INTO idempotency(key, result_json) VALUES (?, ?)",
                (idempotency_key, str(result_summary)),
            )

        cur.execute("COMMIT")
        return {"success": True, "total": total, "summary": result_summary}
    except HTTPException:
        raise
    except Exception:
        cur.execute("ROLLBACK")
        raise HTTPException(status_code=500, detail="internal error")
    finally:
        conn.close()


@app.post("/admin/archive", status_code=200)
async def archive_old_transactions():
    """
    Archives transactions older than a week to a file and cleans up old data.
    This operation will block all other API calls while running.
    Steps:
    1. Export old transactions to a CSV file
    2. Delete exported transactions from the database
    3. Clean up expired idempotency keys
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Begin exclusive transaction - this will block other connections
        cur.execute("BEGIN EXCLUSIVE TRANSACTION")

        # Get the cutoff date for old transactions (1 week ago)
        cur.execute("SELECT datetime('now', '-7 days') as cutoff")
        cutoff_date = cur.fetchone()["cutoff"]

        # First, let's get all old transactions
        cur.execute(
            """
            SELECT th.id, th.user_card_id, u.name as user_name, 
                   th.item_id, i.name as item_name, i.price, th.time
            FROM transaction_history th
            LEFT JOIN users u ON th.user_card_id = u.card_id
            LEFT JOIN items i ON th.item_id = i.id
            WHERE th.time < ?
        """,
            (cutoff_date,),
        )

        old_transactions = cur.fetchall()

        if old_transactions:
            # Create archive filename with timestamp
            archive_dir = Path("transaction_archives")
            archive_dir.mkdir(exist_ok=True)

            archive_path = (
                archive_dir
                / f"transactions_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            )

            # Write to CSV file
            with open(archive_path, "w", newline="") as f:
                import csv

                writer = csv.writer(f)
                writer.writerow(
                    [
                        "id",
                        "user_card_id",
                        "user_name",
                        "item_id",
                        "item_name",
                        "price",
                        "transaction_time",
                    ]
                )

                for trans in old_transactions:
                    writer.writerow(
                        [
                            trans["id"],
                            trans["user_card_id"],
                            trans["user_name"],
                            trans["item_id"],
                            trans["item_name"],
                            trans["price"],
                            trans["time"],
                        ]
                    )

            # Delete archived transactions
            cur.execute(
                """
                DELETE FROM transaction_history
                WHERE time < ?
            """,
                (cutoff_date,),
            )

            archived_count = len(old_transactions)
        else:
            archived_count = 0
            archive_path = None

        # Clean up expired idempotency keys (older than 24 hours)
        cur.execute(
            """
            DELETE FROM idempotency 
            WHERE datetime('now', '-24 hours') >= created_at
        """
        )
        deleted_keys = cur.execute("SELECT changes() as count").fetchone()["count"]

        cur.execute("COMMIT")

        return {
            "success": True,
            "transactions_archived": archived_count,
            "archive_file": str(archive_path) if archive_path else None,
            "expired_keys_deleted": deleted_keys,
            "archive_time": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        cur.execute("ROLLBACK")
        raise HTTPException(
            status_code=500, detail=f"Archive operation failed: {str(e)}"
        )
    finally:
        conn.close()


# TODO: return new balance after adding funds
# Endpoint to add balance to a user
@app.patch("/user/{card_id}/balance", status_code=204)
def add_balance_to_user(card_id: str, amount: int):
    """
    Patch endpoint to add balance to a user.
    Example: PATCH /user/123/balance
    Body: { "amount": 100 }
    """

    if not confirm_user_from_xpel_db(card_id):
        raise HTTPException(
            status_code=403, detail="User not found or inactive in xp-el database"
        )

    if amount == 0:
        return  # no-op

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET balance = balance + ? WHERE card_id = ?",
            (amount, card_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
        conn.commit()
    finally:
        conn.close()


# Endpoint to get user balance
@app.get("/balance/{card_id}")
def get_balance_from_card(card_id: str):
    """
    Get user balance by card_id.
    Example: GET /balance/1234567890
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, balance FROM users WHERE card_id = ?", (card_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return {"name": row["name"], "balance": row["balance"]}
