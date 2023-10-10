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

carts=[]
@router.post("/")
def create_cart(new_cart: NewCart):
    """ """
    cart_id = len(carts) + 1
    cart = {"cart_id": cart_id, "customer": new_cart.customer}
    carts.append(cart)
    return cart


@router.get("/{cart_id}")
def get_cart(cart_id: int):
    """ """
    return carts[cart_id-1]


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    carts[cart_id].append(
        {
            "sku": item_sku,
            "quantity": cart_item.quantity
        }
    ) 
    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = gold + 50, num_red_potions = num_red_potions - 1 WHERE num_red_potions > 0"))
        return {"total_potions_bought": 1, "total_gold_paid": 50}
