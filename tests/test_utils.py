import app.main as main


def test_to_float_ok():
    assert main._to_float("1.23") == 1.23
    assert main._to_float(5) == 5.0


def test_to_float_invalid():
    assert main._to_float("abc") is None
    assert main._to_float(None) is None


def test_symbols_from_config_filters_supported_and_excludes_base():
    supported = {"USD": "US Dollar", "EUR": "Euro", "JPY": "Yen"}
    # CURRENCIES contiene USD y otros; _symbols_from_config debe excluir BASE_CCY y filtrar por supported
    symbols = main._symbols_from_config(supported)
    assert "USD" not in symbols
    # Al menos valida que los soportados típicos aparezcan si están configurados
    # (si tu lista CURRENCIES cambia, este assert puede ajustarse)
    assert all(s in supported for s in symbols)


def test_compute_cross_usd_to_eur():
    rates = {"EUR": 0.9}
    assert main._compute_cross(10, "USD", "EUR", rates) == 9.0


def test_compute_cross_eur_to_usd():
    rates = {"EUR": 0.8}
    assert main._compute_cross(8, "EUR", "USD", rates) == 10.0


def test_compute_cross_cross_pair():
    rates = {"EUR": 0.8, "JPY": 160.0}
    # 8 EUR -> USD = 8 / 0.8 = 10 USD; USD -> JPY = 10*160 = 1600
    assert main._compute_cross(8, "EUR", "JPY", rates) == 1600.0


def test_compute_cross_missing_rate_returns_none():
    rates = {"EUR": 0.8}
    assert main._compute_cross(10, "USD", "JPY", rates) is None
