# מדידת מתח וזרם בטאב הראשי (Main Tab)

## סקירה כללית

בטאב הראשי (Main Tab) של המערכת, ניתן לבצע מדידות מתח וזרם באמצעות מכשיר Keithley 2450 SMU (Source Measure Unit). המערכת תומכת בשני מצבי פעולה:

1. **מצב מתח (Voltage Mode)**: מקור מתח / מדידת זרם
2. **מצב זרם (Current Mode)**: מקור זרם / מדידת מתח

בכל מצב, אחד מהפרמטרים מוגדר לערך קבוע (bias), והפרמטר השני נמדד.

---

## איך זה עובד

### 1. בחירת מצב המדידה

המשתמש בוחר את מצב המדידה באמצעות כפתורי הרדיו בממשק:

```python
# קוד מ-main_tab.py, שורות 285-293
self.keithley_mode_var = ctk.StringVar(value="voltage")
mode_radio_frame = ctk.CTkFrame(mode_frame)
mode_radio_frame.pack(pady=2)
ctk.CTkRadioButton(mode_radio_frame, text="Source Voltage / Measure Current", 
                  variable=self.keithley_mode_var, value="voltage",
                  command=self.on_keithley_mode_change).pack(side='left', padx=5)
ctk.CTkRadioButton(mode_radio_frame, text="Source Current / Measure Voltage", 
                  variable=self.keithley_mode_var, value="current",
                  command=self.on_keithley_mode_change).pack(side='left', padx=5)
```

### 2. הגדרת ערכי ה-Bias והגבלות

#### מצב מתח (Voltage Mode):
- **Bias Voltage**: ערך המתח הקבוע (V)
- **Current Limit**: הגבלת הזרם המקסימלי (A)

#### מצב זרם (Current Mode):
- **Bias Current**: ערך הזרם הקבוע (A)
- **Voltage Limit**: הגבלת המתח המקסימלי (V)

### 3. הפעלת ה-SMU

כאשר המשתמש מפעיל את ה-SMU (דרך המתג "Enable SMU Output"), המערכת מגדירה את ה-SMU בהתאם למצב שנבחר:

```python
# קוד מ-main_tab.py, שורות 1141-1177
def on_keithley_output_toggle(self):
    """Handle Keithley output enable/disable toggle"""
    enabled = self.keithley_output_var.get()
    self.keithley_output_enabled = enabled
    
    if not enabled:
        # Turn off SMU output
        try:
            if self.hw_controller.smu is not None and hasattr(self.hw_controller, 'smu'):
                self.hw_controller.stop_smu()
                if self.update_queue:
                    self.update_queue.put(('UPDATE_STATUS', 'SMU output turned OFF'))
        except Exception as e:
            print(f"Error turning off SMU: {e}")
    else:
        # Setup and enable SMU output based on mode
        try:
            if self.hw_controller.smu is not None and hasattr(self.hw_controller, 'smu'):
                mode = self.keithley_mode_var.get()
                bias_value = float(self.keithley_bias_entry.get())
                
                if mode == "voltage":
                    current_limit = float(self.keithley_current_limit_entry.get())
                    self.hw_controller.setup_smu_for_iv_measurement(current_limit)
                    self.hw_controller.set_smu_voltage(bias_value, current_limit)
                else:  # current mode
                    voltage_limit = float(self.keithley_voltage_limit_entry.get())
                    # Setup for current source mode
                    self.hw_controller.setup_smu_for_current_source(voltage_limit)
                    self.hw_controller.set_smu_current(bias_value)
                
                if self.update_queue:
                    self.update_queue.put(('UPDATE_STATUS', f'SMU output enabled: {bias_value} {"V" if mode == "voltage" else "A"}'))
        except (ValueError, Exception) as e:
            print(f"Error enabling SMU: {e}")
            self.keithley_output_var.set(False)
            self.keithley_output_enabled = False
            if self.update_queue:
                self.update_queue.put(('UPDATE_STATUS', f'Error enabling SMU: {e}'))
```

### 4. הגדרת ה-SMU למצב מתח (Voltage Source / Current Measurement)

כאשר נבחר מצב מתח, המערכת קוראת לפונקציה `setup_smu_for_iv_measurement()`:

```python
# קוד מ-keithley_2450.py, שורות 253-318
def setup_for_iv_measurement(self, current_limit=0.1, voltage_range=None):
    """
    Setup SMU for I-V measurement
    
    Args:
        current_limit: Current limit (A)
        voltage_range: Voltage range (V). If None, will use default 20V range.
                      Keithley 2450 supports: 0.2V, 2V, 20V, 200V
        
    Returns:
        True if successful, False otherwise
    """
    if not self.smu:
        print("SMU not connected. Cannot setup SMU.")
        return False
    
    try:
        # Configure as voltage source
        print("Sending: SOUR:FUNC VOLT")
        self.smu.write(self.scpi.set_source_voltage())
        
        # Set voltage range (important for allowing voltages > 2V)
        if voltage_range is None:
            # Default to 20V range to allow higher voltages
            voltage_range = 20.0
        else:
            # Select the smallest range that covers the requested voltage
            if voltage_range <= 0.2:
                voltage_range = 0.2
            elif voltage_range <= 2.0:
                voltage_range = 2.0
            elif voltage_range <= 20.0:
                voltage_range = 20.0
            else:
                voltage_range = 200.0
        
        print(f"Sending: SOUR:VOLT:RANG {voltage_range}")
        self.smu.write(self.scpi.set_voltage_range(voltage_range))
        
        # Configure measurement function to current
        print('Sending: SENS:FUNC "CURR"')
        self.smu.write(self.scpi.set_sense_current())
        
        # Set current limit/compliance
        print(f'Sending: SOUR:VOLT:ILIM {current_limit}')
        self.smu.write(self.scpi.set_current_limit(current_limit))
        
        # Set NPLC
        print('Sending: SENS:CURR:NPLC 1')
        self.smu.write(self.scpi.set_nplc(1))
        
        # Set current range
        print(f'Sending: SENS:CURR:RANG {current_limit}')
        self.smu.write(self.scpi.set_current_range(current_limit))
        
        # Turn output on
        print("Sending: OUTP ON")
        self.smu.write(self.scpi.output_on())
        
        print(f"SMU configured for I-V measurement (voltage range: {voltage_range}V, current limit: {current_limit}A)")
        return True
    except Exception as e:
        print(f"Error setting up SMU: {e}")
        import traceback
        traceback.print_exc()
        return False
```

**פקודות SCPI שנשלחות:**
1. `SOUR:FUNC VOLT` - הגדרת מקור למתח
2. `SOUR:VOLT:RANG {voltage_range}` - הגדרת טווח המתח
3. `SENS:FUNC "CURR"` - הגדרת מדידה לזרם
4. `SOUR:VOLT:ILIM {current_limit}` - הגדרת הגבלת זרם
5. `SENS:CURR:NPLC 1` - הגדרת מספר מחזורי קו חשמל
6. `SENS:CURR:RANG {current_limit}` - הגדרת טווח מדידת זרם
7. `OUTP ON` - הפעלת הפלט

לאחר מכן, המערכת מגדירה את ערך המתח:

```python
# קוד מ-keithley_2450.py, שורות 390-409
def set_voltage(self, voltage):
    """
    Set SMU output voltage
    
    Args:
        voltage: Voltage to set (V)
        
    Returns:
        True if successful, False otherwise
    """
    if not self.smu:
        print("SMU not connected. Cannot set voltage.")
        return False
    
    try:
        self.smu.write(self.scpi.set_voltage(voltage))
        return True
    except Exception as e:
        print(f"Error setting SMU voltage: {e}")
        return False
```

**פקודת SCPI:**
- `SOUR:VOLT {voltage}` - הגדרת ערך המתח

### 5. הגדרת ה-SMU למצב זרם (Current Source / Voltage Measurement)

כאשר נבחר מצב זרם, המערכת קוראת לפונקציה `setup_for_current_source_measurement()`:

```python
# קוד מ-keithley_2450.py, שורות 411-463
def setup_for_current_source_measurement(self, voltage_limit=20.0, current_range=None):
    """
    Setup SMU for current source / voltage measurement mode
    
    Args:
        voltage_limit: Voltage limit (compliance) (V)
        current_range: Current range (A). If None, will use default range.
        
    Returns:
        True if successful, False otherwise
    """
    if not self.smu:
        print("SMU not connected. Cannot setup SMU.")
        return False
    
    try:
        # Configure as current source
        print("Sending: SOUR:FUNC CURR")
        self.smu.write(self.scpi.set_source_current())
        
        # Set current range
        if current_range is None:
            current_range = 0.1  # Default to 100mA range
        print(f"Sending: SOUR:CURR:RANG {current_range}")
        self.smu.write(self.scpi.set_current_source_range(current_range))
        
        # Set voltage limit (compliance)
        print(f"Sending: SOUR:CURR:VLIM {voltage_limit}")
        self.smu.write(self.scpi.set_voltage_limit(voltage_limit))
        
        # Configure measurement function to voltage
        print('Sending: SENS:FUNC "VOLT"')
        self.smu.write(self.scpi.set_sense_voltage())
        
        # Set voltage range
        print(f"Sending: SENS:VOLT:RANG {voltage_limit}")
        self.smu.write(self.scpi.set_voltage_measurement_range(voltage_limit))
        
        # Set NPLC
        print('Sending: SENS:VOLT:NPLC 1')
        self.smu.write('SENS:VOLT:NPLC 1')
        
        # Turn output on
        print("Sending: OUTP ON")
        self.smu.write(self.scpi.output_on())
        
        print(f"SMU configured for current source mode (voltage limit: {voltage_limit}V, current range: {current_range}A)")
        return True
    except Exception as e:
        print(f"Error setting up SMU for current source: {e}")
        import traceback
        traceback.print_exc()
        return False
```

**פקודות SCPI שנשלחות:**
1. `SOUR:FUNC CURR` - הגדרת מקור לזרם
2. `SOUR:CURR:RANG {current_range}` - הגדרת טווח הזרם
3. `SOUR:CURR:VLIM {voltage_limit}` - הגדרת הגבלת מתח (compliance)
4. `SENS:FUNC "VOLT"` - הגדרת מדידה למתח
5. `SENS:VOLT:RANG {voltage_limit}` - הגדרת טווח מדידת מתח
6. `SENS:VOLT:NPLC 1` - הגדרת מספר מחזורי קו חשמל למדידת מתח
7. `OUTP ON` - הפעלת הפלט

לאחר מכן, המערכת מגדירה את ערך הזרם:

```python
# קוד מ-keithley_2450.py, שורות 465-484
def set_current(self, current):
    """
    Set SMU output current
    
    Args:
        current: Current to set (A)
        
    Returns:
        True if successful, False otherwise
    """
    if not self.smu:
        print("SMU not connected. Cannot set current.")
        return False
    
    try:
        self.smu.write(self.scpi.set_current(current))
        return True
    except Exception as e:
        print(f"Error setting SMU current: {e}")
        return False
```

**פקודת SCPI:**
- `SOUR:CURR {current}` - הגדרת ערך הזרם

### 6. ביצוע המדידות במהלך הניסוי

במהלך הניסוי, המערכת מבצעת מדידות בכל איטרציה של הלולאה:

```python
# קוד מ-main_tab.py, שורות 1414-1430
# Read Keithley measurements if enabled
keithley_voltage = None
keithley_current = None
if self.keithley_output_enabled and self.hw_controller.smu is not None:
    try:
        # Get current mode to pass to measurement function
        current_mode = self.keithley_mode_var.get()  # "voltage" or "current"
        
        # Measure with correct mode
        smu_measurement = self.hw_controller.measure_smu(mode=current_mode)
        if smu_measurement:
            keithley_voltage = smu_measurement.get('voltage', None)
            keithley_current = smu_measurement.get('current', None)
            
            # Update display
            if keithley_voltage is not None:
                self.keithley_voltage_label.configure(text=f'{keithley_voltage:.4f} V')
            if keithley_current is not None:
                self.keithley_current_label.configure(text=f'{keithley_current:.6f} A')
    except Exception as e:
        print(f"[EXPERIMENT_THREAD] Error reading Keithley: {e}")
```

הפונקציה `measure_smu()` קוראת ל-`measure()` של ה-Keithley ומעבירה את המצב:

```python
# קוד מ-hardware_controller.py, שורות 169-172
def measure_smu(self, mode="voltage"):
    """
    Measure voltage and current from SMU
    
    Args:
        mode: "voltage" (Source Voltage / Measure Current) 
              OR "current" (Source Current / Measure Voltage)
    """
    return self.smu.measure(mode=mode)
```

### 7. פונקציית המדידה בפועל

פונקציית המדידה בפועל (מתוקנת):

```python
# קוד מ-keithley_2450.py, שורות 486-540
def measure(self, mode="voltage"):
    """
    Measure voltage and current from SMU
    
    Args:
        mode: "voltage" (Source Voltage / Measure Current) 
              OR "current" (Source Current / Measure Voltage)
    
    Returns:
        Dictionary with voltage and current, or None on error
    """
    if not self.smu:
        return None
    
    try:
        data = {}
        
        if mode == "voltage":
            # Source Voltage mode: We're sourcing voltage, measuring current
            # The important measurement is CURRENT
            current_string = self.smu.query(self.scpi.measure_current())
            data['current'] = float(current_string)
            
            # Also measure voltage to get actual measured value (not just setting)
            voltage_string = self.smu.query(self.scpi.measure_voltage())
            data['voltage'] = float(voltage_string)
            
        elif mode == "current":
            # Source Current mode: We're sourcing current, measuring voltage
            # The important measurement is VOLTAGE
            voltage_string = self.smu.query(self.scpi.measure_voltage())
            data['voltage'] = float(voltage_string)
            
            # Also measure current to get actual measured value
            current_string = self.smu.query(self.scpi.measure_current())
            data['current'] = float(current_string)
        else:
            print(f"Unknown mode: {mode}. Using default voltage mode.")
            # Fallback to voltage mode
            current_string = self.smu.query(self.scpi.measure_current())
            data['current'] = float(current_string)
            voltage_string = self.smu.query(self.scpi.measure_voltage())
            data['voltage'] = float(voltage_string)
        
        return data
    except Exception as e:
        print(f"Error measuring SMU: {e}")
        import traceback
        traceback.print_exc()
        return None
```

**פקודות SCPI שנשלחות:**

**במצב Voltage (Source Voltage / Measure Current):**
1. `MEAS:CURR?` - מדידת זרם (המדידה החשובה)
2. `MEAS:VOLT?` - מדידת מתח (לשם דיוק)

**במצב Current (Source Current / Measure Voltage):**
1. `MEAS:VOLT?` - מדידת מתח (המדידה החשובה)
2. `MEAS:CURR?` - מדידת זרם (לשם דיוק)

**תיקון חשוב:** הפונקציה עברה תיקון כדי למדוד נכון בשני המצבים. במצב Current, הפונקציה משתמשת ב-`MEAS:VOLT?` למדידת המתח בפועל, ולא רק בקריאת ההגדרה.

### 8. שמירת הנתונים

הנתונים נשמרים במערכים ובקובץ הניסוי:

```python
# קוד מ-main_tab.py, שורות 1464-1473
# Store Keithley data for graphing (synchronized with time)
self.keithley_time_data.append(elapsed_time_from_start)
if keithley_voltage is not None:
    self.keithley_voltage_data.append(keithley_voltage)
else:
    self.keithley_voltage_data.append(0.0)
if keithley_current is not None:
    self.keithley_current_data.append(keithley_current)
else:
    self.keithley_current_data.append(0.0)
```

```python
# קוד מ-main_tab.py, שורות 1475-1487
data_point = {
    "time": elapsed_time_from_start,
    "flow_setpoint": self.current_flow_rate,
    "pump_flow_read": pump_data['flow'],
    "pressure_read": pressure if pressure is not None else "",
    "temp_read": temperature if temperature is not None else "",
    "level_read": level if level is not None else "",
    "voltage": keithley_voltage if keithley_voltage is not None else "",
    "current": keithley_current if keithley_current is not None else "",
    "target_voltage": float(self.keithley_bias_entry.get()) if self.keithley_output_enabled else ""
}

self.data_handler.append_data(data_point)
```

---

## סיכום - איך זה עובד

### מצב מתח (Voltage Mode):
1. **מקור**: מתח מוגדר לערך קבוע (Bias Voltage)
2. **מדידה**: זרם נמדד אוטומטית
3. **הגבלה**: זרם מוגבל לערך מקסימלי (Current Limit)

**פקודות SCPI עיקריות:**
- `SOUR:FUNC VOLT` - מקור מתח
- `SENS:FUNC "CURR"` - מדידת זרם
- `SOUR:VOLT {voltage}` - הגדרת מתח
- `MEAS:CURR?` - מדידת זרם (המדידה החשובה)
- `MEAS:VOLT?` - מדידת מתח (לשם דיוק)

### מצב זרם (Current Mode):
1. **מקור**: זרם מוגדר לערך קבוע (Bias Current)
2. **מדידה**: מתח נמדד אוטומטית
3. **הגבלה**: מתח מוגבל לערך מקסימלי (Voltage Limit)

**פקודות SCPI עיקריות:**
- `SOUR:FUNC CURR` - מקור זרם
- `SENS:FUNC "VOLT"` - מדידת מתח
- `SOUR:CURR {current}` - הגדרת זרם
- `MEAS:VOLT?` - מדידת מתח (המדידה החשובה) ✅ **תוקן!**
- `MEAS:CURR?` - מדידת זרם (לשם דיוק)

---

## קבצים רלוונטיים

1. **gui/tabs/main_tab.py** - ממשק המשתמש וניהול המדידות
2. **hardware/smu/keithley_2450.py** - תקשורת עם מכשיר Keithley 2450
3. **hardware/hardware_controller.py** - ממשק אחיד לכל החומרה
4. **hardware/smu/scpi_commands.py** - פקודות SCPI

---

## הערות טכניות

1. **Thread Safety**: המדידות מתבצעות בתוך thread נפרד (`experiment_thread`) כדי לא לחסום את ממשק המשתמש.

2. **Error Handling**: כל קריאה ל-SMU עטופה ב-try-except כדי למנוע קריסות.

3. **Simulation Mode**: אם ה-SMU לא מחובר, המערכת עוברת למצב סימולציה.

4. **Data Storage**: הנתונים נשמרים הן במערכים למיפוי גרפים בזמן אמת והן בקובץ Excel לניתוח מאוחר יותר.

---

## דוגמאות קוד מלאות

### הגדרת SMU למצב מתח

```python
# מ-main_tab.py, שורות 1320-1324
if mode == "voltage":
    current_limit = float(self.keithley_current_limit_entry.get())
    print(f"[EXPERIMENT_THREAD] Setting up Keithley: Voltage mode, Bias={bias_value}V, Limit={current_limit}A")
    self.hw_controller.setup_smu_for_iv_measurement(current_limit)
    self.hw_controller.set_smu_voltage(bias_value, current_limit)
```

### הגדרת SMU למצב זרם

```python
# מ-main_tab.py, שורות 1325-1329
else:  # current mode
    voltage_limit = float(self.keithley_voltage_limit_entry.get())
    print(f"[EXPERIMENT_THREAD] Setting up Keithley: Current mode, Bias={bias_value}A, Limit={voltage_limit}V")
    self.hw_controller.setup_smu_for_current_source(voltage_limit)
    self.hw_controller.set_smu_current(bias_value)
```

### ביצוע מדידה

```python
# מ-main_tab.py, שורות 1417-1430 (מתוקן)
if self.keithley_output_enabled and self.hw_controller.smu is not None:
    try:
        # Get current mode to pass to measurement function
        current_mode = self.keithley_mode_var.get()  # "voltage" or "current"
        
        # Measure with correct mode
        smu_measurement = self.hw_controller.measure_smu(mode=current_mode)
        if smu_measurement:
            keithley_voltage = smu_measurement.get('voltage', None)
            keithley_current = smu_measurement.get('current', None)
            
            # Update display
            if keithley_voltage is not None:
                self.keithley_voltage_label.configure(text=f'{keithley_voltage:.4f} V')
            if keithley_current is not None:
                self.keithley_current_label.configure(text=f'{keithley_current:.6f} A')
    except Exception as e:
        print(f"[EXPERIMENT_THREAD] Error reading Keithley: {e}")
```

---

## סיכום

בטאב הראשי, מדידת המתח והזרם מתבצעת כך:
- **מצב מתח**: המתח מוגדר לערך קבוע (אפס או כל ערך אחר), והזרם נמדד
- **מצב זרם**: הזרם מוגדר לערך קבוע (אפס או כל ערך אחר), והמתח נמדד

המדידות מתבצעות אוטומטית במהלך הניסוי, והנתונים נשמרים הן לתצוגה בזמן אמת והן לשמירה בקובץ.

---

## תיקון באג - עדכון 2024

**בעיה שזוהתה:** הפונקציה `measure()` המקורית תמיד מדדה זרם וקראה את ערך המתח שהוגדר, ולא את המתח הנמדד בפועל. זה גרם לבעיה במצב Current Mode.

**התיקון שבוצע:**
1. הוספת פקודת `MEAS:VOLT?` ב-SCPI commands
2. עדכון `measure()` לקבל פרמטר `mode` ולבחור את הפקודה הנכונה
3. עדכון `measure_smu()` להעביר את ה-mode
4. עדכון הקריאה ב-`main_tab.py` להעביר את המצב הנוכחי

**תוצאה:** כעת המדידות מדויקות בשני המצבים - גם במצב Voltage וגם במצב Current.

