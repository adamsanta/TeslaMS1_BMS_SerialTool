import re
import tkinter as tk

from serial_interface import (
    BROADCAST_ADDR,
    con_serial_port,
    disco_serial_port,
    reset_slave,
    get_slave_id,
    set_slave_id,
)
from tkinter import messagebox


COM_PORT_PATTERN = r'^COM\d+$'

ALERT_REG_IMG = "../img/alert_status_register.png"
FAULT_REG_IMG = "../img/fault_status_register.png"

def check_com_port_format(comport_string):
    if re.match(COM_PORT_PATTERN, comport_string):
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
        
        self.id = None
        self.id_sel = None
        self.id_input = None
        self.id_update_button = None

        self.reset_button = None

        self.vbatt = None
        self.vcells = []
        self.temps = []

        self.update_ov_thr_button = None
        self.update_uv_thr_button = None
        self.update_ot_thr_button = None
        self.update_ut_thr_button = None

        self.alerts_list = ["~ID_assigned", "Gp3_valid", "OTP_ECC", "ALERT_SIG", "Too_hot", "Was_sleeping", "OVT1", "OVT2"]
        self.faults_list = ["_", "_", "INTERN_ISSUE", "FAULT_SIG", "PO_RESET", "CRC_ERR", ">UV_CELLS", ">OV_CELLS"]

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

    def create_com_reset_id_frame(self, main):
        # COM_PORT, Reset, ID
        com_reset_id_frame = tk.Frame(main, width=100, height=100, bg='paleturquoise4')
        com_reset_id_frame.grid(row=0, column=0, padx=10, pady=5)

        ## COM_PORT
        port_frame = tk.Frame(com_reset_id_frame, width=20, height=20, bg='paleturquoise3')
        port_frame.grid(row=0, column=0, padx=5, pady=5)
        
        self.com_port_sel = tk.Label(port_frame, text="COM_PORT: DISCO", width=20, fg="brown", font=("Helvetica", 10, "bold"))
        self.com_port_sel.grid(row=0, column=0, columnspan=2, padx=5, pady=5)
    
        self.com_port_input = tk.Entry(port_frame)
        self.com_port_input.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        self.com_port_input.insert(0, "Enter port here")

        tk.Button(port_frame, text="Set PORT", command=self.set_port).grid(row=2, column=0, padx=5, pady=5)
        tk.Button(port_frame, text="Disconnect", command=self.disco_port).grid(row=2, column=1, padx=5, pady=5)

        ## Reset
        reset_frame = tk.Frame(com_reset_id_frame, width=20, height=20, bg='paleturquoise3')
        reset_frame.grid(row=1, column=0, padx=5, pady=5)
        
        self.reset_button = tk.Button(reset_frame, text="Reset BMS", command=self.reset_board, state=tk.DISABLED)
        self.reset_button.grid(row=0, column=0, padx=5, pady=5)

        ## ID
        id_frame = tk.Frame(com_reset_id_frame, width=20, height=20, bg='paleturquoise3')
        id_frame.grid(row=2, column=0, padx=5, pady=5)
        
        self.id_sel = tk.Label(id_frame, text="ID: ?")
        self.id_sel.grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        
        self.id_update_button = tk.Button(id_frame, text="Set ID:", command=self.set_id, state=tk.DISABLED)
        self.id_update_button.grid(row=1, column=0, padx=5, pady=5)

        self.id_input = tk.Entry(id_frame)
        self.id_input.grid(row=1, column=1, padx=5, pady=5)
        self.id_input.insert(0, "Enter ID here")
        
    def create_measurements_frame(self, main):
        # Voltages, Temperatures
        measurements_frame = tk.Frame(main, width=100, height=100, bg='paleturquoise4')
        measurements_frame.grid(row=0, column=1, padx=10, pady=5)

        # Voltages
        VOLT_ARRAY_WIDTH = 10
        voltages_frame = tk.Frame(measurements_frame, width=20, height=20, bg='paleturquoise3')
        voltages_frame.grid(row=0, column=0, padx=5, pady=5)

        tk.Label(voltages_frame, text="Voltages", width=VOLT_ARRAY_WIDTH, relief='raised').grid(row=0, column=0)

        tk.Label(voltages_frame, text="V", width=VOLT_ARRAY_WIDTH, relief='raised').grid(row=0, column=1)

        tk.Label(voltages_frame, text="Vbatt", width=VOLT_ARRAY_WIDTH, relief='groove').grid(row=1, column=0)
        self.vbatt = tk.Label(voltages_frame, text="?", width=VOLT_ARRAY_WIDTH, relief='groove')
        self.vbatt.grid(row=1, column=1)

        self.vcells = []
        for i in range(1,7):
            tk.Label(voltages_frame, text=f"Vcell_{i}", width=VOLT_ARRAY_WIDTH, relief='groove').grid(row=1+i, column=0)
            current_vcell = tk.Label(voltages_frame, text="?", width=VOLT_ARRAY_WIDTH, relief='groove')
            current_vcell.grid(row=1+i, column=1)
            self.vcells.append(current_vcell)

        # Temperatures
        TEMP_ARRAY_WIDTH = 10
        temp_frame = tk.Frame(measurements_frame, width=20, height=20, bg='paleturquoise3')
        temp_frame.grid(row=1, column=0, padx=5, pady=5)

        tk.Label(temp_frame, text="Temperature", width=TEMP_ARRAY_WIDTH, relief='raised').grid(row=0, column=0)
        tk.Label(temp_frame, text="°C", width=TEMP_ARRAY_WIDTH, relief='raised').grid(row=0, column=1)

        tk.Label(temp_frame, text="Temp1", width=TEMP_ARRAY_WIDTH, relief='groove').grid(row=1, column=0)
        temp1 = tk.Label(temp_frame, text="?", width=TEMP_ARRAY_WIDTH, relief='groove')
        temp1.grid(row=1, column=1)

        tk.Label(temp_frame, text="Temp2", width=TEMP_ARRAY_WIDTH, relief='groove').grid(row=2, column=0)
        temp2 = tk.Label(temp_frame, text="?", width=TEMP_ARRAY_WIDTH, relief='groove')
        temp2.grid(row=2, column=1)

        self.temps = [temp1, temp2]

        # V and T update button  
        v_t_update_frame = tk.Frame(measurements_frame, width=20, height=20, bg='paleturquoise3')
        v_t_update_frame.grid(row=2, column=0, padx=5, pady=5)

        tk.Button(v_t_update_frame, text="Update V and T", command=self.update_meas).grid(row=1, column=0, padx=5, pady=5)

    def create_secu_thresholds_frame(self, main):
        # Security thresholds (volt and temp)
        THR_BOX_WIDTH = 10
        secu_thresholds_frame = tk.Frame(main, width=100, height=100, bg='paleturquoise4')
        secu_thresholds_frame.grid(row=0, column=2, padx=10, pady=5)

        # Voltage thresholds
        v_thr_frame = tk.Frame(secu_thresholds_frame, width=20, height=20, bg='paleturquoise3')
        v_thr_frame.grid(row=0, column=0, padx=5, pady=5)
    
        self.ov_thr_sel = tk.Label(v_thr_frame, width=THR_BOX_WIDTH, text="OV_THR: ?")
        self.ov_thr_sel.grid(row=0, column=0)
        self.uv_thr_sel = tk.Label(v_thr_frame, width=THR_BOX_WIDTH, text="UV_THR: ?")
        self.uv_thr_sel.grid(row=1, column=0)

        self.ov_thr_input = tk.Entry(v_thr_frame, width=int(1.5*THR_BOX_WIDTH))
        self.ov_thr_input.grid(row=0, column=1)
        self.ov_thr_input.insert(0, "Enter OV_THR")
        self.uv_thr_input = tk.Entry(v_thr_frame, width=int(1.5*THR_BOX_WIDTH))
        self.uv_thr_input.grid(row=1, column=1)
        self.uv_thr_input.insert(0, "Enter UV_THR")

        self.update_ov_thr_button = tk.Button(v_thr_frame, text="Set", command=self.update_ov_thr, state=tk.DISABLED)
        self.update_ov_thr_button.grid(row=0, column=3)
        self.update_uv_thr_button = tk.Button(v_thr_frame, text="Set", command=self.update_uv_thr, state=tk.DISABLED)
        self.update_uv_thr_button.grid(row=1, column=3)

        # Temperature thresholds
        t_thr_frame = tk.Frame(secu_thresholds_frame, width=20, height=20, bg='paleturquoise3')
        t_thr_frame.grid(row=1, column=0, padx=5, pady=5)
    
        self.ot_thr_sel = tk.Label(t_thr_frame, width=THR_BOX_WIDTH, text="OT_THR: ?")
        self.ot_thr_sel.grid(row=0, column=0)
        self.ut_thr_sel = tk.Label(t_thr_frame, width=THR_BOX_WIDTH, text="UT_THR: ?")
        self.ut_thr_sel.grid(row=1, column=0)

        self.ot_thr_input = tk.Entry(t_thr_frame, width=int(1.5*THR_BOX_WIDTH))
        self.ot_thr_input.grid(row=0, column=1)
        self.ot_thr_input.insert(0, "Enter OT_THR")
        self.ut_thr_input = tk.Entry(t_thr_frame, width=int(1.5*THR_BOX_WIDTH))
        self.ut_thr_input.grid(row=1, column=1)
        self.ut_thr_input.insert(0, "Enter UT_THR")

        self.update_ot_thr_button = tk.Button(t_thr_frame, text="Set", command=self.update_ot_thr, state=tk.DISABLED)
        self.update_ot_thr_button.grid(row=0, column=3)
        self.update_ut_thr_button = tk.Button(t_thr_frame, text="Set", command=self.update_ut_thr, state=tk.DISABLED)
        self.update_ut_thr_button.grid(row=1, column=3)

    def create_alerts_and_faults_frame(self, main):
        # Alerts and Faults status
        alerts_and_faults_frame = tk.Frame(main, width=100, height=100, bg='paleturquoise4')
        alerts_and_faults_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=5)

        # Alerts
        ALERTS_ARRAY_WIDTH = 10
        alerts_frame = tk.Frame(alerts_and_faults_frame, width=20, height=20, bg='paleturquoise3')
        alerts_frame.grid(row=0, column=0, padx=5, pady=5)

        tk.Label(alerts_frame, text="Alert", width=ALERTS_ARRAY_WIDTH, relief='raised').grid(row=0, column=0)
        tk.Label(alerts_frame, text="State", width=ALERTS_ARRAY_WIDTH, relief='raised').grid(row=1, column=0)

        for i, alert in enumerate(self.alerts_list):
            tk.Label(alerts_frame, text=alert, width=ALERTS_ARRAY_WIDTH, relief='groove').grid(row=0, column=1+i)
            tk.Label(alerts_frame, text="?", width=ALERTS_ARRAY_WIDTH, relief='groove').grid(row=1, column=1+i)

        # Faults
        FAULTS_ARRAY_WIDTH = 10
        faults_frame = tk.Frame(alerts_and_faults_frame, width=20, height=20, bg='paleturquoise3')
        faults_frame.grid(row=1, column=0, padx=5, pady=5)

        tk.Label(faults_frame, text="Fault", width=FAULTS_ARRAY_WIDTH, relief='raised').grid(row=0, column=0)
        tk.Label(faults_frame, text="State", width=FAULTS_ARRAY_WIDTH, relief='raised').grid(row=1, column=0)

        for i, alert in enumerate(self.faults_list):
            tk.Label(faults_frame, text=alert, width=FAULTS_ARRAY_WIDTH, relief='groove').grid(row=0, column=1+i)
            tk.Label(faults_frame, text="?", width=FAULTS_ARRAY_WIDTH, relief='groove').grid(row=1, column=1+i)

        # OV & UV cells
        OVUV_CELLS_ARRAY_WIDTH = 10
        ovuv_cells_frame = tk.Frame(alerts_and_faults_frame, width=20, height=20, bg='paleturquoise3')
        ovuv_cells_frame.grid(row=2, column=0, padx=5, pady=5)

        tk.Label(ovuv_cells_frame, text="Cell num", width=FAULTS_ARRAY_WIDTH, relief='raised').grid(row=0, column=0)
        tk.Label(ovuv_cells_frame, text="V>OVth?", width=FAULTS_ARRAY_WIDTH, relief='raised').grid(row=1, column=0)
        tk.Label(ovuv_cells_frame, text="V<UVth?", width=FAULTS_ARRAY_WIDTH, relief='raised').grid(row=2, column=0)

        for i in range(1,7):
            tk.Label(ovuv_cells_frame, text=i, width=FAULTS_ARRAY_WIDTH, relief='raised').grid(row=0, column=1+i)
            tk.Label(ovuv_cells_frame, text="?", width=FAULTS_ARRAY_WIDTH, relief='groove').grid(row=1, column=1+i)
            tk.Label(ovuv_cells_frame, text="?", width=FAULTS_ARRAY_WIDTH, relief='groove').grid(row=2, column=1+i)

        # Alerts and faults update and info buttons
        alerts_and_faults_update_frame = tk.Frame(alerts_and_faults_frame, width=20, height=20, bg='paleturquoise3')
        alerts_and_faults_update_frame.grid(row=3, column=0, padx=5, pady=5)

        tk.Button(alerts_and_faults_update_frame, text="Update Alerts and Faults", command=self.update_alerts_and_faults).grid(row=0, column=0, padx=5, pady=5)
        tk.Button(alerts_and_faults_update_frame, text="Alerts details", command=self.show_alerts_info).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(alerts_and_faults_update_frame, text="Faults details", command=self.show_faults_info).grid(row=0, column=2, padx=5, pady=5)

    def create_locks_frame(self, main):
        # Config locks
        lock_frame = tk.Frame(main, width=100, height=100, bg='paleturquoise4')
        lock_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=5)

        # Global lock (lock everything that can be locked)
        global_lock_frame = tk.Frame(lock_frame, width=20, height=20, bg='paleturquoise3')
        global_lock_frame.grid(row=0, column=0, padx=5, pady=5)
        # We could use directly the Checkbutton's variable parameter but command will allow us to add more features to a switch action in the future
        # Lock by default
        self.global_lock = tk.IntVar(value=1)
        tk.Checkbutton(global_lock_frame, text="GLOBAL locked", variable=self.global_lock, command=self.lock_all).grid(row=0, column=0)
        
        # BMS ID lock
        id_lock_frame = tk.Frame(lock_frame, width=20, height=20, bg='paleturquoise3')
        id_lock_frame.grid(row=0, column=1, padx=5, pady=5)
        # Lock by default
        self.id_lock = tk.IntVar(value=1)
        self.id_lock_checkbutton = tk.Checkbutton(id_lock_frame, text="ID locked", variable=self.id_lock, command=self.lock_id, state=tk.DISABLED)
        self.id_lock_checkbutton.grid(row=0, column=0)

        # Threshold lock
        thresholds_lock_frame = tk.Frame(lock_frame, width=20, height=20, bg='paleturquoise3')
        thresholds_lock_frame.grid(row=0, column=2, padx=5, pady=5)
        # Lock by default
        self.thresh_lock = tk.IntVar(value=1)
        self.thresh_lock_checkbutton = tk.Checkbutton(thresholds_lock_frame, text="Threshold locked", variable=self.thresh_lock, command=self.lock_thresh, state=tk.DISABLED)
        self.thresh_lock_checkbutton.grid(row=0, column=0)
        
        # Reset lock
        reset_lock_frame = tk.Frame(lock_frame, width=20, height=20, bg='paleturquoise3')
        reset_lock_frame.grid(row=0, column=3, padx=5, pady=5)
        # Lock by default
        self.reset_lock = tk.IntVar(value=1)
        self.reset_lock_checkbutton = tk.Checkbutton(reset_lock_frame, text="Reset locked", variable=self.reset_lock, command=self.lock_reset, state=tk.DISABLED)
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
            self.update_ov_thr_button.config(state=tk.DISABLED)
            self.update_uv_thr_button.config(state=tk.DISABLED)
            self.update_ot_thr_button.config(state=tk.DISABLED)
            self.update_ut_thr_button.config(state=tk.DISABLED)
            self.reset_button.config(state=tk.DISABLED)
            print("Is all locked ?: ", self.is_all_locked)
        else:
            self.is_all_locked = False
            self.id_lock_checkbutton.config(state=tk.NORMAL)
            self.thresh_lock_checkbutton.config(state=tk.NORMAL)
            self.reset_lock_checkbutton.config(state=tk.NORMAL)
            if self.id_lock.get()!=1:
                self.id_update_button.config(state=tk.NORMAL)
            if self.thresh_lock.get()!=1:
                self.update_ov_thr_button.config(state=tk.NORMAL)
                self.update_uv_thr_button.config(state=tk.NORMAL)
                self.update_ot_thr_button.config(state=tk.NORMAL)
                self.update_ut_thr_button.config(state=tk.NORMAL)
            if self.reset_lock.get()!=1:
                self.reset_button.config(state=tk.NORMAL)
            print("Is all locked ?: ", self.is_all_locked)

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
            self.update_ov_thr_button.config(state=tk.DISABLED)
            self.update_uv_thr_button.config(state=tk.DISABLED)
            self.update_ot_thr_button.config(state=tk.DISABLED)
            self.update_ut_thr_button.config(state=tk.DISABLED)
            print("Are Thresholds locked ?: ", self.is_thresh_locked)
        else:
            self.is_thresh_locked = False
            self.update_ov_thr_button.config(state=tk.NORMAL)
            self.update_uv_thr_button.config(state=tk.NORMAL)
            self.update_ot_thr_button.config(state=tk.NORMAL)
            self.update_ut_thr_button.config(state=tk.NORMAL)
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
        print(self.is_reset_locked)
        print(self.is_all_locked)
        print(self.is_reset_locked or self.is_all_locked)
        if self.is_reset_locked or self.is_all_locked:
            print("WARNING: Reset locked")
        else:
            reset_slave(ser=self.serial_con, id=self.id)
            print(f"Reset done for {self.id}")
        # Board ID should have got back to 0
        self.id = get_slave_id(ser=self.serial_con, id=BROADCAST_ADDR)
        self.id_sel.config(text=f"ID: {self.id}")

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

    def disco_port(self):
        if self.serial_con==None:
            messagebox.showwarning("WARNING", f"Nothing connected actually.")
            return False
        if not disco_serial_port(self.serial_con):
            messagebox.showwarning("WARNING", f"Failed to disconnect from {self.serial_con.port}.")
            return False
        self.com_port_sel.config(text="COM_PORT: DISCO", fg="brown", font=("Helvetica", 10, "bold"))
        # Reset the board ID value
        self.id = ""
        self.id_sel.config(text=f"ID: ?")
        return True

    def set_port(self):
        port_name = self.com_port_input.get()
        if not check_com_port_format(port_name):
            messagebox.showwarning("WARNING", f"Bad COM PORT format entered ({port_name}), should be COM[num].")
            return False
        self.serial_con = con_serial_port(port_name)
        if self.serial_con==None:
            messagebox.showwarning("WARNING", f"Connection to {port_name} failed.")
            return False
        self.com_port_sel.config(text=f"COM_PORT: {port_name} (CON)", fg="chartreuse4", font=("Helvetica", 10, "bold"))
        # Get the board ID to be able to address it
        self.id = get_slave_id(ser=self.serial_con, id=BROADCAST_ADDR)
        self.id_sel.config(text=f"ID: {self.id}")
        return True

    def set_id(self):
        id_in = int(self.id_input.get())
        if self.is_id_locked or self.is_all_locked:
            print("WARNING: ID locked")
        else:
            if set_slave_id(ser=self.serial_con, old_id=self.id, new_id=id_in)!=-1:
                self.id_sel.config(text=f"ID: {(id_in if id_in!="" else "?")}")
                self.id = id_in
            else:
                messagebox.showwarning("WARNING", f"Setting ID to {id_in} failed.")

    def update_meas(self):
        self.vbatt.config(text='ok')
        for vcell in self.vcells:
            vcell.config(text='ok')
        for temp in self.temps:
            temp.config(text='ok')

    def update_ov_thr(self):
        if self.is_reset_locked or self.is_all_locked:
            print("WARNING: thresholds update locked")
        else:
            print("Set OVT done")

    def update_uv_thr(self):
        if self.is_reset_locked or self.is_all_locked:
            print("WARNING: thresholds update locked")
        else:
            print("Set UVT done")

    def update_ot_thr(self):
        if self.is_reset_locked or self.is_all_locked:
            print("WARNING: thresholds update locked")
        else:
            print("Set OTT done")

    def update_ut_thr(self):
        if self.is_reset_locked or self.is_all_locked:
            print("WARNING: thresholds update locked")
        else:
            print("Set UTT done")

    def update_alerts_and_faults(self):
        print("update Alerts & Faults")
