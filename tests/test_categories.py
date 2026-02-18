from src.domain.value_objects.categories import category_matches, resolve_category_filter, resolve_category_filters


def test_resolve_category_filter_all_variants():
    assert resolve_category_filter("Todas") is None
    assert resolve_category_filter("  ") is None
    assert resolve_category_filter("all") is None


def test_resolve_category_filter_aliases():
    assert resolve_category_filter("vestuario") == "calcados roupas e bolsas"
    assert resolve_category_filter("Eletronicos") == "eletronicos"


def test_resolve_category_filters_multiple_values():
    values = resolve_category_filters("eletronicos, vestuario ; casa e decoracao")
    assert values == ["eletronicos", "calcados roupas e bolsas", "casa moveis e decoracao"]


def test_category_matches_normalized():
    assert category_matches("vestuario", "Calcados, Roupas e Bolsas") is True
    assert category_matches("eletronicos", "Eletronicos, Audio e Video") is True
    assert category_matches("eletronicos", "Calcados, Roupas e Bolsas") is False


def test_category_matches_when_any_filter_matches():
    assert category_matches(["eletronicos", "vestuario"], "Calcados, Roupas e Bolsas") is True
    assert category_matches(["eletronicos", "vestuario"], "Bebes") is False
