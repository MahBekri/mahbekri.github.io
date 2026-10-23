%Exercise_Joint Distribution.m
%Read data

clear
clc
load data_book_1.mat

%
INTC_price = flipud(INTC_price);
INTC_logret = price2ret(INTC_price);
IBM_price = flipud(IBM_price);
IBM_logret = price2ret(IBM_price);
logret = [INTC_logret, IBM_logret];
price = [INTC_price, IBM_price];

%Calculate Covariance between INTC logreturn and IBM
mu = mean(logret);
Sig = cov(logret);

%Plot bivariate normal
[X1,X2] = meshgrid(linspace(-0.1,0.1,25)',linspace(-0.1,0.1,25)');
X = [X1(:) X2(:)];
p_logret = mvnpdf(X,mu,Sig);
subplot(221),surf(X1,X2,reshape(p_logret,25,25));
subplot(222),contour(X1,X2,reshape(p_logret,25,25));

%Normalized logreturns and calculate covariance
m = repmat(mean(logret),length(logret),1);
sd = repmat(std(logret),length(logret),1);
n_logret = (logret-m)./sd;
n_mu = mean(n_logret);
n_sig = cov(n_logret);

%Plot bivariate normal
[n_X1,n_X2] = meshgrid(linspace(-4,4,25)',linspace(-4,4,25)');
n_X = [n_X1(:) n_X2(:)];
N__pdf =mvnpdf(n_X, n_mu, n_sig);
subplot(223), surf(n_X1,n_X2,reshape(N__pdf,25,25));
subplot(224), contour(n_X1,n_X2,reshape(N__pdf,25,25));

%Relative portion of the portfolio
w = [1/3;2/3];
Var_P = w'*Sig*w
Std_P = sqrt(Var_P)
%Calculate correlations between two logreturn series
Corr_Logret = corr(logret)

%Calculate correlations between two price series
Corr_Price = corr(price)
