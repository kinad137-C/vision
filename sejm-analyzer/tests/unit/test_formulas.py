"""Tests for formulas module."""

from src import formulas


class TestShapley:
    def test_single_party(self):
        assert formulas.shapley_shubik({"A": 100}, 51) == {"A": 1.0}

    def test_equal_parties(self):
        result = formulas.shapley_shubik({"A": 50, "B": 50}, 51)
        assert result["A"] == result["B"] == 0.5

    def test_sum_to_one(self):
        result = formulas.shapley_shubik({"A": 40, "B": 30, "C": 30}, 51)
        assert abs(sum(result.values()) - 1.0) < 0.001


class TestBanzhaf:
    def test_single_party(self):
        assert formulas.banzhaf({"A": 100}, 51) == {"A": 1.0}

    def test_sum_to_one(self):
        result = formulas.banzhaf({"A": 40, "B": 30, "C": 30}, 51)
        assert abs(sum(result.values()) - 1.0) < 0.001


class TestCoalitions:
    def test_finds_coalitions(self):
        result = formulas.min_coalitions({"A": 40, "B": 30, "C": 30}, 51)
        assert len(result) > 0
        assert all(c[1] >= 51 for c in result)


class TestRice:
    def test_unanimous_yes(self):
        assert formulas.rice_index(100, 0) == 1.0

    def test_unanimous_no(self):
        assert formulas.rice_index(0, 100) == 1.0

    def test_split(self):
        assert formulas.rice_index(50, 50) == 0.0

    def test_skewed(self):
        assert formulas.rice_index(75, 25) == 0.5


class TestMarkov:
    def test_consistent_yes(self):
        trans = formulas.transition_matrix(["YES"] * 10)
        assert trans["yes_to_yes"] == 1.0
        assert trans["yes_to_no"] == 0.0

    def test_alternating(self):
        trans = formulas.transition_matrix(["YES", "NO"] * 5)
        assert trans["yes_to_no"] == 1.0
        assert trans["no_to_yes"] == 1.0

    def test_momentum(self):
        trans = {"yes_to_yes": 0.8, "no_to_no": 0.8, "yes_to_no": 0.2, "no_to_yes": 0.2}
        assert formulas.momentum(trans) == 0.8

    def test_volatility(self):
        trans = {"yes_to_yes": 0.2, "no_to_no": 0.2, "yes_to_no": 0.8, "no_to_yes": 0.8}
        assert formulas.volatility(trans) == 0.8


class TestAgreement:
    def test_perfect(self):
        assert formulas.agreement_rate([True, True], [True, True]) == 100.0

    def test_none(self):
        assert formulas.agreement_rate([True, True], [False, False]) == 0.0

    def test_half(self):
        assert formulas.agreement_rate([True, False], [True, True]) == 50.0
