def compute_cost(hours: float, people: int, hourly_rate_per_person: float,
                 material_cost: float, equipment_cost: float) -> dict:
    labor_cost = hours * people * hourly_rate_per_person
    total = labor_cost + material_cost + equipment_cost
    return {"labor_cost": labor_cost, "total_cost": total}
