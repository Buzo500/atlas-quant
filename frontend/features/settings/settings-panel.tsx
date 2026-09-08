'use client';
import { useState } from 'react';
import { Bot, ShieldAlert, FileText } from 'lucide-react';
import { api } from '@/lib/api';
import type { StateResponse } from '@/lib/api-types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { DataTable, Field } from '@/shared/ui';
import { useAction } from '@/shared/use-action';
import { dateTime, moneyUSD, number, percent } from '@/shared/format';

export function SettingsPanel({
  state,
  refresh,
  onError,
}: {
  state: StateResponse;
  refresh: () => Promise<void>;
  onError: (s: string) => void;
}) {
  const { busy, run } = useAction(onError);
  const [weight, setWeight] = useState(state.settings.max_position_weight);
  return (
    <div className="settings-layout">
      <section className="panel settings-controls">
        <div className="panel-heading">
          <h2>Control de ejecución</h2>
          <ShieldAlert size={23} />
        </div>
        <p className="muted">
          La parada bloquea nuevas órdenes simuladas y cancela las pendientes.
          Las posiciones existentes permanecen abiertas y se siguen valorando.
        </p>
        <div className="switch-row">
          <Switch
            aria-label="Parada de ejecución"
            disabled={busy}
            checked={state.settings.kill_switch}
            onCheckedChange={(checked) =>
              run(async () => {
                await api('/settings', {
                  kill_switch: checked,
                });
                await refresh();
              })
            }
          />
          <strong>
            {state.settings.kill_switch
              ? 'Parada activada'
              : 'Simulación habilitada bajo reglas'}
          </strong>
        </div>
        <div className="field-compact">
          <Field label="Peso máximo por posición (0–1)">
            <Input
              type="number"
              min=".01"
              max="1"
              step=".05"
              value={weight}
              onChange={(e) => setWeight(Number(e.target.value))}
            />
          </Field>
        </div>
        {weight !== state.settings.max_position_weight && (
          <p className="notice amber">
            El borrador difiere del límite vigente (
            {percent(state.settings.max_position_weight)}). Guarda el límite
            para aplicarlo.
          </p>
        )}
        <Button
          disabled={busy}
          onClick={() =>
            run(async () => {
              await api('/settings', {
                max_position_weight: weight,
              });
              await refresh();
            })
          }
        >
          Guardar límite
        </Button>
        <p className="footnote">
          Cada experimento tiene una cuenta simulada independiente. No se
          agregan como una única cartera. Si su peso validado supera este
          límite, su ejecución se bloquea.
        </p>
      </section>
      <section className="panel settings-providers">
        <div className="panel-heading">
          <h2>Proveedores de IA</h2>
          <Bot size={20} />
        </div>
        {state.providers.map((p) => (
          <div key={p.provider} className="provider">
            <div>
              <strong>
                {p.provider === 'openai' ? 'OpenAI' : 'Anthropic'}
              </strong>
              <span className={'tag ' + (!p.configured ? 'amber' : '')}>
                {p.configured ? 'CLAVE CONFIGURADA' : 'SIN CLAVE'}
              </span>
            </div>
            {p.models.length > 0 ? (
              p.models.map((model) => (
                <p className="muted" key={model.id}>
                  <code>{model.id}</code> · {moneyUSD(model.input_per_million)}{' '}
                  entrada / {moneyUSD(model.output_per_million)} salida por
                  millón de tokens.
                </p>
              ))
            ) : (
              <p className="muted">Catálogo de modelos no disponible.</p>
            )}
          </div>
        ))}
        <p>
          Crea un archivo <code>.env</code> en la carpeta del proyecto, usando{' '}
          <code>.env.example</code> como plantilla. Añade la clave del proveedor
          elegido y reinicia ATLAS.
        </p>
        <p className="muted">
          Las claves solo se leen en el motor local. El archivo queda excluido
          de Git. Los importes son estimaciones en USD; la factura del proveedor
          prevalece.
        </p>
      </section>
      <section className="panel settings-audit">
        <div className="panel-heading">
          <h2>Registro de actividad</h2>
          <FileText size={20} />
        </div>
        <p className="muted">Se muestran hasta 40 eventos recientes.</p>
        <DataTable
          heads={['N.º', 'Fecha', 'Evento', 'Referencia']}
          numericColumns={[0]}
          emptyMessage="Todavía no hay actividad registrada."
          rows={state.audit.map((a) => [
            number(a.seq, { maximumFractionDigits: 0 }),
            <time key="at" dateTime={a.at}>
              {dateTime(a.at)}
            </time>,
            a.event,
            a.entity ? (
              <code key="entity" title={a.entity}>
                {a.entity.slice(0, 12)}
              </code>
            ) : (
              'Sistema'
            ),
          ])}
        />
      </section>
    </div>
  );
}
