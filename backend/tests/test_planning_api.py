import xmlrpc.client

from app.api.planning import ODOO_ERRORS
from app.services.odoo_client import OdooAuthError


def test_odoo_errors_covers_auth_failure():
    assert isinstance(OdooAuthError("bad creds"), ODOO_ERRORS)


def test_odoo_errors_covers_network_failure():
    # e.g. DNS resolution failure talking to a customer's Odoo instance
    assert isinstance(OSError("Name or service not known"), ODOO_ERRORS)


def test_odoo_errors_covers_xmlrpc_fault():
    assert isinstance(xmlrpc.client.Fault(1, "boom"), ODOO_ERRORS)
