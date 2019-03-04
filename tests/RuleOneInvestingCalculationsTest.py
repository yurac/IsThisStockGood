"""Tests for the app/RuleOneInvestingCalculations.py functions."""


import os
import sys
import unittest

app_path = os.path.join(os.path.dirname(__file__), "..", 'app')
sys.path.append(app_path)

import RuleOneInvestingCalculations as RuleOne

class RuleOneInvestingCalculationsTest(unittest.TestCase):

  def test_compound_annual_growth_rate(self):
    growth_rate = RuleOne.compound_annual_growth_rate(2805000, 108957000, 8)
    self.assertEqual(growth_rate, 57.57)

  def test_slope_of_best_fit_line_for_data(self):
    data = [1.3, 2.5, 3.5, 8.5]
    slope = RuleOne.slope_of_best_fit_line_for_data(data)
    self.assertEqual(slope, 2.26)

  def test_max_position_size(self):
    share_price = 50.25
    trade_volume = 2134099
    max_position,max_shares = RuleOne.max_position_size(share_price,
                                                        trade_volume)
    self.assertEqual(max_position, 1072335)
    self.assertEqual(max_shares, 21340)

  def test_rule_one_margin_of_safety_price(self):
    pass

  def test_calculate_future_eps(self):
    pass

  def test_calculate_future_pe(self):
    pass

  def test_calculate_estimated_future_price(self):
    future_price = RuleOne.calculate_estimated_future_price(1.25, 3)
    self.assertEqual(future_price, 3.75)

  def test_calculate_sticker_price(self):
    pass

  def test_calculate_margin_of_safety(self):
    default_margin_of_safety = RuleOne.calculate_margin_of_safety(100)
    self.assertEqual(default_margin_of_safety, 50)

    smaller_margin_of_safety = \
        RuleOne.calculate_margin_of_safety(100, margin_of_safety=0.25)
    self.assertEqual(smaller_margin_of_safety, 75)