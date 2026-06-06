import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import threading
import config
import creator


def _add_paste_menu(entry: ttk.Entry):
    menu = tk.Menu(entry, tearoff=0)
    menu.add_command(label="Вырезать",   command=lambda: entry.event_generate("<<Cut>>"))
    menu.add_command(label="Копировать", command=lambda: entry.event_generate("<<Copy>>"))
    menu.add_command(label="Вставить",   command=lambda: entry.event_generate("<<Paste>>"))
    menu.add_separator()
    menu.add_command(label="Выделить всё", command=lambda: entry.select_range(0, "end"))
    entry.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GetCourse — Автосоздание дашборда")
        self.resizable(False, False)
        self.cfg = config.load()
        self._build_ui()

    def _build_ui(self):
        pad = dict(padx=12)

        frm_acc = ttk.LabelFrame(self, text="Аккаунт GetCourse")
        frm_acc.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        self._field(frm_acc, "URL аккаунта", "gc_url", 0,
                    placeholder="https://myschool.getcourse.ru")
        self._field(frm_acc, "E-mail", "gc_email", 1)
        self._field(frm_acc, "Пароль", "gc_password", 2, show="*")

        frm_web = ttk.LabelFrame(self, text="Параметры вебинара")
        frm_web.grid(row=1, column=0, sticky="ew", padx=12, pady=4)

        ttk.Label(frm_web, text="Тег вебинара").grid(row=0, column=0, sticky="w", **pad)
        self.tag_var = tk.StringVar()
        _e = ttk.Entry(frm_web, textvariable=self.tag_var, width=35)
        _e.grid(row=0, column=1, sticky="ew", **pad)
        _add_paste_menu(_e)
        ttk.Label(frm_web, text="например: zero-luxury-8",
                  foreground="grey").grid(row=0, column=2, sticky="w")

        ttk.Label(frm_web, text="Дата вебинара").grid(row=1, column=0, sticky="w", **pad)
        self.date_var = tk.StringVar()
        _e = ttk.Entry(frm_web, textvariable=self.date_var, width=20)
        _e.grid(row=1, column=1, sticky="w", **pad)
        _add_paste_menu(_e)
        ttk.Label(frm_web, text="ДД.ММ.ГГГГ", foreground="grey").grid(
            row=1, column=2, sticky="w")

        ttk.Label(frm_web, text="Предложение").grid(row=2, column=0, sticky="w", **pad)
        self.offer_var = tk.StringVar()
        _e = ttk.Entry(frm_web, textvariable=self.offer_var, width=45)
        _e.grid(row=2, column=1, columnspan=2, sticky="ew", **pad)
        _add_paste_menu(_e)
        ttk.Label(frm_web, text="например: [zero-luxury-8] Платное участие — 499 руб.",
                  foreground="grey").grid(row=3, column=1, columnspan=2, sticky="w", padx=12)

        ttk.Label(frm_web, text="Спикер (utm_medium)").grid(row=4, column=0, sticky="w", **pad)
        self.speaker_var = tk.StringVar()
        _e = ttk.Entry(frm_web, textvariable=self.speaker_var, width=35)
        _e.grid(row=4, column=1, sticky="ew", **pad)
        _add_paste_menu(_e)

        ttk.Label(frm_web, text="Telegram-бот").grid(row=5, column=0, sticky="w", **pad)
        self.tgbot_var = tk.StringVar(value=self.cfg.get("tg_bot", "zerocoder_university_bot"))
        _e = ttk.Entry(frm_web, textvariable=self.tgbot_var, width=35)
        _e.grid(row=5, column=1, sticky="ew", **pad)
        _add_paste_menu(_e)

        frm_btn = ttk.Frame(self)
        frm_btn.grid(row=2, column=0, sticky="ew", padx=12, pady=8)

        self.diag_btn = ttk.Button(
            frm_btn, text="Разведка формы", command=self._run_diagnostic)
        self.diag_btn.pack(side="left")

        self.run_btn = ttk.Button(
            frm_btn, text="Создать дашборд", command=self._run)
        self.run_btn.pack(side="left", padx=8)

        ttk.Button(frm_btn, text="Сохранить настройки",
                   command=self._save_cfg).pack(side="left")

        frm_log = ttk.LabelFrame(self, text="Лог")
        frm_log.grid(row=3, column=0, sticky="nsew", padx=12, pady=(4, 12))
        self.log_text = tk.Text(
            frm_log, height=12, width=72, state="disabled",
            bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)

    def _field(self, parent, label, cfg_key, row, placeholder="", show=""):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=12, pady=5)
        var = tk.StringVar(value=self.cfg.get(cfg_key, ""))
        setattr(self, f"{cfg_key}_var", var)
        kw = {"show": show} if show else {}
        e = ttk.Entry(parent, textvariable=var, width=45, **kw)
        e.grid(row=row, column=1, sticky="ew", padx=12, pady=5)
        _add_paste_menu(e)
        if placeholder:
            ttk.Label(parent, text=placeholder, foreground="grey").grid(
                row=row, column=2, sticky="w")

    def _log(self, msg: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _save_cfg(self):
        self.cfg.update({
            "gc_url": self.gc_url_var.get().rstrip("/"),
            "gc_email": self.gc_email_var.get(),
            "gc_password": self.gc_password_var.get(),
            "tg_bot": self.tgbot_var.get(),
        })
        config.save(self.cfg)
        messagebox.showinfo("Сохранено", "Настройки сохранены.")

    def _validate_account(self):
        errors = []
        if not self.gc_url_var.get():
            errors.append("Введите URL аккаунта")
        if not self.gc_email_var.get():
            errors.append("Введите e-mail")
        if not self.gc_password_var.get():
            errors.append("Введите пароль")
        return errors

    def _validate_webinar(self):
        errors = self._validate_account()
        if not self.tag_var.get():
            errors.append("Введите тег вебинара")
        if not self.date_var.get():
            errors.append("Введите дату вебинара")
        else:
            try:
                datetime.strptime(self.date_var.get(), "%d.%m.%Y")
            except ValueError:
                errors.append("Дата вебинара: формат ДД.ММ.ГГГГ")
        if not self.offer_var.get():
            errors.append("Введите название предложения")
        if not self.speaker_var.get():
            errors.append("Введите utm_medium спикера")
        return errors

    def _set_buttons(self, state):
        self.run_btn.state([state])
        self.diag_btn.state([state])

    def _run_diagnostic(self):
        errors = self._validate_account()
        if errors:
            messagebox.showerror("Ошибка", "\n".join(errors))
            return
        self._set_buttons("disabled")
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

        def task():
            try:
                creator.run_diagnostic(
                    gc_url=self.gc_url_var.get().rstrip("/"),
                    email=self.gc_email_var.get(),
                    password=self.gc_password_var.get(),
                    log_fn=lambda msg: self.after(0, self._log, msg),
                )
            except Exception as e:
                self.after(0, self._log, f"✗ {e}")
            finally:
                self.after(0, lambda: self._set_buttons("!disabled"))

        threading.Thread(target=task, daemon=True).start()

    def _run(self):
        errors = self._validate_webinar()
        if errors:
            messagebox.showerror("Ошибка", "\n".join(errors))
            return
        self._set_buttons("disabled")
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

        webinar_date = datetime.strptime(self.date_var.get(), "%d.%m.%Y")

        def task():
            try:
                creator.run(
                    gc_url=self.gc_url_var.get().rstrip("/"),
                    email=self.gc_email_var.get(),
                    password=self.gc_password_var.get(),
                    tag=self.tag_var.get().strip(),
                    webinar_date=webinar_date,
                    offer_name=self.offer_var.get().strip(),
                    speaker_utm=self.speaker_var.get().strip(),
                    tg_bot=self.tgbot_var.get().strip(),
                    log_fn=lambda msg: self.after(0, self._log, msg),
                    ready_fn=lambda: self.after(0, lambda: self._set_buttons("!disabled")),
                )
            except Exception as e:
                self.after(0, self._log, f"✗ {e}")
                self.after(0, lambda: self._set_buttons("!disabled"))

        threading.Thread(target=task, daemon=True).start()


if __name__ == "__main__":
    app = App()
    app.mainloop()
