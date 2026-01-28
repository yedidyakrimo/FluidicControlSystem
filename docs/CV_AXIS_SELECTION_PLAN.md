# תוכנית: הוספת בחירת צירים לטאב CV

## מטרה
להוסיף אפשרות לשנות את הצירים של הגרף בטאב CV, בדיוק כמו בטאב הראשי, אבל רק לפרמטרים הרלוונטיים ל-CV.

## פרמטרים רלוונטיים ל-CV
- **Voltage** (מתח) - נתוני מתח מהמדידה
- **Current** (זרם) - נתוני זרם מהמדידה  
- **Time** (זמן) - זמן שחלף מתחילת המדידה

## שינויים נדרשים

### 1. הוספת cv_time_data ב-`__init__` (`gui/tabs/cv_tab.py`)
- הוסף `self.cv_time_data = []` לרשימת ה-data arrays
- זה ישמש לאחסון זמן שחלף לכל נקודת מדידה

### 2. עדכון `_run_cv_sweep_thread` (`gui/tabs/cv_tab.py`)
- חשב זמן שחלף מתחילת המדידה לכל נקודה
- שמור את הזמן ב-`cv_time_data` במקביל ל-voltage ו-current
- אפשר לחשב זמן לפי: `time_elapsed = index / points_per_second` או לפי `time.time()` מתחילת המדידה

### 3. הוספת ComboBoxes לבחירת צירים (`gui/tabs/cv_tab.py` - `create_widgets()`)
- הוסף Frame חדש באזור `graph_control_frame` (שורה ~163)
- X-Axis ComboBox עם ערכים: `['Voltage', 'Current', 'Time']`
- Y-Axis ComboBox עם ערכים: `['Voltage', 'Current']`
- ברירת מחדל: X-Axis = 'Voltage', Y-Axis = 'Current' (הגרף הקלאסי)
- הוסף command: `command=self.on_cv_axis_change`

### 4. הוספת פונקציה `on_cv_axis_change()` (`gui/tabs/cv_tab.py`)
- קרא את הערכים הנבחרים מה-ComboBoxes
- קרא ל-`plot_cv_xy_graph()` עם הצירים הנבחרים

### 5. הוספת פונקציה `plot_cv_xy_graph()` (`gui/tabs/cv_tab.py`)
- דומה ל-`plot_iv_xy_graph()` ב-IV Tab
- קבל `x_axis_type` ו-`y_axis_type` כפרמטרים
- בחר את הנתונים המתאימים לפי הצירים:
  - אם X-Axis = 'Voltage': `x_data = cv_voltage_data`
  - אם X-Axis = 'Current': `x_data = cv_current_data`
  - אם X-Axis = 'Time': `x_data = cv_time_data`
  - אם Y-Axis = 'Voltage': `y_data = cv_voltage_data`
  - אם Y-Axis = 'Current': `y_data = cv_current_data`
- עדכן labels ו-title לפי הצירים הנבחרים
- צייר את הגרף

### 6. עדכון `_update_cv_graph()` (`gui/tabs/cv_tab.py`)
- שנה את הפונקציה לקרוא ל-`plot_cv_xy_graph()` עם הצירים הנבחרים
- או פשוט קרא ל-`on_cv_axis_change()` כדי לעדכן את הגרף

### 7. עדכון `run_cv_sweep()` (`gui/tabs/cv_tab.py`)
- נקה גם `cv_time_data` כשמתחיל מדידה חדשה

### 8. (אופציונלי) הוספת פונקציה `get_axis_unit_label()` (`gui/tabs/cv_tab.py`)
- אם רוצים תמיכה ב-SI units (כמו ב-IV Tab)
- זה לא חובה, אבל יכול להיות שימושי

## סדר ביצוע
1. הוספת cv_time_data ב-__init__
2. עדכון _run_cv_sweep_thread - חישוב ושמירת time_data
3. עדכון run_cv_sweep - ניקוי time_data
4. הוספת ComboBoxes ב-create_widgets
5. הוספת on_cv_axis_change()
6. הוספת plot_cv_xy_graph()
7. עדכון _update_cv_graph() להשתמש בפונקציה החדשה

## הערות
- Time data יכול להיות מחושב לפי אינדקס: `time = index / points_per_second`
- או לפי זמן אמיתי: `time = time.time() - start_time`
- מומלץ להשתמש בזמן אמיתי אם אפשר
- אם אין נתוני זמן, אפשר להציג הודעה או להסתיר את 'Time' מה-ComboBox

