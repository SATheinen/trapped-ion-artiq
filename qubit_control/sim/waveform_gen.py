from config import E_CHARGE, M_CA, ELECTRODE_PITCH, N_ELECTRODES, N_ZONES, SECULAR_FREQ
import numpy as np
from sim.trap_module import Trap
import matplotlib.pyplot as plt
from pathlib import Path

class WaveformGen:

    def smoothstep(self, tau):
        return 10*tau**3 - 15*tau**4 + 6*tau**5
    
    def generate_waveform(self, trap, z_start, z_end, duration_s, dt_s, k):
        n_frames = int(round(duration_s / dt_s)) + 1
        t = np.linspace(0, duration_s, n_frames)
        z0_of_t = z_start + (z_end - z_start) * self.smoothstep(t / duration_s)

        voltages_arr = np.zeros((n_frames, N_ELECTRODES))
        for frame in range(n_frames):
            voltages_arr[frame, :] = trap.solve_voltages(z0_of_t[frame], k)
        return voltages_arr
    
    def generate_all_routes(duration=200e-6, dt_s = 1e-6):
        trap = Trap()
        gen = WaveformGen()
        k = trap.target_curvature(SECULAR_FREQ)

        for i in range(N_ZONES):
            for j in range(N_ZONES):

                z_start = trap.zone_positions[i]
                z_end = trap.zone_positions[j]

                waveform = gen.generate_waveform(trap, z_start, z_end, duration_s, dt_s, k)
                n_frames = waveform.shape[0]
                t = np.linspace(0, duration_s, n_frames)

                out_dir = Path(__file__).parent.parent / "config" / "waveforms"
                out_dir.mkdir(parents=True, exist_ok=True)
                npy_path = out_dir / f"z{i}_to_z{j}.npy"
                np.save(npy_path, waveform)
                print(f"saved {waveform.shape} waveform → {npy_path}")
    
if __name__ == "__main__":
    trap = Trap()
    gen = WaveformGen()

    duration_s = 200e-6
    dt_s = 1e-6
    k = trap.target_curvature(SECULAR_FREQ)

    z_start = trap.zone_positions[0]
    z_end = trap.zone_positions[-1]

    waveform = gen.generate_waveform(trap, z_start, z_end, duration_s, dt_s, k)
    n_frames = waveform.shape[0]
    t = np.linspace(0, duration_s, n_frames)

    out_dir = Path(__file__).parent.parent / "config" / "waveforms"
    out_dir.mkdir(parents=True, exist_ok=True)
    npy_path = out_dir / "z0_to_z4.npy"
    np.save(npy_path, waveform)
    print(f"saved {waveform.shape} waveform → {npy_path}")

    # Recompute z_0(t) for plotting
    z0_of_t = z_start + (z_end - z_start) * gen.smoothstep(t / duration_s)

    # U(z,t) on a (n_frames, n_z) grid for the heatmap
    z_grid = np.linspace(trap.electrode_positions[0], trap.electrode_positions[-1], 200)
    U_grid = np.array([trap.potential(z_grid, V_t) for V_t in waveform])

    fig, axes = plt.subplots(3, 1, figsize=(9, 9), sharex=True)

    # — Top: trajectory z₀(t) with zone reference lines
    ax = axes[0]
    ax.plot(t * 1e6, z0_of_t * 1e6, color="black", lw=2)
    for k_zone, z in enumerate(trap.zone_positions):
        ax.axhline(z * 1e6, color="grey", lw=0.5, ls="--", alpha=0.5)
        ax.text(duration_s * 1e6 * 1.01, z * 1e6, f"Z{k_zone}",
                va="center", fontsize=9)
    ax.set_ylabel("z₀(t)  (μm)")
    ax.set_title("Minimum-jerk trajectory  Z0 → Z4")
    ax.grid(alpha=0.25, ls=":")

    # — Middle: 7 electrode voltage traces
    ax = axes[1]
    for i in range(N_ELECTRODES):
        ax.plot(t * 1e6, waveform[:, i], lw=1.4, label=f"V{i}")
    ax.set_ylabel("Vᵢ(t)  (V)")
    ax.set_title("Electrode voltages")
    ax.legend(loc="upper right", ncol=4, fontsize=8)
    ax.grid(alpha=0.25, ls=":")

    # — Bottom: U(z,t) heatmap with the target z₀(t) overlaid
    ax = axes[2]
    pcm = ax.pcolormesh(t * 1e6, z_grid * 1e6, U_grid.T,
                        shading="auto", cmap="viridis")
    ax.plot(t * 1e6, z0_of_t * 1e6, color="white", lw=1.2, ls="--", alpha=0.85)
    ax.set_xlabel("t (μs)")
    ax.set_ylabel("z (μm)")
    ax.set_title("U(z,t)  —  white dashed: target z₀(t)")
    fig.colorbar(pcm, ax=ax, label="U (V)")

    fig.tight_layout()
    pdf_path = Path("waveform_z0_to_z4.pdf")
    fig.savefig(pdf_path, bbox_inches="tight")
    print(f"saved figure → {pdf_path.resolve()}")