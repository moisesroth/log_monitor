# info

> "log_monitor.py" monitor a log file, searching for some triggers and send them by e-mail.


# configuration

> some informations need to be set inside de code

 - log_dir           >>> this will define where app logs will be save
 - def get_config(): >>> follow examples on code to define triggers and thresholds
 - def send_mail():  >>> s = smtplib.SMTP('localhost',25), this adress need to be set for your mail server
 - def print_logs(): >>> if no mail needed, set "mail" parameter to False


# usage

on Linux:
```sh
nohup python log_monitor.py &
```

on Windows:
```sh
python log_monitor.py
```





 



