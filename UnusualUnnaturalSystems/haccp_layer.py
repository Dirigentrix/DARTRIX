class HACCPLayer:
    """
    HACCP (Hazard Analysis and Critical Control Points) validation layer.
    Manages CCP (Critical Control Points) limits and validation logic.
    """
    def __init__(self):
        # Default limits for a food/production environment
        self.ccp_limits = {
            "refrigerator_temp": {"min": 0, "max": 5.0, "unit": "C"},
            "cooking_temp": {"min": 75.0, "max": 100.0, "unit": "C"},
            "ph_level": {"min": 4.0, "max": 4.6, "unit": "pH"}
        }

    def validate_reading(self, point_id, value):
        """
        Validates a specific sensor reading against CCP limits.
        Returns (is_valid, message).
        """
        if point_id not in self.ccp_limits:
            return True, f"Point {point_id} is not a registered CCP. Reading accepted."
        
        limits = self.ccp_limits[point_id]
        if value < limits["min"]:
            return False, f"CRITICAL: {point_id} below limit ({value} < {limits['min']}{limits['unit']})"
        if value > limits["max"]:
            return False, f"CRITICAL: {point_id} above limit ({value} > {limits['max']}{limits['unit']})"
        
        return True, f"{point_id} reading {value}{limits['unit']} is within safe limits."

    def get_ccp_status(self):
        return self.ccp_limits
