#!/usr/bin/env python3
"""
Raspberry Pi Internet Connectivity Monitor
Continuously tests internet connectivity and controls LED status
"""

import subprocess
import time
import logging
import os
from datetime import datetime

# ===== CONFIGURATION =====
LED_TYPE = "sysfs"              # Use "sysfs" for on-board LEDs or "gpio" for external
LED_PATH = "/sys/class/leds/ACT"  # Path to ACT (green) LED
PING_TARGET = "8.8.8.8"         # Google DNS - reliable server to ping
PING_INTERVAL = 10              # Check connectivity every 10 seconds
CONSECUTIVE_FAILURES = 3        # Require 3 failed pings before marking as DOWN
LOG_FILE = "/var/log/connectivity_monitor.log"
DEBUG = True                     # Set to True for verbose output on every test

# ===== LOGGING SETUP =====
log_level = logging.DEBUG if DEBUG else logging.INFO

logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===== LED CONTROL CLASS =====
class LED:
    """Control LED via sysfs interface"""
    
    def __init__(self, led_path):
        self.led_path = led_path
        self.brightness_file = f"{led_path}/brightness"
        self.trigger_file = f"{led_path}/trigger"
        
        try:
            # Verify the LED path exists
            with open(self.brightness_file, 'r') as f:
                pass
            logger.info(f"LED initialized via sysfs: {led_path}")
            
            # Set trigger to "none" so we can control it manually
            self._set_trigger("none")
            
        except Exception as e:
            logger.error(f"Failed to initialize LED at {led_path}: {e}")
            raise
    
    def _set_trigger(self, trigger):
        """Set the LED trigger"""
        try:
            with open(self.trigger_file, 'w') as f:
                f.write(trigger)
            logger.debug(f"LED trigger set to: {trigger}")
        except PermissionError:
            logger.error(f"Permission denied setting trigger to '{trigger}'. This script may need to run with sudo.")
            raise
        except Exception as e:
            logger.error(f"Failed to set LED trigger to '{trigger}': {e}")
            raise
    
    def on(self):
        """Turn LED on"""
        try:
            with open(self.brightness_file, 'w') as f:
                f.write('1')
        except Exception as e:
            logger.error(f"Failed to turn LED on: {e}")
    
    def off(self):
        """Turn LED off"""
        try:
            with open(self.brightness_file, 'w') as f:
                f.write('0')
        except Exception as e:
            logger.error(f"Failed to turn LED off: {e}")
    
    def restore_default(self):
        """Restore LED to default behavior (SD card activity)"""
        try:
            self._set_trigger("mmc0")
            logger.info("LED trigger restored to default (mmc0)")
        except Exception as e:
            logger.error(f"Failed to restore LED to default: {e}")

# ===== LED SETUP =====
try:
    led = LED(LED_PATH)
except Exception as e:
    logger.error(f"Failed to initialize LED: {e}")
    exit(1)

# ===== CONNECTIVITY CHECK FUNCTION =====
def check_internet_connectivity():
    """
    Ping a reliable server to check internet connectivity.
    Returns True if ping succeeds, False otherwise.
    """
    try:
        # Use ping with timeout of 3 seconds, only send 1 packet
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "3", PING_TARGET],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logger.warning(f"Ping to {PING_TARGET} timed out")
        return False
    except Exception as e:
        logger.error(f"Error during ping: {e}")
        return False

# ===== MAIN MONITORING LOOP =====
def main():
    """
    Main monitoring loop that continuously checks connectivity
    and controls LED based on status.
    """
    logger.info("Internet Connectivity Monitor started")
    logger.info(f"Debug mode: {'ENABLED' if DEBUG else 'DISABLED'}")
    logger.info(f"LED control via: {LED_TYPE}")
    consecutive_failures = 0
    current_status = None  # Track previous status to avoid redundant logging
    check_count = 0
    
    try:
        while True:
            check_count += 1
            is_connected = check_internet_connectivity()
            
            if DEBUG:
                status_symbol = "✓" if is_connected else "✗"
                logger.debug(f"[Check #{check_count}] {status_symbol} Ping to {PING_TARGET}: {'SUCCESS' if is_connected else 'FAILED'} (consecutive_failures={consecutive_failures})")
            
            if is_connected:
                consecutive_failures = 0
                if current_status != "UP":
                    led.on()
                    logger.info(f"✓ Internet UP - LED ON")
                    current_status = "UP"
            else:
                consecutive_failures += 1
                if consecutive_failures >= CONSECUTIVE_FAILURES:
                    if current_status != "DOWN":
                        led.off()
                        logger.warning(f"✗ Internet DOWN ({consecutive_failures} consecutive failures) - LED OFF")
                        current_status = "DOWN"
                elif DEBUG:
                    logger.debug(f"[Check #{check_count}] Connection failed ({consecutive_failures}/{CONSECUTIVE_FAILURES} failures needed to mark DOWN)")
            
            time.sleep(PING_INTERVAL)
    
    except KeyboardInterrupt:
        logger.info("Monitor interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in monitoring loop: {e}")
    finally:
        led.off()
        led.restore_default()
        logger.info("Internet Connectivity Monitor stopped")

if __name__ == "__main__":
    main()
