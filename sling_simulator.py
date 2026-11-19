import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import math
import csv
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import logging
from dataclasses import dataclass

# Suppress matplotlib font debug output
logging.getLogger('matplotlib.font_manager').setLevel(logging.INFO)
# Set up simulation logging
logging.basicConfig(level=logging.DEBUG, format='%(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SimulationParameters:
    dt: float
    sling_length: float
    sling_mass: float
    initial_hand_x: float
    initial_hand_y: float
    windup_speed_hz: float
    windup_turns: int
    power_stroke_begin_angle_deg: float
    hand_accel_direction_deg: float
    hand_accel_rate: float
    opening_duration: float
    release_angle_deg: float
    sim_time_after_release: float
    maximum_reach: float

@dataclass
class SimulationData:
    times: list
    hand_x: list
    hand_y: list
    hand_vel_x: list
    hand_vel_y: list
    hand_speeds: list
    mass_x: list
    mass_y: list
    mass_vel_x: list
    mass_vel_y: list
    mass_speeds: list
    mass_accel_x: list
    mass_accel_y: list
    mass_accel_mags: list
    angle_deg: list
    ang_speeds: list
    ang_accels: list
    tension: list
    phase: list

class SlingSimulator:
    def __init__(self):
        self.max_sim_steps = 50000
        self.float_threshold = 1e-12

    def _is_angle_newly_at_or_past(self, prev_rad, curr_rad, target_rad):
        prev_rad_norm = prev_rad % (2 * math.pi)
        curr_rad_norm = curr_rad % (2 * math.pi)
        target_rad_norm = target_rad % (2 * math.pi)
        if abs(curr_rad_norm - prev_rad_norm) < 1e-9:
            return abs(curr_rad_norm - target_rad_norm) < 1e-9
        if curr_rad_norm >= prev_rad_norm:
            return prev_rad_norm < target_rad_norm <= curr_rad_norm or \
                   abs(prev_rad_norm - target_rad_norm) < 1e-9
        else:
            return (prev_rad_norm < target_rad_norm < 2 * math.pi) or \
                   (0 <= target_rad_norm <= curr_rad_norm) or \
                   abs(prev_rad_norm - target_rad_norm) < 1e-9

    def run(self, params: SimulationParameters) -> SimulationData:
        # Convert parameters to float64 for precision
        dt = np.float64(params.dt)
        L = np.float64(params.sling_length)
        m = np.float64(params.sling_mass)
        x_h0 = np.float64(params.initial_hand_x)
        y_h0 = np.float64(params.initial_hand_y)
        omega_0 = np.float64(params.windup_speed_hz * 2 * math.pi)
        N_windup_req = params.windup_turns
        theta_ps_start_rad = np.float64(math.radians(params.power_stroke_begin_angle_deg))
        alpha_h_rad = np.float64(math.radians(params.hand_accel_direction_deg))
        a_h_mag = np.float64(params.hand_accel_rate)
        opening_duration = np.float64(params.opening_duration)
        theta_release_rad = np.float64(math.radians(params.release_angle_deg))
        t_post_release_duration = np.float64(params.sim_time_after_release)
        maximum_reach = np.float64(params.maximum_reach)

        # Validate inputs
        if dt <= 0 or L <= 0 or m <= 0 or opening_duration < 0 or maximum_reach < 0:
            raise ValueError("Time step, sling length, mass, opening duration, and maximum reach must be non-negative.")

        # Initialize state
        t_sum = np.float64(0.0)
        t_comp = np.float64(0.0)
        hand_pos_x = x_h0
        hand_pos_y = y_h0
        hand_vel_x = np.float64(0.0)
        hand_vel_y = np.float64(0.0)
        hand_accel_x = np.float64(0.0)
        hand_accel_y = np.float64(0.0)
        theta = np.float64(0.0)
        omega = omega_0
        alpha = np.float64(0.0)
        omega_opening = np.float64(0.0)
        phase = "WINDUP"
        windup_criteria_met = False
        power_stroke_triggered = False
        opening_triggered = False
        release_triggered = False
        t_power_stroke_start = np.float64(0.0)
        t_opening_start = np.float64(0.0)
        t_release = np.float64(0.0)
        reach_limit_hit = False
        prev_theta = np.float64(0.0)

        # Data storage
        times, hand_x_coords, hand_y_coords = [], [], []
        hand_vel_x_coords, hand_vel_y_coords, hand_speeds = [], [], []
        mass_x_coords, mass_y_coords = [], []
        mass_vel_x_coords, mass_vel_y_coords, mass_speeds = [], [], []
        mass_accel_x_coords, mass_accel_y_coords, mass_accel_mags = [], [], []
        angles_deg, ang_speeds, ang_accels, tensions = [], [], [], []
        phases_recorded = []

        step_count = 0
        while step_count < self.max_sim_steps:
            # Kahan summation for time
            y = dt - t_comp
            t = t_sum + y
            t_comp = (t - t_sum) - y
            t_sum = t

            curr_theta = theta % (2 * math.pi)

            # Phase Logic
            if phase == "WINDUP":
                hand_accel_x, hand_accel_y = np.float64(0.0), np.float64(0.0)
                hand_vel_x, hand_vel_y = np.float64(0.0), np.float64(0.0)
                hand_pos_x, hand_pos_y = x_h0, y_h0
                alpha = np.float64(0.0)
                if not windup_criteria_met and (theta / (2 * math.pi)) >= N_windup_req:
                    windup_criteria_met = True
                    logger.debug(f"Windup criteria met: t={t:.6f}, theta={theta:.6f}")
                if windup_criteria_met and self._is_angle_newly_at_or_past(prev_theta, curr_theta, theta_ps_start_rad):
                    phase = "POWER_STROKE"
                    power_stroke_triggered = True
                    t_power_stroke_start = t
                    hand_accel_x = a_h_mag * math.cos(alpha_h_rad)
                    hand_accel_y = a_h_mag * math.sin(alpha_h_rad)
                    logger.debug(f"Power Stroke Start: t={t:.6f}, hand_accel_x={hand_accel_x:.6f}, hand_pos_x={hand_pos_x:.6f}")

            elif phase == "POWER_STROKE":
                if not reach_limit_hit:
                    a_hx, a_hy = hand_accel_x, hand_accel_y
                    r_x = -L * math.cos(theta)
                    r_y = -L * math.sin(theta)
                    cos_psi = (a_hx * r_x + a_hy * r_y) / (L * a_h_mag) if a_h_mag > 0 else 0.0
                    sin_psi = math.sqrt(1 - cos_psi**2) if abs(cos_psi) <= 1 else 0.0
                    a_tangential = a_h_mag * sin_psi
                    alpha = a_tangential / L
                    if abs(alpha) < self.float_threshold:
                        alpha = np.float64(0.0)
                if self._is_angle_newly_at_or_past(prev_theta, curr_theta, theta_release_rad):
                    phase = "OPENING"
                    opening_triggered = True
                    t_opening_start = t
                    omega_opening = omega
                    alpha = np.float64(0.0)
                    logger.debug(f"Opening Start: t={t:.6f}, omega={omega_opening:.6f}")

            elif phase == "OPENING":
                alpha = np.float64(0.0)
                omega = omega_opening
                hand_accel_x = np.float64(0.0)
                hand_accel_y = np.float64(0.0)
                if t >= t_opening_start + opening_duration:
                    phase = "POST_RELEASE"
                    release_triggered = True
                    t_release = t
                    logger.debug(f"Release: t={t:.6f}, hand_pos_x={hand_pos_x:.6f}")

            elif phase == "POST_RELEASE":
                alpha = np.float64(0.0)
                hand_accel_x, hand_accel_y = np.float64(0.0), np.float64(0.0)
                if t >= t_release + t_post_release_duration:
                    break

            # Hand kinematics with Velocity Verlet
            if power_stroke_triggered and not release_triggered:
                hand_pos_x_new = hand_pos_x + hand_vel_x * dt + 0.5 * hand_accel_x * dt**2
                hand_pos_y_new = hand_pos_y + hand_vel_y * dt + 0.5 * hand_accel_y * dt**2
                hand_vel_x_new = hand_vel_x + hand_accel_x * dt
                hand_vel_y_new = hand_vel_y + hand_accel_y * dt
                if abs(hand_pos_x_new - x_h0) < self.float_threshold:
                    hand_pos_x_new = x_h0
                if abs(hand_vel_x_new) < self.float_threshold:
                    hand_vel_x_new = np.float64(0.0)
                hand_pos_x, hand_pos_y = hand_pos_x_new, hand_pos_y_new
                hand_vel_x, hand_vel_y = hand_vel_x_new, hand_vel_y_new

                # Enforce maximum reach
                if phase in ["POWER_STROKE", "OPENING"]:
                    hand_distance = math.sqrt((hand_pos_x - x_h0)**2 + (hand_pos_y - y_h0)**2)
                    if hand_distance >= maximum_reach:
                        hand_vel_x = np.float64(0.0)
                        hand_vel_y = np.float64(0.0)
                        hand_accel_x = np.float64(0.0)
                        hand_accel_y = np.float64(0.0)
                        alpha = np.float64(0.0)
                        reach_limit_hit = True
                        logger.debug(f"Maximum reach exceeded in {phase}: t={t:.6f}, hand_distance={hand_distance:.6f}")

            # Angular kinematics with Velocity Verlet
            if not release_triggered:
                theta_new = theta + omega * dt + 0.5 * alpha * dt**2
                omega_new = omega + alpha * dt
                if abs(alpha) < self.float_threshold:
                    alpha = np.float64(0.0)
                theta, omega = theta_new, omega_new

            # Mass kinematics
            if not release_triggered:
                mass_rel_x = L * math.cos(theta)
                mass_rel_y = L * math.sin(theta)
                mass_pos_x = hand_pos_x + mass_rel_x
                mass_pos_y = hand_pos_y + mass_rel_y
                mass_vel_rel_x = -L * omega * math.sin(theta)
                mass_vel_rel_y = L * omega * math.cos(theta)
                mass_vel_x = hand_vel_x + mass_vel_rel_x
                mass_vel_y = hand_vel_y + mass_vel_rel_y
                a_centripetal_x = -L * omega**2 * math.cos(theta)
                a_centripetal_y = -L * omega**2 * math.sin(theta)
                a_tangential_x = -L * alpha * math.sin(theta)
                a_tangential_y = L * alpha * math.cos(theta)
                mass_accel_x = hand_accel_x + a_centripetal_x + a_tangential_x
                mass_accel_y = hand_accel_y + a_centripetal_y + a_tangential_y
                tension = m * L * omega**2
            else:
                mass_accel_x, mass_accel_y = np.float64(0.0), np.float64(0.0)
                tension = np.float64(0.0)
                mass_pos_x += mass_vel_x * dt
                mass_pos_y += mass_vel_y * dt
                mass_vel_x, mass_vel_y = mass_vel_x, mass_vel_y  # Velocity remains constant post-release

            # Store data
            times.append(float(t))
            hand_x_coords.append(float(hand_pos_x))
            hand_y_coords.append(float(hand_pos_y))
            hand_vel_x_coords.append(float(hand_vel_x))
            hand_vel_y_coords.append(float(hand_vel_y))
            hand_speeds.append(float(math.sqrt(hand_vel_x**2 + hand_vel_y**2)))
            mass_x_coords.append(float(mass_pos_x))
            mass_y_coords.append(float(mass_pos_y))
            mass_vel_x_coords.append(float(mass_vel_x))
            mass_vel_y_coords.append(float(mass_vel_y))
            mass_speeds.append(float(math.sqrt(mass_vel_x**2 + mass_vel_y**2)))
            mass_accel_x_coords.append(float(mass_accel_x))
            mass_accel_y_coords.append(float(mass_accel_y))
            mass_accel_mags.append(float(math.sqrt(mass_accel_x**2 + mass_accel_y**2)))
            angles_deg.append(float(math.degrees(curr_theta)))
            ang_speeds.append(float(omega))
            ang_accels.append(float(alpha))
            tensions.append(float(tension))
            phases_recorded.append(phase)

            prev_theta = curr_theta
            step_count += 1

        if step_count >= self.max_sim_steps:
            raise RuntimeError("Maximum simulation steps reached.")

        logger.debug(f"Simulation ended: t={t:.6f}, steps={step_count}")
        return SimulationData(
            times=times, hand_x=hand_x_coords, hand_y=hand_y_coords,
            hand_vel_x=hand_vel_x_coords, hand_vel_y=hand_vel_y_coords, hand_speeds=hand_speeds,
            mass_x=mass_x_coords, mass_y=mass_y_coords,
            mass_vel_x=mass_vel_x_coords, mass_vel_y=mass_vel_y_coords, mass_speeds=mass_speeds,
            mass_accel_x=mass_accel_x_coords, mass_accel_y=mass_accel_y_coords, mass_accel_mags=mass_accel_mags,
            angle_deg=angles_deg, ang_speeds=ang_speeds, ang_accels=ang_accels,
            tension=tensions, phase=phases_recorded
        )

class SlingSimulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sling Kinematics Simulator")
        self.root.geometry("1600x1200")

        self.simulation_data = None
        self.speed_var = tk.StringVar(value="N/A m/s")
        self.hand_distance_var = tk.StringVar(value="N/A m")
        self.peak_hand_speed_var = tk.StringVar(value="N/A m/s")
        self.peak_mass_speed_var = tk.StringVar(value="N/A m/s")

        # Variables
        self.dt_var = tk.DoubleVar(value=0.0005)
        self.sling_length_var = tk.DoubleVar(value=0.75)
        self.sling_mass_var = tk.DoubleVar(value=0.1)
        self.initial_hand_x_var = tk.DoubleVar(value=0.0)
        self.initial_hand_y_var = tk.DoubleVar(value=0.0)
        self.windup_speed_hz_var = tk.DoubleVar(value=2.0)
        self.windup_turns_var = tk.IntVar(value=1)
        self.power_stroke_begin_angle_deg_var = tk.DoubleVar(value=180.0)
        self.hand_accel_direction_deg_var = tk.DoubleVar(value=90.0)
        self.hand_accel_rate_var = tk.DoubleVar(value=100.0)
        self.opening_duration_var = tk.DoubleVar(value=0.01)
        self.release_angle_deg_var = tk.DoubleVar(value=0.0)
        self.sim_time_after_release_var = tk.DoubleVar(value=0.5)
        self.maximum_reach_var = tk.DoubleVar(value=2.0)

        # UI Layout
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        inputs_frame = ttk.LabelFrame(main_frame, text="Simulation Parameters", padding="10")
        inputs_frame.grid(row=0, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N))

        stats_frame = ttk.LabelFrame(main_frame, text="Simulation Statistics", padding="10")
        stats_frame.grid(row=1, column=0, padx=5, pady=5, sticky=(tk.W, tk.E))

        buttons_frame = ttk.Frame(main_frame, borderwidth=2, relief="groove")
        buttons_frame.grid(row=2, column=0, padx=5, pady=0, sticky=(tk.W, tk.E))

        traj_frame = ttk.LabelFrame(main_frame, text="Trajectory Plot", padding="10")
        traj_frame.grid(row=3, column=0, padx=5, pady=5, sticky=(tk.W, tk.E))

        plot_frame = ttk.LabelFrame(main_frame, text="Simulation Plots", padding="10")
        plot_frame.grid(row=0, column=1, rowspan=4, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Set weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(0, weight=2)
        main_frame.rowconfigure(1, minsize=80, weight=0)
        main_frame.rowconfigure(2, minsize=50, weight=0)
        main_frame.rowconfigure(3, weight=1)

        # Input Widgets
        inputs_frame.columnconfigure(0, weight=1)
        inputs_frame.columnconfigure(1, weight=1)
        inputs_frame.columnconfigure(2, weight=1)
        inputs_frame.columnconfigure(3, weight=1)

        left_inputs = [
            ("Sling Length (m):", self.sling_length_var),
            ("Sling Mass (kg):", self.sling_mass_var),
            ("Initial Hand X (m):", self.initial_hand_x_var),
            ("Initial Hand Y (m):", self.initial_hand_y_var),
            ("Windup Speed (Hz):", self.windup_speed_hz_var)
        ]
        for row_idx, (label, var) in enumerate(left_inputs):
            ttk.Label(inputs_frame, text=label).grid(row=row_idx, column=0, sticky=tk.W, pady=2)
            ttk.Entry(inputs_frame, textvariable=var, width=10).grid(row=row_idx, column=1, sticky=tk.W, pady=2)

        right_inputs = [
            ("Windup Turns:", self.windup_turns_var),
            ("Hand Accel Rate (m/s²):", self.hand_accel_rate_var),
            ("Opening Duration (s):", self.opening_duration_var),
            ("Sim Time After Release (s):", self.sim_time_after_release_var),
            ("Maximum Reach (m):", self.maximum_reach_var)
        ]
        for row_idx, (label, var) in enumerate(right_inputs):
            ttk.Label(inputs_frame, text=label).grid(row=row_idx, column=2, sticky=tk.W, pady=2)
            ttk.Entry(inputs_frame, textvariable=var, width=10).grid(row=row_idx, column=3, sticky=tk.W, pady=2)

        slider_start_row = max(len(left_inputs), len(right_inputs))
        for idx, (label, var) in enumerate([
            ("P.Stroke Start Angle (°):", self.power_stroke_begin_angle_deg_var),
            ("Release Angle (°):", self.release_angle_deg_var),
            ("Hand Accel Dir (°):", self.hand_accel_direction_deg_var)
        ]):
            ttk.Label(inputs_frame, text=label).grid(row=slider_start_row + idx, column=0, sticky=tk.W, pady=2)
            ttk.Scale(inputs_frame, from_=0, to=359, variable=var, orient=tk.HORIZONTAL, length=150).grid(
                row=slider_start_row + idx, column=1, columnspan=3, sticky=tk.W, pady=2)
            ttk.Label(inputs_frame, textvariable=var, width=5).grid(row=slider_start_row + idx, column=4, sticky=tk.W)

        # Statistics Widgets
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        stats_frame.columnconfigure(2, weight=1)
        stats_frame.columnconfigure(3, weight=1)
        ttk.Label(stats_frame, text="Peak Hand Speed:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(stats_frame, textvariable=self.peak_hand_speed_var, width=15).grid(row=0, column=1, sticky=tk.W, pady=2)
        ttk.Label(stats_frame, text="Peak Mass Speed:").grid(row=0, column=2, sticky=tk.W, pady=2)
        ttk.Label(stats_frame, textvariable=self.peak_mass_speed_var, width=15).grid(row=0, column=3, sticky=tk.W, pady=2)
        ttk.Label(stats_frame, text="Mass Speed at Release:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(stats_frame, textvariable=self.speed_var, width=15).grid(row=1, column=1, sticky=tk.W, pady=2)
        ttk.Label(stats_frame, text="Hand Distance Moved:").grid(row=1, column=2, sticky=tk.W, pady=2)
        ttk.Label(stats_frame, textvariable=self.hand_distance_var, width=15).grid(row=1, column=3, sticky=tk.W, pady=2)

        # Buttons
        self.run_button = ttk.Button(buttons_frame, text="Run Simulation", command=self.run_simulation)
        self.run_button.pack(side=tk.LEFT, padx=5, pady=10)
        self.export_button = ttk.Button(buttons_frame, text="Export to CSV", command=self.export_to_csv, state=tk.DISABLED)
        self.export_button.pack(side=tk.LEFT, padx=5, pady=10)
        self.reset_button = ttk.Button(buttons_frame, text="Reset", command=self.reset_inputs)
        self.reset_button.pack(side=tk.LEFT, padx=5, pady=10)

        # Main Plotting Area
        self.fig = plt.Figure(figsize=(8, 8), dpi=100)
        self.ax_accel = self.fig.add_subplot(411)
        self.ax_velocity = self.fig.add_subplot(412)
        self.ax_ang_speed = self.fig.add_subplot(413)
        self.ax_tension = self.fig.add_subplot(414)
        self.fig.tight_layout(pad=2.0)

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas.draw()

        # Trajectory Plot
        self.traj_fig = plt.Figure(figsize=(6, 6), dpi=100)
        self.traj_ax = self.traj_fig.add_subplot(111)
        self.traj_fig.tight_layout(pad=2.0)

        self.traj_canvas = FigureCanvasTkAgg(self.traj_fig, master=traj_frame)
        self.traj_canvas_widget = self.traj_canvas.get_tk_widget()
        self.traj_canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.traj_canvas.draw()

    def reset_inputs(self):
        self.sling_length_var.set(0.75)
        self.sling_mass_var.set(0.1)
        self.initial_hand_x_var.set(0.0)
        self.initial_hand_y_var.set(0.0)
        self.windup_speed_hz_var.set(2.0)
        self.windup_turns_var.set(1)
        self.hand_accel_rate_var.set(100.0)
        self.opening_duration_var.set(0.01)
        self.sim_time_after_release_var.set(0.5)
        self.power_stroke_begin_angle_deg_var.set(180.0)
        self.hand_accel_direction_deg_var.set(90.0)
        self.release_angle_deg_var.set(0.0)
        self.dt_var.set(0.0005)
        self.maximum_reach_var.set(2.0)
        self.peak_hand_speed_var.set("N/A m/s")
        self.peak_mass_speed_var.set("N/A m/s")
        self.speed_var.set("N/A m/s")
        self.hand_distance_var.set("N/A m")

    def run_simulation(self):
        try:
            # Gather parameters
            params = SimulationParameters(
                dt=self.dt_var.get(),
                sling_length=self.sling_length_var.get(),
                sling_mass=self.sling_mass_var.get(),
                initial_hand_x=self.initial_hand_x_var.get(),
                initial_hand_y=self.initial_hand_y_var.get(),
                windup_speed_hz=self.windup_speed_hz_var.get(),
                windup_turns=self.windup_turns_var.get(),
                power_stroke_begin_angle_deg=self.power_stroke_begin_angle_deg_var.get(),
                hand_accel_direction_deg=self.hand_accel_direction_deg_var.get(),
                hand_accel_rate=self.hand_accel_rate_var.get(),
                opening_duration=self.opening_duration_var.get(),
                release_angle_deg=self.release_angle_deg_var.get(),
                sim_time_after_release=self.sim_time_after_release_var.get(),
                maximum_reach=self.maximum_reach_var.get()
            )

            # Run simulation
            simulator = SlingSimulator()
            sim_data = simulator.run(params)

            # Calculate statistics
            hand_distance = math.sqrt((sim_data.hand_x[-1] - sim_data.hand_x[0])**2 + 
                                    (sim_data.hand_y[-1] - sim_data.hand_y[0])**2)
            peak_hand_speed = max(sim_data.hand_speeds) if sim_data.hand_speeds else 0.0
            peak_mass_speed = max(sim_data.mass_speeds) if sim_data.mass_speeds else 0.0
            release_idx = next((i for i, p in enumerate(sim_data.phase) if p == "POST_RELEASE"), len(sim_data.times) - 1)
            if release_idx > 0:
                speed_at_release = sim_data.mass_speeds[release_idx - 1]
            else:
                speed_at_release = 0.0

            # Update GUI
            self.hand_distance_var.set(f"{hand_distance:.2f} m")
            self.peak_hand_speed_var.set(f"{peak_hand_speed:.2f} m/s")
            self.peak_mass_speed_var.set(f"{peak_mass_speed:.2f} m/s")
            self.speed_var.set(f"{speed_at_release:.2f} m/s")

            # Store data in dictionary format for compatibility
            self.simulation_data = {
                "times": sim_data.times, "hand_x": sim_data.hand_x, "hand_y": sim_data.hand_y,
                "hand_vel_x": sim_data.hand_vel_x, "hand_vel_y": sim_data.hand_vel_y,
                "mass_x": sim_data.mass_x, "mass_y": sim_data.mass_y,
                "mass_vel_x": sim_data.mass_vel_x, "mass_vel_y": sim_data.mass_vel_y,
                "mass_speed": sim_data.mass_speeds, "mass_accel_x": sim_data.mass_accel_x,
                "mass_accel_y": sim_data.mass_accel_y, "mass_accel_mag": sim_data.mass_accel_mags,
                "angle_deg": sim_data.angle_deg, "ang_speed": sim_data.ang_speeds,
                "ang_accel": sim_data.ang_accels, "tension": sim_data.tension, "phase": sim_data.phase
            }

            self.plot_data()
            self.export_button.config(state=tk.NORMAL)

        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except RuntimeError as e:
            messagebox.showwarning("Simulation Limit", str(e))
        except tk.TclError as e:
            messagebox.showerror("Input Error", f"Invalid input: {e}")

    def plot_data(self):
        if not self.simulation_data:
            return

        d = self.simulation_data
        times = np.array(d["times"])

        # Clear all axes
        self.ax_accel.clear()
        self.ax_velocity.clear()
        self.ax_ang_speed.clear()
        self.ax_tension.clear()
        for ax in self.ax_tension.figure.axes:
            if ax is not self.ax_tension and ax is not self.ax_accel and ax is not self.ax_velocity and ax is not self.ax_ang_speed:
                ax.remove()

        # Set x-axis limits
        t_max = times[-1]
        for ax in [self.ax_accel, self.ax_velocity, self.ax_ang_speed, self.ax_tension]:
            ax.set_xlim(0, t_max)

        # Plot Acceleration
        self.ax_accel.plot(times, d["mass_accel_x"], label="Accel X (m/s²)", color="purple")
        self.ax_accel.plot(times, d["mass_accel_y"], label="Accel Y (m/s²)", color="brown")
        self.ax_accel.set_xlabel("Time (s)")
        self.ax_accel.set_ylabel("Acceleration (m/s²)")
        self.ax_accel.set_title("Sling Bullet Acceleration Components")
        self.ax_accel.legend(loc='center left', bbox_to_anchor=(0, 0.5), fontsize='small')
        self.ax_accel.grid(True)

        # Plot Velocity
        self.ax_velocity.plot(times, d["mass_vel_x"], label="Vel X (m/s)", color="blue")
        self.ax_velocity.plot(times, d["mass_vel_y"], label="Vel Y (m/s)", color="green")
        self.ax_velocity.set_xlabel("Time (s)")
        self.ax_velocity.set_ylabel("Velocity (m/s)")
        self.ax_velocity.set_title("Sling Velocity Components")
        self.ax_velocity.legend(loc='center left', bbox_to_anchor=(0, 0.5), fontsize='small')
        self.ax_velocity.grid(True)

        # Plot Angular Speed
        self.ax_ang_speed.plot(times, np.array(d["ang_speed"]) / (2 * math.pi), label="Angular Speed (rps)", color="magenta")
        self.ax_ang_speed.set_xlabel("Time (s)")
        self.ax_ang_speed.set_ylabel("Angular Speed (rps)")
        self.ax_ang_speed.set_title("Sling Angular Speed")
        self.ax_ang_speed.set_ylim(bottom=0)
        self.ax_ang_speed.legend(loc='center left', bbox_to_anchor=(0, 0.5), fontsize='small')
        self.ax_ang_speed.grid(True)

        # Plot Tension and Angular Acceleration
        self.ax_tension.plot(times, d["tension"], label="Tension (N)", color="navy")
        self.ax_tension.set_xlabel("Time (s)")
        self.ax_tension.set_ylabel("Tension (N)", color="navy")
        self.ax_tension.set_title("Sling Tension and Angular Acceleration")
        self.ax_tension.tick_params(axis='y', labelcolor="navy")
        self.ax_tension.grid(True)

        ax_ang_accel = self.ax_tension.twinx()
        ax_ang_accel.plot(times, np.array(d["ang_accel"]) / (2 * math.pi), label="Angular Accel (rps/s)", color="red")
        ax_ang_accel.set_ylabel("Angular Accel (rps/s)", color="red")
        ax_ang_accel.tick_params(axis='y', labelcolor="red")

        lines1, labels1 = self.ax_tension.get_legend_handles_labels()
        lines2, labels2 = ax_ang_accel.get_legend_handles_labels()
        self.ax_tension.legend(lines1 + lines2, labels1 + labels2, loc='center left', bbox_to_anchor=(0, 0.5), fontsize='small')

        # Trajectory Plot
        self.traj_ax.clear()
        if self.traj_ax.get_legend():
            self.traj_ax.get_legend().remove()

        self.traj_ax.axis('equal')
        self.traj_ax.plot(d["mass_x"], d["mass_y"], label="Bullet Trajectory", color="black")
        self.traj_ax.plot(d["hand_x"], d["hand_y"], label="Hand Trajectory", color="orange", linestyle=":")
        if d["mass_x"]:
            self.traj_ax.plot(d["mass_x"][0], d["mass_y"][0], 'go', label="Bullet Start")
            self.traj_ax.plot(d["mass_x"][-1], d["mass_y"][-1], 'ro', label="Bullet End")
            self.traj_ax.plot([d["mass_x"][0], d["mass_x"][-1]], [d["mass_y"][0], d["mass_y"][-1]], 'k--', label="Start to End")
        if d["hand_x"]:
            self.traj_ax.plot(d["hand_x"][0], d["hand_y"][0], 'bx', label="Hand Start")
        self.traj_ax.set_xlabel("X Position (m)")
        self.traj_ax.set_ylabel("Y Position (m)")
        self.traj_ax.set_title("Hand and Sling Bullet Trajectory")
        self.traj_ax.autoscale(False)
        self.traj_ax.set_xlim(-15, 15)
        self.traj_ax.set_ylim(-15, 15)
        self.traj_ax.set_xticks(np.arange(-15, 16, 3))
        self.traj_ax.set_yticks(np.arange(-15, 16, 3))
        self.traj_ax.legend(fontsize='small')
        self.traj_ax.grid(True)
        self.traj_ax.text(0.05, 0.10, self.speed_var.get(), transform=self.traj_ax.transAxes, fontsize=20, fontweight='bold', bbox=dict(facecolor='white', alpha=0.7, edgecolor='black'))
        self.traj_ax.text(0.05, 0.02, self.hand_distance_var.get(), transform=self.traj_ax.transAxes, fontsize=20, fontweight='bold', bbox=dict(facecolor='white', alpha=0.7, edgecolor='black'))

        self.fig.tight_layout(pad=2.0)
        self.traj_fig.tight_layout(pad=2.0)
        self.canvas.draw()
        self.traj_canvas.draw()

    def export_to_csv(self):
        if not self.simulation_data:
            messagebox.showinfo("No Data", "Please run the simulation first.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save Simulation Data"
        )
        if not filepath:
            return

        try:
            d = self.simulation_data
            with open(filepath, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    "Time (s)", "Hand X (m)", "Hand Y (m)", 
                    "Hand Vel X (m/s)", "Hand Vel Y (m/s)",
                    "Mass X (m)", "Mass Y (m)", 
                    "Mass Vel X (m/s)", "Mass Vel Y (m/s)", "Mass Speed (m/s)",
                    "Mass Accel X (m/s^2)", "Mass Accel Y (m/s^2)", "Mass Accel Mag (m/s^2)",
                    "Angle (deg)", "Ang Speed (rps)", "Ang Accel (rps/s)",
                    "Tension (N)", "Phase"
                ])
                for i in range(len(d["times"])):
                    writer.writerow([
                        d["times"][i], d["hand_x"][i], d["hand_y"][i],
                        d["hand_vel_x"][i], d["hand_vel_y"][i],
                        d["mass_x"][i], d["mass_y"][i],
                        d["mass_vel_x"][i], d["mass_vel_y"][i], d["mass_speed"][i],
                        d["mass_accel_x"][i], d["mass_accel_y"][i], d["mass_accel_mag"][i],
                        d["angle_deg"][i], d["ang_speed"][i] / (2 * math.pi), d["ang_accel"][i] / (2 * math.pi),
                        d["tension"][i], d["phase"][i]
                    ])
            messagebox.showinfo("Export Successful", f"Data exported to {filepath}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Could not write to file: {e}")

if __name__ == '__main__':
    root = tk.Tk()
    app = SlingSimulatorApp(root)
    root.mainloop()
