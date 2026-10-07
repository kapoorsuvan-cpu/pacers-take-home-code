"""Sensitivity checks, game-cluster bootstrap, player percentiles and forecast."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
pa=argparse.ArgumentParser();pa.add_argument('--results',type=Path,default=Path('results'));a=pa.parse_args();b=a.results;rng=np.random.default_rng(20261006)
r=pd.read_pickle(b/'regular_possessions.pkl');p=pd.read_pickle(b/'playoffs_possessions.pkl');shots=pd.read_pickle(b/'regular_shots_joined.pkl');player=pd.read_csv(b/'regular_player_metrics.csv').set_index('PLAYER_NAME')
rows=[]
for season,z in [('regular',r),('playoffs',p)]:
 for scope in ['all','non_garbage']:
  x=z if scope=='all' else z[z.NON_GARBAGE]
  for cut in [5,7,8]:
   fast=x[x.LIVE_START & x.DURATION.between(0,cut) & x.OFFENSIVEREBOUNDS.eq(0)]
   for key,side in [('TEAM','off'),('OPPONENT','def')]:
    n=fast.groupby(key).size();freq=n/x.groupby(key).size();ppp=fast.groupby(key).PTS.mean();rows.append(dict(season=season,scope=scope,cutoff=cut,side=side,ind_n=int(n['IND']),ind_ppp=ppp['IND'],ind_share=100*freq['IND'],share_rank=int(freq.rank(ascending=side=='def',method='min')['IND'])))
pd.DataFrame(rows).to_csv(b/'quick_sensitivity.csv',index=False)
def boot(g,metric):
 x=g.groupby('GAMEID')[metric].agg(['sum','size']).to_numpy();ids=rng.integers(0,len(x),(4000,len(x)));z=x[ids].sum(axis=1);return z[:,0]/z[:,1]
ind=p[p.TEAM.eq('IND')];east=ind[ind.OPPONENT.ne('OKC')];finals=ind[ind.OPPONENT.eq('OKC')];delta=boot(finals,'TURNOVERS')-boot(east,'TURNOVERS');delta_ppp=boot(finals,'PTS')-boot(east,'PTS')
ha=shots[shots.PLAYER_NAME.eq('Sam Hauser')];all3=shots[shots.three];league3=all3.SHOT_MADE_FLAG.mean();co=player[player.three_a>=200];n=len(co);h=co.loc['Sam Hauser'];rank=int(co.three_pct.rank(ascending=False,method='min')['Sam Hauser']);own3=ha[ha.three];m=own3.SHOT_MADE_FLAG.sum();att=len(own3);posterior=(m+200*league3)/(att+200)
# No tracking claims: 'assisted' is NBA scorer credit on makes only.
assist3=own3.assist_make.sum()/m
sample=ha.assign(game=ha.GAME_ID).groupby('game').apply(lambda x:pd.Series({'makes3':x[x.three].SHOT_MADE_FLAG.sum(),'att3':x.three.sum()}),include_groups=False).to_numpy();ids=rng.integers(0,len(sample),(4000,len(sample)));z=sample[ids].sum(axis=1);ci=np.quantile(z[:,0]/z[:,1],[.025,.975])
extra={'hauser':{'3pa':att,'3pm':int(m),'3pt_pct':m/att*100,'cohort_n':n,'rank':rank,'percentile':(n-rank)/(n-1)*100,'league_3pt_pct':league3*100,'assisted_3pm_pct':assist3*100,'shrunken_3pt_pct_prior_200_attempts':posterior*100,'bootstrap_game_95pct_3p':[100*v for v in ci],'surplus_points_vs_league_at_same_3pa':float(3*(m-league3*att))},'playoffs':{'east_poss':len(east),'east_ppp':east.PTS.mean(),'east_tov_pct':east.TURNOVERS.mean()*100,'finals_poss':len(finals),'finals_ppp':finals.PTS.mean(),'finals_tov_pct':finals.TURNOVERS.mean()*100,'tov_delta_pp':100*(finals.TURNOVERS.mean()-east.TURNOVERS.mean()),'tov_delta_game_bootstrap_95pct_pp':[100*v for v in np.quantile(delta,[.025,.975])],'ppp_delta_game_bootstrap_95pct':list(np.quantile(delta_ppp,[.025,.975]))}}
model=json.load(open(b/'wins_model.json'));forecast=[]
for case,net in [('downside',-2.0),('base',2.0),('upside',4.5)]:forecast.append({'case':case,'assumed_net':net,'predicted_wins':model['intercept']+model['wins_per_net_point']*net})
extra['forecast']={'model':model,'scenarios':forecast,'notice':'Scenario net ratings are analyst assumptions, not a fitted injury model. Scenario range is not a confidence interval. Fit uses 2024-25 teams and cannot capture future schedule strength.'}
json.dump(extra,open(b/'deep_findings.json','w'),indent=2)
print(json.dumps(extra,indent=2))
# Retain full player distribution to make the percentile reproducible.
co[['three_a','three_pct','efg','rim_rate','ast_tov']].sort_values('three_pct',ascending=False).to_csv(b/'player_shooting_cohort_200_3pa.csv')
