%Exercise_optim_CVaR
%
clear;
close all;
clc;
rng(0);

%Read portfolio Return data
load data_book_portfolio

for i= 1:6
    Return(:,i) = data(2:(length(data)),i)./data(1:(length(data)-1),i);
end

%Select assets into portfolio
symbol = {'INTC','IBM','AAPL','MSFT','MMM','CSCO'};
nAsset = numel(symbol);
Return = Return(:,1:6);

%Simulate asset scenarios
nScen = 5000;

%simulationMethod

% case based on empirical distribution using t-copula
AssetScen = simEmpirical(Return,nScen);

%Histogram of asset scenarios
plotAssetHist(symbol,AssetScen);

%CVaR Portfolio Optimization
%Construct a fully invested long only portfolio using PortfolioCVaR object
p1 = PortfolioCVaR('Scenarios', AssetScen);
p1 = setDefaultConstraints(p1);
p1 = setProbabilityLevel(p1, 0.95);

%Plot efficient frontier and calculate portfolio weights
figure;
w1 = estimateFrontier(p1);
plotFrontier(p1,w1);
plotWeight(w1, symbol,'CVaR Portfolio');

%Visualize histogram of portfolio Returns
port = 6;
% Select port number above
plotCVaRHist(p1, w1, Return, port, 50)

%Construct the Mean Varaince Portfolio Optimization
p2 = Portfolio;
p2 = setAssetList(p2, symbol);
p2 = estimateAssetMoments(p2, Return);
p2 = setDefaultConstraints(p2);

%Plot efficient frontier and calculate portfolio weights
w2 = estimateFrontier(p2);
plotFrontier(p2,w2);
plotWeight(w2, symbol, 'Mean-Variance Portfolio ');

%estimate the CVaR and Return of portfolios
pReturn1 = estimatePortReturn(p1,w1);
pRisk1 = estimatePortRisk(p1,w1);
pReturn2 = estimatePortReturn(p1,w2);
pRisk2 = estimatePortRisk(p1,w2);

%Plot the Mean-CVaR efficient frontiers
figure
plot(pRisk1,pReturn1,'-r',pRisk2, pReturn2,'--b')
title('Efficient Frontiers (CVaR VS Mean-Variance)');
xlabel('CVaR of Portfolio');
ylabel('Mean of Portfolio Returns');
legend({'CVaR','Mean-Variance'},'Location','southeast')

%Compare the portfolio weights of both methods
plotWeight2(w1, w2, symbol)

%Function that simulate empirical asset scenarios
function AssetScen = simEmpirical(Return,nScen)

    %Transform the data to the copula scale (unit square) using a kernel estimateator of the CDF.
    [nSample,nAsset] = size(Return);
    u = zeros(nSample,nAsset);
    for i = 1:nAsset
        u(:,i) = ksdensity(Return(:,i),Return(:,i),'function','cdf');
    end

    %Fit a t copula to the data.
    [rho, dof] = copulafit('t',u);

    %Generate a random sample from the copula.
    r = copularnd('t',rho,dof,nScen);

    %Transform the random sample back to the original scale of the data.
    AssetScen = zeros(nScen,nAsset);
    for i = 1:nAsset
        AssetScen(:,i) = ksdensity(Return(:,i),r(:,i),'function','icdf');
    end
end

%Function that plot the histogram of the assets
function plotAssetHist(symbol,Return)
    figure
    nAsset = numel(symbol);
    plotCol = 3;
    plotRow = ceil(nAsset/plotCol);
    for i = 1:nAsset
        subplot(plotRow,plotCol,i);
        histogram(Return(:,i));
        title(symbol{i});
    end
end

%Function that plot CVaR histogram with the bins with value lower than VaR
function plotCVaRHist(p, w, Return, port, nBin)

    % portfolio Returns given port
    portReturn = Return*w(:,port);

    % Calculate VaR and CVaR of the portfolios.
    VaR = estimatePortVaR(p,w(:,port));
    CVaR = estimatePortRisk(p,w(:,port));

    % Convert positive number to negative number
    VaR = -VaR;
    CVaR = -CVaR;

    % Plot main histogram
    figure;
    h1 = histogram(portReturn,nBin);
    title('Histogram of Returns');
    xlabel('Returns')
    ylabel('Frequency')
    hold on;

    % Highlight bins with lower edges < VaR level in red
    edges = h1.BinEdges;
    counts = h1.Values.*(edges(1:end-1) < VaR);
    h2 = histogram('BinEdges',edges,'BinCounts',counts);
    h2.FaceColor = 'r';

    % Add CVaR line
    plot([CVaR;CVaR],[0;max(h1.BinCounts)*0.80],'--r')

    % Add CVaR text
    text(edges(1), max(h1.BinCounts)*0.85,['CVaR = ' num2str(round(-CVaR,4))])
    hold off;
end

%Function that plot portfolio weights

function plotWeight(w, symbol, title1)
    figure;
    w = round(w'*100,1);
    area(w);
    ylabel('Portfolio weights (%)')
    xlabel('Port')
    title(title1);
    ylim([0 100]);
    legend(symbol);
end

%Function that plot portfolio weight CVaR VS MV

function plotWeight2(w1, w2, symbol)
    figure;
    subplot(1,2,1)
    w1 = round(w1'*100,1);
    area(w1);
    ylabel('Portfolio weights (%)')
    xlabel('Port')
    title('CVaR');
    xlim([1 10])
    ylim([0 100]);
    legend(symbol);
    subplot(1,2,2)
    w2 = round(w2'*100,1);
    area(w2);
    ylabel('Portfolio weights (%)')
    xlabel('Port')
    title('Mean-Variance');
    xlim([1 10])
    ylim([0 100]);
    legend(symbol);
end
