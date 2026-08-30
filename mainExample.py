import os
from dotenv import load_dotenv
from tableau_data_pipeline_C3A.data_pipeline import get_data

load_dotenv()

# 1️⃣ Tableau Cloud
try:
    df_tableau = get_data(
        source="tableau_cloud",
        content_url="Regional/sheets/Obesity",
        server=os.getenv("TABLEAU_SERVER"),
        site_content_url=os.getenv("TABLEAU_SITE"),
        token_name=os.getenv("TABLEAU_TOKEN_NAME"),
        token_secret=os.getenv("TABLEAU_TOKEN_SECRET")
    )
    print("Tableau Cloud data:")
    print(df_tableau.head())
except Exception as e:
    print("Error fetching Tableau data:", e)

# 2️⃣ Hyper file
# try:
#     df_hyper = get_data(source="hyper", path=os.getenv("HYPER_FILE_PATH"))
#     print("Hyper file data:")
#     print(df_hyper.head())
# except Exception as e:
#     print("Error reading Hyper file:", e)

# 3️⃣ Local CSV
# try:
#     df_csv = get_data(source="csv", path=os.getenv("LOCAL_CSV_PATH"))
#     print("CSV file data:")
#     print(df_csv.head())
# except Exception as e:
#     print("Error reading CSV:", e)

# 4️⃣ SQL
# try:
#     df_sql = get_data(
#         source="sql",
#         query="SELECT TOP 10 * FROM sales",
#         conn_str=os.getenv("SQL_SERVER_CONN")
#     )
#     print("SQL data:")
#     print(df_sql.head())
# except Exception as e:
#     print("Error reading SQL:", e)