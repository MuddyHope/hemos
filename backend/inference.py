import numpy as np
import pandas as pd
from collections import deque


class CardiacMonitor:
    WINDOW = 100
    PREDICT_EVERY = 10

    def __init__(self, model, encoder, features):
        self.model    = model
        self.encoder  = encoder
        self.features = features
        self.hr_buffer   = deque(maxlen=self.WINDOW)
        self.temp_buffer = deque(maxlen=self.WINDOW)

        self.last_prediction_time = 0
        self.cached_result = None

    def _slope(self, values):
        arr = np.array(values, dtype=float)
        if len(arr) < 2:
            return 0.0
        x = np.arange(len(arr))
        return round(float(np.polyfit(x, arr, 1)[0]), 4)

    def _pearson(self, hr_vals, temp_vals):
        ha = np.array(hr_vals, dtype=float)
        ta = np.array(temp_vals, dtype=float)
        if ha.std() == 0 or ta.std() == 0:
            return 0.0
        return round(float(np.corrcoef(ha, ta)[0, 1]), 4)

    # 🔥 NEW: Safety + ML hybrid prediction
    def predict(self, hr, temp):

        import time

        self.hr_buffer.append(hr)
        self.temp_buffer.append(temp)

        now = time.time()

        # # ⛔ skip prediction if too soon
        # if now - self.last_prediction_time < self.PREDICT_EVERY:
        #     return self.cached_result or {
        #         "prediction": "Waiting",
        #         "confidence": 0.0
        #     }

        self.last_prediction_time = now
        # ── 1. HARD SAFETY CHECKS ───────────────────────────────
        if temp is not None:
            if temp < 30 or temp > 45:
                return {
                    'hr': hr,
                    'temp': temp,
                    'prediction': 'Sensor Error',
                    'confidence': 100.0,
                    'reason': 'Temperature out of realistic range'
                }

        if hr is not None:
            if hr < 20 or hr > 220:
                return {
                    'hr': hr,
                    'temp': temp,
                    'prediction': 'Sensor Error',
                    'confidence': 100.0,
                    'reason': 'Heart rate out of realistic range'
                }

        # ── 2. ADD TO BUFFERS ──────────────────────────────────
        self.hr_buffer.append(hr)
        self.temp_buffer.append(temp)
        hl, tl = list(self.hr_buffer), list(self.temp_buffer)

        # ── 3. WARM-UP PHASE ───────────────────────────────────
        if len(hl) < 10:
            return {
                'hr': hr,
                'temp': temp,
                'prediction': 'Warming Up',
                'confidence': 0.0,
                'reason': 'Not enough data yet'
            }

        # ── 4. FEATURE ENGINEERING ─────────────────────────────
        hrv             = round(float(np.std(hl)), 4)
        hr_trend        = self._slope(hl)
        temp_trend      = self._slope(tl)
        hr_rolling_mean = round(float(np.mean(hl)), 4)
        bpm_temp_corr   = self._pearson(hl, tl)

        fv = pd.DataFrame([{
            'hr': hr, 'temp': temp, 'hrv': hrv,
            'hr_trend': hr_trend, 'temp_trend': temp_trend,
            'hr_rolling_mean': hr_rolling_mean,
            'bpm_temp_corr': bpm_temp_corr,
        }])[self.features]

        # ── 5. ML PREDICTION ──────────────────────────────────
        pred_enc   = self.model.predict(fv)[0]
        pred_label = self.encoder.inverse_transform([pred_enc])[0]
        confidence = float(self.model.predict_proba(fv)[0].max() * 100)

        # ── 6. PHYSIOLOGICAL OVERRIDES ────────────────────────
        reason = "ML prediction"

        if temp is not None:
            if temp < 35:
                pred_label = "Hypothermia Risk"
                confidence = max(confidence, 90)
                reason = "Low body temperature"
            elif temp > 38:
                pred_label = "Fever / Infection Risk"
                confidence = max(confidence, 90)
                reason = "High body temperature"

        if hr is not None:
            if hr > 120:
                pred_label = "Tachycardia Risk"
                confidence = max(confidence, 90)
                reason = "High heart rate"
            elif hr < 50:
                pred_label = "Bradycardia Risk"
                confidence = max(confidence, 90)
                reason = "Low heart rate"

        # ── 7. LOW CONFIDENCE HANDLING ────────────────────────
        if confidence < 60:
            pred_label = "Uncertain"
            reason = "Low model confidence"

        return {
            'hr': hr,
            'temp': temp,
            'prediction': pred_label,
            'confidence': round(confidence, 1),
            'reason': reason,
            'features': {
                'hrv': hrv,
                'hr_trend': hr_trend,
                'temp_trend': temp_trend,
                'hr_rolling_mean': hr_rolling_mean,
                'bpm_temp_corr': bpm_temp_corr,
            }
        }