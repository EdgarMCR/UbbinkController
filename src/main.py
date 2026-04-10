import logging
import time
from dataclasses import dataclass
from enum import Enum

from src.config import get_controller


@dataclass
class RegistryInfo:
    address: int
    functioncode: int


class Registries(Enum):
    READ_SUPPLY_PRESSURE = RegistryInfo(4023, 4)
    READ_EXTRACT_PRESSURE = RegistryInfo(4024, 4)
    READ_SUPPLY_AIRFLOW_PRESET = RegistryInfo(4031, 4)
    READ_SUPPLY_AIRFLOW_ACTUAL = RegistryInfo(4032, 4)
    READ_EXTRACT_AIRFLOW_PRESET = RegistryInfo(4041, 4)
    READ_EXTRACT_AIRFLOW_ACTUAL = RegistryInfo(4042, 4)
    READ_SUPPLY_TEMPERATURE = RegistryInfo(4036, 4)
    READ_EXTRACT_TEMPERATURE = RegistryInfo(4046, 4)
    READ_BYPASS_STATUS = RegistryInfo(4050, 4)
    READ_FILTER_STATUS = RegistryInfo(4100, 4)
    READ_AIRFLOW_MODE = RegistryInfo(8001, 3)


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

def read_airflow(controller):
    airflow = read_vigor_data(controller, Registries.READ_AIRFLOW)
    print(f"Current Airflow: {airflow} m3/h")

def set_boost_mode(controller):
    try:
        # Write 3 (Boost) to Setting Register 4021
        print("Setting Vigor to Boost Mode...")
        controller.write_register(4021, 3, functioncode=6)
        print("Success!")
    except Exception as e:
        print(f"Failed to set boost: {e}")

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


# Example Usage:
# set_airflow_mode(controller, 3)  # This triggers Boost
def main():
    controller = get_controller()
    # read_airflow(controller)

    # for reg in Registries:
    #     time.sleep(0.2)
    #     value = read_vigor_data(controller, reg.value)
    #     print(f"Reading {reg}: {value}")

    time.sleep(0.2)

    # value = controller.read_register(8001, functioncode=3)
    # print(f"Current value: {value}")

    # set_airflow_mode(controller, AirflowMode.LOW)

    release_to_wall_unit(controller)

if __name__ == "__main__":
    main()