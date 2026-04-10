
import time
import serial

import minimalmodbus

from src.config import get_controller


class Registries(Enum):
    pass


def read_vigor_data(controller):
    try:
        # Read Current Mode (Holding Register 4022)
        # function_code 3 is for Holding Registers
        # current_mode = instrument.read_register(4032, functioncode=3)
        
        # Read Airflow (Input Register 4032)
        # function_code 4 is for Input Registers
        airflow = controller.read_register(4032, functioncode=4)
        
        # print(f"Current Mode: {current_mode}")
        print(f"Current Airflow: {airflow} m3/h")
        
    except Exception as e:
        print(f"Failed to read: {e}")

def set_boost_mode():
    try:
        # Write 3 (Boost) to Setting Register 4021
        print("Setting Vigor to Boost Mode...")
        instrument.write_register(4021, 3, functioncode=6)
        print("Success!")
    except Exception as e:
        print(f"Failed to set boost: {e}")

if __name__ == "__main__":
    controller = get_controller()
    read_vigor_data(controller)
    # Uncomment the line below to actually trigger the boost
    # set_boost_mode()