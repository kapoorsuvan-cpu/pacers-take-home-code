import pandas as pd,tarfile,pathlib
for f in pathlib.Path('work/pacers/data').glob('*.tar.xz'):
 with tarfile.open(f) as t:
  df=pd.read_csv(t.extractfile(t.getmembers()[0]),low_memory=False)
 df.to_pickle(str(f).replace('.tar.xz','.pkl'))
 gid='GAMEID' if 'GAMEID' in df else 'GAME_ID';gids=df[gid].unique();print(f.stem,len(df),'games',len(gids),'ids',min(gids),max(gids))
 if 'GAMEDATE' in df:
  print(df.GAMEDATE.min(),df.GAMEDATE.max());print(df.STARTTYPE.value_counts().to_string());print('IND opponent games',df[df.OPPONENT=='IND'][gid].nunique())
