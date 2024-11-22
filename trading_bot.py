import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from datetime import datetime
import time
import logging
import json
import threading
import re
import connectDB
import settrade_v2
from settrade_v2 import Investor
import decimal
#set up loging
logging.basicConfig(
    filename="App.log",level=logging.INFO,format="%(asctime)s - %(message)s"
)

#load config from json file
with open("config.json") as config_file:
    config =json.load(config_file)

# API setting
APP_ID = config["app_id"]
APP_SECRET = config["app_secret"]
APP_CODE = config["app_code"]
BROKER_ID= config["broker_id"]
IS_AUTO_QUEUE = config["is_auto_queue"]
ACCOUNT_NO_D = config["account_no_D"]
ACOUNT_NO_E = config["account_no_E"]
MIN_VALUE = config["min_value"]
MIN_INSIDERS = config["min_insiders"]
GAIN_THRESHOLD = config["gain_threshold"]
DROP_THRESHOLD = config["drop_threshold"]
MIN_OWN_CHANGE = config["min_own_change"]

# lock for thread-safe operation
lock = threading.Lock()
# Define History Data
trade_history = []

def clean_and_convert(value, value_type="float"):
    """
    Cleans a string value by removing unwanted characters and attempts to convert to a given type.
    Args:
        value (str): The string value to clean and convert.
        value_type (str): The desired type for conversion ("float" or "int").
    Returns:
        Converted value if successful, or None if conversion fails.
    """
    # Use regular expressions to extract the numeric parts
    cleaned_value = re.sub(r"[^\d.-]", "", value)

    try:
        if value_type == "float":
            return float(cleaned_value) if cleaned_value else None
        elif value_type == "int":
            return int(cleaned_value) if cleaned_value else None
    except ValueError as e:
        logging.error(f"Conversion error: {e} for value: {value}")
        return None
# Function to scrape OpenInsider data
def scrape_openinsider(custom_url):
         logging.info(f"Scraping insider data from {custom_url}")

         try:
             response = requests.get(custom_url)
             response.raise_for_status()
             soup = BeautifulSoup(response.text, "html.parser")

             table = soup.find("table", {"class": "tinytable"})
             if not table:
                logging.error(
                "Error: Unable to locate the insider trading table on the page."
            )
                return {}

             insider_data = defaultdict(list)
             rows = table.find("tbody").find_all("tr")

             logging.info(f"Found {len(rows)} rows in the table.")

             for row_index, row in enumerate(rows):
                 cols = row.find_all("td")

                 if len(cols) < 17:
                    logging.warning(
                      f"Row {row_index + 1} skipped: Found {len(cols)} columns. Data: {[col.text.strip() for col in cols]}"
                     )
                    continue

                 try:
                        insider_data_dict = {
                        "filing_date": cols[1].text.strip(),
                        "trade_date": cols[2].text.strip(),
                        "ticker": cols[3].text.strip(),
                        "company_name": cols[4].text.strip(),
                        "insider_name": cols[5].text.strip(),
                        "title": cols[6].text.strip(),
                        "trade_type": cols[7].text.strip(),
                        "price": cols[8].text.strip(),
                        "qty": cols[9].text.strip(),
                        "owned": cols[10].text.strip(),
                        "own_change": cols[11].text.strip(),
                        "total_value": cols[12].text.strip(),
                        }

                       # Log parsed data for debugging
                        logging.debug(
                        f"Parsed data for row {row_index + 1}: {insider_data_dict}"
                        )

                        # Use clean_and_convert to clean and convert the values
                        insider_data_dict["price"] = clean_and_convert(
                        insider_data_dict["price"], "float"
                        )
                        insider_data_dict["qty"] = clean_and_convert(
                    insider_data_dict["qty"], "int"
                  )
                        insider_data_dict["own_change"] = clean_and_convert(
                     insider_data_dict["own_change"], "float"
                      )
                        insider_data_dict["total_value"] = clean_and_convert(
                     insider_data_dict["total_value"], "float"
                      )

                        if (
                            insider_data_dict["price"] is not None
                            and insider_data_dict["qty"] is not None
                            and insider_data_dict["own_change"] is not None
                            and insider_data_dict["total_value"] is not None
                             ):
                            insider_data[insider_data_dict["ticker"]].append(insider_data_dict)
                            logging.info(
                            f"Stock {insider_data_dict['ticker']} added successfully."
                             )
                        else:
                            logging.warning(
                            f"Row {row_index + 1} skipped: Missing critical data."
                             )

                 except (ValueError, TypeError) as e:
                         logging.error(
                          f"Error converting data for {insider_data_dict.get('ticker', 'unknown')}: {e}"
                             )
                 continue

             logging.info(f"Scraped {len(insider_data)} stocks from insider data")
             return insider_data

         except requests.RequestException as e:
           logging.error(f"Error fetching insider data: {e}")
           return {}

def get_insider():
    connection = connectDB.create_connection()
    cursor = connection.cursor()
    insider_data = defaultdict(list)
    try: 
        cursor.execute("SELECT * From asl.openinsider")
        rows = cursor.fetchall()
        logging.info(f"Found {len(rows)} rows in the table.")
        
        for rows_index, row in enumerate(rows):
            insider_data_dict = {
                    "filing_date": row[0],
                    "trade_date": row[1],
                    "ticker": row[2],
                    "company_name":row[3],
                    "insider_name":row[4],
                    "title": row[5],
                    "trade_type": row[6],
                    "price": row[7],
                    "qty": row[8],
                    "owned": row[9],
                    "own_change": row[10],
                    "total_value": row[11]
                 }
            
            
            insider_data[insider_data_dict["ticker"]].append(insider_data_dict)
            logging.info(f"{insider_data_dict["ticker"]} added successfully. ")
        return insider_data     
    except Exception as e:
        logging.error(f"Error get_insider : {e}")
    finally:
        cursor.close()
        connection.close()
        
def record_trade(trade_type,ticker,quantity,price):
    trade = {
        "type":trade_type,
        "ticker": ticker,
        "quantity": quantity,
        "price":price,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

    }
    #Append the trade to the trade history in a thread-safe manner
    with lock:
        trade_history.append(trade)
    logging.info(
        f" Recorded trade : {trade_type} {quantity} shares of {ticker} at ${price} "
    )    

class TradingBot:
    def __init__(self) :
        self.api = "";  # set Api
        self.investor = Investor(
            app_id = APP_ID,
            app_secret = APP_SECRET,
            broker_id=BROKER_ID,
            app_code= APP_CODE,
            is_auto_queue=IS_AUTO_QUEUE
        )
        self.budget = self.get_bugget()
        self.original_budget = self.budget # save original budget
        self.positions ={}
        self.is_running = False
        pass
    def get_bugget(self):

        try:
            #account = self.invertor.Derivatives(account_no=ACCOUNT_NO_D)
            account = self.investor.Equity(ACOUNT_NO_E)
            account_info = account.get_account_info()
            cash_balance =float(account_info["cashBalance"])
            logging.info(f"Current balance: ${cash_balance}")
            return  cash_balance  
        except Exception as e:
            logging.error(f"Error fetch SETTRADE Account balance: {e}")    
    def buy_stock(self,ticker,price,pin,max_position_size=0.6):
        if ticker in self.positions:
            logging.info(f"Already holding position in {ticker}, skipping buy.")
            return
        #max_spend = self.budget * max_position_size
        max_spend = self.budget
        buying_power = max_spend /price
        quantity = int(buying_power)

        logging.info(f"Attemp to buy {quantity} shares of {ticker} at {price} ")
        logging.info(f"Budget before trade: ${self.budget}, Max Spend :${max_spend}")
         # Settrade Buy
        equity = self.investor.Equity(ACOUNT_NO_E)
        if quantity > 0:
            try:
                #self.api.submit_order(
                #    symbol=ticker,
                #    qty=quantity,
                #    side="buy",
                #    type="market",
                #    time_in_force="gtc",
                #)
                place_order = equity.place_order(
                    side="Buy",
                    symbol=ticker,
                    trustee_id_type="Local",
                    volume= quantity,
                    qty_open=0,
                    price=price,
                    price_type="Limit",
                    validity_type="Day",
                    valid_till_date=datetime.now().strftime("%Y-%m-%d"),  # '2024-11-11',
                    bypass_warning=False,
                    pin=pin
                )

                with lock:
                    self.positions[ticker] = {
                        "quantity": quantity,
                        "buy_price":price,
                        "highest_price":price,
                    }
                    self.budget -= quantity * price
                logging.info(f"Bought { quantity}  shares of {ticker} at {price}")
                record_trade("buy",ticker,quantity,price)

            except Exception as e:
                logging.error(f"Error buying {ticker} : {e} ")
    def sell_stock(self,ticker,price,pin):
        if ticker in self.positions:
            #Settrade Sell
            equity = self.investor.Equity(ACOUNT_NO_E)
            quantity = self.positions[ticker]["quantity"]
            try:
                place_order = equity.place_order(
                    side="Sell",
                    symbol=ticker,
                    trustee_id_type="Local",
                    volume= quantity,
                    qty_open=0,
                    price=price,
                    price_type="Limit",
                    valid_till_date="Day",
                    bypass_warning=False,
                    validity_type=datetime.now().strftime("%Y-%m-%d"),  # '2024-11-11'
                    pin=pin
                )
                logging.info(f"Sold {quantity} shares of {ticker} ")
                with lock:
                    self.budget += quantity * self.get_current_price(ticker)
                    record_trade(
                        "sell",ticker,quantity,self.get_current_price(ticker)
                    )
                    del self.positions[ticker]
            except Exception as e:
                logging.error(f"Error selling {ticker} :{e}")    
    def monitor_price(
      self,gain_threshold=GAIN_THRESHOLD,drop_threshold=DROP_THRESHOLD      
    ):            
        #TODO Get/Set  User PIN
        pin="000000"
        while self.positions and self.is_running:
            if self.is_market_open():
                for ticket,info in self.positions.items():
                    current_price = self.get_current_price(ticket)
                    buy_price = info["buy_price"]
                    highest_price = info.get("highest_price",buy_price)
                    
                    gain =(current_price -buy_price) / buy_price *100

                    if current_price >  highest_price:
                        with lock:
                            self.positions[ticket]["highest_price"] = current_price
                        logging.info(f"{ticket} reach a new high price of { current_price}")

                    if gain >= gain_threshold:
                        logging.info(f"Stock {ticket} reach a {gain_threshold} % gain")
                        drop = (highest_price - current_price) / highest_price * 100
                        if drop >= drop_threshold:
                            logging.info(f"Stock {ticket} dropped by {drop_threshold}% form its peak")
                            self.sell_stock(ticket,current_price,pin)
                else:
                    logging.info("Market is clossed, skipping monitering.")
                time.sleep(1) # Monitor every 60 seconds                


    def get_current_price(self,ticker):
               
        try:
            client = self.investor
            market = client.MarketData()
            res = market.get_candlestick(
                symbol=ticker,
                interval="1d",
                limit=1,
                normalized=True,
            )
           
            return  sum(res["close"]) #bar.close
        except Exception as e:
            logging.error(f"Error fetching current price for {ticker}: {e}  ")
            return 0
    def filter_significant_transaction(
            self,
            insider_data,
            min_value=MIN_VALUE,
            min_insiders=MIN_INSIDERS,
            min_own_change=5,
    ):
        significant_stocks = []
        # List to temporarily hold stocks that meet value criteria but not own_change
        lower_own_change_stocks = []

        for ticker,transactions in insider_data.items():
            total_value = sum(item["total_value"] for item in transactions)
            unique_insiders = len(set(item["insider_name"] for item in transactions))
            avg_own_change =(
               sum( item["own_change"] for item in transactions) /len(transactions)
               if len(transactions) > 0
               else 0
            )

            # log why certain stocks are not passing filters
            if total_value < min_value:
                logging.info(f"Stocks {ticker}  excluded for low total value: {total_value}" )
                continue
            if unique_insiders < min_insiders:
                logging.info(f"Stock {ticker} excluded for low unique insider : {unique_insiders} ")
                continue
            if avg_own_change < min_own_change:
                #if the stock has high valuw but lower ownership change, hold it for secondary consideration
                lower_own_change_stocks.append({
                    'ticker' :ticker,
                    'total_value':total_value,
                    'avg_own_Change':avg_own_change,
                    'unique_insiders': unique_insiders
                })   
                logging.info(f"Stock {ticker} has hig total value but lower onwership change: { avg_own_change} % " )
                continue
                # if both value and ownership change pass, add full stock data to significant_stock
            significant_stocks.append({
                    'ticker' :ticker,
                    'total_value':total_value,
                    'avg_own_Change':avg_own_change,
                    'unique_insiders': unique_insiders
                })
            logging.info(f"Stock {ticker} pass filters : Total value: {total_value} , Unique insiders: {unique_insiders} ,Avg Own: {avg_own_change} % ")

          #if no stocks met both conditions , prioritize the ones with high value  , even if own_change is lower
        if not significant_stocks and lower_own_change_stocks:
            #sort lower-owner-chnage stocks by total value in descening order
            lower_own_change_stocks.sort(key=lambda x:x['total_value'],reverse=True)
            top_stock = lower_own_change_stocks[0]
            significant_stocks.append(top_stock)
            logging.info(f"Prioritizing stock {top_stock['ticker']} based on high total value despite lower ownership change: {top_stock['avg_own_change']}% ")

        return significant_stocks

    def run_trading_cycle(
            self,insider_data,gain_threshold=GAIN_THRESHOLD,drop_threshold=DROP_THRESHOLD
        ):
            #TODO  Store user PIN
            pin ="000000"  
            self.is_running = True
            stop_buying = False # Flag stop buying stocks when funds are low
            while self.is_running:
                if not stop_buying:
                    significant_stocks = self.filter_significant_transaction(
                        insider_data,
                        min_value =MIN_VALUE,
                        min_insiders =MIN_INSIDERS,
                        min_own_change=MIN_OWN_CHANGE,
                    )

                    if not significant_stocks:
                        logging.info(
                            " No significant stocks found in this cycle ,Skipping tradding. ")
                        time.sleep(300) # wait for 5 minutes before repeating the cycle
                        continue

                     # Sort stocks based on total_value (or any priority metric) to try higher-priority ones first
                    significant_stocks.sort(key=lambda t: t['total_value'], reverse=True)

                     # Try to bu stocks dynamically based on the available budget
                    for stock in significant_stocks:
                        ticker = stock['ticker']    # Extract ticker form the stock dictionary
                        price = self.get_current_price(ticker)
                        if price > 0 and   self.budget > price:
                        # Dynamically adjust the buying power for each stock based on the remaining budget
                           max_spend =  self.budget # self.budget * 0.2 # 20 % of the remaing budget can be spent on each stock
                           buying_power = min(max_spend,self.budget) /price
                           quantity = int(buying_power)

                           if quantity > 0:
                               self.buy_stock(ticker,price,pin)
                           else:
                               logging.info(f"Insufficient funds to buy {ticker} at {price} ")
                        else:
                            logging.info(f"Skipping stock {ticker} due to insufficient budget or price issue.")

                    #if budget falls below 15 % of the original budget, stop further purchases
                    if self.budget < self.original_budget * 0.15:
                        logging.info(f" Bugget too low to continue buying. Stopping purchases.")
                        stop_buying = True
                # Monitor prices after attemping to buy or if buying has stop
                self.monitor_prices(gain_threshold=gain_threshold,drop_threshold=drop_threshold)   

                 # Check if budget has returned to the original budget after selling stocks
                current_budget = self.get_budget()
                if current_budget >= self.original_budget:
                    logging.info(f" Budget restored to original amount. Resuming purchaeses. ")     
                    stop_buying = False # Resume buying if the budget is restored

                logging.info("Completed a trading cyccle, repeateing...")
                time.sleep(300) # wait for 5 minutes before repeating the cycle   
    
    def is_market_open(self):
        try:
            if time.strftime('%H:$M') >='10.00' and time.strftime('%H:%M') <= '12.30':
                clock = True
            elif time.strftime('%H:$M') >='14.30' and time.strftime('%H:%M') <= '16.30' :
                clock = True
            else:
                clock = False    
            #loging
            return clock
        except Exception as e:
            logging.error(f"Error Fetch market open status: {e}")
        return False    

    def stop(self):
         logging.info("Stoping the trading...")
         self.is_running = False
                               