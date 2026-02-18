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
from src.domain.value_objects.categories import gui_category_options, resolve_category_filters
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
        ttk.Label(config, text="Min desconto (%):").grid(row=1, column=0, sticky=tk.W, pady=(6, 0))
        self.min_desconto_var = tk.StringVar(value=str(self.settings.offers_min_desconto_percent))
        ttk.Entry(config, textvariable=self.min_desconto_var, width=8).grid(row=1, column=1, sticky=tk.W, padx=(8, 0), pady=(6, 0))
        ttk.Label(config, text="Min comissao (%):").grid(row=2, column=0, sticky=tk.W, pady=(6, 0))
        self.min_comissao_var = tk.StringVar(value=str(self.settings.offers_min_comissao_percent))
        ttk.Entry(config, textvariable=self.min_comissao_var, width=8).grid(row=2, column=1, sticky=tk.W, padx=(8, 0), pady=(6, 0))
        ttk.Label(config, text="Categorias (Ctrl+clique):").grid(row=3, column=0, sticky=tk.W, pady=(6, 0))
        category_options = gui_category_options()
        self.categorias_listbox = tk.Listbox(
            config,
            selectmode=tk.MULTIPLE,
            exportselection=False,
            height=6,
            width=34,
        )
        self.categorias_listbox.grid(row=3, column=1, sticky=tk.W, padx=(8, 0), pady=(6, 0))
        for option in category_options:
            self.categorias_listbox.insert(tk.END, option)

        default_categories = resolve_category_filters(self.settings.offers_categoria_filter)
        if default_categories:
            for idx, option in enumerate(category_options):
                option_filters = resolve_category_filters(option)
                if option_filters and option_filters[0] in default_categories:
                    self.categorias_listbox.selection_set(idx)
        else:
            self.categorias_listbox.selection_set(0)

        ttk.Label(config, text="Categorias extras (virgula):").grid(row=4, column=0, sticky=tk.W, pady=(6, 0))
        self.categoria_extra_var = tk.StringVar(value="")
        ttk.Entry(config, textvariable=self.categoria_extra_var, width=34).grid(
            row=4,
            column=1,
            sticky=tk.W,
            padx=(8, 0),
            pady=(6, 0),
        )

        self.visual_browser_var = tk.BooleanVar(value=not self.settings.scraper_headless)
        ttk.Checkbutton(
            config,
            text="Abrir navegador visual (nao headless)",
            variable=self.visual_browser_var,
        ).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(8, 0))

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
        self.log_text.tag_configure("audit_aprovado", foreground="#0f7b0f")
        self.log_text.tag_configure("audit_filtrado", foreground="#b22222")

    def _setup_logging(self) -> None:
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s", "%H:%M:%S")

        self.logger = logging.getLogger("gui")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        for handler in list(self.logger.handlers):
            if getattr(handler, "_gui_queue_handler", False):
                self.logger.removeHandler(handler)

        self._attach_queue_handler(self.logger, formatter)
        # Logs de "scraperofertas.scraper" propagam para "scraperofertas" (sem duplicar no painel).
        for logger_name in ("scraperofertas", "scheduler"):
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.INFO)
            self._attach_queue_handler(logger, formatter)

    def _attach_queue_handler(self, logger: logging.Logger, formatter: logging.Formatter) -> None:
        for existing in logger.handlers:
            if getattr(existing, "_gui_queue_handler", False):
                return
        handler = QueueLogHandler(self.log_queue)
        handler._gui_queue_handler = True  # type: ignore[attr-defined]
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def _show_info_async(self, title: str, message: str) -> None:
        self.root.after(0, lambda t=title, m=message: messagebox.showinfo(t, m))

    def _show_warning_async(self, title: str, message: str) -> None:
        self.root.after(0, lambda t=title, m=message: messagebox.showwarning(t, m))

    def _show_error_async(self, title: str, message: str) -> None:
        self.root.after(0, lambda t=title, m=message: messagebox.showerror(t, m))

    def _process_log_queue(self) -> None:
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.config(state="normal")
                tag: str | None = None
                if "Relatorio auditoria | Aprovado |" in message:
                    tag = "audit_aprovado"
                elif "Relatorio auditoria | Filtrado |" in message:
                    tag = "audit_filtrado"

                if tag:
                    self.log_text.insert(tk.END, message + "\n", tag)
                else:
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

    def _parse_offer_filters(self) -> tuple[int, int]:
        min_desconto_raw = self.min_desconto_var.get().strip()
        min_comissao_raw = self.min_comissao_var.get().strip()

        min_desconto = self.settings.offers_min_desconto_percent if not min_desconto_raw else int(min_desconto_raw)
        min_comissao = self.settings.offers_min_comissao_percent if not min_comissao_raw else int(min_comissao_raw)

        if min_desconto < 0:
            raise ValueError("min desconto precisa ser maior ou igual a zero")
        if min_comissao < 0:
            raise ValueError("min comissao precisa ser maior ou igual a zero")

        return min_desconto, min_comissao

    def _parse_category_filters(self) -> list[str]:
        selected_values = [self.categorias_listbox.get(idx) for idx in self.categorias_listbox.curselection()]
        extras = self.categoria_extra_var.get().strip()
        raw_values = list(selected_values)
        if extras:
            raw_values.append(extras)
        return resolve_category_filters(raw_values)

    def _parse_headless_mode(self) -> bool:
        return not bool(self.visual_browser_var.get())

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
                self._show_info_async("Sucesso", "Login atualizado com sucesso.")
            else:
                self.logger.warning("Login nao confirmado.")
                self._show_warning_async("Aviso", "Login nao confirmado.")
        except Exception as exc:
            error_msg = f"Falha ao atualizar login: {exc}"
            self.logger.error(error_msg)
            self._show_error_async("Erro", error_msg)
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
            min_desconto, min_comissao = self._parse_offer_filters()
            category_filters = self._parse_category_filters()
            headless = self._parse_headless_mode()
        except ValueError as exc:
            messagebox.showerror("Erro", str(exc))
            return

        categories_label = ", ".join(category_filters) if category_filters else "todas"
        filtros_msg = (
            f"Filtros: desconto>={min_desconto}% | comissao>={min_comissao}% | categoria={categories_label}"
            if scraper_type in {"ofertas", "ofertas_relampago", "todos"}
            else "Filtros de desconto/comissao nao se aplicam a cupons"
        )
        confirm = messagebox.askyesno(
            "Confirmar",
            "Executar "
            f"'{scraper_type}' com max {max_items} itens?\n{filtros_msg}\n"
            f"Navegador visual: {'sim' if not headless else 'nao'}\n"
            "A interface continuara responsiva.",
        )
        if not confirm:
            return

        self.is_running = True
        self._set_buttons_state(False)
        self.update_status(f"Executando {scraper_type}...")
        category_filter_payload = category_filters or None
        threading.Thread(
            target=self._run_job_worker,
            args=(scraper_type, max_items, min_desconto, min_comissao, category_filter_payload, headless),
            daemon=True,
        ).start()

    def _run_job_worker(
        self,
        scraper_type: str,
        max_items: int,
        min_desconto: int,
        min_comissao: int,
        category_filters: list[str] | None,
        headless: bool,
    ) -> None:
        try:
            categories_label = ", ".join(category_filters) if category_filters else "todas"
            self.logger.info(
                "Iniciando tarefa: "
                f"{scraper_type} max_items={max_items} min_desconto={min_desconto} "
                f"min_comissao={min_comissao} categoria={categories_label} "
                f"headless={headless}"
            )
            if scraper_type == "cupons":
                self.logger.info("Filtros de desconto/comissao/categoria nao se aplicam a cupons")

            async def run_async():
                async with build_container(self.settings) as container:
                    if scraper_type == "todos":
                        return await run_jobs_in_sequence(
                            job_use_case=container.job_use_case,
                            engine_factory=lambda: container.engine_factory(
                                headless=headless,
                                max_produtos=max_items,
                            ),
                            max_items=max_items,
                            timeout_seconds=self.settings.scheduler_job_timeout_seconds,
                            min_desconto_percent=min_desconto,
                            min_comissao_percent=min_comissao,
                            category_filter=category_filters,
                        )

                    async with container.engine_factory(headless=headless, max_produtos=max_items) as engine:
                        return await container.job_use_case.execute(
                            scraper_type=scraper_type,
                            max_items=max_items,
                            engine=engine,
                            min_desconto_percent=min_desconto,
                            min_comissao_percent=min_comissao,
                            category_filter=category_filters,
                        )

            result = asyncio.run(run_async())

            if scraper_type == "todos":
                cupons_novos = result.cupons.novos if result.cupons is not None else 0
                self.logger.info(
                    "Execucao concluida | "
                    f"ofertas_novos={result.ofertas.novos} "
                    f"relampago_novos={result.ofertas_relampago.novos} "
                    f"cupons_novos={cupons_novos} "
                    f"ofertas_filtrados={result.ofertas.filtrados} "
                    f"relampago_filtrados={result.ofertas_relampago.filtrados}"
                )
                self._show_info_async(
                    "Sucesso",
                    "Executar Todos finalizado.\n"
                    f"Ofertas novos: {result.ofertas.novos}\n"
                    f"Ofertas filtrados: {result.ofertas.filtrados}\n"
                    f"Relampago novos: {result.ofertas_relampago.novos}\n"
                    f"Relampago filtrados: {result.ofertas_relampago.filtrados}\n"
                    f"Cupons novos: {cupons_novos}",
                )
            else:
                self.logger.info(
                    "Execucao concluida | "
                    f"scraper={scraper_type} novos={result.novos} existentes={result.existentes} "
                    f"filtrados={result.filtrados} erros={result.erros}"
                )
                self._show_info_async(
                    "Sucesso",
                    f"Tarefa {scraper_type} finalizada.\n"
                    f"Novos: {result.novos}\n"
                    f"Existentes: {result.existentes}\n"
                    f"Filtrados: {result.filtrados}\n"
                    f"Erros: {result.erros}",
                )
        except Exception as exc:
            error_msg = f"Falha na tarefa {scraper_type}: {exc}"
            self.logger.error(error_msg)
            self._show_error_async("Erro", error_msg)
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
