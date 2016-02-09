# coding: UTF-8
import argparse
import logging
import os
import smtplib
import socket
import threading
import time
from email.MIMEText import MIMEText



# LOG CONFIGURATION
####################
#log_dir = '/logs/' 
log_dir = '/home/moises/'


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
# this way we can use de same code at any servers.
def get_config(host_name):
    app.info('Identifying configurations for the host_name: '+str(host_name))
    monitor_config = []
    # examples
    # this configuration will be set for the host "serv-01" only. Note the host should be lower case.
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
    # end configuration for "serv-01"

    # this configuration will be set for the host "serv-01" only. Note the host should be lower case.
    if 'serv-02' in host_name.lower():
        filename = '/logs/app1.log'
        monitor_config.append( { 'filename':filename,
                                 'triggers':['warning', 'error', 'exception'],
                                 'triggers_off':['database is locked'],
                                 'time_between_newline':0} ) # 0 = disabled
    # end configuration for "serv-02"

    # this configuration will be set for the host "moises-virtualbox" only. Note the host should be lower case.
    if 'moises-virtualbox' in host_name.lower():
        filename = '/home/moises/myapp.log'
        monitor_config.append( { 'filename':filename,
                                 'triggers':['warning', 'error', 'exception'],
                                 'triggers_off':[],
                                 'tbr':120,
                                 'time_between_newline':87000} ) #24:10h
    # end configuration for "moises-virtualbox"

    if len(monitor_config) == 0:
        app.warning('No configuration was set for this host_name: '+str(host_name))

    return monitor_config




# MAIL CONFIGURATION
####################
def send_mail(mail_from, mail_to, mail_cc, mail_cco, mail_subject, template):
    status = True
    try:
        msg = MIMEText(template,'html')
        msg['Subject'] = mail_subject
        msg['From'] = mail_from
        msg['To'] = mail_to
        msg['CC'] = mail_cc

        s = smtplib.SMTP('localhost',25) #correio.company.com.br, 25
        s.sendmail(mail_from, [mail_to, mail_cc, mail_cco], msg.as_string())
        s.quit()
        app.info('Mail successfully send!')
    except Exception as inst:
        status = False
        app.error('error at: '+str(inst))
        app.info('Mail not sent!')


def create_msg(thread_info):
    server_name = str(thread_info.get('server_name'))
    file_name = str(thread_info.get('file_name'))
    alerts = []
    for alert in thread_info.get('log_alert'):
        alerts.append('<tr><td>'+alert+'</td></tr>')
    #alerts = ''.join([(lambda x:'<tr><td>'+x+'</td></tr>')(alert) for alert in thread_info.get('log_alert')])
    txt = '''
        <html>
            <head>
                <meta charset="UTF-8">
                <title>Document</title>
                <style type="text/css">
                    html {
                        font: 15pt Arial;
                    }

                    div::before {
                        content: "Log Alert";
                        font: 10pt Arial;
                        font-weight: bold;
                        color: white;
                        background-color: #273747;
                        padding: 5px;
                        display: block;
                        position: relative;
                        top: -10px;
                        left: -10px;
                        width: 560px;
                    }

                    div {
                        background-color: rgba(222,222,222,.8);
                        margin: 20px;
                        padding: 10px;
                        width: 550px;
                        min-height: auto;
                }
                </style>
            </head>
            <body>
                <div>
                    <h1>'''+server_name+'''</h1>
                    <h3>'''+file_name+'''</h3>
                    <table>
                        <tr><th valign="top">Log Alert:</th></tr>
                        '''+alerts+'''
                    </table>        
                </div>
            </body>
            </html> 
    '''
    return txt




# MAIN CODE
###########
# register logs and send mail
def print_logs(thread_info, mail=False):
    logs = thread_info['log_alert']
    filename = thread_info['file_name']
    for l in logs:
        alert.info(filename+' >> '+str(l.strip()))
    if mail:
        txt = create_msg(thread_info)
        send_mail(mail_from='adminssss@moises-pc.local',
                   mail_to='admin@moises-pc.local',
                   mail_cc='',
                   mail_cco='',
                   mail_subject='Python Monitor Alert',
                   template=txt)

def trigger_consult(triggers, line):
    result = False
    app.debug('testing line = '+str(line.strip()))
    app.debug('triggers = '+str(triggers))
    for t in triggers:
        app.debug('checking triegger = '+str(t))
        if t.lower() in line.lower():
            app.debug('trigger "'+str(t)+'" matched')
            result = True
            break
    app.debug('return = '+str(result))
    return result

def check_threshold(valor, threshold):
    if threshold == 0:
        return False
    elif valor > 99999: # time module return a float, so this is used to validade the threshold type
        return True if time.time()-valor > threshold else False
    else:
        return True if valor > threshold else False

def monitor(thread_info, filename, triggers, triggers_off=[], tbr=10, tba=5, tra=999, refresh_sleep=1, time_between_newline=500):
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
    last_run = time.time() - tbr*60 # show the first event without waiting for the time_between_run configuration
    last_append = time.time()
    last_status = time.time()
    last_newline = time.time()
    retorno = []
    thread_info['log_alert'] = []

    # starting monitoring
    app.info('filename=%s >> Starting monitoring' %filename)
    app.info('filename=%s >> triggers=%s' %(filename, str(', ').join(triggers) or "No triggers was set."))
    app.info('filename=%s >> triggers_off=%s' %(filename, str(', ').join(triggers_off) or "No triggers was set."))
    app.info('filename=%s >> time_between_newline=%s seconds' %(filename, time_between_newline))
    while 1:
        app.debug('while runing..'+str(filename))
        where = file.tell()
        line = file.readline()

        if not line:
            time.sleep(refresh_sleep)
            file.seek(where)
        else:
            app.debug('new line! %s' %line.strip())
            last_newline = time.time()
            if trigger_consult(triggers, line):
                app.debug('checking triggers_off')
                if not trigger_consult(triggers_off, line):
                    app.debug('trigger mach!')
                    thread_info['log_alert'].append(line,)
                    last_append = time.time()
                    retorno.append(line,)
                else:
                    app.debug('trigger discarded by triggers_off!')

        # check if there is alerts
        n_logs = len(thread_info.get('log_alert'))
        if n_logs > 0:
            app.debug('there are '+str(n_logs)+' alerts waiting to be send..')
            if check_threshold(last_run, tbr): # tbr = time_between_run
                app.debug('last_run OK: '+str(time.time()-last_run)+'/'+str(tbr))
                if check_threshold(last_append, tba) or check_threshold(n_logs, tra): #time_between_append, threshold_run_anyway
                    app.info('Alert generated on '+filename)
                    print_logs(thread_info)
                    thread_info['log_alert']=[]
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
                print_logs(thread_info)
            break

        if check_threshold(last_newline, time_between_newline):
            msg = str(time_between_newline)+' seconds whitout no logs from '+filename
            app.info(msg)
            thread_info['log_alert'].append(msg)
            print_logs(thread_info)
            thread_info['log_alert']=[]
            last_newline = time.time()

    app.info('while stoped after '+str(int(time.time()-start_run))+' seconds for '+filename)
    app.info('Stopping monitoring >> filename='+filename)

def run_thread_monitor(filename, triggers, triggers_off=[], tbr=10, tba=5, tra=999, refresh_sleep=1, time_between_newline=120):
    thread_info = { 'server_name':socket.gethostname(),'script_name':filename.split("\\")[-1],'file_name':filename,'log_alert':[]}
    threading.Thread(target=monitor, args=(thread_info, filename, triggers, triggers_off, tbr, tba, tra, refresh_sleep, time_between_newline)).start()
    app.info('Trigger successfully started!')




# read parameters from command line. Not in use yet
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

