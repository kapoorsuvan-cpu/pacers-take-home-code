"""Reproduce possession, event and shot analysis from shufinskiy/nba_data.
Run: python analyze.py --data /path/to/downloaded/tar.xz/files --out results
Only pandas/numpy plus Python standard library required.
"""
import argparse,json,re,tarfile
from pathlib import Path
import pandas as pd
import numpy as np
P=argparse.ArgumentParser();P.add_argument('--data',type=Path,default=Path('data'));P.add_argument('--out',type=Path,default=Path('results'));args=P.parse_args();args.out.mkdir(parents=True,exist_ok=True)
def load(name):
 with tarfile.open(args.data/(name+'.tar.xz')) as t:return pd.read_csv(t.extractfile(name+'.csv'),low_memory=False)
def sec(s):
 a=str(s).split(':');return float(a[0])*60+float(a[1])
def summ(g):
 n=len(g);fga=g.FG2A.sum()+g.FG3A.sum();return pd.Series(dict(poss=n,points=g.PTS.sum(),ppp=g.PTS.mean(),tov_rate=g.TURNOVERS.mean()*100,efg=(g.FG2M.sum()+1.5*g.FG3M.sum())/fga*100 if fga else np.nan,orb_poss=(g.OFFENSIVEREBOUNDS>0).mean()*100,avg_seconds=g.DURATION.mean()))
qa={};tables={}
for season,suffix in [('regular','2024'),('playoffs','po_2024')]:
 raw=load('nbastats_'+suffix).drop_duplicates();shots=load('shotdetail_'+suffix);p=load('pbpstats_'+suffix)
 raw['DESC']=raw.HOMEDESCRIPTION.fillna('')+raw.VISITORDESCRIPTION.fillna('')
 side=shots.drop_duplicates('GAME_ID').set_index('GAME_ID')[['HTM','VTM']]
 raw['TEAM']=raw.PLAYER1_TEAM_ABBREVIATION
 raw.loc[raw.TEAM.isna() & raw.HOMEDESCRIPTION.notna(),'TEAM']=raw.GAME_ID.map(side.HTM)
 raw.loc[raw.TEAM.isna() & raw.VISITORDESCRIPTION.notna(),'TEAM']=raw.GAME_ID.map(side.VTM)
 # Each possession repeats once per event-video link. DESCRIPTION/URL are not possession identifiers.
 before=len(p);p=p.drop_duplicates(subset=[c for c in p if c not in ['DESCRIPTION','URL']]).copy()
 teams=raw.groupby('GAME_ID').TEAM.apply(lambda g:sorted(set(g.dropna())))
 assert all(len(t)==2 for t in teams)
 p['TEAM']=[next(t for t in teams.loc[gid] if t!=opp) for gid,opp in zip(p.GAMEID,p.OPPONENT)]
 p.EVENTS=p.EVENTS.fillna('');p['FTM']=p.EVENTS.map(lambda s:sum('Free Throw' in l and 'MISS ' not in l for l in s.split('\n')))
 p['FTA']=p.EVENTS.map(lambda s:sum('Free Throw' in l for l in s.split('\n')))
 ft_owner=raw[raw.EVENTMSGTYPE.eq(3)].drop_duplicates(['GAME_ID','DESC']).set_index(['GAME_ID','DESC']).TEAM.to_dict()
 p['FTM']=[sum('Free Throw' in line and 'MISS ' not in line and ft_owner.get((gid,line),team)==team for line in ev.split('\n')) for gid,team,ev in zip(p.GAMEID,p.TEAM,p.EVENTS)]
 p['PTS']=2*p.FG2M+3*p.FG3M+p.FTM
 p['DURATION']=p.STARTTIME.map(sec)-p.ENDTIME.map(sec)
 # A real attacking possession has a shot attempt, free throw or turnover; discard empty period endings.
 empty=~((p.FG2A+p.FG3A+p.FTA+p.TURNOVERS)>0);excluded=p[empty].copy();p=p[~empty].copy()
 p['LIVE_START']=p.STARTTYPE.str.contains('Miss|Block|Steal')
 p['QUICK']=p.LIVE_START & p.DURATION.between(0,7) & (p.OFFENSIVEREBOUNDS==0)
 p['AFTER_MAKE']=p.STARTTYPE.str.contains('Make')
 p['NON_GARBAGE']=~(((p.PERIOD==4)&(p.STARTSCOREDIFFERENTIAL.abs()>20)) | ((p.PERIOD<=3)&(p.STARTSCOREDIFFERENTIAL.abs()>25)))
 raw['FGA']=raw.EVENTMSGTYPE.isin([1,2]);raw['FGM']=raw.EVENTMSGTYPE==1;raw['THREE']=raw.DESC.str.contains('3PT')
 raw['FTA']=raw.EVENTMSGTYPE==3;raw['FTM']=raw.FTA & ~raw.DESC.str.contains('MISS')
 raw['PTS']=raw.FGM.astype(int)*(2+raw.THREE.astype(int))+raw.FTM.astype(int)
 raw['AST']=(raw.EVENTMSGTYPE==1)&raw.PLAYER2_ID.gt(0)
 raw['TOV']=raw.EVENTMSGTYPE==5
 raw['STL']=(raw.EVENTMSGTYPE==5)&raw.PLAYER2_ID.gt(0)
 # Rebound classification uses cumulative Off/Def counters in descriptions.
 rebounds=raw[(raw.EVENTMSGTYPE==4)&raw.PLAYER1_ID.gt(1000)&raw.PLAYER1_ID.lt(1600000000)].copy()
 counters=rebounds.DESC.str.extract(r'Off:(\d+) Def:(\d+)').astype(float);rebounds['OFF_TOTAL']=counters[0];rebounds['DEF_TOTAL']=counters[1]
 rebounds=rebounds.sort_values(['GAME_ID','EVENTNUM'])
 rebounds['OREB']=rebounds.groupby(['GAME_ID','PLAYER1_ID']).OFF_TOTAL.diff().fillna(rebounds.OFF_TOTAL)>0
 rebounds['DREB']=rebounds.groupby(['GAME_ID','PLAYER1_ID']).DEF_TOTAL.diff().fillna(rebounds.DEF_TOTAL)>0
 # Validate totals against source, not estimated possessions.
 pts_raw=raw.groupby(['GAME_ID','TEAM']).PTS.sum();pts_pos=p.groupby(['GAMEID','TEAM']).PTS.sum();diff=pts_pos-pts_raw
 qa[season]={'games_raw':int(raw.GAME_ID.nunique()),'games_possessions':int(p.GAMEID.nunique()),'games_shots':int(shots.GAME_ID.nunique()),'rows_before':before,'unique_possessions_before_empty_filter':len(p)+len(excluded),'empty_endings_removed':len(excluded),'retained_possessions':len(p),'pacers_games':int(p[p.TEAM=='IND'].GAMEID.nunique()),'score_discrepancy_teamgames':int((diff.fillna(0)!=0).sum()),'sum_possession_minus_event_pts':float(diff.sum()),'max_absolute_score_difference':float(diff.abs().max()),'negative_duration':int((p.DURATION<0).sum())}
 diff[diff!=0].to_csv(args.out/f'{season}_score_discrepancies.csv')
 # Global summary uses event points / reconstructed counted possessions. Explicitly not NBA official ratings.
 off=p.groupby('TEAM').apply(summ,include_groups=False);de=p.groupby('OPPONENT').apply(summ,include_groups=False)
 tm=off[['poss','points']].copy();tm['ortg']=raw.groupby('TEAM').PTS.sum()/off.poss*100;tm['drtg']=pd.Series({t:raw[raw.GAME_ID.isin(p[p.TEAM==t].GAMEID.unique()) & (raw.TEAM!=t)].groupby('TEAM').PTS.sum().sum() for t in off.index})/de.poss*100
 # Opponent points are safer calculated game-by-game to exclude neutral events.
 opppts={t:sum(float(pts_raw.get((g,next(x for x in teams[g] if x!=t)),0)) for g in p[p.TEAM==t].GAMEID.unique()) for t in off.index};tm['drtg']=pd.Series(opppts)/de.poss*100;tm['net']=tm.ortg-tm.drtg
 minutes=raw.groupby('GAME_ID').PERIOD.max().map(lambda q:48+max(q-4,0)*5)
 tm['minutes']={t:minutes.loc[p[p.TEAM==t].GAMEID.unique()].sum() for t in off.index};tm['pace']=(off.poss+de.poss)/2/tm.minutes*48
 game_scores=pts_raw.unstack();wins={t:sum(pts_raw[g,t]>pts_raw[g,next(x for x in teams[g] if x!=t)] for g in p[p.TEAM==t].GAMEID.unique()) for t in off.index};tm['wins']=pd.Series(wins);tm['games']=p.groupby('TEAM').GAMEID.nunique()
 box=raw.groupby('TEAM').agg(fga=('FGA','sum'),fgm=('FGM','sum'),fta=('FTA','sum'),ftm=('FTM','sum'),ast=('AST','sum'),tov=('TOV','sum'))
 box['fg3m']=raw[raw.FGM&raw.THREE].groupby('TEAM').size();box['fg3a']=raw[raw.FGA&raw.THREE].groupby('TEAM').size();box['orb']=rebounds.groupby('TEAM').OREB.sum();box['drb']=rebounds.groupby('TEAM').DREB.sum()
 tm=tm.join(box);tm['efg']=(tm.fgm+.5*tm.fg3m)/tm.fga*100;tm['ast_pct']=tm.ast/tm.fgm*100;tm['three_rate']=tm.fg3a/tm.fga*100;tm['three_pct']=tm.fg3m/tm.fg3a*100;tm['tov_per100']=tm.tov/tm.poss*100
 for t in tm.index:
  gs=p[p.TEAM==t].GAMEID.unique();opp_reb=rebounds[rebounds.GAME_ID.isin(gs)&(rebounds.TEAM!=t)];tm.loc[t,'oreb_pct']=tm.loc[t,'orb']/(tm.loc[t,'orb']+opp_reb.DREB.sum())*100;tm.loc[t,'dreb_pct']=tm.loc[t,'drb']/(tm.loc[t,'drb']+opp_reb.OREB.sum())*100
 for metric in ['ortg','drtg','net','pace','efg','ast_pct','three_rate','three_pct','tov_per100','oreb_pct','dreb_pct']:
  high=metric not in ['drtg','tov_per100'];tm[metric+'_rank']=tm[metric].rank(ascending=not high,method='min');tm[metric+'_pctile']=(len(tm)-tm[metric].rank(ascending=not high,method='average'))/(len(tm)-1)*100
 tm.to_csv(args.out/f'{season}_team_metrics.csv');tables[season]=tm
 # Start-of-possession, quick live-ball attacks and clutch splits.
 spl=[]
 conditions={'all':pd.Series(True,index=p.index),'quick_live_7s':p.QUICK,'after_make':p.AFTER_MAKE,'after_steal':p.STARTTYPE.eq('Off Steal'),'after_miss':p.STARTTYPE.str.contains('Miss'),'after_timeout':p.STARTTYPE.eq('Off Timeout'),'offensive_rebound':p.OFFENSIVEREBOUNDS.gt(0),'late_clock_18s_plus':p.DURATION.ge(18)&p.OFFENSIVEREBOUNDS.eq(0),'clutch':(p.PERIOD>=4)&p.STARTTIME.map(sec).le(300)&p.STARTSCOREDIFFERENTIAL.abs().le(5)}
 for scope,q in [('all_minutes',p),('non_garbage',p[p.NON_GARBAGE])]:
  for label,mask in conditions.items():
   z=q[mask.loc[q.index]]
   for side,key in [('off','TEAM'),('def','OPPONENT')]:
    su=z.groupby(key).apply(summ,include_groups=False);su['scope']=scope;su['side']=side;su['split']=label;su['share']=su.poss/(q.groupby(key).size())*100;su['rank_ppp']=su.ppp.rank(ascending=side=='def',method='min');su['rank_share']=su.share.rank(ascending=False,method='min');su['percentile_ppp']=(len(su)-su.ppp.rank(ascending=side=='def',method='average'))/(len(su)-1)*100;spl.append(su.reset_index().rename(columns={key:'team'}))
 pd.concat(spl).to_csv(args.out/f'{season}_possession_splits.csv',index=False)
 # Series summaries and every start type retained for auditing.
 p.groupby(['TEAM','OPPONENT','STARTTYPE']).apply(summ,include_groups=False).to_csv(args.out/f'{season}_start_types.csv')
 if season=='playoffs':
  for_side=[]
  for t in ['IND']:
   pp=p[(p.TEAM==t)|(p.OPPONENT==t)].copy();pp['series_opponent']=np.where(pp.TEAM==t,pp.OPPONENT,pp.TEAM);pp['side']=np.where(pp.TEAM==t,'off','def');pp.groupby(['series_opponent','side']).apply(summ,include_groups=False).to_csv(args.out/'pacers_series.csv')
 # Join shots to raw events for assisted vs unassisted made shots. No assisted misses inferred.
 shots=shots.merge(raw[['GAME_ID','EVENTNUM','AST','PLAYER2_ID']],left_on=['GAME_ID','GAME_EVENT_ID'],right_on=['GAME_ID','EVENTNUM'],how='left',validate='one_to_one')
 shots['TEAM']=shots.TEAM_ID.map(raw.dropna(subset=['PLAYER1_TEAM_ID']).drop_duplicates('PLAYER1_TEAM_ID').set_index('PLAYER1_TEAM_ID').TEAM)
 shots['OPPONENT']=np.where(shots.TEAM==shots.HTM,shots.VTM,shots.HTM)
 shots['three']=shots.SHOT_TYPE.str.startswith('3PT');shots['pts']=shots.SHOT_MADE_FLAG*(2+shots.three.astype(int));shots['rim']=shots.SHOT_ZONE_BASIC.eq('Restricted Area');shots['corner3']=shots.SHOT_ZONE_BASIC.str.contains('Corner 3');shots['assist_make']=shots.AST.fillna(False).astype(bool)
 def shot_summary(g):
  m=g.SHOT_MADE_FLAG.sum();return pd.Series({'fga':len(g),'fgm':m,'fg_pct':100*m/len(g),'pps':g.pts.mean(),'assisted_make_pct':100*g.assist_make.sum()/m if m else np.nan})
 for key in ['TEAM','OPPONENT','PLAYER_NAME']:
  z=shots.groupby([key,'SHOT_ZONE_BASIC']).apply(shot_summary,include_groups=False);z['share']=z.fga/shots.groupby(key).size()*100;z.to_csv(args.out/f'{season}_shots_{key.lower()}.csv')
 player=shots.groupby('PLAYER_NAME').apply(shot_summary,include_groups=False);player['rim_rate']=shots.groupby('PLAYER_NAME').rim.mean()*100;player['three_rate']=shots.groupby('PLAYER_NAME').three.mean()*100;player['efg']=shots.groupby('PLAYER_NAME').pts.mean()*50
 for flag in ['rim','three','corner3']:
  g=shots[shots[flag]].groupby('PLAYER_NAME').SHOT_MADE_FLAG;player[flag+'_a']=g.size();player[flag+'_pct']=g.mean()*100
 player['games']=raw[raw.PLAYER1_ID.gt(1000)].groupby('PLAYER1_NAME').GAME_ID.nunique();player['tov']=raw[raw.TOV].groupby('PLAYER1_NAME').size();player['ast']=raw[raw.AST].groupby('PLAYER2_NAME').size();player['stl']=raw[raw.STL].groupby('PLAYER2_NAME').size();player['ftm']=raw[raw.FTM].groupby('PLAYER1_NAME').size();player['fta']=raw[raw.FTA].groupby('PLAYER1_NAME').size();player['pts']=raw.groupby('PLAYER1_NAME').PTS.sum();player['ast_tov']=player.ast/player.tov;player['ts']=player.pts/(2*(player.fga+.44*player.fta))*100;player['orb']=rebounds.groupby('PLAYER1_NAME').OREB.sum();player['drb']=rebounds.groupby('PLAYER1_NAME').DREB.sum()
 player.to_csv(args.out/f'{season}_player_metrics.csv');shots.to_pickle(args.out/f'{season}_shots_joined.pkl');p.to_pickle(args.out/f'{season}_possessions.pkl');raw.to_pickle(args.out/f'{season}_events.pkl')
 print(season,qa[season]);print(tm.loc['IND'].to_string())
json.dump(qa,open(args.out/'qa.json','w'),indent=2)
# Cross-sectional 2024-25 mapping from reconstructed net rating to actual wins (not a causal projection).
t=tables['regular'];coef=np.polyfit(t.net,t.wins,1);pred=np.polyval(coef,t.net);res=t.wins-pred
json.dump({'intercept':coef[1],'wins_per_net_point':coef[0],'rmse':float(np.sqrt(np.mean(res**2))),'pacers_2025_fitted_wins':float(np.polyval(coef,t.loc['IND','net']))},open(args.out/'wins_model.json','w'),indent=2)
