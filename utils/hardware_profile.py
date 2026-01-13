"""Hardware profile detection and configuration for gaming laptops.

This module provides detection logic for specific laptop models (e.g., Lenovo LOQ)
and provides hardware-optimized power management recommendations.
"""

import os
import subprocess
from typing import Optional

try:
    from loguru import logger
except ImportError:
    # Fallback logger for testing/standalone use
    import logging
    logger = logging.getLogger(__name__)

# Hardware profile types
PROFILE_GENERIC = "generic"
PROFILE_LENOVO_LOQ = "lenovo_loq"
PROFILE_GAMING_LAPTOP = "gaming_laptop"

# Timeout constants (in seconds)
GAMING_SUSPEND_TIMEOUT = 3600   # 60 minutes for gaming laptops
GENERIC_SUSPEND_TIMEOUT = 1800  # 30 minutes for generic laptops
GAMING_SCREEN_OFF_TIMEOUT = 600  # 10 minutes for gaming laptops
GENERIC_SCREEN_OFF_TIMEOUT = 330  # 5.5 minutes for generic laptops


class HardwareProfile:
    """Represents detected hardware profile with optimized settings."""

    def __init__(self):
        self._profile_type: str = PROFILE_GENERIC
        self._vendor: str = ""
        self._product_name: str = ""
        self._has_nvidia: bool = False
        self._has_dgpu: bool = False
        self._detect_hardware()

    def _read_dmi_info(self, field: str) -> str:
        """Read DMI information from sysfs."""
        path = f"/sys/class/dmi/id/{field}"
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    return f.read().strip()
        except (IOError, PermissionError) as e:
            logger.debug(f"Could not read {path}: {e}")
        return ""

    def _detect_nvidia_gpu(self) -> bool:
        """Check if NVIDIA GPU is present."""
        try:
            # Check for NVIDIA GPU via lspci
            result = subprocess.run(
                ["lspci"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if "NVIDIA" in result.stdout:
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Fallback: Check for nvidia driver module
        try:
            result = subprocess.run(
                ["lsmod"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if "nvidia" in result.stdout.lower():
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return False

    def _detect_dgpu(self) -> bool:
        """Check if a discrete GPU is present (NVIDIA or AMD).
        
        Detects discrete GPUs by looking for NVIDIA or AMD Radeon/ATI cards
        in lspci output. Excludes integrated AMD APUs.
        """
        try:
            result = subprocess.run(
                ["lspci"],
                capture_output=True,
                text=True,
                timeout=5
            )
            output = result.stdout.upper()
            lines = output.split('\n')
            
            for line in lines:
                # Only check VGA, 3D controller, or Display controller lines
                if not any(ctrl in line for ctrl in ["VGA", "3D", "DISPLAY"]):
                    continue
                    
                # NVIDIA discrete GPU detection
                if "NVIDIA" in line:
                    return True
                    
                # AMD discrete GPU detection (Radeon cards)
                # Check for Radeon branding which indicates discrete GPU
                # ATI was acquired by AMD, so check for both
                if "RADEON" in line:
                    return True
                if "ATI" in line and "RADEON" in line:
                    return True
                    
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return False

    def _detect_hardware(self):
        """Detect hardware and set appropriate profile."""
        # Read system information
        self._vendor = self._read_dmi_info("sys_vendor")
        self._product_name = self._read_dmi_info("product_name")
        product_family = self._read_dmi_info("product_family")

        # Detect GPU capabilities
        self._has_nvidia = self._detect_nvidia_gpu()
        self._has_dgpu = self._detect_dgpu()

        # Log detected hardware
        logger.info(f"Hardware detected: {self._vendor} {self._product_name}")
        logger.info(f"NVIDIA GPU: {self._has_nvidia}, Discrete GPU: {self._has_dgpu}")

        # Determine profile type
        vendor_lower = self._vendor.lower()
        product_lower = self._product_name.lower()
        family_lower = product_family.lower()

        # Lenovo LOQ detection
        if "lenovo" in vendor_lower:
            if "loq" in product_lower or "loq" in family_lower:
                self._profile_type = PROFILE_LENOVO_LOQ
                logger.info("Detected Lenovo LOQ gaming laptop")
                return

            # Other Lenovo gaming laptops (Legion, IdeaPad Gaming)
            if any(name in product_lower for name in ["legion", "ideapad gaming"]):
                self._profile_type = PROFILE_GAMING_LAPTOP
                logger.info("Detected Lenovo gaming laptop")
                return

        # Generic gaming laptop detection (has dGPU)
        if self._has_dgpu:
            self._profile_type = PROFILE_GAMING_LAPTOP
            logger.info("Detected gaming laptop with discrete GPU")
            return

        self._profile_type = PROFILE_GENERIC
        logger.info("Using generic hardware profile")

    @property
    def profile_type(self) -> str:
        """Return the detected profile type."""
        return self._profile_type

    @property
    def vendor(self) -> str:
        """Return the system vendor."""
        return self._vendor

    @property
    def product_name(self) -> str:
        """Return the product name."""
        return self._product_name

    @property
    def has_nvidia(self) -> bool:
        """Return True if NVIDIA GPU is detected."""
        return self._has_nvidia

    @property
    def has_discrete_gpu(self) -> bool:
        """Return True if a discrete GPU is detected."""
        return self._has_dgpu

    @property
    def is_gaming_laptop(self) -> bool:
        """Return True if this is a gaming laptop profile."""
        return self._profile_type in [PROFILE_LENOVO_LOQ, PROFILE_GAMING_LAPTOP]

    @property
    def is_lenovo_loq(self) -> bool:
        """Return True if this is a Lenovo LOQ laptop."""
        return self._profile_type == PROFILE_LENOVO_LOQ

    def get_recommended_ac_power_profile(self) -> str:
        """Get recommended power profile when on AC power.

        For gaming laptops, returns 'performance' to avoid throttling.
        For generic laptops, returns 'balanced'.
        """
        if self.is_gaming_laptop:
            return "performance"
        return "balanced"

    def get_recommended_battery_power_profile(self) -> str:
        """Get recommended power profile when on battery.

        Returns 'balanced' for gaming laptops to maintain usability,
        or 'power-saver' for generic laptops.
        """
        if self.is_gaming_laptop:
            return "balanced"
        return "power-saver"

    def get_idle_suspend_timeout(self) -> int:
        """Get recommended idle timeout before suspend (in seconds).

        Gaming laptops get longer timeouts to avoid interrupting downloads,
        updates, or background tasks.
        """
        if self.is_gaming_laptop:
            return GAMING_SUSPEND_TIMEOUT
        return GENERIC_SUSPEND_TIMEOUT

    def get_screen_off_timeout(self) -> int:
        """Get recommended screen off timeout (in seconds).

        Gaming laptops get longer timeouts.
        """
        if self.is_gaming_laptop:
            return GAMING_SCREEN_OFF_TIMEOUT
        return GENERIC_SCREEN_OFF_TIMEOUT

    def should_use_prime_run(self) -> bool:
        """Return True if prime-run should be used for GPU workloads.

        This is relevant for NVIDIA Optimus laptops using hybrid graphics.
        """
        return self._has_nvidia and self.is_gaming_laptop

    def get_nvidia_prime_command(self) -> str:
        """Get the command prefix for running apps on NVIDIA GPU.

        Returns 'prime-run' for Optimus setups, empty string otherwise.
        """
        if self.should_use_prime_run():
            return "prime-run"
        return ""


# Singleton instance
_hardware_profile: Optional[HardwareProfile] = None


def get_hardware_profile() -> HardwareProfile:
    """Get the singleton hardware profile instance."""
    global _hardware_profile
    if _hardware_profile is None:
        _hardware_profile = HardwareProfile()
    return _hardware_profile


def is_lenovo_loq() -> bool:
    """Convenience function to check if running on Lenovo LOQ."""
    return get_hardware_profile().is_lenovo_loq


def is_gaming_laptop() -> bool:
    """Convenience function to check if running on a gaming laptop."""
    return get_hardware_profile().is_gaming_laptop


def get_recommended_power_profile(on_battery: bool) -> str:
    """Get recommended power profile based on power state.

    Args:
        on_battery: True if running on battery power.

    Returns:
        Recommended power profile name ('performance', 'balanced', or 'power-saver').
    """
    profile = get_hardware_profile()
    if on_battery:
        return profile.get_recommended_battery_power_profile()
    return profile.get_recommended_ac_power_profile()
