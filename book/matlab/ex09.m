%exercice_AVaR
%
clear;
close all;
clc;
rng(0);

%Read portfolio Return data
load data_book_portfolio_1

%Select assets into portfolio
StockTicker = {'INTC','IBM','AAPL','MSFT','MMM'};
numofStock = length(StockTicker);

%Stocks
for i=1:numofStock
    stockReturn(:,i) = data(2:(length(data)),i)./data(1:(length(data)-1),i);
end

%Calculate VaR and AVaR for each asset for beta = 0.90 till beta = 0.99
beta = 0.90:0.01:0.99;
valueAtRisk = zeros(length(beta),numofStock);
averageValueAtRisk = zeros(length(beta),numofStock);
normalAverageValueAtRisk = zeros(length(beta),numofStock);
normalValueAtRisk = zeros(length(beta),numofStock);

for j=1:length(beta)
    for i=1:numofStock
        [vp,vm]=empVaR(beta(j),-stockReturn(:,i));
        valueAtRisk(j,i)=vp;
        averageValueAtRisk(j,i)=empAVaR(beta(j),-stockReturn(:,i));
        [normalAverageValueAtRisk(j,i),normalValueAtRisk(j,i)]...
            =normalAVaR(beta(j),-stockReturn(:,i));
    end
end

%Calculate the empirical portfolio VaR and AVaR for beta = 0.90 till beta = 0.99

%Calculate the normal portfolio VaR and AVaR for beta = 0.90 till beta = 0.99

w = [0.2,0.2,0.2,0.2,0.2];

%Portfolio return
portReturn = stockReturn*w.';

%Portfolio VaR
portValueAtRisk = zeros(length(beta),1);
portAverageValueAtRisk = zeros(length(beta),1);
portNormalAverageValueAtRisk = zeros(length(beta),1);
portNormalValueAtRisk = zeros(length(beta),1);

for j=1:length(beta)
    [vp,vm]=empVaR(beta(j),-portReturn);
    portValueAtRisk(j)=vp;
    portAverageValueAtRisk(j)=empAVaR(beta(j),-portReturn);
    [portNormalAverageValueAtRisk(j),portNormalValueAtRisk(j)]...
        =normalAVaR(beta(j),-portReturn);
end

%Show the results in row
valueAtRisk
averageValueAtRisk
normalValueAtRisk
normalAverageValueAtRisk

portValueAtRisk
portAverageValueAtRisk
portNormalValueAtRisk
portNormalAverageValueAtRisk

function [vm,vp]=empVaR(eps,lossdata)
    %Input parameters:
    % eps: Confidence level. For example 0.95 or 0.99.
    % lossdata: vector valued (Nx1 or 1xN) loss time series of a portfolio
    %Outpur Parameters
    % vm = VaR_e^+(L) = sup{x: P(L<=x)<=e}
    % vm = VaR_e^-(L) = inf{x: P(L<=x)>=e}
    % where L is a random variable for the loss and e is confidence level.
    %
    n = length(lossdata);
    sortlossdata = sort(lossdata);
    cce = ceil(n*eps);
    vm=sortlossdata(cce-1);
    vp=sortlossdata(cce);
end


%%
function [averageValueAtRisk,valueAtRisk]=normalAVaR(eps,lossdata)
    %Input parameters:
    % eps: Confidence level. For example 0.95 or 0.99.
    % lossdata: vector valued (Nx1 or 1xN) loss time series of a portfolio
    %Outpur Parameters
    % v : Average Value At Risk with the assumption "Loss is normaly
    % distributed" i.e. L~N(m,V) where L is a random variable of loss.
    %
    mu = mean(lossdata);
    sigma = std(lossdata);
    valueAtRisk=icdf('normal',eps,mu,sigma);
    averageValueAtRisk=sigma*exp(-(valueAtRisk-mu)^2/(2*sigma^2) )/((1-eps)*sqrt(2*pi))+mu;
end
