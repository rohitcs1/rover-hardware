class ObstacleAvoidance:
    """
    Classifies obstacles according to measured distance.

    > 50 cm: CLEAR
    20-50 cm: CAUTION
    < 20 cm: DANGER
    """

    def __init__(
        self,
        caution_distance=50.0,
        danger_distance=20.0,
    ):
        self.caution_distance = caution_distance
        self.danger_distance = danger_distance

    def analyze_distance(self, distance_cm):
        if distance_cm is None:
            return {
                "obstacleDetected": None,
                "obstacleLevel": "UNKNOWN",
                "obstacleMessage": "Distance unavailable",
                "buzzerPattern": "OFF",
            }

        if distance_cm < self.danger_distance:
            return {
                "obstacleDetected": True,
                "obstacleLevel": "DANGER",
                "obstacleMessage": (
                    f"Obstacle critically close: {distance_cm} cm"
                ),
                "buzzerPattern": "FAST",
            }

        if distance_cm <= self.caution_distance:
            return {
                "obstacleDetected": True,
                "obstacleLevel": "CAUTION",
                "obstacleMessage": (
                    f"Obstacle nearby: {distance_cm} cm"
                ),
                "buzzerPattern": "SLOW",
            }

        return {
            "obstacleDetected": False,
            "obstacleLevel": "CLEAR",
            "obstacleMessage": "Path clear",
            "buzzerPattern": "OFF",
        }
