#


#
import numpy
import pandas

from matplotlib import pyplot

from sklearn.metrics import r2_score, mean_squared_error

import torch
from torch import nn


#
from neuro_kernel import Skeleton


def log_verse(x, x_lag, eps=1e-11):
    return numpy.log((x + eps) / (x_lag + eps))


def log_inverse(x, x_lag, eps=1e-11):
    return numpy.multiply((numpy.exp(x) - eps), (x_lag - eps))


#
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print('Using device:', device)

dt = './data/DailyDelhiClimateTrain.csv'
ds = './data/DailyDelhiClimateTest.csv'

data_train = pandas.read_csv(dt)
data_test = pandas.read_csv(ds)
data_train = data_train.set_index('date')
data_test = data_test.set_index('date')

thresh = data_train.shape[0]

data = pandas.concat((data_train, data_test), axis=0)

data[[x + '_LAG1' for x in data.columns.values]] = data.shift(periods=1)
data = data.dropna()

data_log = data.copy()
for col in [x for x in data.columns.values if 'LAG' not in x]:
    data_log[col] = log_verse(data[col].values, data[col + '_LAG1'].values)
data_log[[x for x in data_log.columns.values if 'LAG' in x]] = data_log[[x for x in data_log.columns.values if 'LAG' not in x]].shift(periods=1)
data_log = data_log.dropna()

data_train = data.iloc[:thresh, :]
data_test = data.iloc[thresh:, :]

target = 'meantemp'
factors = [x for x in data_train.columns.values if 'LAG' in x]


x_train = data_train[factors].values
y_train = data_train[[target]].values
x_val = data_test[factors].values
y_val = data_test[[target]].values

# activators = [nn.ELU, nn.ELU]
# activators = [nn.LeakyReLU, nn.LeakyReLU]
# activators = [nn.PReLU, nn.PReLU]
# activators = [nn.RReLU, nn.RReLU]
# activators = [nn.SELU, nn.SELU]
# activators = [nn.CELU, nn.CELU]
# activators = [nn.GELU, nn.GELU]
# activators = [nn.SiLU, nn.SiLU]

"""
layers = [nn.Linear] * 2
layers_dimensions = [2, 1]
layers_kwargs = [{}] * 2
activators = [nn.ReLU] * 2
drops = [0.00, 0.00]
verbose = 100
"""

layers = [nn.RNN, nn.Linear]
layers_dimensions = [10, 1]
layers_kwargs = [{'nonlinearity': 'relu'}, {}]
activators = [None, nn.ReLU]
drops = [0.0, 0.0]
verbose = 100

"""
layers = [nn.GRU, nn.Linear]
layers_dimensions = [12, 1]
layers_kwargs = [{}, {}]
activators = [None, nn.ReLU]
drops = [0.05, 0.0]
verbose = 100
"""
"""
layers = [nn.LSTM, nn.Linear]
layers_dimensions = [100, 1]
layers_kwargs = [{}, {}]
activators = [None, nn.ReLU]
drops = [0.2, 0.0]
verbose = 100
"""
"""
layers = [nn.LSTM, nn.LSTM, nn.LSTM, nn.LSTM, nn.Linear]
layers_dimensions = [100, 100, 100, 50, 1]
layers_kwargs = [{}, {}, {}, {}, {}]
activators = [None, None, None, None, nn.ReLU]
drops = [0.4, 0.4, 0.4, 0.4, 0.0]
verbose = 100
"""
model = Skeleton(layers, layers_dimensions, layers_kwargs, activators, drops, verbose, device=device)

optimizer = torch.optim.Adam
optimizer_kwargs = {'lr': 0.001}
loss_function = nn.MSELoss()

torch.tensor(x_train, dtype=torch.float)

window = 10

xx_train = []
xx_val = []
yy_train = []
yy_val = []
for j in range(x_train.shape[0] - window):
    xx_train.append(x_train[-j - window - 1:-j - 1, :].reshape(1, window, x_train.shape[1]))
    yy_train.append(y_train[-j - window - 1:-j - 1].reshape(1, window, 1))
for j in range(x_val.shape[0] - window):
    xx_val.append(x_val[-j - window - 1:-j - 1, :].reshape(1, window, x_val.shape[1]))
    yy_val.append(y_val[-j - window - 1:-j - 1].reshape(1, window, 1))
xx_train = numpy.concatenate(xx_train, axis=0)
xx_val = numpy.concatenate(xx_val, axis=0)
yy_train = numpy.concatenate(yy_train, axis=0)
yy_val = numpy.concatenate(yy_val, axis=0)
xx_train = torch.tensor(xx_train, dtype=torch.float, device=device)
xx_val = torch.tensor(xx_val, dtype=torch.float, device=device)
yy_train = torch.tensor(yy_train, dtype=torch.float, device=device)
yy_val = torch.tensor(yy_val, dtype=torch.float, device=device)

# yy_train[:20, -1, :]

model.fit(xx_train, yy_train, xx_val, yy_val, optimizer, optimizer_kwargs, loss_function, epochs=10000)

yy_train_hat = model.predict(x=xx_train)
yy_val_hat = model.predict(x=xx_val)

if device.type == 'cuda':
    yy_train = yy_train.cpu()
    yy_val = yy_val.cpu()
r2_train = r2_score(y_true=yy_train.numpy()[:, -1, :], y_pred=yy_train_hat.numpy()[:, -1, :])
r2_val = r2_score(y_true=yy_val.numpy()[:, -1, :], y_pred=yy_val_hat.numpy()[:, -1, :])
rmse_train = mean_squared_error(y_true=yy_train.numpy()[:, -1, :], y_pred=yy_train_hat.numpy()[:, -1, :])
rmse_val = mean_squared_error(y_true=yy_val.numpy()[:, -1, :], y_pred=yy_val_hat.numpy()[:, -1, :])

a = pandas.DataFrame(data={'tt': numpy.arange(start=0, stop=yy_train.shape[0]), 'value': yy_train.numpy()[:, -1, :].flatten(), 'kind': ['true'] * yy_train.shape[0], 'fold': ['train'] * yy_train.shape[0]})
b = pandas.DataFrame(data={'tt': numpy.arange(start=yy_train.shape[0], stop=yy_train.shape[0]+yy_val.shape[0]), 'value': yy_val.numpy()[:, -1, :].flatten(), 'kind': ['true'] * yy_val.shape[0], 'fold': ['val'] * yy_val.shape[0]})
c = pandas.DataFrame(data={'tt': numpy.arange(start=0, stop=yy_train_hat.shape[0]), 'value': yy_train_hat.numpy()[:, -1, :].flatten(), 'kind': ['hat'] * yy_train_hat.shape[0], 'fold': ['train'] * yy_train_hat.shape[0]})
d = pandas.DataFrame(data={'tt': numpy.arange(start=yy_train_hat.shape[0], stop=yy_train_hat.shape[0]+yy_val_hat.shape[0]), 'value': yy_val_hat.numpy()[:, -1, :].flatten(), 'kind': ['hat'] * yy_val_hat.shape[0], 'fold': ['val'] * yy_val_hat.shape[0]})
result = pandas.concat((a, b, c, d), axis=0, ignore_index=True)

# pyplot.plot(a['tt'].values, a['value'].values, 'black')
# pyplot.plot(b['tt'].values, b['value'].values, 'gray')
# pyplot.plot(c['tt'].values, c['value'].values, 'navy')
# pyplot.plot(d['tt'].values, d['value'].values, 'orange')

# pyplot.plot(a['tt'].values, (a['value'] - c['value']).values, 'black')
# pyplot.plot(b['tt'].values, (b['value'] - d['value']).values, 'navy')

# model.plot()

# RESULTS

# currently the best result for 'meantemp':
# RNNxLinear [10, 1], no drops

# window = 10

# layers = [nn.RNN, nn.Linear]
# layers_dimensions = [10, 1]
# layers_kwargs = [{'nonlinearity': 'relu'}, {}]
# activators = [None, nn.LeakyReLU]
# drops = [0.0, 0.0]
# verbose = 100

# train :: r2   :: 0.9526094936288734
# val   :: r2   :: 0.9377260126640103
# train :: rmse :: 2.4741302
# val   :: rmse :: 2.4960816

