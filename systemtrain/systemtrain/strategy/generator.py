from __future__ import annotations

import copy
import random

from systemtrain.strategy.dsl import (
    StrategyGene,
    crossover_genes,
    mutate_gene,
    random_gene,
)
from systemtrain.strategy.templates import seeded_population


def create_initial_population(size: int, seed: int | None = None) -> list[StrategyGene]:
    rng = random.Random(seed)
    return seeded_population(size, rng)


def breed_next_generation(
    population: list[StrategyGene],
    fitness_scores: list[float],
    elite_count: int,
    tournament_size: int,
    crossover_rate: float,
    mutation_rate: float,
    rng: random.Random,
) -> list[StrategyGene]:
    indexed = sorted(zip(fitness_scores, population), key=lambda x: x[0], reverse=True)
    elites = [g for _, g in indexed[:elite_count]]
    offspring: list[StrategyGene] = []

    while len(offspring) < len(population) - elite_count:
        parent_a = _tournament_select(indexed, tournament_size, rng)
        parent_b = _tournament_select(indexed, tournament_size, rng)
        if rng.random() < crossover_rate:
            child = crossover_genes(parent_a, parent_b, rng)
        else:
            child = copy.deepcopy(parent_a)
        child = mutate_gene(child, mutation_rate, rng)
        offspring.append(child)

    return elites + offspring


def _tournament_select(
    indexed: list[tuple[float, StrategyGene]],
    k: int,
    rng: random.Random,
) -> StrategyGene:
    contestants = rng.sample(indexed, min(k, len(indexed)))
    return max(contestants, key=lambda x: x[0])[1]
