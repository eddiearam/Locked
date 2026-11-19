# Locked k-means results

Numbers below are copied from `python fit_clusters.py`. They are not slide layouts.

## A. Business question

Which usage segment is this user in, so Locked can choose the intervention strength instead of treating every user the same?

The model informs how strong an intervention to apply. Without it, Locked keeps all users in one group and applies the same strong intervention.

## B. Data

- Source: not provided.
- Period: not provided.
- The files do not say whether the CSV is synthetic, scraped, or public.
- File: `data/locked_screentime_full.csv`
- 700 rows. One row per `User_ID`. No missing values.
- Train / test: 490 / 210 (70/30, `random_state=42`).

| Column | Role |
|---|---|
| `User_ID` | Identifier. Excluded from the fit. |
| `Operating_System` | Android or iOS. Excluded. |
| `App_Usage_Time` | Feature. Minutes per day, as named in `load_screentime.py`. |
| `Screen_On_Time` | Feature. Hours per day, as named in `load_screentime.py`. |
| `Number_of_Apps_Installed` | Feature. |
| `Age` | Excluded. It does not track usage in this file. |
| `User_Behavior_Class` | Excluded. Clustering has no outcome, and this column is already a 1–5 usage rank. |

## C. Model specification

- Family: k-means (`KMeans`, `n_init=10`, `random_state=42`).
- Features: `App_Usage_Time`, `Screen_On_Time`, `Number_of_Apps_Installed`.
- Outcome: none.
- Preprocessing: `StandardScaler` fit on the 490 training rows only, then applied to the test rows and to a new user.
- K-means is fit on the scaled training rows only. Test rows are assigned to those trained centers.
- Selected k: **3**, from the training elbow only.

## D. Train/test elbow result

Elbow rule: rescale k and WCSS to 0–1, draw the straight line from k=1 to k=10, and take the k farthest from that line. The test curve is scored the same way only as a check. It does not choose k.

Training WCSS:

| k | WCSS | Chord distance |
|---|---|---|
| 1 | 1470.00 | 0.0000 |
| 2 | 342.73 | 0.4766 |
| 3 | 172.23 | 0.4820 |
| 4 | 93.06 | 0.4424 |
| 5 | 57.48 | 0.3813 |
| 6 | 47.31 | 0.3078 |
| 7 | 42.19 | 0.2317 |
| 8 | 38.67 | 0.1549 |
| 9 | 35.71 | 0.0778 |
| 10 | 34.14 | 0.0000 |

Test WCSS, using the trained centers:

| k | WCSS | Chord distance |
|---|---|---|
| 1 | 560.36 | 0.0000 |
| 2 | 164.36 | 0.4354 |
| 3 | 83.64 | 0.4616 |
| 4 | 43.23 | 0.4355 |
| 5 | 25.97 | 0.3793 |
| 6 | 22.28 | 0.3055 |
| 7 | 18.72 | 0.2316 |
| 8 | 17.70 | 0.1544 |
| 9 | 16.15 | 0.0778 |
| 10 | 15.57 | 0.0000 |

Training elbow k = 3. Test elbow k = 3. They agree.

k=2 is close on both curves (train chord distance 0.4766 versus 0.4820 at k=3). The rule still selects 3, and the test curve selects 3 as well.

Baseline versus v1 on the test rows:

- Baseline, k=1, test WCSS: 560.36
- V1, k=3, test WCSS: 83.64
- Reduction: 85.07%

## E. Cluster interpretation

Centers are the training centroids converted back to the original units. Cluster numbers are arbitrary.

| Cluster | Name | App minutes / day | Screen hours / day | Apps installed | Train users | Test users |
|---|---|---|---|---|---|---|
| 0 | Light Users | 98.26 | 2.35 | 23.63 | 203 (41.43%) | 82 (39.05%) |
| 2 | Moderate Users | 315.81 | 5.92 | 59.78 | 181 (36.94%) | 94 (44.76%) |
| 1 | Heavy Users | 539.80 | 10.03 | 89.55 | 106 (21.63%) | 34 (16.19%) |

Light users are near 2 hours of screen-on time. Moderate users are near 6 hours. Heavy users are near 10 hours, with much higher app time and more apps installed.

## F. Decision rule

`recommend_intervention(new_user)` scales the three usage values with the training scaler, assigns the nearest training center, and returns the segment and action.

| Segment | Action |
|---|---|
| Light Users | Light reminder and basic accountability |
| Moderate Users | Structured screen-time goal and notification |
| Heavy Users | Stronger commitment intervention with a financial-stake recommendation |

## G. Example new-user decision

Input: app usage 480 minutes, screen-on time 8.0 hours, 75 apps installed.

- Predicted cluster: 1
- Predicted segment: Heavy Users
- Action: Stronger commitment intervention with a financial-stake recommendation

## H. Baseline vs V1 value calculation

Two comparisons. The WCSS comparison is the model fit. The dollars are a hypothetical assumption, not Locked's costs.

Fit, on the 210 test users:

- One group (k=1) test WCSS: 560.36
- Three segments (k=3) test WCSS: 83.64
- Test WCSS reduction: 85.07%

Hypothetical costs, assumed for this exercise:

- Light intervention: $0.20 per user
- Moderate intervention: $0.50 per user
- Strong intervention: $1.00 per user
- Baseline: all 210 test users get the strong intervention

Test-set cost under that assumption:

- Baseline: 210 × $1.00 = $210.00
- V1: 82 × $0.20 + 94 × $0.50 + 34 × $1.00 = $16.40 + $47.00 + $34.00 = $97.40
- Savings: $112.60
- Percentage savings: 53.62%

## I. One-sentence business headline

Splitting users into light, moderate, and heavy usage segments cuts test-set within-cluster variation by 85.07% versus one group, and under the stated cost assumptions saves $112.60 (53.62%) on the 210 test users by reserving the strong intervention for the heavy segment.

## J. Chart files

- `outputs/train_elbow.png`
- `outputs/test_elbow.png`
- `outputs/baseline_vs_v1_test_wcss.png`
