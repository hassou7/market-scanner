# exchanges/sf_pairs_service.py

import requests
import pandas as pd

class SFPairsService:

    def __init__(self):
        self.base_url = "https://webapi.sevenfigures.ch/api/DataAnalyses/"

    def get_pairs_of_exchange(self, exchange):
        url = self.base_url + "GetPairsList"
        
        # Define query parameters
        params = {
            "exchange": exchange,
        }

        print(f"Fetching pairs for exchange: {exchange}")

        # Make the GET request
        response = requests.get(url, params=params)

        if response.status_code == 200:
            try:
                results = response.json()  # Corrected variable usage
                return results  # Return the list of pairs
            except ValueError:
                print("Error: Response is not in JSON format")
                return [] 
        else:
            print(f"Error {response.status_code}: {response.text}")
            return [] 


    def get_ohlcv_for_pair(self, pair_token, quote, exchange, timeframe, quantity):

        # Define the API endpoint
        url = self.base_url + "GetPairOHLCVAndSignals"
            
        # Define query parameters
        params = {
            "token": pair_token,
            "quote": quote,
            "exchange": exchange,
            "timeframe": timeframe,
            "quantity": quantity
        }
            
        # Make the GET request
        response = requests.get(url, params=params)
            
        # Print the response
        if response.status_code == 200:
            result = response.json()
            result_df = pd.DataFrame(result["Datas"])
            return result_df
            #print(pd.DataFrame(result_df))  # Parse JSON response
        else:
            print(f"Error {response.status_code}: {response.text}")
