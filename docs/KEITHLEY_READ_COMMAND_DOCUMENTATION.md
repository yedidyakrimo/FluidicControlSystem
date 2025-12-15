# תיעוד פעולת Keithley 2450 - פקודת READ

**תאריך:** 2024-12-19

**מטרת המסמך:** תיעוד מפורט של פעולת Keithley 2450 SMU, במיוחד פקודת READ? ופירוק הנתונים למתח וזרם, לצורך בדיקה ושיפור הפעולה.

---

## תוכן עניינים

1. [סקירה כללית](#סקירה-כללית)
2. [איך ה-Keithley קורא נתונים](#איך-ה-keithley-קורא-נתונים)
3. [פקודת READ? - פירוט מפורט](#פקודת-read---פירוט-מפורט)
4. [פירוק נתונים למתח וזרם](#פירוק-נתונים-למתח-וזרם)
5. [שמירת נתונים ב-Excel](#שמירת-נתונים-ב-excel)
6. [זרימת הנתונים במערכת](#זרימת-הנתונים-במערכת)

---

## סקירה כללית

Keithley 2450 הוא Source Measure Unit (SMU) - מכשיר שמסוגל גם להזין מתח/זרם וגם למדוד אותם בו-זמנית. במערכת שלנו, המכשיר משמש למדידות I-V (מתח-זרם) במהלך ניסויים.

### מצבי פעולה עיקריים:

1. **מצב Voltage (Source Voltage / Measure Current)**
   - המכשיר מזין מתח קבוע
   - המכשיר מודד את הזרם הזורם

2. **מצב Current (Source Current / Measure Voltage)**
   - המכשיר מזין זרם קבוע
   - המכשיר מודד את המתח הנוצר

---

## איך ה-Keithley קורא נתונים

### תהליך הקריאה הכללי

התהליך מתחיל כאשר המערכת מבקשת לקרוא נתונים מה-Keithley:

```
1. הקוד קורא: keithley.read_data() או keithley.measure()
   ↓
2. הפונקציה שולחת פקודת SCPI: "READ?"
   ↓
3. Keithley מבצע מדידה ומחזיר תגובה
   ↓
4. הקוד מפרק את התגובה למתח וזרם
   ↓
5. הנתונים נשמרים במערכים ובקובץ CSV/Excel
```

### מיקום הקוד

הפונקציה הראשית לקריאת נתונים נמצאת ב-`hardware/smu/keithley_2450.py`:

**שורות 508-554:**
```python
def measure(self, mode="voltage"):
    """
    Measure voltage and current from SMU
    
    Uses READ? command to read all values simultaneously (more efficient)
    """
    if not self.smu:
        return None
    
    try:
        # Use READ? to get all measurements simultaneously
        # READ? returns: voltage,current,resistance,status (comma-separated)
        read_string = self.smu.query(self.scpi.read_data())
        
        # Parse the response (comma-separated values)
        values = read_string.strip().split(',')
        
        data = {}
        if len(values) >= 2:
            # First value is voltage, second is current
            data['voltage'] = float(values[0])
            data['current'] = float(values[1])
        else:
            # Fallback if parsing fails
            print(f"Warning: Could not parse READ? response: {read_string}")
            return None
        
        return data
    except Exception as e:
        print(f"Error measuring SMU: {e}")
        return None
```

**שורות 556-563:**
```python
def read_data(self):
    """
    Read voltage and current from SMU
    
    Returns:
        Dictionary with voltage and current values
    """
    return self.measure()
```

---

## פקודת READ? - פירוט מפורט

### מהי פקודת READ?

פקודת `READ?` היא פקודת SCPI (Standard Commands for Programmable Instruments) ששולחת למכשיר Keithley 2450.

**מיקום הפקודה בקוד:**
- `hardware/smu/scpi_commands.py`, שורה 159-161:
```python
@staticmethod
def read_data():
    """Read measurement data"""
    return "READ?"
```

### מה הפקודה עושה?

1. **שולחת למכשיר:** `READ?`
2. **המכשיר מבצע:**
   - מבצע מדידה של כל הערכים הפעילים
   - מחזיר את כל הנתונים בפורמט מוגדר
3. **תגובת המכשיר:** מחרוזת עם ערכים מופרדים בפסיקים

### פורמט התגובה

התגובה של `READ?` היא מחרוזת בפורמט:
```
voltage,current,resistance,status
```

**דוגמה לתגובה:**
```
1.5000,0.0025,600.0,0
```

**פירוש הערכים:**
- **ערך 1 (voltage):** המתח הנמדד בוולט (V)
- **ערך 2 (current):** הזרם הנמדד באמפר (A)
- **ערך 3 (resistance):** ההתנגדות המחושבת באוהם (Ω) - מחושב אוטומטית
- **ערך 4 (status):** סטטוס המדידה (0 = תקין)

### יתרונות פקודת READ?

1. **יעילות:** קריאה אחת במקום מספר קריאות נפרדות
2. **סינכרון:** כל הערכים נמדדים באותו רגע
3. **מהירות:** פחות תקשורת עם המכשיר = מדידות מהירות יותר

### השוואה לפקודות אחרות

| פקודה | מה היא עושה | תגובה |
|------|------------|-------|
| `READ?` | קורא את כל הערכים בבת אחת | `voltage,current,resistance,status` |
| `MEAS:CURR?` | מודד רק זרם | `current_value` |
| `MEAS:VOLT?` | מודד רק מתח | `voltage_value` |

**הערה:** `READ?` יעילה יותר כי היא קוראת הכל בבת אחת.

---

## פירוק נתונים למתח וזרם

### איך הקוד מפרק את התגובה?

הפירוק מתבצע בפונקציה `measure()` (שורות 529-536):

```python
# שלב 1: קבלת התגובה מהמכשיר
read_string = self.smu.query(self.scpi.read_data())
# דוגמה: read_string = "1.5000,0.0025,600.0,0"

# שלב 2: הסרת רווחים מיותרים
read_string = read_string.strip()
# תוצאה: "1.5000,0.0025,600.0,0"

# שלב 3: פיצול לפי פסיקים
values = read_string.split(',')
# תוצאה: ['1.5000', '0.0025', '600.0', '0']

# שלב 4: חילוץ מתח וזרם
if len(values) >= 2:
    data['voltage'] = float(values[0])  # 1.5000 V
    data['current'] = float(values[1])   # 0.0025 A
```

### דיאגרמת פירוק

```
"1.5000,0.0025,600.0,0"
         ↓
    strip() - הסרת רווחים
         ↓
"1.5000,0.0025,600.0,0"
         ↓
    split(',') - פיצול לפי פסיקים
         ↓
['1.5000', '0.0025', '600.0', '0']
         ↓
    float(values[0]) → voltage = 1.5000 V
    float(values[1]) → current = 0.0025 A
```

### איך להפריד לקריאת מתח וזרם נפרדות?

אם רוצים לקרוא מתח וזרם בנפרד, יש שתי אפשרויות:

#### אפשרות 1: שימוש ב-READ? ופירוק ידני

```python
# קריאת כל הנתונים
read_string = smu.query("READ?")
values = read_string.strip().split(',')

# הפרדה למתח וזרם
voltage = float(values[0])  # ערך ראשון = מתח
current = float(values[1])  # ערך שני = זרם
resistance = float(values[2]) if len(values) > 2 else None  # ערך שלישי = התנגדות
status = int(values[3]) if len(values) > 3 else None  # ערך רביעי = סטטוס
```

#### אפשרות 2: שימוש בפקודות נפרדות

```python
# קריאת מתח בלבד
voltage = float(smu.query("MEAS:VOLT?"))

# קריאת זרם בלבד
current = float(smu.query("MEAS:CURR?"))
```

**הערה:** אפשרות 1 יעילה יותר כי היא מבצעת מדידה אחת במקום שתיים.

### דוגמת קוד מלאה לפירוק

```python
def read_voltage_and_current_separately(self):
    """
    קריאת מתח וזרם בנפרד מתוך תגובת READ?
    """
    if not self.smu:
        return None, None
    
    try:
        # שליחה: READ?
        read_string = self.smu.query("READ?")
        
        # פירוק התגובה
        values = read_string.strip().split(',')
        
        # בדיקת תקינות
        if len(values) < 2:
            print(f"Error: Invalid READ? response: {read_string}")
            return None, None
        
        # הפרדה למתח וזרם
        voltage = float(values[0])  # מתח בוולט
        current = float(values[1])  # זרם באמפר
        
        # אפשר גם לקרוא התנגדות וסטטוס אם נדרש
        resistance = float(values[2]) if len(values) > 2 else None
        status = int(values[3]) if len(values) > 3 else None
        
        return voltage, current
        
    except Exception as e:
        print(f"Error reading voltage and current: {e}")
        return None, None
```

### טיפול בשגיאות

הקוד הנוכחי כולל טיפול בשגיאות בסיסי:

```python
if len(values) >= 2:
    data['voltage'] = float(values[0])
    data['current'] = float(values[1])
else:
    print(f"Warning: Could not parse READ? response: {read_string}")
    return None
```

**שיפורים אפשריים:**
- בדיקת תקינות הערכים (לא NaN, לא אינסוף)
- בדיקת סטטוס המדידה
- טיפול בשגיאות המרה (ValueError)

---

## שמירת נתונים ב-Excel

### תהליך השמירה

הנתונים נשמרים בשני שלבים:

1. **שמירה בזמן אמת ל-CSV**
2. **ייצוא ל-Excel בסוף הניסוי**

### שלב 1: שמירה ל-CSV

**מיקום:** `utils/data_handler.py`

**פונקציה:** `append_data()` (שורות 95-104)

```python
def append_data(self, data_point):
    if self.writer and data_point:
        try:
            self.writer.writerow(data_point)
        except Exception as e:
            print(f"Error writing data: {e}")
```

**פורמט נקודת נתונים:**
```python
data_point = {
    "time": elapsed_time_from_start,
    "flow_setpoint": self.current_flow_rate,
    "pump_flow_read": pump_data['flow'],
    "pressure_read": pressure,
    "temp_read": temperature,
    "level_read": level,
    "voltage": keithley_voltage,      # מהפונקציה measure()
    "current": keithley_current,      # מהפונקציה measure()
    "target_voltage": target_voltage
}
```

**פורמט CSV:**
```csv
time,flow_setpoint,pump_flow_read,pressure_read,temp_read,level_read,voltage,current,target_voltage
0.0,1.5,1.48,15.2,25.3,0.75,1.5000,0.0025,1.5
1.0,1.5,1.49,15.3,25.4,0.76,1.5010,0.0026,1.5
```

### שלב 2: ייצוא ל-Excel

**פונקציה:** `export_to_excel()` (שורות 138-222)

```python
def export_to_excel(self, output_path=None):
    """
    Export the current CSV data to Excel format
    """
    # קריאת קובץ CSV
    df = pd.read_csv(self.file_path, comment='#')
    
    # יצירת קובץ Excel
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # כתיבת נתונים לגיליון "Experiment Data"
        df.to_excel(writer, sheet_name='Experiment Data', index=False)
        
        # התאמת רוחב עמודות
        # ... (קוד התאמה)
        
        # יצירת גיליון סיכום
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
```

### מבנה קובץ Excel

קובץ Excel מכיל שני גיליונות:

#### גיליון 1: "Experiment Data"
כל הנתונים מהניסוי:

| time | flow_setpoint | pump_flow_read | pressure_read | temp_read | level_read | voltage | current | target_voltage |
|------|---------------|----------------|---------------|-----------|------------|---------|---------|----------------|
| 0.0  | 1.5           | 1.48           | 15.2          | 25.3      | 0.75       | 1.5000  | 0.0025  | 1.5            |
| 1.0  | 1.5           | 1.49           | 15.3          | 25.4      | 0.76       | 1.5010  | 0.0026  | 1.5            |

#### גיליון 2: "Summary"
סיכום סטטיסטי של הניסוי:

| Parameter | Value |
|-----------|-------|
| Total Data Points | 1000 |
| Experiment Duration (s) | 3600.00 |
| Average Flow Rate | 1.50 |
| Max Pressure | 20.5 |
| Min Temperature | 24.8 |
| Max Level | 0.85 |

### זרימת הנתונים מ-READ? ל-Excel

```
Keithley 2450
    ↓
READ? → "1.5000,0.0025,600.0,0"
    ↓
measure() → פירוק למתח וזרם
    ↓
data = {'voltage': 1.5000, 'current': 0.0025}
    ↓
data_point = {..., 'voltage': 1.5000, 'current': 0.0025}
    ↓
DataHandler.append_data(data_point)
    ↓
CSV file: "1.5000,0.0025"
    ↓
export_to_excel()
    ↓
Excel file: עמודות voltage ו-current
```

---

## זרימת הנתונים במערכת

### תהליך מלא - מקריאת Keithley לשמירה

```
1. MainTab.experiment_thread()
   ↓
2. HardwareController.read_keithley()
   ↓
3. Keithley2450.read_data()
   ↓
4. Keithley2450.measure()
   ↓
5. smu.query("READ?")
   ↓
6. Keithley מחזיר: "1.5000,0.0025,600.0,0"
   ↓
7. פירוק: values = ['1.5000', '0.0025', '600.0', '0']
   ↓
8. data = {'voltage': 1.5000, 'current': 0.0025}
   ↓
9. חזרה ל-MainTab
   ↓
10. data_point = {..., 'voltage': 1.5000, 'current': 0.0025}
    ↓
11. DataHandler.append_data(data_point)
    ↓
12. כתיבה ל-CSV
    ↓
13. בסוף הניסוי: export_to_excel()
    ↓
14. קובץ Excel עם עמודות voltage ו-current
```

### מיקומי קבצים רלוונטיים

| קובץ | תפקיד | שורות רלוונטיות |
|------|-------|-----------------|
| `hardware/smu/keithley_2450.py` | קריאת נתונים מה-Keithley | 508-563 |
| `hardware/smu/scpi_commands.py` | הגדרת פקודת READ? | 159-161 |
| `utils/data_handler.py` | שמירה ל-CSV/Excel | 95-222 |
| `gui/tabs/main_tab.py` | שימוש בנתונים | 1464-1491 |

---

## סיכום והמלצות לבדיקה

### נקודות לבדיקה

1. **תקינות תגובת READ?**
   - בדוק שהתגובה תמיד בפורמט: `voltage,current,resistance,status`
   - בדוק טיפול בשגיאות כאשר התגובה לא תקינה

2. **פירוק נתונים**
   - ודא שהמתח תמיד בעמדה 0 (`values[0]`)
   - ודא שהזרם תמיד בעמדה 1 (`values[1]`)

3. **שמירה ב-Excel**
   - ודא שעמודות voltage ו-current נשמרות נכון
   - בדוק שהערכים לא נחתכים או משתנים

### שיפורים אפשריים

1. **הוספת בדיקות תקינות:**
```python
# בדיקת תקינות ערכים
if abs(voltage) > 200:  # מתח לא הגיוני
    print(f"Warning: Unusual voltage value: {voltage}V")
if abs(current) > 1:  # זרם לא הגיוני
    print(f"Warning: Unusual current value: {current}A")
```

2. **שימוש בהתנגדות:**
```python
# חישוב התנגדות אם לא קיים בתגובה
if len(values) > 2 and float(values[2]) > 0:
    resistance = float(values[2])
else:
    resistance = voltage / current if current != 0 else float('inf')
```

3. **שימוש בסטטוס:**
```python
# בדיקת סטטוס המדידה
if len(values) > 3:
    status = int(values[3])
    if status != 0:
        print(f"Warning: Measurement status indicates issue: {status}")
```

---

## נספח: פקודות SCPI רלוונטיות

| פקודה | תיאור | תגובה |
|------|------|-------|
| `READ?` | קריאת כל הנתונים | `voltage,current,resistance,status` |
| `MEAS:VOLT?` | מדידת מתח | `voltage_value` |
| `MEAS:CURR?` | מדידת זרם | `current_value` |
| `SOUR:VOLT?` | שאילתת מתח מוגדר | `voltage_setting` |
| `SOUR:CURR?` | שאילתת זרם מוגדר | `current_setting` |

---

**מסמך זה נוצר לצורך בדיקה ושיפור פעולת קריאת הנתונים מה-Keithley 2450.**

**תאריך עדכון אחרון:** 2024-12-19

