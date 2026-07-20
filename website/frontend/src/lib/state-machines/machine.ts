/**
 * Tiny explicit state-machine helper. Each machine declares its full
 * transition table; anything not in the table is an illegal transition.
 */
export interface TransitionTable<S extends string> {
  readonly [from: string]: readonly S[];
}

export function canTransition<S extends string>(
  table: TransitionTable<S>,
  from: S,
  to: S,
): boolean {
  return (table[from] ?? []).includes(to);
}

export function assertTransition<S extends string>(
  table: TransitionTable<S>,
  from: S,
  to: S,
  name: string,
): S {
  if (from === to) return to;
  if (!canTransition(table, from, to)) {
    throw new Error(`Illegal ${name} transition: ${from} → ${to}`);
  }
  return to;
}

export function isTerminal<S extends string>(table: TransitionTable<S>, state: S): boolean {
  return (table[state] ?? []).length === 0;
}
