import numpy as np
from sklearn.metrics import average_precision_score, confusion_matrix, precision_score, recall_score, f1_score, roc_auc_score

CP, CE, CR = 500., 8000., 1500.
def evaluate(y, prob, threshold=.5):
    y=np.asarray(y); pred=np.asarray(prob)>=threshold
    tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    cost=(tp+fp)*CP+fn*CE+tp*CR
    return {'ap':float(average_precision_score(y,prob)), 'roc_auc':float(roc_auc_score(y,prob)),
            'recall':float(recall_score(y,pred,zero_division=0)),
            'precision':float(precision_score(y,pred,zero_division=0)),
            'f1':float(f1_score(y,pred,zero_division=0)), 'cost_per_1000':float(cost/len(y)*1000),
            'alert_rate':float(pred.mean()), 'tp':int(tp),'fp':int(fp),'fn':int(fn),'tn':int(tn)}

def choose_threshold(y,prob,capacity=.12):
    # Solo probabilidades out of fold de entrenamiento. No usa el holdout.
    thresholds=np.unique(np.r_[np.linspace(0,1,201),prob,1.000001])
    options=[]
    for t in thresholds:
        pred=prob>=t
        if pred.mean() <= capacity:
            tp=((y==1)&pred).sum(); fp=((y==0)&pred).sum(); fn=((y==1)&~pred).sum()
            options.append(((tp+fp)*CP+fn*CE+tp*CR,float(t)))
    return min(options)[1]
