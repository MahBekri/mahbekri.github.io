%Goodness_of_Fit.m
% ‘data’ contain the closing price of the index

logret = price2ret(data);

% QQ-plot.
xmin = min(logret);
xmax = max(logret);
dx = (xmax-xmin)/200;
xdata = xmin:dx:xmax;
ydata = hist( logret, xdata );
ydata = ydata./length(logret);

% Empirical Mean, Variance, Skewness and Kurtosis
mu = mean(logret);
sig = sqrt(var(logret));
s = skewness(logret);
k = kurtosis(logret);

% Plotting pdf normal
pdfNorm = exp(-(xdata-mu).^2/(2*sig^2))/sqrt(2*pi*sig);
subplot(2,2,1),plot(data)
subplot(2,2,3),plot(logret)
subplot(2,2,2),plot(xdata,ydata, 'b.-', xdata, pdfNorm/sum(pdfNorm), 'k-')
sortedlogret = sort(logret);
x = (logret-mu)./sig;
subplot(2,2,4),qqplot(x)

% Estimate KS, AD and JB statistics
[H_ks,kspvalue,ks_stat,cv_ks] = kstest(x)
[H_ad,adpvalue,adstat,cv_ad] = adtest(x)
[H_jb,jbpvalue,jbstat,cv_jb] = jbtest(x)
