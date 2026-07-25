from app.services.planning.ffd import Order, Vehicle, assign_orders_ffd


def _order(picking_id: int, weight_kg: float, volume_m3: float = 1.0) -> Order:
    return Order(picking_id=picking_id, weight_kg=weight_kg, volume_m3=volume_m3, lat=0.0, lon=0.0)


def _vehicle(
    vehicle_id: int, capacity_weight_kg: float, capacity_volume_m3: float = 100.0
) -> Vehicle:
    return Vehicle(
        vehicle_id=vehicle_id,
        capacity_weight_kg=capacity_weight_kg,
        capacity_volume_m3=capacity_volume_m3,
    )


def test_assigns_orders_within_capacity():
    orders = [_order(1, 300), _order(2, 200), _order(3, 100)]
    vehicles = [_vehicle(10, capacity_weight_kg=500)]

    assignments, unassigned = assign_orders_ffd(orders, vehicles)

    # 300 + 200 exactly fill the vehicle; 100 has no remaining capacity left
    assert assignments[0].total_weight_kg == 500
    assert {o.picking_id for o in assignments[0].assigned_orders} == {1, 2}
    assert [o.picking_id for o in unassigned] == [3]


def test_orders_sorted_heaviest_first_and_no_overflow():
    orders = [_order(1, 50), _order(2, 400), _order(3, 100)]
    vehicles = [_vehicle(10, capacity_weight_kg=400)]

    assignments, unassigned = assign_orders_ffd(orders, vehicles)

    # heaviest order (400kg) placed first, fills the vehicle exactly
    assert [o.picking_id for o in assignments[0].assigned_orders] == [2]
    assert {o.picking_id for o in unassigned} == {1, 3}


def test_unassigned_when_no_vehicle_has_capacity():
    orders = [_order(1, 1000)]
    vehicles = [_vehicle(10, capacity_weight_kg=500)]

    assignments, unassigned = assign_orders_ffd(orders, vehicles)

    assert assignments[0].assigned_orders == []
    assert [o.picking_id for o in unassigned] == [1]


def test_no_zone_bias_orders_spread_by_capacity_only():
    orders = [_order(1, 300), _order(2, 300)]
    vehicles = [_vehicle(10, capacity_weight_kg=300), _vehicle(20, capacity_weight_kg=300)]

    assignments, unassigned = assign_orders_ffd(orders, vehicles)

    assert unassigned == []
    assert len(assignments[0].assigned_orders) == 1
    assert len(assignments[1].assigned_orders) == 1
