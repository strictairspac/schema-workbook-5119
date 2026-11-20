from fastapi import APIRouter,Depends
from src.config.database import db_session
from src.utils.security import current,writer
from src.schemas.drill import DrillInput
from src.services import drills,backups,txnlog
router=APIRouter()
@router.get('/txnlogs')
def txnlogs(db=Depends(db_session),user=Depends(writer)):return txnlog.listing(db)
@router.get('/backups')
def backup_list(db=Depends(db_session),user=Depends(current)):return backups.listing(db)
@router.post('/backups',status_code=201)
def backup_create(db=Depends(db_session),user=Depends(writer)):return backups.create(db,user.email)
@router.get('/drills')
def drill_list(db=Depends(db_session),user=Depends(current)):return drills.listing(db)
@router.post('/drills',status_code=201)
def drill_create(data:DrillInput,db=Depends(db_session),user=Depends(writer)):return drills.create(db,data,user)
@router.post('/drills/{ident}/resume')
def drill_resume(ident:int,db=Depends(db_session),user=Depends(writer)):return drills.resume(db,ident,user)
@router.get('/drills/{ident}')
def drill_detail(ident:int,db=Depends(db_session),user=Depends(current)):return drills.detail(db,ident)
