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
    redml = 0
    greenml = 0
    blueml = 0
    for potion in potions_delivered:
        if potion.potion_type[0] == 100:
            redml += 100
        if potion.potion_type[1] == 100:
            greenml += 100
        if potion.potion_type[2] == 100:
            blueml += 100

        red = potion.potion_type[0]
        green = potion.potion_type[1]
        blue = potion.potion_type[2]
        
        with db.engine.begin() as connection:
            sql_query = sqlalchemy.text("""
                UPDATE potion_inventory 
                SET quantity = quantity + :num_potions_delivered
                WHERE red = :red
                AND green = :green
                AND blue = :blue
            """)
            connection.execute(sql_query,
            {"num_potions_delivered": potion.quantity, "red": red, "green": green, "blue": blue })

    with db.engine.begin() as connection:
        sql_query = sqlalchemy.text("""
            UPDATE global_inventory
            SET num_red_ml = num_red_ml - :redml,
            num_green_ml = num_green_ml - :greenml,
            num_blue_ml = num_blue_ml - :blueml
        """)
        connection.execute(sql_query, {"redml": redml, "greenml": greenml, "blueml": blueml})
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
    bottle_plan = []
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_ml, num_green_ml, num_blue_ml FROM global_inventory")).first()
        red_ml = result.num_red_ml
        green_ml = result.num_green_ml
        blue_ml = result.num_blue_ml  

        if red_ml/100 > 0:
            bottle_plan.append(
                {
                    "potion_type": [100, 0, 0, 0],
                    "quantity": int(red_ml//100)
                }
            )
        
        if green_ml/100 > 0:
            bottle_plan.append(
                {
                    "potion_type": [0, 100, 0, 0],
                    "quantity": int(green_ml//100)
                }
            )
        
        if blue_ml/100 > 0:
            bottle_plan.append(
                {
                    "potion_type": [0, 0, 100, 0],
                    "quantity": int(blue_ml//100)
                }
            )

        return bottle_plan
