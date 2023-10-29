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
                """SELECT potion_id FROM potion_inventory
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
    bottle_plan = []
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT 
            SUM(red_ml_change) AS red_ml_total,
            SUM(blue_ml_change) AS blue_ml_total,
            SUM(dark_ml_change) AS dark_ml_total,
            SUM(green_ml_change) AS green_ml_total,
            SUM(potion_quantity) AS num_potions
            FROM ledger_all""")).one()
        red_ml = result.red_ml_total
        green_ml = result.green_ml_total
        blue_ml = result.blue_ml_total  
        dark_ml = result.dark_ml_total
        num_potions = result.num_potions

        potions = connection.execute(sqlalchemy.text("SELECT * from potion_inventory ORDER BY id DESC"))
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
                num_potions += 1
                

        for potion in plan:
            bottler.append({
                "potion_type": plan[potion][1],
                "quantity": plan[potion][0]
            })
        return bottler
