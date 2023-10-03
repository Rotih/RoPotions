from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """

    # Can return a max of 20 items.

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_potions FROM global_inventory"))
        red_potions = result.scalar()
        if red_potions:
            connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = gold + 50, num_red_potions = num_red_potions - 1 WHERE num_red_potions > 0"))
            return [{"sku": "RED_POTION_0", "name": "red potion", "quantity": red_potions, "price": 50, "potion_type": [100, 0, 0, 0]}]

    return [
            {
                "sku": "RED_POTION_0",
                "name": "red potion",
                "quantity": 1,
                "price": 50,
                "potion_type": [100, 0, 0, 0],
            }
        ]
