from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver")
def post_deliver_barrels(barrels_delivered: list[Barrel]):
    """ """

    print(barrels_delivered)
    gold_to_subtract = barrels_delivered*50
    ml_to_add = 500 * barrels_delivered

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET gold = gold - {gold_to_subtract}, num_red_ml = num_red_ml + {ml_to_add}"))

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_potions FROM global_inventory"))
        num_red_potions = result.scalar()
        if num_red_potions < 10:
            return [
                {
                    "sku": "SMALL_RED_BARREL",
                    "quantity": 1,
                }
            ]
    
    return []
            




