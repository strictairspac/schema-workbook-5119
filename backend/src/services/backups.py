import hashlib,json
from sqlalchemy import select
from src.models.entities import Relation,Dependency,Backup,TxnCounter,Audit
from src.utils.serialization import record
def listing(db):return [record(x) for x in db.scalars(select(Backup).order_by(Backup.id.desc()))]
def create(db,actor):
    counter=db.scalar(select(TxnCounter).where(TxnCounter.id==1).with_for_update())
    if not counter:
        counter=TxnCounter(id=1,seq=0);db.add(counter);db.flush()
    relations=[record(x) for x in db.scalars(select(Relation).order_by(Relation.id))]
    dependencies=[record(x) for x in db.scalars(select(Dependency).order_by(Dependency.id))]
    digest=hashlib.sha256(json.dumps({'relations':relations,'dependencies':dependencies},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    obj=Backup(actor=actor,commit_seq=counter.seq,relations=relations,dependencies=dependencies,relation_count=len(relations),dependency_count=len(dependencies),sha256=digest)
    db.add(obj);db.add(Audit(actor=actor,action='创建数据库备份 覆盖至提交#'+str(counter.seq)))
    db.commit()
    return record(obj)
