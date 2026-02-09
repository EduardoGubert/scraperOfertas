from __future__ import annotations

import asyncio
import logging
import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, scrolledtext, ttk

from src.application.use_cases.run_all_jobs import run_jobs_in_sequence
from src.bootstrap import build_container
from src.infrastructure.config.settings import get_settings


class QueueLogHandler(logging.Handler):
    def __init__(self, log_queue: queue.Queue[str]):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        self.log_queue.put(msg)


class ScraperGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.settings = get_settings()
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.is_running = False

        self.root.title("Scraper ML - egnOfertas")
        self.root.geometry("920x650")
        self.root.resizable(True, True)

        self._setup_ui()
        self._setup_logging()
        self._process_log_queue()
        self.update_status("Pronto")

    def _setup_ui(self) -> None:
        frame = ttk.Frame(self.root, padding="12")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(4, weight=1)

        title = ttk.Label(frame, text="scraperOfertas - Controle", font=("Segoe UI", 16, "bold"))
        title.grid(row=0, column=0, sticky=tk.W, pady=(0, 12))

        config = ttk.LabelFrame(frame, text="Configuracoes", padding="10")
        config.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 12))
        ttk.Label(config, text="Max itens por job:").grid(row=0, column=0, sticky=tk.W)
        self.max_items_var = tk.StringVar(value=str(self.settings.scheduler_max_produtos))
        ttk.Entry(config, textvariable=self.max_items_var, width=8).grid(row=0, column=1, sticky=tk.W, padx=(8, 0))

        buttons = ttk.Frame(frame)
        buttons.grid(row=2, column=0, sticky=tk.W, pady=(0, 12))

        self.login_btn = ttk.Button(buttons, text="Atualizar Login", command=self.on_login, width=24)
        self.login_btn.grid(row=0, column=0, padx=(0, 8))

        self.ofertas_btn = ttk.Button(buttons, text="Scraper Ofertas", command=lambda: self.start_job("ofertas"), width=24)
        self.ofertas_btn.grid(row=0, column=1, padx=(0, 8))

        self.relampago_btn = ttk.Button(
            buttons,
            text="Scraper Ofertas Relampago",
            command=lambda: self.start_job("ofertas_relampago"),
            width=28,
        )
        self.relampago_btn.grid(row=0, column=2, padx=(0, 8))

        self.cupons_btn = ttk.Button(buttons, text="Scraper Cupons", command=lambda: self.start_job("cupons"), width=24)
        self.cupons_btn.grid(row=1, column=1, padx=(0, 8), pady=(8, 0))

        self.todos_btn = ttk.Button(buttons, text="Executar Todos", command=lambda: self.start_job("todos"), width=24)
        self.todos_btn.grid(row=1, column=2, padx=(0, 8), pady=(8, 0))

        self.status_var = tk.StringVar(value="Status: Pronto")
        ttk.Label(frame, textvariable=self.status_var, font=("Segoe UI", 10, "bold")).grid(row=3, column=0, sticky=tk.W)

        log_frame = ttk.LabelFrame(frame, text="Logs", padding="6")
        log_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=24,
            state="disabled",
            wrap=tk.WORD,
            font=("Consolas", 9),
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    def _setup_logging(self) -> None:
        self.logger = logging.getLogger("gui")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.logger.handlers.clear()

        handler = QueueLogHandler(self.log_queue)
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%H:%M:%S"))
        self.logger.addHandler(handler)

    def _process_log_queue(self) -> None:
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.config(state="normal")
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.see(tk.END)
                self.log_text.config(state="disabled")
        except queue.Empty:
            pass
        self.root.after(120, self._process_log_queue)

    def update_status(self, status: str) -> None:
        self.status_var.set(f"Status: {status}")

    def _set_buttons_state(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.login_btn.config(state=state)
        self.ofertas_btn.config(state=state)
        self.relampago_btn.config(state=state)
        self.cupons_btn.config(state=state)
        self.todos_btn.config(state=state)

    def _parse_max_items(self) -> int:
        value = self.max_items_var.get().strip()
        if not value:
            return self.settings.scheduler_max_produtos
        parsed = int(value)
        if parsed <= 0:
            raise ValueError("max itens precisa ser maior que zero")
        return parsed

    def on_login(self) -> None:
        if self.is_running:
            messagebox.showwarning("Aviso", "Ja existe uma operacao em andamento.")
            return
        self._set_buttons_state(False)
        self.is_running = True
        self.update_status("Atualizando login...")
        threading.Thread(target=self._run_login_worker, daemon=True).start()

    def _run_login_worker(self) -> None:
        try:
            async def login_async():
                async with build_container(self.settings) as container:
                    async with container.engine_factory(headless=False, max_produtos=1) as engine:
                        ok = await engine.fazer_login_manual()
                        return ok

            ok = asyncio.run(login_async())
            if ok:
                self.logger.info("Login atualizado com sucesso.")
                self.root.after(0, lambda: messagebox.showinfo("Sucesso", "Login atualizado com sucesso."))
            else:
                self.logger.warning("Login nao confirmado.")
                self.root.after(0, lambda: messagebox.showwarning("Aviso", "Login nao confirmado."))
        except Exception as exc:
            self.logger.error(f"Erro ao atualizar login: {exc}")
            self.root.after(0, lambda: messagebox.showerror("Erro", f"Falha ao atualizar login: {exc}"))
        finally:
            self.is_running = False
            self.root.after(0, lambda: self._set_buttons_state(True))
            self.root.after(0, lambda: self.update_status("Pronto"))

    def start_job(self, scraper_type: str) -> None:
        if self.is_running:
            messagebox.showwarning("Aviso", "Ja existe uma operacao em andamento.")
            return

        try:
            max_items = self._parse_max_items()
        except ValueError as exc:
            messagebox.showerror("Erro", str(exc))
            return

        confirm = messagebox.askyesno(
            "Confirmar",
            f"Executar '{scraper_type}' com max {max_items} itens?\nA interface continuara responsiva.",
        )
        if not confirm:
            return

        self.is_running = True
        self._set_buttons_state(False)
        self.update_status(f"Executando {scraper_type}...")
        threading.Thread(target=self._run_job_worker, args=(scraper_type, max_items), daemon=True).start()

    def _run_job_worker(self, scraper_type: str, max_items: int) -> None:
        try:
            self.logger.info(f"Iniciando tarefa: {scraper_type} max_items={max_items}")

            async def run_async():
                async with build_container(self.settings) as container:
                    if scraper_type == "todos":
                        return await run_jobs_in_sequence(
                            job_use_case=container.job_use_case,
                            engine_factory=lambda: container.engine_factory(
                                headless=True,
                                max_produtos=max_items,
                            ),
                            max_items=max_items,
                            timeout_seconds=self.settings.scheduler_job_timeout_seconds,
                        )

                    async with container.engine_factory(headless=True, max_produtos=max_items) as engine:
                        return await container.job_use_case.execute(
                            scraper_type=scraper_type,
                            max_items=max_items,
                            engine=engine,
                        )

            result = asyncio.run(run_async())

            if scraper_type == "todos":
                self.logger.info(
                    "Execucao concluida | "
                    f"ofertas_novos={result.ofertas.novos} "
                    f"relampago_novos={result.ofertas_relampago.novos} "
                    f"cupons_novos={result.cupons.novos}"
                )
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Sucesso",
                        "Executar Todos finalizado.\n"
                        f"Ofertas novos: {result.ofertas.novos}\n"
                        f"Relampago novos: {result.ofertas_relampago.novos}\n"
                        f"Cupons novos: {result.cupons.novos}",
                    ),
                )
            else:
                self.logger.info(
                    "Execucao concluida | "
                    f"scraper={scraper_type} novos={result.novos} existentes={result.existentes} erros={result.erros}"
                )
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Sucesso",
                        f"Tarefa {scraper_type} finalizada.\n"
                        f"Novos: {result.novos}\n"
                        f"Existentes: {result.existentes}\n"
                        f"Erros: {result.erros}",
                    ),
                )
        except Exception as exc:
            self.logger.error(f"Falha na tarefa {scraper_type}: {exc}")
            self.root.after(0, lambda: messagebox.showerror("Erro", f"Falha na tarefa {scraper_type}: {exc}"))
        finally:
            self.is_running = False
            self.root.after(0, lambda: self.update_status("Pronto"))
            self.root.after(0, lambda: self._set_buttons_state(True))

    def on_closing(self) -> None:
        if self.is_running:
            if not messagebox.askyesno("Confirmar", "Existe uma tarefa em andamento. Fechar mesmo assim?"):
                return
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    gui = ScraperGUI(root)
    gui.logger.info(f"GUI iniciada em {datetime.now().isoformat()}")
    root.protocol("WM_DELETE_WINDOW", gui.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
