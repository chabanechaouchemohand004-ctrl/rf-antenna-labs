"""WR90 rectangular waveguide: analytical model next to the HFSS numbers.

Computes, for an air-filled copper WR90 guide:
  - cutoff frequencies of the first modes,
  - TE10 phase constant beta(f) and guided wavelength,
  - TE10 conductor attenuation (smooth copper walls, lossless air),
and compares them with the values read from the HFSS captures in figures/.

Run:  python wr90_theory.py
Needs: numpy, matplotlib.
Outputs: results printed to the console, plus two PNG files in figures/.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# --- Physical constants -------------------------------------------------
C0 = 299_792_458.0            # m/s
MU0 = 4e-7 * np.pi            # H/m
ETA0 = 376.730313668          # ohm, free-space impedance

# --- WR90 geometry and material (from the lab statement) ----------------
A = 22.86e-3                  # m, inner width
B = 10.16e-3                  # m, inner height
L = 100e-3                    # m, simulated length
SIGMA_CU = 5.8e7              # S/m, copper

# --- Values read from the HFSS captures (Ansys Electronics Desktop 2021 R2)
# See figures/ and the README for where each number comes from.
HFSS_FC_TE10_GHZ = 6.58       # -3 dB point on dB(S(2:1,1:1)), marker label
HFSS_FC_TE20_GHZ = 13.17      # -3 dB point on dB(S(2:2,1:2)), marker label
HFSS_PHASE_10GHZ_RAD = -15.8190   # cang_rad(S(2:1,1:1)) at 10 GHz, marker m5
HFSS_S21_10GHZ_DB = -0.0108   # dB(S(2:1,1:1)) at 10 GHz, marker m1


def cutoff_hz(m, n, a=A, b=B):
    """Cutoff frequency of mode (m, n) in a rectangular guide."""
    return 0.5 * C0 * np.sqrt((m / a) ** 2 + (n / b) ** 2)


def beta_te10(f_hz):
    """TE10 phase constant in rad/m. Zero below cutoff."""
    k0 = 2 * np.pi * np.asarray(f_hz) / C0
    fc = cutoff_hz(1, 0)
    arg = 1 - (fc / np.asarray(f_hz)) ** 2
    return np.where(arg > 0, k0 * np.sqrt(np.clip(arg, 0, None)), 0.0)


def guided_wavelength_te10(f_hz):
    """Guided wavelength in m. Valid above cutoff."""
    return 2 * np.pi / beta_te10(f_hz)


def alpha_conductor_te10_db_per_m(f_hz, sigma=SIGMA_CU):
    """TE10 conductor attenuation in dB/m (Pozar, Microwave Engineering).

    alpha_c = Rs * (2 b pi^2 + a^3 k^2) / (a^3 b beta k eta)   [Np/m]
    """
    f = np.asarray(f_hz, dtype=float)
    k = 2 * np.pi * f / C0
    beta = beta_te10(f)
    rs = np.sqrt(2 * np.pi * f * MU0 / (2 * sigma))
    with np.errstate(divide="ignore", invalid="ignore"):
        alpha_np = rs * (2 * B * np.pi**2 + A**3 * k**2) / (
            A**3 * B * beta * k * ETA0
        )
    return 8.685889638 * alpha_np


def main():
    out_dir = Path(__file__).resolve().parent / "figures"
    out_dir.mkdir(exist_ok=True)

    # 1. Cutoff frequencies
    print("Cutoff frequencies (theory, c = 299 792 458 m/s)")
    for (m, n, name) in [(1, 0, "TE10"), (2, 0, "TE20"), (0, 1, "TE01"), (1, 1, "TE11/TM11")]:
        print(f"  {name:10s} {cutoff_hz(m, n) / 1e9:8.3f} GHz")
    fc10 = cutoff_hz(1, 0) / 1e9
    fc20 = cutoff_hz(2, 0) / 1e9
    print(f"Single-mode band: {fc10:.3f} to {fc20:.3f} GHz")
    print(f"Manufacturer band 8.2 to 12.4 GHz lies inside it.\n")

    print("HFSS -3 dB cutoff vs theory")
    for name, hfss, th in [("TE10", HFSS_FC_TE10_GHZ, fc10), ("TE20", HFSS_FC_TE20_GHZ, fc20)]:
        print(f"  {name}: HFSS {hfss:.2f} GHz, theory {th:.3f} GHz, "
              f"difference {100 * (hfss - th) / th:+.2f} %")

    # 2. Guided wavelength and beta at 10 GHz
    f0 = 10e9
    lam0 = C0 / f0
    lam_g_th = float(guided_wavelength_te10(f0))
    beta_th = float(beta_te10(f0))
    beta_hfss = abs(HFSS_PHASE_10GHZ_RAD) / L
    lam_g_hfss = 2 * np.pi / beta_hfss
    print("\nAt 10 GHz")
    print(f"  free-space wavelength : {lam0 * 1e3:.2f} mm")
    print(f"  guided wavelength     : theory {lam_g_th * 1e3:.2f} mm, "
          f"HFSS {lam_g_hfss * 1e3:.2f} mm "
          f"({100 * (lam_g_hfss - lam_g_th) / lam_g_th:+.2f} %)")
    print(f"  beta                  : theory {beta_th:.1f} rad/m, HFSS {beta_hfss:.1f} rad/m")

    # 3. Attenuation
    alpha_th = float(alpha_conductor_te10_db_per_m(f0))
    alpha_hfss = abs(HFSS_S21_10GHZ_DB) / L
    print(f"  attenuation           : theory {alpha_th:.4f} dB/m, "
          f"HFSS {alpha_hfss:.4f} dB/m (|S21| / L)")
    print("\nTheory attenuation across the manufacturer band")
    for f_ghz in (8.2, 9.4, 10.0, 12.4):
        print(f"  {f_ghz:5.1f} GHz  {float(alpha_conductor_te10_db_per_m(f_ghz * 1e9)):.4f} dB/m")

    # 4. Figure: dispersion
    f = np.linspace(5e9, 15e9, 2000)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(f / 1e9, beta_te10(f), label="TE10 (theory)")
    beta_te20 = np.where(
        f > cutoff_hz(2, 0),
        2 * np.pi * f / C0 * np.sqrt(np.clip(1 - (cutoff_hz(2, 0) / f) ** 2, 0, None)),
        0.0,
    )
    ax.plot(f / 1e9, beta_te20, label="TE20 (theory)")
    ax.plot(f / 1e9, 2 * np.pi * f / C0, "k--", lw=0.8, label="free space, k0")
    ax.plot([10], [beta_hfss], "o", color="tab:red", label="HFSS, from S21 phase at 10 GHz")
    ax.axvspan(8.2, 12.4, color="grey", alpha=0.12, label="manufacturer band")
    ax.set_xlabel("Frequency (GHz)")
    ax.set_ylabel("Phase constant (rad/m)")
    ax.set_title("WR90 dispersion: analytical curves, one HFSS point")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "wr90_dispersion.png", dpi=150)
    plt.close(fig)

    # 5. Figure: attenuation
    fa = np.linspace(7.0e9, 13.0e9, 1000)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(fa / 1e9, alpha_conductor_te10_db_per_m(fa), label="TE10 conductor loss (theory)")
    ax.plot([10], [alpha_hfss], "o", color="tab:red", label="HFSS, |S21| / L at 10 GHz")
    ax.axvspan(8.2, 12.4, color="grey", alpha=0.12, label="manufacturer band")
    ax.set_xlabel("Frequency (GHz)")
    ax.set_ylabel("Attenuation (dB/m)")
    ax.set_title("WR90 attenuation: smooth copper, air-filled")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "wr90_attenuation.png", dpi=150)
    plt.close(fig)
    print(f"\nFigures written to {out_dir}")


if __name__ == "__main__":
    main()
