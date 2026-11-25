"""Prueba opcional real de prompting; nunca inventa una llamada ni una respuesta."""
import json
import os
import time
import requests
import numpy as np
import pandas as pd
import mlflow
from sklearn.model_selection import StratifiedKFold
from .datos import split, BASE, TARGET, DOCS, SEED, dump
from .experimentos import tracking, commit
from .metricas import evaluate

PROMPT = ('Clasifica falla actual en una lectura sintética AI4I. Usa solo las mediciones disponibles. '
          'No infieras RUL ni eventos futuros. Devuelve únicamente JSON con probability entre 0 y 1. '
          'Las etiquetas de los ejemplos son 0 sin falla y 1 con falla. Ejemplos: {examples}. Lectura: {row}')

def run():
    train,_,meta=split();provider=os.getenv('LLM_PROVIDER','openai');model=os.getenv('LLM_MODEL','')
    key=os.getenv('OPENAI_API_KEY' if provider=='openai' else 'ANTHROPIC_API_KEY','')
    if not key or not model:
        evidence = DOCS/'llm.json'
        if evidence.exists():
            saved = json.loads(evidence.read_text(encoding='utf-8'))
            if saved.get('status') == 'executed' and saved.get('dataset_sha256') == meta['dataset_sha256']:
                return saved
        result={'status':'not_executed','reason':'Se requiere API key privada y LLM_MODEL explícito; no hay respuestas ni métricas inventadas.',
                'provider':provider,'protocol':'3 folds de entrenamiento; 20 filas por fold; ejemplos solo de su train; holdout nunca enviado',
                'prompt_template':PROMPT,'scope':'La clasificación numérica sí admite prompting; no hay evidencia ejecutada para este snapshot del dataset.'}
        dump(DOCS/'llm.json',result);return result
    tracking();X=train[BASE];y=train[TARGET].to_numpy();records=[];start=time.perf_counter()
    with mlflow.start_run(run_name='llm_prompting'):
        mlflow.set_tags({'phase':'llm','family':provider,'git_commit':commit(),'scope':'subset CV, not comparable to full CV ranking'})
        mlflow.log_params({'llm_model':model,'seed':SEED,'temperature':0,'source_table':meta['table'],
                           'snapshot_utc':meta['snapshot_utc'],'dataset_sha256':meta['dataset_sha256']})
        for fold,(a,b) in enumerate(StratifiedKFold(3,shuffle=True,random_state=SEED).split(X,y)):
            rng=np.random.default_rng(SEED+fold)
            examples=[]
            for label in [0,1]:
                for idx in rng.choice(a[y[a]==label],3,replace=False):
                    examples.append({**X.iloc[idx].to_dict(),'label':int(y[idx])})
            # Submuestra natural, sin balancearla artificialmente ni cambiarla según respuestas.
            selected=rng.choice(b,min(20,len(b)),replace=False)
            for idx in selected:
                prompt=PROMPT.format(examples=json.dumps(examples),row=X.iloc[idx].to_json())
                if provider=='openai':
                    response=requests.post('https://api.openai.com/v1/chat/completions',timeout=90,
                        headers={'Authorization':'Bearer '+key},json={'model':model,'temperature':0,
                        'messages':[{'role':'user','content':prompt}], 'response_format':{'type':'json_object'}})
                    response.raise_for_status();text=response.json()['choices'][0]['message']['content']
                elif provider=='anthropic':
                    response=requests.post('https://api.anthropic.com/v1/messages',timeout=90,
                        headers={'x-api-key':key,'anthropic-version':'2023-06-01'},
                        json={'model':model,'temperature':0,'max_tokens':100,'messages':[{'role':'user','content':prompt}]})
                    response.raise_for_status();text=response.json()['content'][0]['text']
                else:raise ValueError('LLM_PROVIDER debe ser openai o anthropic')
                value=json.loads(text)['probability']
                if not 0<=float(value)<=1:raise ValueError('Probabilidad inválida')
                records.append({'reading_id':int(train.iloc[idx].reading_id),'fold':fold,'y':int(y[idx]),'probability':float(value)})
        frame=pd.DataFrame(records);frame.to_csv(DOCS/'llm_predictions.csv',index=False)
        metrics=evaluate(frame.y,frame.probability) if frame.y.nunique()==2 else {}
        mlflow.log_metrics({**metrics,'elapsed_seconds':time.perf_counter()-start});mlflow.log_dict({'prompt':PROMPT},'prompt.json')
        mlflow.log_artifact(str(DOCS/'llm_predictions.csv'))
        result={'status':'executed','model':model,'rows':len(frame),'metrics':metrics, 'dataset_sha256':meta['dataset_sha256'],
                'warning':'60 filas de CV; incertidumbre alta y presupuesto distinto. No participa del ranking de 5 familias.'}
        dump(DOCS/'llm.json',result);return result

if __name__=='__main__':print(run())
