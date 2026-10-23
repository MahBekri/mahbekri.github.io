%Exercise_VaR_Backtesting
clear;
close all;
clc;
rng(0);

%Read Data
load data_book_DJI_crisis
Returns = tick2ret(DJI_price);
DateReturns = dates(2:end);
SampleSize = length(Returns);

%Set the estimation window as 250 trading days.
TestWindowStart     = find(year(DateReturns)==2011,1);
TestWindow         = TestWindowStart : SampleSize;
EstimationWindowSize = 250;

%For a VaR confidence level of 95% and 99%, set the complement of the VaR level.
pVaR = [0.05 0.01];

%Assuming that the portfolio return is normally distributed:
%Estimate VaR by multiplying the z-score, by the standard deviation of the returns.
Zscore = norminv(pVaR);
Normal95 = zeros(length(TestWindow),1);
Normal99 = zeros(length(TestWindow),1);

for t = TestWindow
    i = t - TestWindowStart + 1;
    EstimationWindow = t-EstimationWindowSize:t-1;
    Sigma = std(Returns(EstimationWindow));
    Normal95(i) = -Zscore(1)*Sigma;
    Normal99(i) = -Zscore(2)*Sigma;
end

figure;
plot(DateReturns(TestWindow),[Normal95 Normal99])
xlabel('Date')
ylabel('VaR')
legend({'95% Confidence Level','99% Confidence Level'},'Location','Best')
title('VaR Estimation Using the Gaussian Distribution')

%Estimate VaR Using the Historical Simulation(HS) Method
Historical95 = zeros(length(TestWindow),1);
Historical99 = zeros(length(TestWindow),1);

for t = TestWindow
    i = t - TestWindowStart + 1;
    EstimationWindow = t-EstimationWindowSize:t-1;
    X = Returns(EstimationWindow);
    Historical95(i) = -quantile(X,pVaR(1));
    Historical99(i) = -quantile(X,pVaR(2));
end

figure;
plot(DateReturns(TestWindow),[Historical95 Historical99])
ylabel('VaR')
xlabel('Date')
legend({'95% Confidence Level','99% Confidence Level'},'Location','Best')
title('VaR Estimation Using the Historical Simulation Method')

%Using the decay factor of 0.94, initiate the EWMA model
Lambda = 0.94;
Sigma2 = zeros(length(Returns),1);
Sigma2(1) = Returns(1)^2;

for i = 2 : (TestWindowStart-1)
    Sigma2(i) = (1-Lambda) * Returns(i-1)^2 + Lambda * Sigma2(i-1);
end

%Use the EWMA in the test window to estimate the VaR
Zscore = norminv(pVaR);
EWMA95 = zeros(length(TestWindow),1);
EWMA99 = zeros(length(TestWindow),1);

for t = TestWindow
    k = t - TestWindowStart + 1;
    Sigma2(t) = (1-Lambda) * Returns(t-1)^2 + Lambda * Sigma2(t-1);
    Sigma = sqrt(Sigma2(t));
    EWMA95(k) = -Zscore(1)*Sigma;
    EWMA99(k) = -Zscore(2)*Sigma;
end

figure;
plot(DateReturns(TestWindow),[EWMA95 EWMA99])
ylabel('VaR')
xlabel('Date')
legend({'95% Confidence Level','99% Confidence Level'},'Location','Best')
title('VaR Estimation Using the EWMA Method')

%VaR Backtesting
%Plot all VaR estimates at the 95% confidence level and compare them to the returns
ReturnsTest = Returns(TestWindow);
DatesTest = DateReturns(TestWindow);
figure;
plot(DatesTest,[ReturnsTest -Normal95 -Historical95 -EWMA95])
ylabel('VaR')
xlabel('Date')
legend({'Returns','Normal','Historical','EWMA'},'Location','Best')
title('Comparison of returns and VaR at 95% for different models')
% Zoom in on the time series during the third quarter of 2011, that witnessed
% a large and sudden change in the value of returns.
ZoomInd = (DatesTest >= '03-Jul-2011') & (DatesTest <= '30-Sep-2011');
VaRData = [-Normal95(ZoomInd) -Historical95(ZoomInd) -EWMA95(ZoomInd)];
VaRFormat = {'-','--','-.'};
D = DatesTest(ZoomInd);
R = ReturnsTest(ZoomInd);
N = Normal95(ZoomInd);
H = Historical95(ZoomInd);
E = EWMA95(ZoomInd);
IndN95 = (R < -N);
IndHS95 = (R < -H);
IndEWMA95 = (R < -E);
figure;
bar(D,R,0.5,'FaceColor',[0.7 0.7 0.7]);
hold on
for i = 1 : size(VaRData,2)
    stairs(D-0.5,VaRData(:,i),VaRFormat{i});
end
ylabel('VaR')
xlabel('Date')
legend({'Returns','Normal','Historical','EWMA'},'Location','Best','AutoUpdate','Off')
title('95% VaR violations for different models')
ax = gca;
ax.ColorOrderIndex = 1;

plot(D(IndN95),-N(IndN95),'o',D(IndHS95),-H(IndHS95),'o',...
    D(IndEWMA95),-E(IndEWMA95),'o','MarkerSize',8,'LineWidth',1.5)
xlim([D(1)-1, D(end)+1])
hold off;

%Using the varbacktest object, compare the different test results
%for the Gaussian distribution at the 95% and 99% VaR levels.
vbt = varbacktest(ReturnsTest,[Normal95 Normal99],'PortfolioID','DJI','VaRID',...
    {'Normal95','Normal99'},'VaRLevel',[0.95 0.99]);

summary(vbt)
runtests(vbt)

%Using the varbacktest object, run the same tests on the portfolio,
%for the three approaches at both VaR confidence levels.
vbt = varbacktest(ReturnsTest,[Normal95 Historical95 EWMA95 Normal99 Historical99 ...
    EWMA99],'PortfolioID','DJI','VaRID',{'Normal95','Historical95','EWMA95',...
    'Normal99','Historical99','EWMA99'},'VaRLevel',[0.95 0.95 0.95 0.99 0.99 0.99]);
runtests(vbt)

% Visualize the results for 2015 and 2017 for the 95% VaR confidence level.
Ind2015 = (year(DatesTest) == 2015);
vbt2015 = varbacktest(ReturnsTest(Ind2015),[Normal95(Ind2015) Historical95(Ind2015) EWMA95(Ind2015)],...
    'PortfolioID','DJI, 2015','VaRID',{'Normal','Historical','EWMA'});
runtests(vbt2015)

Ind2017 = (year(DatesTest) == 2017);
vbt2017 = varbacktest(ReturnsTest(Ind2017),[Normal95(Ind2017) Historical95(Ind2017) EWMA95(Ind2017)],...
    'PortfolioID','DJI, 2017','VaRID',{'Normal','Historical','EWMA'});
runtests(vbt2017)

%Show the test details of the conditional coverage independence(cci)
cci(vbt2017)

%Show the details of the time between failures independence test(tbfi)
tbfi(vbt2017)
