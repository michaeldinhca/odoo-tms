from app.services.fleet_lookup import fetch_employees, fetch_fleet_vehicles


class FakeOdooClient:
    def __init__(self, data: dict[str, list[dict]], missing_models: set[str] | None = None):
        self._data = data
        self._missing_models = missing_models or set()

    def search_read(self, model, domain=None, fields=None, company_id=None):
        return self._data.get(model, [])

    def model_exists(self, model):
        return model not in self._missing_models


def test_fetch_fleet_vehicles_maps_native_fields():
    client = FakeOdooClient(
        {"fleet.vehicle": [{"id": 1, "name": "Truck 1", "license_plate": "ABC-123"}]}
    )

    available, vehicles = fetch_fleet_vehicles(client)

    assert available is True
    assert vehicles == [{"id": 1, "name": "Truck 1", "license_plate": "ABC-123"}]


def test_fetch_fleet_vehicles_handles_absent_fleet_module_gracefully():
    client = FakeOdooClient({}, missing_models={"fleet.vehicle"})

    available, vehicles = fetch_fleet_vehicles(client)

    assert available is False
    assert vehicles == []


def test_fetch_employees_maps_native_fields():
    client = FakeOdooClient(
        {
            "hr.employee": [
                {"id": 5, "name": "Jane Doe", "work_phone": "555-1234", "mobile_phone": ""}
            ]
        }
    )

    available, employees = fetch_employees(client)

    assert available is True
    assert employees == [
        {"id": 5, "name": "Jane Doe", "work_phone": "555-1234", "mobile_phone": ""}
    ]


def test_fetch_employees_handles_absent_hr_module_gracefully():
    client = FakeOdooClient({}, missing_models={"hr.employee"})

    available, employees = fetch_employees(client)

    assert available is False
    assert employees == []
