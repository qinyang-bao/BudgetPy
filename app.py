import os
from json import dumps
from tkinter import *
from tkinter import messagebox, simpledialog, filedialog
from PIL import Image, ImageTk
from datetime import datetime, timedelta
from dbManager import DBManager, __date_format__
from commands import CommandFactory, Command, EnterRecord, JumpToDate, JumpToMonth


class App(object):
    date_formats = None
    path = {
        "images": os.path.join(os.path.dirname(os.path.realpath(__file__)), "images"),
        "budgets": os.path.join(os.path.dirname(os.path.realpath(__file__)), "budgets"),
    }

    def __init__(self, logger, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.num_records_displayed = int(os.environ.get("RECORDS_DISPLAYED"))
        os.makedirs(App.path['budgets'], exist_ok=True)

        self.dm = DBManager(logger)
        self.cf = CommandFactory(self)
        self.logger = logger

        self.window = Tk()
        self.window.resizable(0, 0)  # disable resizing

        self.init_menu()

        # create frames
        self.create_record_frame = Frame(self.window, bg="white", highlightbackground="black", highlightcolor="black",
                                         highlightthickness=1, pady=10, padx=10)
        self.create_record_frame.pack(side=TOP, fill="x")

        self.view_record_frame_1 = Frame(self.window, bg="white", pady=10, padx=10)
        self.view_record_frame_1.pack(fill="x")

        self.view_record_frame_2 = Frame(self.window, bg="white", pady=0, padx=10)
        self.view_record_frame_2.pack(fill="x")

        self.view_record_frame_3 = Frame(self.window, bg="white", pady=10, padx=10)
        self.view_record_frame_3.pack(fill="x")

        # input fields for creating a new record
        Label(self.create_record_frame, text="Enter a new withdraw record:", fg="black", bg="white").grid(row=0, sticky=W)

        self.new_record_date, self.new_record_reason, self.new_record_amount = StringVar(), StringVar(), StringVar()

        Label(self.create_record_frame, text="Date(yy-mm-dd)", fg="black", bg="white").grid(row=1, column=0, sticky=W)
        Entry(self.create_record_frame, textvariable=self.new_record_date).grid(row=1, column=1)
        self.new_record_date.set(self.get_today_date())

        Label(self.create_record_frame, text="Reason", fg="black", bg="white").grid(row=2, column=0, sticky=W)
        Entry(self.create_record_frame, textvariable=self.new_record_reason).grid(row=2, column=1)

        Label(self.create_record_frame, text="Amount", fg="black", bg="white").grid(row=3, column=0, sticky=W)
        Entry(self.create_record_frame, textvariable=self.new_record_amount).grid(row=3, column=1)

        Button(self.create_record_frame, text="Enter", command=self.enter_record).grid(row=4, column=0, sticky=W)

        # operations for viewing records
        self.view_record_month, self.view_record_date = StringVar(), StringVar()
        self._current_first_record_id = 0

        Label(self.view_record_frame_1, text="Enter month to jump to (yy-mm):", fg="black", bg="white")\
            .grid(row=0, sticky=W)
        Entry(self.view_record_frame_1, textvariable=self.view_record_month).grid(row=0, column=1)
        Button(self.view_record_frame_1, text="Enter", command=self.jump_to_month).grid(row=0, column=2)

        Label(self.view_record_frame_1, text="Enter date to jump to (yy-mm-dd):", fg="black", bg="white")\
            .grid(row=1, sticky=W)
        Entry(self.view_record_frame_1, textvariable=self.view_record_date).grid(row=1, column=1)
        Button(self.view_record_frame_1, text="Enter", command=self.jump_to_date).grid(row=1, column=2)

        self.add_button_image("double_prev.png", self.jump_to_prev_records, self.view_record_frame_2, 2, 0)
        self.add_button_image("prev.png", self.jump_to_prev_record, self.view_record_frame_2, 2, 1)
        self.add_button_image("next.png", self.jump_to_next_record, self.view_record_frame_2, 2, 2)
        self.add_button_image("double_next.png", self.jump_to_next_records, self.view_record_frame_2, 2, 3)

        # records for view
        self.reload_records()

        # create a budget file if none exists
        self._create_budget_file(self.dm.__table__)

    def init_menu(self):
        window = self.window

        # creating a root menu to insert all the sub menus
        root_menu = Menu(window)
        window.config(menu=root_menu)

        # creating the file submenu, used to import and export and create new budget sheet
        file_menu = Menu(root_menu)
        root_menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Budget (Ctrl-n)", command=self.create_new_budget)
        file_menu.add_command(label="Open Budget (Ctrl-o)", command=self.open_budget)
        file_menu.add_command(label="Export as Excel (Ctrl-e)", command=self.export_budget_as_excel)
        file_menu.add_separator()
        file_menu.add_command(label="Exit (Ctrl-q)", command=window.quit)

        # creating the edit sub menu, used for undo and redo a record
        edit_menu = Menu(root_menu)
        root_menu.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo (Ctrl-z)", command=Command.undo)
        edit_menu.add_command(label="Redo (Ctrl-y)", command=Command.redo)

        # add shortcuts
        shortcuts = {
            "<Control-n>": lambda eve: self.create_new_budget(),
            "<Control-o>": lambda eve: self.open_budget(),
            "<Control-e>": lambda eve: self.export_budget_as_excel(),
            "<Control-q>": lambda eve: self.window.quit(),
            "<Control-z>": lambda eve: Command.undo(),
            "<Control-y>": lambda eve: Command.redo(),
        }

        for shortcut in shortcuts:
            self.window.bind(shortcut, shortcuts[shortcut])

    def create_new_budget(self):
        filename = simpledialog.askstring("Input", "Please enter name of the new budget", parent=self.window)
        if filename:
            filename = os.path.splitext(filename)[0]
            self.dm.set_table_in_use(filename)
            self._create_budget_file(filename)

            self.reload_records()

    def open_budget(self):
        filepath = filedialog.askopenfilename(initialdir=App.path['budgets'], title="Select budget",
                                              filetypes=(("BudgetPy files", "*.bp"), ("Excel files", "*.xlsx")))
        if filepath:
            filename = os.path.splitext(os.path.split(filepath)[1])[0]
            if os.path.splitext(filepath)[1] == '.xlsx':
                self.dm.excel_to_db(filepath)
            elif os.path.splitext(filepath)[1] == '.bp':
                self.dm.set_table_in_use(filename)

            self._create_budget_file(filename)

            self.reload_records()

    def export_budget_as_excel(self):
        self.dm.db_to_excel()
        messagebox.showinfo("Info", "Export Complete!")

    def _create_budget_file(self, name):
        path = os.path.join(App.path['budgets'], "{}.bp".format(name))
        if not os.path.exists(path):
            with open(path, "w") as f:
                d = {"db": self.dm.__db_name__,
                     "table_name": name}
                f.write(dumps(d))

    @staticmethod
    def add_button_image(image_name, command, frame, row, column, size=(15, 15)):
        image = ImageTk.PhotoImage(Image.open(os.path.join(App.path['images'], image_name)).resize(size))
        btn = Button(frame, image=image, command=command)
        btn.image = image  # stupid tkinter needs to keep a reference to the photo object, else nothing would should up
        btn.grid(row=row, column=column, sticky=W)

    def reload_records(self):
        self.window.title("BudgetPy-{}".format(self.dm.__table__))
        self.init_record_viewing_date()
        self.init_record_viewing_records()

    def init_record_viewing_date(self):
        if self.dm.get_num_records() > 0:
            default_date = self.dm.get_last_date()
        else:
            default_date = datetime.today().strftime(__date_format__)
        default_month = "-".join(default_date.split("-")[:-1])
        self.view_record_month.set(default_month)
        self.view_record_date.set(default_date)

    # make sure to call this function after you have called "init_record_viewing_date"
    def init_record_viewing_records(self):
        if self.dm.get_num_records() > 0:
            self._jump_to_date()
        else:
            # if there is no records, just use empty dummy records
            for widget in self.view_record_frame_3.winfo_children():
                widget.destroy()

            self.display_empty_records(self.num_records_displayed, 0)

            Label(self.view_record_frame_3, text="Total: {:.2f}".format(0), fg="black", bg="white", borderwidth=2,
                  relief="ridge").grid(row=self.num_records_displayed, pady=5, sticky=W)

            Label(self.view_record_frame_3, text="Monthly Total: {:.2f}".format(0), fg="black", bg="white",
                  borderwidth=2, relief="ridge").grid(row=self.num_records_displayed, column=1, pady=5, sticky=W)

    def jump_to_prev_records(self, num_record=None):
        num_record = num_record if num_record else self.num_records_displayed
        self.jump_to_id(self._current_first_record_id - num_record)

    def jump_to_prev_record(self):
        self.jump_to_id(self._current_first_record_id - 1)

    def jump_to_next_record(self):
        self.jump_to_id(self._current_first_record_id + 1)

    def jump_to_next_records(self, num_record=None):
        num_record = num_record if num_record else self.num_records_displayed
        self.jump_to_id(self._current_first_record_id + num_record)

    def jump_to_id(self, id, num_record=None):
        num_record = num_record if num_record else self.num_records_displayed
        if self.dm.get_num_records() < 1:
            self.alert("There is nothing in this budget!")
            return
        try:
            records = self.dm.get_records_after_id(id, num_record)
            self._current_first_record_id = int(records[0][0])
            self.display_records(records)
        except ValueError as e:
            self.alert("Date out of range! Records exhausted!")
            self.logger.error(str(e))

    def jump_to_month(self):
        self._execute_command(JumpToMonth)

    def _jump_to_month(self, num_record=None):
        num_record = num_record if num_record else self.num_records_displayed

        try:
            self.view_record_date.set(self.year_month_to_date(self.view_record_month.get()))
            self._jump_to_date(num_record)

        except ValueError as e:
            self.alert(str(e))

    def jump_to_date(self):
        self._execute_command(JumpToDate)

    def _jump_to_date(self, num_record=None):
        if self.dm.get_num_records() == 0:
            return

        num_record = num_record if num_record else self.num_records_displayed
        try:
            date = datetime.strptime(self._convert_date(self.view_record_date.get()), __date_format__)
            first_valid_date = None
            first_recorded_date = datetime.strptime(self.dm.get_first_date(), __date_format__)

            records = self.dm.get_withdraw(date)
            records = records if records else []
            while len(records) < num_record and date >= first_recorded_date:
                date -= timedelta(days=1)
                more_records = self.dm.get_withdraw(date)
                if more_records:
                    records += more_records

                    if not first_valid_date:
                        first_valid_date = date
                        self.view_record_month.set(self._trim_day(date.strftime(__date_format__)))

            self._current_first_record_id = int(records[0][0])

            self.display_records(records)

        except ValueError as e:
            self.alert(str(e))

    def display_records(self, records):
        for widget in self.view_record_frame_3.winfo_children():
            widget.destroy()

        total = 0
        for index, record in enumerate(records):
            Label(self.view_record_frame_3, text=record[1], fg="black", bg="white").grid(row=index, padx=5, sticky=W)
            Label(self.view_record_frame_3, text=record[2], fg="black", bg="white").grid(row=index, column=1, padx=5,
                                                                                         sticky=W)
            Label(self.view_record_frame_3, text=record[3], fg="black", bg="white").grid(row=index, column=2, padx=5,
                                                                                         sticky=W)
            total += float(record[3])

        self.display_empty_records(self.num_records_displayed - len(records), len(records))

        Label(self.view_record_frame_3, text="Total: {:.2f}".format(total), fg="black", bg="white", borderwidth=2,
              relief="ridge").grid(row=self.num_records_displayed, pady=5, sticky=W)

        date = datetime.strptime(records[0][1], __date_format__)
        Label(self.view_record_frame_3, text="Monthly Total: {:.2f}".format(self.dm.get_monthly_total(date)),
              fg="black", bg="white", borderwidth=2, relief="ridge")\
            .grid(row=self.num_records_displayed, column=1, pady=5, sticky=W)

    def display_empty_records(self, num, starting_row):
        for i in range(starting_row, starting_row+num):
            Label(self.view_record_frame_3, text="", fg="black", bg="white").grid(row=i, padx=5, sticky=W)
            Label(self.view_record_frame_3, text="", fg="black", bg="white").grid(row=i, column=1, padx=5, sticky=W)
            Label(self.view_record_frame_3, text="", fg="black", bg="white").grid(row=i, column=2, padx=5, sticky=W)

    def enter_record(self):
        self._execute_command(EnterRecord)

    def set_record_fields(self, date, reason, amount):
        self.new_record_date.set(date)
        self.new_record_reason.set(reason)
        self.new_record_amount.set(amount)
        self.reload_records()

    def _execute_command(self, command_class):
        try:
            c = self.cf.get_command(command_class)
            c.execute()
        except Exception as e:
            self.alert(str(e))

    @staticmethod
    def _get_date_formats():
        if not App.date_formats:
            year = ['%y', "%-y", "%Y"]
            month = ['%m', "%-m", "%b", "%B"]
            day = ['%d', "%-d"]
            date_formats = []
            for y in year:
                for m in month:
                    for d in day:
                        date_formats += [y + "-" + m + "-" + d]
            App.date_formats = date_formats
        return App.date_formats

    @staticmethod
    def _convert_date(date):
        '''
        :param date:
        :return: convert the given date string into the desired format
        '''
        for fmt in App._get_date_formats():
            try:
                return datetime.strptime(date, fmt).strftime(__date_format__)
            except ValueError:
                pass

        raise ValueError("{} is not a recognized date".format(date))

    @staticmethod
    def _convert_amount(amount):
        try:
            return float(amount)
        except ValueError:
            raise ValueError("{} is not a valid number".format(amount))

    @staticmethod
    def _convert_reason(reason):
        if reason != "":
            return reason
        raise ValueError("reason cannot be empty")

    @staticmethod
    def _trim_day(date):
        return "-".join(date.split("-")[:-1])

    @staticmethod
    def get_today_date():
        return datetime.today().strftime(__date_format__)

    @staticmethod
    def get_date_format():
        return __date_format__

    @staticmethod
    def _convert_year_month(year_month):
        '''
        :param year_month:
        :return: convert the given year_month string into the desired format
        '''
        try:
            date = App._convert_date(App.year_month_to_date(year_month))
            return App._trim_day(date)
        except ValueError:
            raise ValueError("{} is not a recognized year month".format(year_month))

    @staticmethod
    def year_month_to_date(year_month):
        if App.is_year_month(year_month):
            date = year_month + "-31"
            try:
                App._convert_date(date)
            except ValueError:
                date = year_month + "-30"
            return date
        else:
            raise ValueError("Month is in wrong format! Must be yy-mm")

    @staticmethod
    def is_year_month(year_month):
        try:
            App._convert_date(year_month+"-01")
            return True
        except ValueError:
            return False

    @staticmethod
    def alert(msg):
        messagebox.showinfo("Alert !", msg)

    def dummy(self):
        self.alert("clicked")

    def run(self):
        self.window.mainloop()


