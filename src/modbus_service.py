
import time
import logging
import threading
from dataclasses import dataclass
from enum import Enum

from src.config import get_controller, PORT, SLAVE_ID, BAUD_RATE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RegistryInfo:
    address: int
    functioncode: int


class Registries(Enum):
    SUPPLY_PRESSURE = RegistryInfo(4023, 4)
    EXTRACT_PRESSURE = RegistryInfo(4024, 4)
    SUPPLY_AIRFLOW_PRESET = RegistryInfo(4031, 4)
    SUPPLY_AIRFLOW_ACTUAL = RegistryInfo(4032, 4)
    EXTRACT_AIRFLOW_PRESET = RegistryInfo(4041, 4)
    EXTRACT_AIRFLOW_ACTUAL = RegistryInfo(4042, 4)
    SUPPLY_TEMPERATURE = RegistryInfo(4036, 4)
    EXTRACT_TEMPERATURE = RegistryInfo(4046, 4)
    BYPASS_STATUS = RegistryInfo(4050, 4)
    FILTER_STATUS = RegistryInfo(4100, 4)
    CONTROL_MODE = RegistryInfo(8000, 3)
    AIRFLOW_MODE = RegistryInfo(8001, 3)


class BypassModes(Enum):
    INITIALIZING = 0
    OPENING = 1
    CLOSING = 2
    OPEN = 3
    CLOSED = 4

class FilterStatus(Enum):
    CLEAN = 0
    DIRTY = 1

class AirflowMode(Enum):
    HOLIDAY = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3

def read_vigor_data(controller, reg_info: RegistryInfo):
    try:
        value = controller.read_register(reg_info.address, functioncode=reg_info.functioncode)
    except Exception as e:
        logging.exception(f"Failed to read {value}: {e}")
        value = None
    return value

def set_modbus_control(controller):
    # Check current control mode (Register 8000)
    # Function code 3 (Holding Register)
    current_control = controller.read_register(8000, functioncode=3)
    if current_control != 1:
        controller.write_register(8000, 1, functioncode=6)
        logging.info(f"Modbus control set to {current_control}, sleeping for a moment...")
        time.sleep(0.1)

def set_airflow_mode(controller, mode: AirflowMode):
    """     Sets the airflow mode (0-3). """
    try:
        set_modbus_control(controller)

        # Step 2: Set the actual mode (Register 8001)
        controller.write_register(8001, mode.value, functioncode=6)

        logging.info(f"Airflow mode successfully set to: {mode}")
    except Exception as e:
        logging.exception(f"Failed to set airflow mode: {e}")

def release_to_wall_unit(controller):
    """    Reverts control back to the physical machine/wall switch.    """
    try:
        logging.info("Reverting control to Wall Unit...")
        controller.write_register(8000, 0, functioncode=6)
        logging.info("Machine is now in local control mode.")
    except Exception as e:
        logging.exception(f"Failed to revert control: {e}")



class VigorModbusService:
    def __init__(self, port=PORT, slave_id=SLAVE_ID, baud_rate=BAUD_RATE):
        self.lock = threading.Lock()
        self.controller = get_controller(port, slave_id, baud_rate)

    def read_register_safe(self, reg_info: RegistryInfo) -> int | None:
        """Thread-safe reading from the Modbus controller."""
        with self.lock:
            try:
                time.sleep(0.1)  # Breather for the Vigor CPU
                return self.controller.read_register(reg_info.address, functioncode=reg_info.functioncode)
            except Exception as e:
                logger.error(f"Failed to read register {reg_info}: {e}")
                return None

    def write_register_safe(self, address: int, value: int, functioncode: int = 6) -> bool:
        """Thread-safe writing to the Modbus controller."""
        with self.lock:
            try:
                time.sleep(0.1)
                self.controller.write_register(address, value, functioncode=functioncode)
                return True
            except Exception as e:
                logger.error(f"Failed to write {value} to {address}: {e}")
                return False

    def get_status(self) -> dict:
        """Fetches all relevant status registers."""
        modes = {0: 'Holiday (40 m^3/h)', 1: 'Low (50 m^3/h)', 2: 'Normal (100 m^3/h)', 3: 'High (150 m^3/h)'}
        current_airflow_mode = self.read_register_safe(Registries.AIRFLOW_MODE.value)  # 0-3 Mode
        current_airflow = modes[current_airflow_mode]
        return {
            "control_mode": self.read_register_safe(Registries.CONTROL_MODE.value),  # 0=Wall, 1=Modbus
            "current_setting": current_airflow,
            "supply_airflow_m3h": self.read_register_safe(Registries.SUPPLY_AIRFLOW_ACTUAL.value),
            "extract_airflow_m3h": self.read_register_safe(Registries.EXTRACT_AIRFLOW_ACTUAL.value),
            "supply_temp": self.read_register_safe(Registries.SUPPLY_TEMPERATURE.value),
            "extract_temp": self.read_register_safe(Registries.EXTRACT_TEMPERATURE.value),
        }

    def set_airflow_mode(self, mode: AirflowMode) -> bool:
        """Takes control from the wall unit and sets the airflow level."""
        current_control = self.read_register_safe(RegistryInfo(8000, 3))
        if current_control != 1:
            if not self.write_register_safe(8000, 1):
                return False

        return self.write_register_safe(8001, mode.value)

    def revert_to_wall_unit(self) -> bool:
        """Returns control to the physical machine."""
        logger.info("Reverting control to Wall Unit...")
        return self.write_register_safe(8000, 0)


# Instantiate a single global service
vigor_service = VigorModbusService()