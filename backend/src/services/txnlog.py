from sqlalchemy import select
from src.models.entities import TxnCounter,TxnLog
from src.utils.serialization import record
def next_seq(db):
    counter=db.scalar(select(TxnCounter).where(TxnCounter.id==1).with_for_update())
    if not counter:
        counter=TxnCounter(id=1,seq=0);db.add(counter);db.flush()
    counter.seq+=1;db.flush()
    return counter.seq
def log_txn(db,user,summary,ops):
    seq=next_seq(db)
    db.add(TxnLog(commit_seq=seq,actor=user.email,summary=summary,ops=ops))
    return seq
def listing(db):return [record(x) for x in db.scalars(select(TxnLog).order_by(TxnLog.commit_seq.desc()).limit(100))]
