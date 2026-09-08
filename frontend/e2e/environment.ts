import { readFileSync, realpathSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export function environment() {
  const root = realpathSync(fileURLToPath(new URL('../..', import.meta.url)));
  const directory = process.env.ATLAS_E2E_RUN_DIR;
  if (!directory || !process.env.ATLAS_E2E_TOKEN)
    throw new Error(
      'Inicia E2E mediante tools/run_e2e.py; nunca se reutiliza una URL externa.',
    );
  const run = realpathSync(directory);
  if (
    path.dirname(run) !== realpathSync(path.join(root, 'var/validation')) ||
    !/^e2e-[a-f0-9]{32}$/.test(path.basename(run))
  )
    throw new Error('El directorio E2E no pertenece a esta ejecución aislada.');
  const record = JSON.parse(readFileSync(path.join(run, 'run.json'), 'utf8'));
  if (
    record.format !== 1 ||
    !record.active ||
    record.token !== process.env.ATLAS_E2E_TOKEN ||
    realpathSync(record.root) !== root ||
    realpathSync(record.data_dir) !== realpathSync(path.join(run, 'data')) ||
    record.base_url !== 'http://127.0.0.1:3000' ||
    record.run_id !== path.basename(run)
  )
    throw new Error('La identidad de la base o del servidor E2E no coincide.');
  for (const pid of [
    record.harness_pid,
    record.children?.backend,
    record.children?.frontend,
  ]) {
    if (!Number.isInteger(pid) || pid <= 0)
      throw new Error('Falta un proceso E2E identificado.');
    process.kill(pid, 0);
  }
  return { root, run, baseURL: record.base_url as string };
}
