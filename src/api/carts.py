from enum import Enum
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"   

@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """

    if sort_col is search_sort_options.customer_name:
        sort_column = db.carts.c.customer
    elif sort_col == search_sort_options.item_sku:
        sort_column = db.potion_inventory.c.sku
    elif sort_col == search_sort_options.line_item_total:
        sort_column = (db.cart_items.c.quantity * db.potion_inventory.c.price)
    elif sort_col is search_sort_options.timestamp:
        sort_column = db.ledger_all.c.created_at
    else:
        assert False, "Invalid sorting column provided."

    sorted_column = sort_column.asc() if sort_order == search_sort_order.asc else sort_column.desc()

    current_page_number = int(search_page) if search_page else 0
    records_offset = current_page_number * 5

    query = (
        sqlalchemy.select(
            db.cart_items.c.id.label("line_item_id"),
            db.potion_inventory.c.sku.label("item_sku"),
            db.carts.c.customer.label("customer_name"),
            (db.cart_items.c.quantity * db.potion_inventory.c.price).label("order_total_price"),
            db.ledger_all.c.created_at.label("order_timestamp"),
        )
        .join(db.carts, db.carts.c.cart_id == db.cart_items.c.cart_id)
        .join(db.potion_inventory, db.potion_inventory.c.id == db.cart_items.c.potion_id)
        .outerjoin(db.ledger_all, db.ledger_all.potion_id == db.potion_inventory.c.id)
        .offset(records_offset)
        .limit(5)
        .order_by(sorted_column)
    )

    if customer_name:
        query = query.where(db.carts.c.customer.ilike(f"%{customer_name}%"))
    if potion_sku:
        query = query.where(db.potion_inventory.c.sku.ilike(f"%{potion_sku}%"))

    with db.engine.connect() as connection:
        query_results = connection.execute(query).fetchall()

    formatted_output = [
        {
            "line_item_id": row.line_item_id,
            "item_sku": row.item_sku,
            "customer_name": row.customer_name,
            "line_item_total": row.order_total_price,
            "timestamp": row.order_timestamp.isoformat()
        }
        for row in query_results
    ]

    total_records_query = query.with_only_columns([sqlalchemy.func.count()]).order_by(None)
    with db.engine.connect() as connection:
        total_record_count = connection.execute(total_records_query).scalar()

    previous_page_token = str(current_page_number - 1) if current_page_number > 0 else ""
    next_page_token = str(current_page_number + 1) if (current_page_number + 1) * 5 < total_record_count else ""

    return {
        "previous": previous_page_token,
        "next": next_page_token,
        "results": formatted_output
    }


class NewCart(BaseModel):
    customer: str


@router.post("/")
def create_cart(new_cart: NewCart):
    """ """
    with db.engine.begin() as connection:
        cart_id = connection.execute(sqlalchemy.text("""
            INSERT INTO carts (customer)
            VALUES (:customer)
            RETURNING cart_id
            """), [{"customer": new_cart.customer}]).scalar_one()
    return {'cart_id': cart_id}


@router.get("/{cart_id}")
def get_cart(cart_id: int):
    """ """
    with db.engine.begin() as connection:
        cart = connection.execute(sqlalchemy.text("""
            SELECT * FROM cart_items
            WHERE cart_id = :cart_id
            """), [{"cart_id": cart_id}])
    return cart


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO cart_items (cart_id, quantity, potion_id)
            SELECT :cart_id, :quantity, potion_inventory.id
            FROM potion_inventory WHERE potion_inventory.sku = :item_sku
        """), [{"cart_id": cart_id, "quantity": cart_item.quantity, "item_sku": item_sku}])
        
    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    with db.engine.begin() as connection:
        total_potions_bought = connection.execute(sqlalchemy.text("""
            SELECT SUM(cart_items.quantity)
            FROM cart_items
            JOIN potion_inventory ON potion_inventory.id = cart_items.potion_id
            WHERE cart_id = :cart_id
            """), [{"cart_id": cart_id}]).scalar_one()


        total_gold_paid = connection.execute(sqlalchemy.text("""
            SELECT SUM(cart_items.quantity * potion_inventory.price)
            FROM cart_items
            JOIN potion_inventory ON potion_inventory.id = cart_items.potion_id
            WHERE cart_id = :cart_id
            """), [{"cart_id": cart_id}]).scalar_one()

        connection.execute(sqlalchemy.text("""
            INSERT INTO ledger_all(gold_change, potion_id, potion_quantity)
            SELECT (:gold, cart_items.potion_id, -:potion_quantity)
            FROM cart_items
            WHERE cart_id = :cart_id;
            """), [{"cart_id": cart_id, "gold": total_gold_paid, "potion_quantity": total_potions_bought}])

    return {"total_potions_bought": total_potions_bought, "total_gold_paid": total_gold_paid}