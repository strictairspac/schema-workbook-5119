from pydantic import BaseModel,Field
class DrillInput(BaseModel):
    relation_id:int=Field(gt=0)
    target_txn_id:int=Field(gt=0)
