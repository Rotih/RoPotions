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
            VALUES (:gold, cart_items.potion_id, -:potion_quantity)
            FROM cart_items
            WHERE potion_inventory.id = cart_items.potion_id and cart_items.cart_id = :cart_id;
            """), [{"cart_id": cart_id, "gold": total_gold_paid, "potion_quantity": total_potions_bought}])

    return {"total_potions_bought": total_potions_bought, "total_gold_paid": total_gold_paid}