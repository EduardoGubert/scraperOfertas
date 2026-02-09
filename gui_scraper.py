"""
GUI Scraper ML Ofertas - egnOfertas
Interface gráfica para o scraper do Mercado Livre
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import asyncio
import logging
import sys
from io import StringIO
from datetime import datetime
import os

# Importa os módulos do projeto
try:
    from scraper_ml_afiliado import ScraperMLAfiliado
    from pipeline import ScrapingPipeline
except ImportError as e:
    messagebox.showerror("Erro de Importação", 
                        f"Não foi possível importar os módulos necessários:\n{e}\n\n"
                        f"Certifique-se de que está executando na pasta correta.")
    sys.exit(1)


class TextHandler(logging.Handler):
    """Handler personalizado para redirecionar logs para o widget Text"""
    
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        
    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.config(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.see(tk.END)
            self.text_widget.config(state='disabled')
            self.text_widget.update()
        # Executa na thread principal
        self.text_widget.after(0, append)


class StdoutRedirect:
    """Redireciona stdout para o widget Text"""
    
    def __init__(self, text_widget):
        self.text_widget = text_widget
        
    def write(self, s):
        if s.strip():  # Só escreve se não for string vazia
            def append():
                self.text_widget.config(state='normal')
                self.text_widget.insert(tk.END, s)
                self.text_widget.see(tk.END)
                self.text_widget.config(state='disabled')
                self.text_widget.update()
            self.text_widget.after(0, append)
            
    def flush(self):
        pass


class ScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Scraper ML Ofertas - egnOfertas")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Variáveis de controle
        self.is_running = False
        self.scraper = None
        
        # Configura a interface
        self.setup_ui()
        self.setup_logging()
        
        # Redireciona stdout
        self.stdout_redirect = StdoutRedirect(self.log_text)
        sys.stdout = self.stdout_redirect
        
        # Status inicial
        self.update_status("Pronto para iniciar")
        self.log("🚀 Interface iniciada - Scraper ML Ofertas")
        
    def setup_ui(self):
        """Cria a interface do usuário"""
        
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Título
        title_label = ttk.Label(main_frame, text="Scraper ML Ofertas - egnOfertas", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Frame de configurações
        config_frame = ttk.LabelFrame(main_frame, text="Configurações", padding="10")
        config_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Campo para número de produtos
        ttk.Label(config_frame, text="Número de produtos:").grid(row=0, column=0, sticky=tk.W)
        self.produtos_var = tk.StringVar(value="20")
        produtos_entry = ttk.Entry(config_frame, textvariable=self.produtos_var, width=10)
        produtos_entry.grid(row=0, column=1, padx=(10, 0), sticky=tk.W)
        
        # Frame de botões
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=2, column=0, columnspan=3, pady=(0, 10))
        
        # Botão Atualizar Login
        self.login_btn = ttk.Button(buttons_frame, text="Atualizar Login", 
                                   command=self.atualizar_login, width=15)
        self.login_btn.grid(row=0, column=0, padx=(0, 10))
        
        # Botão Iniciar Scraping
        self.scraping_btn = ttk.Button(buttons_frame, text="Iniciar Scraping", 
                                      command=self.iniciar_scraping, width=15)
        self.scraping_btn.grid(row=0, column=1)
        
        # Status label
        self.status_var = tk.StringVar(value="Pronto")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, 
                               font=('Arial', 10, 'bold'))
        status_label.grid(row=3, column=0, columnspan=3, pady=(0, 10))
        
        # Área de log
        log_frame = ttk.LabelFrame(main_frame, text="Log de Atividades", padding="5")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Configura redimensionamento
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(4, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)
        
        # Text widget para logs
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, wrap=tk.WORD, 
                                                 state='disabled', font=('Consolas', 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Frame de informações
        info_frame = ttk.Frame(main_frame)
        info_frame.grid(row=5, column=0, columnspan=3, pady=(10, 0))
        
        ttk.Label(info_frame, text="Desenvolvido por Eduardo - egnOfertas", 
                 font=('Arial', 8)).grid(row=0, column=0, columnspan=3)
        
    def setup_logging(self):
        """Configura o sistema de logging"""
        # Remove handlers existentes
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        # Configura novo handler
        self.text_handler = TextHandler(self.log_text)
        self.text_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                            datefmt='%H:%M:%S')
        )
        
        logging.basicConfig(level=logging.INFO, handlers=[self.text_handler])
        
    def log(self, message):
        """Adiciona mensagem ao log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}"
        
        def append():
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, formatted_msg + '\n')
            self.log_text.see(tk.END)
            self.log_text.config(state='disabled')
            self.log_text.update()
        
        self.log_text.after(0, append)
        
    def update_status(self, status):
        """Atualiza o status na interface"""
        self.status_var.set(f"Status: {status}")
        self.root.update()
        
    def disable_buttons(self):
        """Desabilita os botões durante operações"""
        self.login_btn.config(state='disabled')
        self.scraping_btn.config(state='disabled')
        
    def enable_buttons(self):
        """Habilita os botões após operações"""
        self.login_btn.config(state='normal')
        self.scraping_btn.config(state='normal')
        
    def atualizar_login(self):
        """Executa o processo de login em thread separada"""
        if self.is_running:
            messagebox.showwarning("Aviso", "Uma operação já está em andamento!")
            return
            
        # Valida se está na pasta correta (verifica se existe arquivo indicativo)
        if not os.path.exists("scraper_ml_afiliado.py"):
            messagebox.showerror("Erro", "Execute o programa na pasta correta do projeto!")
            return
            
        self.disable_buttons()
        self.update_status("Fazendo login...")
        self.log("🔑 Iniciando processo de login...")
        
        threading.Thread(target=self._run_login, daemon=True).start()
        
    def _run_login(self):
        """Executa o login de forma assíncrona"""
        try:
            self.is_running = True
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def login_process():
                scraper = ScraperMLAfiliado()
                await scraper.fazer_login_manual()
                
            loop.run_until_complete(login_process())
            
            # Atualiza interface na thread principal
            self.root.after(0, lambda: self._login_success())
            
        except Exception as e:
            self.root.after(0, lambda: self._login_error(str(e)))
        finally:
            self.is_running = False
            
    def _login_success(self):
        """Callback para login bem-sucedido"""
        self.update_status("Login concluído com sucesso")
        self.log("✅ Login realizado com sucesso!")
        self.enable_buttons()
        
    def _login_error(self, error_msg):
        """Callback para erro no login"""
        self.update_status("Erro no login")
        self.log(f"❌ Erro no login: {error_msg}")
        messagebox.showerror("Erro no Login", f"Falha ao fazer login:\n{error_msg}")
        self.enable_buttons()
        
    def iniciar_scraping(self):
        """Inicia o processo de scraping"""
        if self.is_running:
            messagebox.showwarning("Aviso", "Uma operação já está em andamento!")
            return
            
        # Valida número de produtos
        try:
            max_produtos = int(self.produtos_var.get())
            if max_produtos <= 0:
                raise ValueError("Número deve ser maior que zero")
        except ValueError:
            messagebox.showerror("Erro", "Digite um número válido de produtos (maior que 0)!")
            return
            
        # Confirma ação
        if not messagebox.askyesno("Confirmar", 
                                  f"Iniciar scraping de {max_produtos} produtos?\n"
                                  f"Esta operação pode demorar alguns minutos."):
            return
            
        self.disable_buttons()
        self.update_status("Executando scraping...")
        self.log(f"🚀 Iniciando scraping de {max_produtos} produtos...")
        
        threading.Thread(target=self._run_scraping, args=(max_produtos,), daemon=True).start()
        
    def _run_scraping(self, max_produtos):
        """Executa o scraping completo"""
        try:
            self.is_running = True
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def scraping_process():
                async with ScrapingPipeline() as pipeline:
                    stats = await pipeline.processar_produtos(max_produtos)
                return stats
                
            stats = loop.run_until_complete(scraping_process())
            
            # Atualiza interface na thread principal
            self.root.after(0, lambda: self._scraping_success(stats))
            
        except Exception as e:
            self.root.after(0, lambda: self._scraping_error(str(e)))
        finally:
            self.is_running = False
            
    def _scraping_success(self, stats):
        """Callback para scraping bem-sucedido"""
        self.update_status("Scraping concluído")
        self.log(f"🎉 Scraping concluído com sucesso!")
        self.log(f"📊 Resultados: {stats['novos']} novos | {stats['existentes']} existentes | {stats['erros']} erros")
        
        messagebox.showinfo("Sucesso!", 
                          f"Scraping concluído!\n\n"
                          f"Novos produtos: {stats['novos']}\n"
                          f"Já existentes: {stats['existentes']}\n"
                          f"Erros: {stats['erros']}")
        self.enable_buttons()
        
    def _scraping_error(self, error_msg):
        """Callback para erro no scraping"""
        self.update_status("Erro no scraping")
        self.log(f"❌ Erro no scraping: {error_msg}")
        messagebox.showerror("Erro no Scraping", f"Falha no scraping:\n{error_msg}")
        self.enable_buttons()
        
    def on_closing(self):
        """Função chamada ao fechar a janela"""
        if self.is_running:
            if not messagebox.askyesno("Confirmar", "Uma operação está em andamento. Deseja mesmo fechar?"):
                return
                
        self.log("👋 Encerrando aplicação...")
        self.root.destroy()


def main():
    """Função principal"""
    # Verifica se está na pasta correta
    if not os.path.exists("scraper_ml_afiliado.py"):
        messagebox.showerror("Erro", 
                           "Execute este programa na pasta do projeto!\n"
                           "A pasta deve conter os arquivos:\n"
                           "- scraper_ml_afiliado.py\n"
                           "- pipeline.py\n"
                           "- database.py")
        return
        
    root = tk.Tk()
    app = ScraperGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()