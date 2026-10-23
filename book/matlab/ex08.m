%ARMA-GARCH Value at Risk
% Data
clear
clc
load data_book_DJI.mat
%%
data = DJI_price;
logret = log(data(2:(length(data)))./data(1:(length(data)-1)));
y = logret;
%%

% Case _ T distribution
[a, b, c, beta1, alpha1, alpha0, DF, res, sig] = ARMAGARCH(logret,'T');

% Case _ normal distribution
%[a, b, c, beta1, alpha1, alpha0, DF, res, sig] = ARMAGARCH(logret,'normal');

%%/
% VaR estimation

sortedlogret = sort(logret);
subplot(2,2,1),plot(data)
subplot(2,2,3),plot(logret)
t = 10;

%Normal t-day VaR
m = mean(logret);
sig_nor = sqrt(var(logret));
norVaR95 = -icdf('normal',0.05,m*t,sig_nor*sqrt(t))
norVaR99 = -icdf('normal',0.01,m*t,sig_nor*sqrt(t))

subplot(2,2,2),plot(res)
subplot(2,2,4),plot(sig)

%%Simulation
Num_Days = 252;
Num_Path = 10000;

%% Case _ T distribution
[sp, ssig] = Path_ARMAGARCH(logret(length(logret)), sig(length(sig)), a, b, c, beta1, alpha1, alpha0,'T', DF, Num_Days, Num_Path);

%% Case _ normal distribution
%[sp, ssig] = Path_ARMAGARCH(logret(length(logret)), sig(length(sig)), a, b, c, beta1, alpha1, alpha0, 'normal', 0, Num_Days, Num_Path);

%%t-day VaR
SimRet = sp(t+1,:);
sortedSimRet = sort(SimRet);
SimVaR95 = -sortedSimRet(floor(0.05*length(sortedSimRet)))
SimVaR99 = -sortedSimRet(floor(0.01*length(sortedSimRet)))

function [a, b, c, beta1, alpha1, alpha0, DF, res, sig] = ARMAGARCH_t(logret,distname)

    if ( strcmp(distname,'T') )

        % Case _ T distribution
        Model = arima('ARLags',1:1,'MALags',1,'Variance',garch(1,1),'Distribution','t');
        %Data
        y=logret;
        EstModel = estimate(Model,y);
        [res,sig,logL] = infer(EstModel,y);
        % GARCH parameters
        alpha0 = EstModel.Variance.Constant;
        alpha1 = EstModel.Variance.ARCH{1};
        beta1 = EstModel.Variance.GARCH{1};
        % ARMA parameters
        a = EstModel.AR{1};
        b = EstModel.MA{1};
        c = EstModel.Constant;
        % DoF
        DF = EstModel.Distribution.DoF;
        %%
    else

        % Case _ normal distribution
        Model = arima('ARLags',1:1,'MALags',1,'Constant',0,'Variance',garch(1,1));
        %Data
        y=logret;
        EstModel = estimate(Model,y);
        [res,sig,logL] = infer(EstModel,y);
        % GARCH parameters
        alpha0 = EstModel.Variance.Constant;
        alpha1 = EstModel.Variance.ARCH{1};
        beta1 = EstModel.Variance.GARCH{1};
        % ARMA parameters
        a = EstModel.AR{1};
        b = EstModel.MA{1};
        c = EstModel.Constant;
        %
        DF = 0;
    end
    return

function [sp, ssig] = Path_ARMAGARCH(initlogret, initSig, a, b, c, beta1, alpha1, alpha0, distname,DF, Num_Days, Num_Path)

    sp = zeros(Num_Days+1, Num_Path );
    ssig = zeros(Num_Days+1, Num_Path );

    if ( strcmp(distname,'T') )
        eps = trnd(DF, Num_Days+1, Num_Path);
    else
        eps = randn(Num_Days+1, Num_Path);
    end

    for j = 1:Num_Path
        sp(1,j) = initlogret;
        ssig(1,j) = initSig;

        for k = 2:Num_Days+1
            ssig(k,j) = sqrt(alpha0+alpha1*ssig(k-1,j)^2*eps(k-1,j)^2 +beta1*ssig(k-1,j)^2);
            sp(k,j) = c + a*sp(k-1,j) + b*ssig(k-1,j)*eps(k-1,j)+ ssig(k,j)*eps(k,j);
        end;
    end;

    return
