# Exercise 06 (chapter 6)  Copulas
# Gaussian (rho = 0.6) and Clayton (theta = 8): cdf, pdf and 1,000 random vectors;
# then Gaussian (rho = 0.6) and Gumbel (theta = 2) copulas with Gamma(3, 1) margins.
from bookkit import *
rng = np.random.default_rng(0)

def figure_copula(name, param, n_sample=1000, N=20):
    u = np.linspace(0, 1, N)
    U1, U2 = np.meshgrid(u, u)
    UU = np.column_stack([U1.ravel(), U2.ravel()])
    cdf = copulacdf(name, UU, param).reshape(N, N)
    pdf = copulapdf(name, UU, param).reshape(N, N)
    ran = copularnd(name, param, n_sample, rng=rng)
    fig = plt.figure(figsize=(8.5, 7))
    fig.suptitle(f"{name} copula, parameter {param}")
    ax = fig.add_subplot(221, projection="3d"); ax.plot_surface(U1, U2, cdf, cmap="Blues")
    ax.set_title("cdf-surf"); ax.set_xlabel("u1"); ax.set_ylabel("u2")
    ax = fig.add_subplot(222); ax.contour(U1, U2, cdf, 10, cmap="Blues_r")
    ax.set_title("cdf-contour"); ax.set_xlabel("u1"); ax.set_ylabel("u2")
    ax = fig.add_subplot(223, projection="3d")
    ax.plot_surface(U1, U2, np.minimum(pdf, np.percentile(pdf, 97)), cmap="Blues")  # clip the corner spikes
    ax.set_title("pdf-surf"); ax.set_xlabel("u1"); ax.set_ylabel("u2")
    ax = fig.add_subplot(224); ax.plot(ran[:, 0], ran[:, 1], ".", ms=2.5)
    ax.set_title("copula random numbers"); ax.set_xlabel("u1"); ax.set_ylabel("u2")
    fig.tight_layout()
    return ran

# Copula_1
ranG = figure_copula("Gaussian", 0.6)
ranC = figure_copula("Clayton", 8)
mat("corr(ranG)", np.corrcoef(ranG, rowvar=False), "{:9.4f}")
mat("corr(ranC)", np.corrcoef(ranC, rowvar=False), "{:9.4f}")

# The other two copulas of the exercise, for comparison (same random-number count)
fig, ax = plt.subplots(1, 3, figsize=(10, 3.4))
for a, (nm, th) in zip(ax, [("Gumbel", 2), ("Frank", 8), ("t", None)]):
    r = copularnd("t", 0.6, 4, 1000, rng=rng) if nm == "t" else copularnd(nm, th, 1000, rng=rng)
    a.plot(r[:, 0], r[:, 1], ".", ms=2); a.set_title(f"{nm}" + (f", θ = {th}" if th else ", ρ = 0.6, ν = 4"))
fig.tight_layout()

# Copula_2: Gamma(alpha = 3, beta = 1) margins (MATLAB: gaminv)
def gamma_sample(name, param, n_sample=1000, a=3, b=1):
    ran = copularnd(name, param, n_sample, rng=rng)
    return stats.gamma.ppf(ran, a, scale=b)

bG = gamma_sample("Gaussian", 0.6)
bGum = gamma_sample("Gumbel", 2)
fig, ax = plt.subplots(1, 2, figsize=(9, 4))
ax[0].plot(bG[:, 0], bG[:, 1], ".", ms=2.5); ax[0].set_title("Gaussian copula ρ = 0.6, Gamma(3,1) margins")
ax[1].plot(bGum[:, 0], bGum[:, 1], ".", ms=2.5, color=COLORS[1]); ax[1].set_title("Gumbel copula θ = 2, Gamma(3,1) margins")
fig.tight_layout()
mat("corr(Gaussian-Gamma)", np.corrcoef(bG, rowvar=False), "{:9.4f}")
mat("corr(Gumbel-Gamma)", np.corrcoef(bGum, rowvar=False), "{:9.4f}")
# Tail dependence coefficients: the limit probability that one variable is extreme given
# that the other is. Lower tail = joint losses, upper tail = joint gains.
print("\nTail dependence      lower    upper")
for nm, lo, up in [("Gaussian, rho=0.6", 0.0, 0.0),
                   ("t, rho=0.6, nu=4", *(2 * stats.t.sf(np.sqrt(5 * 0.4 / 1.6), 5),) * 2),
                   ("Clayton, theta=8", 2 ** (-1 / 8), 0.0),
                   ("Gumbel, theta=2", 0.0, 2 - 2 ** (1 / 2)),
                   ("Frank, theta=8", 0.0, 0.0)]:
    print(f"  {nm:<18} {lo:7.3f}  {up:7.3f}")
print("For loss risk the lower tail matters: Clayton links joint crashes, the Gaussian does not.")
print("\nThe Gumbel sample clusters in the upper-right corner: upper tail dependence,"
      "\nwhich the Gaussian copula cannot produce.")
plt.show()
