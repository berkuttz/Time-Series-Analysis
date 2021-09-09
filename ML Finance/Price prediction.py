# Load libraries
import Snippets

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pandas import read_csv, set_option
from pandas.plotting import scatter_matrix
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, KFold, cross_val_score, GridSearchCV
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.naive_bayes import GaussianNB
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.ensemble import AdaBoostClassifier, GradientBoostingClassifier, RandomForestClassifier, ExtraTreesClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

#Libraries for Deep Learning Models
from keras.models import Sequential
from keras.layers import Dense
from keras.wrappers.scikit_learn import KerasClassifier
from tensorflow.keras.optimizers import SGD
from datetime import datetime, timedelta


# load dataset
dataset = pd.read_csv("C:\\Users\\Vlad\Desktop\\Finance\\ADA 15 min.csv")
# Create short simple moving average over the short window
dataset['short_mavg'] = dataset['Close'].rolling(window=145, min_periods=1, center=False).mean()

# Create long simple moving average over the long window
dataset['long_mavg'] = dataset['Close'].rolling(window=295, min_periods=1, center=False).mean()

# Create signals
dataset['positions'] = np.where(dataset['short_mavg'] > dataset['long_mavg'], 0.0, 1.0)

dataset.drop(['short_mavg', 'long_mavg', 'Close Time.1'], axis=1, inplace=True)

def add_indicators(dataset):

    #calculation of exponential moving average
    def EMA(df, n):
        EMA = pd.Series(df['Close'].ewm(span=n, min_periods=n).mean(), name='EMA_' + str(n))
        return EMA
    dataset['EMA10'] = EMA(dataset, 10)
    dataset['EMA30'] = EMA(dataset, 30)
    dataset['EMA200'] = EMA(dataset, 200)


    #calculation of rate of change
    def ROC(df, n):
        M = df.diff(n - 1)
        N = df.shift(n - 1)
        ROC = pd.Series(((M / N) * 100), name = 'ROC_' + str(n))
        return ROC

    dataset['ROC10'] = ROC(dataset['Close'], 10)
    dataset['ROC30'] = ROC(dataset['Close'], 30)

    #Calculation of price momentum
    def MOM(df, n):
        MOM = pd.Series(df.diff(n), name='Momentum_' + str(n))
        return MOM
    dataset['MOM10'] = MOM(dataset['Close'], 10)
    dataset['MOM30'] = MOM(dataset['Close'], 30)

    #calculation of relative strength index
    def RSI(series, period):
        delta = series.diff().dropna()
        u = delta * 0
        d = u.copy()
        u[delta > 0] = delta[delta > 0]
        d[delta < 0] = -delta[delta < 0]
        u[u.index[period-1]] = np.mean( u[:period] ) #first value is sum of avg gains
        u = u.drop(u.index[:(period-1)])
        d[d.index[period-1]] = np.mean( d[:period] ) #first value is sum of avg losses
        d = d.drop(d.index[:(period-1)])
        rs = u.ewm(com=period-1, adjust=False).mean() / \
        d.ewm(com=period-1, adjust=False).mean()
        return 100 - 100 / (1 + rs)
    dataset['RSI10'] = RSI(dataset['Close'], 10)
    dataset['RSI30'] = RSI(dataset['Close'], 30)
    dataset['RSI200'] = RSI(dataset['Close'], 200)

    #calculation of stochastic osillator.

    def STOK(close, low, high, n):
        STOK = ((close - low.rolling(n).min()) / (high.rolling(n).max() - low.rolling(n).min())) * 100
        return STOK

    def STOD(close, low, high, n):
        STOK = ((close - low.rolling(n).min()) / (high.rolling(n).max() - low.rolling(n).min())) * 100
        STOD = STOK.rolling(3).mean()
        return STOD

        # dataset['%K10'] = STOK(dataset['Close'], dataset['Low'], dataset['High'], 10)
        # dataset['%D10'] = STOD(dataset['Close'], dataset['Low'], dataset['High'], 10)
        # dataset['%K30'] = STOK(dataset['Close'], dataset['Low'], dataset['High'], 30)
        # dataset['%D30'] = STOD(dataset['Close'], dataset['Low'], dataset['High'], 30)
        # dataset['%K200'] = STOK(dataset['Close'], dataset['Low'], dataset['High'], 200)
        # dataset['%D200'] = STOD(dataset['Close'], dataset['Low'], dataset['High'], 200)

        #Calculation of moving average
    def MA(df, n):
        MA = pd.Series(df['Close'].rolling(n, min_periods=n).mean(), name='MA_' + str(n))
        return MA
    dataset['MA10'] = MA(dataset, 2)
    dataset['MA30'] = MA(dataset, 7)
    dataset['MA200'] = MA(dataset, 25)
    dataset['MA400'] = MA(dataset, 55)
    dataset['MA600'] = MA(dataset, 90)

    return dataset

dataset = add_indicators(dataset)

dataset = dataset.dropna(axis=0)
dataset = dataset.drop('Close Time', axis=1)

# split out validation dataset for the end
subset_dataset= dataset.iloc[-round(len(dataset)*0.2):]
subset_dataset.drop(['positions'], axis=1, inplace=True)

dataset = dataset.iloc[:round(len(dataset)*0.8)]

Y = dataset["positions"]
X = dataset.loc[:, dataset.columns != 'positions']
validation_size = 0.3
seed = 1
X_train, X_validation, Y_train, Y_validation = train_test_split(X, Y, test_size=validation_size, random_state=1)

def test_models():
    # test options for classification
    num_folds = 10
    seed = 7
    scoring = 'accuracy'
    #scoring = 'precision'
    #scoring = 'recall'
    #scoring ='neg_log_loss'
    #scoring = 'roc_auc'

    # spot check the algorithms
    models = []
    models.append(('LR', LogisticRegression(n_jobs=-1,  max_iter=4000)))
    models.append(('LDA', LinearDiscriminantAnalysis()))
    models.append(('KNN', KNeighborsClassifier()))
    models.append(('CART', DecisionTreeClassifier()))
    models.append(('NB', GaussianNB()))
    #Neural Network
    models.append(('NN', MLPClassifier()))
    #Ensable Models
    # Boosting methods
    models.append(('AB', AdaBoostClassifier()))
    models.append(('GBM', GradientBoostingClassifier()))
    # Bagging methods
    models.append(('RF', RandomForestClassifier(n_jobs=-1)))

    results = []
    names = []
    for name, model in models:
        kfold = KFold(n_splits=num_folds)
        cv_results = cross_val_score(model, X_train, Y_train, cv=kfold, scoring=scoring)
        results.append(cv_results)
        names.append(name)
        msg = "%s: %f (%f)" % (name, cv_results.mean(), cv_results.std())
        print(msg)

    # # compare algorithms
    fig = plt.figure()
    fig.suptitle('Algorithm Comparison')
    ax = fig.add_subplot(111)
    plt.boxplot(results)
    ax.set_xticklabels(names)
    fig.set_size_inches(15, 8)
    plt.show()

#test_models()
model = LogisticRegression(n_jobs=-1)
model.fit(X_train, Y_train)

predictions = model.predict(X_validation)
print(accuracy_score(Y_validation, predictions))
print(confusion_matrix(Y_validation, predictions))
print(classification_report(Y_validation, predictions))


predictions = model.predict(subset_dataset)
subset_dataset['predictions'] = predictions
subset_dataset['positions'] = subset_dataset['predictions'].diff()
print(100-Snippets.calculate_balance(subset_dataset))
# get those signals from DoubleAvarage. test the best strategy for the gigheest return
# Do not use .diff() .


fig = plt.figure()
fig.set_size_inches(22.5, 10.5)
ax1 = fig.add_subplot(111, ylabel='Google price in $')
subset_dataset["Close"].plot(ax=ax1, color='g', lw=.5)

ax1.plot(subset_dataset.loc[subset_dataset.positions == 1.0].index, subset_dataset["Close"][subset_dataset.positions == 1.0],
         '^', markersize=7, color='k')

ax1.plot(subset_dataset.loc[subset_dataset.positions == -1.0].index, subset_dataset["Close"][subset_dataset.positions == -1.0],
         'v', markersize=7, color='k')

plt.legend(["Price", "Buy", "Sell"])
plt.title("AI ADA pred")

plt.show()