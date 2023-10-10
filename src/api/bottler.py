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
    for potion in potions_delivered:
        if potion.potion_type[0] == 100:
            potion_color = "red"
        elif potion.potion_type[1] == 100:
            potion_color = "green"
        elif potion.potion_type[2] == 100:
            potion_color = "blue"

    with db.engine.begin() as connection:
        sql_query = sqlalchemy.text("""
            UPDATE global_inventory 
            SET num_:potion_color_potions = num_:potion_color_potions + :num_potions_delivered, 
                num_:potion_color_ml = num_:potion_color_ml - :num_ml_removed
        """)
        connection.execute(sql_query, {"potion_color": potion_color, "num_potions_delivered": potion.quantity, "removed": potion.quantity * 100})
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
    ret = []
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_ml, num_green_ml, num_blue_ml FROM global_inventory")).first()
        red_ml = result.num_red_ml
        green_ml = result.num_green_ml
        blue_ml = result.num_blue_ml                
        if red_ml/100 > 0:
            ret.append(
                {
                    "potion_type": [100, 0, 0, 0],
                    "quantity": red_ml/100,
                }
            )
        if green_ml/100 > 0:
            ret.append(
                {
                    "potion_type": [0, 100, 0, 0],
                    "quantity": green_ml/100,
                }
            )
        if blue_ml/100 > 0:
            ret.append(
                {
                    "potion_type": [0, 0, 100, 0],
                    "quantity": blue_ml/100,
                }
            )
    return ret
