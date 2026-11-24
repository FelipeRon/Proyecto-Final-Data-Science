"""Única preparación reutilizada en notebooks, CV e inferencia."""
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin, ClassifierMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from .datos import BASE

DERIVED = ['temperature_delta_k', 'power_w']

class PhysicalFeatures(TransformerMixin, BaseEstimator):
    def fit(self, X, y=None): return self
    def transform(self, X):
        # Lista blanca: se ignoran identificadores, auditoría, target y subtipos.
        out = X[BASE].copy()
        out['temperature_delta_k'] = out.process_temperature_k - out.air_temperature_k
        out['power_w'] = out.torque_nm * out.rotational_speed_rpm * 2*np.pi/60
        return out

def preparation(derived=True):
    numeric = BASE[1:] + (DERIVED if derived else [])
    return ColumnTransformer([
        ('numeric', Pipeline([('imputer', SimpleImputer(strategy='median')),
                              ('scale', StandardScaler())]), numeric),
        ('category', Pipeline([('imputer', SimpleImputer(strategy='most_frequent')),
                               ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))]), ['product_type'])
    ], remainder='drop')

def make_pipeline(model, derived=True):
    return Pipeline([('features',PhysicalFeatures()), ('prepare',preparation(derived)), ('model',model)])

class BusinessRule(ClassifierMixin, BaseEstimator):
    def fit(self, X, y=None):
        self.classes_ = np.array([0,1]); self.n_features_in_ = X.shape[1]; return self
    def predict(self, X):
        return ((X.tool_wear_min.to_numpy() >= 200) | (X.torque_nm.to_numpy() >= 60)).astype(int)
    def predict_proba(self, X):
        pred=self.predict(X).astype(float); return np.column_stack([1-pred,pred])

class DecisionModel(ClassifierMixin, BaseEstimator):
    """Empaqueta umbral congelado con todo el preprocesamiento."""
    def __init__(self, pipeline, threshold=.5): self.pipeline=pipeline; self.threshold=threshold
    def fit(self,X,y):
        self.pipeline.fit(X,y); self.classes_=self.pipeline.classes_; return self
    def predict_proba(self,X): return self.pipeline.predict_proba(X)
    def predict(self,X): return (self.predict_proba(X)[:,1] >= self.threshold).astype(int)
