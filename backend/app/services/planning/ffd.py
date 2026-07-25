from dataclasses import dataclass, field


@dataclass
class Address:
    street1: str = ""
    street2: str = ""
    city: str = ""
    country: str = ""
    zip: str = ""


@dataclass
class Order:
    picking_id: int
    weight_kg: float
    volume_m3: float
    lat: float
    lon: float
    customer_name: str = ""
    items_summary: str = ""
    address: Address = field(default_factory=Address)


@dataclass
class Vehicle:
    vehicle_id: int
    capacity_weight_kg: float
    capacity_volume_m3: float


@dataclass
class VehicleAssignment:
    vehicle_id: int
    assigned_orders: list[Order] = field(default_factory=list)
    total_weight_kg: float = 0.0
    total_volume_m3: float = 0.0
    capacity_weight_kg: float = 0.0
    capacity_volume_m3: float = 0.0

    def remaining_weight_kg(self) -> float:
        return self.capacity_weight_kg - self.total_weight_kg

    def remaining_volume_m3(self) -> float:
        return self.capacity_volume_m3 - self.total_volume_m3


def assign_orders_ffd(
    orders: list[Order], vehicles: list[Vehicle]
) -> tuple[list[VehicleAssignment], list[Order]]:
    """First Fit Decreasing bin-packing.

    Orders are sorted by weight descending, then each is placed into the
    first vehicle with enough remaining weight and volume capacity. No new
    vehicles are created — orders that don't fit anywhere come back as
    `unassigned`. No zone/territory logic is applied (see DECISIONS.md).
    """
    assignments = [
        VehicleAssignment(
            vehicle_id=v.vehicle_id,
            capacity_weight_kg=v.capacity_weight_kg,
            capacity_volume_m3=v.capacity_volume_m3,
        )
        for v in vehicles
    ]

    sorted_orders = sorted(orders, key=lambda o: o.weight_kg, reverse=True)
    unassigned: list[Order] = []

    for order in sorted_orders:
        placed = False
        for assignment in assignments:
            if (
                order.weight_kg <= assignment.remaining_weight_kg()
                and order.volume_m3 <= assignment.remaining_volume_m3()
            ):
                assignment.assigned_orders.append(order)
                assignment.total_weight_kg += order.weight_kg
                assignment.total_volume_m3 += order.volume_m3
                placed = True
                break
        if not placed:
            unassigned.append(order)

    return assignments, unassigned
