from app.services.planning.ffd import Order
from app.services.planning.filo import sequence_filo


def _order(picking_id: int) -> Order:
    return Order(picking_id=picking_id, weight_kg=1.0, volume_m3=1.0, lat=0.0, lon=0.0)


def test_last_loaded_delivered_first():
    load_order = [_order(1), _order(2), _order(3)]

    delivery_order = sequence_filo(load_order)

    assert [o.picking_id for o in delivery_order] == [3, 2, 1]


def test_single_order_sequence_unchanged():
    load_order = [_order(1)]
    assert [o.picking_id for o in sequence_filo(load_order)] == [1]


def test_empty_sequence():
    assert sequence_filo([]) == []


def test_does_not_mutate_input():
    load_order = [_order(1), _order(2)]
    original_ids = [o.picking_id for o in load_order]

    sequence_filo(load_order)

    assert [o.picking_id for o in load_order] == original_ids
