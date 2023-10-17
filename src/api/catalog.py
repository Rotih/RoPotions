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
        result = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory"))

    for potion in result:
        if potion.quantity:
            catalog.append({
               "sku": potion.sku,
               "name": potion.name,
               "quantity": potion.quantity,
               "price": potion.price, 
               "potion_type": [potion.red, potion.green, potion.blue, potion.dark]
            })


    return catalog
