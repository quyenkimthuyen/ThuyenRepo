"""Extract interpretable rules from decision trees trained on historical labels."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier

from systemtrain.learn.setup_miner import LearnedSetup, MinedRule, _eval_htf_filters


@dataclass
class TreeRuleSet:
    long_rules: list[MinedRule]
    short_rules: list[MinedRule]
    train_wr: float
    samples: int


def _tree_to_rules(
    clf: DecisionTreeClassifier,
    feature_names: list[str],
    X: pd.DataFrame,
    y: pd.Series,
    direction: str,
) -> list[MinedRule]:
    """Walk tree leaves and extract AND-rule chains for positive class."""
    tree = clf.tree_
    rules: list[MinedRule] = []

    def recurse(node: int, conditions: list[tuple[str, str, float]]):
        if tree.feature[node] < 0:
            samples = tree.n_node_samples[node]
            if samples < 30:
                return
            value = tree.value[node][0]
            wins = value[1] if len(value) > 1 else 0
            total = value.sum()
            if total < 30:
                return
            wr = wins / total
            if wr < 0.40:
                return
            # Build synthetic rule list from conditions
            for feat, op, thresh in conditions:
                rules.append(
                    MinedRule(feat, op, thresh, direction, wr, int(total), wr * 2 - (1 - wr))
                )
            return
        feat = feature_names[tree.feature[node]]
        thresh = float(tree.threshold[node])
        recurse(node * 2 + 1, conditions + [(feat, "lte", thresh)])
        recurse(node * 2 + 2, conditions + [(feat, "gt", thresh)])

    recurse(0, [])
    return rules


def mine_tree_rules(
    df: pd.DataFrame,
    long_labels: pd.Series,
    short_labels: pd.Series,
    feature_cols: list[str],
    htf_long_mask: np.ndarray,
    htf_short_mask: np.ndarray,
    max_depth: int = 4,
    min_samples_leaf: int = 60,
) -> list[LearnedSetup]:
    """Train shallow trees on long/short labels — discover non-obvious combinations."""
    setups: list[LearnedSetup] = []
    cols = [c for c in feature_cols if c in df.columns]

    for direction, labels, htf_mask in (
        ("long", long_labels, htf_long_mask),
        ("short", short_labels, htf_short_mask),
    ):
        mask = htf_mask & labels.notna().values
        X = df.loc[mask, cols].dropna()
        y = labels.loc[X.index].astype(int)
        if len(X) < 200:
            continue

        baseline = y.mean()
        for depth in (3, 4, 5):
            clf = DecisionTreeClassifier(
                max_depth=depth,
                min_samples_leaf=min_samples_leaf,
                class_weight="balanced",
                random_state=42,
            )
            clf.fit(X, y)
            pred = clf.predict(X)
            if pred.sum() < 30:
                continue
            wr = y[pred == 1].mean()
            n = int(pred.sum())
            if wr < baseline + 0.08:
                continue

            # Extract path to each positive leaf
            paths = _extract_leaf_paths(clf, cols)
            for path_conds in paths:
                leaf_wr, leaf_n = _eval_path(X, y, path_conds)
                if leaf_n < 30 or leaf_wr < baseline + 0.07:
                    continue
                mined = [MinedRule(f, op, t, direction, leaf_wr, leaf_n, leaf_wr * 2 - (1 - wr)) for f, op, t in path_conds]
                if direction == "long":
                    setup = LearnedSetup(long_rules=mined, direction="long_only", source_wr=leaf_wr, source_samples=leaf_n)
                else:
                    setup = LearnedSetup(short_rules=mined, direction="short_only", source_wr=leaf_wr, source_samples=leaf_n)
                setups.append(setup)

    return setups


def _extract_leaf_paths(clf, feature_names: list[str]) -> list[list[tuple[str, str, float]]]:
    from sklearn.tree import _tree

    tree = clf.tree_
    paths: list[list[tuple[str, str, float]]] = []

    def walk(node: int, path: list):
        if tree.feature[node] == _tree.TREE_UNDEFINED:
            vals = tree.value[node][0]
            total = vals.sum()
            if total < 30:
                return
            wr = vals[1] / total if total > 0 else 0
            if wr >= 0.40:
                paths.append(list(path))
            return
        feat = feature_names[tree.feature[node]]
        thresh = float(tree.threshold[node])
        left = tree.children_left[node]
        right = tree.children_right[node]
        walk(left, path + [(feat, "lte", thresh)])
        walk(right, path + [(feat, "gt", thresh)])

    walk(0, [])
    return paths


def _eval_path(X: pd.DataFrame, y: pd.Series, conds: list[tuple[str, str, float]]) -> tuple[float, int]:
    mask = np.ones(len(X), dtype=bool)
    for feat, op, thresh in conds:
        if op == "lte":
            mask &= (X[feat] <= thresh).values
        else:
            mask &= (X[feat] > thresh).values
    n = mask.sum()
    if n == 0:
        return 0.0, 0
    return float(y.values[mask].mean()), int(n)
