"""Importancia por permutación en train; no reabre ni optimiza con test."""
import json
import time
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.inspection import permutation_importance
from threadpoolctl import threadpool_limits
from .datos import DOCS, BASE, TARGET, split, dump
from .experimentos import tracking, MODEL_NAME

def run():
    tracking();train,_,_=split();result=[]
    # Se utilizan todas las fallas train y 1000 negativos, exclusivamente para explicación descriptiva.
    subset=pd.concat([train[train[TARGET]==1],train[train[TARGET]==0].sample(1000,random_state=42)])
    for alias in ['champion','challenger']:
        model=mlflow.sklearn.load_model(f'models:/{MODEL_NAME}@{alias}')
        with threadpool_limits(limits=1):
            imp=permutation_importance(model,subset[BASE],subset[TARGET],scoring='average_precision',n_repeats=3,random_state=42)
        result += [{'alias':alias,'feature':name,'ap_drop_mean':float(mean),'ap_drop_std':float(std)}
                   for name,mean,std in zip(BASE,imp.importances_mean,imp.importances_std)]
    frame=pd.DataFrame(result);frame.to_csv(DOCS/'importancias_train.csv',index=False)
    dump(DOCS/'explicacion.json',{'scope':'training subset enriched for descriptive explanation, not evaluation',
        'rows':len(subset),'positive_rows':int(subset[TARGET].sum()),'method':'permutation AP, 3 repeats',
        'causal':False,'limitations':'Correlated sensors share importance; enriched sample changes prevalence; not individual SHAP explanations'})
    return frame

if __name__=='__main__':print(run())
