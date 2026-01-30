#!/usr/bin/env python3
"""
Raspberry Pi Internet Connectivity Monitor
Continuously tests internet connectivity and controls LED status
"""

import subprocess
import time
import logging
from datetime import datetime
from gpiozero import LED
from signal import pause

# ===== CONFIGURATION =====
GPIO_PIN = 17                    # GPIO pin for LED (change if needed)
PING_TARGET = "8.8.8.8"         # Google DNS - reliable server to ping
PING_INTERVAL = 10              # Check connectivity every 10 seconds
CONSECUTIVE_FAILURES = 3        # Require 3 failed pings before marking as DOWN
LOG_FILE = "/var/log/connectivity_monitor.log"

# ===== LOGGING SETUP =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===== LED SETUP =====
try:
    led = LED(GPIO_PIN)
    logger.info(f"LED initialized on GPIO pin {GPIO_PIN}")
except Exception as e:
    logger.error(f"Failed to initialize LED on pin {GPIO_PIN}: {e}")
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
    consecutive_failures = 0
    current_status = None  # Track previous status to avoid redundant logging
    
    try:
        while True:
            is_connected = check_internet_connectivity()
            
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
            
            time.sleep(PING_INTERVAL)
    
    except KeyboardInterrupt:
        logger.info("Monitor interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in monitoring loop: {e}")
    finally:
        led.off()
        logger.info("Internet Connectivity Monitor stopped")

if __name__ == "__main__":
    main()
