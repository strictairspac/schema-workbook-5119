import hashlib,json
class ReplayError(Exception):pass
def find_gap(present,start,end):
    have=set(present)
    for seq in range(start,end+1):
        if seq not in have:return seq
    return None
def apply_txn(state,ops):
    changes=[]
    for op in ops:
        table,action,ident=op.get('table'),op.get('op'),op.get('id')
        key='relations' if table=='relation' else 'dependencies' if table=='dependency' else None
        if key is None:raise ReplayError('事务日志包含未知对象：'+str(table))
        rows=state[key]
        if action=='insert':
            if ident in rows:raise ReplayError(f'日志与备份不衔接：#{ident} 已存在，无法重复插入')
            rows[ident]=dict(op['after'])
        elif action=='update':
            if ident not in rows:raise ReplayError(f'日志与备份不衔接：找不到 #{ident}，无法更新')
            rows[ident]=dict(op['after'])
        elif action=='delete':
            if ident not in rows:raise ReplayError(f'日志与备份不衔接：找不到 #{ident}，无法删除')
            del rows[ident]
        else:raise ReplayError('事务日志包含未知操作：'+str(action))
        changes.append((table,ident,action))
    return changes
def expected_counts(relations,dependencies,txns):
    for ops in txns:
        for op in ops:
            if op['op']=='insert':
                if op['table']=='relation':relations+=1
                elif op['table']=='dependency':dependencies+=1
            elif op['op']=='delete':
                if op['table']=='relation':relations-=1
                elif op['table']=='dependency':dependencies-=1
    return relations,dependencies
def verify_state(state,expected_relations,expected_dependencies):
    problems=[]
    if len(state['relations'])!=expected_relations:problems.append(f'草案行数核对不一致：隔离库{len(state["relations"])}行，按日志应为{expected_relations}行')
    if len(state['dependencies'])!=expected_dependencies:problems.append(f'依赖行数核对不一致：隔离库{len(state["dependencies"])}行，按日志应为{expected_dependencies}行')
    codes=set()
    for rel in state['relations'].values():
        if rel['code'] in codes:problems.append('草案编号重复：'+str(rel['code']))
        codes.add(rel['code'])
    for did,dep in state['dependencies'].items():
        rel=state['relations'].get(dep['relation_id'])
        if not rel:problems.append(f'依赖#{did}指向不存在的草案#{dep["relation_id"]}');continue
        if not set(list(dep['lhs'])+list(dep['rhs']))<=set(rel['attributes']):problems.append(f'依赖#{did}引用了草案{rel["code"]}之外的属性')
    return problems
def checksum(state):
    payload={'relations':[state['relations'][k] for k in sorted(state['relations'])],'dependencies':[state['dependencies'][k] for k in sorted(state['dependencies'])]}
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
