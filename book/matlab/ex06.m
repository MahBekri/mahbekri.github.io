%Exercise_Copula.m

function Copula_1()
    figure(1)
    ranG =Figure_Copula('Gaussian',0.6);
    figure(2)
    ranC =Figure_Copula('clayton',8);
    corr(ranG)
    corr(ranC)
    return;

function ran = Figure_Copula(name,param)
    Num_Sample = 1000;
    N=20;
    u = linspace(0,1,N);
    [U1,U2] = meshgrid(u,u);
    cdf = copulacdf(name,[U1(:) U2(:)],param);
    pdf = copulapdf(name,[U1(:) U2(:)],param);
    ran = copularnd(name,param,Num_Sample);

    %%
    subplot(221),...
        surf(U1,U2,reshape(cdf,N,N)), ...
        title('cdf-surf'), ...
        xlabel('u1'),ylabel('u2');
    subplot(222), ...
        contour(U1,U2,reshape(cdf,N,N)), ...
        title('cdf-contour'), ...
        xlabel('u1'),ylabel('u2');
    subplot(223), ...
        surf(U1,U2,reshape(pdf,N,N)), ...
        title('pdf-surf'), ...
        xlabel('u1'),ylabel('u2');
    subplot(224), ...
        plot(ran(:,1),ran(:,2),'.'), ...
        title('copula random numbers'), ...
        xlabel('u1'),ylabel('u2');
    return

function ran = Figure_Copula(name,param)
    Num_Sample = 1000;
    N=20;
    u = linspace(0,1,N);
    [U1,U2] = meshgrid(u,u);
    cdf = copulacdf(name,[U1(:) U2(:)],param);
    pdf = copulapdf(name,[U1(:) U2(:)],param);
    ran = copularnd(name,param,Num_Sample);
    subplot(221),...
        surf(U1,U2,reshape(cdf,N,N)), ...
        title('cdf-surf'), ...
        xlabel('u1'),ylabel('u2');
    subplot(222), ...
        contour(U1,U2,reshape(cdf,N,N)), ...
        title('cdf-contour'), ...
        xlabel('u1'),ylabel('u2');
    subplot(223), ...
        surf(U1,U2,reshape(pdf,N,N)), ...
        title('pdf-surf'), ...
        xlabel('u1'),ylabel('u2');
    subplot(224), ...
        plot(ran(:,1),ran(:,2),'.'), ...
        title('copula random numbers'), ...
        xlabel('u1'),ylabel('u2');
    return
function Copula_2()

    Num_Sample = 1000;
    param_G = [3,1];

    % ranGum = Gamma(Num_Sample, Param_G, name, param)

    figure(1)
    ranG= Gamma(Num_Sample, param_G,'Gaussian',0.6);

    figure(2)
    ranGum= Gamma(Num_Sample, param_G,'Gumbel',2);

    corr(ranG)
    corr(ranGum)
    return;

function ran = Gamma(Num_Sample, param_G, name, param)

    ran = copularnd(name,param,Num_Sample);

    b = gaminv(ran, param_G (1), param_G (2));
    plot(b(:,1),b(:,2),'.');
    return

function ran = Gamma(Num_Sample, param_G, name, param)
    ran = copularnd(name,param,Num_Sample);

    b = gaminv(ran, param_G (1), param_G (2));
    plot(b(:,1),b(:,2),'.');
    return
