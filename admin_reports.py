import mysql.connector
from contextlib import contextmanager
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


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


plot_cancellation_report_with_labels()