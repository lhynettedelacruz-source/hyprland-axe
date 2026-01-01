# Lenovo LOQ Gaming Laptop Optimization Guide

This document provides guidance for running Ax-Shell on **Lenovo LOQ** gaming laptops (and similar gaming laptops with NVIDIA Optimus hybrid graphics).

## Overview

Lenovo LOQ laptops are gaming machines designed for high-performance workloads. Ax-Shell now includes hardware detection that automatically optimizes power management for these systems.

### What Ax-Shell Does NOT Do

- **No TLP**: Ax-Shell does **not** install or configure TLP. It uses `power-profiles-daemon` (PPD), which integrates better with modern GNOME/Wayland desktops and gaming laptops.
- **No CPU Governor Override**: The shell respects your system's CPU frequency scaling decisions.
- **No GPU Power Caps**: Ax-Shell never artificially limits your GPU performance.

### What Ax-Shell Provides

- **Power Profile Switching**: Quick access to `power-saver`, `balanced`, and `performance` modes via the system tray.
- **Hardware-Aware Tooltips**: The power profile buttons show recommendations specific to your hardware.
- **Brightness Control**: Screen brightness adjustment via `brightnessctl` or `ddcutil`.

## Understanding Lenovo LOQ Power Management

### Fn+Q and Platform Profiles (CRITICAL)

Lenovo LOQ laptops use **extended platform profiles** controlled by the **Fn+Q** key, not just standard ACPI profiles. This is firmware-level control that **overrides AC power state**.

**Important**: Being plugged in (AC) does NOT guarantee full power. You must use **Fn+Q to select Performance mode**.

| Fn+Q Mode | `platform_profile` Value | GPU Power | Description |
|-----------|-------------------------|-----------|-------------|
| **Quiet** | `low-power` | Limited | Max efficiency, strict power limits |
| **Auto/Balanced** | `balanced` | Moderate | Firmware-managed balance |
| **Performance** | `balanced-performance` | **Full** | High performance, GPU unlocked |
| **Custom** | `custom` | Varies | OEM-controlled / vendor logic |

To check your current platform profile:
```bash
cat /sys/firmware/acpi/platform_profile
```

To see available profiles:
```bash
cat /sys/firmware/acpi/platform_profile_choices
```

### Why 30W GPU Power Happens

If your GPU is limited to ~30W even on AC power, it's because:
- `platform_profile` is NOT set to `balanced-performance`
- Lenovo firmware caps GPU power in other modes
- **Solution**: Press **Fn+Q** until you reach Performance mode

**AC power ≠ Full Power on LOQ. Fn+Q Performance mode = Full Power.**

## Recommended Configuration for Lenovo LOQ

### Power Profiles

| Scenario | Recommended Profile | Fn+Q Mode | Why |
|----------|-------------------|-----------|-----|
| **Gaming / Heavy Workloads** | Performance | **Performance** | Full CPU turbo + GPU boost (135W) |
| **Plugged In (General Use)** | Performance or Balanced | Performance | Avoid unnecessary throttling |
| **On Battery** | Balanced | Balanced | Good compromise between battery life and usability |
| **Maximum Battery Life** | Power Saver | Quiet | Only when needed; may limit performance significantly |

### NVIDIA Optimus / Hybrid Graphics

For NVIDIA Optimus laptops, use `prime-run` to run applications on the discrete GPU:

```bash
# Run a game on NVIDIA GPU
prime-run steam

# Run any application on NVIDIA GPU
prime-run ./your-application
```

**Note**: Most modern games and applications should automatically use the correct GPU. Use `prime-run` when you need to force discrete GPU usage.

### CPU Governor Recommendations

For modern Intel CPUs (12th Gen Alder Lake, 13th Gen Raptor Lake) with hybrid architecture (P-cores and E-cores), or AMD Ryzen processors:

- **Performance Mode**: The system will use `performance` governor, maximizing clock speeds
- **Balanced Mode**: Uses `schedutil` or similar, balancing power and performance
- **Power Saver**: Reduces frequencies to save power

The Linux kernel's scheduler automatically handles workload distribution across CPU cores (including P-core/E-core scheduling on Intel hybrid CPUs).

### Avoiding Conflicts

If you have TLP installed separately, you may want to disable it to avoid conflicts with `power-profiles-daemon`:

```bash
# Disable TLP (if installed)
sudo systemctl disable --now tlp.service
sudo systemctl mask tlp.service

# Ensure power-profiles-daemon is running
sudo systemctl enable --now power-profiles-daemon.service
```

## Hypridle Configuration

The default `hypridle.conf` included with Ax-Shell is configured for general laptops. For gaming laptops, you may want to increase the timeouts to avoid interruptions during downloads or background tasks.

### Default Timeouts (General Laptops)
- Dim screen: 2.5 minutes
- Lock screen: 5 minutes
- Screen off: 5.5 minutes
- Suspend: 30 minutes

### Recommended for Gaming Laptops
Edit `~/.config/Ax-Shell/config/hypr/hypridle.conf`:

```conf
general {
    lock_cmd = pidof hyprlock || hyprlock
    before_sleep_cmd = loginctl lock-session
    after_sleep_cmd = hyprctl dispatch dpms on
}

# Dim screen after 5 minutes
listener {
    timeout = 300
    on-timeout = brightnessctl -s set 10
    on-resume = brightnessctl -r
}

# Lock screen after 10 minutes
listener {
    timeout = 600
    on-timeout = loginctl lock-session
}

# Screen off after 15 minutes
listener {
    timeout = 900
    on-timeout = hyprctl dispatch dpms off
    on-resume = hyprctl dispatch dpms on
}

# Suspend after 60 minutes (or disable for gaming)
listener {
    timeout = 3600
    on-timeout = systemctl suspend
}
```

### Disabling Auto-Suspend When Gaming

To prevent the system from suspending during gaming sessions, you can use `systemd-inhibit`:

```bash
# Run a game with suspend inhibited
systemd-inhibit --what=idle:sleep --who="Gaming Session" --why="Playing a game" steam
```

Or use the gamemode integration if you have `gamemode` installed.

## Troubleshooting

### Performance Issues on AC Power

**First, check Fn+Q platform profile** (most common cause on LOQ):
```bash
cat /sys/firmware/acpi/platform_profile
# Should show "balanced-performance" for full power
```

If not `balanced-performance`, press **Fn+Q** until you reach Performance mode.

Then check power-profiles-daemon:

1. Check your current power profile:
   ```bash
   powerprofilesctl get
   ```

2. Ensure you're on Performance mode when plugged in:
   ```bash
   powerprofilesctl set performance
   ```

3. Verify no conflicting power management services:
   ```bash
   systemctl status tlp.service  # Should be inactive/disabled
   systemctl status power-profiles-daemon.service  # Should be active
   ```

### GPU Limited to 30W (LOQ-Specific)

This is the most common performance issue on Lenovo LOQ:

1. **Root cause**: Fn+Q is not set to Performance mode
2. **Solution**: Press Fn+Q until `platform_profile` shows `balanced-performance`
3. **Verify**:
   ```bash
   cat /sys/firmware/acpi/platform_profile
   # Must be "balanced-performance" for full 135W GPU power
   ```

**Remember**: AC power alone does NOT unlock full GPU power on LOQ. The firmware requires Performance mode via Fn+Q.

### GPU Not Being Used

1. Check if NVIDIA driver is loaded:
   ```bash
   lsmod | grep nvidia
   ```

2. Verify PRIME is working:
   ```bash
   prime-run glxinfo | grep "OpenGL renderer"
   ```

3. For Wayland, ensure you have the correct environment variables in your Hyprland config if needed.

### Battery Draining Too Fast

1. Switch to Balanced or Power Saver mode
2. Check for runaway processes:
   ```bash
   nvtop  # For GPU usage
   htop   # For CPU usage
   ```

3. Ensure discrete GPU isn't being used unnecessarily (hybrid mode should use integrated GPU for desktop)

## Hardware Detection

Ax-Shell automatically detects Lenovo LOQ laptops by reading system DMI information. When detected, it:

1. Shows hardware-specific tooltips on power profile buttons
2. Logs detection in the console for debugging

To verify detection, check the Ax-Shell logs or run:

```bash
cat /sys/class/dmi/id/product_name
cat /sys/class/dmi/id/sys_vendor
```

## Additional Resources

- [Arch Wiki - Lenovo LOQ](https://wiki.archlinux.org/title/Laptop/Lenovo)
- [Arch Wiki - NVIDIA Optimus](https://wiki.archlinux.org/title/NVIDIA_Optimus)
- [Arch Wiki - Power Management](https://wiki.archlinux.org/title/Power_management)
- [Hyprland Wiki](https://wiki.hyprland.org/)
