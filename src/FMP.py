import logging
import traceback
import subprocess
import json

fmp_apikey = None
def get_fmp_apikey():
    global fmp_apikey

    if fmp_apikey is None:
        fmp_apikey = subprocess.check_output("fmp_apikey", shell=True).decode('ascii').strip().split()[0]

    return fmp_apikey

class FMP:
  BASE_URL = "https://financialmodelingprep.com/api/v3/{}/{}?apikey={}"
  PROFILE = "profile"
  INCOME = "income-statement"
  BALANCE = "balance-sheet-statement"
  CASHFLOW = "cash-flow-statement"
  RATIOS = "ratios"

  @classmethod
  def construct_url(cls, url, ticker_symbol,):
    url = FMP.BASE_URL.format(url, ticker_symbol, get_fmp_apikey())
    return url

  def __init__(self, ticker_symbol):
    self.ticker_symbol = ticker_symbol.replace('.', '')
    self.profile_url = FMP.construct_url(FMP.PROFILE, self.ticker_symbol)
    self.income_url = FMP.construct_url(FMP.INCOME, self.ticker_symbol)
    self.balance_url = FMP.construct_url(FMP.BALANCE, self.ticker_symbol)
    self.cashflow_url = FMP.construct_url(FMP.CASHFLOW, self.ticker_symbol)
    self.ratios_url = FMP.construct_url(FMP.RATIOS, self.ticker_symbol)

    self.results = dict()

  def get_urls(self):
    return {FMP.PROFILE: self.profile_url,
            FMP.INCOME: self.income_url,
            FMP.BALANCE: self.balance_url,
            FMP.CASHFLOW: self.cashflow_url,
            FMP.RATIOS: self.ratios_url
            }

  def parse(self, key, data):
    try:
      data = json.loads(data)
      self.results[key] = data
    except Exception as e:
      logging.error(traceback.format_exc())
      return False
    return True
