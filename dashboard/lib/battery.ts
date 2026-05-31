/** Mirrors fairbench.battery per_cell_for_scenario / expected_battery_calls. */
const BATTERY_CELLS = 120;

export function perCellForScenario(scenarioId: string): number {
  let n = 0;
  for (let i = 0; i < scenarioId.length; i++) {
    n += (i + 1) * scenarioId.charCodeAt(i);
  }
  return 6 + (n % 9);
}

export function expectedBatteryCalls(scenarioId: string): number {
  return BATTERY_CELLS * perCellForScenario(scenarioId);
}
