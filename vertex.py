import requests
import time
import json
from math import ceil

# Global dictionary for product mapping (product_id -> ticker_id)
PRODUCT_MAPPING = {}

def update_product_mapping():
    """
    Fetch the latest product mapping from the assets endpoint and update the global dictionary.
    """
    global PRODUCT_MAPPING
    ASSETS_ENDPOINT = "https://gateway.prod.vertexprotocol.com/v2/assets"
    try:
        response = requests.get(ASSETS_ENDPOINT)
        response.raise_for_status()
        symbols = response.json()
        # Create a new mapping from product_id to ticker_id
        new_mapping = {item["product_id"]: item["ticker_id"] for item in symbols}
        if set(new_mapping.keys()) != set(PRODUCT_MAPPING.keys()):
            print("Product mapping updated.")
            PRODUCT_MAPPING = new_mapping
        else:
            print("No new product mapping found.")
    except requests.exceptions.RequestException as e:
        print("Error fetching product symbols:", e)

def chunk_list(lst, chunk_size):
    """
    Yield successive chunks of list lst of size chunk_size.
    """
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

def get_historical_funding_rates(product_ids, count=72, granularity=3600):
    """
    Query the Archive endpoint to get market snapshots for the given product_ids.
    We set max_time to the current time rounded down to the nearest hour plus 5 seconds.
    """
    ARCHIVE_ENDPOINT = "https://archive.prod.vertexprotocol.com/v1"
    headers = {
        "Accept-Encoding": "gzip, br, deflate",
        "Content-Type": "application/json"
    }
    # Round current time down to the nearest hour, then add 5 seconds.
    current_time = int(time.time())
    rounded_time = current_time - (current_time % 3600) + 5

    payload = {
        "market_snapshots": {
            "interval": {
                "count": count,             # e.g., 72 hourly snapshots for 3 days
                "granularity": granularity,   # 3600 seconds = 1 hour
                "max_time": rounded_time      # Nearest hour + 5s
            },
            "product_ids": product_ids      # Batch of product IDs
        }
    }
    try:
        response = requests.post(ARCHIVE_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("snapshots", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching historical funding rates for product_ids {product_ids}: {e}")
        return []

def process_funding_rates(snapshots):
    """
    Process snapshots to extract raw funding rates and map them to ticker symbols.
    
    Assumptions:
      - The API returns the 24hr funding rate multiplied by 1e18.
      - To get the hourly rate, divide by 24.
      
    This function multiplies the hourly rate by 100 to display as a percentage.
    """
    funding_data = {}  # ticker -> list of {timestamp, funding_rate}
    for snapshot in snapshots:
        timestamp = snapshot.get("timestamp")
        funding_rates = snapshot.get("funding_rates", {})
        for prod_id_str, rate_str in funding_rates.items():
            try:
                prod_id = int(prod_id_str)  # Convert key to integer
            except ValueError:
                prod_id = prod_id_str
            ticker = PRODUCT_MAPPING.get(prod_id, f"Unknown({prod_id})")
            try:
                raw_value = float(rate_str)  # This is the 24hr funding rate multiplied by 1e18
            except ValueError:
                raw_value = 0.0
            # Hourly funding rate = (raw_value/1e18)/24, then *100 to convert to percent.
            funding_rate = ((raw_value / 1e18) / 24) * 100
            if ticker not in funding_data:
                funding_data[ticker] = []
            funding_data[ticker].append({
                "timestamp": timestamp,
                "funding_rate": funding_rate
            })
    return funding_data

def main():
    # Step 1: Update the global product mapping.
    update_product_mapping()
    
    # Step 2: Get list of product IDs from the mapping.
    product_ids = list(PRODUCT_MAPPING.keys())
    print("Using product IDs:", product_ids)
    
    # Calculate the maximum batch size allowed: floor(2000 / count)
    count = 72  # number of snapshots (for 3 days hourly)
    max_batch_size = 2000 // count  # integer division
    print(f"Max batch size allowed: {max_batch_size}")
    
    all_snapshots = []
    # Step 3: Process in batches to stay within the limit.
    for batch in chunk_list(product_ids, max_batch_size):
        print("Fetching snapshots for batch:", batch)
        snapshots = get_historical_funding_rates(batch, count=count, granularity=3600)
        if snapshots:
            all_snapshots.extend(snapshots)
        # Sleep a little between batches to respect rate limits.
        time.sleep(0.5)
    
    if not all_snapshots:
        print("No snapshots retrieved.")
        return
    
    # Debug: Print out the first snapshot to inspect its structure.
    print("Debug: First raw snapshot:")
    print(json.dumps(all_snapshots[0], indent=2))
    
    # Step 4: Process snapshots to map funding rates to ticker symbols.
    funding_data = process_funding_rates(all_snapshots)
    
    # Step 5: Calculate the average funding rate for each ticker.
    # The instruction is to sum up all hourly rates for each ticker and divide by 3.
    # (This is equivalent to summing the 72 hourly snapshots and then dividing by 3 to get the average daily funding rate.)
    average_rates = {}
    for ticker, entries in funding_data.items():
        total_rate = sum(entry['funding_rate'] for entry in entries)
        average_rate = total_rate / 3
        average_rates[ticker] = average_rate
    
    # Sort tickers from highest to lowest average rate.
    sorted_rates = sorted(average_rates.items(), key=lambda x: x[1], reverse=True)
    
    # Step 6: Write the results to a text file called 'vertexrates.txt'.
    with open("vertexrates.txt", "w") as f:
        f.write("Ticker\tAverage Funding Rate (%)\n")
        f.write("---------------------------------\n")
        for ticker, avg in sorted_rates:
            f.write(f"{ticker}\t{avg:.6f}\n")
    
    # Also print the results.
    for ticker, avg in sorted_rates:
        print(f"{ticker}: {avg:.6f}%")

if __name__ == "__main__":
    main()
