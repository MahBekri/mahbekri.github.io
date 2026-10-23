%Exercise_performance_measures
clear
clc

%%Data
%Return Benchmark: rb
load data_book_DJI
rb = tick2ret(DJI_price);

%Return portoflio: rp
load data_book_portfolio
for i= 1:6
    Ret_p(:,i) = data(2:(length(data)),i)./data(1:(length(data)-1),i);
end
w= 1/6;
for i= 1:6
    rp = Ret_p(:,i)*w;
end

% Calculate Sharpe Ratio
Sharpe = sharpe(rp,rb)

% Calculate STARR Ratio for alpha = 0.01
alpha = 0.01;
[STARR] = STARR_Ratio(rp,rb,alpha)

% Calculate Rachev ratio for alpha_num = 0.05 and alpha_denum = 0.01
alpha_num = 0.05;
alpha_denum = 0.01;
[Rachev_Ratio] = RachevRatio(rp, alpha_num,alpha_denum)

function [STARR] = STARR_Ratio(rp,rb,alpha)
    %%%%%%%%%%%%%% Mean %%%%%%%%%%%%%
    E = mean(rp-rb);
    %%%%%%%% Expected Loss Tail %%%%%%%%%%%%%%%%%%
    retur = (rp-rb);
    r = sort(retur);
    n = max(size(retur));
    ub = ceil(n*alpha) - 1;
    x = ceil(n*alpha);
    ETL = -1/alpha *(1/n * sum(r(1:ub)) + (alpha - ub/n)*r(x));
    %%%%%%%%%% STARR_ratio
    STARR = E/ETL;
end

function [Rachev_Ratio] = RachevRatio(rp, alpha_num,alpha_denum)
    %%%%%%%%%%%%%% Expected Gain Tail %%%%%%%%%%%%%
    g = sort(rp,'descend');
    n = length(rp);
    beta = alpha_num;
    ub = ceil(n*beta) - 1;
    GTL = -1/beta *(1/n * sum(-g(1:ub)) + (beta - ub/n)*(-g(ub)));
    %%%%%%%% Expected Loss Tail %%%%%%%%%%%%%%%%%%
    r = sort(rp);
    n = length(rp);
    alpha = alpha_denum;
    ub = ceil(n*alpha) - 1;
    ETL = -1/alpha *(1/n * sum(r(1:ub)) + (alpha - ub/n)*r(ub));
    %%%%%%%%%% Rachev_Ratio
    Rachev_Ratio = GTL/ETL;
end
