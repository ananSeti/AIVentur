from trading_bot import TradingBot,trade_history ,lock
import logging
import connectDB

#initialize the tradeing bot
bot = TradingBot()

#current price
#current_price = bot.get_current_price("BBL")
testconnection  =connectDB.get_insider()
