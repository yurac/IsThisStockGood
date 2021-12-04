import random
import src.RuleOneInvestingCalculations as RuleOne
from requests_futures.sessions import FuturesSession
from src.FMP import FMP
from src.MSNMoney import MSNMoney
from src.YahooFinance import YahooFinanceAnalysis
from src.YahooFinance import YahooFinanceQuote
from src.YahooFinance import YahooFinanceQuoteSummary, YahooFinanceQuoteSummaryModule
from threading import Lock

def fetchDataForTickerSymbol(ticker):
  """Fetches and parses all of the financial data for the `ticker`.

    Args:
      ticker: The ticker symbol string.

    Returns:
      Returns a dictionary of all the processed financial data. If
      there's an error, return None.

      Keys include:
        'roic',
        'eps',
        'sales',
        'equity',
        'cash',
        'long_term_debt',
        'free_cash_flow',
        'debt_payoff_time',
        'debt_equity_ratio',
        'ttm_net_income',
        'margin_of_safety_price',
        'current_price'
  """
  if not ticker:
    return None

  data_fetcher = DataFetcher()
  data_fetcher.ticker_symbol = ticker

  # Make all network request asynchronously to build their portion of
  # the json results.
  data_fetcher.fetch_fmp()
  data_fetcher.fetch_pe_ratios()
  data_fetcher.fetch_yahoo_finance_analysis()
  data_fetcher.fetch_yahoo_finance_quote()
  data_fetcher.fetch_yahoo_finance_quote_summary()

  # Wait for each RPC result before proceeding.
  for rpc in data_fetcher.rpcs:
    rpc.result()

  fmp = data_fetcher.fmp
  fmp.analyze()

  pe_ratios = data_fetcher.pe_ratios
  yahoo_finance_analysis = data_fetcher.yahoo_finance_analysis
  yahoo_finance_quote = data_fetcher.yahoo_finance_quote
  margin_of_safety_price, sticker_price = _calculateMarginOfSafetyPrice(fmp, pe_ratios, yahoo_finance_analysis)
  payback_time = _calculatePaybackTime(fmp, yahoo_finance_quote, yahoo_finance_analysis)
  template_values = {
    'ticker' : ticker,
    'name' : yahoo_finance_quote.name if yahoo_finance_quote and yahoo_finance_quote.name else 'null',
    'roic': fmp.roic_averages if fmp.roic_averages else [],
    'eps': fmp.eps_growth_rate_averages if fmp.eps_growth_rate_averages else [],
    'sales': fmp.sales_growth_rate_averages if fmp.sales_growth_rate_averages else [],
    'equity': fmp.equity_growth_rates if fmp.equity_growth_rates else [],
    'cash': fmp.free_cash_flow_growth_rates if fmp.free_cash_flow_growth_rates else [],
    'long_term_debt' : fmp.long_term_debt,
    'free_cash_flow' : fmp.recent_free_cash_flow,
    'debt_payoff_time' : fmp.debt_payoff_time,
    'debt_equity_ratio' : fmp.debt_equity_ratio if fmp.debt_equity_ratio >= 0 else -1,
    'margin_of_safety_price' : margin_of_safety_price if margin_of_safety_price else 'null',
    'current_price' : yahoo_finance_quote.current_price if yahoo_finance_quote and yahoo_finance_quote.current_price else 'null',
    'sticker_price' : sticker_price if sticker_price else 'null',
    'payback_time' : payback_time if payback_time else 'null',
    'average_volume' : yahoo_finance_quote.average_volume if yahoo_finance_quote and yahoo_finance_quote.average_volume else 'null'
  }
  return template_values

def _calculateMarginOfSafetyPrice(fmp, pe_ratios, yahoo_finance_analysis):
  if not yahoo_finance_analysis.five_year_growth_rate or not fmp.equity_growth_rates:
    return None, None
  growth_rate = min(float(yahoo_finance_analysis.five_year_growth_rate),
                    float(fmp.equity_growth_rates[-1]))
  # Divide the growth rate by 100 to convert from percent to decimal.
  growth_rate = growth_rate / 100.0

  if not fmp.ttm_eps or not pe_ratios.pe_low or not pe_ratios.pe_high:
    return None, None
  print("YURI", fmp.ttm_eps, growth_rate, pe_ratios.pe_low, pe_ratios.pe_high)
  margin_of_safety_price, sticker_price = \
      RuleOne.margin_of_safety_price(float(fmp.ttm_eps), growth_rate,
                                     float(pe_ratios.pe_low), float(pe_ratios.pe_high))
  return margin_of_safety_price, sticker_price

def _calculatePaybackTime(fmp, yahoo_finance_quote, yahoo_finance_analysis):
  if not yahoo_finance_analysis.five_year_growth_rate or not fmp.equity_growth_rates:
    return None
  growth_rate = min(float(yahoo_finance_analysis.five_year_growth_rate),
                    float(fmp.equity_growth_rates[-1]))
  # Divide the growth rate by 100 to convert from percent to decimal.
  growth_rate = growth_rate / 100.0

  if not fmp.ttm_net_income or not yahoo_finance_quote.market_cap:
    return None
  payback_time = RuleOne.payback_time(yahoo_finance_quote.market_cap, fmp.ttm_net_income, growth_rate)
  return payback_time


class DataFetcher():
  """A helper class that syncronizes all of the async data fetches."""

  USER_AGENT_LIST = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
  ]

  def __init__(self,):
    self.lock = Lock()
    self.rpcs = []
    self.ticker_symbol = ''
    self.ratios = None
    self.pe_ratios = None
    self.yahoo_finance_analysis = None
    self.yahoo_finance_quote = None
    self.yahoo_finance_quote_summary = None
    self.error = False

  def _create_session(self):
    session = FuturesSession()
    session.headers.update({
      'User-Agent' : random.choice(DataFetcher.USER_AGENT_LIST)
    })
    return session

  def fetch_fmp(self):
    def deco(key, func):
      def f(*args, **kwargs):
        return func(key, *args, **kwargs)
      return f

    self.fmp = FMP(self.ticker_symbol)
    urls = self.fmp.get_urls()
    session = self._create_session()
    for key, url in urls.items():
      rpc = session.get(url, hooks={'response': deco(key, self.parse_fmp)})
      self.rpcs.append(rpc)

  def parse_fmp(self, key, response, *args, **kwargs):
    self.lock.acquire()
    if not self.fmp:
      self.lock.release()
      return
    success = self.fmp.parse(key, response.text)
    if not success:
      self.fmp = None
    self.lock.release()

  def fetch_pe_ratios(self):
    self.pe_ratios = MSNMoney(self.ticker_symbol)
    session = self._create_session()
    rpc = session.get(self.pe_ratios.url, allow_redirects=True, hooks={
       'response': self.parse_pe_ratios,
    })
    self.rpcs.append(rpc)

  # Called asynchronously upon completion of the URL fetch from
  # `fetch_pe_ratios`.
  def parse_pe_ratios(self, response, *args, **kwargs):
    if response.status_code != 200:
      return
    if not self.pe_ratios:
      return
    result = response.text
    success = self.pe_ratios.parse(result)
    if not success:
      self.pe_ratios = None

  def fetch_yahoo_finance_analysis(self):
    self.yahoo_finance_analysis = YahooFinanceAnalysis(self.ticker_symbol)
    session = self._create_session()
    rpc = session.get(self.yahoo_finance_analysis.url, allow_redirects=True, hooks={
       'response': self.parse_yahoo_finance_analysis,
    })
    self.rpcs.append(rpc)

  # Called asynchronously upon completion of the URL fetch from
  # `fetch_yahoo_finance_analysis`.
  def parse_yahoo_finance_analysis(self, response, *args, **kwargs):
    if response.status_code != 200:
      return
    if not self.yahoo_finance_analysis:
      return
    result = response.text
    success = self.yahoo_finance_analysis.parse_analyst_five_year_growth_rate(result)
    if not success:
      self.yahoo_finance_analysis = None

  def fetch_yahoo_finance_quote(self):
    self.yahoo_finance_quote = YahooFinanceQuote(self.ticker_symbol)
    session = self._create_session()
    rpc = session.get(self.yahoo_finance_quote.url, allow_redirects=True, hooks={
       'response': self.parse_yahoo_finance_quote,
    })
    self.rpcs.append(rpc)

  # Called asynchronously upon completion of the URL fetch from
  # `fetch_yahoo_finance_quote`.
  def parse_yahoo_finance_quote(self, response, *args, **kwargs):
    if response.status_code != 200:
      return
    if not self.yahoo_finance_quote:
      return
    result = response.text
    success = self.yahoo_finance_quote.parse_quote(result)
    if not success:
      self.yahoo_finance_quote = None

  def fetch_yahoo_finance_quote_summary(self):
    modules = [YahooFinanceQuoteSummaryModule.assetProfile]
    self.yahoo_finance_quote_summary = YahooFinanceQuoteSummary(self.ticker_symbol, modules)
    session = self._create_session()
    rpc = session.get(self.yahoo_finance_quote_summary.url, allow_redirects=True, hooks={
       'response': self.parse_yahoo_finance_quote_summary,
    })
    self.rpcs.append(rpc)

  # Called asynchronously upon completion of the URL fetch from
  # `fetch_yahoo_finance_quote_summary`.
  def parse_yahoo_finance_quote_summary(self, response, *args, **kwargs):
    if response.status_code != 200:
      return
    if not self.yahoo_finance_quote_summary:
      return
    result = response.text
    success = self.yahoo_finance_quote_summary.parse_modules(result)
    if not success:
      self.yahoo_finance_quote_summary = None
