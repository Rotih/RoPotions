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

        red = potion.potion_type[0]
        green = potion.potion_type[1]
        blue = potion.potion_type[2]
        dark = potion.potion_type[3]
        
        with db.engine.begin() as connection:
            potion_id = connection.execute(sqlalchemy.text(
                """SELECT id FROM potion_inventory
                WHERE red = :red
                AND green = :green
                AND blue = :blue
                AND dark = :dark
                """), {"red": red, "green": green, "blue": blue, "dark": dark}).scalar_one()

            sql_query = sqlalchemy.text("""
                INSERT INTO ledger_all (red_ml_change, green_ml_change, blue_ml_change, dark_ml_change, potion_id, potion_quantity)
                VALUES (-:redml, -:greenml, -:blueml, -:darkml, :potion_id, :potion_quantity)
            """)
            connection.execute(sql_query, {"redml": red * potion.quantity,
            "greenml": green * potion.quantity, "blueml": blue * potion.quantity,
            "darkml": dark * potion.quantity, "potion_id": potion_id, "potion_quantity": potion.quantity})
            
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

    ML_PER_POTION = 100

    bottle_plan = []

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT 
            SUM(red_ml_change) AS red_ml_total,
            SUM(blue_ml_change) AS blue_ml_total,
            SUM(dark_ml_change) AS dark_ml_total,
            SUM(green_ml_change) AS green_ml_total,
            SUM(potion_quantity) AS num_potions
            FROM ledger_all
        """)).one()

        red_ml = result.red_ml_total
        green_ml = result.green_ml_total
        blue_ml = result.blue_ml_total  
        dark_ml = result.dark_ml_total
        num_potions = result.num_potions

        potions = connection.execute(sqlalchemy.text("""SELECT pi.*, SUM(la.potion_quantity) as total_quantity
            FROM potion_inventory pi
            JOIN ledger_all la ON pi.id = la.potion_id
            GROUP BY pi.id
            ORDER BY total_quantity ASC;
            """))        

        plan = {}

        for potion in potions:
            print(potion)
            possible_potions = float('inf')

            if potion.red > 0:
                possible_potions = min(possible_potions, red_ml // potion.red)

            if potion.green > 0:
                possible_potions = min(possible_potions, green_ml // potion.green)

            if potion.blue > 0:
                possible_potions = min(possible_potions, blue_ml // potion.blue)

            if potion.dark > 0:
                possible_potions = min(possible_potions, dark_ml // potion.dark)

            while possible_potions > 0 and num_potions < 300:
                red_ml -= potion.red
                green_ml -= potion.green
                blue_ml -= potion.blue
                dark_ml -= potion.dark

                if potion.sku in plan:
                    plan[potion.sku][0] += 1
                else:
                    plan[potion.sku] = [1, [potion.red, potion.green, potion.blue, potion.dark]]

                possible_potions -= 1
                num_potions += 1

        for potion in plan:
            bottle_plan.append({
                "potion_type": plan[potion][1],
                "quantity": plan[potion][0]
            })

    return bottle_plan
