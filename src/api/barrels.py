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

        # Dynamically construct the column name
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
        result = connection.execute(sqlalchemy.text("SELECT num_red_potions, num_green_potions, num_blue_potions, gold FROM global_inventory"))
        result = result.first()
        numred=0
        numblue=0
        numgreen=0
        gold = result.gold
    for barrel in wholesale_catalog:
        barrel_color = barrel.sku.split('_')[1].lower()
        if gold > barrel.price:
            if (barrel_color == "red" & numred < 5):
                numred += 1
                gold = gold - barrel.price
            elif (barrel_color == "green" & numgreen < 2):
                numgreen += 1
                gold = gold - barrel.price
            elif (barrel_color == "blue" & numblue < 2):
                numblue += 1
                gold = gold - barrel.price
            
        barrel_plan = []

        if numred > 0:
            barrel_plan.append(        
            {
                "sku": "SMALL_RED_BARREL",
                "quantity": numred,
            },
        )
        if numgreen > 0:
            barrel_plan.append(        
            {
                "sku": "SMALL_GREEN_BARREL",
                "quantity": numgreen,
            },
        )
        if numblue > 0:
            barrel_plan.append(        
            {
                "sku": "SMALL_BLUE_BARREL",
                "quantity": numblue,
            },
        )
        return barrel_plan


