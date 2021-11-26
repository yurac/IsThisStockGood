import logging
import traceback
import subprocess
import json
import src.RuleOneInvestingCalculations as RuleOne

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
    self.ticker_symbol = ticker_symbol
    self.profile_url = FMP.construct_url(FMP.PROFILE, self.ticker_symbol)
    self.income_url = FMP.construct_url(FMP.INCOME, self.ticker_symbol)
    self.balance_url = FMP.construct_url(FMP.BALANCE, self.ticker_symbol)
    self.cashflow_url = FMP.construct_url(FMP.CASHFLOW, self.ticker_symbol)
    self.ratios_url = FMP.construct_url(FMP.RATIOS, self.ticker_symbol)

    self.roic = []
    self.roic_averages = []
    self.equity = []
    self.equity_growth_rates = []
    self.free_cash_flow = []
    self.free_cash_flow_growth_rates = []
    self.sales_growth_rate_averages = []
    self.eps_growth_rate_averages = []
    self.ttm_eps = 0
    self.ttm_net_income = 0
    # The longTermDebt value varies across sites but totalCurrentLiabilities and totalNonCurrentLiabilities are fixed.
    # Maybe use totalLiabilities - totalCurrentLiabilities to be more conservative and portable
    self.long_term_debt = 0
    # Last free cash flow from operating activities not including financing and capex
    self.recent_free_cash_flow = 0
    self.debt_payoff_time = 0
    self.debt_equity_ratio = -1

    self.results = dict()

  def get_urls(self):
    return {FMP.PROFILE: self.profile_url,
            FMP.INCOME: self.income_url,
            FMP.BALANCE: self.balance_url,
            FMP.CASHFLOW: self.cashflow_url,
            FMP.RATIOS: self.ratios_url
            }

  def get_roic(self, balance_income):
      balance, income = balance_income
      # This formula is used by FMP. See Damodaran paper for more elaborate calculation
      return 100 * income["operatingIncome"] / (balance["totalAssets"] - balance["totalCurrentLiabilities"])

  def analyze(self):
      self.long_term_debt = self.results[FMP.BALANCE][0]["longTermDebt"]
      self.free_cash_flow = list(reversed(list(map(lambda cashflow: cashflow["netCashProvidedByOperatingActivities"], self.results[FMP.CASHFLOW]))))
      self.recent_free_cash_flow = self.free_cash_flow[-1] 
      self.free_cash_flow_growth_rates = RuleOne.get_growth_rates(self.free_cash_flow)
      self.debt_payoff_time = self.long_term_debt / self.recent_free_cash_flow
      self.equity = list(reversed(list(map(lambda balance: balance["totalStockholdersEquity"], self.results[FMP.BALANCE]))))
      self.equity_growth_rates = RuleOne.get_growth_rates(self.equity)
      total_liabilities = self.results[FMP.BALANCE][0]["totalLiabilities"]
      self.debt_equity_ratio = total_liabilities / self.equity[-1]
      eps = list(reversed(list(map(lambda income: income["epsdiluted"], self.results[FMP.INCOME]))))
      self.eps_growth_rate_averages = RuleOne.get_growth_rates(eps)
      self.ttm_eps = eps[-1]
      net_income = list(reversed(list(map(lambda income: income["netIncome"], self.results[FMP.INCOME]))))
      self.ttm_net_income = net_income[-1]
      self.roic = list(reversed(list(map(self.get_roic, zip(self.results[FMP.BALANCE], self.results[FMP.INCOME])))))
      self.roic_averages = RuleOne.get_averages(self.roic)
      sales = list(reversed(list(map(lambda income: income["revenue"], self.results[FMP.INCOME]))))
      self.sales_growth_rate_averages = RuleOne.get_growth_rates(sales)

  def parse(self, key, data):
    try:
      data = json.loads(data)
      self.results[key] = data
    except Exception as e:
      logging.error(traceback.format_exc())
      return False
    return True
