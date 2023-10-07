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
    num_potions_delivered = len(potions_delivered)
    num_redml_removed = num_potions_delivered * 100

    with db.engine.begin() as connection:
        sql_query = sqlalchemy.text("""
            UPDATE global_inventory 
            SET num_red_potions = num_red_potions + :num_potions_delivered, 
                num_red_ml = num_red_ml - :num_redml_removed
        """)
        connection.execute(sql_query, {"num_potions_delivered": num_potions_delivered, "num_redml_removed": num_redml_removed})
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
        result = connection.execute(sqlalchemy.text("SELECT num_red_ml FROM global_inventory"))
        red_ml = result.first()
        num_potions = int(red_ml.num_red_ml / 100)
        if red_ml > 0:
            return [
                    {
                        "potion_type": [100, 0, 0, 0],
                        "quantity": red_ml,
                    }
                ]
    return []
