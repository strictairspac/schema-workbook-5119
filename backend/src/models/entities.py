from sqlalchemy import Column,Integer,String,JSON,DateTime,ForeignKey,Text,Boolean,UniqueConstraint
from datetime import datetime,timezone
from src.config.database import Base
class User(Base):
    __tablename__='users'
    id=Column(Integer,primary_key=True);email=Column(String(120),unique=True,nullable=False);password=Column(String(300),nullable=False);role=Column(String(20),nullable=False)
class Relation(Base):
    __tablename__='relations'
    id=Column(Integer,primary_key=True);code=Column(String(80),unique=True,nullable=False);title=Column(String(160),nullable=False);attributes=Column(JSON,nullable=False);note=Column(String(300),default='')
class Dependency(Base):
    __tablename__='dependencies'
    id=Column(Integer,primary_key=True);relation_id=Column(Integer,ForeignKey('relations.id'),nullable=False);lhs=Column(JSON,nullable=False);rhs=Column(JSON,nullable=False);note=Column(String(300),default='')
class Report(Base):
    __tablename__='reports'
    id=Column(Integer,primary_key=True);name=Column(String(120),nullable=False);relation_id=Column(Integer,ForeignKey('relations.id'),nullable=False)
    status=Column(String(20),nullable=False,default='queued');input_snapshot=Column(JSON,nullable=False);result=Column(JSON,nullable=True);error=Column(Text,nullable=True)
    created_at=Column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Audit(Base):
    __tablename__='audit_logs'
    id=Column(Integer,primary_key=True);actor=Column(String(120),nullable=False);action=Column(String(160),nullable=False);created_at=Column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class TxnCounter(Base):
    __tablename__='txn_counter'
    id=Column(Integer,primary_key=True);seq=Column(Integer,nullable=False,default=0)
class TxnLog(Base):
    __tablename__='txn_logs'
    id=Column(Integer,primary_key=True);commit_seq=Column(Integer,unique=True,nullable=False);actor=Column(String(120),nullable=False);summary=Column(String(300),nullable=False);ops=Column(JSON,nullable=False);created_at=Column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Backup(Base):
    __tablename__='backups'
    id=Column(Integer,primary_key=True);actor=Column(String(120),nullable=False);commit_seq=Column(Integer,nullable=False)
    relations=Column(JSON,nullable=False);dependencies=Column(JSON,nullable=False);relation_count=Column(Integer,nullable=False);dependency_count=Column(Integer,nullable=False)
    sha256=Column(String(64),nullable=False);created_at=Column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Drill(Base):
    __tablename__='drills'
    id=Column(Integer,primary_key=True);relation_id=Column(Integer,nullable=False);relation_code=Column(String(80),nullable=False)
    backup_id=Column(Integer,nullable=True);target_txn_id=Column(Integer,nullable=False);target_commit_seq=Column(Integer,nullable=False)
    status=Column(String(20),nullable=False,default='pending');applied_seq=Column(Integer,nullable=False,default=0);expected_end_seq=Column(Integer,nullable=False,default=0)
    initialized=Column(Boolean,nullable=False,default=False)
    expected_relation_count=Column(Integer,nullable=True);expected_dependency_count=Column(Integer,nullable=True)
    checksum=Column(String(64),nullable=True);error=Column(Text,nullable=True);actor=Column(String(120),nullable=False)
    created_at=Column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class DrillRelation(Base):
    __tablename__='drill_relations'
    __table_args__=(UniqueConstraint('drill_id','relation_id'),)
    id=Column(Integer,primary_key=True);drill_id=Column(Integer,ForeignKey('drills.id'),nullable=False,index=True);relation_id=Column(Integer,nullable=False)
    code=Column(String(80),nullable=False);title=Column(String(160),nullable=False);attributes=Column(JSON,nullable=False);note=Column(String(300),default='')
class DrillDependency(Base):
    __tablename__='drill_dependencies'
    __table_args__=(UniqueConstraint('drill_id','dependency_id'),)
    id=Column(Integer,primary_key=True);drill_id=Column(Integer,ForeignKey('drills.id'),nullable=False,index=True);dependency_id=Column(Integer,nullable=False);relation_id=Column(Integer,nullable=False)
    lhs=Column(JSON,nullable=False);rhs=Column(JSON,nullable=False);note=Column(String(300),default='')
