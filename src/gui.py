from datetime import datetime
import logging
import os
import re
import tkinter as tk

from pathlib import Path

from serial_interface import (
    OT_THR_TO_CELCIUS_LU_TABLE,
    OT_THR_TO_CELCIUS_LU_TABLE_REVERSE,
    con_serial_port,
    disco_serial_port,
    reset_slave,
    get_slave_id,
    set_slave_id,
    read_adc_meas,
    full_dump,
    read_alerts,
    read_faults,
    read_ov_cells,
    read_uv_cells,
    get_ov_thr,
    get_uv_thr,
    set_ov_thr,
    set_uv_thr,
    get_ot_thr,
    set_ot_thr,
    clear_cuv_cov_faults,
)
from tkinter import messagebox


COM_PORT_PATTERN = r"^COM\d+$"

ROOT_FOLDER = Path(__file__).parent.parent.resolve()

ALERT_REG_IMG = ROOT_FOLDER / "img" / "alert_status_register.png"
FAULT_REG_IMG = ROOT_FOLDER / "img" / "fault_status_register.png"
OT_THR_TABLE_IMG = ROOT_FOLDER / "img" / "ot_thr_meaning.png"

LOG_FILE_FOLDER = ROOT_FOLDER / "log"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE_NAME = f"log_{TIMESTAMP}.txt"
LOG_FILE_PATH = LOG_FILE_FOLDER / LOG_FILE_NAME


def check_com_port_format(com_port_string):
    if re.match(COM_PORT_PATTERN, com_port_string):
        return True
    else:
        return False


class BMSMonitorApp:
    def __init__(self, main):

        self.main = main
        self.main.title("Slave BMS Monitor - Tesla Model S ph.1, 2012/2016")

        self.serial_con = None
        self.com_port_sel = None
        self.com_port_input = None
        self.con_status = False

        self.id = None
        self.id_sel = None
        self.id_input = None
        self.id_update_button = None

        self.reset_button = None

        self.vbatt = None
        self.vcells = []
        self.temps = []

        self.set_ov_thr_button = None
        self.set_uv_thr_button = None
        self.ov_thr_sel = None
        self.uv_thr_sel = None
        self.ov_thr_input = None
        self.uv_thr_input = None
        self.set_ot1_thr_button = None
        self.set_ot2_thr_button = None
        self.ot1_thr_sel = None
        self.ot2_thr_sel = None
        self.ot1_thr_input = None
        self.ot2_thr_input = None

        self.alerts_list = [
            "~ID_assigned",
            "Gp3_valid",
            "OTP_ECC",
            "ALERT_SIG",
            "Too_hot",
            "Was_sleeping",
            "OVT1",
            "OVT2",
        ]
        self.faults_list = [
            "_",
            "_",
            "INTERN_ISSUE",
            "FAULT_SIG",
            "PO_RESET",
            "CRC_ERR",
            "<UV_CELLS",
            ">OV_CELLS",
        ]
        self.alerts_val = []
        self.faults_val = []
        self.ov_cells_val = []
        self.uv_cells_val = []

        self.is_all_locked = True
        self.is_id_locked = True
        self.is_thresh_locked = True
        self.is_reset_locked = True
        self.id_lock_checkbutton = None
        self.thresh_lock_checkbutton = None
        self.reset_lock_checkbutton = None

        # COM_PORT, Reset, ID
        self.create_com_reset_id_frame(main)
        # Voltages, Temperatures
        self.create_measurements_frame(main)
        # Security thresholds (volt and temp)
        self.create_secu_thresholds_frame(main)
        # Alerts and Faults status
        self.create_alerts_and_faults_frame(main)
        # Config locks
        self.create_locks_frame(main)

        # Logging config
        if not os.path.isdir(LOG_FILE_FOLDER):
            os.mkdir(LOG_FILE_FOLDER)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        f_handler = logging.FileHandler(LOG_FILE_PATH)
        f_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        f_handler.setFormatter(f_format)
        self.logger.addHandler(f_handler)

    def create_com_reset_id_frame(self, main):
        # COM_PORT, Reset, ID
        com_reset_id_frame = tk.Frame(main, width=100, height=100, bg="paleturquoise4")
        com_reset_id_frame.grid(row=0, column=0, padx=10, pady=5)

        ## COM_PORT
        port_frame = tk.Frame(
            com_reset_id_frame, width=20, height=20, bg="paleturquoise3"
        )
        port_frame.grid(row=0, column=0, padx=5, pady=5)

        self.com_port_sel = tk.Label(
            port_frame,
            text="COM_PORT: DISCO",
            width=20,
            fg="brown",
            font=("Helvetica", 10, "bold"),
        )
        self.com_port_sel.grid(row=0, column=0, columnspan=2, padx=5, pady=5)

        self.com_port_input = tk.Entry(port_frame)
        self.com_port_input.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        self.com_port_input.insert(0, "Enter port here")

        tk.Button(port_frame, text="Set PORT", command=self.set_port).grid(
            row=2, column=0, padx=5, pady=5
        )
        tk.Button(port_frame, text="Disconnect", command=self.disco_port).grid(
            row=2, column=1, padx=5, pady=5
        )

        ## Reset
        reset_frame = tk.Frame(
            com_reset_id_frame, width=20, height=20, bg="paleturquoise3"
        )
        reset_frame.grid(row=1, column=0, padx=5, pady=5)

        self.reset_button = tk.Button(
            reset_frame, text="Reset BMS", command=self.reset_board, state=tk.DISABLED
        )
        self.reset_button.grid(row=0, column=0, padx=5, pady=5)

        ## ID
        id_frame = tk.Frame(
            com_reset_id_frame, width=20, height=20, bg="paleturquoise3"
        )
        id_frame.grid(row=2, column=0, padx=5, pady=5)

        self.id_sel = tk.Label(id_frame, text="ID: ?")
        self.id_sel.grid(row=0, column=0, columnspan=2, padx=5, pady=5)

        self.id_update_button = tk.Button(
            id_frame, text="Set ID:", command=self.set_id, state=tk.DISABLED
        )
        self.id_update_button.grid(row=1, column=0, padx=5, pady=5)

        self.id_input = tk.Entry(id_frame)
        self.id_input.grid(row=1, column=1, padx=5, pady=5)
        self.id_input.insert(0, "Enter ID here")

    def create_measurements_frame(self, main):
        # Voltages, Temperatures
        measurements_frame = tk.Frame(main, width=100, height=100, bg="paleturquoise4")
        measurements_frame.grid(row=0, column=1, padx=10, pady=5)

        # Voltages
        VOLT_ARRAY_WIDTH = 10
        voltages_frame = tk.Frame(
            measurements_frame, width=20, height=20, bg="paleturquoise3"
        )
        voltages_frame.grid(row=0, column=0, padx=5, pady=5)

        tk.Label(
            voltages_frame, text="Voltages", width=VOLT_ARRAY_WIDTH, relief="raised"
        ).grid(row=0, column=0)

        tk.Label(
            voltages_frame, text="mV", width=VOLT_ARRAY_WIDTH, relief="raised"
        ).grid(row=0, column=1)

        tk.Label(
            voltages_frame, text="Vbatt", width=VOLT_ARRAY_WIDTH, relief="groove"
        ).grid(row=1, column=0)
        self.vbatt = tk.Label(
            voltages_frame, text="?", width=VOLT_ARRAY_WIDTH, relief="groove"
        )
        self.vbatt.grid(row=1, column=1)

        self.vcells = []
        for i in range(1, 7):
            tk.Label(
                voltages_frame,
                text=f"Vcell_{i}",
                width=VOLT_ARRAY_WIDTH,
                relief="groove",
            ).grid(row=1 + i, column=0)
            current_vcell = tk.Label(
                voltages_frame, text="?", width=VOLT_ARRAY_WIDTH, relief="groove"
            )
            current_vcell.grid(row=1 + i, column=1)
            self.vcells.append(current_vcell)

        # Temperatures
        TEMP_ARRAY_WIDTH = 10
        temp_frame = tk.Frame(
            measurements_frame, width=20, height=20, bg="paleturquoise3"
        )
        temp_frame.grid(row=1, column=0, padx=5, pady=5)

        tk.Label(
            temp_frame, text="Temperature", width=TEMP_ARRAY_WIDTH, relief="raised"
        ).grid(row=0, column=0)
        tk.Label(temp_frame, text="degC", width=TEMP_ARRAY_WIDTH, relief="raised").grid(
            row=0, column=1
        )

        tk.Label(
            temp_frame, text="Temp1", width=TEMP_ARRAY_WIDTH, relief="groove"
        ).grid(row=1, column=0)
        temp1 = tk.Label(temp_frame, text="?", width=TEMP_ARRAY_WIDTH, relief="groove")
        temp1.grid(row=1, column=1)

        tk.Label(
            temp_frame, text="Temp2", width=TEMP_ARRAY_WIDTH, relief="groove"
        ).grid(row=2, column=0)
        temp2 = tk.Label(temp_frame, text="?", width=TEMP_ARRAY_WIDTH, relief="groove")
        temp2.grid(row=2, column=1)

        self.temps = [temp1, temp2]

        # V and T update button
        v_t_update_frame = tk.Frame(
            measurements_frame, width=20, height=20, bg="paleturquoise3"
        )
        v_t_update_frame.grid(row=2, column=0, padx=5, pady=5)

        tk.Button(
            v_t_update_frame, text="Update V and T", command=self.update_meas
        ).grid(row=1, column=0, padx=5, pady=5)

    def create_secu_thresholds_frame(self, main):
        # Security thresholds (volt and temp)
        THR_BOX_WIDTH = 10
        secu_thresholds_frame = tk.Frame(
            main, width=100, height=100, bg="paleturquoise4"
        )
        secu_thresholds_frame.grid(row=0, column=2, padx=10, pady=5)

        # Voltage thresholds
        v_thr_frame = tk.Frame(
            secu_thresholds_frame, width=20, height=20, bg="paleturquoise3"
        )
        v_thr_frame.grid(row=0, column=0, padx=5, pady=5)

        tk.Label(
            v_thr_frame, width=THR_BOX_WIDTH, text="OV_THR:", relief="groove"
        ).grid(row=0, column=0)
        self.ov_thr_sel = tk.Label(
            v_thr_frame, width=int(0.5 * THR_BOX_WIDTH), text="?", relief="groove"
        )
        self.ov_thr_sel.grid(row=0, column=1)
        tk.Label(
            v_thr_frame, width=THR_BOX_WIDTH, text="UV_THR:", relief="groove"
        ).grid(row=1, column=0)
        self.uv_thr_sel = tk.Label(
            v_thr_frame, width=int(0.5 * THR_BOX_WIDTH), text="?", relief="groove"
        )
        self.uv_thr_sel.grid(row=1, column=1)

        self.ov_thr_input = tk.Entry(v_thr_frame, width=int(1.5 * THR_BOX_WIDTH))
        self.ov_thr_input.grid(row=0, column=2)
        self.ov_thr_input.insert(0, "Enter OV_THR")
        self.uv_thr_input = tk.Entry(v_thr_frame, width=int(1.5 * THR_BOX_WIDTH))
        self.uv_thr_input.grid(row=1, column=2)
        self.uv_thr_input.insert(0, "Enter UV_THR")

        self.set_ov_thr_button = tk.Button(
            v_thr_frame, text="Set", command=self.set_ov_thr_ui, state=tk.DISABLED
        )
        self.set_ov_thr_button.grid(row=0, column=3)
        self.set_uv_thr_button = tk.Button(
            v_thr_frame, text="Set", command=self.set_uv_thr_ui, state=tk.DISABLED
        )
        self.set_uv_thr_button.grid(row=1, column=3)

        # Temperature thresholds
        t_thr_frame = tk.Frame(
            secu_thresholds_frame, width=20, height=20, bg="paleturquoise3"
        )
        t_thr_frame.grid(row=1, column=0, padx=5, pady=5)

        tk.Label(
            t_thr_frame, width=THR_BOX_WIDTH, text="OT1_THR:", relief="groove"
        ).grid(row=0, column=0)
        self.ot1_thr_sel = tk.Label(
            t_thr_frame, width=THR_BOX_WIDTH, text="?", relief="groove"
        )
        self.ot1_thr_sel.grid(row=0, column=1)
        tk.Label(
            t_thr_frame, width=THR_BOX_WIDTH, text="OT2_THR:", relief="groove"
        ).grid(row=1, column=0)
        self.ot2_thr_sel = tk.Label(
            t_thr_frame, width=THR_BOX_WIDTH, text="?", relief="groove"
        )
        self.ot2_thr_sel.grid(row=1, column=1)

        self.ot1_thr_input = tk.Entry(t_thr_frame, width=int(1.5 * THR_BOX_WIDTH))
        self.ot1_thr_input.grid(row=0, column=2)
        self.ot1_thr_input.insert(0, "Enter OT1_THR")
        self.ot2_thr_input = tk.Entry(t_thr_frame, width=int(1.5 * THR_BOX_WIDTH))
        self.ot2_thr_input.grid(row=1, column=2)
        self.ot2_thr_input.insert(0, "Enter OT2_THR")

        self.set_ot1_thr_button = tk.Button(
            t_thr_frame, text="Set", command=self.set_ot1_thr_ui, state=tk.DISABLED
        )
        self.set_ot1_thr_button.grid(row=0, column=3)
        self.set_ot2_thr_button = tk.Button(
            t_thr_frame, text="Set", command=self.set_ot2_thr_ui, state=tk.DISABLED
        )
        self.set_ot2_thr_button.grid(row=1, column=3)

        tk.Button(
            secu_thresholds_frame,
            text="Update security thresholds",
            command=self.update_secu_thr,
        ).grid(row=2, column=0, padx=5, pady=5)
        tk.Button(
            secu_thresholds_frame,
            text="OT_THR/CONFIG_OT meaning",
            command=self.show_ot_thr_info,
        ).grid(row=3, column=0, padx=5, pady=5)

    def create_alerts_and_faults_frame(self, main):
        # Alerts and Faults status
        alerts_and_faults_frame = tk.Frame(
            main, width=100, height=100, bg="paleturquoise4"
        )
        alerts_and_faults_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=5)

        # Alerts
        ALERTS_ARRAY_WIDTH = 10
        alerts_frame = tk.Frame(
            alerts_and_faults_frame, width=20, height=20, bg="paleturquoise3"
        )
        alerts_frame.grid(row=0, column=0, padx=5, pady=5)

        tk.Label(
            alerts_frame, text="Alert", width=ALERTS_ARRAY_WIDTH, relief="raised"
        ).grid(row=0, column=0)
        tk.Label(
            alerts_frame, text="State", width=ALERTS_ARRAY_WIDTH, relief="raised"
        ).grid(row=1, column=0)

        self.alers_val = []
        for i, alert in enumerate(self.alerts_list):
            tk.Label(
                alerts_frame, text=alert, width=ALERTS_ARRAY_WIDTH, relief="groove"
            ).grid(row=0, column=1 + i)
            alert_val = tk.Label(
                alerts_frame, text="?", width=ALERTS_ARRAY_WIDTH, relief="groove"
            )
            alert_val.grid(row=1, column=1 + i)
            self.alerts_val.append(alert_val)

        # Faults
        FAULTS_ARRAY_WIDTH = 10
        faults_frame = tk.Frame(
            alerts_and_faults_frame, width=20, height=20, bg="paleturquoise3"
        )
        faults_frame.grid(row=1, column=0, padx=5, pady=5)

        tk.Label(
            faults_frame, text="Fault", width=FAULTS_ARRAY_WIDTH, relief="raised"
        ).grid(row=0, column=0)
        tk.Label(
            faults_frame, text="State", width=FAULTS_ARRAY_WIDTH, relief="raised"
        ).grid(row=1, column=0)

        self.faults_val = []
        for i, alert in enumerate(self.faults_list):
            tk.Label(
                faults_frame, text=alert, width=FAULTS_ARRAY_WIDTH, relief="groove"
            ).grid(row=0, column=1 + i)
            fault_val = tk.Label(
                faults_frame,
                text=("?" if i not in [0, 1] else "_"),
                width=FAULTS_ARRAY_WIDTH,
                relief="groove",
            )
            fault_val.grid(row=1, column=1 + i)
            self.faults_val.append(fault_val)

        # OV & UV cells
        OVUV_CELLS_ARRAY_WIDTH = 10
        ovuv_cells_frame = tk.Frame(
            alerts_and_faults_frame, width=20, height=20, bg="paleturquoise3"
        )
        ovuv_cells_frame.grid(row=2, column=0, padx=5, pady=5)

        tk.Label(
            ovuv_cells_frame, text="Cell num", width=FAULTS_ARRAY_WIDTH, relief="raised"
        ).grid(row=0, column=0)
        tk.Label(
            ovuv_cells_frame, text="V>OVth?", width=FAULTS_ARRAY_WIDTH, relief="raised"
        ).grid(row=1, column=0)
        tk.Label(
            ovuv_cells_frame, text="V<UVth?", width=FAULTS_ARRAY_WIDTH, relief="raised"
        ).grid(row=2, column=0)

        self.ov_cells_val = []
        self.uv_cells_val = []
        for i in range(1, 7):
            tk.Label(
                ovuv_cells_frame, text=i, width=FAULTS_ARRAY_WIDTH, relief="raised"
            ).grid(row=0, column=1 + i)
            ov_cell_val = tk.Label(
                ovuv_cells_frame, text="?", width=FAULTS_ARRAY_WIDTH, relief="groove"
            )
            ov_cell_val.grid(row=1, column=1 + i)
            uv_cell_val = tk.Label(
                ovuv_cells_frame, text="?", width=FAULTS_ARRAY_WIDTH, relief="groove"
            )
            uv_cell_val.grid(row=2, column=1 + i)
            self.ov_cells_val.append(ov_cell_val)
            self.uv_cells_val.append(uv_cell_val)

        # Alerts and faults update and info buttons
        alerts_and_faults_update_frame = tk.Frame(
            alerts_and_faults_frame, width=20, height=20, bg="paleturquoise3"
        )
        alerts_and_faults_update_frame.grid(row=3, column=0, padx=5, pady=5)

        tk.Button(
            alerts_and_faults_update_frame,
            text="Update Alerts and Faults",
            command=self.update_alerts_and_faults,
        ).grid(row=0, column=0, padx=5, pady=5)
        tk.Button(
            alerts_and_faults_update_frame,
            text="Alerts details",
            command=self.show_alerts_info,
        ).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(
            alerts_and_faults_update_frame,
            text="Faults details",
            command=self.show_faults_info,
        ).grid(row=0, column=2, padx=5, pady=5)

    def create_locks_frame(self, main):
        # Config locks
        lock_frame = tk.Frame(main, width=100, height=100, bg="paleturquoise4")
        lock_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=5)

        # Global lock (lock everything that can be locked)
        global_lock_frame = tk.Frame(
            lock_frame, width=20, height=20, bg="paleturquoise3"
        )
        global_lock_frame.grid(row=0, column=0, padx=5, pady=5)
        # We could use directly the Checkbutton's variable parameter but command will allow us to add more features to a switch action in the future
        # Lock by default
        self.global_lock = tk.IntVar(value=1)
        tk.Checkbutton(
            global_lock_frame,
            text="GLOBAL locked",
            variable=self.global_lock,
            command=self.lock_all,
        ).grid(row=0, column=0)

        # BMS ID lock
        id_lock_frame = tk.Frame(lock_frame, width=20, height=20, bg="paleturquoise3")
        id_lock_frame.grid(row=0, column=1, padx=5, pady=5)
        # Lock by default
        self.id_lock = tk.IntVar(value=1)
        self.id_lock_checkbutton = tk.Checkbutton(
            id_lock_frame,
            text="ID locked",
            variable=self.id_lock,
            command=self.lock_id,
            state=tk.DISABLED,
        )
        self.id_lock_checkbutton.grid(row=0, column=0)

        # Threshold lock
        thresholds_lock_frame = tk.Frame(
            lock_frame, width=20, height=20, bg="paleturquoise3"
        )
        thresholds_lock_frame.grid(row=0, column=2, padx=5, pady=5)
        # Lock by default
        self.thresh_lock = tk.IntVar(value=1)
        self.thresh_lock_checkbutton = tk.Checkbutton(
            thresholds_lock_frame,
            text="Threshold locked",
            variable=self.thresh_lock,
            command=self.lock_thresh,
            state=tk.DISABLED,
        )
        self.thresh_lock_checkbutton.grid(row=0, column=0)

        # Reset lock
        reset_lock_frame = tk.Frame(
            lock_frame, width=20, height=20, bg="paleturquoise3"
        )
        reset_lock_frame.grid(row=0, column=3, padx=5, pady=5)
        # Lock by default
        self.reset_lock = tk.IntVar(value=1)
        self.reset_lock_checkbutton = tk.Checkbutton(
            reset_lock_frame,
            text="Reset locked",
            variable=self.reset_lock,
            command=self.lock_reset,
            state=tk.DISABLED,
        )
        self.reset_lock_checkbutton.grid(row=0, column=0)

    def lock_all(self):
        if self.global_lock.get() == 1:
            self.is_all_locked = True
            self.id_lock.set(1)
            self.thresh_lock.set(1)
            self.reset_lock.set(1)
            self.id_lock_checkbutton.config(state=tk.DISABLED)
            self.thresh_lock_checkbutton.config(state=tk.DISABLED)
            self.reset_lock_checkbutton.config(state=tk.DISABLED)
            self.id_update_button.config(state=tk.DISABLED)
            self.set_ov_thr_button.config(state=tk.DISABLED)
            self.set_uv_thr_button.config(state=tk.DISABLED)
            self.set_ot1_thr_button.config(state=tk.DISABLED)
            self.set_ot2_thr_button.config(state=tk.DISABLED)
            self.reset_button.config(state=tk.DISABLED)
            print("Is everything locked ?: ", self.is_all_locked)
        else:
            self.is_all_locked = False
            self.id_lock_checkbutton.config(state=tk.NORMAL)
            self.thresh_lock_checkbutton.config(state=tk.NORMAL)
            self.reset_lock_checkbutton.config(state=tk.NORMAL)
            if self.id_lock.get() != 1:
                self.id_update_button.config(state=tk.NORMAL)
            if self.thresh_lock.get() != 1:
                self.set_ov_thr_button.config(state=tk.NORMAL)
                self.set_uv_thr_button.config(state=tk.NORMAL)
                self.set_ot1_thr_button.config(state=tk.NORMAL)
                self.set_ot2_thr_button.config(state=tk.NORMAL)
            if self.reset_lock.get() != 1:
                self.reset_button.config(state=tk.NORMAL)
            print("Is everything locked ?: ", self.is_all_locked)

    def lock_id(self):
        if self.global_lock.get() == 1:
            print("GLOBAL lock on")
            return
        if self.id_lock.get() == 1:
            self.is_id_locked = True
            self.id_update_button.config(state=tk.DISABLED)
            print("Is ID locked ?: ", self.is_id_locked)
        else:
            self.is_id_locked = False
            self.id_update_button.config(state=tk.NORMAL)
            print("Is ID locked ?: ", self.is_id_locked)

    def lock_thresh(self):
        if self.global_lock.get() == 1:
            print("GLOBAL lock on")
            return
        if self.thresh_lock.get() == 1:
            self.is_thresh_locked = True
            self.set_ov_thr_button.config(state=tk.DISABLED)
            self.set_uv_thr_button.config(state=tk.DISABLED)
            self.set_ot1_thr_button.config(state=tk.DISABLED)
            self.set_ot2_thr_button.config(state=tk.DISABLED)
            print("Are Thresholds locked ?: ", self.is_thresh_locked)
        else:
            self.is_thresh_locked = False
            self.set_ov_thr_button.config(state=tk.NORMAL)
            self.set_uv_thr_button.config(state=tk.NORMAL)
            self.set_ot1_thr_button.config(state=tk.NORMAL)
            self.set_ot2_thr_button.config(state=tk.NORMAL)
            print("Are Thresholds locked ?: ", self.is_thresh_locked)

    def lock_reset(self):
        if self.global_lock.get() == 1:
            print("GLOBAL lock on")
            return
        if self.reset_lock.get() == 1:
            self.is_reset_locked = True
            self.reset_button.config(state=tk.DISABLED)
            print("Is reset locked ?: ", self.is_reset_locked)
        else:
            self.is_reset_locked = False
            self.reset_button.config(state=tk.NORMAL)
            print("Is reset locked ?: ", self.is_reset_locked)

    def reset_board(self):
        if not self.con_status:
            print("No board connected")
            return
        print(self.is_reset_locked)
        print(self.is_all_locked)
        print(self.is_reset_locked or self.is_all_locked)
        if self.is_reset_locked or self.is_all_locked:
            print("WARNING: Reset locked")
        else:
            reset_slave(ser=self.serial_con, id=self.id)
            print(f"Reset done for {self.id}")
        # Board ID should have got back to 0
        self.id = get_slave_id(ser=self.serial_con)
        self.id_sel.config(text=f"ID: {self.id}")
        # Update ADC meas two times to let readings stabilizing
        self.update_meas()
        self.update_meas()
        # Update alerts and faults
        self.update_alerts_and_faults()
        # Update thresholds reading
        self.update_secu_thr()
        self.log_full_memory()

    def show_ot_thr_info(self):
        info_window = tk.Toplevel(self.main)
        info_window.title("Over temperature threshold information")
        doc_screenshot = tk.PhotoImage(file=OT_THR_TABLE_IMG)
        image_label = tk.Label(info_window, image=doc_screenshot)
        image_label.image = doc_screenshot
        image_label.pack()
        print("Show over temperature threshold meaning info")

    def show_alerts_info(self):
        info_window = tk.Toplevel(self.main)
        info_window.title("Alerts information")
        resigster_screenshot = tk.PhotoImage(file=ALERT_REG_IMG)
        image_label = tk.Label(info_window, image=resigster_screenshot)
        image_label.image = resigster_screenshot
        image_label.pack()
        print("Show alerts info")

    def show_faults_info(self):
        info_window = tk.Toplevel(self.main)
        info_window.title("Faults information")
        resigster_screenshot = tk.PhotoImage(file=FAULT_REG_IMG)
        image_label = tk.Label(info_window, image=resigster_screenshot)
        image_label.image = resigster_screenshot
        image_label.pack()
        print("Show faults info")

    def log_full_memory(self):
        # Save a full memory dump in the log file
        state_snapshot = ""
        for i, byte in enumerate(full_dump(ser=self.serial_con, id=self.id)):
            state_snapshot = state_snapshot + (
                f"@{i}:{hex(byte)} " if byte > 15 else f"@{i}:{hex(byte)}  "
            )
        self.logger.info(
            "Connection to %s, memory dump: %s", self.serial_con.name, state_snapshot
        )

    def disco_port(self):
        if not self.con_status:
            messagebox.showwarning("WARNING", f"Nothing connected actually.")
            self.con_status = False
            return False
        if not disco_serial_port(self.serial_con):
            messagebox.showwarning(
                "WARNING", f"Failed to disconnect from {self.serial_con.port}."
            )
            return False
        self.com_port_sel.config(
            text="COM_PORT: DISCO", fg="brown", font=("Helvetica", 10, "bold")
        )
        # Reset the board ID value
        self.id = ""
        self.id_sel.config(text=f"ID: ?")
        self.con_status = False
        return True

    def set_port(self):
        if self.con_status:
            messagebox.showwarning(
                "WARNING", f"One board is already connected, disconnect first."
            )
            return False
        port_name = self.com_port_input.get()
        if not check_com_port_format(port_name):
            messagebox.showwarning(
                "WARNING",
                f"Bad COM PORT format entered ({port_name}), should be COM[num].",
            )
            self.con_status = False
            return False
        self.serial_con = con_serial_port(port_name)
        if self.serial_con == None:
            messagebox.showwarning("WARNING", f"Connection to {port_name} failed.")
            self.con_status = False
            return False

        # Get the board ID to be able to address it
        try:
            self.id = get_slave_id(ser=self.serial_con)
        except:
            messagebox.showwarning(
                "WARNING",
                f"Issue heppened when trying to communicate with a BMS at {port_name} (e.g: no answer when reading ID).",
            )
            disco_serial_port(self.serial_con)
            return False
        self.id_sel.config(text=f"ID: {self.id}")
        self.con_status = True
        self.com_port_sel.config(
            text=f"COM_PORT: {port_name} (CON)",
            fg="chartreuse4",
            font=("Helvetica", 10, "bold"),
        )

        # Save a memory dump in the log file
        self.log_full_memory()

        # Update ADC meas two times to let readings stabilizing
        self.update_meas()
        self.update_meas()
        # Update alerts and faults
        # TODO: Determine if we need to clear (clear_cuv_cov_faults) the Cell under and over voltage faults before updating it. It seems that once raised, they remain set.
        # clear_cuv_cov_faults(ser=self.serial_con, id=self.id)
        self.update_alerts_and_faults()
        # Update thresholds reading
        self.update_secu_thr()
        return True

    def set_id(self):
        if not self.con_status:
            print("No board connected")
            return
        id_in = int(self.id_input.get())
        if self.is_id_locked or self.is_all_locked:
            print("WARNING: ID locked")
        else:
            if set_slave_id(ser=self.serial_con, old_id=self.id, new_id=id_in) != -1:
                self.id_sel.config(text=f"ID: {(id_in if id_in!='' else '?')}")
                self.logger.info("ID changed from %s to %s", self.id, id_in)
                self.id = id_in
                self.log_full_memory()
            else:
                messagebox.showwarning("WARNING", f"Setting ID to {id_in} failed.")

    def update_meas(self):
        if not self.con_status:
            print("No board connected")
            return
        print("Update V & T")
        # meas_buff = [GPAI, Vcell1, Vcell2, Vcell3, Vcell4, Vcell5, Vcell6, Temp1, Temp2]
        meas_buff = read_adc_meas(ser=self.serial_con, id=self.id)
        self.vbatt.config(text=meas_buff[0])
        for i, vcell in enumerate(self.vcells):
            vcell.config(text=meas_buff[1 + i])
        for i, temp in enumerate(self.temps):
            temp.config(text=meas_buff[7 + i])

    def update_secu_thr(self):
        # TODO: Display the information when security thresholds are disabled
        print("Update security thresholds")
        ov_thr = get_ov_thr(ser=self.serial_con, id=self.id)
        uv_thr = get_uv_thr(ser=self.serial_con, id=self.id)
        ot1_thr, ot2_thr = get_ot_thr(ser=self.serial_con, id=self.id)
        self.ov_thr_sel.config(text=f"{ov_thr} V")
        self.uv_thr_sel.config(text=f"{uv_thr} V")
        self.ot1_thr_sel.config(
            text=f"{ot1_thr} ({OT_THR_TO_CELCIUS_LU_TABLE[ot1_thr]}degC)"
        )
        self.ot2_thr_sel.config(
            text=f"{ot2_thr} ({OT_THR_TO_CELCIUS_LU_TABLE[ot2_thr]}degC)"
        )

    def set_ov_thr_ui(self):
        if not self.con_status:
            print("No board connected")
            return
        if self.is_thresh_locked or self.is_all_locked:
            print("WARNING: thresholds set locked")
            return
        else:
            ovt_in = float(self.ov_thr_input.get())
            set_ov_thr(ser=self.serial_con, id=self.id, new_ov_thr_v=ovt_in)
            self.logger.info(
                "Overvoltage threshold changed for slave %s from %s to %s V",
                self.id,
                self.ov_thr_sel.cget("text"),
                ovt_in,
            )
            self.ov_thr_sel.config(text=f"{ovt_in} V")
            self.log_full_memory()
            print("Set OVT done")

    def set_uv_thr_ui(self):
        if not self.con_status:
            print("No board connected")
            return
        if self.is_thresh_locked or self.is_all_locked:
            print("WARNING: thresholds set locked")
            return
        else:
            uvt_in = float(self.uv_thr_input.get())
            set_uv_thr(ser=self.serial_con, id=self.id, new_uv_thr_v=uvt_in)
            self.logger.info(
                "Undervoltage threshold changed for slave %s from %s to %s V",
                self.id,
                self.uv_thr_sel.cget("text"),
                uvt_in,
            )
            self.uv_thr_sel.config(text=f"{uvt_in} V")
            self.log_full_memory()
            print("Set UVT done")

    def set_ot1_thr_ui(self):
        if not self.con_status:
            print("No board connected")
            return
        if self.is_thresh_locked or self.is_all_locked:
            print("WARNING: thresholds set locked")
        else:
            ot1t_in = int(self.ot1_thr_input.get())
            if str(ot1t_in) not in list(OT_THR_TO_CELCIUS_LU_TABLE.values()):
                messagebox.showwarning(
                    "WARNING",
                    f"Valid temperatures are (degC): {[temp for temp in OT_THR_TO_CELCIUS_LU_TABLE_REVERSE.keys()]}",
                )
                return
            set_ot_thr(
                ser=self.serial_con, id=self.id, new_ot_thr_deg=ot1t_in, temp_id=1
            )
            self.logger.info(
                "Over temperature 1 threshold changed for slave %s from %s to %s (%sdegC)",
                self.id,
                self.ot1_thr_sel.cget("text"),
                OT_THR_TO_CELCIUS_LU_TABLE_REVERSE[ot1t_in],
                ot1t_in,
            )
            self.ot1_thr_sel.config(
                text=f"{OT_THR_TO_CELCIUS_LU_TABLE_REVERSE[ot1t_in]} ({ot1t_in}degC)"
            )
            self.ot1_thr_input.delete(0, tk.END)
            self.ot1_thr_input.insert(0, "Enter OT1_THR")
            self.log_full_memory()
            print("Set OT1T done")

    def set_ot2_thr_ui(self):
        if not self.con_status:
            print("No board connected")
            return
        if self.is_thresh_locked or self.is_all_locked:
            print("WARNING: thresholds set locked")
        else:
            ot2t_in = int(self.ot2_thr_input.get())
            if str(ot2t_in) not in list(OT_THR_TO_CELCIUS_LU_TABLE.values()):
                messagebox.showwarning(
                    "WARNING",
                    f"Valid temperatures are (degC): {[temp for temp in OT_THR_TO_CELCIUS_LU_TABLE_REVERSE.keys()]}",
                )
                return
            set_ot_thr(
                ser=self.serial_con, id=self.id, new_ot_thr_deg=ot2t_in, temp_id=2
            )
            self.logger.info(
                "Over temperature 2 threshold changed for slave %s from %s to %s (%sdegC)",
                self.id,
                self.ot2_thr_sel.cget("text"),
                OT_THR_TO_CELCIUS_LU_TABLE_REVERSE[ot2t_in],
                ot2t_in,
            )
            self.ot2_thr_sel.config(
                text=f"{OT_THR_TO_CELCIUS_LU_TABLE_REVERSE[ot2t_in]} ({ot2t_in}degC)"
            )
            self.ot2_thr_input.delete(0, tk.END)
            self.ot2_thr_input.insert(0, "Enter OT2_THR")
            self.log_full_memory()
            print("Set OT2T done")

    def update_alerts_and_faults(self):
        if not self.con_status:
            print("No board connected")
            return
        print("update Alerts & Faults")
        alerts = read_alerts(ser=self.serial_con, id=self.id)
        faults = read_faults(ser=self.serial_con, id=self.id)
        ov_cells = read_ov_cells(ser=self.serial_con, id=self.id)
        uv_cells = read_uv_cells(ser=self.serial_con, id=self.id)

        self.alerts_val[0].config(text=(alerts & 0x80) >> 7)
        self.alerts_val[1].config(text=(alerts & 0x40) >> 6)
        self.alerts_val[2].config(text=(alerts & 0x20) >> 5)
        self.alerts_val[3].config(text=(alerts & 0x10) >> 4)
        self.alerts_val[4].config(text=(alerts & 0x08) >> 3)
        self.alerts_val[5].config(text=(alerts & 0x04) >> 2)
        self.alerts_val[6].config(text=(alerts & 0x02) >> 1)
        self.alerts_val[7].config(text=alerts & 0x01)

        self.faults_val[2].config(text=(faults & 0x20) >> 5)
        self.faults_val[3].config(text=(faults & 0x10) >> 4)
        self.faults_val[4].config(text=(faults & 0x08) >> 3)
        self.faults_val[5].config(text=(faults & 0x04) >> 2)
        self.faults_val[6].config(text=(faults & 0x02) >> 1)
        self.faults_val[7].config(text=faults & 0x01)

        self.ov_cells_val[0].config(text=ov_cells & 0x01)
        self.ov_cells_val[1].config(text=(ov_cells & 0x02) >> 1)
        self.ov_cells_val[2].config(text=(ov_cells & 0x04) >> 2)
        self.ov_cells_val[3].config(text=(ov_cells & 0x08) >> 3)
        self.ov_cells_val[4].config(text=(ov_cells & 0x10) >> 4)
        self.ov_cells_val[5].config(text=(ov_cells & 0x20) >> 5)

        self.uv_cells_val[0].config(text=uv_cells & 0x01)
        self.uv_cells_val[1].config(text=(uv_cells & 0x02) >> 1)
        self.uv_cells_val[2].config(text=(uv_cells & 0x04) >> 2)
        self.uv_cells_val[3].config(text=(uv_cells & 0x08) >> 3)
        self.uv_cells_val[4].config(text=(uv_cells & 0x10) >> 4)
        self.uv_cells_val[5].config(text=(uv_cells & 0x20) >> 5)
