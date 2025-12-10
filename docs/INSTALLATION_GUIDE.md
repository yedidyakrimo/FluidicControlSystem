# מדריך התקנה מלא - Fluidic Control System

## ✅ מה שכבר הותקן (דרך pip)

כל החבילות הבאות כבר הותקנו:
- ✅ customtkinter
- ✅ matplotlib
- ✅ pyserial
- ✅ nidaqmx (החבילה Python, אבל צריך את ה-driver)
- ✅ numpy
- ✅ pyvisa
- ✅ pyvisa-py
- ✅ pandas
- ✅ openpyxl

## 🔧 מה שצריך להתקין ידנית

### 1. NI-VISA (חובה עבור Keithley 2450 SMU)

**למה צריך:**
- Keithley 2450 SMU מתחבר דרך USB
- pyvisa-py לא תומך ב-USB VISA resources
- NI-VISA הוא ה-backend המומלץ

**איך להתקין:**

1. **הורד את NI-VISA:**
   - גש לאתר: https://www.ni.com/en-il/support/downloads/drivers/download.ni-visa.html
   - הורד את הגרסה המתאימה ל-Windows (64-bit)
   - או ישירות: https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html

2. **התקן:**
   - הפעל את קובץ ההתקנה שהורדת
   - עקוב אחר ההוראות (התקנה סטנדרטית)
   - הפעל מחדש את המחשב אם נדרש

3. **בדיקה:**
   ```bash
   py -c "import pyvisa; rm = pyvisa.ResourceManager(); print(rm)"
   ```
   אם זה עובד, תראה משהו כמו: `Resource Manager of Visa Library at C:\...`

### 2. NI-DAQmx Runtime (חובה עבור NI USB-6002)

**למה צריך:**
- החבילה `nidaqmx` ב-Python דורשת את ה-driver של National Instruments
- ללא ה-driver, לא ניתן להתחבר ל-NI USB-6002

**איך להתקין:**

1. **הורד את NI-DAQmx Runtime:**
   - גש לאתר: https://www.ni.com/en/support/downloads/drivers/download.ni-daqmx.html
   - הורד את הגרסה המתאימה ל-Windows (64-bit)
   - או ישירות: https://www.ni.com/en/support/downloads/drivers/download.ni-daqmx.html

2. **התקן:**
   - הפעל את קובץ ההתקנה שהורדת
   - עקוב אחר ההוראות (התקנה סטנדרטית)
   - הפעל מחדש את המחשב אם נדרש

3. **בדיקה:**
   - לאחר ההתקנה, התוכנה אמורה לזהות את ה-NI USB-6002 אוטומטית
   - אם יש שגיאה, בדוק שהמכשיר מחובר ו-Windows מזהה אותו

### 3. חלופות (אם NI-VISA לא עובד)

**Keysight IO Libraries:**
- אם NI-VISA לא עובד, תוכל להתקין את Keysight IO Libraries
- אתר: https://www.keysight.com/us/en/lib/software-detail/instrument-driver/io-libraries-suite-2099097.html

## 📋 סיכום - רשימת התקנות

### ✅ כבר הותקן (אוטומטי):
- [x] כל החבילות מ-requirements.txt
- [x] pyvisa-py

### ⚠️ צריך להתקין ידנית:
- [ ] **NI-VISA** - להורדה: https://www.ni.com/en-il/support/downloads/drivers/download.ni-visa.html
- [ ] **NI-DAQmx Runtime** - להורדה: https://www.ni.com/en/support/downloads/drivers/download.ni-daqmx.html

## 🔍 בדיקת התקנה

לאחר התקנת כל הרכיבים, הרץ:

```bash
py main_app.py
```

אם הכל תקין, אמור לראות:
- ✅ "Using NI-VISA backend" או "Using pyvisa-py backend"
- ✅ "Connected to NI device: Dev1" (אם המכשיר מחובר)
- ✅ "Connected to Keithley 2450 SMU" (אם המכשיר מחובר)

אם יש שגיאות:
- בדוק שהמכשירים מחוברים
- בדוק ש-Windows מזהה את המכשירים ב-Device Manager
- ודא שהתקנת את כל ה-drivers

## 📞 תמיכה

אם יש בעיות:
1. בדוק את `VISA_INSTALLATION.md` לפרטים נוספים על VISA
2. ודא שהמכשירים מחוברים ופועלים
3. בדוק את ה-Device Manager ב-Windows


