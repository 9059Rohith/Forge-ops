from unittest.mock import Mock

import pytest

from checkout import checkout


def test_checkout_returns_gateway_result():
    client = Mock()
    client.charge.return_value = {"status": "paid"}

    assert checkout(client, "order-1") == {"status": "paid"}


def test_checkout_preserves_order_identifier():
    client = Mock()
    client.charge.return_value = {"status": "paid"}

    checkout(client, "order-42")

    client.charge.assert_called_once_with("order-42")


def test_checkout_propagates_gateway_errors():
    client = Mock()
    client.charge.side_effect = RuntimeError("gateway unavailable")

    with pytest.raises(RuntimeError, match="gateway unavailable"):
        checkout(client, "order-1")

