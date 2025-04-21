import datetime
import os
import re
import time
import argparse
import pandas as pd
import requests

# Constants for API requests
BASE_URL = "https://api.wigle.net/api/v2/network/search"
REQUEST_DELAY = 5
MAX_RETRIES = 3

def is_valid_token(token):
    return bool(re.fullmatch(r"[\w\-_=]*", token))

def send_request(headers, latrange1, latrange2, longrange1, longrange2, search_after=None, row_num=None, after_date=None):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join("tests", f"{row_num}_{latrange1}_{longrange1}_{timestamp}.csv")

    current_count = 0
    total_count = None
    retries = 0
    if (after_date is None):
        after_date = 20200319

    query_params = {
        "latrange1": latrange1,
        "latrange2": latrange2,
        "longrange1": longrange1,
        "longrange2": longrange2,
        "lastupdt": after_date,
        "rcoisMinimum": 1,
    }

    if search_after:
        query_params["searchAfter"] = search_after

    print("Retrieving results...")

    with open(filename, "a") as f:
        while retries < MAX_RETRIES:
            try:
                response = requests.get(BASE_URL, params=query_params, headers=headers)
                status_code = response.status_code

                if status_code == 200:
                    data = response.json()
                    results = data["results"]
                    current_count += len(results)

                    if total_count is None:
                        total_count = data["totalResults"]

                    print(f"Retrieved {current_count} out of {total_count} results")

                    # Filter the results
                    filtered_results = [result for result in results if "rcois" in result and ("4096" in result["rcois"] or "5a03ba0000" in result["rcois"])]

                    if filtered_results:
                        df = pd.DataFrame(filtered_results)
                        df.to_csv(f, index=False, header=f.tell() == 0, escapechar="\\")

                    if current_count >= total_count:
                        break

                    search_after = data.get("searchAfter")
                    if not search_after:
                        break  # No more results to retrieve

                    query_params["searchAfter"] = search_after
                    time.sleep(REQUEST_DELAY)

                elif status_code == 401:
                    print("Unauthorized. Check your API token.")
                    break

                elif status_code == 429:
                    print("Too many requests. Saving the current results.")
                    break

                else:
                    print(f"Error {status_code}: Failed to retrieve results.")
                    break

            except requests.exceptions.Timeout:
                print("Request timed out. Retrying...")
                retries += 1
                time.sleep(REQUEST_DELAY)

            except requests.exceptions.TooManyRedirects:
                print("Too many redirects. Terminating request.")
                break

            except requests.exceptions.ConnectionError:
                print("Connection Error. Retrying...")
                retries += 1
                time.sleep(REQUEST_DELAY)

            except Exception as e:
                print(f"An error occurred: {e}")
                break

        print(f"All results retrieved. Total results: {current_count}")

    # Read the CSV file and print the number of rows
    if os.path.exists(filename):
        df = pd.read_csv(filename)
        print(f"Number of rows in the CSV file: {len(df)}")
    else:
        print(f"CSV file {filename} not found.")

def main():
    parser = argparse.ArgumentParser(description="Wigle API Script")
    parser.add_argument("--token", required=True, help="Your API token")
    parser.add_argument("--csv_file", required=True, help="CSV file containing coordinates")
    parser.add_argument("--row_num", type=int, required=True, help="Row number to read coordinates from (0-based index)")
    parser.add_argument("--after_date", required=False, help="Provide a date to scan from, default is 20200319")
    args = parser.parse_args()

    headers = {"Authorization": f"Basic {args.token}"}

    # Read the specified row from the CSV file
    try:
        df = pd.read_csv(args.csv_file, delim_whitespace=True, header=None)
        row = df.iloc[args.row_num]
        min_lat, max_lat, min_long, max_long = row[0], row[1], row[2], row[3]
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    send_request(headers, min_lat, max_lat, min_long, max_long, row_num=args.row_num, after_date=args.after_date)

if __name__ == "__main__":
    main()

