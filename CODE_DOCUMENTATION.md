# תיעוד מקיף - מערכת בקרת זרימה (Fluidic Control System)

## תוכן עניינים
1. [סקירה כללית](#סקירה-כללית)
2. [ארכיטקטורת המערכת](#ארכיטקטורת-המערכת)
3. [מודולי חומרה (Hardware Modules)](#מודולי-חומרה-hardware-modules)
4. [מודולי ניסויים (Experiments Modules)](#מודולי-ניסויים-experiments-modules)
5. [מודולי ממשק משתמש (GUI Modules)](#מודולי-ממשק-משתמש-gui-modules)
6. [פקודות SCPI למכשיר Keithley 2450](#פקודות-scpi-למכשיר-keithley-2450)
7. [ניהול נתונים (Data Handler)](#ניהול-נתונים-data-handler)
8. [זרימת הנתונים במערכת](#זרימת-הנתונים-במערכת)
9. [תהליך הרצת ניסוי](#תהליך-הרצת-ניסוי)

---

## סקירה כללית

מערכת בקרת זרימה היא אפליקציה Python לניהול ובקרה של ניסויים במערכות זרימה. המערכת מאפשרת:
- **בקרת משאבה** (Vapourtec Pump) - שליטה בקצב זרימה
- **מדידות חיישנים** - לחץ, טמפרטורה, זרימה, רמת נוזל
- **מדידות I-V** - באמצעות Keithley 2450 SMU
- **ניהול ניסויים** - תלויי זמן ו-I-V
- **תצוגה בזמן אמת** - גרפים וסטטיסטיקות
- **שמירת נתונים** - CSV ו-Excel

---

## ארכיטקטורת המערכת

המערכת בנויה במבנה מודולרי המאפשר תחזוקה קלה והרחבה:

```
FluidicControlSystem/
├── main.py                    # נקודת כניסה
├── main_app.py                # אפליקציה ראשית (230 שורות)
├── data_handler.py            # ניהול שמירת נתונים
│
├── config/                    # קבצי תצורה
│   ├── settings.py           # הגדרות כלליות
│   └── hardware_config.py    # תצורת חומרה
│
├── hardware/                  # מודולי חומרה
│   ├── hardware_controller.py # ממשק ראשי לחומרה
│   ├── base.py               # מחלקה בסיסית
│   ├── pump/                 # משאבה
│   ├── smu/                  # Keithley 2450
│   ├── ni_daq/               # NI USB-6002
│   └── sensors/              # חיישנים
│
├── experiments/              # מודולי ניסויים
│   ├── experiment_manager.py # מנהל ניסויים ראשי
│   ├── base_experiment.py    # מחלקה בסיסית
│   ├── safety_checks.py      # בדיקות בטיחות
│   └── experiment_types/     # סוגי ניסויים
│
└── gui/                      # ממשק משתמש
    └── tabs/                 # טאבים של האפליקציה
        ├── base_tab.py       # מחלקה בסיסית
        ├── main_tab.py        # טאב ראשי
        ├── iv_tab.py         # טאב I-V
        ├── program_tab.py    # טאב תוכניות
        ├── browser_tab.py    # דפדפן ניסויים
        └── scheduler_tab.py  # מתזמן ניסויים
```

### עקרונות עיצוב:
1. **הפרדת אחריות** - כל מודול אחראי על תחום ספציפי
2. **ממשק אחיד** - כל רכיב חומרה יורש מ-`HardwareBase`
3. **תאימות לאחור** - `HardwareController` מספק ממשק זהה ל-`hardware_control.py` הישן
4. **עדכונים thread-safe** - שימוש ב-`queue` לעדכוני GUI

---

## מודולי חומרה (Hardware Modules)

### 1. HardwareController (`hardware/hardware_controller.py`)

**תפקיד**: ממשק ראשי המאחד את כל רכיבי החומרה תחת ממשק אחד.

**מבנה**:
```python
class HardwareController:
    def __init__(self, pump_port, ni_device_name, smu_resource):
        self.pump = VapourtecPump(port=pump_port)
        self.ni_daq = NIUSB6002(device_name=ni_device_name)
        self.pressure_sensor = PressureSensor(...)
        self.temperature_sensor = TemperatureSensor(...)
        self.flow_sensor = FlowSensor(...)
        self.level_sensor = LevelSensor(...)
        self.smu = Keithley2450(resource=smu_resource)
```

**פונקציות עיקריות**:
- `set_pump_flow_rate(flow_rate)` - הגדרת קצב זרימה
- `read_pump_data()` - קריאת נתוני משאבה
- `read_pressure_sensor()` - קריאת לחץ
- `read_temperature_sensor()` - קריאת טמפרטורה
- `read_flow_sensor()` - קריאת זרימה
- `read_level_sensor()` - קריאת רמת נוזל
- `set_valves(valve1, valve2)` - שליטה בשסתומים
- `set_smu_voltage(voltage)` - הגדרת מתח SMU
- `measure_smu()` - מדידת מתח וזרם

---

### 2. Vapourtec Pump (`hardware/pump/vapourtec_pump.py`)

**תפקיד**: שליטה במשאבת Vapourtec דרך ממשק Serial (RS-232).

**פונקציות**:
- `set_flow_rate(flow_rate_ml_min)` - הגדרת קצב זרימה
- `read_data()` - קריאת נתוני משאבה (זרימה, לחץ)
- `stop()` - עצירת המשאבה

**פרוטוקול תקשורת**: Serial (COM port), 9600 baud

---

### 3. Keithley 2450 SMU (`hardware/smu/keithley_2450.py`)

**תפקיד**: שליטה במכשיר Keithley 2450 Source Measure Unit למדידות I-V.

**מבנה**:
```python
class Keithley2450(HardwareBase):
    def __init__(self, resource=None):
        self.scpi = SCPICommands()  # כל פקודות SCPI
        self.smu = None  # VISA resource
```

**פונקציות עיקריות**:
- `auto_detect()` - זיהוי אוטומטי של המכשיר
- `connect_to_resource(resource)` - חיבור למשאב ספציפי
- `setup_for_iv_measurement(current_limit)` - הגדרה למדידת I-V
- `set_voltage(voltage)` - הגדרת מתח פלט
- `measure()` - ביצוע מדידה (מתח וזרם)
- `setup_iv_sweep(start_v, end_v, step_v)` - הגדרה ל-sweep
- `stop()` - כיבוי פלט

**תמיכה ב-VISA**:
- ניסיון ראשון: NI-VISA (מומלץ למכשירי USB)
- גיבוי: pyvisa-py (תמיכה מוגבלת ב-USB)
- מצב סימולציה: אם VISA לא זמין

---

### 4. SCPI Commands (`hardware/smu/scpi_commands.py`)

**תפקיד**: מרכז כל פקודות SCPI למכשיר Keithley 2450.

**קטגוריות פקודות**:

#### זיהוי ואיפוס:
- `*IDN?` - זיהוי מכשיר
- `*RST` - איפוס למצב ברירת מחדל

#### הגדרת מקור (Source):
- `SOUR:FUNC VOLT` - הגדרת מקור למתח
- `SOUR:VOLT:RANG <range>` - טווח מתח
- `SOUR:VOLT:ILIM <limit>` - הגבלת זרם (compliance)
- `SOUR:VOLT <voltage>` - הגדרת מתח פלט

#### הגדרת מדידה (Sense):
- `SENS:FUNC "CURR"` - מדידת זרם
- `SENS:CURR:RANG <range>` - טווח מדידת זרם
- `SENS:CURR:NPLC <nplc>` - מספר מחזורי רשת (דיוק)
- `SENS:CURR:APER <time>` - זמן מדידה

#### שליטת פלט:
- `OUTP ON` - הפעלת פלט
- `OUTP OFF` - כיבוי פלט
- `OUTP?` - שאילתת מצב פלט

#### מדידות:
- `MEAS:CURR?` - מדידת זרם (מבצע מדידה אוטומטית)
- `READ?` - קריאת נתוני מדידה

**דוגמת שימוש**:
```python
scpi = SCPICommands()
# איפוס
smu.write(scpi.reset())
# הגדרת מקור למתח
smu.write(scpi.set_source_voltage())
# הגדרת הגבלת זרם
smu.write(scpi.set_current_limit(0.1))
# הגדרת מתח
smu.write(scpi.set_voltage(1.0))
# הפעלת פלט
smu.write(scpi.output_on())
# מדידה
current = smu.query(scpi.measure_current())
```

---

### 5. NI USB-6002 DAQ (`hardware/ni_daq/ni_usb6002.py`)

**תפקיד**: שליטה במכשיר NI USB-6002 Data Acquisition.

**פונקציות**:
- `read_analog_input(channel)` - קריאת קלט אנלוגי
- `write_analog_output(channel, voltage)` - כתיבת פלט אנלוגי
- `write_digital_output(port/line, state)` - כתיבת פלט דיגיטלי

**ערוצים**:
- `ai0` - חיישן לחץ
- `ai1` - חיישן טמפרטורה
- `ai2` - חיישן זרימה
- `ai3` - חיישן רמת נוזל
- `ao0` - בקרת טמפרטורת חימום
- `port0/line0` - שסתום 1 (Main)
- `port0/line1` - שסתום 2 (Rinsing)

---

### 6. חיישנים (`hardware/sensors/`)

כל חיישן הוא מחלקה נפרדת:

#### PressureSensor (`pressure_sensor.py`)
- **ערוץ**: `ai0`
- **טווח**: 0-100 PSI
- **פונקציה**: `read()` - מחזיר לחץ ב-PSI

#### TemperatureSensor (`temperature_sensor.py`)
- **ערוץ**: `ai1`
- **טווח**: 20-100°C
- **פונקציה**: `read()` - מחזיר טמפרטורה ב-°C

#### FlowSensor (`flow_sensor.py`)
- **ערוץ**: `ai2`
- **טווח**: 0-10 ml/min
- **פונקציה**: `read()` - מחזיר זרימה ב-ml/min
- **תכונה**: מתעדכן לפי setpoint של המשאבה (סימולציה)

#### LevelSensor (`level_sensor.py`)
- **ערוץ**: `ai3`
- **טווח**: 0-100% (0.0-1.0)
- **פונקציה**: `read()` - מחזיר רמה (0.0-1.0)

---

## מודולי ניסויים (Experiments Modules)

### 1. ExperimentManager (`experiments/experiment_manager.py`)

**תפקיד**: מנהל ראשי לכל סוגי הניסויים.

**מבנה**:
```python
class ExperimentManager:
    def __init__(self, hardware_controller, data_handler):
        self.hw_controller = hardware_controller
        self.data_handler = data_handler
        self.time_dependent_exp = TimeDependentExperiment(...)
        self.iv_exp = IVExperiment(...)
        self.safety_checker = SafetyChecker(...)
```

**פונקציות**:
- `run_time_dependent_experiment(program)` - הרצת ניסוי תלוי זמן
- `run_iv_experiment(start_v, end_v, step_v)` - הרצת ניסוי I-V
- `stop_experiment()` - עצירת ניסוי
- `finish_experiment()` - סיום ניסוי (השלמת שלב נוכחי)
- `perform_safety_checks()` - בדיקות בטיחות

---

### 2. BaseExperiment (`experiments/base_experiment.py`)

**תפקיד**: מחלקה בסיסית לכל סוגי הניסויים.

**ממשק**:
```python
class BaseExperiment(ABC):
    @abstractmethod
    def run(self, *args, **kwargs):
        """הרצת הניסוי - חייב להיות מיושם"""
        pass
    
    def stop(self):
        """עצירת הניסוי"""
        pass
    
    def finish(self):
        """סיום הניסוי - השלמת שלב נוכחי"""
        pass
```

---

### 3. TimeDependentExperiment (`experiments/experiment_types/time_dependent.py`)

**תפקיד**: ניסוי תלוי זמן - ריצה לפי תוכנית עם שלבים.

**פורמט תוכנית**:
```python
program = [
    {
        'duration': 60,           # משך זמן (שניות)
        'flow_rate': 1.5,         # קצב זרימה (ml/min)
        'valve_setting': {        # הגדרות שסתומים
            'valve1': 'main',
            'valve2': 'main'
        },
        'temp': 25.0              # טמפרטורה (אופציונלי)
    },
    # ... שלבים נוספים
]
```

**תהליך הרצה**:
1. יצירת קובץ נתונים חדש
2. לולאה על כל שלב:
   - הגדרת קצב זרימה ושסתומים
   - לולאה למשך השלב:
     - בדיקות בטיחות
     - קריאת נתונים מכל החיישנים
     - שמירת נתונים לקובץ
     - המתנה 1 שנייה
3. עצירת הניסוי

---

### 4. IVExperiment (`experiments/experiment_types/iv_experiment.py`)

**תפקיד**: ניסוי I-V - מדידת מאפיין זרם-מתח.

**פרמטרים**:
- `start_v`: מתח התחלתי (V)
- `end_v`: מתח סופי (V)
- `step_v`: גודל צעד (V)
- `delay`: השהיה בין מדידות (שניות, ברירת מחדל: 0.1)

**תהליך הרצה**:
1. יצירת קובץ נתונים חדש
2. הגדרת SMU למדידת I-V
3. חישוב נקודות מתח (sweep ידני)
4. לולאה על כל נקודת מתח:
   - הגדרת מתח
   - המתנה לייצוב (0.1 שנייה)
   - מדידת זרם
   - שמירת נתונים
   - השהיה בין מדידות
5. עצירת הניסוי

**הערה**: המערכת משתמשת ב-sweep ידני (לא sweep מובנה של SMU) כדי להימנע מבעיות trigger model.

---

### 5. SafetyChecker (`experiments/safety_checks.py`)

**תפקיד**: בדיקות בטיחות במהלך ניסויים.

**בדיקות**:
- `check_level(threshold=0.05)` - בדיקת רמת נוזל (מינימום 5%)
- `check_pressure(max_pressure=100.0)` - בדיקת לחץ מקסימלי (100 PSI)
- `check_temperature(max_temperature=100.0)` - בדיקת טמפרטורה מקסימלית (100°C)

**פונקציה ראשית**:
- `perform_all_checks()` - ביצוע כל הבדיקות

**התנהגות**: אם אחת הבדיקות נכשלת, הניסוי נעצר אוטומטית.

---

## מודולי ממשק משתמש (GUI Modules)

### 1. BaseTab (`gui/tabs/base_tab.py`)

**תפקיד**: מחלקה בסיסית לכל הטאבים.

**מבנה**:
```python
class BaseTab(ctk.CTkFrame):
    def __init__(self, parent, hw_controller, data_handler, exp_manager, update_queue):
        self.hw_controller = hw_controller
        self.data_handler = data_handler
        self.exp_manager = exp_manager
        self.update_queue = update_queue
        # מערכי נתונים משותפים
        self.flow_x_data, self.flow_y_data = [], []
        # ...
```

**פונקציות**:
- `create_widgets()` - יצירת ווידג'טים (חייב להיות מיושם)
- `update_data()` - עדכון נתונים (אופציונלי)
- `cleanup()` - ניקוי משאבים (אופציונלי)

---

### 2. MainTab (`gui/tabs/main_tab.py`)

**תפקיד**: טאב ראשי לשליטה וניטור ניסויים.

**תכונות**:
- **פרמטרי ניסוי**: קצב זרימה, משך זמן, הגדרות שסתומים
- **מטא-דאטה**: שם ניסוי, תיאור, תגיות, מפעיל
- **כפתורי שליטה**: Start, Stop, Finish, Clear Graph
- **קריאות חיישנים**: לחץ, טמפרטורה, זרימה, רמת נוזל
- **סטטיסטיקות**: ממוצע, מינימום, מקסימום, סטיית תקן
- **גרפים**: מצב multi-panel או single graph
- **אפשרויות ייצוא**: Excel, PNG, PDF

**מצבי גרף**:
- **Multi-panel**: 4 גרפים (זרימה, לחץ, טמפרטורה, רמה)
- **Single graph**: גרף אחד עם בחירת ציר X ו-Y

**פונקציות עיקריות**:
- `start_recording()` - התחלת הקלטה
- `stop_recording()` - עצירת הקלטה
- `update_multi_panel_graphs()` - עדכון גרפים multi-panel
- `on_axis_change()` - עדכון גרף single
- `update_statistics()` - עדכון סטטיסטיקות
- `export_excel()` - ייצוא ל-Excel
- `export_graph_png()` - ייצוא גרף ל-PNG
- `export_graph_pdf()` - ייצוא גרף ל-PDF

---

### 3. IVTab (`gui/tabs/iv_tab.py`)

**תפקיד**: טאב למדידות I-V.

**תכונות**:
- **סטטוס SMU**: חיבור, זיהוי מכשיר, רשימת VISA resources
- **בקרה מהירה**: הגדרת מתח ידנית, מדידה, כיבוי פלט
- **פרמטרי I-V**: מתח התחלתי, סופי, גודל צעד
- **נתוני I-V**: גרף I-V, נתוני זמן, סטטיסטיקות
- **אפשרויות ייצוא**: Excel, PNG, PDF

**פונקציות עיקריות**:
- `detect_smu()` - זיהוי אוטומטי של SMU
- `refresh_smu_status()` - רענון סטטוס SMU
- `set_smu_voltage_manual()` - הגדרת מתח ידנית
- `measure_smu_manual()` - מדידה ידנית
- `iv_direct_run()` - הרצת ניסוי I-V ישיר
- `iv_run_program()` - הרצת ניסוי I-V מתוכנית
- `update_iv_graph()` - עדכון גרף I-V
- `plot_iv_xy_graph()` - ציור גרף לפי צירים נבחרים

---

### 4. ProgramTab (`gui/tabs/program_tab.py`)

**תפקיד**: טאב לכתיבת והרצת תוכניות ניסוי.

**תכונות**:
- **עורך תוכנית**: אזור טקסט לעריכת תוכנית JSON
- **כפתורי שליטה**: Load, Save, Run, Stop
- **ספריית תוכניות**: רשימת תוכניות שמורות
- **סטטוס**: מצב ניסוי נוכחי

**פורמט תוכנית**:
```json
[
    {
        "duration": 60,
        "flow_rate": 1.5,
        "valve_setting": {
            "valve1": "main",
            "valve2": "main"
        }
    }
]
```

**פונקציות**:
- `load_program()` - טעינת תוכנית מקובץ
- `save_program()` - שמירת תוכנית לקובץ
- `load_selected()` - טעינת תוכנית מהספרייה
- `run_program()` - הרצת תוכנית
- `parse_program()` - פרסור תוכנית JSON

---

### 5. BrowserTab (`gui/tabs/browser_tab.py`)

**תפקיד**: דפדפן ניסויים - צפייה וניהול ניסויים קודמים.

**תכונות**:
- **חיפוש וסינון**: חיפוש לפי שם, תאריך, תגיות
- **רשימת ניסויים**: רשימה עם פרטים (תאריך, שם, תיאור)
- **פעולות**: Load, Compare, Export

**פונקציות**:
- `refresh_experiments()` - רענון רשימת ניסויים
- `filter_experiments()` - סינון ניסויים
- `load_experiment()` - טעינת ניסוי
- `compare_experiments()` - השוואת ניסויים
- `export_selected_experiment()` - ייצוא ניסוי

---

### 6. SchedulerTab (`gui/tabs/scheduler_tab.py`)

**תפקיד**: מתזמן ניסויים - תזמון ניסויים לעתיד.

**תכונות**:
- **תזמון**: בחירת תאריך ושעה
- **בחירת תוכנית**: בחירה מתוכניות שמורות
- **רשימת ניסויים מתוזמנים**: רשימה עם תאריך/שעה ותוכנית
- **פעולות**: Remove, Clear All

**פונקציות**:
- `schedule_experiment()` - תזמון ניסוי
- `refresh_scheduled_experiments()` - רענון רשימה
- `remove_scheduled()` - הסרת ניסוי מתוזמן
- `clear_scheduled()` - ניקוי כל הניסויים המתוזמנים

---

## פקודות SCPI למכשיר Keithley 2450

### סקירה כללית

SCPI (Standard Commands for Programmable Instruments) הוא פרוטוקול תקשורת סטנדרטי למכשירי מדידה. כל הפקודות מאורגנות ב-`hardware/smu/scpi_commands.py`.

### קטגוריות פקודות

#### 1. זיהוי ואיפוס

| פקודה | תיאור | דוגמה |
|------|------|------|
| `*IDN?` | זיהוי מכשיר | `KEITHLEY INSTRUMENTS,MODEL 2450,04666218,1.2.3` |
| `*RST` | איפוס למצב ברירת מחדל | איפוס כל ההגדרות |

**שימוש**:
```python
scpi = SCPICommands()
# זיהוי
idn = smu.query(scpi.identify())
# איפוס
smu.write(scpi.reset())
```

---

#### 2. הגדרת מקור (Source Configuration)

| פקודה | תיאור | פרמטרים |
|------|------|---------|
| `SOUR:FUNC VOLT` | הגדרת מקור למתח | - |
| `SOUR:VOLT:RANG <range>` | טווח מתח | 0.2, 2, 20, 200 V |
| `SOUR:VOLT:ILIM <limit>` | הגבלת זרם (compliance) | 0.001-1.05 A |
| `SOUR:VOLT <voltage>` | הגדרת מתח פלט | בטווח שנבחר |

**שימוש**:
```python
# הגדרת מקור למתח
smu.write(scpi.set_source_voltage())
# טווח 20V
smu.write(scpi.set_voltage_range(20))
# הגבלת זרם 0.1A
smu.write(scpi.set_current_limit(0.1))
# הגדרת מתח 1.0V
smu.write(scpi.set_voltage(1.0))
```

**הערה חשובה**: `SOUR:VOLT:ILIM` משמש להגדרת compliance (הגבלת זרם), לא `SENS:CURR:PROT` שאינו נתמך ב-Keithley 2450.

---

#### 3. הגדרת מדידה (Sense Configuration)

| פקודה | תיאור | פרמטרים |
|------|------|---------|
| `SENS:FUNC "CURR"` | מדידת זרם | - |
| `SENS:CURR:RANG <range>` | טווח מדידת זרם | 0.000001-1.05 A |
| `SENS:CURR:NPLC <nplc>` | מספר מחזורי רשת | 0.01-10 |
| `SENS:CURR:APER <time>` | זמן מדידה | שניות |

**שימוש**:
```python
# הגדרת מדידת זרם
smu.write(scpi.set_sense_current())
# טווח 0.1A
smu.write(scpi.set_current_range(0.1))
# דיוק גבוה (10 מחזורי רשת)
smu.write(scpi.set_nplc(10))
```

**NPLC (Number of Power Line Cycles)**:
- **0.01**: מהיר ביותר, פחות מדויק
- **1**: איזון טוב
- **10**: איטי ביותר, מדויק ביותר

---

#### 4. שליטת פלט (Output Control)

| פקודה | תיאור | תגובה |
|------|------|------|
| `OUTP ON` | הפעלת פלט | מתח מוחל על הפלט |
| `OUTP OFF` | כיבוי פלט | פלט מכובה |
| `OUTP?` | שאילתת מצב פלט | `1` (ON) או `0` (OFF) |

**שימוש**:
```python
# הפעלת פלט
smu.write(scpi.output_on())
# בדיקת מצב
state = smu.query(scpi.query_output_state())
# כיבוי פלט
smu.write(scpi.output_off())
```

---

#### 5. מדידות (Measurements)

| פקודה | תיאור | תגובה |
|------|------|------|
| `MEAS:CURR?` | מדידת זרם | `current_value` (A) |
| `READ?` | קריאת נתוני מדידה | `voltage,current,resistance,status` |

**שימוש**:
```python
# מדידת זרם (מבצע מדידה אוטומטית)
current = float(smu.query(scpi.measure_current()))
# קריאת נתונים מלאים
data = smu.query(scpi.read_data())
# פורמט: "voltage,current,resistance,status"
```

**הערה חשובה**: `MEAS:CURR?` מבצע מדידה אוטומטית, כך שאין צורך ב-`INIT` לפני המדידה.

---

### דוגמת תהליך מלא - מדידת I-V

```python
scpi = SCPICommands()

# 1. איפוס
smu.write(scpi.reset())
time.sleep(0.5)

# 2. הגדרת מקור למתח
smu.write(scpi.set_source_voltage())
smu.write(scpi.set_voltage_range(20))  # טווח 20V
smu.write(scpi.set_current_limit(0.1))  # הגבלת זרם 0.1A

# 3. הגדרת מדידת זרם
smu.write(scpi.set_sense_current())
smu.write(scpi.set_current_range(0.1))  # טווח 0.1A
smu.write(scpi.set_nplc(1))  # דיוק בינוני

# 4. הפעלת פלט
smu.write(scpi.output_on())

# 5. לולאת sweep
for voltage in [0, 0.5, 1.0, 1.5, 2.0]:
    # הגדרת מתח
    smu.write(scpi.set_voltage(voltage))
    time.sleep(0.1)  # המתנה לייצוב
    
    # מדידה
    current = float(smu.query(scpi.measure_current()))
    
    # שמירת נתונים
    print(f"V={voltage}V, I={current}A")

# 6. כיבוי פלט
smu.write(scpi.output_off())
```

---

### פקודות שהוסרו/תוקנו

#### 1. `SENS:CURR:PROT` (הוסר)
- **בעיה**: לא נתמך ב-Keithley 2450
- **פתרון**: שימוש ב-`SOUR:VOLT:ILIM` במקום

#### 2. `SOUR:SWE:VOLT:STAT OFF` (הוסר)
- **בעיה**: גרם לשגיאות trigger model
- **פתרון**: לא נדרש - המערכת משתמשת ב-sweep ידני

#### 3. `INIT` (הוסר)
- **בעיה**: גרם לשגיאות trigger model
- **פתרון**: `MEAS:CURR?` מבצע מדידה אוטומטית, אין צורך ב-`INIT`

---

## ניהול נתונים (Data Handler)

### DataHandler (`data_handler.py`)

**תפקיד**: ניהול שמירת נתונים לקבצים.

**תכונות**:
- שמירה ל-CSV
- ייצוא ל-Excel
- מטא-דאטה (שם, תיאור, תגיות, מפעיל)
- שמות קבצים מותאמים אישית

**פונקציות**:
- `create_new_file()` - יצירת קובץ CSV חדש
- `append_data(data_point)` - הוספת נקודת נתונים
- `export_to_excel(output_path)` - ייצוא ל-Excel
- `set_custom_filename(filename)` - הגדרת שם קובץ מותאם
- `set_metadata(metadata)` - הגדרת מטא-דאטה

**פורמט נתונים**:
```python
data_point = {
    "time": 1234567890.123,
    "flow_setpoint": 1.5,
    "pump_flow_read": 1.48,
    "pressure_read": 15.2,
    "temp_read": 25.3,
    "level_read": 0.75
}
```

**פורמט קובץ CSV**:
```csv
time,flow_setpoint,pump_flow_read,pressure_read,temp_read,level_read
1234567890.123,1.5,1.48,15.2,25.3,0.75
```

---

## זרימת הנתונים במערכת

### 1. קריאת חיישנים

```
Sensor (Hardware)
    ↓
Sensor Class (hardware/sensors/)
    ↓
HardwareController (hardware/hardware_controller.py)
    ↓
MainApp.update_sensor_readings()
    ↓
update_queue.put(('UPDATE_READINGS', data))
    ↓
MainTab (עדכון labels)
```

### 2. הרצת ניסוי

```
User clicks "Start" (MainTab)
    ↓
MainTab.start_recording()
    ↓
ExperimentManager.run_time_dependent_experiment(program)
    ↓
TimeDependentExperiment.run(program)
    ↓
Loop: Read sensors → Save data → Update GUI
    ↓
DataHandler.append_data(data_point)
    ↓
update_queue.put(('UPDATE_GRAPH', data))
    ↓
MainTab.update_multi_panel_graphs()
```

### 3. מדידת I-V

```
User clicks "Run I-V" (IVTab)
    ↓
IVTab.iv_direct_run()
    ↓
ExperimentManager.run_iv_experiment(start_v, end_v, step_v)
    ↓
IVExperiment.run(start_v, end_v, step_v)
    ↓
Loop: Set voltage → Measure current → Save data
    ↓
HardwareController.set_smu_voltage(voltage)
    ↓
Keithley2450.set_voltage(voltage)
    ↓
SCPICommands.set_voltage(voltage) → "SOUR:VOLT {voltage}"
    ↓
SMU (Hardware)
```

### 4. עדכוני GUI (Thread-Safe)

```
Background Thread
    ↓
update_queue.put(('UPDATE_TYPE', data))
    ↓
MainApp.check_update_queue() (runs in main thread)
    ↓
Route to appropriate tab
    ↓
Tab.update_widgets()
```

**הערה**: כל עדכוני GUI חייבים להתבצע ב-main thread. עדכונים מ-background threads עוברים דרך `update_queue`.

---

## תהליך הרצת ניסוי

### ניסוי תלוי זמן

1. **הכנה**:
   - המשתמש מזין פרמטרים (זרימה, משך, שסתומים)
   - המשתמש מזין מטא-דאטה (שם, תיאור)
   - לחיצה על "Start"

2. **התחלה**:
   - `MainTab.start_recording()` נקרא
   - `DataHandler.create_new_file()` - יצירת קובץ CSV
   - `DataHandler.set_metadata()` - שמירת מטא-דאטה
   - `ExperimentManager.run_time_dependent_experiment()` - התחלת ניסוי

3. **ביצוע**:
   - לולאה על כל שלב בתוכנית:
     - הגדרת קצב זרימה ושסתומים
     - לולאה למשך השלב:
       - `SafetyChecker.perform_all_checks()` - בדיקות בטיחות
       - קריאת חיישנים (לחץ, טמפרטורה, זרימה, רמה)
       - `DataHandler.append_data()` - שמירת נתונים
       - `update_queue.put()` - עדכון GUI
       - המתנה 1 שנייה

4. **סיום**:
   - `ExperimentManager.stop_experiment()` - עצירת משאבה
   - `DataHandler.export_to_excel()` (אופציונלי) - ייצוא ל-Excel

---

### ניסוי I-V

1. **הכנה**:
   - המשתמש מזין פרמטרים (מתח התחלתי, סופי, צעד)
   - לחיצה על "Run I-V"

2. **התחלה**:
   - `IVTab.iv_direct_run()` נקרא
   - `DataHandler.create_new_file()` - יצירת קובץ CSV
   - `HardwareController.setup_smu_iv_sweep()` - הגדרת SMU

3. **ביצוע**:
   - חישוב נקודות מתח (sweep ידני)
   - לולאה על כל נקודת מתח:
     - `HardwareController.set_smu_voltage(voltage)` - הגדרת מתח
     - המתנה לייצוב (0.1 שנייה)
     - `HardwareController.measure_smu()` - מדידת זרם
     - `DataHandler.append_data()` - שמירת נתונים
     - `update_queue.put()` - עדכון גרף I-V
     - השהיה בין מדידות

4. **סיום**:
   - `HardwareController.stop_smu()` - כיבוי פלט SMU
   - `DataHandler.export_to_excel()` (אופציונלי) - ייצוא ל-Excel

---

## סיכום

המערכת בנויה במבנה מודולרי המאפשר:
- **תחזוקה קלה** - כל מודול אחראי על תחום ספציפי
- **הרחבה** - הוספת רכיבי חומרה/ניסויים חדשים קלה
- **בדיקות** - כל מודול ניתן לבדיקה בנפרד
- **קריאות** - קוד מאורגן ומובן

**נקודות מפתח**:
1. **HardwareController** - ממשק אחיד לכל רכיבי החומרה
2. **ExperimentManager** - ניהול מרכזי של ניסויים
3. **BaseTab** - בסיס משותף לכל הטאבים
4. **SCPI Commands** - כל פקודות SCPI מאורגנות במקום אחד
5. **Thread-Safe Updates** - עדכוני GUI דרך queue

---

**תאריך עדכון**: נובמבר 2024  
**גרסה**: 2.0 (מבנה מודולרי)

