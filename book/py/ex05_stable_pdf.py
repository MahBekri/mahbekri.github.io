# Exercise 05 (chapter 5)  Stable probability density function
# Densities and cdfs of S(alpha, beta, gam, delta) in the S1 parameterisation
# (MATLAB: makedist('Stable', ...)).
from bookkit import *

x = np.arange(-5, 5.0001, 0.1)
styles = ["-", "-.", "--"]

def compare(params, fn, title, labels):
    plt.figure(figsize=(6.4, 4))
    for (a, b, g, d), st, lab in zip(params, styles, labels):
        pd = Stable(a, b, g, d)
        plt.plot(x, getattr(pd, fn)(x), st, label=lab)
    plt.title(title); plt.legend(loc="upper left")

# 1. pdfs for alpha = 1.8, 0.8, 0.3 (beta = 0.5, gam = 0.8, delta = 0.2)
A = [(1.8, 0.5, 0.8, 0.2), (0.8, 0.5, 0.8, 0.2), (0.3, 0.5, 0.8, 0.2)]
compare(A, "pdf", "Alpha parameter in pdf plots", ["α = 1.8", "α = 0.8", "α = 0.3"])
# 2. pdfs for beta = 0.3, 0.5, 0.8 (alpha = 0.3, gam = 0.8, delta = 0.2)
B = [(0.3, 0.3, 0.8, 0.2), (0.3, 0.5, 0.8, 0.2), (0.3, 0.8, 0.8, 0.2)]
compare(B, "pdf", "Beta parameter in pdf plots", ["β = 0.3", "β = 0.5", "β = 0.8"])
# 3. cdfs for different alpha
compare(A, "cdf", "Alpha parameter in cdf plots", ["α = 1.8", "α = 0.8", "α = 0.3"])
# 4. cdfs for different beta
compare(B, "cdf", "Beta parameter in cdf plots", ["β = 0.3", "β = 0.5", "β = 0.8"])

# 5. Standard normal, Cauchy and Levy as special cases of the stable law.
# NOTE: the book's code uses (1.8, 0.3, 1/sqrt(2), 0.2), (0.8, 0.3, 0.8, 0.2) and
# (0.3, 0.8, 0.8, 0.2), which are not these laws. The closed-form cases are:
#   Normal N(0,1) = S(2, 0, 1/sqrt(2), 0)
#   Cauchy        = S(1, 0, 1, 0)
#   Levy          = S(0.5, 1, 1, 0)
pd_norm = Stable(2, 0, 1 / np.sqrt(2), 0)
pd_cauchy = Stable(1, 0, 1, 0)
pd_levy = Stable(0.5, 1, 1, 0)
plt.figure(figsize=(6.4, 4))
plt.plot(x, pd_norm.pdf(x), "-", label="Normal")
plt.plot(x, pd_cauchy.pdf(x), ".", ms=4, label="Cauchy")
plt.plot(x, pd_levy.pdf(x), "--", label="Lévy")
plt.title("Pdf plots"); plt.legend(loc="upper left")

# check against the closed forms
print("max |stable - closed form| on the grid:")
print(f"  normal: {np.max(np.abs(pd_norm.pdf(x) - stats.norm.pdf(x))):.2e}")
print(f"  Cauchy: {np.max(np.abs(pd_cauchy.pdf(x) - stats.cauchy.pdf(x))):.2e}")
print(f"  Levy:   {np.max(np.abs(pd_levy.pdf(x) - stats.levy.pdf(x))):.2e}")
plt.show()
