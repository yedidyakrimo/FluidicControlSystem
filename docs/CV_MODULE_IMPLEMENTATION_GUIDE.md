# מדריך יישום מלא: מודול Cyclic Voltammetry (CV) עם TSP

## תוכן עניינים

1. [מבוא - מה זה CV?](#1-מבוא---מה-זה-cv)
2. [עקרונות ארכיטקטורה](#2-עקרונות-ארכיטקטורה)
3. [מבנה הקבצים והקוד](#3-מבנה-הקבצים-והקוד)
4. [איך זה עובד - זרימת הנתונים](#4-איך-זה-עובד---זרימת-הנתונים)
5. [מדריך יישום צעד אחר צעד](#5-מדריך-יישום-צעד-אחר-צעד)
6. [פירוט טכני של כל קובץ](#6-פירוט-טכני-של-כל-קובץ)
7. [איך לבדוק ולנפות באגים](#7-איך-לבדוק-ולנפות-באגים)
8. [שגיאות נפוצות ופתרונות](#8-שגיאות-נפוצות-ופתרונות)

---

## 1. מבוא - מה זה CV?

### 1.1 מה זה Cyclic Voltammetry?

**Cyclic Voltammetry (CV)** היא טכניקה אלקטרוכימית למדידת זרם כתלות במתח. התוכנית מבצעת "סוויפ" (sweep) של מתח בין 4 נקודות קודקוד (vertices) בסדר מעגלי:

```
V1 → V2 → V3 → V4 → V1
```

**דוגמה:**
- V1 = 0.0V
- V2 = 1.0V
- V3 = -1.0V
- V4 = 0.0V

הסוויפ יעבור: 0V → 1V → -1V → 0V → (חוזר ל-V1)

### 1.2 למה TSP ולא SCPI רגיל?

**SCPI רגיל (כמו ב-main_tab):**
- המחשב שולח פקודה אחת, מחכה לתשובה, שולח פקודה הבאה
- בעיית תזמון: אם המחשב "מתעכב", המדידות לא מדויקות
- איטי: כל פקודה = round-trip דרך USB/GPIB

**TSP (Test Script Processor):**
- המחשב שולח **סקריפט שלם** (Lua) למכשיר
- המכשיר **מריץ את הסקריפט בעצמו** - תזמון מדויק
- מהיר: כל המדידות רצות במכשיר, המחשב רק מקבל את התוצאות

**למה זה חשוב ל-CV?**
- CV דורש תזמון מדויק בין נקודות
- אם המחשב "מתעכב", הזמן בין נקודות משתנה → תוצאות לא מדויקות
- עם TSP, המכשיר שולט בתזמון → תוצאות מדויקות

---

## 2. עקרונות ארכיטקטורה

### 2.1 הפרדה מוחלטת מהקוד הקיים

**עקרון מרכזי:** המודול CV **לא נוגע** בקוד הקיים (`main_tab`, `keithley_2450.py` עם SCPI). כל הקוד נבנה **מאפס** בקבצים נפרדים.

### 2.2 מבנה המודול

```
hardware/smu/
├── keithley_2450.py          # קוד קיים - SCPI רגיל (לא נוגעים!)
├── keithley_2450_tsp.py      # ⭐ קוד חדש - TSP wrapper
├── tsp_script_generator.py   # ⭐ קוד חדש - יוצר סקריפטים Lua
└── tsp_scpi_commands.py      # ⭐ קוד חדש - פקודות SCPI ל-TSP

experiments/experiment_types/
└── cv_experiment.py          # ⭐ קוד חדש - ניהול ניסוי CV

gui/tabs/
└── cv_tab.py                 # ⭐ קוד חדש - ממשק משתמש
```

### 2.3 זרימת הנתונים

```
GUI (cv_tab.py)
    ↓
CVExperiment (cv_experiment.py)
    ↓
Keithley2450TSP (keithley_2450_tsp.py)
    ↓
TSPScriptGenerator (tsp_script_generator.py) → יוצר Lua script
    ↓
Keithley 2450 (מכשיר) → מריץ את הסקריפט
    ↓
Keithley2450TSP → קורא את הנתונים מה-buffer
    ↓
CVExperiment → שומר את הנתונים
    ↓
GUI → מציג גרף
```

---

## 3. מבנה הקבצים והקוד

### 3.1 סקירה כללית

| **קובץ** | **תפקיד** | **תלות** |
|---------|----------|---------|
| `tsp_scpi_commands.py` | מגדיר פקודות SCPI ל-TSP | אין |
| `tsp_script_generator.py` | יוצר סקריפטים Lua | אין |
| `keithley_2450_tsp.py` | ממשק TSP למכשיר | `tsp_scpi_commands.py`, `tsp_script_generator.py`, `keithley_2450.py` |
| `cv_experiment.py` | ניהול ניסוי CV | `keithley_2450_tsp.py` |
| `cv_tab.py` | ממשק משתמש | `cv_experiment.py` |

### 3.2 תרשים זרימת הקוד

```
┌─────────────────────────────────────────────────────────────┐
│                    GUI Layer (cv_tab.py)                     │
│  - קלט משתמש (V1, V2, V3, V4, Points/Second, Current Range) │
│  - כפתור "Run CV Sweep"                                      │
│  - גרף (matplotlib)                                          │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────────┐
│              Experiment Layer (cv_experiment.py)             │
│  - יוצר Keithley2450TSP wrapper                              │
│  - קורא ל-run_cv_sweep_tsp()                               │
│  - שומר נתונים ב-DataHandler                                │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────────┐
│          TSP Wrapper Layer (keithley_2450_tsp.py)            │
│  - _ensure_scpi_mode() → בודק/מעביר למצב SCPI               │
│  - write_tsp_script() → שולח סקריפט למכשיר                 │
│  - run_cv_sweep_tsp() → מריץ סוויפ מלא                     │
│  - fetch_buffer_data() → קורא נתונים מה-buffer             │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ↓                               ↓
┌───────────────────┐      ┌──────────────────────────────┐
│ TSPScriptGenerator │      │   TSPSCPICommands             │
│ (יוצר Lua script)  │      │   (פקודות SCPI)              │
└───────────────────┘      └──────────────────────────────┘
        │                               │
        └───────────────┬───────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                    Keithley 2450 (מכשיר)                     │
│  - מקבל סקריפט Lua דרך loadscriptrun                        │
│  - מריץ את הסקריפט (סוויפ + מדידות)                        │
│  - שומר נתונים ב-defbuffer1                                 │
│  - מדפיס נתונים דרך print()                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. איך זה עובד - זרימת הנתונים

### 4.1 שלב 1: המשתמש לוחץ "Run CV Sweep"

**קובץ:** `cv_tab.py`, פונקציה: `run_cv_sweep()`

```python
# 1. קורא פרמטרים מהממשק
v1 = float(self.v1_entry.get())
v2 = float(self.v2_entry.get())
v3 = float(self.v3_entry.get())
v4 = float(self.v4_entry.get())
points_per_second = float(self.points_per_sec_entry.get())
current_range = float(self.current_range_entry.get())

# 2. יוצר thread רקע
threading.Thread(
    target=self._run_cv_sweep_thread,
    args=(v1, v2, v3, v4, points_per_second, current_range),
    daemon=True
).start()
```

### 4.2 שלב 2: Thread רקע יוצר CVExperiment

**קובץ:** `cv_tab.py`, פונקציה: `_run_cv_sweep_thread()`

```python
# יוצר CVExperiment
self.cv_experiment = CVExperiment(self.hw_controller, self.data_handler)

# קורא ל-run()
self.cv_experiment.run(v1, v2, v3, v4, points_per_second, current_range)
```

### 4.3 שלב 3: CVExperiment יוצר TSP wrapper

**קובץ:** `cv_experiment.py`, פונקציה: `run()`

```python
# מקבל TSP wrapper
tsp = self._get_tsp_wrapper()  # יוצר Keithley2450TSP

# מריץ סוויפ
result = tsp.run_cv_sweep_tsp(
    v1, v2, v3, v4,
    points_per_second,
    current_range
)
```

### 4.4 שלב 4: TSP Wrapper יוצר סקריפט Lua

**קובץ:** `keithley_2450_tsp.py`, פונקציה: `run_cv_sweep_tsp()`

```python
# יוצר סקריפט Lua
script = self.script_generator.generate_cv_sweep_script(
    v1, v2, v3, v4, points_per_second, current_range, current_limit
)
```

**קובץ:** `tsp_script_generator.py`, פונקציה: `generate_cv_sweep_script()`

הפונקציה יוצרת סקריפט Lua שמכיל:

```lua
-- Reset and clear buffer
reset()
defbuffer1.clear()

-- Configure SMU
smu.source.func = smu.FUNC_DC_VOLTAGE
smu.measure.func = smu.FUNC_DC_CURRENT
smu.measure.sense = smu.SENSE_2_WIRE
smu.measure.range = 0.1
smu.source.ilimit.level = 0.1
smu.measure.autozero.enable = smu.OFF

-- Turn output ON
smu.source.output = smu.ON

-- Sweep: V1 -> V2 -> V3 -> V4 -> V1
for i = 0, points-1 do
    voltage = start_v + i * step_size
    smu.source.voltage.level = voltage
    smu.measure.read(defbuffer1)
    delay(dwell_time)
end

-- Turn output OFF
smu.source.output = smu.OFF
waitcomplete()
```

### 4.5 שלב 5: TSP Wrapper שולח סקריפט למכשיר

**קובץ:** `keithley_2450_tsp.py`, פונקציה: `write_tsp_script()`

```python
# 1. בודק/מעביר למצב SCPI
if not self._ensure_scpi_mode():
    return False

# 2. בונה בלוק loadscriptrun
script_lines = script_content.strip().split('\n')
formatted_script = '\r\n'.join(script_lines)
full_command = f"loadscriptrun\r\n{formatted_script}\r\nendscript"

# 3. שולח למכשיר (עם טיפול ב-write_termination)
smu.write_termination = ''
if hasattr(smu, 'write_raw'):
    smu.write_raw(full_command.encode('utf-8') + b'\n')
else:
    smu.write(full_command + '\n')
smu.write_termination = original_write_termination

# 4. בודק שגיאות
has_error, error_msg = self._check_system_error()
```

### 4.6 שלב 6: המכשיר מריץ את הסקריפט

המכשיר (Keithley 2450):
1. מקבל את בלוק `loadscriptrun ... endscript`
2. "מקמפל" את הסקריפט Lua
3. מריץ את הסקריפט:
   - מגדיר את ה-SMU
   - מבצע סוויפ (לולאה)
   - בכל איטרציה: קובע מתח → מודד זרם → שומר ב-`defbuffer1`
   - מחכה עם `delay()`
4. מסיים עם `waitcomplete()`

### 4.7 שלב 7: TSP Wrapper מחכה לסיום

**קובץ:** `keithley_2450_tsp.py`, פונקציה: `run_cv_sweep_tsp()`

```python
# מחכה לסיום עם *OPC?
opc_result = smu.query("*OPC?")
# מחזיר "1" כשהסקריפט הסתיים
```

### 4.8 שלב 8: TSP Wrapper קורא נתונים מה-buffer

**קובץ:** `keithley_2450_tsp.py`, פונקציה: `fetch_buffer_data()`

```python
# 1. יוצר סקריפט Lua לקריאת buffer
fetch_script = """
local n = defbuffer1.n
if n == 0 then
    print("EMPTY")
else
    -- שרשור כל הנתונים למחרוזת אחת
    local readings_str = ""
    local source_str = ""
    for i = 1, n do
        if i > 1 then
            readings_str = readings_str .. ","
            source_str = source_str .. ","
        end
        readings_str = readings_str .. tostring(defbuffer1.readings[i])
        source_str = source_str .. tostring(defbuffer1.sourcevalues[i])
    end
    print(n .. "," .. readings_str .. "," .. source_str)
end
"""

# 2. שולח את הסקריפט
full_command = f"loadscriptrun\r\n{fetch_script}\r\nendscript"
smu.write(...)

# 3. קורא את התשובה (מה שה-print() הדפיס)
result_str = smu.read().strip()

# 4. מפרסר את הנתונים
parts = result_str.split(',')
n = int(float(parts[0]))
current_data = [float(x) for x in parts[1:n+1]]
voltage_data = [float(x) for x in parts[n+1:2*n+1]]
```

### 4.9 שלב 9: CVExperiment שומר נתונים

**קובץ:** `cv_experiment.py`, פונקציה: `run()`

```python
voltage_data = result['voltage_data']
current_data = result['current_data']

# שומר כל נקודה
for i, (voltage, current) in enumerate(zip(voltage_data, current_data)):
    data_point = {
        "time": i,
        "voltage": voltage,
        "current": current,
        "elapsed_time": i / points_per_second
    }
    self.data_handler.append_data(data_point)
```

### 4.10 שלב 10: GUI מעדכן גרף

**קובץ:** `cv_tab.py`, פונקציה: `_run_cv_sweep_thread()`

```python
# מעדכן את הנתונים
self.cv_voltage_data = result['voltage_data']
self.cv_current_data = result['current_data']

# מעדכן את הגרף
self.after(0, lambda: self._update_cv_graph())
```

---

## 5. מדריך יישום צעד אחר צעד

### 5.1 שלב 1: יצירת מבנה תיקיות

```
your_project/
├── hardware/
│   └── smu/
│       ├── tsp_scpi_commands.py
│       ├── tsp_script_generator.py
│       └── keithley_2450_tsp.py
├── experiments/
│   └── experiment_types/
│       └── cv_experiment.py
└── gui/
    └── tabs/
        └── cv_tab.py
```

### 5.2 שלב 2: יצירת `tsp_scpi_commands.py`

**תפקיד:** מגדיר כל פקודות ה-SCPI שקשורות ל-TSP.

**קוד:**

```python
"""
TSP-related SCPI commands for Keithley 2450
"""

class TSPSCPICommands:
    @staticmethod
    def query_language():
        """Query current command language"""
        return "*LANG?"
    
    @staticmethod
    def set_language_scpi():
        """Set command language to SCPI"""
        return "*LANG SCPI"
    
    @staticmethod
    def system_error():
        """Query system error"""
        return "SYST:ERR?"
    
    @staticmethod
    def operation_complete():
        """Query operation complete status"""
        return "*OPC?"
    
    @staticmethod
    def event_status_register():
        """Query event status register"""
        return "*ESR?"
```

**הערות:**
- כל פונקציה מחזירה מחרוזת SCPI
- אין כאן לוגיקה, רק הגדרות פקודות

### 5.3 שלב 3: יצירת `tsp_script_generator.py`

**תפקיד:** יוצר סקריפטים Lua לסוויפ CV.

**קוד:**

```python
"""
TSP Script Generator for Cyclic Voltammetry
"""

class TSPScriptGenerator:
    @staticmethod
    def generate_cv_sweep_script(v1, v2, v3, v4, points_per_second, current_range, current_limit=0.1):
        """
        Generate Lua script for CV sweep
        
        Args:
            v1, v2, v3, v4: Voltage vertices (V)
            points_per_second: Sampling density
            current_range: Manual current range (A)
            current_limit: Current compliance (A)
        
        Returns:
            str: Complete Lua script
        """
        # חישוב פרמטרים
        path_segments = [
            abs(v2 - v1),  # V1 -> V2
            abs(v3 - v2),  # V2 -> V3
            abs(v4 - v3),  # V3 -> V4
            abs(v1 - v4)   # V4 -> V1
        ]
        total_path_length = sum(path_segments)
        
        # חישוב מספר נקודות
        estimated_time = total_path_length / 1.0  # seconds
        total_points = int(points_per_second * estimated_time)
        total_points = max(total_points, 40)  # Minimum 40 points
        
        # חישוב נקודות לכל קטע
        points_per_segment = []
        for segment_length in path_segments:
            if total_path_length > 0:
                points = max(10, int(total_points * (segment_length / total_path_length)))
            else:
                points = 10
            points_per_segment.append(points)
        
        # חישוב step size לכל קטע
        step_sizes = []
        for segment_length, points in zip(path_segments, points_per_segment):
            if points > 1:
                step = segment_length / (points - 1)
            else:
                step = 0.0
            step_sizes.append(step)
        
        # חישוב dwell time
        dwell_time = 1.0 / points_per_second
        
        # בניית סקריפט Lua
        script_lines = [
            "-- Cyclic Voltammetry Sweep Script",
            "reset()",
            "defbuffer1.clear()",
            "",
            "-- Configure SMU",
            "smu.source.func = smu.FUNC_DC_VOLTAGE",
            "smu.measure.func = smu.FUNC_DC_CURRENT",
            "smu.measure.sense = smu.SENSE_2_WIRE",
            f"smu.measure.range = {current_range}",
            f"smu.source.ilimit.level = {current_limit}",
            "smu.measure.autozero.enable = smu.OFF",
            "",
            "-- Turn output ON",
            "smu.source.output = smu.ON",
            "",
            "-- Sweep: V1 -> V2 -> V3 -> V4 -> V1",
        ]
        
        # יצירת קוד סוויפ לכל קטע
        vertices = [v1, v2, v3, v4, v1]
        segment_names = ["V1->V2", "V2->V3", "V3->V4", "V4->V1"]
        
        for start_v, end_v, step_size, points, seg_name in zip(
            vertices[:-1], vertices[1:], step_sizes, points_per_segment, segment_names
        ):
            script_lines.append(f"-- Segment: {seg_name}")
            
            if abs(end_v - start_v) < 1e-9:
                # נקודה יחידה
                script_lines.append(f"smu.source.voltage.level = {end_v}")
                script_lines.append(f"smu.measure.read(defbuffer1)")
                script_lines.append(f"delay({dwell_time})")
            else:
                # סוויפ
                if end_v > start_v:
                    # קדימה
                    script_lines.append(f"for i = 0, {points - 1} do")
                    script_lines.append(f"    voltage = {start_v} + i * {step_size}")
                    script_lines.append(f"    smu.source.voltage.level = voltage")
                    script_lines.append(f"    smu.measure.read(defbuffer1)")
                    script_lines.append(f"    delay({dwell_time})")
                    script_lines.append("end")
                else:
                    # אחורה
                    script_lines.append(f"for i = 0, {points - 1} do")
                    script_lines.append(f"    voltage = {start_v} - i * {abs(step_size)}")
                    script_lines.append(f"    smu.source.voltage.level = voltage")
                    script_lines.append(f"    smu.measure.read(defbuffer1)")
                    script_lines.append(f"    delay({dwell_time})")
                    script_lines.append("end")
            
            script_lines.append("")
        
        # סיום
        script_lines.extend([
            "-- Turn output OFF",
            "smu.source.output = smu.OFF",
            "waitcomplete()",
            ""
        ])
        
        return "\n".join(script_lines)
```

**הערות:**
- הפונקציה מחשבת את כל הפרמטרים (נקודות, step size, dwell time)
- יוצרת סקריפט Lua מלא
- מחזירה מחרוזת

### 5.4 שלב 4: יצירת `keithley_2450_tsp.py`

**תפקיד:** ממשק TSP למכשיר - שולח סקריפטים, קורא נתונים.

**קוד (חלקי - רק הפונקציות המרכזיות):**

```python
"""
TSP wrapper for Keithley 2450
"""

import time
from hardware.smu.tsp_script_generator import TSPScriptGenerator
from hardware.smu.tsp_scpi_commands import TSPSCPICommands


class Keithley2450TSP:
    def __init__(self, keithley_2450_instance):
        """
        Initialize TSP wrapper
        
        Args:
            keithley_2450_instance: Instance of Keithley2450 class
        """
        self.keithley = keithley_2450_instance
        self.tsp_scpi = TSPSCPICommands()
        self.script_generator = TSPScriptGenerator()
    
    def _get_visa_resource(self):
        """Get VISA resource"""
        if not self.keithley or not self.keithley.smu:
            return None
        return self.keithley.smu
    
    def _ensure_scpi_mode(self):
        """Ensure device is in SCPI mode"""
        smu = self._get_visa_resource()
        if not smu:
            return False
        
        try:
            # Check current language
            lang = smu.query(self.tsp_scpi.query_language()).strip()
            
            # If not SCPI, set it
            if "SCPI" not in lang.upper():
                smu.write(self.tsp_scpi.set_language_scpi())
                time.sleep(0.1)
                # Verify
                lang = smu.query(self.tsp_scpi.query_language()).strip()
                if "SCPI" not in lang.upper():
                    return False
            
            return True
        except Exception as e:
            # Try to set anyway
            try:
                smu.write(self.tsp_scpi.set_language_scpi())
                time.sleep(0.1)
                return True
            except:
                return False
    
    def _check_system_error(self):
        """Check for system errors"""
        smu = self._get_visa_resource()
        if not smu:
            return (False, "")
        
        try:
            error_str = smu.query(self.tsp_scpi.system_error()).strip()
            # Format: "error_code,\"error_message\""
            parts = error_str.split(',', 1)
            if len(parts) >= 2:
                error_code = parts[0].strip()
                error_msg = parts[1].strip().strip('"')
                
                try:
                    if int(error_code) != 0:
                        return (True, f"Error {error_code}: {error_msg}")
                except ValueError:
                    pass
            
            return (False, "")
        except Exception as e:
            return (False, "")
    
    def write_tsp_script(self, script_content, script_name="cv_sweep"):
        """
        Write TSP script to instrument using loadscriptrun
        
        Args:
            script_content: Lua script content as string
            script_name: Optional script name
        
        Returns:
            True if successful, False otherwise
        """
        smu = self._get_visa_resource()
        if not smu:
            return False
        
        try:
            # Step 1: Ensure SCPI mode
            if not self._ensure_scpi_mode():
                return False
            
            # Step 2: Clear previous errors
            self._check_system_error()
            
            # Step 3: Build script block
            script_lines = script_content.strip().split('\n')
            formatted_script = '\r\n'.join(script_lines)
            full_command = f"loadscriptrun\r\n{formatted_script}\r\nendscript"
            
            # Step 4: Increase timeout
            original_timeout = smu.timeout
            smu.timeout = 10000  # 10 seconds
            
            # Step 5: Send script (with write_termination handling)
            original_write_termination = getattr(smu, 'write_termination', None)
            try:
                smu.write_termination = ''
                if hasattr(smu, 'write_raw'):
                    smu.write_raw(full_command.encode('utf-8') + b'\n')
                else:
                    smu.write(full_command + '\n')
            finally:
                if original_write_termination is not None:
                    smu.write_termination = original_write_termination
            
            # Step 6: Wait and check errors
            time.sleep(0.2)
            has_error, error_msg = self._check_system_error()
            if has_error:
                print(f"TSP Error: {error_msg}")
                smu.timeout = original_timeout
                return False
            
            smu.timeout = original_timeout
            return True
            
        except Exception as e:
            print(f"TSP Error: {e}")
            return False
    
    def run_cv_sweep_tsp(self, v1, v2, v3, v4, points_per_second, current_range, current_limit=0.1, timeout=300):
        """
        Run Cyclic Voltammetry sweep using TSP
        
        Returns:
            dict with keys: 'success', 'voltage_data', 'current_data', 'error'
        """
        smu = self._get_visa_resource()
        if not smu:
            return {
                'success': False,
                'voltage_data': [],
                'current_data': [],
                'error': 'SMU not connected'
            }
        
        try:
            # Generate TSP script
            script = self.script_generator.generate_cv_sweep_script(
                v1, v2, v3, v4, points_per_second, current_range, current_limit
            )
            
            # Write and execute script
            if not self.write_tsp_script(script):
                has_error, error_msg = self._check_system_error()
                if has_error:
                    return {
                        'success': False,
                        'voltage_data': [],
                        'current_data': [],
                        'error': f'Failed to write TSP script: {error_msg}'
                    }
                return {
                    'success': False,
                    'voltage_data': [],
                    'current_data': [],
                    'error': 'Failed to write TSP script'
                }
            
            # Wait for completion
            time.sleep(0.2)
            original_timeout = smu.timeout
            smu.timeout = timeout * 1000
            
            try:
                opc_result = smu.query(self.tsp_scpi.operation_complete())
                if "1" not in str(opc_result):
                    print(f"Warning: Operation complete returned: {opc_result}")
            except Exception as e:
                print(f"Warning: Error waiting for completion: {e}")
            
            smu.timeout = original_timeout
            
            # Fetch buffer data
            return self.fetch_buffer_data()
            
        except Exception as e:
            return {
                'success': False,
                'voltage_data': [],
                'current_data': [],
                'error': f'TSP sweep error: {str(e)}'
            }
    
    def fetch_buffer_data(self):
        """
        Fetch voltage and current data from defbuffer1
        
        Returns:
            dict with keys: 'success', 'voltage_data', 'current_data', 'error'
        """
        smu = self._get_visa_resource()
        if not smu:
            return {
                'success': False,
                'voltage_data': [],
                'current_data': [],
                'error': 'SMU not connected'
            }
        
        try:
            original_timeout = smu.timeout
            
            # Create fetch script
            fetch_script = """local n = defbuffer1.n
if n == 0 then
    print("EMPTY")
else
    local readings_str = ""
    local source_str = ""
    for i = 1, n do
        if i > 1 then
            readings_str = readings_str .. ","
            source_str = source_str .. ","
        end
        readings_str = readings_str .. tostring(defbuffer1.readings[i])
        source_str = source_str .. tostring(defbuffer1.sourcevalues[i])
    end
    print(n .. "," .. readings_str .. "," .. source_str)
end"""
            
            # Ensure SCPI mode
            if not self._ensure_scpi_mode():
                return {
                    'success': False,
                    'voltage_data': [],
                    'current_data': [],
                    'error': 'Could not ensure SCPI mode'
                }
            
            # Send fetch script
            fetch_lines = fetch_script.strip().split('\n')
            formatted_fetch = '\r\n'.join(fetch_lines)
            fetch_command = f"loadscriptrun\r\n{formatted_fetch}\r\nendscript"
            
            original_write_termination = getattr(smu, 'write_termination', None)
            try:
                smu.write_termination = ''
                if hasattr(smu, 'write_raw'):
                    smu.write_raw(fetch_command.encode('utf-8') + b'\n')
                else:
                    smu.write(fetch_command + '\n')
            finally:
                if original_write_termination is not None:
                    smu.write_termination = original_write_termination
            
            # Wait and read
            time.sleep(0.3)
            smu.timeout = 5000
            try:
                result_str = smu.read().strip()
            except Exception as e:
                time.sleep(0.2)
                try:
                    smu.query("*OPC?")
                    result_str = smu.read().strip()
                except Exception as e2:
                    smu.timeout = original_timeout
                    return {
                        'success': False,
                        'voltage_data': [],
                        'current_data': [],
                        'error': f'Failed to read: {e}, {e2}'
                    }
            
            smu.timeout = original_timeout
            
            # Parse result
            if result_str == "EMPTY" or result_str == "0":
                return {
                    'success': True,
                    'voltage_data': [],
                    'current_data': [],
                    'error': None
                }
            
            parts = result_str.split(',')
            if len(parts) < 2:
                return {
                    'success': False,
                    'voltage_data': [],
                    'current_data': [],
                    'error': f'Invalid format: {result_str}'
                }
            
            try:
                n = int(float(parts[0]))
                if n == 0:
                    return {
                        'success': True,
                        'voltage_data': [],
                        'current_data': [],
                        'error': None
                    }
                
                if len(parts) < (1 + 2 * n):
                    return {
                        'success': False,
                        'voltage_data': [],
                        'current_data': [],
                        'error': f'Incomplete data: expected {1 + 2 * n}, got {len(parts)}'
                    }
                
                current_data = [float(x) for x in parts[1:n+1]]
                voltage_data = [float(x) for x in parts[n+1:2*n+1]]
                
                return {
                    'success': True,
                    'voltage_data': voltage_data,
                    'current_data': current_data,
                    'error': None
                }
            except (ValueError, IndexError) as e:
                return {
                    'success': False,
                    'voltage_data': [],
                    'current_data': [],
                    'error': f'Parse error: {e}'
                }
            
        except Exception as e:
            return {
                'success': False,
                'voltage_data': [],
                'current_data': [],
                'error': f'Error: {str(e)}'
            }
    
    def is_connected(self):
        """Check if connected"""
        return self.keithley and self.keithley.connected and not self.keithley.simulation_mode
```

**הערות:**
- `_ensure_scpi_mode()` - בודק/מעביר למצב SCPI
- `_check_system_error()` - בודק שגיאות
- `write_tsp_script()` - שולח סקריפט למכשיר
- `run_cv_sweep_tsp()` - מריץ סוויפ מלא
- `fetch_buffer_data()` - קורא נתונים מה-buffer

### 5.5 שלב 5: יצירת `cv_experiment.py`

**תפקיד:** ניהול ניסוי CV - קשר בין GUI ל-TSP wrapper.

**קוד:**

```python
"""
Cyclic Voltammetry experiment using TSP
"""

from experiments.base_experiment import BaseExperiment
from hardware.smu.keithley_2450_tsp import Keithley2450TSP


class CVExperiment(BaseExperiment):
    def __init__(self, hardware_controller, data_handler):
        super().__init__(hardware_controller, data_handler)
        self.tsp_wrapper = None
    
    def _get_tsp_wrapper(self):
        """Get or create TSP wrapper"""
        if not self.hw_controller or not self.hw_controller.smu:
            return None
        
        if self.tsp_wrapper is None:
            self.tsp_wrapper = Keithley2450TSP(self.hw_controller.smu)
        
        return self.tsp_wrapper
    
    def run(self, v1, v2, v3, v4, points_per_second, current_range):
        """
        Run CV experiment
        
        Args:
            v1, v2, v3, v4: Voltage vertices (V)
            points_per_second: Sampling density
            current_range: Manual current range (A)
        """
        if not self.is_running:
            self.is_running = True
            print("Starting CV measurement...")
        
        try:
            # Create new data file
            self.data_handler.create_new_file()
            
            # Get TSP wrapper
            tsp = self._get_tsp_wrapper()
            if not tsp:
                print("Error: SMU not connected")
                self.stop()
                return
            
            if not tsp.is_connected():
                print("Error: SMU not connected")
                self.stop()
                return
            
            # Run TSP sweep
            print(f"Running CV sweep: V1={v1}V, V2={v2}V, V3={v3}V, V4={v4}V")
            result = tsp.run_cv_sweep_tsp(
                v1, v2, v3, v4,
                points_per_second,
                current_range
            )
            
            if not result['success']:
                print(f"CV sweep failed: {result.get('error', 'Unknown')}")
                self.stop()
                return
            
            # Save data
            voltage_data = result['voltage_data']
            current_data = result['current_data']
            
            if len(voltage_data) != len(current_data):
                min_len = min(len(voltage_data), len(current_data))
                voltage_data = voltage_data[:min_len]
                current_data = current_data[:min_len]
            
            for i, (voltage, current) in enumerate(zip(voltage_data, current_data)):
                data_point = {
                    "time": i,
                    "voltage": voltage,
                    "current": current,
                    "elapsed_time": i / points_per_second if points_per_second > 0 else 0
                }
                self.data_handler.append_data(data_point)
            
            print(f"CV completed: {len(voltage_data)} points")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()
```

**הערות:**
- יוצר TSP wrapper
- קורא ל-`run_cv_sweep_tsp()`
- שומר נתונים ב-DataHandler

### 5.6 שלב 6: יצירת `cv_tab.py` (GUI)

**תפקיד:** ממשק משתמש - קלט, גרף, כפתורים.

**קוד (חלקי - רק החלקים המרכזיים):**

```python
"""
CV Tab - Cyclic Voltammetry GUI
"""

import customtkinter as ctk
from tkinter import messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading

from gui.tabs.base_tab import BaseTab
from experiments.experiment_types.cv_experiment import CVExperiment


class CVTab(BaseTab):
    def __init__(self, parent, hw_controller, data_handler, exp_manager, update_queue=None):
        super().__init__(parent, hw_controller, data_handler, exp_manager, update_queue)
        
        self.cv_voltage_data = []
        self.cv_current_data = []
        self.cv_measurement_running = False
        self.cv_experiment = None
        
        self.create_widgets()
        self.setup_graphs()
    
    def create_widgets(self):
        """Create CV tab widgets"""
        # Left panel - Parameters
        left_frame = ctk.CTkFrame(self)
        left_frame.pack(side='left', fill='both', padx=5, pady=5)
        
        # Voltage vertices
        ctk.CTkLabel(left_frame, text="V1 (V):").grid(row=0, column=0, padx=5, pady=2)
        self.v1_entry = ctk.CTkEntry(left_frame, width=150)
        self.v1_entry.insert(0, '0.0')
        self.v1_entry.grid(row=0, column=1, padx=5, pady=2)
        
        # ... (V2, V3, V4, Points/Second, Current Range)
        
        # Buttons
        ctk.CTkButton(left_frame, text="Run CV Sweep", command=self.run_cv_sweep).pack(pady=5)
        self.cv_stop_button = ctk.CTkButton(left_frame, text="Stop", command=self.stop_cv_sweep, state='disabled')
        self.cv_stop_button.pack(pady=5)
        
        # Status
        self.cv_status_label = ctk.CTkLabel(left_frame, text="Ready", text_color='green')
        self.cv_status_label.pack(pady=5)
        
        # Right panel - Graph
        right_frame = ctk.CTkFrame(self)
        right_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)
        
        self.cv_graph_frame = ctk.CTkFrame(right_frame)
        self.cv_graph_frame.pack(fill='both', expand=True)
    
    def setup_graphs(self):
        """Initialize CV graph"""
        self.cv_fig, self.cv_ax = plt.subplots(figsize=(8, 6))
        self.cv_ax.set_xlabel("Voltage (V)")
        self.cv_ax.set_ylabel("Current (A)")
        self.cv_ax.set_title("Cyclic Voltammetry")
        self.cv_ax.grid(True)
        
        self.cv_canvas = FigureCanvasTkAgg(self.cv_fig, self.cv_graph_frame)
        self.cv_canvas.draw()
        self.cv_canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def run_cv_sweep(self):
        """Run CV sweep"""
        if self.cv_measurement_running:
            return
        
        try:
            # Get parameters
            v1 = float(self.v1_entry.get())
            v2 = float(self.v2_entry.get())
            v3 = float(self.v3_entry.get())
            v4 = float(self.v4_entry.get())
            points_per_second = float(self.points_per_sec_entry.get())
            current_range = float(self.current_range_entry.get())
            
            # Validate
            if points_per_second <= 0 or current_range <= 0:
                messagebox.showerror('Error', 'Invalid parameters')
                return
            
            # Check connection
            if not self.hw_controller.smu or not self.hw_controller.smu.connected:
                messagebox.showerror('Error', 'SMU not connected')
                return
            
            # Clear data
            self.cv_voltage_data.clear()
            self.cv_current_data.clear()
            
            # Update UI
            self.cv_measurement_running = True
            self.cv_stop_button.configure(state='normal')
            self.cv_status_label.configure(text='Running...', text_color='orange')
            
            # Run in thread
            threading.Thread(
                target=self._run_cv_sweep_thread,
                args=(v1, v2, v3, v4, points_per_second, current_range),
                daemon=True
            ).start()
            
        except ValueError:
            messagebox.showerror('Error', 'Invalid values')
        except Exception as e:
            messagebox.showerror('Error', f'Error: {e}')
    
    def _run_cv_sweep_thread(self, v1, v2, v3, v4, points_per_second, current_range):
        """Background thread for CV sweep"""
        try:
            # Create experiment
            self.cv_experiment = CVExperiment(self.hw_controller, self.data_handler)
            
            # Run
            self.cv_experiment.run(v1, v2, v3, v4, points_per_second, current_range)
            
            # Fetch data
            if self.cv_experiment and hasattr(self.cv_experiment, 'tsp_wrapper') and self.cv_experiment.tsp_wrapper:
                result = self.cv_experiment.tsp_wrapper.fetch_buffer_data()
                if result['success']:
                    self.cv_voltage_data = result['voltage_data']
                    self.cv_current_data = result['current_data']
                    
                    # Update UI
                    self.after(0, lambda: self._update_cv_graph())
                    self.after(0, lambda: self.cv_status_label.configure(text='Completed', text_color='green'))
            
        except Exception as e:
            self.after(0, lambda: messagebox.showerror('Error', f'Error: {e}'))
        finally:
            self.cv_measurement_running = False
            self.after(0, lambda: self.cv_stop_button.configure(state='disabled'))
    
    def _update_cv_graph(self):
        """Update CV graph"""
        self.cv_ax.clear()
        
        if len(self.cv_voltage_data) > 0 and len(self.cv_current_data) > 0:
            self.cv_ax.plot(self.cv_voltage_data, self.cv_current_data, linewidth=2)
        
        self.cv_ax.set_xlabel("Voltage (V)")
        self.cv_ax.set_ylabel("Current (A)")
        self.cv_ax.set_title("Cyclic Voltammetry")
        self.cv_ax.grid(True)
        
        self.cv_fig.tight_layout()
        self.cv_canvas.draw()
    
    def stop_cv_sweep(self):
        """Stop CV sweep"""
        if self.cv_experiment:
            self.cv_experiment.stop()
        self.cv_measurement_running = False
        self.cv_stop_button.configure(state='disabled')
        self.cv_status_label.configure(text='Stopped', text_color='orange')
```

**הערות:**
- GUI עם customtkinter
- גרף עם matplotlib
- Thread רקע לביצוע המדידה
- עדכון UI דרך `self.after()`

---

## 6. פירוט טכני של כל קובץ

### 6.1 `tsp_scpi_commands.py`

**תפקיד:** מגדיר פקודות SCPI.

**פונקציות:**
- `query_language()` → `"*LANG?"`
- `set_language_scpi()` → `"*LANG SCPI"`
- `system_error()` → `"SYST:ERR?"`
- `operation_complete()` → `"*OPC?"`
- `event_status_register()` → `"*ESR?"`

**אין כאן לוגיקה** - רק הגדרות פקודות.

### 6.2 `tsp_script_generator.py`

**תפקיד:** יוצר סקריפטים Lua.

**פונקציה מרכזית:** `generate_cv_sweep_script()`

**מה היא עושה:**
1. מחשבת את אורך המסלול (V1→V2→V3→V4→V1)
2. מחשבת מספר נקודות כולל
3. מחשבת נקודות לכל קטע (פרופורציונלי לאורך)
4. מחשבת step size לכל קטע
5. מחשבת dwell time (1 / points_per_second)
6. בונה סקריפט Lua עם:
   - `reset()` + `defbuffer1.clear()`
   - הגדרת SMU
   - לולאות סוויפ לכל קטע
   - `waitcomplete()`

**החזרה:** מחרוזת Lua

### 6.3 `keithley_2450_tsp.py`

**תפקיד:** ממשק TSP למכשיר.

**פונקציות מרכזיות:**

#### `_ensure_scpi_mode()`
- בודק מצב שפה (`*LANG?`)
- אם לא SCPI, מעביר (`*LANG SCPI`)
- מחזיר True/False

#### `_check_system_error()`
- שולח `SYST:ERR?`
- מפרסר תשובה: `"error_code,\"message\""`
- מחזיר `(has_error: bool, error_message: str)`

#### `write_tsp_script(script_content)`
- בודק/מעביר למצב SCPI
- בונה בלוק: `loadscriptrun\r\n{script}\r\nendscript`
- שולח למכשיר (עם טיפול ב-`write_termination`)
- בודק שגיאות
- מחזיר True/False

#### `run_cv_sweep_tsp(...)`
- יוצר סקריפט (דרך `TSPScriptGenerator`)
- שולח למכשיר (דרך `write_tsp_script()`)
- מחכה לסיום (`*OPC?`)
- קורא נתונים (דרך `fetch_buffer_data()`)
- מחזיר dict עם `success`, `voltage_data`, `current_data`, `error`

#### `fetch_buffer_data()`
- יוצר סקריפט Lua לקריאת buffer:
  ```lua
  local n = defbuffer1.n
  -- שרשור כל הנתונים למחרוזת אחת
  print(n .. "," .. readings_str .. "," .. source_str)
  ```
- שולח למכשיר
- קורא תשובה (מה שה-`print()` הדפיס)
- מפרסר: `"n,reading1,...,readingN,source1,...,sourceN"`
- מחזיר dict עם `success`, `voltage_data`, `current_data`, `error`

### 6.4 `cv_experiment.py`

**תפקיד:** ניהול ניסוי CV.

**פונקציות:**

#### `_get_tsp_wrapper()`
- בודק אם יש TSP wrapper
- אם לא, יוצר חדש (`Keithley2450TSP(self.hw_controller.smu)`)
- מחזיר wrapper

#### `run(...)`
- יוצר קובץ נתונים חדש
- מקבל TSP wrapper
- קורא ל-`run_cv_sweep_tsp()`
- שומר נתונים ב-DataHandler
- מטפל בשגיאות

### 6.5 `cv_tab.py`

**תפקיד:** ממשק משתמש.

**פונקציות מרכזיות:**

#### `create_widgets()`
- יוצר שדות קלט (V1, V2, V3, V4, Points/Second, Current Range)
- יוצר כפתורים (Run, Stop)
- יוצר labels (Status, Data Points)

#### `setup_graphs()`
- יוצר figure matplotlib
- יוצר canvas
- מגדיר axes (xlabel, ylabel, title, grid)

#### `run_cv_sweep()`
- קורא פרמטרים מהממשק
- בודק תקינות
- בודק חיבור SMU
- יוצר thread רקע

#### `_run_cv_sweep_thread()`
- יוצר `CVExperiment`
- קורא ל-`run()`
- קורא נתונים מה-TSP wrapper
- מעדכן UI (גרף, status)

#### `_update_cv_graph()`
- מנקה axes
- מצייר גרף (`plot(voltage_data, current_data)`)
- מעדכן canvas

---

## 7. איך לבדוק ולנפות באגים

### 7.1 בדיקת חיבור SMU

**בקוד:**
```python
if not self.hw_controller.smu or not self.hw_controller.smu.connected:
    print("SMU not connected")
    return
```

**בדיקה ידנית:**
```python
# ב-Python console
from hardware.smu.keithley_2450 import Keithley2450
smu = Keithley2450()
smu.auto_detect()
print(smu.connected)  # צריך להיות True
print(smu.smu.query("*IDN?"))  # צריך להחזיר IDN
```

### 7.2 בדיקת מצב SCPI

**בקוד:**
```python
lang = smu.query("*LANG?")
print(f"Language: {lang}")  # צריך להיות "SCPI"
```

**בדיקה ב-NI-MAX:**
1. פתח NI-MAX
2. Write: `*LANG?`
3. Read: צריך להחזיר `"SCPI"`

### 7.3 בדיקת סקריפט Lua

**בקוד:**
```python
from hardware.smu.tsp_script_generator import TSPScriptGenerator
gen = TSPScriptGenerator()
script = gen.generate_cv_sweep_script(0, 1, -1, 0, 10, 0.1)
print(script)  # הדפס את הסקריפט
```

**בדיקה ב-NI-MAX:**
1. העתק את הסקריפט
2. Write (ב-NI-MAX):
   ```
   loadscriptrun
   reset()
   print("test")
   endscript
   ```
3. Read: צריך להחזיר `"test"`

### 7.4 בדיקת שגיאות SCPI

**בקוד:**
```python
error_str = smu.query("SYST:ERR?")
print(f"Error: {error_str}")  # צריך להיות "0,\"No error\""
```

**בדיקה ב-NI-MAX:**
1. Write: `SYST:ERR?`
2. Read: צריך להחזיר `"0,\"No error\""`

### 7.5 בדיקת buffer

**בקוד:**
```python
# אחרי סוויפ
fetch_script = """
local n = defbuffer1.n
print(n)
end
"""
# שולח דרך loadscriptrun
result = smu.read()
print(f"Buffer size: {result}")  # צריך להחזיר מספר
```

**בדיקה ב-NI-MAX:**
1. Write:
   ```
   loadscriptrun
   print(defbuffer1.n)
   endscript
   ```
2. Read: צריך להחזיר מספר נקודות

### 7.6 Debugging Tips

1. **הדפס כל שלב:**
   ```python
   print("Step 1: Generating script...")
   script = self.script_generator.generate_cv_sweep_script(...)
   print(f"Script length: {len(script)}")
   
   print("Step 2: Sending script...")
   if not self.write_tsp_script(script):
       print("Failed to send script")
       return
   
   print("Step 3: Waiting for completion...")
   # ...
   ```

2. **בדוק שגיאות אחרי כל פעולה:**
   ```python
   has_error, error_msg = self._check_system_error()
   if has_error:
       print(f"Error: {error_msg}")
   ```

3. **בדוק timeout:**
   ```python
   print(f"Timeout: {smu.timeout} ms")
   smu.timeout = 10000  # הגדל אם צריך
   ```

4. **בדוק write_termination:**
   ```python
   print(f"Write termination: {smu.write_termination}")
   ```

---

## 8. שגיאות נפוצות ופתרונות

### 8.1 שגיאת SCPI -110 / -111

**תסמינים:**
```
Error -110: SCPI command header error
Error -111: SCPI header separator error
```

**סיבות אפשריות:**
1. המכשיר לא במצב SCPI
2. פורמט שגוי של `loadscriptrun`
3. פקודת TSP שגויה בסקריפט

**פתרונות:**
1. **בדוק מצב SCPI:**
   ```python
   lang = smu.query("*LANG?")
   if "SCPI" not in lang.upper():
       smu.write("*LANG SCPI")
   ```

2. **בדוק פורמט loadscriptrun:**
   ```python
   # נכון:
   full_command = f"loadscriptrun\r\n{script}\r\nendscript"
   
   # לא נכון:
   full_command = f"loadscriptrun {script} endscript"  # חסר \r\n
   ```

3. **בדוק פקודות TSP:**
   - `smu.source.ilimit.level` (נכון)
   - `smu.source.voltage.limit` (לא נכון!)

### 8.2 Query Unterminated

**תסמינים:**
```
Query unterminated
```

**סיבות אפשריות:**
1. `loadscriptrun` לא נשלח עם `endscript`
2. `write_termination` מוסיף תווים מיותרים

**פתרונות:**
1. **וודא שיש endscript:**
   ```python
   full_command = f"loadscriptrun\r\n{script}\r\nendscript"
   ```

2. **השתמש ב-write_raw:**
   ```python
   smu.write_termination = ''
   smu.write_raw(full_command.encode('utf-8') + b'\n')
   smu.write_termination = original_write_termination
   ```

### 8.3 Buffer Empty

**תסמינים:**
```
Buffer is empty
result_str == "EMPTY"
```

**סיבות אפשריות:**
1. הסקריפט לא רץ
2. `smu.measure.read(defbuffer1)` לא נקרא
3. הסקריפט נכשל לפני המדידות

**פתרונות:**
1. **בדוק שהסקריפט רץ:**
   ```python
   # אחרי write_tsp_script
   has_error, error_msg = self._check_system_error()
   if has_error:
       print(f"Script error: {error_msg}")
   ```

2. **בדוק *OPC?:**
   ```python
   opc_result = smu.query("*OPC?")
   print(f"OPC: {opc_result}")  # צריך להיות "1"
   ```

3. **בדוק buffer size:**
   ```python
   fetch_script = "print(defbuffer1.n)"
   # שולח וקורא
   ```

### 8.4 Timeout

**תסמינים:**
```
Timeout error
```

**סיבות אפשריות:**
1. סוויפ ארוך מדי
2. timeout קטן מדי

**פתרונות:**
1. **הגדל timeout:**
   ```python
   smu.timeout = 300000  # 5 דקות (ב-milliseconds)
   ```

2. **בדוק זמן סוויפ:**
   ```python
   estimated_time = total_path_length / 1.0  # seconds
   print(f"Estimated time: {estimated_time} seconds")
   ```

### 8.5 Parse Error

**תסמינים:**
```
Error parsing buffer data
Invalid data format
```

**סיבות אפשריות:**
1. פורמט תשובה שגוי
2. buffer לא מכיל נתונים

**פתרונות:**
1. **הדפס תשובה:**
   ```python
   result_str = smu.read().strip()
   print(f"Raw result: {result_str[:200]}")  # הדפס 200 תווים ראשונים
   ```

2. **בדוק פורמט:**
   ```python
   # צריך להיות: "n,reading1,...,readingN,source1,...,sourceN"
   parts = result_str.split(',')
   print(f"Parts count: {len(parts)}")
   print(f"First part (n): {parts[0]}")
   ```

---

## סיכום

המודול CV מבוסס על TSP (Test Script Processor) של Keithley 2450. הוא מורכב מ-5 קבצים עיקריים:

1. **`tsp_scpi_commands.py`** - פקודות SCPI
2. **`tsp_script_generator.py`** - יוצר סקריפטים Lua
3. **`keithley_2450_tsp.py`** - ממשק TSP למכשיר
4. **`cv_experiment.py`** - ניהול ניסוי
5. **`cv_tab.py`** - ממשק משתמש

הזרימה:
GUI → CVExperiment → Keithley2450TSP → TSPScriptGenerator → Keithley 2450 → Buffer → Keithley2450TSP → CVExperiment → GUI

**עקרונות מרכזיים:**
- הפרדה מוחלטת מהקוד הקיים
- TSP במקום SCPI רגיל (תזמון מדויק)
- טיפול ב-`write_termination` ו-`loadscriptrun`
- בדיקת מצב SCPI לפני כל פעולה
- קריאת נתונים דרך `print()` ב-Lua

**לבדיקה:**
- NI-MAX לבדיקת פקודות SCPI
- הדפסת סקריפטים Lua
- בדיקת שגיאות עם `SYST:ERR?`
- בדיקת buffer עם `defbuffer1.n`

---

**מסמך זה מספק את כל המידע הדרוש ליישם את מודול ה-CV מחדש בפרויקט חדש.**


