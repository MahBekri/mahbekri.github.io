% Exercise_LogNormalFit.m
% Data is the downloaded INTC Price Data

[parmhat,parmci] = lognfit(data);
xmin= min(data);
xmax= max(data);
dx = 5;
x = xmin:dx:xmax;
[ydata,xdata]= hist(data, x);

figure(1)
bar(x,ydata/length(data),'hist');
h = findobj(gca,'Type','patch');
gray=0.6*[1,1,1];
set(h,'FaceColor',gray,'EdgeColor',gray)

hold on;
plot(x,dx*lognpdf(x,parmhat(1),parmhat(2)),'-');
hold off

h = findobj(gca,'Type','patch');
gray=0.6*[1,1,1];
set(h,'FaceColor',gray,'EdgeColor',gray)

hold on;
plot(x,dx*lognpdf(x,parmhat(1),parmhat(2)),'-');
hold off

sorteddata = sort(data);
a=ones(1,length(sorteddata));
empcdf = cumsum(a)./length(sorteddata);

figure(2)
stairs(sorteddata,empcdf);
hold on;
plot(sorteddata,logncdf(sorteddata,parmhat(1),parmhat(2)),'-');
hold off
%Exercise_NormalFit.m
% Data is the downloaded INTC Price Data

data = flipud(data);
logret = price2ret(data);

[mu,sig,muci,sigci] = normfit(logret);
xmin= min(logret);
xmax= max(logret);
dx = 0.001;
x = xmin:dx:xmax;

[ydata,xdata]=hist(logret, x);
bar(x,ydata/length(logret),'hist');

h = findobj(gca,'Type','patch');
gray=0.6*[1,1,1];
set(h,'FaceColor',gray,'EdgeColor',gray)

hold on;
plot(x,dx*normpdf(x,mu,sig),'-');
hold off
