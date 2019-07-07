import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor


def get_machine_learning(regressor_func, X, y, n_estimators=100, max_features=None):
    """
    Get machine learning predictions and the mean square error with sklearn
    :param regressor_func: Regressor from sklearn.ensemble
    :param X: independent data
    :type X: numpy.array
    :param y: dependent data
    :type y: list
    :param n_estimators:
    :type n_estimators: int
    :param max_features:
    :type max_features: int
    :return: predicted values, mean square error
    :rtype: tuple
    """
    if max_features is None:
        max_features = len(X[0, :])
    regressor = regressor_func(n_estimators=n_estimators, max_features=max_features)
    regressor.fit(X, y)
    y_pred = regressor.predict(X)

    mse = np.mean(np.square(np.subtract(y_pred, y)))

    return y_pred, mse, regressor.feature_importances_


def get_random_forest(X, y, n_estimators=100, max_features=None):
    return get_machine_learning(RandomForestRegressor, X, y, n_estimators, max_features)


def get_gradient_boosting(X, y, n_estimators=100, max_features=None):
    return get_machine_learning(GradientBoostingRegressor, X, y, n_estimators, max_features)
