'use client';

import type { CorporateReview } from '@/lib/api-types';
import { Field } from '@/shared/ui';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  MappingFields,
  mappingRecord,
  type MappingRow,
} from './corporate-shared';

type ReviewRow = { id: string; review: CorporateReview };
export type CorporateBookDraft = {
  mapping: MappingRow[];
  payments: MappingRow[];
  reviews: ReviewRow[];
};
export const emptyCorporateDraft = (): CorporateBookDraft => ({
  mapping: [],
  payments: [],
  reviews: [],
});

export function corporateBookInput(
  value: CorporateBookDraft,
  voiding: boolean,
) {
  const reviews: Record<string, CorporateReview> = {};
  for (const row of value.reviews) {
    const id = row.id.trim();
    if (!id || !row.review.evidence.trim() || id in reviews)
      throw new Error(
        'Cada revisión corporativa necesita un ID de evento distinto y evidencia.',
      );
    reviews[id] = row.review;
  }
  return {
    ...(!voiding && value.mapping.length
      ? { corporate_mapping: mappingRecord(value.mapping) }
      : {}),
    ...(!voiding && value.payments.length
      ? { unaccredited_payments: mappingRecord(value.payments) }
      : {}),
    ...(value.reviews.length ? { corporate_reviews: reviews } : {}),
  };
}

export function BookCorporateFields({
  value,
  onChange,
  voiding,
}: {
  value: CorporateBookDraft;
  onChange: (v: CorporateBookDraft) => void;
  voiding: boolean;
}) {
  const setReviews = (reviews: ReviewRow[]) => onChange({ ...value, reviews });
  return (
    <details className="details corporate-form">
      <summary>Dividendos, splits y derechos afectados por el lote</summary>
      <p className="muted">
        Para un evento individual puedes usar «Dividendos y splits». En un lote,
        copia el ID del evento desde su identidad y acredita cada derecho
        afectado. Una corrección anterior a la exfecha puede requerir una
        revisión conjunta.
      </p>
      {!voiding && (
        <>
          <MappingFields
            label="Referencias corporativas del CSV"
            rows={value.mapping}
            setRows={(mapping) => onChange({ ...value, mapping })}
          />
          <p className="muted">
            Referencia: corporate_event_ref del CSV. Destino: ID interno del
            evento.
          </p>
          <MappingFields
            label="Cobros sin derecho acreditado"
            rows={value.payments}
            setRows={(payments) => onChange({ ...value, payments })}
          />
          <p className="muted">
            Referencia: external_id del cobro. Destino: evidencia del efectivo
            recibido. Un cobro sin evento queda limitado hasta enlazar y
            acreditar su derecho.
          </p>
        </>
      )}
      {value.reviews.map((row, index) => {
        const update = (review: CorporateReview) =>
          setReviews(
            value.reviews.map((r, i) => (i === index ? { ...r, review } : r)),
          );
        const text = (
          key:
            | 'evidence'
            | 'eligible_quantity'
            | 'discrepancy_reason'
            | 'gross_amount'
            | 'gross_explanation'
            | 'fraction_evidence',
          label: string,
        ) => (
          <Field label={`${label} · evento ${index + 1}`}>
            <Input
              value={row.review[key] || ''}
              maxLength={500}
              onChange={(e) =>
                update({
                  ...row.review,
                  [key]:
                    e.target.value ||
                    (key === 'eligible_quantity' || key === 'gross_amount'
                      ? null
                      : ''),
                })
              }
            />
          </Field>
        );
        return (
          <fieldset className="corporate-mapping" key={index}>
            <legend>Revisión corporativa {index + 1}</legend>
            <div className="form-grid">
              <Field label={`ID del evento a revisar ${index + 1}`}>
                <Input
                  required
                  value={row.id}
                  onChange={(e) =>
                    setReviews(
                      value.reviews.map((r, i) =>
                        i === index ? { ...r, id: e.target.value } : r,
                      ),
                    )
                  }
                />
              </Field>
              <Field label={`Versión del evento ${index + 1}`}>
                <Input
                  type="number"
                  min={1}
                  required
                  value={row.review.event_revision}
                  onChange={(e) =>
                    update({
                      ...row.review,
                      event_revision: Number(e.target.value),
                    })
                  }
                />
              </Field>
              <Field label={`Secuencia económica del evento ${index + 1}`}>
                <Input
                  type="number"
                  min={1}
                  required
                  value={row.review.day_sequence}
                  onChange={(e) =>
                    update({
                      ...row.review,
                      day_sequence: Number(e.target.value),
                    })
                  }
                />
              </Field>
              {text('evidence', 'Evidencia de la revisión')}
              {text('eligible_quantity', 'Cantidad elegible (solo dividendo)')}
              {text('discrepancy_reason', 'Motivo de diferencia de cantidad')}
              {text('gross_amount', 'Bruto declarado (opcional)')}
              {text('gross_explanation', 'Evidencia de diferencia de bruto')}
              {text('fraction_evidence', 'Evidencia de fracción (solo split)')}
            </div>
            <Button
              type="button"
              variant="outline"
              onClick={() =>
                setReviews(value.reviews.filter((_, i) => i !== index))
              }
            >
              Quitar revisión corporativa {index + 1}
            </Button>
          </fieldset>
        );
      })}
      <Button
        type="button"
        variant="outline"
        disabled={value.reviews.length >= 100}
        onClick={() =>
          setReviews([
            ...value.reviews,
            {
              id: '',
              review: {
                event_revision: 1,
                day_sequence: 10,
                evidence: '',
                eligible_quantity: null,
                discrepancy_reason: '',
                gross_amount: null,
                gross_explanation: '',
                fraction_evidence: '',
              },
            },
          ])
        }
      >
        Añadir revisión corporativa al lote
      </Button>
    </details>
  );
}
