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

    sort_column_str = {
        search_sort_options.customer_name: "carts.customer_name",
        search_sort_options.item_sku: "potion_inventory.sku",
        search_sort_options.line_item_total: "(cart_items.quantity * potion_inventory.price)",
        search_sort_options.timestamp: "ledger_all.created_at",
    }.get(sort_col)
    
    if not sort_column_str:
        raise ValueError("Invalid sorting column provided.")

    order_direction = "ASC" if sort_order == search_sort_order.asc else "DESC"
    
    current_page_number = int(search_page) if search_page else 0
    records_offset = current_page_number * 5
    
    sql_query = f"""
        SELECT
        cart_items.id AS line_item_id,
        potion_inventory.sku AS item_sku,
        carts.customer_name AS customer_name,
        (cart_items.quantity * potion_inventory.price) AS order_total_price,
        ledger_all.created_at AS order_timestamp
        FROM cart_items
        JOIN carts ON carts.cart_id = cart_items.cart_id
        JOIN potion_inventory ON potion_inventory.id = cart_items.potion_id
        LEFT JOIN ledger_all ON ledger_all.potion_id = potion_inventory.id
        WHERE carts.customer_name LIKE %s
        AND potion_inventory.sku LIKE %s
        ORDER BY {sort_column_str} {order_direction}
        LIMIT 5 OFFSET {records_offset}
    """
    
    customer_name_filter = f"%{customer_name}%" if customer_name else "%"
    potion_sku_filter = f"%{potion_sku}%" if potion_sku else "%"

    with db.engine.connect() as connection:
        query_results = connection.execute(sql_query, (customer_name_filter, potion_sku_filter)).fetchall()

    formatted_output = [
        {
            "line_item_id": row[0],
            "item_sku": row[1],
            "customer_name": row[2],
            "line_item_total": row[3],
            "timestamp": row[4].isoformat() if row[4] else None
        }
        for row in query_results
    ]

    count_query = f"""
        SELECT COUNT(*)
        FROM cart_items
        JOIN carts ON carts.cart_id = cart_items.cart_id
        JOIN potion_inventory ON potion_inventory.id = cart_items.potion_id
        WHERE carts.customer_name LIKE %s
        AND potion_inventory.sku LIKE %s
    """
    with db.engine.connect() as connection:
        total_record_count = connection.execute(count_query, (customer_name_filter, potion_sku_filter)).scalar()

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
        
        potion_id = connection.execute(sqlalchemy.text("""
            SELECT potion_id
            FROM cart_items
            WHERE cart_id = :cart_id
            """), [{"cart_id": cart_id}]).scalar_one()
        
        curr_num = connection.execute(sqlalchemy.text("""
            SELECT SUM(potion_quantity)
            FROM ledger_all
            WHERE potion_id = :potion_id
        """), [{"potion_id": potion_id}]).scalar_one()

        if curr_num < total_potions_bought:
            return {"total_potions_bought": 0, "total_gold_paid": 0}


        total_gold_paid = connection.execute(sqlalchemy.text("""
            SELECT SUM(cart_items.quantity * potion_inventory.price)
            FROM cart_items
            JOIN potion_inventory ON potion_inventory.id = cart_items.potion_id
            WHERE cart_id = :cart_id
            """), [{"cart_id": cart_id}]).scalar_one()

        connection.execute(sqlalchemy.text("""
            INSERT INTO ledger_all(gold_change, potion_id, potion_quantity)
            SELECT :gold, cart_items.potion_id, -:potion_quantity
            FROM cart_items
            WHERE cart_id = :cart_id;
            """), [{"cart_id": cart_id, "gold": total_gold_paid, "potion_quantity": total_potions_bought}])

    return {"total_potions_bought": total_potions_bought, "total_gold_paid": total_gold_paid}