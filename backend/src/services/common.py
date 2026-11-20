from src.models.entities import Audit
from src.utils.serialization import record
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from src.services.txnlog import log_txn
def save(db,obj,user,action,ops=None):
    db.add(obj)
    try:
        db.flush()
        if callable(ops):ops=ops()
        db.add(Audit(actor=user.email,action=action))
        if ops is not None:log_txn(db,user,action,ops)
        db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'编号已存在或引用对象无效，请调整后重试')
    return record(obj)
