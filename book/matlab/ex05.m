%Exercise Stable Probability Density Function

clear
clc

%Compare PDFs of Stable Distributions for different alpha values.
%In each case, beta = 0.5, gam = 0.8, and delta = 0.2.
pd1 = makedist('Stable','alpha',1.8,'beta',0.5,'gam',0.8,'delta',0.2);
pd2 = makedist('Stable','alpha',0.8,'beta',0.5,'gam',0.8,'delta',0.2);
pd3 = makedist('Stable','alpha',0.3,'beta',0.5,'gam',0.8,'delta',0.2);

%Calculate the pdf for each distribution.
x = -5:.1:5;
pdf1 = pdf(pd1,x);
pdf2 = pdf(pd2,x);
pdf3 = pdf(pd3,x);

%Plot all three pdf functions
figure
plot(x,pdf1,'b-');
hold on
plot(x,pdf2,'r-.');
plot(x,pdf3,'k--');
title('Alpha Parameter in PDFs Plots')
legend('\alpha = 1.8','\alpha = 0.8','\alpha = 0.3','Location','northwest')
hold off

%Compare the pdfs for stable distributions with different beta values.
%In each case, alpha = 0.3, gam = 0.8, and delta = 0.2.
pd1 = makedist('Stable','alpha',0.3,'beta',0.3,'gam',0.8,'delta',0.2);
pd2 = makedist('Stable','alpha',0.3,'beta',0.5,'gam',0.8,'delta',0.2);
pd3 = makedist('Stable','alpha',0.3,'beta',0.8,'gam',0.8,'delta',0.2);

% Calculate the pdf for each distribution.
x = -5:.1:5;
pdf1 = pdf(pd1,x);
pdf2 = pdf(pd2,x);
pdf3 = pdf(pd3,x);
% Plot all three pdf functions
figure
plot(x,pdf1,'b-');
hold on
plot(x,pdf2,'r-.');
plot(x,pdf3,'k--');
title('Beta Parameter in PDFs Plots')
legend('\beta = 0.3','\beta = 0.5','\beta = 0.8','Location','northwest')
hold off

%Compare CDFs of Stable Distributions with different alpha values.
%In each case, beta = 0.5, gam = 0.8, and delta = 0.2.
pd1 = makedist('Stable','alpha',1.8,'beta',0.5,'gam',0.8,'delta',0.2);
pd2 = makedist('Stable','alpha',0.8,'beta',0.5,'gam',0.8,'delta',0.2);
pd3 = makedist('Stable','alpha',0.3,'beta',0.5,'gam',0.8,'delta',0.2);

%Calculate the cdf for each distribution.
x = -5:.1:5;
cdf1 = cdf(pd1,x);
cdf2 = cdf(pd2,x);
cdf3 = cdf(pd3,x);

% Plot all three cdf functions
figure
plot(x,cdf1,'b-');
hold on
plot(x,cdf2,'r-.');
plot(x,cdf3,'k--');
title('Alpha Parameter in CDFs Plots')
legend('\alpha = 1.8','\alpha = 0.8','\alpha = 0.3','Location','northwest')
hold off

%Compare the cdfs for stable distributions with different beta values.
%In all cases, alpha = 0.3, gam = 0.8, and delta = 0.2.
pd1 = makedist('Stable','alpha',0.3,'beta',0.3,'gam',0.8,'delta',0.2);
pd2 = makedist('Stable','alpha',0.3,'beta',0.5,'gam',0.8,'delta',0.2);
pd3 = makedist('Stable','alpha',0.3,'beta',0.8,'gam',0.8,'delta',0.2);

% Calculate the cdf for each distribution.
x = -5:.1:5;
cdf1 = cdf(pd1,x);
cdf2 = cdf(pd2,x);
cdf3 = cdf(pd3,x);

% Plot all three pdf functions
figure
plot(x,cdf1,'b-');
hold on
plot(x,cdf2,'r-.');
plot(x,cdf3,'k--');
title('Beta Parameter in CDFs Plots')
legend('\beta = 0.3','\beta = 0.5','\beta = 0.8','Location','northwest')
hold off

% Compare the pdfs for the standard normal, Cauchy, and Lévy distributions.
% Create a probability distribution object for the standard normal, Cauchy, and Lévy distributions.
pd_norm = makedist('Stable','alpha',1.8,'beta',0.3,'gam',1/sqrt(2),'delta',0.2);
pd_cauchy = makedist('Stable','alpha',0.8,'beta',0.3,'gam',0.8,'delta',0.2);
pd_levy = makedist('Stable','alpha',0.3,'beta',0.8,'gam',0.8,'delta',0.2);

% Calculate the pdf for each distribution.
x = -5:.1:5;
pdf_norm = pdf(pd_norm,x);
pdf_cauchy = pdf(pd_cauchy,x);
pdf_levy = pdf(pd_levy,x);

%Plot all three pdf functions
figure
plot(x,pdf_norm,'b-');
hold on
plot(x,pdf_cauchy,'r.');
plot(x,pdf_levy,'k--');
title('Pdf Plots')
legend('Normal','Cauchy','Levy','Location','northwest')
hold off
