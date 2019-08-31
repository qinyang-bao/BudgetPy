from datetime import datetime, timedelta


class CommandFactory(object):
    factory = None

    def __init__(self, app, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = app

        if not CommandFactory.factory:
            CommandFactory.factory = self

    def get_command(self, command_class, *args, **kwargs):
        return command_class(app=self.app, *args, **kwargs)


class Command(object):
    history = []
    history_idx = 0

    def __init__(self, app, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = app

    def execute(self):
        # this happens when we call execute directly, instead of the redo method calling execute
        if self not in Command.history:
            # this means that whenever a new command is issued, we through away anything in the command history after
            # the command where the history idx is pointing to currently
            Command.history = Command.history[:Command.history_idx]
            Command.history.append(self)
            Command.history_idx += 1

    def unexecute(self):
        raise NotImplementedError

    @staticmethod
    def undo():
        if Command.history_idx > 0:
            Command.history[Command.history_idx-1].unexecute()  # minus one because idx is initialized to 0 while
            # history is empty, meaning it is actually one less than the actual index for the history list
            Command.history_idx -= 1

    @staticmethod
    def redo():
        if Command.history_idx < len(Command.history):
            Command.history_idx += 1
            Command.history[Command.history_idx-1].execute()

    @staticmethod
    def get_prev_command_of_type(command_class):
        idx = Command.history_idx - 1
        last_command = None
        while idx > 0:
            if isinstance(Command.history[idx-1], command_class):
                last_command = Command.history[idx-1]
                break
            idx -= 1
        return last_command


class EnterRecord(Command):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        app = self.app
        try:
            self.date = app._convert_date(app.new_record_date.get())
            self.reason = app._convert_reason(app.new_record_reason.get())
            self.amount = app._convert_amount(app.new_record_amount.get())
        except ValueError as e:
            raise ValueError(str(e))

    def execute(self):
        super().execute()

        app = self.app
        try:
            app.dm.insert_new_withdraw(self.date, self.reason, self.amount)
            app.set_record_fields(app.get_today_date(), "", "")
        except Exception as e:
            app.alert("Error while adding record to database: {}".format(str(e)))

    def unexecute(self):
        app = self.app
        last_command = Command.get_prev_command_of_type(EnterRecord)

        try:
            app.dm.delete_widthraw(self.date, self.reason, self.amount)
            if last_command:
                app.set_record_fields(last_command.date, last_command.reason, last_command.amount)
            else:
                app.set_record_fields(app.get_today_date(), "", "")
        except Exception as e:
            app.alert("Error while removing record from database: {}".format(str(e)))


class JumpToDate(Command):
    def __init__(self, num_record=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        app = self.app
        self.num_record = num_record if num_record else app.num_records_displayed

        try:
            self.date = app._convert_date(app.view_record_date.get())
        except ValueError as e:
            raise ValueError(str(e))

    def execute(self):
        super().execute()
        self.app.view_record_date.set(self.date)
        self.app._jump_to_date(self.num_record)

    def unexecute(self):
        last_command = Command.get_prev_command_of_type(JumpToDate)
        if last_command:
            self.app.view_record_date.set(last_command.date)
        else:
            self.app.view_record_date.set(self.app.dm.get_last_date())
        self.app._jump_to_date(self.num_record)


class JumpToMonth(Command):
    def __init__(self, num_record=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        app = self.app
        self.num_record = num_record if num_record else app.num_records_displayed

        try:
            self.year_month = app._convert_year_month(app.view_record_month.get())
        except ValueError as e:
            raise ValueError(str(e))

    def execute(self):
        super().execute()
        self.app.view_record_month.set(self.year_month)
        self.app._jump_to_month(self.num_record)

    def unexecute(self):
        last_command = Command.get_prev_command_of_type(JumpToMonth)
        if last_command:
            self.app.view_record_month.set(last_command.year_month)
        else:
            self.app.view_record_month.set(self.app._trim_day(self.app.dm.get_last_date()))
        self.app._jump_to_month(self.num_record)

