# Vertex Funding Rates

This repository contains a Python script that retrieves historical funding rate data from the Vertex Protocol Archive (indexer) API, processes hourly snapshots for multiple products, calculates the average daily funding rate (by summing 72 hourly snapshots over 3 days and dividing by 3), and writes the results to a text file (`vertexrates.txt`) sorted from highest to lowest.

## Overview

The script performs the following tasks:

- **Product Mapping:**  
  Retrieves product mappings (product ID to ticker) from the Vertex V2 assets endpoint.

- **Historical Data Query:**  
  Queries the Vertex Archive API for market snapshots with a granularity of 3600 seconds (1 hour). The `max_time` parameter is set to the nearest hour plus 5 seconds to capture data just after a funding event.

- **Data Processing:**  
  Processes the raw funding rates. The API returns a 24‑hour funding rate scaled by 1e18; the script converts it into an hourly rate (dividing by 24) and then into a percentage (multiplying by 100).

- **Average Calculation:**  
  Averages the hourly funding rates over 3 days (72 snapshots divided by 3) for each ticker.

- **Output:**  
  Writes the sorted (highest to lowest average rate) results to a text file named `vertexrates.txt`.

## Requirements

- Python 3.6 or higher
- `requests` library

## Installation

1. Clone the repository:

```bash
git clone https://github.com/Rockazim/vertex-funding-rates.git
cd vertex-funding-rates
```
2. install the required library using pip:

```bash
pip install requests
```
3. Run the Python script
```bash
python vertex.py
```
