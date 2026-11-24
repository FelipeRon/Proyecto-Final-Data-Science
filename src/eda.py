"""Exploración solo de entrenamiento; el holdout no guía decisiones."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .datos import split, BASE, TARGET, DOCS, dump
from .pipeline import PhysicalFeatures

def run():
    train, test, meta=split()
    frame=PhysicalFeatures().transform(train)
    frame[TARGET]=train[TARGET].to_numpy()
    dest=DOCS/'figuras';dest.mkdir(exist_ok=True)
    summary=pd.DataFrame({'dtype':train.dtypes.astype(str),'missing':train.isna().sum()})
    summary.to_csv(DOCS/'tipos_faltantes.csv')
    frame.describe(include='all').to_csv(DOCS/'descriptivos.csv')
    numerical=BASE[1:]+['temperature_delta_k','power_w']
    outliers=[]
    for col in numerical:
        x=frame[col];q1,q3=x.quantile([.25,.75]);iqr=q3-q1
        z=(x-x.mean())/x.std(ddof=0)
        outliers.append({'feature':col,'iqr_outliers':int(((x<q1-1.5*iqr)|(x>q3+1.5*iqr)).sum()),
                         'abs_z_ge_3':int((z.abs()>=3).sum()),'iqr_low':q1-1.5*iqr,'iqr_high':q3+1.5*iqr})
    pd.DataFrame(outliers).to_csv(DOCS/'atipicos.csv',index=False)
    corr=frame[numerical+[TARGET]].corr(method='spearman')
    corr.to_csv(DOCS/'spearman.csv')
    fig,ax=plt.subplots(figsize=(8,6));im=ax.imshow(corr,cmap='coolwarm',vmin=-1,vmax=1)
    ax.set_xticks(range(len(corr)),corr.columns,rotation=70,ha='right',fontsize=7)
    ax.set_yticks(range(len(corr)),corr.columns,fontsize=7);fig.colorbar(im,ax=ax)
    fig.tight_layout();fig.savefig(dest/'correlacion.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(2,4,figsize=(12,5))
    for ax,col in zip(axes.flat,numerical):ax.boxplot(frame[col].dropna());ax.set_title(col,fontsize=8)
    axes.flat[-1].axis('off');fig.tight_layout();fig.savefig(dest/'boxplots.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(2,4,figsize=(12,5))
    for ax,col in zip(axes.flat,numerical):
        for label in [0,1]: ax.hist(frame.loc[frame[TARGET]==label,col],bins=25,alpha=.5,density=True,label=str(label))
        ax.set_title(col,fontsize=8)
    axes.flat[0].legend();axes.flat[-1].axis('off');fig.tight_layout();fig.savefig(dest/'distribuciones.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(5,3));train[TARGET].value_counts().sort_index().plot.bar(ax=ax)
    ax.set_ylabel('Lecturas en entrenamiento');ax.set_title('Target');fig.tight_layout();fig.savefig(dest/'target.png',dpi=150);plt.close(fig)
    result={'scope':'train_only','train_rows':len(train),'holdout_rows':len(test),'positives_train':int(train[TARGET].sum()),
            'prevalence_train':float(train[TARGET].mean()),'source_scope':meta['scope'],
            'feature_target_spearman':corr[TARGET].drop(TARGET).to_dict(),
            'findings':[
                {'finding':'Desbalance','evidence':f'{train[TARGET].mean():.2%} fallas en train',
                 'consequence':'AP como métrica principal; CV estratificada; accuracy no decide.'},
                {'finding':'Colas físicas','evidence':outliers,
                 'consequence':'Conservar extremos; comparar modelos no lineales; no recortar globalmente.'},
                {'finding':'Variables físicas acopladas','evidence':{'temp_delta_spearman':float(corr.loc['temperature_delta_k',TARGET]),'power_spearman':float(corr.loc['power_w',TARGET])},
                 'consequence':'Derivar diferencia térmica y potencia en el pipeline, y comprobar aporte mediante ablation en CV.'}]
            }
    dump(DOCS/'eda.json',result)
    return result
