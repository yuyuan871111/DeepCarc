#!/account/tli/anaconda3/bin/python

import time
start_time = time.time()


###Loading packages
import os
import numpy as np
import pandas as pd
import math
import itertools
from sklearn.model_selection import train_test_split
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.utils import class_weight
from sklearn import metrics
from sklearn.metrics import confusion_matrix, f1_score, roc_curve

from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from xgboost import XGBClassifier


from sklearn.metrics import roc_auc_score
import warnings
warnings.filterwarnings('ignore')
from numpy.random import seed
seed(1)


import itertools


def measurements(y_test, y_pred, y_pred_prob):  
    acc = metrics.accuracy_score(y_test, y_pred)
    sensitivity = metrics.recall_score(y_test, y_pred)
    TN, FP, FN, TP = confusion_matrix(y_test, y_pred).ravel()
    specificity = TN/(TN+FP)
    precision = metrics.precision_score(y_test, y_pred)
    f1 = metrics.f1_score(y_test, y_pred)
    mcc = metrics.matthews_corrcoef(y_test, y_pred)
    auc = roc_auc_score(y_test, y_pred_prob)
    npv = TN/(TN+FN)       
    return [TN, FP, FN, TP, acc, auc, sensitivity, specificity, precision, npv, f1, mcc]

def model_predict(X, y, model, col_name):
    y_pred_prob = model.predict_proba(X)
    # keep probabilities for the positive outcome only
    y_pred_prob = y_pred_prob[:, 1]
    y_pred_class = np.where(y_pred_prob > 0.5, 1, 0)

    ###create dataframe
    pred_result = pd.DataFrame()
    pred_result['id'] = y.index
    pred_result['y_true'] = y.values
    pred_result['prob_'+col_name] = y_pred_prob
    pred_result['class_'+col_name] = y_pred_class
    
    performance =measurements(y, y_pred_class, y_pred_prob)

    return pred_result, performance


lr = [0.0001, 0.001, 0.01]
n_estimators = [100, 300, 500, 700]
max_depth = [7, 9, 11]
subsample = [0.7, 0.8, 1]
scale_pos_weight=[0.65]

var = '105'

paras = [l for l in itertools.product(lr, n_estimators, max_depth, subsample, scale_pos_weight)]
print(len(paras))
para = paras[int(var)]
print(para)

tmp = pd.read_csv('/account/tli/carcinogenecity/data/mol2vec/carcinogenecity_mol2vec_297.csv',low_memory=False)
cols = tmp.columns[10:]
data = tmp[['CID', 'usage', 'label', *cols]]
print(data.shape)


X,  y = data[data.usage == 'training'].iloc[:,3:], data[data.usage == 'training']['label']
X_val,  y_val = data[data.usage == 'validation'].iloc[:,3:], data[data.usage == 'validation']['label']
X_test, y_test = data[data.usage == 'test'].iloc[:,3:], data[data.usage == 'test']['label']

print(X.shape)
print(X_val.shape)
print(X_test.shape)



base_path = '/account/tli/carcinogenecity/results/mol2vec/para_selection/xgboost'

path10 = base_path + '/training_performance'
path20 = base_path + '/validation_performance'
path30 = base_path + '/test_performance'

path1 = base_path + '/training_class'
path2 = base_path + '/validation_class'
path3 = base_path + '/test_class'

###make the directory
os.mkdir(base_path)
os.mkdir(path10)
os.mkdir(path20)
os.mkdir(path30)

os.mkdir(path1)
os.mkdir(path2)
os.mkdir(path3)


#initial performance dictionary
train_results={}
validation_results={}
test_results={}

pred_val_df = pd.DataFrame()
pred_test_df = pd.DataFrame()

for i in range(200):
    #pred_df = pd.DataFrame()
    skf = StratifiedKFold(n_splits=5, random_state=i, shuffle=True)
    j = 0
    for train_index, validation_index in skf.split(X, y):
        ###get train, validation dataset
        X_train, X_validation = X.iloc[train_index,:], X.iloc[validation_index,:]
        y_train, y_validation = y.iloc[train_index], y.iloc[validation_index]
        
        ### scale the input
        sc = MinMaxScaler()
        sc.fit(X_train)
        X_train = sc.transform(X_train)
        X_validation = sc.transform(X_validation)
        X_val_s = sc.transform(X_val)
        X_test_s = sc.transform(X_test)
        
        ### define column name
        col_name = 'xgboost_'+'seed_'+str(i)+'_skf_'+str(j)+'_paras_'+var+'_lr_'+str(para[0])+'_n_'+str(para[1])+'_depth_'+str(para[2])+'_subsample_'+str(para[3])+'_scale_pos_weight_'+str(para[4])
        col_name2 = 'xgboost_'+'paras_'+var
        
        ###create classifier
        #class_weight = {0:int(var1),1:(100-int(var1))}
        clf = XGBClassifier(learning_rate=para[0], n_estimators=para[1], max_depth=para[2], subsample=para[3], scale_pos_weight=para[4])
        clf.fit(X_train, y_train)
        
        ### predict validation results
        train_class, train_result=model_predict(X_validation, y_validation, clf, col_name)
        train_results[col_name]=train_result
        
        ### predict validation results
        validation_class, validation_result=model_predict(X_val_s, y_val, clf, col_name)
        validation_results[col_name]=validation_result

        ### predict test results
        test_class, test_result=model_predict(X_test_s, y_test, clf, col_name)
        test_results[col_name]=test_result
        
        pred_val_df = pd.concat([pred_val_df, validation_class], axis=1, sort=False)
        pred_test_df = pd.concat([pred_test_df, test_class],axis=1, sort=False)
        j += 1
        train_class.to_csv(path1+'/train_'+col_name+'.csv')     
        
###save the result of validation results
pd.DataFrame(data=train_results.items()).to_csv(path10+'/train_'+col_name2+'.csv')
pred_val_df.to_csv(path2+'/validation_'+col_name2+'.csv')
pd.DataFrame(data=validation_results.items()).to_csv(path20+'/validation_'+col_name2+'.csv')
pred_test_df.to_csv(path3+'/test_'+col_name2+'.csv')
pd.DataFrame(data=test_results.items()).to_csv(path30+'/test_'+col_name2+'.csv')

print("--- %s seconds ---" % (time.time() - start_time))    