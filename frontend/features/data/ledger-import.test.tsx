import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DataPanel } from "@/app/workbench";
import { api } from "@/lib/api";
import { dataset as datasetResponse, portfolioResponse } from "@/test/fixtures";

vi.mock("@/lib/api", () => ({ api: vi.fn() }));
const request = vi.mocked(api);
const reply = () => ({
  added: 1,
  duplicates: 0,
  total: 1,
  committed: false,
  portfolio: portfolioResponse(),
  preview_token: "a".repeat(64),
});
const props = () => ({
  dataset: datasetResponse(),
  refresh: vi.fn(async () => {}),
  selectDataset: vi.fn(),
  onError: vi.fn(),
});

async function editLedger() {
  const user = userEvent.setup();
  screen.getByRole("combobox", { name: "Tipo de archivo" }).focus();
  await user.keyboard("{ArrowDown}");
  await user.click(await screen.findByRole("option", { name: "Movimientos de cartera" }));
  fireEvent.change(screen.getByRole("textbox", { name: "Contenido CSV" }), {
    target: { value: "csv-reviewed" },
  });
  return user;
}

describe("Confirmación de movimientos", () => {
  beforeEach(() => {
    request.mockReset();
  });
  it("confirma el CSV revisado con el token del servidor", async () => {
    request.mockResolvedValueOnce(reply()).mockResolvedValueOnce({ ...reply(), committed: true });
    const input = props();
    render(<DataPanel {...input} />);
    const user = await editLedger();
    await user.click(screen.getByRole("button", { name: "Previsualizar movimientos" }));
    await user.click(await screen.findByRole("button", { name: "Confirmar importación" }));
    expect(request).toHaveBeenLastCalledWith(`/datasets/${input.dataset.id}/ledger`, {
      csv: "csv-reviewed",
      commit: true,
      preview_token: "a".repeat(64),
    });
    await waitFor(() => expect(input.refresh).toHaveBeenCalledOnce());
    expect(screen.queryByRole("button", { name: "Confirmar importación" })).toBeNull();
  });

  it.each(["dataset", "version", "csv"])("exige otra revisión al cambiar %s", async (change) => {
    request.mockResolvedValue(reply());
    const input = props();
    const view = render(<DataPanel {...input} />);
    const user = await editLedger();
    await user.click(screen.getByRole("button", { name: "Previsualizar movimientos" }));
    await screen.findByRole("button", { name: "Confirmar importación" });
    if (change === "csv")
      fireEvent.change(screen.getByRole("textbox", { name: "Contenido CSV" }), {
        target: { value: "other-csv" },
      });
    else
      view.rerender(
        <DataPanel
          {...input}
          dataset={{
            ...input.dataset,
            ...(change === "dataset" ? { id: "other" } : { version: 2 }),
          }}
        />,
      );
    expect(screen.queryByRole("button", { name: "Confirmar importación" })).toBeNull();
    expect(request).toHaveBeenCalledTimes(1);
  });

  it("descarta una previsualización que termina después de editar el CSV", async () => {
    let resolve!: (value: unknown) => void;
    request.mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done;
        }),
    );
    render(<DataPanel {...props()} />);
    const user = await editLedger();
    await user.click(screen.getByRole("button", { name: "Previsualizar movimientos" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Contenido CSV" }), {
      target: { value: "new-csv" },
    });
    await act(async () => resolve(reply()));
    expect(screen.queryByRole("button", { name: "Confirmar importación" })).toBeNull();
  });

  it("retira una confirmación rechazada para pedir otra previsualización", async () => {
    request
      .mockResolvedValueOnce(reply())
      .mockRejectedValueOnce(new Error("La previsualización ha cambiado."));
    const input = props();
    render(<DataPanel {...input} />);
    const user = await editLedger();
    await user.click(screen.getByRole("button", { name: "Previsualizar movimientos" }));
    await user.click(await screen.findByRole("button", { name: "Confirmar importación" }));
    await waitFor(() =>
      expect(input.onError).toHaveBeenLastCalledWith("La previsualización ha cambiado."),
    );
    expect(screen.queryByRole("button", { name: "Confirmar importación" })).toBeNull();
    expect(input.refresh).not.toHaveBeenCalled();
  });
});
