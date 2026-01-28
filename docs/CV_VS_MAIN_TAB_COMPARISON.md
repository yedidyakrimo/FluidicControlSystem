# השוואה בין Main Tab ו-CV Tab - אפיון תקלות אפשריות

## סקירה כללית

מסמך זה משווה בין שתי גישות שונות לשימוש ב-Keithley 2450:
1. **Main Tab**: שימוש בפקודות SCPI סטנדרטיות (computer-controlled)
2. **CV Tab**: שימוש ב-TSP scripts (script-based, autonomous execution)

---

## 1. ארכיטקטורה כללית

### Main Tab - גישה מסורתית (SCPI)
```
Python Application
    ↓
HardwareController
    ↓
Keithley2450 (hardware/smu/keithley_2450.py)
    ↓
SCPI Commands (hardware/smu/scpi_commands.py)
    ↓
PyVISA → Keithley 2450
```

**תכונות:**
- שליחת פקודות SCPI בודדות
- קבלת תשובות מיידיות
- בקרה מלאה מהמחשב
- מדידות נקודתיות (point-by-point)

### CV Tab - גישה TSP
```
Python Application
    ↓
HardwareController
    ↓
CVExperiment
    ↓
Keithley2450TSP (hardware/smu/keithley_2450_tsp.py)
    ↓
TSP Script Generator (hardware/smu/tsp_script_generator.py)
    ↓
loadscriptrun → Lua Script → Keithley 2450 TSP Engine
    ↓
Bulk Data Retrieval
```

**תכונות:**
- שליחת סקריפט Lua שלם
- ביצוע אוטונומי במכשיר
- מדידות מהירות עם timing מדויק
- קבלת נתונים בבת אחת (bulk)

---

## 2. השוואת תהליך ההתחברות

### Main Tab - התחברות SMU

**קוד:**
```python
# gui/tabs/main_tab.py
# Refresh Keithley status
smu_info = self.hw_controller.get_smu_info()

# hardware/smu/keithley_2450.py
def get_info(self):
    idn = self.smu.query(self.scpi.identify())  # *IDN?
    return {"connected": True, "idn": idn.strip()}
```

**פקודות SCPI:**
- `*IDN?` - זיהוי מכשיר

**מצב מכשיר:**
- SCPI mode (ברירת מחדל)
- לא דורש שינוי מצב

### CV Tab - התחברות SMU

**קוד:**
```python
# gui/tabs/cv_tab.py
# Check SMU connection
if not self.hw_controller.smu or not self.hw_controller.smu.connected:
    messagebox.showerror('Error', 'SMU not connected.')

# experiments/experiment_types/cv_experiment.py
tsp = Keithley2450TSP(self.hw_controller.smu)
if not tsp.is_connected():
    print("Error: SMU not connected")
```

**פקודות SCPI:**
- משתמש באותו `*IDN?` דרך Keithley2450
- לא משנה מצב מכשיר

**הבדל קריטי:**
- CV Tab משתמש ב-TSP scripts, אבל המכשיר עדיין צריך להיות במצב SCPI כדי לקבל את פקודת `loadscriptrun`
- **בעיה אפשרית**: אם המכשיר במצב TSP בלבד, פקודות SCPI לא יעבדו

---

## 3. השוואת הגדרת SMU

### Main Tab - הגדרת SMU

**קוד:**
```python
# hardware/smu/keithley_2450.py - setup_for_iv_measurement()
self.smu.write("SOUR:FUNC VOLT")           # Set source to voltage
self.smu.write("SOUR:VOLT:RANG:AUTO ON")   # Auto range
self.smu.write('SENS:FUNC "CURR"')         # Measure current
self.smu.write("SENS:CURR:RANG:AUTO ON")   # Auto range
self.smu.write(f"SOUR:VOLT:ILIM {limit}")  # Current limit
self.smu.write("SENS:CURR:NPLC 1")         # NPLC
self.smu.write("OUTP ON")                  # Output ON
```

**פקודות SCPI (נשלחות בנפרד):**
1. `SOUR:FUNC VOLT`
2. `SOUR:VOLT:RANG:AUTO ON`
3. `SENS:FUNC "CURR"`
4. `SENS:CURR:RANG:AUTO ON`
5. `SOUR:VOLT:ILIM {current_limit}`
6. `SENS:CURR:NPLC 1`
7. `OUTP ON`

**תכונות:**
- כל פקודה נשלחת בנפרד
- תשובה מיידית לכל פקודה
- בקרה מלאה מהמחשב

### CV Tab - הגדרת SMU (בתוך TSP Script)

**קוד:**
```python
# hardware/smu/tsp_script_generator.py
script_lines = [
    "reset()",
    "defbuffer1.clear()",
    "smu.source.func = smu.FUNC_DC_VOLTAGE",
    "smu.measure.func = smu.FUNC_DC_CURRENT",
    "smu.measure.sense = smu.SENSE_2_WIRE",
    f"smu.measure.range = {current_range}",
    "smu.measure.autozero.enable = smu.OFF",
    "smu.source.output = smu.ON",
    # ... sweep code ...
    "smu.source.output = smu.OFF",
    "waitcomplete()"
]
```

**פקודות Lua (בתוך script):**
1. `reset()` - איפוס מכשיר
2. `defbuffer1.clear()` - ניקוי buffer
3. `smu.source.func = smu.FUNC_DC_VOLTAGE` - מקור מתח
4. `smu.measure.func = smu.FUNC_DC_CURRENT` - מדידת זרם
5. `smu.measure.sense = smu.SENSE_2_WIRE` - 2-wire sensing
6. `smu.measure.range = {current_range}` - טווח ידני (לא auto!)
7. `smu.measure.autozero.enable = smu.OFF` - כיבוי autozero
8. `smu.source.output = smu.ON` - הפעלת פלט

**הבדלים קריטיים:**

| מאפיין | Main Tab | CV Tab |
|--------|----------|--------|
| **Range Mode** | Auto-range (`RANG:AUTO ON`) | Manual range (ערך קבוע) |
| **Autozero** | לא מוגדר (ברירת מחדל) | כבוי במפורש (`OFF`) |
| **Sensing** | לא מוגדר (ברירת מחדל) | 2-wire במפורש |
| **Reset** | לא מתבצע אוטומטית | `reset()` בתחילת script |

---

## 4. השוואת שליחת פקודות

### Main Tab - שליחת פקודות SCPI

**קוד:**
```python
# hardware/smu/keithley_2450.py
def set_voltage(self, voltage):
    self.smu.write(self.scpi.set_voltage(voltage))  # SOUR:VOLT {voltage}
    time.sleep(0.2)
    self.smu.write(self.scpi.set_display_home())

def measure(self, mode="voltage"):
    read_string = self.smu.query(self.scpi.read_data())  # READ?
    # Parse response
```

**פורמט:**
- פקודה אחת בכל פעם
- `write()` לפקודות ללא תשובה
- `query()` לפקודות עם תשובה (`?`)
- תשובה מיידית

**דוגמה:**
```
PC → Keithley: "SOUR:VOLT 1.0"
Keithley → PC: (no response, command executed)
PC → Keithley: "READ?"
Keithley → PC: "1.000000E+00,1.234567E-03"
```

### CV Tab - שליחת TSP Script

**קוד:**
```python
# hardware/smu/keithley_2450_tsp.py
def write_tsp_script(self, script_content):
    full_command = f"loadscriptrun\r\n{script_content}\r\nendscript"
    smu.write(full_command)
    time.sleep(0.1)
```

**פורמט:**
- סקריפט שלם נשלח בבת אחת
- `loadscriptrun` הוא פקודת SCPI
- הסקריפט עצמו הוא Lua code
- המכשיר מריץ את הסקריפט אוטונומית

**דוגמה:**
```
PC → Keithley: "loadscriptrun"
PC → Keithley: "reset()"
PC → Keithley: "smu.source.voltage.level = 1.0"
PC → Keithley: "smu.measure.read(defbuffer1)"
PC → Keithley: "endscript"
Keithley → PC: (executes script internally)
PC → Keithley: "*OPC?"
Keithley → PC: "1" (when done)
```

**הבדלים קריטיים:**

| מאפיין | Main Tab | CV Tab |
|--------|----------|--------|
| **Line Endings** | `\n` (ברירת מחדל PyVISA) | `\r\n` (נדרש ל-loadscriptrun) |
| **Command Termination** | אוטומטי (PyVISA) | `endscript` מפורש |
| **Response Timing** | מיידי | מאוחר (אחרי *OPC?) |
| **Error Detection** | מיידי (SCPI error) | מאוחר (בסוף script) |

---

## 5. השוואת מדידות

### Main Tab - מדידות נקודתיות

**קוד:**
```python
# gui/tabs/main_tab.py - experiment_thread()
smu_measurement = self.hw_controller.measure_smu(mode=current_mode)
if smu_measurement:
    keithley_voltage = smu_measurement.get('voltage')
    keithley_current = smu_measurement.get('current')
```

**תהליך:**
1. `READ?` נשלח
2. תשובה מיידית: `"voltage,current"`
3. Parsing מיידי
4. שמירה מיידית

**פקודות SCPI:**
- `READ?` - מדידה אחת
- תשובה: `"1.000000E+00,1.234567E-03"`

### CV Tab - מדידות bulk

**קוד:**
```python
# hardware/smu/keithley_2450_tsp.py - fetch_buffer_data()
fetch_script = """local n = defbuffer1.n
if n == 0 then
    print("EMPTY")
else
    -- Format: n,readings,sourcevalues
    print(n .. "," .. readings_str .. "," .. source_str)
end"""
smu.write(f"loadscriptrun\r\n{fetch_script}\r\nendscript")
time.sleep(0.3)
result_str = smu.read().strip()
```

**תהליך:**
1. TSP script נשלח לקריאת buffer
2. המכשיר מריץ את הסקריפט
3. `print()` שולח נתונים ל-output buffer
4. קריאה מהמחשב אחרי delay
5. Parsing של כל הנתונים בבת אחת

**פקודות:**
- `loadscriptrun` + Lua script
- `print()` בתוך script
- `read()` מהמחשב

**הבדלים קריטיים:**

| מאפיין | Main Tab | CV Tab |
|--------|----------|--------|
| **Data Source** | `READ?` command | `defbuffer1` buffer |
| **Data Format** | `"voltage,current"` | `"n,reading1,...,readingN,source1,...,sourceN"` |
| **Timing** | סינכרוני (מיידי) | אסינכרוני (עם delay) |
| **Error Handling** | מיידי | מאוחר (אחרי קריאה) |

---

## 6. זיהוי תקלות אפשריות

### תקלה #1: מצב מכשיר לא תואם

**תסמינים:**
- שגיאת SCPI: "Undefined header"
- `loadscriptrun` לא מזוהה

**סיבה אפשרית:**
- המכשיר במצב TSP בלבד
- פקודות SCPI לא נתמכות

**פתרון:**
```python
# לפני שליחת loadscriptrun, ודא שהמכשיר במצב SCPI
smu.write("*LANG SCPI")  # Set to SCPI mode
smu.write("*RST")        # Reset
```

**הבדל:**
- Main Tab: עובד רק במצב SCPI (ברירת מחדל)
- CV Tab: צריך SCPI כדי לשלוח `loadscriptrun`, אבל הסקריפט עצמו הוא Lua

### תקלה #2: Line Endings שגויים

**תסמינים:**
- "Query unterminated"
- Script לא מתבצע

**סיבה אפשרית:**
- `loadscriptrun` דורש `\r\n` (Windows)
- PyVISA ברירת מחדל משתמש ב-`\n`

**פתרון:**
```python
# נכון:
full_command = f"loadscriptrun\r\n{script}\r\nendscript"

# שגוי:
full_command = f"loadscriptrun\n{script}\nendscript"
```

**הבדל:**
- Main Tab: `\n` מספיק (PyVISA מטפל)
- CV Tab: צריך `\r\n` במפורש

### תקלה #3: קריאת נתונים לפני סיום Script

**תסמינים:**
- `read()` מחזיר ריק או שגיאה
- נתונים חסרים

**סיבה אפשרית:**
- `*OPC?` נקרא לפני שהסקריפט מסתיים
- `read()` נקרא לפני ש-`print()` מסיים

**פתרון:**
```python
# נכון:
smu.write(f"loadscriptrun\r\n{script}\r\nendscript")
time.sleep(0.3)  # Wait for script to start
result = smu.read()  # Read output
smu.query("*OPC?")   # Verify completion

# שגוי:
smu.write(f"loadscriptrun\r\n{script}\r\nendscript")
smu.query("*OPC?")   # This might consume the output!
result = smu.read()   # Nothing to read
```

**הבדל:**
- Main Tab: `query()` מחזיר תשובה מיידית
- CV Tab: צריך לקרוא לפני `*OPC?` או אחרי delay

### תקלה #4: Buffer לא נקי

**תסמינים:**
- נתונים ישנים מעורבים בחדשים
- מספר נקודות לא נכון

**סיבה אפשרית:**
- `defbuffer1.clear()` לא בוצע
- Buffer לא אופס לפני מדידה חדשה

**פתרון:**
```python
# בסקריפט TSP:
script = """
reset()              # Reset device
defbuffer1.clear()   # Clear buffer explicitly
-- ... rest of script ...
"""
```

**הבדל:**
- Main Tab: לא משתמש ב-buffer, כל מדידה נקייה
- CV Tab: צריך לנקות buffer במפורש

### תקלה #5: Range לא תואם

**תסמינים:**
- שגיאת compliance
- מדידות לא מדויקות

**סיבה אפשרית:**
- Main Tab משתמש ב-auto-range
- CV Tab משתמש ב-manual range
- Manual range קטן מדי או גדול מדי

**פתרון:**
```python
# ודא שה-range מתאים לערכים הצפויים
# לדוגמה, אם current_range = 0.1A אבל הזרם יכול להגיע ל-0.2A:
current_range = max(expected_max_current * 1.2, 0.1)
```

**הבדל:**
- Main Tab: Auto-range מתאים אוטומטית
- CV Tab: Manual range צריך להיות נכון מראש

### תקלה #6: Autozero כבוי

**תסמינים:**
- offset במדידות
- דריפט לאורך זמן

**סיבה אפשרית:**
- CV Tab מכבה autozero במפורש (`smu.measure.autozero.enable = smu.OFF`)
- Main Tab משאיר autozero פעיל (ברירת מחדל)

**פתרון:**
```python
# אם צריך דיוק גבוה, אפשר להשאיר autozero פעיל:
# smu.measure.autozero.enable = smu.ON  # במקום OFF
```

**הבדל:**
- Main Tab: Autozero פעיל (ברירת מחדל)
- CV Tab: Autozero כבוי (למהירות)

---

## 7. סיכום הבדלים קריטיים

| מאפיין | Main Tab (SCPI) | CV Tab (TSP) | סיכון תקלה |
|--------|-----------------|--------------|-------------|
| **מצב מכשיר** | SCPI | SCPI (לשליחת loadscriptrun) | נמוך |
| **Line Endings** | `\n` | `\r\n` | **גבוה** |
| **Range Mode** | Auto | Manual | **בינוני** |
| **Autozero** | ON (default) | OFF | נמוך |
| **Reset** | לא אוטומטי | אוטומטי | נמוך |
| **Data Source** | `READ?` | `defbuffer1` | נמוך |
| **Timing** | סינכרוני | אסינכרוני | **גבוה** |
| **Error Detection** | מיידי | מאוחר | **בינוני** |
| **Buffer Management** | לא רלוונטי | צריך clear() | **בינוני** |

---

## 8. המלצות לתיקון

### 1. תיקון Line Endings
```python
# hardware/smu/keithley_2450_tsp.py
# ודא ש-\r\n משמש בכל מקום
full_command = f"loadscriptrun\r\n{script_content}\r\nendscript"
```

### 2. תיקון קריאת נתונים
```python
# קרוא לפני *OPC? או עם delay מספיק
smu.write(fetch_command)
time.sleep(0.3)  # Wait for script execution
result = smu.read()  # Read output
smu.query("*OPC?")   # Verify completion
```

### 3. תיקון Buffer Management
```python
# ודא ש-reset() ו-clear() תמיד מתבצעים
script = """
reset()
defbuffer1.clear()
-- ... rest ...
"""
```

### 4. תיקון Error Handling
```python
# בדוק *ESR? אחרי כל loadscriptrun
smu.write(script_command)
time.sleep(0.2)
esr = smu.query("*ESR?")
if int(esr) != 0:
    print(f"Error detected: ESR = {esr}")
```

### 5. תיקון Range Validation
```python
# ודא שה-range מתאים
if current_range <= 0 or current_range > 1.0:
    raise ValueError(f"Invalid current range: {current_range}")
```

---

## 9. בדיקות מומלצות

1. **בדיקת מצב מכשיר:**
   ```python
   smu.write("*LANG?")
   lang = smu.read()
   if "SCPI" not in lang:
       smu.write("*LANG SCPI")
   ```

2. **בדיקת Line Endings:**
   ```python
   # Test script
   test_script = "print('test')"
   smu.write(f"loadscriptrun\r\n{test_script}\r\nendscript")
   # Should not give "query unterminated"
   ```

3. **בדיקת Buffer:**
   ```python
   # Before sweep
   smu.write("loadscriptrun\r\nprint(defbuffer1.n)\r\nendscript")
   n_before = int(smu.read())
   # After sweep
   n_after = int(smu.read())
   # Should be n_before + new_points
   ```

---

## 10. מסקנות

ההבדלים העיקריים בין Main Tab ל-CV Tab:

1. **Line Endings**: CV Tab צריך `\r\n` במפורש
2. **Timing**: CV Tab אסינכרוני, צריך delays
3. **Range**: CV Tab manual, צריך validation
4. **Buffer**: CV Tab צריך clear() מפורש
5. **Error Handling**: CV Tab מאוחר, צריך בדיקות נוספות

**התקלות הסבירות ביותר:**
1. "Query unterminated" → Line endings שגויים
2. "SCPI error" → מצב מכשיר או syntax שגוי
3. נתונים חסרים → קריאה לפני סיום script
4. נתונים ישנים → buffer לא נקי

---

**תאריך יצירה:** 2024
**גרסה:** 1.0



