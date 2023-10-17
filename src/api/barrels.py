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
    for barrel in barrels_delivered:
        print(barrel)
        barrel_color = barrel.sku.split('_')[1].lower()

        barrel_color_ml = f"num_{barrel_color}_ml"

        with db.engine.begin() as connection:
            sql_query = sqlalchemy.text(f"""
                UPDATE global_inventory 
                SET gold = gold - :gold_to_subtract, 
                    {barrel_color_ml} = {barrel_color_ml} + :ml_to_add
            """)
            connection.execute(sql_query, {"gold_to_subtract": barrel.price * barrel.quantity, "ml_to_add": barrel.ml_per_barrel * barrel.quantity})

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT gold, num_red_ml, num_blue_ml, num_dark_ml, num_green_ml FROM global_inventory")).first()

    gold = result.gold
    redml = result.num_red_ml
    greenml = result.num_gree_nml
    blueml = result.num_blue_ml
    darkml = result.num_dark_ml

    plan = {}

    for barrel in wholesale_catalog:
        barrel_color = barrel.sku.split('_')[1].lower()
        if gold > barrel.price:
            if (barrel_color == "red" and redml < 100):
                if barrel.sku in plan:
                    plan[barrel.sku] += 1
                else:
                    plan[barrel.sku] = 1
            if (barrel_color == "green" and greenml < 100):
                if barrel.sku in plan:
                    plan[barrel.sku] += 1
                else:
                    plan[barrel.sku] = 1
            if (barrel_color == "blue" and blueml < 100):
                if barrel.sku in plan:
                    plan[barrel.sku] += 1
                else:
                    plan[barrel.sku] = 1
            if (barrel_color == "dark" and darkml < 100):
                if barrel.sku in plan:
                    plan[barrel.sku] += 1
                else:
                    plan[barrel.sku] = 1

    
    for barrel in plan:
        plan.append(
            {
                "sku": barrel,
                "quantity": plan[barrel]
            }
        )
    
    return plan