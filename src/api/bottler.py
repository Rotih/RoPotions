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
    darkml = 0
    for potion in potions_delivered:
        if potion.potion_type[0] == 100:
            redml += 100
        if potion.potion_type[1] == 100:
            greenml += 100
        if potion.potion_type[2] == 100:
            blueml += 100
        if potion.potion_type[3] == 100:
            darkml += 100

        red = potion.potion_type[0]
        green = potion.potion_type[1]
        blue = potion.potion_type[2]
        dark = potion.potion_type[3]
        
        with db.engine.begin() as connection:
            sql_query = sqlalchemy.text("""
                UPDATE potion_inventory 
                SET quantity = quantity + :num_potions_delivered
                WHERE red = :red
                AND green = :green
                AND blue = :blue
                AND dark = :dark
            """)
            connection.execute(sql_query,
            {"num_potions_delivered": potion.quantity, "red": red, "green": green, "blue": blue, "dark": dark})

    with db.engine.begin() as connection:
        sql_query = sqlalchemy.text("""
            UPDATE global_inventory
            SET num_red_ml = num_red_ml - :redml,
            num_green_ml = num_green_ml - :greenml,
            num_blue_ml = num_blue_ml - :blueml,
            num_dark_ml = num_dark_ml - :darkml
        """)
        connection.execute(sql_query, {"redml": redml, "greenml": greenml, "blueml": blueml, "darkml": darkml})
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

    # Current Logic: bottle potions based on least amount in inventory. TODO: update to be smarter
    bottle_plan = []
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_ml, num_green_ml, num_blue_ml, num_dark_ml FROM global_inventory")).first()
        red_ml = result.num_red_ml
        green_ml = result.num_green_ml
        blue_ml = result.num_blue_ml  
        dark_ml = result.num_dark_ml

        potions = connection.execute(sqlalchemy.text("SELECT * from potion_inventory ORDER BY quantity asc"))
        num_potions = connection.execute(sqlalchemy.text("SELECT SUM(quantity) FROM potion_inventory")).scalar()
        plan = {}
        bottler = []

        for potion in potions:
            if (num_potions < 300 and ((potion.red <= red_ml) and (potion.green <= green_ml) and (potion.blue <= blue_ml) and (potion.dark <= dark_ml))):
                red_ml -= potion.red
                green_ml -= potion.green
                blue_ml -= potion.blue
                dark_ml -= potion.dark
                if potion.sku in plan:
                    plan[potion.sku][0] += 1
                else:
                    plan[potion.sku] = [1, [potion.red, potion.green, potion.blue, potion.dark]]
                

        for potion in plan:
            bottler.append({
                "potion_type": plan[potion][1],
                "quantity": plan[potion][0]
            })
        return bottler
