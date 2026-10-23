%Alpha-VaR

clear
clc
load data_book_DJI.mat
data = DJI_price;

%%
logret = log(data(2:(length(data)))./data(1:(length(data)-1)));
sortedlogret = sort(logret);

xmin = min(logret);
xmax = max(logret);
dx = (xmax-xmin)/100;
xdata = xmin:dx:xmax;
ydata = hist( logret, xdata );
ydata = ydata./length(logret);

m = mean(logret);
sig_nor = sqrt(var(logret));
s = skewness(logret);
k = kurtosis(logret);

pdfNormal = exp(-(xdata-m).^2/(2*sig_nor^2))/sqrt(2*pi*sig_nor);

x = (logret-m)./sig_nor;
[H_ks_nor,kspvalue_nor,ksstat_nor,cv_ks_nor] = kstest(x);

pdStable = fitdist(logret,'stable');
pdfStable = pdf(pdStable, xdata);

x = -5:.1:5;

cdfStable = cdf(pdStable,sortedlogret);
[h_stable,p_stable,ksstat_stable,cv_stable]= kstest(logret,[sortedlogret,cdfStable]);

norVaR95 = -icdf('normal',0.05,m,sig_nor);
norVaR99 = -icdf('normal',0.01,m,sig_nor);
stableVaR95 = -icdf('stable',0.05,pdStable.alpha,pdStable.beta,pdStable.gam,pdStable.delta);
stableVaR99 = -icdf('stable',0.01,pdStable.alpha,pdStable.beta,pdStable.gam,pdStable.delta);

empVaR95 = -sortedlogret(floor(0.05*length(logret)));
empVaR99 = -sortedlogret(floor(0.01*length(logret)));

subplot(2,2,1), plot(xdata,ydata,'o', xdata, pdfNormal/sum(pdfNormal),'-');
subplot(2,2,2), qqplot(sortedlogret,norminv(sortedlogret,m,sig_nor));
subplot(2,2,3), plot(xdata,ydata,'o', xdata, pdfStable/sum(pdfStable),'-');
subplot(2,2,4), qqplot(sortedlogret,icdf(pdStable,sortedlogret));
