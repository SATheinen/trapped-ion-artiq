from config import E_CHARGE, M_CA, ELECTRODE_PITCH, N_ELECTRODES, N_ZONES, SECULAR_FREQ
import numpy as np
import matplotlib.pyplot as plt

class Trap:

    def __init__(self):
        self.electrode_positions = (np.arange(N_ELECTRODES) - (N_ELECTRODES - 1) / 2) * ELECTRODE_PITCH
        self.zone_to_electrode = np.arange(1, 1 + N_ZONES)
        self.zone_positions = self.electrode_positions[self.zone_to_electrode]
        self.sigma = ELECTRODE_PITCH

    def phi(self, z, i):
        return np.exp(-(z - self.electrode_positions[i])**2 / (2 * self.sigma**2))
    
    def phi_prime(self, z, i):
        return -(z - self.electrode_positions[i]) / (self.sigma**2) * self.phi(z, i)
    
    def phi_double_prime(self, z, i):
        return ((z - self.electrode_positions[i])**2 / self.sigma**4 - 1 / self.sigma**2) * self.phi(z, i)
    
    def potential(self, z, voltages):
        voltage_sum = 0
        for i in range(N_ELECTRODES):
            voltage_sum += voltages[i] * self.phi(z, i)
        return voltage_sum
    
    def target_curvature(self, omega):
        return M_CA * omega**2 / E_CHARGE
    
    def solve_voltages(self, z0, k, reg=1e-6):
        A = np.array([
            [self.phi(z0, i) for i in range(N_ELECTRODES)],
            [self.phi_prime(z0, i) for i in range(N_ELECTRODES)],
            [self.phi_double_prime(z0, i) for i in range(N_ELECTRODES)],
        ])
        b = np.array([0.0, 0.0, k])
        y = np.linalg.solve(A @ A.T + reg * np.eye(3), b)
        return A.T @ y

if __name__ == "__main__":
    trap = Trap()
    k = trap.target_curvature(SECULAR_FREQ)

    voltages_per_zone = [trap.solve_voltages(z0, k) for z0 in trap.zone_positions]
    for z0, V in zip(trap.zone_positions, voltages_per_zone):
        u_prime = sum(V[i] * trap.phi_prime(z0, i) for i in range(N_ELECTRODES))
        u_dprime = sum(V[i] * trap.phi_double_prime(z0, i) for i in range(N_ELECTRODES))
        assert abs(u_prime) < 1e-3, f"slope not zero at z0={z0}: {u_prime}"
        assert abs(u_dprime - k) / k < 1e-3, f"curvature mismatch at z0={z0}"

    z_grid = np.linspace(trap.electrode_positions[0], trap.electrode_positions[-1], 800)
    fig, ax = plt.subplots(figsize=(9, 5))
    for k_zone, (z0, V) in enumerate(zip(trap.zone_positions, voltages_per_zone)):
        ax.plot(z_grid * 1e6, trap.potential(z_grid, V), label=f"Z{k_zone} (z₀={z0*1e6:.0f} μm)")
        ax.axvline(z0 * 1e6, color="black", lw=0.4, alpha=0.3)
    ax.set_xlabel("z (μm)")
    ax.set_ylabel("U(z)  (V)")
    ax.set_title("Trap potential — one solution per zone")
    ax.legend()
    ax.grid(alpha=0.25, ls=":")
    fig.tight_layout()
    fig.savefig("zone_potentials.pdf", bbox_inches="tight")

    print("Zone | V_0     V_1     V_2     V_3     V_4     V_5     V_6")
    for k_zone, V in enumerate(voltages_per_zone):
        print(f"  Z{k_zone}  | " + "  ".join(f"{v:+.3f}" for v in V))