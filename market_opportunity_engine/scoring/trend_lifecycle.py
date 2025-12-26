import numpy as np

def trend_features(series):
    y = np.array(series, dtype=float)
    if len(y) < 4:
        return None

    x = np.arange(len(y))
    slope = np.polyfit(x, y, 1)[0]
    diffs = np.diff(y)
    accel = diffs[-1] - diffs[-2] if len(diffs) >= 2 else 0
    volatility = np.std(diffs)

    return slope, accel, volatility

def classify_stage(series):
    f = trend_features(series)
    if not f:
        return "未知", None

    slope, accel, vol = f

    if slope > 1 and accel > 0 and vol < 5:
        return "加速期", 6
    if slope > 1 and accel < 0:
        return "饱和期", 2
    if slope < 0:
        return "衰退期", 0

    return "观察期", 4
