// Compatibility exports for existing imports; features have explicit dependencies.
export { moneyEUR as money, percent as pct } from '@/shared/format';
export { Metric, Field, Choice, DataTable } from '@/shared/ui';
export { Curve } from '@/components/atlas/curve';
export { Lab } from '@/features/research/lab';
export { ResearchResult } from '@/features/research/research-result';
export { DataPanel } from '@/features/data/data-panel';
export { AgentPanel } from '@/features/experiments/agent-panel';
export { SettingsPanel } from '@/features/settings/settings-panel';
