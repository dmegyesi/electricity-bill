# TODO Move statistics printing to functions
# TODO Write output stats to CSV
# TODO Split code to multiple files
# TODO Tests
# TODO Set up Makefile, add README, sample data files

import csv
import os
from collections import defaultdict
from datetime import datetime, timedelta

from dateutil import easter


class ElectricityData:
    date = ""
    hour = 0
    consumption = 0.0

    def __init__(self, date, hour, consumption):
        self.date = date
        self.hour = hour
        self.consumption = consumption

    # When checking for equivalence, only consider the day and hour
    def __eq__(self, other):
        return self.date == other.date and self.hour == other.hour

    # Sort by day and hour
    def __lt__(self, other):
        return self.date < other.date or (self.date == other.date and self.hour < other.hour)

    def __cmp__(self, other):
        return cmp(self.date, other.date)


# Find all CSV files in the input folder and parse them
INPUTFOLDER = "input/"

files = os.listdir(INPUTFOLDER)
files = list(filter(lambda f: f.endswith(".csv"), files))

importedData = []

for file in files:
    with open(INPUTFOLDER + file, newline="") as inputFile:
        reader = csv.reader(inputFile, delimiter=";")
        next(reader)  # drop the header
        for row in reader:
            # Format:
            # CUPS;Date;Time;AE_kWh;REAL/ESTIMATED
            # ES0000000000000000AA0A;04/04/2021;1;0,116;R
            date = datetime.strptime(row[1], "%d/%m/%Y")
            hour = int(row[2])  # 1..24 -> 0:00-0:59: 1, 1:00-1:59: 2 ... 23:00-23:59: 24
            consumption = float(str(row[3]).replace(",", ".")) if row[3] != "" else 0.0
            isRealOrEstimate = row[4]

            # If missing data or not real consumption, drop it
            if "" in (row[1], row[2], row[3], row[4]) or isRealOrEstimate == "E":
                next(reader)
            else:
                importedData.append(ElectricityData(date, hour, consumption))

importedData.sort()
minDate = min(importedData).date
maxDate = max(importedData).date

print(f"Total records: {len(importedData)}")
print(f"Earliest record: {minDate.date()}")
print(f"Latest record: {maxDate.date()}")

# All the years we imported
years = list(range(minDate.year, maxDate.year + 1))

# The nationwide common bank holidays (month, day) have a discount in the electricity bill
# There's one missing, Easter Friday, that must be calculated for each year
FIX_NATIONAL_HOLIDAYS = [
    (1, 1),
    (5, 1),
    (10, 12),
    (11, 1),
    (12, 6),
    (12, 8),
    (12, 25)
]


def getBankHolidays(years):
    bankHolidays = set()

    for year in years:

        # Add the static, well-known days
        for holiday in FIX_NATIONAL_HOLIDAYS:
            month, day = holiday
            bankHolidays.add(datetime(year, month, day))

        # And finally the Easter Friday (Viernes Santo)
        easterSunday = easter.easter(year)
        easterFriday = easterSunday - timedelta(days=2)
        bankHolidays.add(datetime(easterFriday.year, easterFriday.month, easterFriday.day))

    return bankHolidays


bankHolidays = getBankHolidays(years)

# Calculate the daily and monthly consumptions, based on the hour categories

# With defaultdict we don't need to validate if the key exists and initialize it
dailyConsumptions = defaultdict(lambda: defaultdict(float))
monthlyConsumptions = defaultdict(lambda: defaultdict(float))

# Hour categories; input hour is between 1st..24th hour
HOUR_DESIGNATIONS = {}
for h in range(1, 10):
    HOUR_DESIGNATIONS[h] = "valle"
for h in range(9, 11):
    HOUR_DESIGNATIONS[h] = "llana"
for h in range(15, 19):
    HOUR_DESIGNATIONS[h] = "llana"
for h in range(23, 25):
    HOUR_DESIGNATIONS[h] = "llana"
for h in range(11, 15):
    HOUR_DESIGNATIONS[h] = "punta"
for h in range(19, 23):
    HOUR_DESIGNATIONS[h] = "punta"

# Categorize the parsed hourly consumptions into daily punta, llana, valle
for record in importedData:
    date = record.date

    # Bank holidays and weekends -> 24h hora valle
    if date in bankHolidays or date.weekday() >= 5:
        dailyConsumptions[date]["valle"] += record.consumption
        monthlyConsumptions[datetime(date.year, date.month, 1)]["valle"] += record.consumption

    # For the rest, depends on the hour
    else:
        dailyConsumptions[date][HOUR_DESIGNATIONS[record.hour]] += record.consumption
        monthlyConsumptions[datetime(date.year, date.month, 1)][HOUR_DESIGNATIONS[record.hour]] += record.consumption

for day in dailyConsumptions:
    print(f"{day.strftime('%Y-%m-%d %a')}\n"
          f"\tpunta: {round(dailyConsumptions[day]['punta'], 2)} kWh\n"
          f"\tllana: {round(dailyConsumptions[day]['llana'], 2)} kWh\n"
          f"\tvalle: {round(dailyConsumptions[day]['valle'], 2)} kWh\n")

for month in monthlyConsumptions:
    print(f"{month.strftime('%Y-%m')}\n"
          f"\tpunta: {round(monthlyConsumptions[month]['punta'], 2)} kWh\n"
          f"\tllana: {round(monthlyConsumptions[month]['llana'], 2)} kWh\n"
          f"\tvalle: {round(monthlyConsumptions[month]['valle'], 2)} kWh\n")
