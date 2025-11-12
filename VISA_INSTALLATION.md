# הוראות התקנת VISA עבור Keithley 2450 SMU

## בעיה: המכשיר לא מזוהה

אם ה-Keithley 2450 לא מזוהה, זה בגלל שחסר VISA backend שתומך ב-USB.

## פתרון: התקנת NI-VISA

### שלב 1: הורדת NI-VISA

1. גש לאתר National Instruments:
   https://www.ni.com/en-il/support/downloads/drivers/download.ni-visa.html

2. הורד את הגרסה המתאימה ל-Windows שלך (64-bit)

### שלב 2: התקנה

1. הפעל את קובץ ההתקנה שהורדת
2. עקוב אחר ההוראות (התקנה סטנדרטית)
3. הפעל מחדש את המחשב אם נדרש

### שלב 3: בדיקה

לאחר ההתקנה, הפעל את התוכנה ובדוק:

1. פתח את התוכנה `main_app.py`
2. עבור לטאב "IV"
3. לחץ על "Detect SMU" או "List Devices"
4. המכשיר אמור להופיע

## חלופה: Keysight IO Libraries

אם NI-VISA לא עובד, תוכל להתקין את Keysight IO Libraries:
https://www.keysight.com/us/en/lib/software-detail/instrument-driver/io-libraries-suite-2099097.html

## בדיקת VISA Backend

לבדוק איזה VISA backend מותקן, הרץ:

```python
python -c "import pyvisa; rm = pyvisa.ResourceManager(); print(rm)"
```

אם זה עובד, תראה משהו כמו: `Resource Manager of Visa Library at C:\...`

## פתרון זמני: pyvisa-py

אם אתה לא יכול להתקין NI-VISA כרגע, `pyvisa-py` כבר מותקן, אבל הוא לא תומך ב-USB VISA resources.

**הערה:** `pyvisa-py` עובד רק עם:
- Serial ports (COM ports)
- TCP/IP connections
- לא עם USB VISA resources

## סיכום

**לשימוש עם Keithley 2450 דרך USB - צריך NI-VISA!**

לאחר התקנת NI-VISA, התוכנה תזהה את המכשיר אוטומטית.




