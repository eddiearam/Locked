"""Fit Locked usage segments with k-means.

Run from the repo root:

    python fit_clusters.py

k is chosen from the training elbow only. Test WCSS uses the centers
learned on the training rows and is not used to pick k.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

RANDOM_STATE = 42
K_RANGE = range(1, 11)
FEATURES = [
    "App_Usage_Time",
    "Screen_On_Time",
    "Number_of_Apps_Installed",
]
EXCLUDED = [
    "User_ID",
    "Operating_System",
    "Age",
    "User_Behavior_Class",
]

# Hypothetical dollars per user. Not Locked's real costs.
TIER_COST = {
    "light": 0.20,
    "moderate": 0.50,
    "strong": 1.00,
}
TIER_ACTION = {
    "light": "Light reminder and basic accountability",
    "moderate": "Structured screen-time goal and notification",
    "strong": "Stronger commitment intervention with a financial-stake recommendation",
}
BASELINE_TIER = "strong"

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "locked_screentime_full.csv"
OUTPUT_DIR = ROOT / "outputs"

EXAMPLE_USER = {
    "App_Usage_Time": 480,
    "Screen_On_Time": 8.0,
    "Number_of_Apps_Installed": 75,
}


def wcss_from_centers(X, centers):
    """Sum of squared distances from each row to its nearest center."""
    distances = ((X[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    return float(distances.min(axis=1).sum())


def geometric_elbow(ks, values):
    """k farthest from the straight line between the first and last point.

    k and the curve are each rescaled to 0-1 so a step in k and a step in
    WCSS count equally. This is how the training elbow is chosen.
    """
    k = np.asarray(list(ks), dtype=float)
    y = np.asarray(list(values), dtype=float)
    k_unit = (k - k.min()) / (k.max() - k.min())
    y_unit = (y - y.min()) / (y.max() - y.min())
    start = np.array([k_unit[0], y_unit[0]])
    end = np.array([k_unit[-1], y_unit[-1]])
    chord = end - start
    chord_length = np.linalg.norm(chord)
    distances = []
    for point in np.column_stack([k_unit, y_unit]):
        distance = np.abs(chord[0] * (start[1] - point[1]) - chord[1] * (start[0] - point[0]))
        distances.append(float(distance / chord_length))
    chosen = int(k[int(np.argmax(distances))])
    return chosen, distances


def tier_for_rank(rank, n_clusters):
    """Map a low-to-high usage rank onto light, moderate, or strong."""
    if n_clusters == 1:
        return BASELINE_TIER
    light_n = max(1, n_clusters // 3)
    strong_n = max(1, n_clusters // 3)
    if rank < light_n:
        return "light"
    if rank >= n_clusters - strong_n:
        return "strong"
    return "moderate"


def segment_names(centers_original):
    """Name each cluster from its screen-on center, lowest usage first."""
    order = list(np.argsort(centers_original[:, 1]))
    tiers = {}
    names = {}
    for rank, cluster in enumerate(order):
        tier = tier_for_rank(rank, len(order))
        tiers[int(cluster)] = tier
    tier_totals = {}
    for tier in tiers.values():
        tier_totals[tier] = tier_totals.get(tier, 0) + 1
    seen = {tier: 0 for tier in tier_totals}
    base = {"light": "Light Users", "moderate": "Moderate Users", "strong": "Heavy Users"}
    for cluster in order:
        cluster = int(cluster)
        tier = tiers[cluster]
        seen[tier] += 1
        name = base[tier]
        if tier_totals[tier] > 1:
            place = "Lower" if seen[tier] == 1 else "Higher"
            if tier_totals[tier] > 2 and seen[tier] not in (1, tier_totals[tier]):
                place = "Middle"
            name = f"{place}-{base[tier].split()[0].lower()} users"
            name = name[0].upper() + name[1:]
        names[cluster] = name
    return names, tiers


def save_elbow(path, ks, values, title, selected_k, other_k=None):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(list(ks), values, marker="o", color="#1f4e79")
    ax.axvline(selected_k, color="#c45911", linestyle="--", label=f"k chosen on training data = {selected_k}")
    if other_k is not None and other_k != selected_k:
        ax.axvline(other_k, color="#548235", linestyle=":", label=f"elbow on this curve = {other_k}")
    ax.set_xlabel("k")
    ax.set_ylabel("WCSS")
    ax.set_title(title)
    ax.set_xticks(list(ks))
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def save_baseline_chart(path, baseline_wcss, v1_wcss, selected_k):
    fig, ax = plt.subplots(figsize=(7, 5))
    labels = ["Baseline\nk = 1", f"V1\nk = {selected_k}"]
    values = [baseline_wcss, v1_wcss]
    bars = ax.bar(labels, values, color=["#7f7f7f", "#1f4e79"])
    ax.set_ylabel("Test WCSS")
    ax.set_title("Test WCSS: one group vs selected k")
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.1f}", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def recommend_intervention(new_user, scaler, model, names, tiers):
    row = pd.DataFrame([{feature: new_user[feature] for feature in FEATURES}])
    scaled = scaler.transform(row)
    cluster = int(model.predict(scaled)[0])
    tier = tiers[cluster]
    return {
        "input": {feature: new_user[feature] for feature in FEATURES},
        "cluster": cluster,
        "segment": names[cluster],
        "tier": tier,
        "action": TIER_ACTION[tier],
    }


def money(amount):
    return f"${amount:.2f}"


def main():
    df = pd.read_csv(DATA_PATH)
    X = df[FEATURES]
    train_X, test_X = train_test_split(X, test_size=0.30, random_state=RANDOM_STATE)

    scaler = StandardScaler()
    train_scaled = scaler.fit_transform(train_X)
    test_scaled = scaler.transform(test_X)

    models = {}
    train_wcss = []
    test_wcss = []
    for k in K_RANGE:
        model = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_STATE)
        model.fit(train_scaled)
        models[k] = model
        train_wcss.append(float(model.inertia_))
        test_wcss.append(wcss_from_centers(test_scaled, model.cluster_centers_))

    selected_k, train_distances = geometric_elbow(K_RANGE, train_wcss)
    test_elbow_k, test_distances = geometric_elbow(K_RANGE, test_wcss)
    elbows_agree = selected_k == test_elbow_k

    model = models[selected_k]
    centers_original = scaler.inverse_transform(model.cluster_centers_)
    names, tiers = segment_names(centers_original)

    train_labels = model.labels_
    test_labels = model.predict(test_scaled)

    baseline_test_wcss = test_wcss[0]
    v1_test_wcss = test_wcss[selected_k - 1]
    wcss_reduction_pct = (baseline_test_wcss - v1_test_wcss) / baseline_test_wcss * 100

    test_costs = np.array([TIER_COST[tiers[int(label)]] for label in test_labels])
    baseline_cost = TIER_COST[BASELINE_TIER] * len(test_X)
    v1_cost = float(test_costs.sum())
    dollar_savings = baseline_cost - v1_cost
    dollar_savings_pct = dollar_savings / baseline_cost * 100

    decision = recommend_intervention(EXAMPLE_USER, scaler, model, names, tiers)

    OUTPUT_DIR.mkdir(exist_ok=True)
    save_elbow(
        OUTPUT_DIR / "train_elbow.png",
        K_RANGE,
        train_wcss,
        "Training elbow (k is chosen on this curve)",
        selected_k,
    )
    save_elbow(
        OUTPUT_DIR / "test_elbow.png",
        K_RANGE,
        test_wcss,
        "Test WCSS from trained centers (not used to choose k)",
        selected_k,
        other_k=test_elbow_k,
    )
    save_baseline_chart(
        OUTPUT_DIR / "baseline_vs_v1_test_wcss.png",
        baseline_test_wcss,
        v1_test_wcss,
        selected_k,
    )

    print(f"rows: {len(df)}")
    print(f"training rows: {len(train_X)}")
    print(f"test rows: {len(test_X)}")
    print(f"features: {', '.join(FEATURES)}")
    print(f"excluded: {', '.join(EXCLUDED)}")
    print("preprocessing: StandardScaler fit on training rows only")
    print(f"random_state: {RANDOM_STATE}")
    print("k means: KMeans n_init=10, fit on scaled training rows only")
    print()
    print("elbow method: geometric, max distance from the chord between k=1 and k=10")
    print("k is selected from the training curve only")
    print()
    print("train WCSS")
    for k, value, distance in zip(K_RANGE, train_wcss, train_distances):
        print(f"  k={k} wcss={value:.2f} chord_distance={distance:.4f}")
    print(f"selected k: {selected_k}")
    print()
    print("test WCSS from trained centers")
    for k, value, distance in zip(K_RANGE, test_wcss, test_distances):
        print(f"  k={k} wcss={value:.2f} chord_distance={distance:.4f}")
    print(f"test elbow k: {test_elbow_k}")
    print(f"train and test elbow agree: {elbows_agree}")
    print()
    print(f"baseline test WCSS k=1: {baseline_test_wcss:.2f}")
    print(f"v1 test WCSS k={selected_k}: {v1_test_wcss:.2f}")
    print(f"test WCSS reduction: {wcss_reduction_pct:.2f}%")
    print()
    print("cluster centers in original units (training fit)")
    for cluster in range(selected_k):
        center = centers_original[cluster]
        train_n = int((train_labels == cluster).sum())
        test_n = int((test_labels == cluster).sum())
        print(
            f"  cluster {cluster}: {names[cluster]}"
            f" | app_usage_min={center[0]:.2f}"
            f" screen_on_hours={center[1]:.2f}"
            f" apps_installed={center[2]:.2f}"
            f" | train {train_n} ({train_n / len(train_X) * 100:.2f}%)"
            f" test {test_n} ({test_n / len(test_X) * 100:.2f}%)"
            f" | tier={tiers[cluster]}"
            f" | action={TIER_ACTION[tiers[cluster]]}"
        )
    print()
    print("example new user")
    for feature, value in decision["input"].items():
        print(f"  {feature}: {value}")
    print(f"  predicted cluster: {decision['cluster']}")
    print(f"  predicted segment: {decision['segment']}")
    print(f"  recommended action: {decision['action']}")
    print()
    print("hypothetical cost assumptions (not real Locked costs)")
    print(f"  light intervention: {money(TIER_COST['light'])} per user")
    print(f"  moderate intervention: {money(TIER_COST['moderate'])} per user")
    print(f"  strong intervention: {money(TIER_COST['strong'])} per user")
    print(f"  baseline: every test user receives the strong intervention")
    print(f"  costs counted on the {len(test_X)} test users")
    print("v1 assumed cost by segment on the test users")
    for cluster in range(selected_k):
        test_n = int((test_labels == cluster).sum())
        tier = tiers[cluster]
        print(f"  {names[cluster]}: {test_n} x {money(TIER_COST[tier])} = {money(TIER_COST[tier] * test_n)}")
    print(f"baseline assumed cost: {money(baseline_cost)}")
    print(f"v1 assumed cost: {money(v1_cost)}")
    print(f"assumed dollar savings: {money(dollar_savings)}")
    print(f"assumed percentage savings: {dollar_savings_pct:.2f}%")
    print()
    print("charts:")
    print("  outputs/train_elbow.png")
    print("  outputs/test_elbow.png")
    print("  outputs/baseline_vs_v1_test_wcss.png")


if __name__ == "__main__":
    main()
