import time

from src.config import get_controller
from src.modbus_service import Registries, AirflowMode, read_vigor_data, release_to_wall_unit, set_airflow_mode


def read_all_stats(controller):
    for reg in Registries:
        time.sleep(0.2)
        value = read_vigor_data(controller, reg.value)
        print(f"Reading {reg}: {value}")


def main():
    controller = get_controller()

    read_all_stats(controller)
    time.sleep(0.2)

    set_airflow_mode(controller, AirflowMode.HIGH)
    time.sleep(10)
    read_all_stats(controller)
    set_airflow_mode(controller, AirflowMode.LOW)
    release_to_wall_unit(controller)


if __name__ == "__main__":
    main()