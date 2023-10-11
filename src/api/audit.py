from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/inventory")
def get_inventory():
    """ """
    sql_to_execute = "SELECT num_red_potions, num_red_ml, num_green_potions, num_green_ml, num_blue_potions, num_blue_ml, gold FROM global_inventory"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute)).first()

    total_potions = result.num_red_potions + result.num_green_potions + result.num_blue_potions
    total_ml = result.num_red_ml + result.num_green_ml + result.num_blue_ml
    return {"number_of_potions": total_potions, "ml_in_barrels": total_ml, "gold": result.gold}

class Result(BaseModel):
    gold_match: bool
    barrels_match: bool
    potions_match: bool

# Gets called once a day
@router.post("/results")
def post_audit_results(audit_explanation: Result):
    """ """
    print(audit_explanation)

    return "OK"
