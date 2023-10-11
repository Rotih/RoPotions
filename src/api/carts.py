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

carts={}
@router.post("/")
def create_cart(new_cart: NewCart):
    """ """
    cart_id = len(carts) + 1
    carts[cart_id] = {}
    
    return {"cart_id": cart_id}


@router.get("/{cart_id}")
def get_cart(cart_id: int):
    """ """
    return carts[cart_id-1]


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    carts[cart_id][item_sku]= cart_item.quantity

    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    cart = carts[cart_id]
    num_red = 0
    num_green = 0
    num_blue = 0
    for item_sku in cart:
        item_color = item_sku.split('_')[0].lower()
        if(item_color == "red"):
            num_red += cart[item_sku]
            gold_to_add = num_red * 10
        elif(item_color == "green"):
            num_green += cart[item_sku]
            gold_to_add = num_green * 1
        elif(item_color == "blue"):
            num_blue += cart[item_sku]
            gold_to_add = num_blue * 1
        with db.engine.begin() as connection:
           sql_query = sqlalchemy.text("""
                UPDATE global_inventory 
                SET num_:item_color_potions = num_:item_color_potions - :num_sold,
                    gold = gold + gold_to_add
            """)
           connection.execute(sql_query, {"item_color": item_color, "num_sold": cart[item_sku], "gold_to_add": gold_to_add})

    return {"total_potions_bought": num_red + num_green + num_blue, "total_gold_paid": (num_red * 10 + num_green + num_blue)}
