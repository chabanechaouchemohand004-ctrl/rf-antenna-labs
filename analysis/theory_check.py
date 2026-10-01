"""
Analytical cross-checks for the FEKO simulations.

1. 5-element patch array @ 770 MHz: array factor (uniform vs Dolph-Chebyshev -20 dB)
   compared with the FEKO phi = 0 deg cuts.
2. E-plane sectoral horn (WR-90, 10 GHz): Balanis closed-form directivity vs FEKO gain.
3. K-band pyramidal horn: aperture-efficiency estimate vs FEKO gain.

Run:  python theory_check.py      (numpy, scipy, matplotlib)
"""
import warnings
import numpy as np
import matplotlib.pyplot as plt
from scipy.special import fresnel
from scipy.signal.windows import chebwin

warnings.filterwarnings("ignore", message="This window is not suitable")
C0 = 299_792_458.0


def db(x):
    return 20 * np.log10(np.maximum(np.abs(x), 1e-12))


# ---------------------------------------------------------------------------
# 1. Linear array
# ---------------------------------------------------------------------------
F0 = 770e6
LAM0 = C0 / F0
EPS_R = 4.5
D = LAM0 / np.sqrt(EPS_R)          # FEKO "period = lambda" -> lambda_d = 18.35 cm
N = 5

theta = np.radians(np.linspace(-90, 90, 36001))
k = 2 * np.pi / LAM0
n = np.arange(N) - (N - 1) / 2

w_uni = np.ones(N)
w_cheb = chebwin(N, at=20)          # Dolph-Chebyshev, -20 dB side lobes
w_cheb_edge1 = w_cheb / w_cheb[0]   # normalised like the FEKO excitation (edge = 1 V)


def array_factor(w, element=None):
    af = np.abs(np.exp(1j * k * D * np.outer(np.sin(theta), n)) @ w)
    if element is not None:
        af = af * element
    return af / af.max()


def metrics(af):
    """HPBW (deg), first-null angle (deg), peak side-lobe level (dB)."""
    t = np.degrees(theta)
    p = db(af)
    i0 = np.argmax(af)
    right = af[i0:]
    hp = t[i0 + np.argmax(right < 1 / np.sqrt(2))]
    # first null = first local minimum right of the peak
    j = i0 + np.argmax(np.diff(right) > 0)
    null = t[j]
    sll = p[j:].max()
    return 2 * hp, null, sll


# Illustrative element pattern: patch over an infinite ground plane -> field
# vanishes at the horizon. cos(theta) is a crude stand-in, not a patch model.
elem = np.cos(theta)

cases = {
    "Uniform": w_uni,
    "Chebyshev -20 dB": w_cheb,
}
# Values read on the POSTFEKO phi = 0 deg cuts (report figs 1.1.1e and 1.3e)
feko = {
    "Uniform":          dict(hpbw=21.25, sll=-14.5, lobes=[(36, -14.5), (71, -28.0)]),
    "Chebyshev -20 dB": dict(hpbw=24.13, sll=-23.0, lobes=[(41, -23.0), (72, -35.0)]),
}

print(f"Array: N = {N}, f0 = {F0/1e6:.0f} MHz, d = {D*100:.2f} cm = {D/LAM0:.3f} lambda0")
print("Chebyshev weights (edge = 1):", np.round(w_cheb_edge1, 3))
print(f"{'':18s}{'HPBW AF':>9s}{'HPBW FEKO':>11s}{'SLL AF':>9s}{'SLL AF*cos':>12s}{'SLL FEKO':>10s}")
for name, w in cases.items():
    h, nul, s = metrics(array_factor(w))
    _, _, s_el = metrics(array_factor(w, elem))
    fk = feko[name]
    print(f"{name:18s}{h:8.2f}°{fk['hpbw']:10.2f}°{s:8.1f} dB{s_el:9.1f} dB{fk['sll']:8.1f} dB"
          f"   (first null {nul:.1f}°)")

# ---- figure ---------------------------------------------------------------
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
t = np.degrees(theta)
for ax, (name, w) in zip(axes, cases.items()):
    ax.plot(t, db(array_factor(w)), color="#1f5fa8", lw=1.6, label="Array factor (theory)")
    ax.plot(t, db(array_factor(w, elem)), color="#1f5fa8", lw=1.0, ls="--",
            label="AF × cos θ (element roll-off)")
    pts = feko[name]["lobes"]
    xs = [s * a for a, _ in pts for s in (-1, 1)]
    ys = [l for _, l in pts for _ in (0, 1)]
    ax.scatter(xs, ys, color="#d1495b", zorder=3, s=28, label="FEKO side lobes")
    ax.axhline(-20, color="0.6", lw=0.8, ls=":")
    ax.set_title(name)
    ax.set_xlabel("θ (deg)")
    ax.set_xlim(-90, 90)
    ax.set_ylim(-45, 2)
    ax.grid(alpha=0.3)
axes[0].set_ylabel("Normalised pattern (dB)")
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=3, fontsize=9, frameon=False)
fig.suptitle("5-patch array, 770 MHz, d = 0.47 λ0 — theory vs FEKO", fontsize=11)
fig.tight_layout(rect=(0, 0.07, 1, 1))
fig.savefig("../figures/array_theory_vs_feko.png", dpi=150)

# ---------------------------------------------------------------------------
# 2. E-plane sectoral horn (Balanis, Antenna Theory, eq. 13-19)
# ---------------------------------------------------------------------------
A, B1, RHO1 = 22.86e-3, 140e-3, 330e-3


def d_eplane(f, a=A, b1=B1, rho1=RHO1):
    lam = C0 / f
    q = b1 / np.sqrt(2 * lam * rho1)
    S, C = fresnel(q)
    return 64 * a * rho1 / (np.pi * lam * b1) * (C**2 + S**2)


print("\nE-plane horn (a = 22.86 mm, b1 = 140 mm, rho1 = 330 mm)")
for f, g_feko in [(8.2e9, 14.9), (10e9, 15.8), (12.4e9, 16.7)]:
    print(f"  {f/1e9:5.1f} GHz  Balanis D_E = {10*np.log10(d_eplane(f)):5.1f} dBi   FEKO gain = {g_feko} dBi")

# rho1 needed for 19 dBi at 10 GHz with optimum b1 = sqrt(2 lambda rho1)
lam = C0 / 10e9
for r in np.arange(10, 400) * lam:
    if 10 * np.log10(d_eplane(10e9, b1=np.sqrt(2 * lam * r), rho1=r)) >= 19:
        print(f"  19 dBi needs rho1 ≈ {r/lam:.0f} λ ({r:.2f} m) -> target not reachable with rho1 = 11 λ")
        break

# ---------------------------------------------------------------------------
# 3. Pyramidal horn, K band (a1 = 60.3 mm, b1 = 46.9 mm), optimum-horn eff. ~0.51
# ---------------------------------------------------------------------------
print("\nPyramidal horn (a1 = 60.3 mm, b1 = 46.9 mm), D ≈ 0.51·4π·a1·b1/λ²")
for f, g_feko in [(18e9, 18.9), (22.25e9, 20.2), (26.5e9, 20.9)]:
    lam = C0 / f
    d_est = 0.51 * 4 * np.pi * 60.3e-3 * 46.9e-3 / lam**2
    print(f"  {f/1e9:5.2f} GHz  estimate = {10*np.log10(d_est):5.1f} dBi   FEKO = {g_feko} dBi")
