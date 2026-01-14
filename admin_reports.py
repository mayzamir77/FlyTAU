import mysql.connector
from contextlib import contextmanager
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np


@contextmanager
def db_cur():
    mydb = None
    cursor = None
    try:
        mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="FLYTAU",
            autocommit=True
        )
        cursor = mydb.cursor()
        yield cursor

    except mysql.connector.Error as err:
        raise err

    finally:
        if cursor:
            cursor.close()
        if mydb:
            mydb.close()


def plot_cancellation_report_with_labels():
    query = """
    SELECT
        YEAR(booking_date) AS year,
        MONTH(booking_date) AS month,
        ROUND(
            SUM(CASE WHEN booking_status = 'Customer Cancellation' THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
            2
        ) AS cancellation_rate_percentage
    FROM booking
    GROUP BY YEAR(booking_date), MONTH(booking_date)
    ORDER BY year, month;
    """

    try:
        with db_cur() as cursor:
            cursor.execute(query)
            df = pd.DataFrame(cursor.fetchall(), columns=[desc[0] for desc in cursor.description])

        df['period'] = df['year'].astype(str) + '-' + df['month'].astype(str).str.zfill(2)

        plt.figure(figsize=(10, 6))

        bars = plt.bar(df['period'], df['cancellation_rate_percentage'], color='skyblue', edgecolor='navy')

        plt.bar_label(bars, padding=3, fmt='%.1f%%', fontweight='bold')

        plt.title('Monthly Booking Customer Cancellation Rate', fontsize=14)
        plt.xlabel('Year - Month')
        plt.ylabel('Cancellation Rate (%)')

        plt.ylim(0, 115)

        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.show()

    except Exception as e:
        print(f"Error: {e}")


def plot_bookings_vs_cancellations():
    query = """
    SELECT
        YEAR(booking_date) AS year,
        MONTH(booking_date) AS month,
        COUNT(*) AS total_bookings,
        SUM(CASE WHEN booking_status = 'Customer Cancellation' THEN 1 ELSE 0 END) AS cancelled_count
    FROM booking
    GROUP BY YEAR(booking_date), MONTH(booking_date)
    ORDER BY year, month;
    """
    try:
        with db_cur() as cursor:
            cursor.execute(query)
            df = pd.DataFrame(cursor.fetchall(), columns=[desc[0] for desc in cursor.description])

        df['period'] = df['year'].astype(str) + '-' + df['month'].astype(str).str.zfill(2)

        # הגדרות מיקום לעמודות הצמודות
        x = np.arange(len(df['period']))
        width = 0.35

        plt.figure(figsize=(12, 6))

        # ציור שתי העמודות
        plt.bar(x - width / 2, df['total_bookings'], width, label='Total Bookings', color='skyblue')
        plt.bar(x + width / 2, df['cancelled_count'], width, label='Cancellations', color='orange')

        plt.title('Total Bookings vs Customer Cancellations', fontsize=14)
        plt.xlabel('Year - Month')
        plt.ylabel('Count')
        plt.xticks(x, df['period'], rotation=45, ha='right')
        plt.legend()
        plt.grid(axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout()
        plt.show()

    except Exception as e:
        print(f"Error: {e}")


def plot_revenue_by_aircraft_original_query():
    # השאילתה המקורית שלך בדיוק כפי שכתבת אותה
    query = """
    SELECT 
        a.size AS Size, 
        a.manufacturer AS Manufacturer, 
        c.class_type AS Class, 
        SUM(IFNULL(clean_bookings.payment, 0)) AS Revenue
    FROM aircraft AS a
    JOIN class AS c ON a.aircraft_id = c.aircraft_id
    LEFT JOIN flight AS f ON a.aircraft_id = f.aircraft_id
    LEFT JOIN (
        SELECT DISTINCT b.booking_id, b.flight_id, b.payment, ss.class_type
        FROM booking AS b
        JOIN selected_seats_in_booking AS ss ON b.booking_id = ss.booking_id
    ) AS clean_bookings ON f.flight_id = clean_bookings.flight_id 
                       AND c.class_type = clean_bookings.class_type
    GROUP BY a.size, a.manufacturer, c.class_type;
    """
    try:
        with db_cur() as cursor:
            cursor.execute(query)
            df = pd.DataFrame(cursor.fetchall(), columns=[desc[0] for desc in cursor.description])

        if df.empty:
            print("No data found.")
            return

        # יצירת עמודה משולבת של יצרנית וגודל כדי שיהיה קל לראות בגרף
        df['Aircraft'] = df['Manufacturer'] + " (" + df['Size'] + ")"

        plt.figure(figsize=(12, 6))

        # גרף עמודות פשוט שמראה הכנסה לפי סוג מטוס ומחולק למחלקות (Hue)
        sns.barplot(data=df, x='Aircraft', y='Revenue', hue='Class', palette='Set2')

        plt.title('Revenue by Aircraft and Class', fontsize=14)
        plt.xlabel('Aircraft Type (Size)')
        plt.ylabel('Total Revenue')
        plt.xticks(rotation=30)
        plt.legend(title='Seat Class')
        plt.grid(axis='y', linestyle='--', alpha=0.6)
        plt.tight_layout()
        plt.show()

    except Exception as e:
        print(f"Error: {e}")


# הפעלה
plot_revenue_by_aircraft_original_query()