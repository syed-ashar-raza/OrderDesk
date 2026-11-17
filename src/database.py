"""Small in-memory database containing fictional orders."""

ORDERS = {
    "A123": {
        "order_id": "A123",
        "customer": "Ali Khan",
        "status": "Shipped",
        "estimated_delivery": "2026-11-20",
    },
    "A124": {
        "order_id": "A124",
        "customer": "Sara Ahmed",
        "status": "Processing",
        "estimated_delivery": "2026-11-22",
    },
    "A125": {
        "order_id": "A125",
        "customer": "Usman Malik",
        "status": "Delivered",
        "estimated_delivery": "2026-11-15",
    },
    "A126": {
        "order_id": "A126",
        "customer": "Fatima Noor",
        "status": "Cancelled",
        "estimated_delivery": None,
    },
    "A127": {
        "order_id": "A127",
        "customer": "Hamza Ali",
        "status": "Out for delivery",
        "estimated_delivery": "2026-11-17",
    },
    "A128": {
        "order_id": "A128",
        "customer": "Ayesha Iqbal",
        "status": "Processing",
        "estimated_delivery": "2026-11-24",
    },
}
