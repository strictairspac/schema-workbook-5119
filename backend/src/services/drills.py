from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from src.models.entities import Relation,Backup,TxnLog,Drill,DrillRelation,DrillDependency,Audit
from src.utils.serialization import record
from src.constants.enums import DRILL_STATES
from src.services import replay
PENDING,RECOVERED,UNRECOVERABLE=DRILL_STATES
def listing(db):return [record(x) for x in db.scalars(select(Drill).order_by(Drill.id.desc()))]
def create(db,data,user):
    relation=db.get(Relation,data.relation_id)
    if not relation:raise HTTPException(404,'关系草案不存在')
    target=db.get(TxnLog,data.target_txn_id)
    if not target:raise HTTPException(404,'目标提交不存在；回滚的事务不算提交，请从事务日志中选择')
    backup=db.scalar(select(Backup).where(Backup.commit_seq<target.commit_seq).order_by(Backup.commit_seq.desc()).limit(1))
    drill=Drill(relation_id=relation.id,relation_code=relation.code,backup_id=backup.id if backup else None,
        target_txn_id=target.id,target_commit_seq=target.commit_seq,status=PENDING,
        applied_seq=backup.commit_seq if backup else 0,expected_end_seq=target.commit_seq-1,actor=user.email)
    db.add(drill);db.add(Audit(actor=user.email,action='创建恢复演练 草案'+relation.code+' 目标提交#'+str(target.commit_seq)))
    db.commit()
    if not backup:return mark(db,drill.id,'没有早于目标提交的备份，无法还原该提交之前的样子')
    return run(db,drill.id)
def resume(db,ident,user):
    drill=db.get(Drill,ident)
    if not drill:raise HTTPException(404,'演练不存在')
    db.add(Audit(actor=user.email,action='续跑恢复演练 #'+str(ident)));db.commit()
    return run(db,ident)
def run(db,drill_id):
    drill=db.get(Drill,drill_id)
    if not drill:raise HTTPException(404,'演练不存在')
    if drill.status!=PENDING:return record(drill)
    try:return _replay(db,drill)
    except IntegrityError:
        db.rollback();return record(db.get(Drill,drill_id))
def _replay(db,drill):
    backup=db.get(Backup,drill.backup_id)
    if not backup:return mark(db,drill.id,'备份已被移除，无法恢复')
    if not drill.initialized:
        for r in backup.relations:db.add(DrillRelation(drill_id=drill.id,relation_id=r['id'],code=r['code'],title=r['title'],attributes=r['attributes'],note=r.get('note','')))
        for d in backup.dependencies:db.add(DrillDependency(drill_id=drill.id,dependency_id=d['id'],relation_id=d['relation_id'],lhs=d['lhs'],rhs=d['rhs'],note=d.get('note','')))
        drill.initialized=True;db.commit()
    logs=list(db.scalars(select(TxnLog).where(TxnLog.commit_seq>backup.commit_seq,TxnLog.commit_seq<drill.target_commit_seq).order_by(TxnLog.commit_seq)))
    gap=replay.find_gap([x.commit_seq for x in logs],backup.commit_seq+1,drill.target_commit_seq-1)
    if gap is not None:return mark(db,drill.id,f'事务日志断档：缺少第{gap}号提交，无法按实际提交顺序完整回放')
    by_seq={x.commit_seq:x for x in logs}
    state=load_state(db,drill.id)
    for seq in range(drill.applied_seq+1,drill.target_commit_seq):
        try:changes=replay.apply_txn(state,by_seq[seq].ops)
        except replay.ReplayError as e:
            db.rollback();return mark(db,drill.id,str(e))
        mirror(db,drill.id,state,changes)
        drill.applied_seq=seq
        db.commit()
    state=load_state(db,drill.id)
    txns=[by_seq[s].ops for s in range(backup.commit_seq+1,drill.target_commit_seq)]
    exp_rel,exp_dep=replay.expected_counts(backup.relation_count,backup.dependency_count,txns)
    drill.expected_relation_count,drill.expected_dependency_count=exp_rel,exp_dep
    problems=replay.verify_state(state,exp_rel,exp_dep)
    if problems:return mark(db,drill.id,'；'.join(problems))
    drill.status=RECOVERED;drill.checksum=replay.checksum(state);drill.error=None
    db.commit()
    return record(drill)
def mark(db,drill_id,error):
    drill=db.get(Drill,drill_id)
    drill.status=UNRECOVERABLE;drill.error=error
    db.commit()
    return record(drill)
def load_state(db,drill_id):
    rels=db.scalars(select(DrillRelation).where(DrillRelation.drill_id==drill_id))
    deps=db.scalars(select(DrillDependency).where(DrillDependency.drill_id==drill_id))
    return {'relations':{x.relation_id:{'id':x.relation_id,'code':x.code,'title':x.title,'attributes':x.attributes,'note':x.note} for x in rels},
            'dependencies':{x.dependency_id:{'id':x.dependency_id,'relation_id':x.relation_id,'lhs':x.lhs,'rhs':x.rhs,'note':x.note} for x in deps}}
def mirror(db,drill_id,state,changes):
    for table,ident,action in changes:
        if table=='relation':
            row=db.scalar(select(DrillRelation).where(DrillRelation.drill_id==drill_id,DrillRelation.relation_id==ident))
            if action=='delete':
                if row:db.delete(row)
                continue
            data=state['relations'][ident]
            if not row:row=DrillRelation(drill_id=drill_id,relation_id=ident);db.add(row)
            row.code,row.title,row.attributes,row.note=data['code'],data['title'],data['attributes'],data.get('note','')
        else:
            row=db.scalar(select(DrillDependency).where(DrillDependency.drill_id==drill_id,DrillDependency.dependency_id==ident))
            if action=='delete':
                if row:db.delete(row)
                continue
            data=state['dependencies'][ident]
            if not row:row=DrillDependency(drill_id=drill_id,dependency_id=ident);db.add(row)
            row.relation_id,row.lhs,row.rhs,row.note=data['relation_id'],data['lhs'],data['rhs'],data.get('note','')
def detail(db,ident):
    drill=db.get(Drill,ident)
    if not drill:raise HTTPException(404,'演练不存在')
    result=record(drill)
    backup=db.get(Backup,drill.backup_id) if drill.backup_id else None
    result['backup_commit_seq']=backup.commit_seq if backup else None
    if drill.status==RECOVERED:
        rel=db.scalar(select(DrillRelation).where(DrillRelation.drill_id==ident,DrillRelation.relation_id==drill.relation_id))
        deps=list(db.scalars(select(DrillDependency).where(DrillDependency.drill_id==ident,DrillDependency.relation_id==drill.relation_id).order_by(DrillDependency.dependency_id)))
        result['relation']=record(rel) if rel else None
        result['dependencies']=[record(x) for x in deps]
    return result
