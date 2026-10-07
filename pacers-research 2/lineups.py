"""Conservative lineup reconstruction from substitution/event constraints.
A quarter is retained only if precisely five starters per team can be inferred
and all substitutions are valid. No five-man lineup is guessed.
On/off estimates are descriptive and unadjusted for teammates or opponents.
"""
from pathlib import Path
import argparse,json
import pandas as pd
import numpy as np
P=argparse.ArgumentParser();P.add_argument('--results',type=Path,default=Path('results'));a=P.parse_args();base=a.results
TARGETS={'Tyrese Haliburton':('IND',1630169),'Sam Hauser':('BOS',1630573),'Kris Dunn':('LAC',1627739),'Ivica Zubac':('LAC',1627826),'Myles Turner':('IND',1626167)}
def seconds(v):
 m,s=str(v).split(':');return 60*float(m)+float(s)
for season in ['regular','playoffs']:
 raw=pd.read_pickle(base/f'{season}_events.pkl');p=pd.read_pickle(base/f'{season}_possessions.pkl');shots=pd.read_pickle(base/f'{season}_shots_joined.pkl')
 gameids=raw[raw.TEAM.isin(['IND','BOS','LAC'])].GAME_ID.unique();raw=raw[raw.GAME_ID.isin(gameids)].copy();raw['sec']=raw.PCTIMESTRING.map(seconds)
 segments=[];events=[];excluded=[];time_total=0;time_valid=0
 for (gid,period),g in raw.groupby(['GAME_ID','PERIOD'],sort=False):
  # File ordering is chronological, including any replay corrections.
  rs=list(g.to_dict('records'));teams=list(g.TEAM.dropna().unique());teams=[t for t in teams if t in ['IND','BOS','LAC'] or t in g.PLAYER1_TEAM_ABBREVIATION.dropna().unique()]
  if len(teams)!=2:excluded.append((gid,period,'team_count'));continue
  plen=720 if period<=4 else 300;time_total+=plen
  starters={t:set() for t in teams};entered=set();idteam={}
  for r in rs:
   typ=int(r['EVENTMSGTYPE'])
   for j in [1,2,3]:
    pid=r[f'PLAYER{j}_ID'];team=r[f'PLAYER{j}_TEAM_ABBREVIATION']
    if pd.notna(team) and 1000<pid<1600000000:idteam[int(pid)]=team
   if typ==8:
    out=int(r['PLAYER1_ID']);inn=int(r['PLAYER2_ID']);t=idteam.get(out)
    if t in starters and out not in entered:starters[t].add(out)
    entered.add(inn);continue
   if typ not in [1,2,3,4,5,6,10]:continue
   if typ in [3,6] and ('TECHNICAL' in str(r['DESC']).upper() or 'T.FOUL' in str(r['DESC']).upper()):continue
   js=[1,2,3] if typ==10 else [1,2] if typ in [1,2,5,6] else [1]
   for j in js:
    pid=int(r[f'PLAYER{j}_ID']);t=idteam.get(pid)
    if t in starters and pid not in entered:starters[t].add(pid)
  if any(len(v)!=5 for v in starters.values()):excluded.append((gid,period,'initial_'+str([len(v) for v in starters.values()])));continue
  current={t:set(v) for t,v in starters.items()};valid=True;local=[];ev=[];previous=plen
  for r in rs:
   at=r['sec']
   if at>previous+.1:valid=False;break
   if previous>at:local.append((gid,period,previous,at,{t:tuple(sorted(v)) for t,v in current.items()}))
   previous=at
   ev.append((gid,int(r['EVENTNUM']),{t:tuple(sorted(v)) for t,v in current.items()}))
   if r['EVENTMSGTYPE']==8:
    out=int(r['PLAYER1_ID']);inn=int(r['PLAYER2_ID']);t=idteam.get(out)
    if t not in current or out not in current[t] or inn in current[t]:valid=False;break
    current[t].remove(out);current[t].add(inn)
  if not valid:excluded.append((gid,period,'invalid_sub_or_clock'));continue
  if previous>0:local.append((gid,period,previous,0,{t:tuple(sorted(v)) for t,v in current.items()}))
  time_valid+=plen;segments.extend(local);events.extend(ev)
 merged=[]
 for item in segments:
  gid,q,st,en,l=item
  if merged and merged[-1][0:2]==(gid,q) and merged[-1][3]==st and merged[-1][4]==l:
   old=merged[-1];merged[-1]=(gid,q,old[2],en,l)
  else:merged.append(item)
 segments=merged
 lookup={(g,e):l for g,e,l in events};p['STARTSEC']=p.STARTTIME.map(seconds);p['ENDSEC']=p.ENDTIME.map(seconds)
 segby={}
 for g,q,start,end,l in segments:segby.setdefault((g,q),[]).append((start,end,l))
 # Use only possessions wholly inside one unchanged lineup interval. Boundary-spanning possessions excluded.
 prows=[]
 for r in p[p.GAMEID.isin(gameids)].to_dict('records'):
  found=[l for st,en,l in segby.get((r['GAMEID'],r['PERIOD']),[]) if st>=r['STARTSEC'] and en<=r['ENDSEC'] and r['STARTSEC']>r['ENDSEC']]
  if len(found)==1:r['LINEUP']=found[0];prows.append(r)
 pp=pd.DataFrame(prows);out=[]
 for name,(team,pid) in TARGETS.items():
  if not len(pp):continue
  z=pp[(pp.TEAM==team)|(pp.OPPONENT==team)].copy();z['ON']=z.LINEUP.map(lambda l:pid in l.get(team,[]))
  for on,g in z.groupby('ON'):
   o=g[g.TEAM==team];d=g[g.OPPONENT==team];mins=sum((st-en)/60 for gid,q,st,en,l in segments if team in l and ((pid in l[team])==on))
   out.append({'player':name,'team':team,'on':bool(on),'validated_minutes':mins,'off_poss':len(o),'def_poss':len(d),'ortg':100*o.PTS.mean(),'drtg':100*d.PTS.mean(),'net':100*(o.PTS.mean()-d.PTS.mean()),'quick_share':100*o.QUICK.mean(),'opp_quick_share':100*d.QUICK.mean(),'tov_rate':100*o.TURNOVERS.mean()})
 pd.DataFrame(out).to_csv(base/f'{season}_onoff.csv',index=False)
 player_minutes={}
 for g,q,st,en,l in segments:
  for t,ps in l.items():
   for pid in ps:player_minutes[pid]=player_minutes.get(pid,0)+(st-en)/60
 json.dump({'coverage_minutes':time_valid/60,'possible_minutes':time_total/60,'coverage_pct':time_valid/time_total*100,'quarters_excluded':len(excluded),'exclusions':excluded,'player_minutes':player_minutes},open(base/f'{season}_lineup_qa.json','w'),indent=2,default=int)
 print(season,'lineup coverage',time_valid/time_total*100);print(pd.DataFrame(out).to_string(index=False))
 # Hauser shot conversion by court context and offensive-rebound follow-ups.
 s=shots[shots.PLAYER_NAME.eq('Sam Hauser')].copy();rows=[]
 for r in s.to_dict('records'):
  line=lookup.get((r['GAME_ID'],r['GAME_EVENT_ID']),{});bos=line.get('BOS',[])
  r['tatum_on']=1628369 in bos;r['lineup_valid']=bool(bos);rows.append(r)
 s=pd.DataFrame(rows)
 if len(s):
  s.groupby(['lineup_valid','tatum_on','SHOT_ZONE_BASIC']).agg(attempts=('SHOT_MADE_FLAG','size'),makes=('SHOT_MADE_FLAG','sum'),points=('pts','sum')).to_csv(base/f'{season}_hauser_shot_context.csv')
