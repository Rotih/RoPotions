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
    catalog = []
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_potions, num_green_potions, num_blue_potions FROM global_inventory"))
        red_potions = result.num_red_potions.scalar()
        green_potions = result.num_green_potions.scalar()
        blue_potions = result.num_blue_potions.scalar()                
        if red_potions:
            catalog.append(
                {
                    "sku": "RED_POTION_0",
                    "name": "red potion",
                    "quantity": red_potions,
                    "price": 10,
                    "potion_type": [100, 0, 0, 0]})
        if green_potions:
            catalog.append(
                {
                    "sku": "GREEN_POTION_0",
                    "name": "green potion",
                    "quantity": green_potions,
                    "price": 10,
                    "potion_type": [0, 100, 0, 0]
                }
            )
        if blue_potions:
            catalog.append(
                {
                    "sku": "BLUE_POTION_0",
                    "name": "blue potion",
                    "quantity": blue_potions,
                    "price": 10,
                    "potion_type": [0, 0, 100, 0]
                }
            )

    return catalog
