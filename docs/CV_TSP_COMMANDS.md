## CV – רשימת כל הפקודות (SCPI + TSP) שהקוד משתמש בהן

המסמך הזה מרכז **את כל הפקודות** שהקוד של ה‑CV משתמש בהן מול ה‑Keithley 2450, כדי שתוכל לבדוק ידנית מי מהן גורמת לשגיאת SCPI.

---

## 1. פקודות SCPI שנשלחות מהמחשב (PyVISA)

הפקודות האלה נשלחות כטקסט דרך `smu.write(...)` / `smu.query(...)` בקובץ `keithley_2450_tsp.py` בעזרת המחלקה `TSPSCPICommands`.

### 1.1 פקודות שפה / מצב פקודות

- `*LANG?`  (**QUERY**)  
  - סוג: **Query** – תמיד להשתמש כ‑`*LANG?` ולקרוא תשובה.  
  - נשלחת מתוך `_ensure_scpi_mode()` כדי לבדוק באיזה מצב שפה המכשיר נמצא.

- `*LANG SCPI`  (**WRITE**)  
  - סוג: **Write‑only** – אין `?`, לא מצפים לתשובה.  
  - נשלחת מתוך `_ensure_scpi_mode()` כדי להעביר את המכשיר למצב SCPI לפני שימוש ב־`loadscriptrun`.

### 1.2 שאילתת שגיאות / סטטוס

- `SYST:ERR?`  (**QUERY**)  
  - סוג: **Query** – להשתמש כ‑`SYST:ERR?` ולקרוא שורה אחת של תשובה.  
  - נשלחת מתוך `_check_system_error()` כדי לקבל קוד שגיאה והודעה, למשל:  
    `-110, "SCPI command header error"`  
    `-111, "SCPI header separator error"`

- `*ESR?`  (**QUERY**)  
  - סוג: **Query** – להשתמש כ‑`*ESR?` ולקרוא תשובה אחת.  
  - נשלחת בסוף `fetch_buffer_data()` כדי לקרוא את Event Status Register ולאתר שגיאות נוספות אחרי קריאת הנתונים.

### 1.3 סנכרון וסיום פעולה

- `*OPC?`  (**QUERY**)  
  - סוג: **Query** – תמיד כ‑`*OPC?` ולקרוא תשובה (`"1"` כאשר הסתיים).  
  - נשלחת בתוך `run_cv_sweep_tsp()` אחרי שליחת סקריפט ה‑CV, כדי לחכות לסיום הסקריפט.  
  - נשלחת גם ב־`fetch_buffer_data()` כגיבוי אם `read()` נכשל, כדי לוודא שהסקריפט של הקריאה הסתיים.

---

## 2. בלוקי `loadscriptrun` שנשלחים (SCPI + Lua יחד)

אלה הבלוקים שנשלחים כ‑**SCPI command** `loadscriptrun` עם תוכן Lua (TSP) בפנים.  
הפורמט הכללי ששולחים ל‑SMU:

```text
loadscriptrun\r\n
<Lua script content with \r\n between lines>\r\n
endscript\r\n
```

- `loadscriptrun`  (**WRITE**)  
  - סוג: **Write‑only** – פקודת SCPI שמתחילה בלוק סקריפט. אין `?`, לא קוראים תשובה.
- `<Lua script content>`  (**WRITE בתוך הבלוק**)  
  - כל שורה היא קוד TSP (Lua) – נשלחת בתוך אותו בלוק, לא כ‑SCPI נפרדות.
- `endscript`  (**WRITE**)  
  - סוג: **Write‑only** – מסיים את בלוק הסקריפט שהחל ב‑`loadscriptrun`.

יש שני סקריפטים עיקריים:
1. סקריפט הסוויפ של ה‑CV (נוצר ב‑`TSPScriptGenerator.generate_cv_sweep_script`)
2. סקריפט הקריאה מה‑buffer (`fetch_script` בתוך `fetch_buffer_data`)

להלן כל שורת Lua שמופיעה בסקריפטים האלה.

---

## 3. פקודות TSP / Lua – סקריפט ה‑CV (Sweep)

נוצר בקובץ `hardware/smu/tsp_script_generator.py` בפונקציה:

- `TSPScriptGenerator.generate_cv_sweep_script(...)`

### 3.1 אתחול וניקוי

- `reset()`  
- `defbuffer1.clear()`

### 3.2 הגדרת מצב עבודה של ה‑SMU

- `smu.source.func = smu.FUNC_DC_VOLTAGE`  
  - מגדיר את המקור (Source) למתח.

- `smu.measure.func = smu.FUNC_DC_CURRENT`  
  - מגדיר את המדידה לזרם.

- `smu.measure.sense = smu.SENSE_2_WIRE`  
  - מגדיר מדידת 2‑wire.

- `smu.measure.range = <current_range>`  
  - טווח זרם ידני, מגיע מהמשתנה `current_range` שהמשתמש בוחר.

- `smu.source.voltage.limit = <current_limit>`  
  - מגביל את הזרם (current compliance) בזמן סורסינג מתח, ערך ברירת מחדל 0.1A אלא אם תגדיר אחרת.

- `smu.measure.autozero.enable = smu.OFF`  
  - מכבה AutoZero לטובת מהירות.

### 3.3 הפעלת יציאה

- `smu.source.output = smu.ON`  
- `smu.source.output = smu.OFF`

### 3.4 לולאת הסוויפ (4 קטעים: V1→V2→V3→V4→V1)

לכל קטע סוויפ, המחולל מייצר אחת מהתבניות הבאות (תלוי בכיוון ובאם יש שינוי במתח):

#### 3.4.1 נקודה יחידה (אם `end_v ≈ start_v`)

- `smu.source.voltage.level = <end_v>`  
- `smu.measure.read(defbuffer1)`  
- `delay(<dwell_time>)`

#### 3.4.2 סוויפ קדימה (end_v > start_v)

```lua
-- Segment N: <Vx->Vy>
for i = 0, <points - 1> do
    voltage = <start_v> + i * <step_size>
    smu.source.voltage.level = voltage
    smu.measure.read(defbuffer1)
    delay(<dwell_time>)
end
```

הפקודות בפנים:
- `for i = 0, N do ... end` (לולאת Lua רגילה)
- `voltage = <expression>`
- `smu.source.voltage.level = voltage`
- `smu.measure.read(defbuffer1)` – מודד זרם וכותב ל‑`defbuffer1`
- `delay(<dwell_time>)`

#### 3.4.3 סוויפ אחורה (end_v < start_v)

```lua
-- Segment N: <Vx->Vy>
for i = 0, <points - 1> do
    voltage = <start_v> - i * <abs(step_size)>
    smu.source.voltage.level = voltage
    smu.measure.read(defbuffer1)
    delay(<dwell_time>)
end
```

אותן פקודות כמו קדימה, רק עם מינוס.

### 3.5 סיום הסקריפט

- `waitcomplete()`  
  - מחכה לסיום כל פעולות ה‑SMU לפני החזרה.

---

## 4. פקודות TSP / Lua – סקריפט קריאת ה‑Buffer

נמצא בקובץ `hardware/smu/keithley_2450_tsp.py` בפונקציה `fetch_buffer_data()`, בתוך המשתנה `fetch_script`:

```lua
local n = defbuffer1.n
if n == 0 then
    print("EMPTY")
else
    -- Get readings and sourcevalues separately
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
    -- Print in format: n,readings,sourcevalues
    print(n .. "," .. readings_str .. "," .. source_str)
end
```

הפקודות/פונקציות שמשתמשים בהן כאן:

- `local n = defbuffer1.n`
- `if n == 0 then ... else ... end`
- `print("EMPTY")`
- `local readings_str = ""`
- `local source_str = ""`
- `for i = 1, n do ... end`
- `if i > 1 then ... end`
- שרשור מחרוזות:  
  - `readings_str = readings_str .. ","`  
  - `source_str = source_str .. ","`  
  - `readings_str = readings_str .. tostring(defbuffer1.readings[i])`  
  - `source_str = source_str .. tostring(defbuffer1.sourcevalues[i])`
- `print(n .. "," .. readings_str .. "," .. source_str)`

---

## 5. תקציר – רשימת כל הפקודות לבדיקה ידנית

### 5.1 SCPI (מול PyVISA / NI‑MAX)

להלן סיכום הפקודות ברמת SCPI, עם הסוג (Read / Write / Query) כדי שתוכל להריץ אותן ישירות ב‑NI‑MAX:

| **Command**     | **Type**  | **איך להריץ ב‑NI‑MAX**                          | **הערות**                          |
|-----------------|-----------|-------------------------------------------------|-------------------------------------|
| `*LANG?`        | QUERY     | לכתוב `*LANG?` ולקרוא תשובה אחת                | מחזיר את מצב השפה הנוכחי          |
| `*LANG SCPI`    | WRITE     | לכתוב `*LANG SCPI` (אין קריאת תשובה)           | מעביר את המכשיר למצב SCPI         |
| `SYST:ERR?`     | QUERY     | לכתוב `SYST:ERR?` ולקרוא תשובה                 | מחזיר קוד שגיאה והודעה            |
| `*ESR?`         | QUERY     | לכתוב `*ESR?` ולקרוא תשובה                     | קורא Event Status Register         |
| `*OPC?`         | QUERY     | לכתוב `*OPC?` ולקרוא `"1"` כשתם הביצוע         | סנכרון לסיום פעולה                 |
| `loadscriptrun` | WRITE (*) | **לא כפקודה בודדת!** ראה דוגמת בלוק למעלה      | יש לשלוח יחד עם הסקריפט וה‑`endscript` |
| `endscript`     | WRITE (*) | חלק מאותו בלוק כמו `loadscriptrun`             | סוגר בלוק סקריפט                   |

> (*) בפועל, ב‑NI‑MAX עדיף להדביק את כל הבלוק יחד (ראה סעיף 2) ולא לנסות להריץ `loadscriptrun` לבד.

### 5.2 TSP / Lua – סקריפט הסוויפ

הפקודות האלה **אינן SCPI** – הן רצות **רק בתוך בלוק `loadscriptrun ... endscript`**. ב‑NI‑MAX בודקים אותן ע״י שליחת הבלוק המלא.

| **Lua / TSP Command**                            | **Type**             | **הערה**                                 |
|--------------------------------------------------|----------------------|-------------------------------------------|
| `reset()`                                        | TSP (WRITE in script)| איפוס מכשיר                               |
| `defbuffer1.clear()`                             | TSP                  | ניקוי ה‑buffer                            |
| `smu.source.func = smu.FUNC_DC_VOLTAGE`          | TSP                  | מקור מתח                                  |
| `smu.measure.func = smu.FUNC_DC_CURRENT`         | TSP                  | מדידת זרם                                 |
| `smu.measure.sense = smu.SENSE_2_WIRE`           | TSP                  | 2‑wire                                    |
| `smu.measure.range = <current_range>`            | TSP                  | טווח זרם ידני                             |
| `smu.source.ilimit.level = <current_limit>`      | TSP                  | הגדרת current compliance למתח מקור       |
| `smu.measure.autozero.enable = smu.OFF`          | TSP                  | כיבוי AutoZero                            |
| `smu.source.output = smu.ON` / `smu.OFF`         | TSP                  | הדלקה/כיבוי יציאה                        |
| `smu.source.voltage.level = <value>`             | TSP                  | קביעת מתח ה‑source                        |
| `smu.measure.read(defbuffer1)`                   | TSP                  | מדידה וכתיבה ל‑`defbuffer1`              |
| `delay(<dwell_time>)`                            | TSP                  | השהייה בין נקודות                         |
| `for i = 0, N do ... end`                        | TSP                  | לולאת סוויפ                               |
| `waitcomplete()`                                 | TSP                  | המתנה לסיום כל הפעולות                   |

### 5.3 TSP / Lua – סקריפט קריאת הנתונים

| **Lua / TSP Command**                            | **Type**             | **הערה**                                  |
|--------------------------------------------------|----------------------|--------------------------------------------|
| `local n = defbuffer1.n`                         | TSP                  | מספר הנקודות ב‑buffer                     |
| `if n == 0 then ... else ... end`                | TSP                  | לוגיקה לפי האם יש נתונים                  |
| `print("EMPTY")`                                 | TSP (PRINT)          | כותב טקסט ל‑output                         |
| `local readings_str = ""`                        | TSP                  | מחרוזת לקריאות זרם                        |
| `local source_str = ""`                          | TSP                  | מחרוזת למתחים                             |
| `for i = 1, n do ... end`                        | TSP                  | לולאה על כל נקודות ה‑buffer               |
| `readings_str = readings_str .. ","`             | TSP                  | שרשור פסיק בין ערכים                      |
| `source_str = source_str .. ","`                 | TSP                  | שרשור פסיק בין ערכים                      |
| `readings_str = readings_str .. tostring(...)`   | TSP                  | שרשור ערך זרם                              |
| `source_str = source_str .. tostring(...)`       | TSP                  | שרשור ערך מתח                              |
| `print(n .. "," .. readings_str .. "," .. source_str)` | TSP (PRINT)   | מדפיס בפורמט CSV לקריאה ב‑SCPI           |

---

אם תרצה, נוכל עכשיו לקחת מתוך הרשימה הזו כל פעם פקודה/בלוק אחד, להריץ אותו ידנית מול המכשיר (למשל דרך NI‑MAX או תוכנית Python קצרה), ולבדוק **בדיוק** באיזו נקודה מתקבלת שגיאת `-110` או `-111`. כך נאתר את הבעיה בצורה הכי מדויקת.



