import pandas as pd

try:
    print("Lecture Excel:")
    df_lecture = pd.read_excel("Lecture_Time_Table_Win'26_v6.xlsx", header=None)
    print(df_lecture.head(3))
except Exception as e:
    print("Error reading Lecture:", e)

print("\n")

try:
    print("Slots Excel:")
    xl = pd.ExcelFile("Slots_Win_2025-26_15Dec2025.xlsx")
    print("Sheet names:", xl.sheet_names)
    df_slots = pd.read_excel(xl, "Slots", header=None)
    print(df_slots.head(5))
except Exception as e:
    print("Error reading Slots:", e)
