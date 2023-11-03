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
    redml = 0
    greenml = 0
    blueml = 0
    darkml = 0
    gold = 0
    for barrel in barrels_delivered:
        print(barrel)
        barrel_color = barrel.sku.split('_')[1].lower()

        if barrel_color == "red":
            redml += barrel.ml_per_barrel * barrel.quantity
        if barrel_color == "green":
            greenml += barrel.ml_per_barrel * barrel.quantity
        if barrel_color == "blue":
            blueml += barrel.ml_per_barrel * barrel.quantity
        if barrel_color == "dark":
            darkml += barrel.ml_per_barrel * barrel.quantity
        gold -= barrel.price * barrel.quantity

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO ledger_all (red_ml_change, green_ml_change, blue_ml_change, dark_ml_change, gold_change)
            VALUES (:redml, :greenml, :blueml, :darkml, :gold)
            """), [{"redml": redml, "greenml": greenml, "blueml": blueml, "darkml": darkml, "gold": gold}])
    
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
        result = connection.execute(sqlalchemy.text("""
            SELECT 
            SUM(gold_change) AS gold_total,
            SUM(red_ml_change) AS red_ml_total,
            SUM(blue_ml_change) AS blue_ml_total,
            SUM(dark_ml_change) AS dark_ml_total,
            SUM(green_ml_change) AS green_ml_total
            FROM ledger_all
        """)).one()

    gold = result.gold_total
    redml = result.red_ml_total
    blueml = result.blue_ml_total
    darkml = result.dark_ml_total
    greenml = result.green_ml_total

    brown_budget = gold * 0.2
    budgets = {
        "red": gold * 0.3 + brown_budget / 2,
        "green": gold * 0.3 + brown_budget / 2,
        "blue": 0,
        "dark": gold * 0.2
    }

    #calculate cost-effectiveness and sort the catalog accordingly
    wholesale_catalog.sort(key=lambda barrel: barrel.ml_per_barrel / barrel.price, reverse=True)

    plan = {}
    ml_thresholds = {
        "red": 500,
        "green": 500,
        "blue": 300,
        "dark": 300
    }

    for barrel in wholesale_catalog:
        barrel_color = barrel.sku.split('_')[1].lower()

        if gold >= barrel.price and budgets.get(barrel_color, 0) >= barrel.price:
            purchase_quantity = min(barrel.quantity, int(budgets[barrel_color] / barrel.price))

            if purchase_quantity > 0:
                if barrel_color == "red" and redml < ml_thresholds["red"]:
                    plan[barrel.sku] = plan.get(barrel.sku, 0) + purchase_quantity
                    gold -= barrel.price * purchase_quantity
                    budgets[barrel_color] -= barrel.price * purchase_quantity

                elif barrel_color == "green" and greenml < ml_thresholds["green"]:
                    plan[barrel.sku] = plan.get(barrel.sku, 0) + purchase_quantity
                    gold -= barrel.price * purchase_quantity
                    budgets[barrel_color] -= barrel.price * purchase_quantity

                elif barrel_color == "blue" and blueml < ml_thresholds["blue"]:
                    plan[barrel.sku] = plan.get(barrel.sku, 0) + purchase_quantity
                    gold -= barrel.price * purchase_quantity
                    budgets[barrel_color] -= barrel.price * purchase_quantity

                elif barrel_color == "dark" and darkml < ml_thresholds["dark"]:
                    plan[barrel.sku] = plan.get(barrel.sku, 0) + purchase_quantity
                    gold -= barrel.price * purchase_quantity
                    budgets[barrel_color] -= barrel.price * purchase_quantity

    barrel_plan = []
    for barrel in plan:
        barrel_plan.append(
            {
                "sku": barrel,
                "quantity": plan[barrel]
            }
        )

    return barrel_plan