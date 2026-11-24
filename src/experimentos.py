"""Baselines, cinco familias, 90 búsquedas, holdout final y Model Registry."""
import argparse
import json
import os
import subprocess
import time
import warnings
from pathlib import Path
import joblib
import mlflow
import mlflow.sklearn
from mlflow.models import infer_signature
from mlflow.tracking import MlflowClient
import numpy as np
import pandas as pd
from scipy.stats import loguniform, randint
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import StratifiedKFold, ParameterSampler
from sklearn.metrics import average_precision_score
from threadpoolctl import threadpool_limits
from .datos import ROOT, DOCS, DATA, SEED, BASE, TARGET, PROJECT, split, dump
from .pipeline import make_pipeline, BusinessRule, DecisionModel
from .metricas import evaluate, choose_threshold

ART=ROOT/'artifacts'; CV=StratifiedKFold(3,shuffle=True,random_state=SEED)
MODEL_NAME=PROJECT+'-modelo'
PIP=['scikit-learn==1.6.1','pandas==2.2.3','numpy==2.2.4','scipy==1.15.2','mlflow==2.22.0']

def tracking():
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env', override=False)
    ART.mkdir(exist_ok=True);DOCS.mkdir(exist_ok=True)
    uri=os.getenv('MLFLOW_TRACKING_URI', 'sqlite:///'+(ART/'mlflow.db').as_posix())
    mlflow.set_tracking_uri(uri)
    if mlflow.get_experiment_by_name(PROJECT) is None:
        mlflow.create_experiment(PROJECT, artifact_location=None if uri.startswith('http') else (ART/'mlruns').as_uri())
    mlflow.set_experiment(PROJECT)

def commit():
    try:return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    except Exception:return 'unavailable'

def models():
    # Valores por defecto salvo semilla; un hilo para reproducibilidad.
    return {'logistic':LogisticRegression(random_state=SEED),
            'random_forest':RandomForestClassifier(random_state=SEED),
            'hist_boosting':HistGradientBoostingClassifier(random_state=SEED),
            'mlp':MLPClassifier(random_state=SEED),
            'gaussian_nb':GaussianNB()}

def cv_fit(estimator,X,y):
    oof=np.zeros(len(y)); fold_ap=[]; fold_train=[]; fold_cost=[]; fit_seconds=[]; notices=[]
    for a,b in CV.split(X,y):
        model=clone(estimator); start=time.perf_counter()
        with warnings.catch_warnings(record=True) as caught, threadpool_limits(limits=1):
            warnings.simplefilter('always');model.fit(X.iloc[a],y[a])
        notices += [str(w.message) for w in caught]
        fit_seconds.append(time.perf_counter()-start)
        prob=model.predict_proba(X.iloc[b])[:,1]; oof[b]=prob
        fold_ap.append(average_precision_score(y[b],prob))
        fold_train.append(average_precision_score(y[a],model.predict_proba(X.iloc[a])[:,1]))
        fold_cost.append(evaluate(y[b],prob)['cost_per_1000'])
    start=time.perf_counter()
    with warnings.catch_warnings(record=True) as caught,threadpool_limits(limits=1):
        warnings.simplefilter('always');estimator.fit(X,y)
    notices += [str(w.message) for w in caught]
    seconds=time.perf_counter()-start
    return estimator,oof,{'cv_ap_mean':float(np.mean(fold_ap)),'cv_ap_std':float(np.std(fold_ap,ddof=1)),
        'train_ap':float(average_precision_score(y,estimator.predict_proba(X)[:,1])),
        'fold_train_ap_mean':float(np.mean(fold_train)),
        'cv_cost_per_1000':float(np.mean(fold_cost)),
        'fit_seconds':seconds,'cv_fit_seconds':float(sum(fit_seconds))},fold_ap,notices

def run_one(name,estimator,phase,params=None,nested=False,derived=True):
    train,_,meta=split();X=train[BASE];y=train[TARGET].to_numpy()
    with mlflow.start_run(run_name=name,nested=nested) as run:
        mlflow.set_tags({'phase':phase,'family':name.split('/')[0],'git_commit':commit(),
                         'source_scope':meta['scope'],'dataset_sha256':meta['dataset_sha256']})
        mlflow.log_params({'seed':SEED,'cv_folds':3,'source_table':meta['table'],
                           'snapshot_utc':meta['snapshot_utc'],'derived':derived,
                           **{k:str(v) for k,v in estimator.get_params().items() if k.startswith('model__') and '__' not in k[7:]}})
        if params:mlflow.log_params({k:str(v) for k,v in params.items()})
        fitted,oof,metrics,folds,notices=cv_fit(estimator,X,y)
        metrics['gap_ap']=metrics['train_ap']-metrics['cv_ap_mean']
        mlflow.log_metrics(metrics); mlflow.log_dict({'fold_ap':folds,'warnings':notices},'cv.json')
        mlflow.log_dict(meta,'dataset.json')
        mlflow.sklearn.log_model(fitted,'pipeline',signature=infer_signature(X,fitted.predict(X)),
                                 input_example=X.head(3),pip_requirements=PIP,code_paths=[str(ROOT/'src')])
        rid=run.info.run_id
        dest=ART/'evaluated';dest.mkdir(exist_ok=True)
        joblib.dump(fitted,dest/(rid+'.joblib'));np.save(dest/(rid+'.npy'),oof)
        result={'name':name,'phase':phase,'run_id':rid,**metrics,'fold_ap':folds,
                'params':params or {},'warnings':len(notices),
                'learning_rate':getattr(fitted.named_steps.get('model',None),'learning_rate',None) if hasattr(fitted,'named_steps') else None}
        print(f'{phase}: {name}: AP={metrics["cv_ap_mean"]:.4f} +/- {metrics["cv_ap_std"]:.4f}',flush=True)
        return result

def baseline_candidates():
    tracking();path=DOCS/'candidatos.json'
    if path.exists():
        _,_,meta=split()
        rows=json.loads(path.read_text(encoding='utf-8'))
        try:
            recorded=MlflowClient().get_run(rows[0]['run_id'])
        except Exception as exc:
            raise RuntimeError('Checkpoint de otro tracking. Restaurar el respaldo o usar scripts/new_experiment.py en un checkout limpio.') from exc
        if recorded.data.tags.get('dataset_sha256') != meta['dataset_sha256']:
            raise ValueError('Checkpoint de otro dataset; no se reutilizan resultados sobre datos distintos')
        return rows
    rows=[]
    rows.append(run_one('dummy',make_pipeline(DummyClassifier(strategy='most_frequent')), 'baseline'))
    rows.append(run_one('business_rule',BusinessRule(),'baseline'))
    dump(DOCS/'baselines.json',rows)
    for name,est in models().items():rows.append(run_one(name,make_pipeline(est),'candidato'))
    ablation=run_one('hist_boosting_without_derived',make_pipeline(models()['hist_boosting'],derived=False),'ablation',derived=False)
    dump(DOCS/'ablacion.json',ablation)
    dump(path,rows); export_runs();return rows

def spaces():
    return {
      'logistic':{'model__C':loguniform(1e-3,1e3),'model__class_weight':[None,'balanced'], 'model__max_iter':[500,1000]},
      'random_forest':{'model__n_estimators':randint(50,151),'model__max_depth':[None,4,6,10,16],
          'model__min_samples_leaf':randint(1,12),'model__max_features':['sqrt',.7,1.], 'model__class_weight':[None,'balanced']},
      'hist_boosting':{'model__learning_rate':loguniform(.02,.3),'model__max_iter':randint(50,151),
          'model__max_leaf_nodes':randint(7,32),'model__l2_regularization':loguniform(1e-4,10),
          'model__min_samples_leaf':randint(10,50)},
      'mlp':{'model__hidden_layer_sizes':[(32,),(64,),(100,),(32,16)],'model__alpha':loguniform(1e-5,.1),
          'model__learning_rate_init':loguniform(1e-4,.01),'model__max_iter':[200,300]},
      'gaussian_nb':{'model__var_smoothing':loguniform(1e-12,1e-2)}}

def tuning():
    candidates=baseline_candidates();tracking();path=DOCS/'tuning.json'
    if path.exists():return json.loads(path.read_text(encoding='utf-8'))
    top=sorted([r for r in candidates if r['phase']=='candidato'], key=lambda r:r['cv_ap_mean'], reverse=True)[:3]
    dump(DOCS/'plan_tuning.json',{'selected_families':[r['name'] for r in top], 'configurations_per_family':30,
        'method':'ParameterSampler aleatorio con semilla, misma CV fija; 30 configuraciones por familia',
        'scales':'C, alpha, var_smoothing, learning_rate y l2 en log; tamaños y profundidades discretos'})
    allrows=[]
    for original in top:
        name=original['name'];checkpoint=DOCS/('tuning_'+name+'.json')
        if checkpoint.exists():allrows+=json.loads(checkpoint.read_text(encoding='utf-8'));continue
        rows=[]
        with mlflow.start_run(run_name='tuning_parent_'+name):
            mlflow.set_tags({'phase':'tuning_parent','family':name,'git_commit':commit()})
            _,_,meta=split()
            mlflow.log_params({'seed':SEED,'cv_folds':3,'configurations':30,
                'source_table':meta['table'],'snapshot_utc':meta['snapshot_utc'],
                'dataset_sha256':meta['dataset_sha256']})
            for i,params in enumerate(ParameterSampler(spaces()[name],n_iter=30,random_state=SEED)):
                params={k:(v.item() if isinstance(v,np.generic) else v) for k,v in params.items()}
                est=make_pipeline(models()[name]).set_params(**params)
                rows.append(run_one(name+f'/config_{i+1:02}',est,'tuning',params,nested=True))
        dump(checkpoint,rows);allrows+=rows
    dump(path,allrows);export_runs();return allrows

def final():
    tuned=tuning();tracking();path=DOCS/'seleccion.json'
    if path.exists():return json.loads(path.read_text(encoding='utf-8'))
    train,test,meta=split();y=train[TARGET].to_numpy()
    candidates=json.loads((DOCS/'candidatos.json').read_text(encoding='utf-8'))
    pool=[r for r in candidates if r['phase']=='candidato']+tuned
    # Dos familias distintas; la elección se congela antes de consultar el holdout.
    ordered=sorted(pool,key=lambda r:r['cv_ap_mean'],reverse=True);chosen=[]
    for r in ordered:
        if r['name'].split('/')[0] not in [x['name'].split('/')[0] for x in chosen]:chosen.append(r)
        if len(chosen)==2:break
    plan=[]
    for r in chosen:
        prob=np.load(ART/'evaluated'/(r['run_id']+'.npy'))
        threshold=choose_threshold(y,prob)
        plan.append({**r,'threshold':threshold,'oof_business':evaluate(y,prob,threshold)})
    dump(DOCS/'decision_before_holdout.json',plan)
    lock=ART/'holdout_started.lock'
    if lock.exists():raise RuntimeError('Holdout ya iniciado; recuperar corrida existente, no reevaluar para elegir otro ganador')
    lock.write_text('Holdout starts after CV ranking and thresholds are frozen',encoding='utf-8')
    results=[];client=MlflowClient()
    for i,r in enumerate(plan):
        fitted=joblib.load(ART/'evaluated'/(r['run_id']+'.joblib'))
        deployed=DecisionModel(fitted,r['threshold']);deployed.classes_=np.array([0,1])
        start=time.perf_counter();prob=deployed.predict_proba(test[BASE])[:,1];inference=time.perf_counter()-start
        metrics=evaluate(test[TARGET].to_numpy(),prob,r['threshold'])
        with mlflow.start_run(run_name='final_'+('champion' if i==0 else 'challenger')) as run:
            mlflow.set_tags({'phase':'final','family':r['name'].split('/')[0],'git_commit':commit(),
                             'selected_by':'CV average precision before holdout', 'source_scope':meta['scope']})
            mlflow.log_params({'selected_run_id':r['run_id'],'threshold':r['threshold'],'seed':SEED,
                'source_table':meta['table'],'snapshot_utc':meta['snapshot_utc'],'dataset_sha256':meta['dataset_sha256']})
            mlflow.log_metrics({**{'test_'+k:v for k,v in metrics.items()},
                               'inference_seconds':inference,'cv_ap_mean':r['cv_ap_mean'],'cv_ap_std':r['cv_ap_std']})
            signature=infer_signature(train[BASE],deployed.predict(train[BASE]))
            info=mlflow.sklearn.log_model(deployed,'pipeline',signature=signature,input_example=train[BASE].head(3),
                pip_requirements=PIP,code_paths=[str(ROOT/'src')])
            version=mlflow.register_model(info.model_uri,MODEL_NAME)
            alias='champion' if i==0 else 'challenger';client.set_registered_model_alias(MODEL_NAME,alias,version.version)
            pd.DataFrame({'reading_id':test.reading_id,'y':test[TARGET], 'probability':prob,
                          'prediction':deployed.predict(test[BASE])}).to_csv(DOCS/(alias+'_predictions.csv'),index=False)
            results.append({**r,'alias':alias,'final_run_id':run.info.run_id,'version':version.version,
                            'test':metrics,'inference_seconds':inference})
    gap=results[0]['cv_ap_mean']-results[1]['cv_ap_mean']
    answer={'model_name':MODEL_NAME,'models':results,'cv_difference':gap,
            'difference_exceeds_fold_std':gap>max(r['cv_ap_std'] for r in results),
            'holdout_policy':'Evaluado una vez para cada finalista; no cambia el ranking de CV',
            'source':meta,'cost_assumptions':{'inspection':500,'emergency':8000,'residual':1500,'capacity':.12}}
    dump(path,answer);export_runs();return answer

def reproduce():
    tracking();result=json.loads((DOCS/'seleccion.json').read_text(encoding='utf-8'))
    train,test,meta=split()
    if meta['dataset_sha256']!=result['source']['dataset_sha256']:raise ValueError('Dataset de otra evaluación')
    model=mlflow.sklearn.load_model(f'models:/{MODEL_NAME}@champion')
    now=evaluate(test[TARGET].to_numpy(),model.predict_proba(test[BASE])[:,1],model.threshold)
    expected=result['models'][0]['test']
    for k,v in expected.items():
        if not np.isclose(now[k],v,rtol=0,atol=1e-12):raise AssertionError(f'No reproduce {k}')
    return {'registry_uri':f'models:/{MODEL_NAME}@champion','reproduced':True,'metrics':now}

def export_runs():
    tracking();exp=mlflow.get_experiment_by_name(PROJECT)
    rows=mlflow.search_runs([exp.experiment_id],max_results=10000)
    # No rutas privadas del host en la exportación de evidencia.
    rows.drop(columns=['artifact_uri'],errors='ignore').to_csv(DOCS/'corridas.csv',index=False)
    return rows

def all_stages():
    from .eda import run
    run();baseline_candidates();tuning();final();print(reproduce())

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['all','candidates','tuning','final','verify','export'])
    stage=parser.parse_args().stage
    {'all':all_stages,'candidates':baseline_candidates,'tuning':tuning,'final':final,
     'verify':lambda:print(reproduce()),'export':export_runs}[stage]()
