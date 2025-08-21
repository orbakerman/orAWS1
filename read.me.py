# platform-cli

כלי שורת פקודה (CLI) לניהול משאבי AWS: EC2, S3, Route53
מיועד לשימוש על ידי מפתחים תוך שמירה על מגבלות ובקרות אבטחה.

---

## ✨ יכולות

- ✅ יצירה, הפעלה, עצירה ורשימת EC2 (עם מגבלת 2 מופעלים)
- ✅ ניהול דליי S3 עם בקרת public/private
- ✅ ניהול רשומות DNS בתוך Route53 zones
- ✅ כל המשאבים מתויגים אוטומטית (CreatedBy=platform-cli, Owner)

---

## 🧰 דרישות מוקדמות

- Python 3.8+
- AWS CLI מותקן ומוגדר (`aws configure` או פרופיל)
- הרשאות מתאימות ב-AWS (EC2, S3, Route53, SSM)

---

## ⚙ התקנה

```bash
git clone <url-of-your-repo>
cd platform-cli
pip install -r requirements.txt
