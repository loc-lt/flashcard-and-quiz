import datetime

class Systemp_log():
    def __init__(self,log_message,Name_error):
        self.log_message=log_message
        self.Name_error=Name_error
        self.file_name='log_'+datetime.datetime.now().strftime("%y_%m_%d")
    def append_new_line(self):
        """Append given text as a new line at the end of file"""
        # Open the file in append & read mode ('a+')
        with open(self.file_name, "a+") as file_object:
            # Move read cursor to the start of file.
            file_object.seek(0)
            # If file is not empty then append '\n'
            data = file_object.read(100)
            if len(data) > 0:
                file_object.write("\n")
            # Append text at the end of file
            file_object.writelines("-------------------Log----------------")
            file_object.write(datetime.datetime.now().strftime("%y/%m/%d-%H:%M:%S") + '\n')
            file_object.write(self.log_message+' ---- '+self.Name_error)