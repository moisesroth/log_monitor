# coding: UTF-8
import argparse
import logging
import os
import smtplib
import socket
import socket
import sys
import threading
import time
from email.MIMEText import MIMEText



# LOG CONFIGURATION
####################

log_dir = '/logs/' # change the directory as necessary. Aything below needs to be changed

script_name = str(os.path.basename(__file__))[:-3]
host_name = str((socket.gethostname()).split('.')[0])

log_type = 'app'
app = logging.getLogger(script_name+'_'+log_type)
app.setLevel(logging.INFO)
if not len(app.handlers):
    hdlr = logging.FileHandler(log_dir+script_name+'_'+host_name+'_'+log_type+'.log')
    formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(funcName)s(): %(message)s")
    hdlr.setFormatter(formatter)
    app.addHandler(hdlr)

log_type = 'alert'
alert = logging.getLogger(script_name+'_'+log_type)
alert.setLevel(logging.INFO)
if not len(alert.handlers):
    hdlr = logging.FileHandler(log_dir+script_name+'_'+host_name+'_'+log_type+'.log')
    formatter = logging.Formatter('%(asctime)s | %(message)s')#  u'[%(levelname)s]
    hdlr.setFormatter(formatter)
    alert.addHandler(hdlr)




# MONITOR CONFIGURATION
#######################
# I use "if" to validade the current host an apply the configuration
# this way we can use de same code at any servers. This configuration could be a separated file too.
def get_config(host_name):
    app.info('Identifying configurations for the host_name:: '+str(host_name))
    monitor_config = []
    # examples
    if 'serv-01' in host_name.lower():
        filename = '/logs/myapplication.log'
        monitor_config.append( { 'filename':filename,
                                 'triggers':['warning', 'error', 'exception'],
                                 'triggers_off':[],
                                 'tbr':120,
                                 'time_between_newline':87000} ) #24:10h

        filename = '/logs/nohup.log'
        monitor_config.append( { 'filename':filename,
                                 'triggers':['java.lang.OutOfMemoryError', 'warning', 'error', 'exception'],
                                 'triggers_off':['error to define', 'none of it was'],
                                 'tbr':120,
                                 'time_between_newline':600} ) # 00:10h

    if 'serv-02' in host_name.lower():
        filename = '/logs/app1.log'
        monitor_config.append( { 'filename':filename,
                                 'triggers':['warning', 'error', 'exception'],
                                 'triggers_off':['database is locked'],
                                 'time_between_newline':0} ) # 0 = disabled

    if len(monitor_config) == 0:
        app.warning('No configuration was set for this host_name: '+str(host_name))

    return monitor_config




# MAIL CONFIGURATION
####################
def mail_configuration(mail_from, mail_to, mail_cc, mail_cco, mail_subject, script_info, template):
    if mail_from == None or mail_to == None or mail_cc == None or mail_cco == None or mail_subject == None or script_info == None or template == None:
        app.warning('7 arguments are required to send an e-mail')
        print '\n>> 7 arguments are required!\n(mail_subject, mail_from, mail_to, mail_cc, mail_cco, script_info, template)'
    else:
        msg = MIMEText(template,'html')
        msg['Subject'] = mail_subject
        msg['From'] = mail_from
        msg['To'] = mail_to
        msg['CC'] = mail_cc

        s = smtplib.SMTP('correio.company.com.br',25)
        s.sendmail(mail_from, [mail_to, mail_cc, mail_cco], msg.as_string())
        s.quit()

def create_msg(script_info):
    server_name = str(script_info.get("script_server"))
    file_name = str(script_info.get("script_log_file"))
    alerts = str("<br>".join(script_info.get("script_log_info")))
    txt = '''
        <head>
        <title>Python Monitor Alert</title>
        <style type="text/css">
            li { margin-top: 0.5em; margin-bottom: 0.5em; }
            body { font-family: Georgia;}
        </style>
        </head>

        <body>
        <h1>Python Monitor</h1>
        <h3>'''+file_name+'''</h3>
        <table>
            <tr><td>Servidor</td><td>'''+server_name+'''</td></tr>
            <tr><td>Log File</td><td>'''+file_name+'''</td></tr>
            <tr><td valign="top">Log Info</td><td>'''+alerts+'''</td></tr>
        </table>
        </body>
    '''
    return txt

def send_mail(script_info, logger=app):
    logger.debug('runing..')
    txt = create_msg(script_info)
    mail_configuration(mail_from='python.monitor@company.com',
                       mail_to='jhon@company.com',
                       mail_cc='mary@company.com',
                       mail_cco='',
                       mail_subject='Python Monitor Alert',
                       script_info=script_info,
                       template=txt)



# MAIN CODE
###########
# send mail and register logs
def print_logs(logs, filename, script_info, logger=app):
    send_mail(script_info, logger=logger)
    logger.debug('runing..')
    for l in logs:
        logger.info(filename+' '+str(l.strip()))

def check_threshold(valor, threshold):
    if threshold == 0:
        return False
    elif valor > 99999: # time
        return True if time.time()-valor > threshold else False
    else:
        return True if valor > threshold else False

def monitor(filename, triggers, triggers_off=[], script_info={}, tbr=10, tba=5, tra=999, refresh_sleep=1, time_between_newline=500):
    # variable description
    #time_between_run = tbr     # minimum time between send alerts (could be bypassed with time_between_newline)
    #time_between_append = tba  # time to summarize logs before send an alert (could be bypassed with threshold_run_anyway)
    #threshold_run_anyway = tra # maximun amount of logs before force send an alert (used to bypass time_between_append)
    #time_between_newline       # maximum time without receiving logs (this is a parallel process and ignores all previously defined threshold)

    # shortcut to variables
    time_between_run = tbr
    time_between_append = tba
    threshold_run_anyway = tra

    # reading monitored log file
    file = open(filename,'r')
    st_results = os.stat(filename)
    st_size = st_results[6]
    file.seek(st_size)

    # auxiliary variables
    start_run = time.time()
    last_run = time.time()
    last_append = time.time()
    last_status = time.time()
    last_newline = time.time()
    retorno = []
    script_info['script_log_info'] = []

    # starting monitoring
    app.info('filename=%s >> Starting monitoring' %filename)
    app.info('filename=%s >> triggers=%s' %(str(', ').join(triggers) or "No triggers was set.", filename))
    app.info('filename=%s >> triggers_off=%s' %(str(', ').join(triggers_off) or "No triggers was set.", filename))
    app.info('filename=%s >> time_between_newline=%s seconds' %(filename, time_between_newline))
    while 1:
        app.debug('while runing..'+str(filename))
        where = file.tell()
        line = file.readline()

        if not line:
            time.sleep(refresh_sleep)
            file.seek(where)
        else:
            app.debug('new line! %s' %line)
            last_newline = time.time()
            if trigger_consult(triggers, line):
                if not trigger_consult(triggers_off, line):
                    app.debug('trigger mach!')
                    script_info['script_log_info'].append(line,)
                    last_append = time.time()
                    retorno.append(line,)
                else:
                    app.debug('trigger discarded by triggers_off!')

        # check if there is alerts
        n_logs = len(script_info.get('script_log_info'))
        if n_logs > 0:
            app.debug('there are '+str(n_logs)+' alerts waiting to be send..')
            if check_threshold(last_run, tbr): # tbr = time_between_run
                app.debug('last_run OK: '+str(time.time()-last_run)+'/'+str(tbr))
                if check_threshold(last_append, tba) or check_threshold(n_logs, tra): #time_between_append, threshold_run_anyway
                    app.info('Alert generated on '+filename)
                    print_logs(logs=script_info['script_log_info'], filename=filename, script_info=script_info, logger=alert)
                    script_info['script_log_info']=[]
                    last_run = time.time()
            else:
                app.debug('last_run NOK: '+str(time.time()-last_run)+'/'+str(tbr))

        # heartbeat monitoring
        if check_threshold(last_status, 60):
            app.info('while running for '+filename)
            last_status = time.time()

        # time to live, if seted, the monitoring will stop after the threshold. 0 always return False
        if check_threshold(start_run, 0):
            app.debug('while stopping for '+filename)
            if n_logs > 0: # send remaning alertes on buffer
                print_logs(logs=script_info['script_log_info'], filename=filename, script_info=script_info, logger=alert)
            break

        if check_threshold(last_newline, time_between_newline):
            msg = str(time_between_newline)+' seconds whitout no logs from '+filename
            app.info(msg)
            script_info['script_log_info'].append(msg)
            #send_mail(script_info, logger=app)
            print_logs(logs=script_info['script_log_info'], filename=filename, script_info=script_info, logger=alert)
            script_info['script_log_info']=[]
            last_newline = time.time()

    app.info('while stoped after '+str(int(time.time()-start_run))+' seconds for '+filename)
    app.info('Stopping monitoring >> filename='+filename)

def run_thread_monitor(filename, triggers, triggers_off=[], script_info={}, tbr=10, tba=5, tra=999, refresh_sleep=1, time_between_newline=120):
    if script_info == {}:
        script_info = { 'script_server':socket.gethostname(),'script_name':filename.split("\\")[-1],'script_log_file':filename,'script_log_info':[]}
    threading.Thread(target=monitor, args=(filename, triggers, triggers_off, script_info, tbr, tba, tra, refresh_sleep, time_between_newline)).start()
    app.info('Trigger successfully started!')

def trigger_consult(triggers, line):
    result = False
    for t in triggers:
        app.debug('checking triegger = '+str(t))
        app.debug('on line = '+str(line.strip()))
        if t.lower() in line.lower():
            app.debug('trigger "'+str(t)+'" matched')
            result = True
            break
    app.debug('return = '+str(result))
    return result




# read parameters from command line
def get_parameters():
    parser = argparse.ArgumentParser(prog='log_monitor')
    parser.add_argument('-f',     type=str,             required=True, dest='filename',     help='Full path of monitored file.')
    parser.add_argument('-t',     type=str,  nargs="+", required=True, dest='triggers',     help='Triggers to be alert.')
    parser.add_argument('-t_off', type=str,  nargs="*", default=[],    dest='triggers_off', help='Exclude from triggers.')
    parser.add_argument('-tbr',   type=int,  nargs="?", default=60,    dest='tbr',          help='Minimum time in seconds between send alerts. (default: %(default)s)')
    parser.add_argument('-tba',   type=int,  nargs="?", default=10,    dest='tba',          help='Minimum time in seconds between summary alertas. (default: %(default)s)')
    parser.add_argument('-tra',   type=int,  nargs="?", default=100,   dest='tra',          help='Maximum amount of alerts before force send it. (default: %(default)s)')
    parser.add_argument('-tbn',   type=int,  nargs="?", default=0,     dest='tbn',          help='Maximum time without receiving logs. 0 = Disable (default: %(default)s)')
    return vars(parser.parse_args())




if __name__ == '__main__':
    app.info('Starting..')
    try:
        for config in get_config(host_name):
            app.info('waiting 3 seconds..')
            time.sleep(3)
            app.info('Starting thread for '+str(config))
            run_thread_monitor(**config)
    except Exception as inst:
        app.error('error at: '+str(inst))

