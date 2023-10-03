from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver")
def post_deliver_bottles(potions_delivered: list[PotionInventory]):
    """ """
    print(potions_delivered)
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute))

    return "OK"

# Gets called 4 times a day
@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into red potions.
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_potions FROM global_inventory"))
        red_potions = result.scalar()
        if red_potions:
            connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = gold + <price_of_red_potion>, num_red_potions = num_red_potions - 1 WHERE num_red_potions > 0"))
            return [{"sku": "RED_POTION_0", "name": "red potion", "quantity": red_potions, "price": 50, "potion_type": [100, 0, 0, 0]}]


    return [
            {
                "potion_type": [100, 0, 0, 0],
                "quantity": 5,
            }
        ]
