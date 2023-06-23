"""
This file contains the unit tests for the current_prices.py file.
"""
import pytest

from app.ranking_service import get_number_pages, get_limit_per_page


@pytest.mark.parametrize(
    "page, page_size, total_limit, expected_limit",
    [
        (1, 10, 100, 10),
        (2, 10, 100, 10),
        (3, 10, 100, 10),
        (4, 10, 100, 10),
        (5, 10, 100, 10),
        (6, 10, 100, 10),
        (7, 10, 100, 10),
        (8, 10, 100, 5),
        (9, 10, 100, 5),
        (1, 10, 8, 8),
        (2, 10, 8, 0),
        (1, 10, 10, 10),
        (2, 10, 10, 0),
        (1, 10, 0, 0),
        (2, 10, 0, 0)
    ],
)
def test_get_limit_per_page(page, page_size, total_limit, expected_limit):
    limit = get_limit_per_page(
        page=page, page_size=page_size, total_limit=total_limit
    )
    assert limit == expected_limit
