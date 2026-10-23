%%
%
%ARMA-GARCH models

% Data
clear
clc
load data_book_DJI.mat

%%
data = DJI_price;
logret = log(data(2:(length(data)))./data(1:(length(data)-1)));
y = logret;
%%

%Approximate the AR(1) model parameters
Model = arima('ARLags',1);
EstModel = estimate(Model,y)
%%
%Approximate the MA(1) model parameters
Model = arima('MALags',1);
EstModel = estimate(Model,y)
%%
%Approximate the ARMA(1,1) model parameters
Model = arima('ARLags',1,'MALags',1);
EstModel = estimate(Model,y)
%%
%Approximate the GARCH(1,1) model parameters
Model = arima('Variance',garch(1,1));
EstModel = estimate(Model,y)
