import numpy as np

EPS = 1e-9


class PVPredictor:
    # Predicts the next PV values from a rolling window of the last measurements only

    methods = ["persistence", "average", "taylor1", "taylor2", "smart_persistence"]

    def __init__(
        self,
        method: str = "smart_persistence",
        window: int = 4,                    # Number of past measurements used (4 = one hour at 15 min)
        clear_sky=None                      # Clear-sky PV profile [kW], from the sun's geometry
    ):
        if method not in self.methods:
            raise ValueError(f"Unknown method, choose from {self.methods}")
        if method == "smart_persistence" and clear_sky is None:
            raise ValueError("Smart persistence requires the clear-sky profile")

        self.method = method
        self.window = window
        self.clear_sky = None if clear_sky is None else np.asarray(clear_sky, dtype=float)

    def predict(self, history, horizon):
        # history: measurements up to and including the current step. Returns the next `horizon` values.
        t = len(history) - 1
        past = np.asarray(history[max(0, t - self.window + 1):], dtype=float)
        ahead = np.arange(1, horizon + 1)

        if self.method == "persistence" or len(past) < 2:
            prediction = np.full(horizon, past[-1])

        elif self.method == "average":
            prediction = np.full(horizon, past.mean())

        elif self.method in ("taylor1", "taylor2"):
            # Polynomial fitted on the window (x = 0 at the current step), extrapolated ahead:
            # first order uses the slope, second order adds the curvature
            degree = 1 if self.method == "taylor1" else min(2, len(past) - 1)
            x = np.arange(-len(past) + 1, 1)
            prediction = np.polyval(np.polyfit(x, past, degree), ahead)

        else:
            # Clear-sky index over the window, applied to the clear-sky profile ahead
            sky = self.clear_sky[t - len(past) + 1:t + 1]
            index = past.sum() / sky.sum() if sky.sum() > EPS else 1.0
            prediction = index * self._clear_sky_ahead(t, horizon)

        upper = self._clear_sky_ahead(t, horizon) if self.clear_sky is not None else np.inf
        return np.clip(prediction, 0.0, upper)

    def _clear_sky_ahead(self, t, horizon):
        ahead = self.clear_sky[t + 1:t + 1 + horizon]
        return np.pad(ahead, (0, horizon - len(ahead)))
