import subprocess

from fabric.utils.helpers import exec_shell_command_async
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label

import config.data as data
import modules.icons as icons
from utils.hardware_profile import get_hardware_profile


class Systemprofiles(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="systemprofiles",
            orientation="h" if not data.VERTICAL else "v",
            spacing=3,
        )

        if data.BAR_THEME == "Dense" or data.BAR_THEME == "Edge":
            self.add_style_class("invert")

        self.bat_save = None
        self.bat_balanced = None
        self.bat_perf = None

        # Get hardware profile for optimized tooltips
        self.hw_profile = get_hardware_profile()

        children = []

        try:
            result = subprocess.run(
                ["powerprofilesctl", "list"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            available_profiles = result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            available_profiles = ""

        # Generate tooltips based on hardware profile
        save_tooltip = self._get_power_saver_tooltip()
        balanced_tooltip = self._get_balanced_tooltip()
        perf_tooltip = self._get_performance_tooltip()

        if "power-saver" in available_profiles:
            self.bat_save = Button(
                name="battery-save",
                child=Label(name="battery-save-label", markup=icons.power_saving),
                on_clicked=lambda *_: self.set_power_mode("power-saver"),
                tooltip_text=save_tooltip,
            )
            children.append(self.bat_save)

        if "balanced" in available_profiles:
            self.bat_balanced = Button(
                name="battery-balanced",
                child=Label(name="battery-balanced-label", markup=icons.power_balanced),
                on_clicked=lambda *_: self.set_power_mode("balanced"),
                tooltip_text=balanced_tooltip,
            )
            children.append(self.bat_balanced)

        if "performance" in available_profiles:
            self.bat_perf = Button(
                name="battery-performance",
                child=Label(
                    name="battery-performance-label", markup=icons.power_performance
                ),
                on_clicked=lambda *_: self.set_power_mode("performance"),
                tooltip_text=perf_tooltip,
            )
            children.append(self.bat_perf)

        # Group the mode buttons into a container.
        if children:
            self.add(
                Box(
                    name="power-mode-switcher",
                    orientation="h" if not data.VERTICAL else "v",
                    spacing=4,
                    children=children,
                )
            )

        if data.BAR_COMPONENTS_VISIBILITY.get("sysprofiles", False):
            self.get_current_power_mode()
            self.hide_timer = None
            self.hover_counter = 0
        # self.set_power_mode("balanced")

    def get_current_power_mode(self):
        try:
            # Run the command to get the current power mode
            result = subprocess.run(
                ["powerprofilesctl", "get"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )

            # Get the output and strip unnecessary whitespace
            output = result.stdout.strip()

            # Validate the output
            if output in ["power-saver", "balanced", "performance"]:
                self.current_mode = output
            else:
                self.current_mode = "balanced"

            # Update button styles based on the current mode
            self.update_button_styles()

        except subprocess.CalledProcessError as err:
            print(f"Command failed: {err}")
            self.current_mode = "balanced"

        except Exception as err:
            print(f"Error retrieving current power mode: {err}")
            self.current_mode = "balanced"

    def set_power_mode(self, mode):
        """
        Switches power mode by running the corresponding auto-cpufreq command.
        mode: one of 'powersave', 'balanced', or 'performance'
        """
        commands = {
            "power-saver": "powerprofilesctl set power-saver",
            "balanced": "powerprofilesctl set balanced",
            "performance": "powerprofilesctl set performance",
        }
        if mode in commands:
            try:
                exec_shell_command_async(commands[mode])
                self.current_mode = mode
                self.update_button_styles()
            except Exception as err:
                # Optionally, handle errors or display a notification.
                print(f"Error setting power mode: {err}")

    def update_button_styles(self):
        """
        Optionally updates button styles to reflect the current mode.
        Adjust the styling method based on your toolkit's capabilities.
        """
        if self.bat_save:
            self.bat_save.remove_style_class("active")
        if self.bat_balanced:
            self.bat_balanced.remove_style_class("active")
        if self.bat_perf:
            self.bat_perf.remove_style_class("active")

        if self.current_mode == "power-saver" and self.bat_save:
            self.bat_save.add_style_class("active")
        elif self.current_mode == "balanced" and self.bat_balanced:
            self.bat_balanced.add_style_class("active")
        elif self.current_mode == "performance" and self.bat_perf:
            self.bat_perf.add_style_class("active")

    def _get_power_saver_tooltip(self) -> str:
        """Generate tooltip for power saver mode based on hardware profile."""
        if self.hw_profile.is_gaming_laptop:
            return "Power saver - May limit GPU/CPU performance"
        return "Power saving mode"

    def _get_balanced_tooltip(self) -> str:
        """Generate tooltip for balanced mode based on hardware profile."""
        if self.hw_profile.is_lenovo_loq:
            return "Balanced - Recommended for battery (LOQ)"
        if self.hw_profile.is_gaming_laptop:
            return "Balanced - Good for battery use"
        return "Balanced mode"

    def _get_performance_tooltip(self) -> str:
        """Generate tooltip for performance mode based on hardware profile."""
        if self.hw_profile.is_lenovo_loq:
            return "Performance - Recommended when plugged in (LOQ)"
        if self.hw_profile.is_gaming_laptop:
            return "Performance - Full GPU/CPU power (use when plugged in)"
        return "Performance mode"
