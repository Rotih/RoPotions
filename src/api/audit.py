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
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT SUM(red_ml_change) as num_red_ml,
            SUM(dark_ml_change) as num_dark_ml,
            SUM(green_ml_change) as num_green_ml,
            SUM(blue_ml_change) as num_blue_ml,
            SUM(gold_change) as gold FROM ledger_all
        """)).one()

        potions = connection.execute(sqlalchemy.text("SELECT SUM(potion_quantity) FROM ledger_all")).scalar()

    num_ml = result.num_red_ml + result.num_green_ml + result.num_blue_ml + result.num_dark_ml
    print(result.gold)
    print(potions)
    
    return {"number_of_potions": potions, "ml_in_barrels": num_ml, "gold": result.gold}

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
